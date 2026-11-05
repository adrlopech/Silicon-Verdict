"""Resilient structured-output calls to Gemini (single entry point for every call in the project).

What it handles:
- Model chain: configured model + preferred list + models discovered on the account; callers may pass `prefer` to put some first.
- Error classification (the free tier allows only ~20 requests PER DAY per model):
    * 429 "per day" / retry delay > 15 min  -> the model is parked until the quota resets (persisted on disk, so later runs skip it instantly);
    * 429 per-minute                          -> parked for the delay Google reports (capped);
    * 503 / 504 / 500 / timeouts              -> parked briefly so we do not hammer a saturated model;
    * 400 / 404                               -> unusable for this request, skipped for the rest of the process.
- No useless waiting: if every model is parked for a long time it fails immediately with a clear message instead of burning minutes.
- Optional validator: a response it rejects is retried on the next model. Batch helper keeps the valid items of a partial answer.
"""
import json
import logging
import random
import re
import threading
import time
from typing import Any, Callable, List, Optional, Tuple, Type

from google import genai
from google.genai import types
from pydantic import BaseModel, create_model

from config.settings import settings

logger = logging.getLogger(__name__)

PREFERRED_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]
STATE_FILE = settings.BASE_DIR / "data" / "gemini_state.json"
SHORT_COOLDOWN = 25.0        # seconds a model rests after a 503/504/500/timeout
MAX_MINUTE_COOLDOWN = 90.0   # per-minute 429s never park a model longer than this
LONG_WAIT_THRESHOLD = 15 * 60
MAX_WAIT_FOR_MODEL = 45.0    # we only sleep for a model that is back within this many seconds
_TEXT_MODEL_RE = re.compile(r"^gemini-[\d.]+-flash(-lite)?$")

_dead_models: set = set()
_discovered: Optional[List[str]] = None
_state: Optional[dict] = None
_lock = threading.Lock()


class GeminiUnavailable(RuntimeError):
    """Raised when no model can serve the request (quota exhausted, saturated or all attempts failed)."""


# ------------------------------- persistent state -------------------------------
def _load_state() -> dict:
    global _state
    if _state is None:
        try:
            _state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            _state = {}
        _state.setdefault("cooldown", {})
        _state.setdefault("usage", {})
    return _state


def _save_state() -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(_state, indent=1), encoding="utf-8")
    except Exception as exc:  # the state is an optimisation, never a reason to fail
        logger.debug("Could not save Gemini state: %s", exc)


def _park(model: str, seconds: float, reason: str) -> None:
    with _lock:
        st = _load_state()
        st["cooldown"][model] = max(st["cooldown"].get(model, 0), time.time() + seconds)
        _save_state()
    logger.warning("'%s' parked for %s (%s).", model, _fmt(seconds), reason)


def _parked_for(model: str) -> float:
    with _lock:
        return max(0.0, _load_state()["cooldown"].get(model, 0) - time.time())


def _count_use(model: str) -> None:
    with _lock:
        st = _load_state()
        day = time.strftime("%Y-%m-%d")
        st["usage"] = {day: st["usage"].get(day, {})}  # keep today only
        st["usage"][day][model] = st["usage"][day].get(model, 0) + 1
        _save_state()


def usage_today() -> dict:
    with _lock:
        return dict(_load_state()["usage"].get(time.strftime("%Y-%m-%d"), {}))


def quota_status() -> dict:
    """{model: seconds_until_available} for the models currently parked (diagnostics)."""
    now = time.time()
    with _lock:
        return {m: round(t - now) for m, t in _load_state()["cooldown"].items() if t > now}


def _fmt(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 3600}h{seconds % 3600 // 60:02d}m" if seconds >= 3600 else f"{seconds // 60}m{seconds % 60:02d}s" if seconds >= 60 else f"{seconds}s"


# ------------------------------- error handling -------------------------------
def _parse_delay(text: str) -> Optional[float]:
    m = re.search(r"retry in ((?:\d+(?:\.\d+)?[hms])+)", text, flags=re.I) or re.search(r"retryDelay'?\"?: ?'?\"?((?:\d+(?:\.\d+)?[hms])+)", text)
    if not m:
        return None
    total = 0.0
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)([hms])", m.group(1)):
        total += float(num) * {"h": 3600, "m": 60, "s": 1}[unit]
    return total


def _classify(exc: Exception) -> Tuple[str, float]:
    """-> (kind, park_seconds). kind: daily | minute | transient | unusable | other."""
    text = str(exc)
    up = text.upper()
    if "429" in text or "RESOURCE_EXHAUSTED" in up:
        delay = _parse_delay(text)
        if "per day" in text.lower() or "PERDAY" in up.replace(" ", "") or (delay or 0) > LONG_WAIT_THRESHOLD:
            return "daily", max(delay or 6 * 3600, 600)
        return "minute", min(max(delay or 30, 5), MAX_MINUTE_COOLDOWN)
    if re.search(r"\b(400|401|403|404)\b", text) or any(k in up for k in ("INVALID_ARGUMENT", "NOT_FOUND", "PERMISSION_DENIED", "API_KEY_INVALID")):
        return "unusable", 0
    if any(k in up for k in ("503", "504", "500", "UNAVAILABLE", "DEADLINE", "INTERNAL", "TIMEOUT", "TIMED OUT", "CONNECTION", "READ ERROR", "REMOTEPROTOCOL")):
        return "transient", SHORT_COOLDOWN * random.uniform(0.8, 1.6)
    return "other", SHORT_COOLDOWN


def _discover_models(client: genai.Client) -> List[str]:
    """Text 'flash' models the key can use, beyond the preferred list. Cached per process."""
    global _discovered
    if _discovered is not None:
        return _discovered
    found: List[str] = []
    try:
        for m in client.models.list():
            name = (m.name or "").replace("models/", "")
            actions = getattr(m, "supported_actions", None) or []
            if "generateContent" in actions and _TEXT_MODEL_RE.match(name):
                found.append(name)
    except Exception as exc:
        logger.warning("Could not list Gemini models (%s). Using the preferred chain only.", str(exc)[:120])
    _discovered = sorted(found, reverse=True)  # newest version numbers first
    return _discovered


def model_chain(client: genai.Client) -> List[str]:
    chain = [settings.GEMINI_MODEL] + PREFERRED_MODELS + _discover_models(client)
    ordered = list(dict.fromkeys(chain))
    return [m for m in ordered if m not in _dead_models]



def _gemini_structured(
    prompt: str,
    system_instruction: Optional[str],
    schema: Optional[Type[BaseModel]],
    temperature: float = 0.7,
    validate: Optional[Callable[[Any], List[str]]] = None,
    timeout_ms: int = 60000,
    max_passes: int = 5,
    max_total_seconds: float = 300.0,
    prefer: Optional[List[str]] = None,
    max_output_tokens: Optional[int] = None,
    images: Optional[List[bytes]] = None,
) -> Tuple[Any, Tuple[int, int], str]:
    """Returns (parsed_object, (input_tokens, output_tokens), model_name). Raises GeminiUnavailable.

    schema=None returns the parsed JSON (dict/list). `prefer` lists models to try first (e.g. a stronger one for reviews).
    `max_passes` bounds the number of model calls to max_passes * 2.
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY, http_options=types.HttpOptions(timeout=timeout_ms))
    start = time.time()
    last_error = "no attempt made"
    tries: dict = {}
    max_calls = max_passes * 2
    calls = 0

    while calls < max_calls:
        chain = model_chain(client)
        if prefer:
            chain = [m for m in prefer if m in chain] + [m for m in chain if m not in prefer]
        ready = [m for m in chain if _parked_for(m) <= 0]
        if not ready:
            waits = [(_parked_for(m), m) for m in chain]
            soonest = min(waits)[0] if waits else 0
            if not waits or soonest > MAX_WAIT_FOR_MODEL or time.time() - start + soonest > max_total_seconds:
                parked = ", ".join(f"{m} {_fmt(w)}" for w, m in sorted(waits)[:4])
                raise GeminiUnavailable(f"no Gemini model available right now (free-tier quota or saturation). Back in: {parked}. Last error: {last_error}")
            logger.info("All models resting; waiting %.0fs for the first one...", soonest + 0.5)
            time.sleep(soonest + 0.5)
            continue
        if time.time() - start > max_total_seconds:
            raise GeminiUnavailable(f"time budget exhausted ({last_error})")
        model = min(ready, key=lambda m: (tries.get(m, 0), chain.index(m)))  # least-tried first, chain order breaks ties
        tries[model] = tries.get(model, 0) + 1
        calls += 1
        try:
            logger.info("Gemini request via '%s' (call %d/%d)...", model, calls, max_calls)
            cfg = dict(system_instruction=system_instruction, response_mime_type="application/json", temperature=temperature)
            if schema is not None:
                cfg["response_schema"] = schema
            if max_output_tokens:
                cfg["max_output_tokens"] = max_output_tokens
            contents = [types.Part.from_bytes(data=b, mime_type="image/jpeg") for b in (images or [])] + [prompt] if images else prompt
            res = client.models.generate_content(model=model, contents=contents, config=types.GenerateContentConfig(**cfg))
            _count_use(model)
            obj = schema.model_validate_json(res.text) if schema is not None else json.loads(res.text)
            if validate:
                problems = validate(obj)
                if problems:
                    last_error = f"rejected by validator: {problems}"
                    logger.warning("Response from '%s' rejected: %s", model, problems)
                    continue
            usage = getattr(res, "usage_metadata", None)
            tokens = (
                (getattr(usage, "prompt_token_count", 0) or 0) if usage else 0,
                (getattr(usage, "candidates_token_count", 0) or 0) if usage else 0,
            )
            return obj, tokens, model
        except Exception as exc:
            last_error = str(exc)[:220].replace("\n", " ")
            kind, secs = _classify(exc)
            if kind == "unusable" and "NO LONGER AVAILABLE" in last_error.upper():
                _park(model, 24 * 3600, "retired for this account")  # persisted: later runs never try it again today
            elif kind == "unusable":
                logger.warning("'%s' unusable for this request, skipped for this run: %s", model, last_error[:140])
                _dead_models.add(model)
            elif kind == "daily":
                _park(model, secs, "daily free-tier quota exhausted")
            else:
                _park(model, secs, f"{kind}: {last_error[:80]}")
    raise GeminiUnavailable(last_error)


# ------------------------------- fallback providers (OpenAI-compatible APIs) -------------------------------
# To add a provider: add its key / model-list fields to config/settings.py and one line here. Order = fallback order after Gemini.
PROVIDERS = [
    # (name, base url, settings attribute with the key, settings attribute with comma-separated models in preference order)
    ("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "GROQ_MODELS"),
    # {CLOUDFLARE_ACCOUNT_ID} in a URL is replaced with that setting; the provider stays disabled while it is empty
    ("cloudflare", "https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_MODELS"),
]
PROVIDER_MAX_OUTPUT = 5000   # free tiers meter tokens per minute (Groq: 8000 for prompt + reserved output), so the reserve must stay small
_provider_dead: set = set()


class _ProviderBusy(Exception):
    def __init__(self, wait: float, why: str):
        super().__init__(why)
        self.wait = wait


def _provider_key(attr: str) -> str:
    key = (getattr(settings, attr, "") or "").strip()
    return "" if (not key or key.startswith("your_")) else key


def _resolve(prov: tuple) -> Optional[tuple]:
    """The provider with its URL template filled in, or None if it is not fully configured."""
    url = prov[1]
    for ph in re.findall(r"\{(\w+)\}", url):
        val = (getattr(settings, ph, "") or "").strip()
        if not val:
            return None
        url = url.replace("{" + ph + "}", val)
    return (prov[0], url, prov[2], prov[3]) if _provider_key(prov[2]) else None


def enabled_providers() -> List[tuple]:
    return [r for r in (_resolve(p) for p in PROVIDERS) if r]


def _strip_titles(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _strip_titles(v) for k, v in node.items() if k != "title"}
    if isinstance(node, list):
        return [_strip_titles(v) for v in node]
    return node


def _user_content(text: str, images):
    if not images:
        return text
    import base64
    return [{"type": "text", "text": text}] + [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(b).decode()}} for b in images]


def _compatible_one_model(prov: tuple, model: str, prompt, system, schema, temperature, validate, max_output_tokens, attempts: int = 2, images=None):
    """One model of an OpenAI-compatible API. Raises _ProviderBusy (rate/size limit: try another model), GeminiUnavailable (fatal for the provider)
    or ValueError (this model cannot produce a valid answer)."""
    import requests
    name, url, key_attr, _m = prov
    headers = {"Authorization": f"Bearer {_provider_key(key_attr)}", "Content-Type": "application/json"}
    feedback, last_error, use_temperature, use_json_mode = "", "no attempt made", True, True
    for attempt in range(1, attempts + 1):
        body = {"model": model, "max_completion_tokens": min(max_output_tokens or PROVIDER_MAX_OUTPUT, PROVIDER_MAX_OUTPUT),
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": _user_content(prompt + feedback, images)}]}
        if use_json_mode:
            body["response_format"] = {"type": "json_object"}
        if use_temperature:
            body["temperature"] = temperature
        if "gpt-oss" in model:
            body["reasoning_effort"] = "low"  # reasoning tokens count against the output budget
        logger.info("%s request via '%s' (attempt %d/%d)...", name, model, attempt, attempts)
        try:
            r = requests.post(f"{url}/chat/completions", headers=headers, json=body, timeout=120)
        except requests.RequestException as exc:
            last_error = f"network: {exc}"[:200]
            continue
        low = r.text.lower()
        if r.status_code == 400 and "temperature" in low and use_temperature:
            use_temperature = False
            continue
        if r.status_code == 400 and any(k in low for k in ("json_validate_failed", "failed_generation", "parsing failed")):
            last_error, use_json_mode = "malformed JSON", False  # strict JSON mode is flaky with long schemas: plain text + our own extraction
            feedback = "\n\nYour previous answer was not valid JSON (possibly cut off). Return a complete, valid JSON object."
            continue
        if r.status_code in (400, 404) and any(k in low for k in ("model_not_found", "does not exist", "decommissioned")):
            _provider_dead.add(f"{name}:{model}")
            raise ValueError(f"model {model} not available")
        if r.status_code in (401, 403):
            raise GeminiUnavailable(f"{name} rejected the API key ({r.status_code}).")
        if r.status_code == 429 and ("insufficient_quota" in low or "per day" in low):
            raise GeminiUnavailable(f"{name}: daily quota or credit exhausted.")
        if r.status_code in (413, 429):
            try:
                wait = float(r.headers.get("retry-after", 20))
            except (TypeError, ValueError):
                wait = 20.0
            raise _ProviderBusy(wait, f"{name}/{model} per-minute token limit ({r.status_code})")
        if r.status_code in (500, 502, 503, 504):
            last_error = f"{name} {r.status_code}"
            time.sleep(3 * attempt)
            continue
        if r.status_code != 200:
            raise GeminiUnavailable(f"{name} error {r.status_code}: {r.text[:200]}")
        data = r.json()
        try:
            text = data["choices"][0]["message"]["content"] or ""
            if not use_json_mode:  # plain-text answer: drop code fences / chatter around the JSON object
                text = text[text.index("{"): text.rindex("}") + 1]
            obj = schema.model_validate_json(text) if schema is not None else json.loads(text)
        except Exception as exc:
            last_error = f"invalid answer: {str(exc)[:160]}"
            feedback = f"\n\nYour previous answer was invalid ({last_error}). Return a corrected, complete JSON object."
            continue
        if validate:
            problems = validate(obj)
            if problems:
                last_error = f"rejected by validator: {problems}"
                logger.warning("%s/%s response rejected: %s", name, model, problems)
                feedback = "\n\nYour previous answer was rejected for these reasons, fix ALL of them: " + "; ".join(map(str, problems))
                continue
        usage = data.get("usage") or {}
        return obj, (usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)), f"{name}:{model}"
    raise ValueError(last_error)


def _compatible_structured(prov: tuple, prompt, system_instruction, schema, temperature, validate, max_output_tokens, images=None):
    """Tries every model of a provider (rotating on rate limits; one short wait if all are busy). Schema goes in the prompt in compact form."""
    name, _url, _k, models_attr = prov
    system = system_instruction or "You are a precise assistant."
    if schema is not None:
        system += "\n\nRespond ONLY with one JSON object that validates against this JSON Schema (no markdown):\n" + json.dumps(_strip_titles(schema.model_json_schema()), separators=(",", ":"))
    else:
        system += "\n\nRespond ONLY with one valid JSON object."
    models = [m.strip() for m in str(getattr(settings, models_attr.replace("_MODELS", "_VISION_MODELS") if images else models_attr, "")).split(",") if m.strip()]
    if images and not models:
        raise GeminiUnavailable(f"{name}: no vision model configured")
    errors: List[str] = []
    for round_idx in range(2):
        shortest_wait = None
        for model in models:
            if f"{name}:{model}" in _provider_dead:
                continue
            try:
                return _compatible_one_model(prov, model, prompt, system, schema, temperature, validate, max_output_tokens, images=images)
            except _ProviderBusy as busy:
                errors.append(str(busy))
                shortest_wait = busy.wait if shortest_wait is None else min(shortest_wait, busy.wait)
            except ValueError as exc:
                errors.append(f"{name}/{model}: {exc}")
        if shortest_wait is None or shortest_wait > 45 or round_idx == 1:
            break
        logger.info("%s: every model hit its per-minute limit; waiting %.0fs...", name, shortest_wait + 1)
        time.sleep(shortest_wait + 1)
    raise GeminiUnavailable(f"{name} fallback failed: {errors[-1] if errors else 'no usable model'}")


def generate_structured(
    prompt: str,
    system_instruction: Optional[str],
    schema: Optional[Type[BaseModel]],
    temperature: float = 0.7,
    validate: Optional[Callable[[Any], List[str]]] = None,
    timeout_ms: int = 60000,
    max_passes: int = 5,
    max_total_seconds: float = 300.0,
    prefer: Optional[List[str]] = None,
    max_output_tokens: Optional[int] = None,
    provider_first: Optional[str] = None,
    images: Optional[List[bytes]] = None,
) -> Tuple[Any, Tuple[int, int], str]:
    """Gemini first; if no Gemini model can serve the request, each configured fallback provider is tried in order.
    `provider_first="groq"` tries that provider before Gemini (e.g. a stronger model for fact-checking).
    Returns (parsed_object, (input_tokens, output_tokens), model_name). Raises GeminiUnavailable if every provider fails."""
    if provider_first:
        for prov in enabled_providers():
            if prov[0] == provider_first:
                try:
                    return _compatible_structured(prov, prompt, system_instruction, schema, temperature, validate, max_output_tokens, images)
                except GeminiUnavailable as pexc:
                    logger.warning("%s unavailable (%s); using Gemini.", provider_first, str(pexc)[:140])
    try:
        return _gemini_structured(prompt, system_instruction, schema, temperature, validate, timeout_ms, max_passes, max_total_seconds, prefer, max_output_tokens, images)
    except GeminiUnavailable as exc:
        providers = [p for p in enabled_providers() if p[0] != provider_first]
        if not providers:
            raise
        errors = [f"gemini: {str(exc)[:120]}"]
        logger.warning("Gemini unavailable (%s).", errors[0])
        for prov in providers:
            logger.warning("Falling back to %s...", prov[0])
            try:
                return _compatible_structured(prov, prompt, system_instruction, schema, temperature, validate, max_output_tokens, images)
            except GeminiUnavailable as pexc:
                errors.append(str(pexc)[:140])
                logger.warning("%s", pexc)
        raise GeminiUnavailable(" | ".join(errors))


def generate_structured_list(
    prompt: str,
    system_instruction: str,
    item_schema: Type[BaseModel],
    count: int,
    validate_item: Callable[[Any], List[str]],
    temperature: float = 0.8,
    **kwargs: Any,
) -> Tuple[List[Any], Tuple[int, int], str]:
    """Asks for `count` different items in ONE request (one quota unit instead of `count`) and keeps every item that passes
    `validate_item`; the call only counts as failed when none is valid."""
    Batch = create_model("Batch", items=(List[item_schema], ...))
    kept: List[Any] = []

    def _validate(batch: Any) -> List[str]:
        kept.clear()
        problems: List[str] = []
        for item in batch.items:
            p = validate_item(item)
            if p:
                problems.append(str(p)[:120])
            else:
                kept.append(item)
        return [] if kept else (problems[:3] or ["empty batch"])

    full_prompt = prompt + f"\nReturn a JSON object with `items`: a list of EXACTLY {count} different items (different topics), each matching the schema. Every item must be as long, complete and detailed as if it were the only one requested: do NOT shorten items because there are several."
    _obj, tokens, model = generate_structured(
        prompt=full_prompt, system_instruction=system_instruction, schema=Batch, temperature=temperature,
        validate=_validate, max_output_tokens=kwargs.pop("max_output_tokens", 32768), **kwargs,
    )
    logger.info("Batch via %s: %d of %d items valid", model, len(kept), count)
    return list(kept), tokens, model
