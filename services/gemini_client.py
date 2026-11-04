"""Resilient structured-output calls to Gemini.

- Rotates across a chain of text models (preferred order first, then models discovered on the account),
  so a demand spike on one model does not stop the pipeline.
- Retries 503/504/429/500 with exponential backoff + jitter after each full pass over the chain.
- Skips models that do not exist for the key (404) or reject the request (400) for the rest of the process.
- An optional validator can reject a response (treated like a failure: next model, no sleep).
"""
import logging
import random
import re
import time
from typing import Any, Callable, List, Optional, Tuple, Type

from google import genai
from google.genai import types
from pydantic import BaseModel

from config.settings import settings

logger = logging.getLogger(__name__)

PREFERRED_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]
_TEXT_MODEL_RE = re.compile(r"^gemini-[\d.]+-flash(-lite)?$")
BACKOFF_SECONDS = [2, 5, 10, 20, 40]

_dead_models: set = set()
_discovered: Optional[List[str]] = None


class GeminiUnavailable(RuntimeError):
    """Raised when every model/attempt failed."""


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


def _is_retriable(exc: Exception) -> bool:
    msg = str(exc).upper()
    return any(k in msg for k in ("503", "504", "429", "500", "UNAVAILABLE", "DEADLINE", "RESOURCE_EXHAUSTED", "INTERNAL", "TIMEOUT", "TIMED OUT", "CONNECTION"))


def generate_structured(
    prompt: str,
    system_instruction: str,
    schema: Type[BaseModel],
    temperature: float = 0.7,
    validate: Optional[Callable[[Any], List[str]]] = None,
    timeout_ms: int = 45000,
    max_passes: int = 5,
    max_total_seconds: float = 300.0,
) -> Tuple[Any, Tuple[int, int], str]:
    """Returns (parsed_object, (input_tokens, output_tokens), model_name). Raises GeminiUnavailable."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY, http_options=types.HttpOptions(timeout=timeout_ms))
    start = time.time()
    last_error = "no attempt made"

    for pass_idx in range(max_passes):
        chain = model_chain(client)
        # Rotate the starting model each pass so a saturated first choice does not eat every pass
        if chain:
            shift = pass_idx % len(chain)
            chain = chain[shift:] + chain[:shift]
        for model in chain:
            if time.time() - start > max_total_seconds:
                raise GeminiUnavailable(f"time budget exhausted ({last_error})")
            try:
                logger.info("Gemini request via '%s' (pass %d/%d)...", model, pass_idx + 1, max_passes)
                res = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=temperature,
                    ),
                )
                obj = schema.model_validate_json(res.text)
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
                last_error = str(exc)[:200]
                if _is_retriable(exc):
                    logger.warning("'%s' busy or timed out: %s", model, last_error[:120])
                elif "404" in last_error or "NOT_FOUND" in last_error.upper() or "400" in last_error or "INVALID_ARGUMENT" in last_error.upper():
                    logger.warning("'%s' unusable for this request, skipping it for this run: %s", model, last_error[:120])
                    _dead_models.add(model)
                else:
                    logger.warning("'%s' failed: %s", model, last_error[:120])
        if pass_idx < max_passes - 1:
            wait = BACKOFF_SECONDS[min(pass_idx, len(BACKOFF_SECONDS) - 1)] * random.uniform(0.8, 1.3)
            logger.info("All models failed this pass. Waiting %.1fs before retrying...", wait)
            time.sleep(wait)

    raise GeminiUnavailable(last_error)
