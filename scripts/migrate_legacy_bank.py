#!/usr/bin/env python3
"""Moves the pregenerated scripts of the old categories into the Motion model.

  simple rows (StoryProject, mascot + vector scenes)        -> MotionProject, format 'simple' (or 'hardware' when the row is a hardware curiosity), the mascot poses become cursor actions
  game rows   (game_frame/stat_card triggers)   -> MotionProject, kind 'game': its game_frame beats become footage scenes, shown over screenshots of that game
                                                              (services.game_images.stage_legacy_footage assigns them when the video is rendered)

Every converted script must pass the same validator a live Motion generation passes (services.motion_generator.make_validator) before its row is rewritten
(series -> 'motion'); rows that cannot be converted are left untouched and reported.

  python scripts/migrate_legacy_bank.py --dry-run      # convert and validate, write nothing
  python scripts/migrate_legacy_bank.py                # rewrite the rows
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.game_images import LEGACY_DIRS  # noqa: E402
from services.history import get_db_connection  # noqa: E402
from services.motion_generator import CURSOR_ACTIONS, MotionProject, MotionSceneModel, cursor_from_pose, estimated_seconds, make_validator  # noqa: E402

ICON_MAP = {"fire": "flame", "magnifier": "search", "drop": "droplet", "plane": "rocket", "cable": "net", "building": "server", "eye": "search", "chip": "chip", "battery": "battery",
            "bolt": "bolt", "wifi": "wifi", "cloud": "cloud", "lock": "lock", "clock": "clock", "phone": "phone", "gear": "gear", "heart": "heart", "star": "star", "arrow": "arrow",
            "thermometer": "thermometer", "bulb": "bulb", "wave": "wave"}
FILLERS = {"so", "but", "and", "now", "then", "here's", "heres", "well", "also", "yes", "okay", "ok", "oh", "that's", "thats", "because"}
MAX_WORDS = 20


def clean(w: str) -> str:
    return re.sub(r"[^\w]", "", w.lower())


def sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def chunk_text(text: str, limit: int = MAX_WORDS) -> List[str]:
    """Splits narration into pieces of at most `limit` words, at sentence ends first, then at commas."""
    out: List[str] = []
    cur: List[str] = []
    for sent in sentences(text):
        parts = [sent]
        if len(sent.split()) > limit:
            parts = [p.strip() for p in re.split(r"(?<=[,;:])\s+", sent) if p.strip()]
        for part in parts:
            n = len(part.split())
            while n > limit:  # last resort: cut a long clause in half
                ws = part.split()
                cut = limit
                out.append(" ".join(cur + ws[:cut]) if not cur else " ".join(cur))
                if cur:
                    cur = []
                    continue
                part, n = " ".join(ws[cut:]), len(ws) - cut
            if cur and len(" ".join(cur).split()) + n > limit:
                out.append(" ".join(cur))
                cur = []
            cur.append(part)
    if cur:
        out.append(" ".join(cur))
    out = [o for o in out if o.strip()]
    merged: List[str] = []
    for o in out:  # a piece shorter than 3 words cannot be a narration: it joins its neighbour
        if merged and (len(o.split()) < 3 or len(merged[-1].split()) < 3):
            merged[-1] = merged[-1] + " " + o
        else:
            merged.append(o)
    return merged


STOP_TAIL = {"a", "an", "the", "to", "of", "and", "in", "on", "that", "for", "with", "is", "are", "was", "it", "its", "your", "you", "or", "but", "so", "as", "at", "by", "from", "this", "these", "those",
             "can", "will", "than", "when", "while", "if", "into", "not", "do", "does", "did", "has", "have", "had", "be", "been", "just", "really", "simply", "actually", "very"}


def _tidy(ws: List[str]) -> List[str]:
    ws = [w.strip(",.;:!?\"'()") for w in ws if w.strip(",.;:!?\"'()")]
    while ws and clean(ws[0]) in FILLERS:
        ws.pop(0)
    while ws and clean(ws[-1]) in STOP_TAIL:
        ws.pop()
    return ws


def headline(chunk: str) -> Tuple[str, Optional[str]]:
    """A short on-screen line from a spoken line: its first clause (3-6 words, never ending on a stopword); accent = its last 1-2 words."""
    clauses = [c for c in re.split(r"[.!?;:\u2014]|, ", chunk.strip()) if c.strip()]
    ws: List[str] = []
    for c in clauses:
        cand = _tidy(c.split()[:6])
        if len(cand) >= 3:
            ws = cand
            break
        if len(cand) > len(ws):
            ws = cand
    if len(ws) < 2:
        ws = _tidy(re.sub(r"[.!?;:,]", "", chunk).split()[:6]) or ["Tech", "fact"]
    if len(ws) >= 5:
        return " ".join(ws[:-2]), " ".join(ws[-2:])
    if len(ws) >= 3:
        return " ".join(ws[:-1]), ws[-1]
    return " ".join(ws), None


def key_phrase(chunk: str) -> str:
    """2-3 striking words of a line, for a bigText scene."""
    t, a = headline(chunk)
    ws = ((a or "") + " " + t).split() if a else t.split()
    ws = _tidy(ws[-3:] if a is None else (a.split() + [])[-3:]) if a else _tidy(ws[-3:])
    return " ".join(ws[-3:]) or t


def spoken(value: float, narration: str) -> bool:
    txt = narration.lower().replace(",", "")
    digits = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", txt)]
    if any(abs(d - value) < 1e-6 or (value and abs(d - value) / value < 0.06) for d in digits):
        return True
    nums = {"zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
            "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million", "billion"}
    return any(w in nums for w in re.findall(r"[a-z]+", txt))


def segments(script: str, anchors: List[str]) -> List[str]:
    """Cuts the script at each anchor word (in order). Returns one narration per anchor (the first one also gets whatever precedes it)."""
    words = script.split()
    starts: List[int] = []
    pos = 0
    for a in anchors:
        idx = next((i for i in range(pos, len(words)) if clean(words[i]) == clean(a)), None)
        starts.append(idx if idx is not None else -1)
        if idx is not None:
            pos = idx + 1
    found = [(i, s) for i, s in enumerate(starts) if s >= 0]
    if not found:
        return [script]
    cuts = [0] + [s for _, s in found[1:]]
    cuts = sorted(set(cuts))
    segs = [" ".join(words[a:b]) for a, b in zip(cuts, cuts[1:] + [len(words)])]
    out: List[str] = []
    for sg in segs:
        if out and len(sg.split()) < 3:
            out[-1] += " " + sg
        else:
            out.append(sg)
    return [s for s in out if s.strip()]


def icons_of(*names) -> Optional[List[str]]:
    out = [ICON_MAP[n] for n in names if n and n in ICON_MAP]
    return out[:3] or None


def words_n(t: Optional[str]) -> int:
    return len((t or "").split())


def trim_words(t: str, n: int) -> str:
    return " ".join(t.split()[:n])


def story_scene_to_motion(sc: dict, narr: str, flash_text: Optional[str] = None) -> dict:
    """One legacy StoryScene (vector_type + labels) -> one Motion scene dict, narration included."""
    vt = sc.get("vector_type") or "none"
    label = (sc.get("label") or "").strip()
    text = (sc.get("text") or "").strip()
    d: Dict = {"narration": narr, "durationInFrames": 90, "type": "textWithAccent"}
    h_text, h_acc = headline(narr)
    ic = icons_of(sc.get("icon"), sc.get("icon2"), sc.get("icon3"))
    if sc.get("flash"):
        d.update(type="flash", text=(flash_text or text or label or h_text).upper()[:40])
        d["text"] = trim_words(d["text"], 5)
        return d
    if vt == "counter" and sc.get("value_to") and float(sc["value_to"]) > 0 and spoken(float(sc["value_to"]), narr):
        d.update(type="counter", text=trim_words(label or h_text, 6), value=float(sc["value_to"]), unit="")
        if h_acc and not label:
            d["accentText"] = h_acc
    elif vt == "big_text" and text:
        n = words_n(text)
        if n <= 3:
            d.update(type="bigText", text=text)
        else:
            ws = text.split()
            d.update(type="textWithAccent", text=" ".join(ws[: max(1, n - 2)][:5]), accentText=" ".join(ws[-2:]))
    elif vt == "bars" and sc.get("label") and sc.get("label2"):
        d.update(type="list", text=trim_words(h_text, 5), items=[trim_words(label, 5), trim_words(sc["label2"], 5)])
    elif vt == "trio":
        items = [trim_words(x, 5) for x in (sc.get("label"), sc.get("label2"), sc.get("label3")) if x]
        if len(items) >= 2:
            d.update(type="list", text=trim_words(h_text, 5), items=items)
        else:
            d.update(text=h_text, accentText=h_acc)
    elif vt in ("icon", "flow", "gauge") and label:
        ws = label.split()
        if len(ws) >= 3:
            d.update(text=" ".join(ws[:-1][:6]), accentText=ws[-1])
        elif len(ws) == 2:
            d.update(text=ws[0], accentText=ws[1])
        else:
            d.update(text=label, accentText=h_acc if h_acc and len(h_acc.split()) <= 3 else None)
    else:
        d.update(text=h_text, accentText=h_acc)
    if ic:
        d["icons"] = ic
    return d


def finish(scenes: List[dict], pose_for: List[Optional[str]]) -> List[dict]:
    """Applies structure rules: adjacent types, first scene, cursor actions (from the legacy mascot poses), merged shorts."""
    for i, s in enumerate(scenes):
        s["cursor"] = cursor_from_pose(pose_for[i] if i < len(pose_for) else None, s["type"], i, len(scenes))
        assert s["cursor"] in (None, *CURSOR_ACTIONS)
        if s["type"] == "bigText" and words_n(s["text"]) > 4:
            s["type"] = "textWithAccent"
        if s["type"] == "textWithAccent" and not s.get("accentText"):
            ws = s["text"].split()
            if len(ws) >= 3:
                s["text"], s["accentText"] = " ".join(ws[:-1]), ws[-1]
    def key_of(b: dict) -> str:
        return trim_words(b.get("accentText") or " ".join((b.get("text") or "").split()[-3:]), 3)

    for _ in range(3):
        changed = False
        for i in range(1, len(scenes)):
            a, b = scenes[i - 1], scenes[i]
            if a["type"] != b["type"] or b["type"] in ("outro", "footage"):
                continue
            changed = True
            if b["type"] == "textWithAccent" and words_n(b["text"]) <= 4 and not b.get("accentText"):
                b["type"] = "bigText"
            elif b["type"] == "textWithAccent":
                b["type"], b["text"], b["accentText"] = "bigText", key_of(b), None
            elif b["type"] == "bigText":
                b["type"] = "textWithAccent"
                ws = b["text"].split()
                if len(ws) >= 2 and not b.get("accentText"):
                    b["text"], b["accentText"] = " ".join(ws[:-1]), ws[-1]
            else:  # counter / list / flash repeated: tell it as a plain headline
                b["type"] = "textWithAccent"
                if not b.get("text") and b.get("items"):
                    b["text"] = b["items"][0]
                for k in ("items", "value", "unit"):
                    b.pop(k, None)
                if not b.get("accentText"):
                    ws = b["text"].split()
                    if len(ws) >= 3:
                        b["text"], b["accentText"] = " ".join(ws[:-1]), ws[-1]
        if not changed:
            break
    if scenes and scenes[0]["type"] not in ("bigText", "textWithAccent"):
        scenes[0]["type"] = "textWithAccent"
    return scenes


def make_outro(narr: str) -> dict:
    return {"type": "outro", "text": "STAY CURIOUS", "accentText": "Follow for more", "narration": narr, "durationInFrames": 90}


def hardware_poses(n: int, base: List[Optional[str]]) -> List[Optional[str]]:
    """Hardware keeps the cursor as an accent: the hook, a reveal in the middle, the takeaway and the outro (poses taken from the legacy script when it had them)."""
    keep = {0, n // 3, (2 * n) // 3, n - 2, n - 1}
    cycle = ["surprised", "point", "think", "shrug", "cheer"]
    out: List[Optional[str]] = [None] * n
    for k, i in enumerate(sorted(i for i in keep if 0 <= i < n)):
        p = base[i] if i < len(base) and base[i] and base[i] != "idle" else cycle[k % len(cycle)]
        out[i] = p
    return out


def chunk_spans(script: str) -> Tuple[List[str], List[Tuple[int, int]]]:
    """Whole-sentence narration pieces of the script and the (first, last+1) word index each covers (shorter pieces when the script is short, to reach 11 scenes)."""
    chunks: List[str] = []
    for limit in (MAX_WORDS, 16, 13, 11):
        chunks = chunk_text(script, limit)
        if len(chunks) >= 11:
            break
    spans, pos = [], 0
    for c in chunks:
        n = len(c.split())
        spans.append((pos, pos + n))
        pos += n
    return chunks, spans


def anchor_chunks(script: str, anchors: List[str], spans: List[Tuple[int, int]]) -> List[Optional[int]]:
    """For each anchor (in order) the index of the chunk that contains its word (None when the word is not found)."""
    words = script.split()
    out: List[Optional[int]] = []
    pos = 0
    for a in anchors:
        idx = next((i for i in range(pos, len(words)) if clean(words[i]) == clean(a)), None)
        if idx is None:
            out.append(None)
            continue
        pos = idx + 1
        out.append(next((k for k, (lo, hi) in enumerate(spans) if lo <= idx < hi), None))
    return out


USE_LLM = True
LLM_FALLBACKS = 0
CACHE_PATH = BASE_DIR / "temp" / "legacy_headlines.json"
_CACHE: Dict[str, list] = {}


def llm_headlines(chunks: List[str], title: str = "") -> List[Optional[Tuple[str, str, str]]]:
    """On-screen headlines (text, accent, big) for narration lines, written by the LLM; None entries (or a whole None list) mean 'use the heuristic'."""
    global LLM_FALLBACKS
    if not USE_LLM or not chunks:
        return [None] * len(chunks)
    import hashlib
    if not _CACHE and CACHE_PATH.is_file():
        _CACHE.update(json.loads(CACHE_PATH.read_text(encoding="utf-8")))
    ck = hashlib.sha1(("v2|" + "\n".join(chunks)).encode()).hexdigest()
    if ck in _CACHE:
        return [tuple(x) for x in _CACHE[ck]]
    from pydantic import BaseModel
    from services.gemini_client import GeminiUnavailable, generate_structured

    class H(BaseModel):
        text: str
        accent: str
        big: str

    class HL(BaseModel):
        lines: List[H]

    def content(text: str) -> set:
        return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if len(w) > 3 and w not in STOP_TAIL and w not in FILLERS}

    vocab = content(" ".join(chunks))
    WEAK = {"profile", "sound", "data", "lens", "mode", "on", "off", "more", "this", "that", "audio", "system", "thing", "stuff", "idea"}

    def validate(x: HL) -> List[str]:
        if len(x.lines) != len(chunks):
            return [f"need exactly {len(chunks)} lines, got {len(x.lines)}"]
        bad = []
        seen = set()
        for i, (h, ch) in enumerate(zip(x.lines, chunks), 1):
            h.text, h.accent, h.big = [re.sub(r"\s+", " ", v).strip().strip("\"'").rstrip(".") for v in (h.text, h.accent, h.big)]
            if h.accent and not content(h.accent):
                h.accent = ""
            if h.text.split() and clean(h.text.split()[-1]) in STOP_TAIL:
                bad.append(f"line {i}: the headline ends on a loose word ({h.text.split()[-1]!r})")
            if not 2 <= len(h.text.split()) <= 5 or len(h.accent.split()) > 2 or not 1 <= len(h.big.split()) <= 3:
                bad.append(f"line {i}: text 2-5 words, accent 0-2 words, big 1-3 words")
                continue
            if h.big.lower() in WEAK or (len(h.big.split()) == 1 and len(h.big) < 5):
                bad.append(f"line {i}: `big` is too vague ({h.big!r}): name the actual idea")
            if not (content(h.text + " " + h.big) & content(ch)) and not (content(h.text + " " + h.big) & vocab):
                bad.append(f"line {i}: the headline shares no key word with its narration line")
            if h.text.lower() in seen:
                bad.append(f"line {i}: headline repeats an earlier one")
            seen.add(h.text.lower())
        return bad

    try:
        res, _tok, _model = generate_structured(
            prompt=f"Video title: {title}\nNarration lines, in order (together they form one monologue):\n" + "\n".join(f"{i + 1}. {c}" for i, c in enumerate(chunks)) + "\nReturn one headline object per line, same order and same count.",
            system_instruction="You write the on-screen headlines of a kinetic-typography tech video, like premium product reels. Each headline must make sense on its own on a phone screen and name "
                               "the real idea of its narration line, using the line's own key words (never generic labels such as Profile, Sound, Data or Mode). For each numbered line produce: "
                               "`text` (2-5 words, a complete mini phrase such as 'Mic on, quality gone'), `accent` (1-2 words shown in colour under it: the emotional key words, may be empty), "
                               "`big` (1-3 words naming the concrete thing, e.g. 'Narrow bandwidth', for a one-word-punch scene). Different headlines for different lines. "
                               "American English, no emojis, no final period, and NEVER add a claim, number or name that the line does not contain.",
            schema=HL, temperature=0.4, validate=validate, max_output_tokens=2500)
        out = [(h.text, h.accent, h.big) for h in res.lines]
        _CACHE[ck] = [list(x) for x in out]
        CACHE_PATH.parent.mkdir(exist_ok=True)
        CACHE_PATH.write_text(json.dumps(_CACHE), encoding="utf-8")
        return out
    except (GeminiUnavailable, RuntimeError, ValueError):
        LLM_FALLBACKS += 1
        return [None] * len(chunks)


JUNK = {"wild", "right", "wow", "really", "thing", "things", "stuff", "here", "there", "actually", "simply", "literally", "because"}


def good_accent(a: Optional[str]) -> Optional[str]:
    """An accent must carry a real word: 'The thing', 'Wild' or 'Because' are dropped (the scene then shows the headline alone)."""
    words = [w for w in re.findall(r"[A-Za-z0-9'\u2260-]+", a or "") if len(w) > 2 and clean(w) not in STOP_TAIL and clean(w) not in FILLERS and clean(w) not in JUNK]
    return a if words else None


def derived_scene(chunk: str, prev_type: str, hl: Optional[Tuple[str, str, str]] = None) -> dict:
    h, a = headline(chunk)
    if hl:
        h, a = hl[0], good_accent(hl[1] or None)
    if prev_type == "textWithAccent":
        big = hl[2] if hl else key_phrase(chunk)
        return {"type": "bigText", "text": big, "narration": chunk, "durationInFrames": 90}
    return {"type": "textWithAccent", "text": h, "accentText": a, "narration": chunk, "durationInFrames": 90}


def convert_simple(row: dict, fmt: str) -> dict:
    script = row["full_script"]
    chunks, spans = chunk_spans(script)
    legacy = row["scenes"]
    where = anchor_chunks(script, [s["word_anchor"] for s in legacy], spans)
    by_chunk: Dict[int, dict] = {}
    for sc, k in zip(legacy, where):
        if k is None:
            continue
        cur = by_chunk.get(k)
        if cur is None or ((cur.get("vector_type") or "none") == "none" and (sc.get("vector_type") or "none") != "none") or (sc.get("flash") and not cur.get("flash")):
            by_chunk[k] = sc
    scenes: List[dict] = []
    poses: List[Optional[str]] = []
    data_kinds = ("counter", "bars", "trio")  # these carry real data from the legacy script: kept as they were (counter, list)
    need = [k for k in range(len(chunks)) if by_chunk.get(k) is None or (by_chunk[k].get("vector_type") or "none") not in data_kinds]
    hls = dict(zip(need, llm_headlines([chunks[k] for k in need], row.get("title", ""))))
    for k, ch in enumerate(chunks):
        sc = by_chunk.get(k)
        if sc is not None and k not in hls:
            scenes.append(story_scene_to_motion(sc, ch))
            poses.append(sc.get("pose"))
            continue
        d = derived_scene(ch, scenes[-1]["type"] if scenes else "", hls.get(k))
        if sc is not None:  # the legacy scene's pose, icons and flash survive; only the headline is the new one
            ic = icons_of(sc.get("icon"), sc.get("icon2"), sc.get("icon3"))
            if ic:
                d["icons"] = ic
            if sc.get("flash") and hls.get(k):
                d = {"type": "flash", "text": trim_words(hls[k][2].upper(), 4), "narration": ch, "durationInFrames": 90}
        scenes.append(d)
        poses.append(sc.get("pose") if sc is not None else None)
    return finalize(row, scenes, poses, fmt)


def convert_game(row: dict) -> dict:
    script = row["full_script"]
    chunks, spans = chunk_spans(script)
    trig = row["visual_triggers"]
    where = anchor_chunks(script, [t["word_anchor"] for t in trig], spans)
    by_chunk: Dict[int, dict] = {}
    for t, k in zip(trig, where):
        if k is not None and (k not in by_chunk or (t.get("asset_id") == "stat_card" and by_chunk[k].get("asset_id") != "stat_card")):
            by_chunk[k] = t
    scenes: List[dict] = []
    need = [k for k in range(len(chunks)) if by_chunk.get(k) is None or not by_chunk[k].get("annotation")]
    hls = dict(zip(need, llm_headlines([chunks[k] for k in need], row.get('title', ''))))
    for k, ch in enumerate(chunks):
        t = by_chunk.get(k)
        if t is None:
            scenes.append(derived_scene(ch, scenes[-1]["type"] if scenes else "", hls.get(k)))
            continue
        h, a = headline(ch)
        if hls.get(k):
            h, a = hls[k][0], good_accent(hls[k][1] or None)
        d = {"type": "textWithAccent", "text": h, "accentText": a, "narration": ch, "durationInFrames": 90}
        label, ann = (t.get("label") or "").strip(), (t.get("annotation") or "").strip()
        num = re.match(r"^\s*([\d.,]+)\s*(.*)$", label)
        val = float(num.group(1).replace(",", "") or 0) if num and re.search(r"\d", num.group(1)) else 0.0
        if t.get("asset_id") == "stat_card" and val > 0 and spoken(val, ch):
            d.update(type="counter", text=trim_words((ann or h).title(), 6), accentText=None, value=val, unit=trim_words(num.group(2), 2))
        elif ann:
            ws = _tidy(ann.title().split()[:6]) or [h]
            d.update(text=" ".join(ws[:-1]) if len(ws) >= 3 else " ".join(ws), accentText=(ws[-1] if len(ws) >= 3 else (trim_words(t.get("game_title") or "", 2) or None)))
        if t.get("asset_id") == "game_frame":  # shown over a screenshot of the game (assigned when the video is rendered): the callout is what the screenshot illustrates
            callout = trim_words(" ".join(_tidy((ann or label or h).upper().split())), 6)
            d = {"type": "footage", "text": callout or "IN THE GAME", "narration": ch, "durationInFrames": 90}
        scenes.append(d)
    # a game video should be seen: with fewer than 6 screenshot scenes, every other plain headline (never the hook or the closing line) is shown over a screenshot too
    foot = sum(1 for x in scenes if x["type"] == "footage")
    for i in range(2, len(scenes) - 1, 2):
        if foot >= 7:
            break
        x = scenes[i]
        if x["type"] in ("textWithAccent", "bigText") and scenes[i - 1]["type"] != "footage" and foot < 6 or (x["type"] in ("textWithAccent", "bigText") and foot < 6):
            callout = trim_words(" ".join(_tidy(((x.get("text") or "") + " " + (x.get("accentText") or "")).upper().split())), 6)
            if callout:
                scenes[i] = {"type": "footage", "text": callout, "narration": x["narration"], "durationInFrames": 90}
                foot += 1
    return finalize(row, scenes, [None] * len(scenes), "game")


def finalize(row: dict, scenes: List[dict], poses: List[Optional[str]], fmt: str) -> dict:
    # the closing line becomes the outro scene
    last = scenes[-1]
    outro_narr = last["narration"]
    scenes = scenes[:-1]
    poses = poses[: len(scenes)]
    scenes.append(make_outro(outro_narr))
    n = len(scenes)
    if fmt == "game":
        poses = [None] * n
    elif fmt == "hardware":
        poses = hardware_poses(n, poses + [None] * (n - len(poses)))
    else:
        poses = (poses + [None] * n)[: n - 1] + ["cheer"]
        for i in range(n):  # the legacy poses already cover most scenes; idle ones keep the cursor waiting too
            if poses[i] is None and i % 2 == 0:
                poses[i] = "idle"
    scenes = finish(scenes, poses)
    title = row["title"].strip()
    if "#siliconverdict" not in title.lower() and len(title) <= 82:
        title += " #siliconverdict"
    banner = re.sub(r"\s+", " ", row.get("header_banner") or row["topic"]).strip()
    screen = banner.title()
    if len(screen) > 24:
        screen = " ".join(screen[:24].split()[:-1]) or screen[:24]
    tags = [t.lstrip("#") for t in row.get("tags", [])][:8]
    while len(tags) < 6:
        tags.append(["siliconverdict", "tech facts", "explained", "tech", "shorts", "curiosity"][len(tags) % 6])
    out = {
        "topic": row["topic"], "screen_title": screen, "title": title[:100], "description": row["description"], "tags": tags, "pinned_comment": row["pinned_comment"],
        "accent": "#00F0FF", "scenes": scenes, "kind": "curiosity", "format": fmt, "fact_checked": False,
    }
    if fmt == "game":  # a game video of the plain format, told over that game's screenshots
        from collections import Counter
        names = Counter((t.get("game_title") or "").strip() for t in row.get("visual_triggers", []) if t.get("game_title"))
        out.update(kind="game", format=None, game=names.most_common(1)[0][0] if names else None)
    return out


def to_project(d: dict) -> MotionProject:
    scenes = []
    for s in d["scenes"]:
        s = {k: v for k, v in s.items() if v is not None}
        scenes.append(MotionSceneModel(**s))
    return MotionProject(**{**d, "scenes": scenes})


def classify(row: dict, series: str) -> str:
    if series == "game":
        return "game"
    return "hardware" if "hardware" in (row.get("category_name") or "").lower() else "simple"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--no-llm", action="store_true", help="Write the on-screen headlines with the local heuristic only")
    args = ap.parse_args()
    global USE_LLM
    USE_LLM = not args.no_llm
    with get_db_connection() as conn:  # the original rows are copied once, so a re-run (better converter, new headlines) always starts from the legacy scripts
        conn.execute("CREATE TABLE IF NOT EXISTS story_bank_legacy (id INTEGER PRIMARY KEY, series TEXT NOT NULL, payload TEXT NOT NULL)")
        conn.execute("INSERT OR IGNORE INTO story_bank_legacy (id, series, payload) SELECT id, series, payload FROM story_bank WHERE series IN ('simple', 'game')")
        rows = conn.execute("SELECT l.id, l.series, l.payload FROM story_bank_legacy l JOIN story_bank b ON b.id = l.id ORDER BY l.id").fetchall()
    ok = bad = 0
    for r in rows:
        data = json.loads(r["payload"])
        fmt = classify(data, r["series"])
        try:
            d = convert_game(data) if r["series"] == "game" else convert_simple(data, fmt)
            proj = to_project(d)
            check = proj.model_copy(deep=True)
            prev_type = ""
            for sc_ in check.scenes:  # a banked game script gets its screenshots at render time: validate it with the footage scenes told as headlines (alternating, as footage may repeat)
                if sc_.type == "footage":
                    sc_.type = "bigText" if prev_type == "textWithAccent" else "textWithAccent"
                    sc_.text = trim_words(sc_.text, 4)
                prev_type = sc_.type
            problems = make_validator(None, None, None if fmt == "game" else fmt)(check)
            if fmt == "game" and (not proj.game or proj.game.strip().lower() not in LEGACY_DIRS):
                problems.append(f"unknown game {proj.game!r}")
        except Exception as exc:  # noqa: BLE001
            problems, proj = [f"conversion error: {str(exc)[:200]}"], None
        if problems:
            bad += 1
            print(f"[{r['series']} #{r['id']}] {data['topic']}: " + " | ".join(problems[:4]))
            continue
        ok += 1
        if args.verbose:
            print(f"[{r['series']} #{r['id']}] ok {fmt}: {data['topic']} (~{estimated_seconds(proj):.0f} s, {len(proj.scenes)} scenes)")
        if not args.dry_run:
            with get_db_connection() as conn:
                conn.execute("UPDATE story_bank SET series = 'motion', payload = ?, model = ? WHERE id = ?", (proj.model_dump_json(), "migrated", r["id"]))
    print(f"headline writer fell back to the heuristic for {LLM_FALLBACKS} script(s)")
    print(f"converted {ok}, left as they were {bad}{' (dry run: nothing written)' if args.dry_run else ''}")


if __name__ == "__main__":
    main()
