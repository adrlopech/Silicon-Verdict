"""Series 6 - Motion Graphics: kinetic-typography explainers, over 60 s and at most 3 minutes (YouTube monetisation needs MORE than 60 s), vertical 1080x1920, always English.

Two kinds share one engine:
- "curiosity": a tech / hardware / coding idea told with animated words, counters, code and bars;
- "game": an engineering fact about a game, told with the same motion graphics plus REAL footage of that game (Steam screenshots and trailer clips).
  The script is written against the captions of the footage that is available, so every footage scene shows what the narrator mentions.

A model writes the scene list as structured JSON; this module validates and repairs it (language, lengths, scene rules, footage ids, duration), has a
second pass fact-check it (and check footage vs narration), and hands the result to the MotionGraphic Remotion composition.
"""
import difflib
import logging
import re
import time
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from services.game_facts import figures_in
from services.gemini_client import GeminiUnavailable, generate_structured

STRONG_REVIEWERS = ["@cf/openai/gpt-oss-120b"]  # game claims are checked only by the strongest reviewer; if it is unavailable the video is held, not published

logger = logging.getLogger(__name__)

FPS = 30
from config.settings import settings as _settings
MIN_SECONDS, MAX_SECONDS = 62.0, _settings.MAX_VIDEO_SECONDS   # final video: > 60 s for monetisation, never more than the 3-minute ceiling (the script itself aims for 65-80 s)
MIN_FRAMES, MAX_FRAMES = int(MIN_SECONDS * FPS), int(MAX_SECONDS * FPS)
WORDS_PER_SECOND = 2.5                  # natural narration pace used to estimate the final length
CURSOR_ACTIONS = ("click", "select", "drag", "toggle")  # the pointer only does things that mean something: no browser tab to introduce the topic, no hovering, no loading ring, no waiting
TOGGLE_KEYS = ("airplane", "wifi", "bluetooth", "airdrop")
FX_NAMES = ("plane", "rocket", "satellite", "waves", "bolts", "embers", "snow", "drops", "packets", "coins", "equalizer", "signalbars", "notifications", "batteryfill", "clock", "padlock", "magnify", "bits")


# The 20 drawn interfaces of the `ui` scene. n = how many rows (items, or code lines for the terminal), value = what `value` means, need = the other fields that must be set, action = what the pointer does.
UI_PRESETS: Dict[str, dict] = {
    "display": {"action": "click", "n": (2, 5), "value": "index", "need": (), "doc": 'items = the refresh-rate options ("60 Hz", "120 Hz", "144 Hz"), value = the option the pointer picks (1-based)'},
    "taskmgr": {"action": "click", "n": (3, 5), "value": "index", "need": (), "doc": 'items = processes "Name|percent of CPU", value = the process the pointer ends (1-based)'},
    "bios": {"action": "click", "n": (3, 6), "value": "index", "need": ("accentText",), "doc": 'items = options "Option|Value", value = the option changed, accentText = its new value'},
    "terminal": {"action": "select", "n": (3, 8), "value": "index", "need": ("code",), "doc": 'code = the lines (a "$ " line is a command, the others are its output), value = the line the pointer selects (1-based)'},
    "gpupanel": {"action": "click", "n": (2, 4), "value": "index", "need": (), "doc": 'items = switches "Name|on" or "Name|off", value = the switch the pointer flips; the frame-time graph then calms down'},
    "gamemenu": {"action": "drag", "n": (2, 4), "value": "index", "need": ("leftValue", "rightValue"), "doc": 'items = sliders "Name|from>to" (0-100), value = the slider the pointer drags, leftValue / rightValue = the FPS before / after'},
    "frametime": {"action": "select", "n": (0, 0), "value": "number", "need": ("leftValue",), "doc": "no items; value = the height of the stutter spike in ms, leftValue = the usual frame time in ms; the pointer selects the spike"},
    "speedtest": {"action": "drag", "n": (0, 3), "value": "number", "need": ("unit",), "doc": 'value = the result, unit = Mbps or ms, items (optional) = other readings "Ping|12 ms"; the pointer drags the needle up to the result'},
    "wifilist": {"action": "click", "n": (2, 4), "value": "index", "need": (), "doc": 'items = networks "Name|band|bars" (bars 1-4), value = the network the pointer presses'},
    "router": {"action": "click", "n": (2, 4), "value": "index", "need": ("accentText",), "doc": 'items = settings "Field|current value", value = the field edited, accentText = its new value'},
    "keycaps": {"action": "click", "n": (2, 4), "value": None, "need": ("accentText",), "doc": 'items = the keys of a shortcut in order ("Win", "Shift", "S"), accentText = what it does'},
    "filemgr": {"action": "drag", "n": (3, 5), "value": "folder", "need": (), "doc": 'items = the file first, then 2-4 folders "Name|note"; value = the folder (1-based among the folders) the file is dropped on'},
    "diskbar": {"action": "drag", "n": (3, 5), "value": "number", "need": ("leftValue", "rightValue"), "doc": 'items = segments "Name|percent" adding up to 100, the LAST one is the free space; value = the free percent afterwards, leftValue / rightValue = write speed before / after in MB/s'},
    "battery": {"action": "drag", "n": (1, 1), "value": "number", "need": (), "doc": 'items = ["Charge limit|100>80"] (the slider the pointer drags), value = the battery health in percent'},
    "tabmem": {"action": "click", "n": (3, 5), "value": "index", "need": (), "doc": 'items = browser tabs "Name|MB", value = the heavy tab the pointer closes'},
    "speclabel": {"action": "select", "n": (3, 5), "value": "index", "need": (), "doc": 'text = the label, items = its parts "token|what it means" in order, value = the part the pointer selects'},
    "leaderboard": {"action": "drag", "n": (3, 6), "value": "index", "need": (), "doc": 'items = rows "Name|score" in their TRUE order (best first), value = the row that starts misplaced at the bottom and that the pointer drags up to its place'},
    "partpicker": {"action": "drag", "n": (2, 4), "value": "index", "need": ("accentText", "leftValue"), "doc": 'items = slots "Slot|Part" with one "Slot|empty", value = the empty slot, accentText = the part dropped there, leftValue = 1 if it fits or 0 if not, unit = why it does not fit'},
    "dimm": {"action": "click", "n": (4, 4), "value": None, "need": ("leftValue", "rightValue"), "doc": 'items = the four slot names ("A1", "A2", "B1", "B2"), leftValue / rightValue = the two slots (1-4) the sticks go into, accentText (optional) = the badge that lights up'},
    "permissions": {"action": "click", "n": (2, 4), "value": "index", "need": (), "doc": 'items = switches "Name|on" (Microphone, Camera, Location), value = the one the pointer turns off'},
}
UI_FORMATS_OFF = ("tier", "versus", "myth", "evolution", "top5", "quiz", "news", "review", "priced")  # these formats are built from a fixed run of their own scenes
MAX_UI_SCENES = 2


def _ui_problems(p: "MotionProject", fmt: Optional[str]) -> List[str]:
    out: List[str] = []
    uis = [(i, s) for i, s in enumerate(p.scenes, 1) if s.type == "ui"]
    for s in p.scenes:
        if s.type != "ui":
            s.preset = None
    if not uis:
        return out
    if fmt in UI_FORMATS_OFF:
        out.append(f"{fmt} videos are built from their own scenes: no ui scenes")
    if len(uis) > MAX_UI_SCENES:
        out.append(f"at most {MAX_UI_SCENES} ui scenes per video")
    if any(b[0] - a[0] < 2 for a, b in zip(uis, uis[1:])):
        out.append("two ui scenes must have at least one other scene between them")
    for i, s in uis:
        spec = UI_PRESETS.get((s.preset or "").strip().lower())
        if not spec:
            out.append(f"scene {i}: a ui scene needs `preset`, one of {', '.join(UI_PRESETS)}")
            continue
        s.preset = (s.preset or "").strip().lower()
        name = s.preset
        rows_ = [it.split("|") for it in (s.items or [])]
        n = len(s.code or []) if name == "terminal" else len(s.items or [])
        lo, hi = spec["n"]
        if not lo <= n <= hi:
            out.append(f"scene {i}: the {name} preset needs {lo}-{hi} {'code lines' if name == 'terminal' else 'items'}, got {n}")
        v = s.value
        top = n - 1 if spec["value"] == "folder" else n
        if spec["value"] in ("index", "folder") and (v is None or not 1 <= round(v) <= max(1, top)):
            out.append(f"scene {i}: {name} needs `value` = a 1-based position between 1 and {max(1, top)}")
        if spec["value"] == "number" and (v is None or v <= 0):
            out.append(f"scene {i}: {name} needs a positive `value`")
        for field in spec["need"]:
            got = getattr(s, field)
            if got is None or (isinstance(got, (str, list)) and not got):
                out.append(f"scene {i}: {name} needs `{field}`")
        if name == "taskmgr" and any(len(r) < 2 or not re.search(r"\d", r[1]) for r in rows_):
            out.append(f"scene {i}: taskmgr items look like \"Browser|62\"")
        if name in ("bios", "router", "tabmem", "leaderboard", "speclabel", "filemgr") and name != "filemgr" and any(len(r) < 2 or not r[1].strip() for r in rows_):
            out.append(f"scene {i}: {name} items look like \"Name|value\"")
        if name in ("tabmem", "leaderboard") and any(len(r) < 2 or not re.search(r"\d", r[1]) for r in rows_):
            out.append(f"scene {i}: {name} items need a number after the bar")
        if name == "gamemenu" and any(len(r) < 2 or not re.fullmatch(r"\s*\d+\s*>\s*\d+\s*", r[1]) for r in rows_):
            out.append(f"scene {i}: gamemenu items look like \"Shadows|90>40\"")
        if name == "battery" and not (rows_ and len(rows_[0]) > 1 and re.fullmatch(r"\s*\d+\s*>\s*\d+\s*", rows_[0][1])):
            out.append(f"scene {i}: battery's item looks like \"Charge limit|100>80\"")
        if name == "wifilist" and any(len(r) < 3 or not re.fullmatch(r"\s*[1-4]\s*", r[2]) for r in rows_):
            out.append(f"scene {i}: wifilist items look like \"Home|5 GHz|4\" (bars 1-4)")
        if name == "diskbar" and (len(rows_) < 3 or any(len(r) < 2 or not re.search(r"\d", r[1]) for r in rows_) or abs(sum(float(re.search(r"[\d.]+", r[1]).group()) for r in rows_ if len(r) > 1 and re.search(r"\d", r[1])) - 100) > 1.5):
            out.append(f"scene {i}: diskbar segments \"Name|percent\" must add up to 100")
        if name == "diskbar" and v is not None and rows_ and len(rows_[-1]) > 1 and re.search(r"\d", rows_[-1][1]) and v <= float(re.search(r"[\d.]+", rows_[-1][1]).group()):
            out.append(f"scene {i}: diskbar's `value` (free percent afterwards) must be bigger than the free percent shown")
        if name == "partpicker":
            empties = [k for k, r in enumerate(rows_, 1) if len(r) > 1 and r[1].strip().lower() == "empty"]
            if len(empties) != 1 or (v is not None and round(v) != empties[0]):
                out.append(f"scene {i}: partpicker needs exactly one \"Slot|empty\" row and `value` = its position")
            if s.leftValue is not None and s.leftValue <= 0 and not (s.unit or "").strip():
                out.append(f"scene {i}: partpicker with leftValue 0 needs `unit` = why the part does not fit")
        if name == "dimm":
            a, b = s.leftValue, s.rightValue
            if a is None or b is None or not (1 <= round(a) <= 4 and 1 <= round(b) <= 4) or round(a) == round(b):
                out.append(f"scene {i}: dimm needs two different slots (1-4) in leftValue and rightValue")
        if name == "speclabel" and not s.text.strip():
            out.append(f"scene {i}: speclabel needs `text` = the label")
        if name in ("speedtest", "frametime") and s.value is not None and s.value > 0 and not _spoken(s):
            out.append(f"scene {i}: the number {s.value:g} must be mentioned in that scene's narration")
    return out


# Where each action makes sense (the pointer never decorates): select highlights the key phrase of a headline, drag pulls a progress bar or carries the new tier chip into its row,
# click presses a step or a setting (code and list scenes), toggle flips a Control Center switch (only as the video starts).
CURSOR_SCENES = {"select": ("bigText", "textWithAccent", "card", "ui"), "drag": ("progressBar", "tier", "ui"), "click": ("codeBlock", "list", "ui"), "toggle": ("bigText", "textWithAccent")}
CURSOR_GAP = 2  # at least two scenes between two pointer scenes


def _cursor_priority(fmt: Optional[str]) -> dict:
    order = ("toggle", "click", "drag", "select") if fmt == "fix" else ("toggle", "select", "drag", "click") if fmt == "decode" else ("toggle", "drag", "select", "click")
    return {a: n for n, a in enumerate(order)}


def limit_cursor(scenes, fmt: Optional[str]) -> None:
    """Keeps the most useful pointer moments up to a small budget (4 in the fix-it format, 3 elsewhere), never closer than CURSOR_GAP scenes: things it moves first, then the phrase it selects."""
    budget = 4 if fmt == "fix" else 3
    prio = _cursor_priority(fmt)
    candidates = sorted((i for i, sc in enumerate(scenes) if sc.cursor), key=lambda i: (0 if scenes[i].type == "ui" else 1, prio.get(scenes[i].cursor, 9), i))  # a drawn interface exists to be used: its pointer moment comes first
    keep: list = []
    for i in candidates:
        if len(keep) < budget and all(abs(i - j) >= CURSOR_GAP for j in keep):
            keep.append(i)
    for i, sc in enumerate(scenes):
        if i not in keep:
            sc.cursor, sc.toggle = None, None


_QUESTION_START = re.compile(r"^(would|do|does|did|will|which|is|are|can|could|should|have|has|what|how|why|who)\b", re.I)


def vote_options(pinned: str) -> Optional[List[str]]:
    """The two short options of a pinned-comment vote ("5060 Ti or 5080? Reply with one word." -> ["5060 Ti", "5080"]; "Reply SURPRISED or KNEW IT." -> ["Surprised", "Knew it"]),
    or None when the question does not name two short things (the outro then simply has no A / B cards)."""
    text = (pinned or "").strip()
    m = re.search(r"\breply\s+(.{1,24}?)\s+or\s+(.{1,24}?)\s*[.!?]*$", text, re.I)
    if not m and not _QUESTION_START.match(text):
        m = re.match(r"^(.{2,28}?),?\s+or\s+(.{2,28}?)\s*\?", text, re.I)
    if not m:
        return None
    out = []
    for raw in m.groups():
        t = re.sub(r"^(the|a|an)\s+", "", raw.strip(" ,.?!"), flags=re.I)
        if not t or len(t.split()) > 3:
            return None
        if re.search(r"\d", t) and re.search(r"[A-Za-z]", t) and " " not in t:
            t = t.upper()  # a model name: "9800x3d" -> "9800X3D", "ddr4" -> "DDR4"
        elif t.isupper() and len(t) > 5 and not re.search(r"\d", t):
            t = t.capitalize()  # a shouted word ("SURPRISED", "KNEW IT"), never a model name with digits ("USB 3.2" stays as it is)
        out.append(t[0].upper() + t[1:])
    return out


VOTE_TITLE, VOTE_ACCENT = "YOUR PICK?", "Vote below"
_FOLLOW = re.compile(r"[^.!?]*\bfollow\b[^.!?]*[.!]\s*", re.I)


def add_vote_items(project: Any) -> None:
    """Gives the outro its two vote options (drawn as A / B cards) from the pinned comment, which repeats the same choice the narration ends with. Existing items are kept.
    With a vote on screen the outro is about the vote: its headline asks for the pick (not "STAY CURIOUS / Follow for more" over the cards) and its narration drops the
    "Follow for more" sentence, so the last thing said is the question."""
    outro = project.scenes[-1] if project.scenes else None
    if outro is None or outro.type != "outro":
        return
    if not outro.items:
        opts = vote_options(getattr(project, "pinned_comment", "") or "")
        if opts:
            outro.items = opts
    if not outro.items or len(outro.items) != 2:
        return
    outro.text, outro.accentText = VOTE_TITLE, VOTE_ACCENT
    rest = _FOLLOW.sub("", outro.narration or "").strip()
    if rest.endswith("?") and len(rest.split()) >= 3:
        outro.narration = rest


def mark_tier_teasers(scenes) -> None:
    """Open loop on screen: while the final board has an S item that is not placed yet, every tier scene shows a covered "?" chip in the S row (it is revealed in its own scene)."""
    tiers = [s for s in scenes if s.type == "tier"]
    if not tiers or not any((it.split("|", 1)[0].strip().upper() == "S") for it in (tiers[-1].items or [])):
        return
    for s in tiers:
        s.tease = not any(it.split("|", 1)[0].strip().upper() == "S" for it in (s.items or [])) or None


def fix_duplicate_accents(scenes) -> None:
    """The headline and its accent phrase are drawn one under the other, so an accent that repeats the first or last words of the headline reads as a stutter
    ("Check before you believe" + "believe"): the repeated words are taken out of the headline (the accent keeps them)."""
    for s in scenes:
        acc = (s.accentText or "").strip()
        if len(acc) < 3 or s.type not in ("bigText", "textWithAccent", "tier", "headline"):
            continue
        words, a_words = s.text.split(), acc.split()
        k = len(a_words)
        norm = lambda ws: [re.sub(r"[^a-z0-9]", "", w.lower()) for w in ws]  # noqa: E731
        if len(words) > k and norm(words[-k:]) == norm(a_words):
            s.text = " ".join(words[:-k]).rstrip(" ,;:-")
        elif len(words) > k and norm(words[:k]) == norm(a_words):
            s.text = " ".join(words[k:]).lstrip(" ,;:-")


def sanitize_cursors(scenes, fmt: Optional[str]) -> None:
    """Drops every pointer action that would mean nothing (an older script's tab, hover, busy or idle; a click on a headline; a drag on a list) and enforces the budget and spacing."""
    for i, sc in enumerate(scenes):
        act = (sc.cursor or "").strip().lower()
        if sc.type == "ui":
            spec = UI_PRESETS.get((sc.preset or "").strip().lower())
            sc.cursor, sc.toggle = (spec["action"] if spec else None), None  # the drawn interface decides what the pointer does in it
            continue
        if act == "click" and sc.type in CURSOR_SCENES["select"]:
            act = "select"  # pressing a headline means nothing; highlighting its key phrase does
        if act not in CURSOR_ACTIONS or sc.type not in CURSOR_SCENES[act] or (act == "toggle" and i != 0):
            act = ""
        sc.cursor = act or None
        tg = (sc.toggle or "").strip().lower()
        sc.toggle = (tg if tg in TOGGLE_KEYS else "airplane") if act == "toggle" else None
    limit_cursor(scenes, fmt)


def assign_cursors(scenes, fmt: Optional[str]) -> None:
    """For hand-written scripts that predate the rules: after sanitize_cursors, adds the pointer moments the format needs (decode: a select on the label, fix: clicks on the setting and the steps,
    tier: the chips it carries, any progress bar: the knob it pulls) and, when still short, selects the key phrase of one headline pair."""
    def free(i: int) -> bool:
        return all(abs(i - j) >= CURSOR_GAP for j, sc in enumerate(scenes) if sc.cursor and j != i)

    def put(i: int, act: str) -> None:
        if not scenes[i].cursor and scenes[i].type in CURSOR_SCENES[act] and free(i):
            scenes[i].cursor = act
    if fmt == "decode" and scenes:
        scenes[0].cursor = "select"
    for i, sc in enumerate(scenes):
        if sc.type == "progressBar":
            put(i, "drag")
        elif sc.type == "tier" and fmt == "tier" and i % 2 == 1:
            put(i, "drag")
        elif sc.type in ("codeBlock", "list") and fmt in ("fix", "decode") and sum(1 for x in scenes if x.cursor == "click") < (2 if fmt == "fix" else 1):
            put(i, "click")
    if sum(1 for sc in scenes if sc.cursor) < 2 and fmt not in ("tier",):
        for i, sc in enumerate(scenes):
            if i > 0 and sc.type == "textWithAccent" and sc.accentText:
                put(i, "select")
                if sum(1 for x in scenes if x.cursor) >= 2:
                    break
    limit_cursor(scenes, fmt)


SceneType = Literal["bigText", "textWithAccent", "counter", "list", "codeBlock", "progressBar", "outro", "curve", "flash", "footage", "tier", "versus", "verdict", "timeline", "ui", "card", "rank", "quiz", "headline", "split", "units"]
FORMATS = ("myth", "tier", "whatif", "easter", "evolution", "versus", "hardware", "simple", "fix", "decode", "top5", "eli5", "fails", "numbers", "quiz", "stop", "rumor", "review", "news", "priced")   # content formats on top of the two kinds (curiosity / game); "easter" is always a game video; "hardware" and "simple" are the old Hardware / Everyday-with-mascot categories, now told in the Motion style; "fix" and "decode" come from the Nov 2026 niche research (notes/niche_research_2026-11.md)
TIER_LETTERS = ("S", "A", "B", "C", "D", "F")
SPLIT_DEMOS = ("bars", "res", "speed", "size", "ago")
# How often `--motion-format any` picks each topic. Our three TikTok breakouts (800+ views) were the number-driven formats (what-if, versus, evolution) and the niche research
# found "fix it now" and "decoded" to be the biggest unserved clusters; tier lists and myths stalled at the first test wave (notes/content_style_study_2026-11.md).
FORMAT_WEIGHTS = {"whatif": 3, "versus": 3, "evolution": 3, "fix": 3, "decode": 3, "hardware": 2, "simple": 1, "myth": 1, "tier": 1, "top5": 2, "eli5": 2, "fails": 2, "numbers": 2, "quiz": 2, "stop": 2, "rumor": 2, "review": 1, "priced": 2, "easter": 1, "classic": 1, "curiosity": 1, "game": 1}


class MotionSceneModel(BaseModel):
    type: SceneType
    text: str = Field(..., description="Main line, at most 7 words (bigText: at most 4). For 'footage': a 2-6 word callout naming the technical detail")
    accentText: Optional[str] = Field(default=None, description="ONE accent word or short phrase (max 3 words) shown in colour, italic serif")
    kicker: Optional[str] = Field(default=None, description="Optional tiny label above the text, 1-3 words")
    value: Optional[float] = Field(default=None, description="counter: final number (> 0); progressBar: percentage 0-100; rank: its position (5, 4, 3, 2, 1); quiz: the correct option (1, 2 or 3)")
    unit: Optional[str] = Field(default=None, description="counter/progressBar suffix such as %, ms, GB")
    items: Optional[List[str]] = Field(default=None, description="quiz: exactly 3 answer options of at most 4 words. list: 2-4 items of at most 5 words. tier: the board so far as \"S|label\" entries (tier letter S A B C D F, label at most 22 characters). timeline: 3-5 chronological \"year|label\" entries (label at most 28 characters)")
    left: Optional[str] = Field(default=None, description="versus: name of the left contender, at most 16 characters (the same in every versus scene)")
    right: Optional[str] = Field(default=None, description="versus: name of the right contender, at most 16 characters (the same in every versus scene)")
    leftValue: Optional[float] = Field(default=None, description="versus: the left contender's real, approximate figure for this scene's metric (> 0); `unit` is shared by both")
    rightValue: Optional[float] = Field(default=None, description="versus: the right contender's real, approximate figure for the same metric (> 0)")
    winner: Optional[Literal["left", "right", "none"]] = Field(default=None, description="versus: who wins this round; leave empty when the BIGGER figure wins, set it when lower is better")
    verdict: Optional[Literal["myth", "fact", "partly", "buy", "wait", "skip"]] = Field(default=None, description="verdict scenes only: is the claim a myth, a fact or partly true (myth format); buy, wait or skip (review format)")
    code: Optional[List[str]] = Field(default=None, description="codeBlock: 2-8 short real code or shell lines (max 38 characters each)")
    light: bool = Field(default=False, description="Light background variant, use for at most one scene")
    mediaId: Optional[str] = Field(default=None, description="footage scenes only: the id of ONE item of the footage list; never reuse an id")
    mediaSrc: Optional[str] = Field(default=None, description="Set by the pipeline, never by the model")
    mediaKind: Optional[str] = Field(default=None, description="Set by the pipeline, never by the model")
    mediaSeconds: Optional[float] = Field(default=None, description="Set by the pipeline, never by the model")
    credit: Optional[str] = Field(default=None, description="Set by the pipeline, never by the model")
    evidence: Optional[str] = Field(default=None, description="GAME videos only: a VERBATIM quote (6-30 words) copied from the SOURCE TEXT that supports this scene's claim about the game; empty if the scene makes no claim about the game")
    visual: Optional[str] = Field(default=None, description="Text scenes: the animated stage drawn behind the text (crowd, memory, cores, network, bars, wave, gauge, map, city, layers, matrix, radar, orbit). Optional: it is picked automatically from the scene's words when empty")
    fx: Optional[str] = Field(default=None, description="An animated element that illustrates the line (plane, rocket, satellite, waves, bolts, embers, snow, drops, packets, coins, equalizer). Optional: it is picked automatically from the scene's words when empty")
    toggle: Optional[str] = Field(default=None, description="With cursor=toggle: the switch of the Control Center panel the cursor flips: airplane, wifi, bluetooth or airdrop")
    cursor: Optional[str] = Field(default=None, description="The pointer acts in this scene ONLY when the action means something: select (drags across the key phrase of a bigText / textWithAccent scene), drag (progressBar: pulls the bar to its value; tier: carries the new chip into its row), click (codeBlock or list: presses the setting or the step), toggle (first scene only, only for a video about a phone/computer setting: opens a Control Center panel and flips a switch). Empty = no pointer in this scene")
    demo: Optional[str] = Field(default=None, description="split scenes only: what each panel draws: bars (a big figure and a proportional bar), res (the same shape drawn with few and with many pixels), speed (two runners racing at the two speeds), size (two squares whose AREAS follow the figures) or ago (a counter of how long ago, for then-versus-now). The figures are leftValue and rightValue, `unit` is shared, left and right are the labels")
    preset: Optional[str] = Field(default=None, description="ui scenes only: the drawn interface (display, taskmgr, bios, terminal, gpupanel, gamemenu, frametime, speedtest, wifilist, router, keycaps, filemgr, diskbar, battery, tabmem, speclabel, leaderboard, partpicker, dimm, permissions); its data goes in items, value, accentText, leftValue, rightValue, unit and code as the UI PRESETS rules say")
    callout: Optional[str] = Field(default=None, description="Set by the pipeline from the narration, never by the model: a short tag (a figure or a key term) that pops up in the middle of a long scene")
    calloutCue: Optional[float] = Field(default=None, description="Set by the pipeline from the voice timing, never by the model: seconds after the scene starts at which the narrator says the callout")
    accentCue: Optional[float] = Field(default=None, description="Set by the pipeline from the voice timing, never by the model: seconds after the scene starts at which the narrator says the accent phrase")
    tease: Optional[bool] = Field(default=None, description="Set by the pipeline, never by the model: a tier scene shown before the S-tier item is placed draws a covered \"?\" chip in the S row")
    cursorCue: Optional[float] = Field(default=None, description="Set by the pipeline from the voice timing, never by the model: seconds after the scene starts at which the narrator says the phrase the pointer acts on")
    icons: Optional[List[str]] = Field(default=None, description="1-3 thematic objects floating around the text, chosen from: chip gpu ram battery bolt wifi globe cloud server disk lock key shield thermometer flame fan gauge clock code brain bulb dollar skull warning controller monitor phone camera wave planet rocket atom magnet droplet snow heart search check cross gear star net arrow. Pick what the scene is ABOUT; leave empty to let the renderer choose from the words")
    narration: str = Field(default="", description="What the narrator SAYS during this scene: one or two natural spoken sentences, 8-16 words, that explain the idea on screen")
    durationInFrames: int = Field(..., description="Minimum scene length in frames at 30 fps (60-150); the pipeline stretches it to fit the narration")


class CaptionWord(BaseModel):
    w: str = Field(..., description="Set by the pipeline: the spoken word")
    s: int = Field(..., description="Set by the pipeline: first frame of the word in the whole video")
    e: int = Field(..., description="Set by the pipeline: last frame")


class MotionProject(BaseModel):
    topic: str
    screen_title: str = Field(..., description="Short title shown in the HUD, at most 24 characters")
    title: str = Field(..., max_length=100, description="YouTube title in English, at most 80 characters, plus 2-3 hashtags")
    description: str = Field(..., description="Two English sentences")
    tags: List[str] = Field(..., description="6-8 English tags")
    pinned_comment: str = Field(..., description="The same two-option vote as the outro, in the form \"A or B? Reply with one word.\" (at most 120 characters)")
    accent: str = Field(default="#00F0FF", description="Accent colour: always the channel electric cyan #00F0FF (or the channel blue #007AFF)")
    scenes: List[MotionSceneModel]
    kind: str = Field(default="curiosity", description="Set by the pipeline: curiosity | game")
    format: Optional[str] = Field(default=None, description="Set by the pipeline: myth | tier | whatif | easter | evolution | versus | hardware | simple | fix | decode (None = the classic explainer)")
    game: Optional[str] = Field(default=None, description="Set by the pipeline for game videos")
    look: Optional[str] = Field(default=None, description="Set by the pipeline: the visual look of the video (services/looks.py)")
    captions: Optional[List[CaptionWord]] = Field(default=None, description="Set by the pipeline from the voice timing: the words of the caption strip")
    fact_checked: bool = Field(default=True, description="Set by the pipeline; False when no model could run the fact-check")
    gemini_input_tokens: int = Field(default=0)
    gemini_output_tokens: int = Field(default=0)

    def to_props(self) -> dict:
        """The JSON the MotionGraphic composition receives as inputProps."""
        return {
            "title": self.screen_title,
            **({"series": self.series_label} if self.series_label else {}),
            "theme": {"accent": self.accent, "background": "#05070C", "text": "#FFFFFF"},
            "scenes": [s.model_dump(exclude_none=True) for s in self.scenes],
            **({"look": self.look} if self.look else {}),
            **({"captions": [c.model_dump() for c in self.captions]} if self.captions else {}),
        }

    @property
    def series_label(self) -> str:
        """The series part of the title ("Fix It Now #4" of "Fix It Now #4: If you..."), shown in the title strip of the HUD."""
        head = self.title.split(":", 1)[0].strip() if ":" in self.title else ""
        return head if 3 <= len(head) <= 24 and "#" not in head.rsplit(" ", 1)[0] else ""

    @property
    def total_frames(self) -> int:
        return sum(s.durationInFrames for s in self.scenes)

    @property
    def narration_words(self) -> int:
        return sum(len(s.narration.split()) for s in self.scenes)

    @property
    def all_text(self) -> str:
        parts = [self.title, self.description, self.pinned_comment, self.screen_title, " ".join(self.tags)]
        for s in self.scenes:
            parts += [s.text, s.accentText or "", s.kicker or "", s.unit or "", " ".join(s.items or []), s.left or "", s.right or "", s.narration]
        return " ".join(p for p in parts if p)


def estimated_seconds(p: MotionProject) -> float:
    """Length after narration: ~2.5 spoken words per second plus a breath per scene, never less than the scenes' own minimum."""
    return max(p.total_frames / FPS, p.narration_words / WORDS_PER_SECOND + 0.7 * len(p.scenes))


SYSTEM_PROMPT = """You write 65-80 second vertical motion-graphics explainers for the channel 'Silicon Verdict' (PC, hardware, games, coding and tech).
They must run MORE than 60 seconds (YouTube monetisation), so be generous with substance: a real story, not a teaser.
The video is kinetic typography on a deep obsidian background with electric-cyan and blue glow (the channel's blue palette), in the style of premium product reels:
one big idea per scene, a single ACCENT word in electric cyan (italic serif), smooth eased motion, counters, bars, code, a punchy outro.
A NARRATOR speaks over the video. Each scene has a `narration` (what is said while that scene is on screen): natural spoken American English, 8-16 words,
conversational and clear, explaining the idea the screen shows (the on-screen words are the headline, the narration is the explanation). Together the narration reads
like one coherent story with a hook at the start, a build-up, a twist, and a closing line, 150-190 words in total (aim for about 11 words per scene). Spell numbers the way they are spoken
(for example "sixteen point seven milliseconds"). The narrations are ONE continuous monologue, not separate captions: each line picks up from the previous one and flows into the next, opening with a connective such as "So", "And", "But", "Here's the thing", "That's why", "Now" or "Which means" (never a stand-alone fact, and never the same opener twice in a row), with questions answered in the following line. The last scene's narration ends with the two-option vote question (see VOTE below), never with "Follow for more".

LANGUAGE: everything (scene text, narration, title, description, tags, comment) MUST be natural American English. Never any other language.
FACTS: only TRUE, verifiable statements; figures must be real and approximate (about / roughly) - never invent numbers.

STORY (11 to 19 scenes, aim for 13+, each 60-150 frames at 30 fps):
1. First scene: a COLD OPEN hook (bigText or textWithAccent), see the RETENTION RULES at the end.
2. Then build the idea step by step, ONE idea per scene, using a variety of scene types:
   - bigText: 1-4 words, huge. textWithAccent: a short white line (max 7 words) + accentText (1-3 words, the emotional/key word). card: the same fields as textWithAccent inside a framed glass card with a quote mark: use it for a key claim or the takeaway, it breaks a run of plain headlines.
   - counter: caption text + accentText, value = a REAL final number > 0, optional unit.
   - list: heading text + 2-4 short items. codeBlock: 2-8 real, short code/shell lines + headline text. progressBar: caption + value 0-100 + unit.
   - curve: caption about acceleration / easing / growth. flash: ONE word on a full accent-coloured screen (a rhythm break; use one or two per video, at least four scenes apart, on the key word of the story).
3. Last scene: type outro, text = a punchy 1-3 word closer, accentText = a short call to action (the pipeline replaces both with the vote when the outro asks one).
Every scene except footage/flash/tier/timeline/versus/verdict floats 1-3 eye-catching `icons` (neon objects) that visually match what that scene is about
(e.g. a scene on heat: thermometer, flame, fan; on speed: gauge, bolt). Always fill `icons` for scenes about a concrete thing.
Rules: never repeat the same scene type back to back (footage scenes may follow each other); at most one scene with light=true; on-screen text is short and
readable in 2 seconds; no emojis.
CURSOR (optional, use it SPARINGLY): the channel's character is a mouse pointer. It appears only when it does something that MEANS something, never as decoration, never to introduce the topic (no browser tab, no hovering, no waiting, no loading ring).
Set `cursor` on a scene only for: select (a bigText or textWithAccent scene: it drags across the key phrase, as if selecting it, while the narrator says it), drag (a progressBar scene: it pulls the bar to its value; a tier scene: it carries the new chip into its row), click (a codeBlock or list scene: it presses the setting or the step the narrator names),
toggle (ONLY the first scene and ONLY when the whole video is about a phone or computer setting such as airplane mode: it opens a macOS-style Control Center panel and flips the switch named in `toggle`: airplane, wifi, bluetooth or airdrop). Never on flash scenes. At most 3 scenes per video (4 in a fix video), never in two scenes in a row.
VISUAL STAGE (optional): every text scene also shows an animated drawing behind the words. It is picked automatically from what the scene says; set `visual` only when you want a specific one: crowd (people, NPCs, teams), memory (RAM, storage, copies), cores (CPU, threads, load), network (online, servers, packets), bars (growth, comparisons), wave (sound, signals), gauge (speed, fps, latency), map (world, regions), city (streets, buildings), layers (rendering, pipelines, stacks), matrix (code, data, AI), radar (weather, scanning, tracking), orbit (a system of parts). Never ask for the same one in consecutive scenes.
Metadata: title <= 80 characters + 2-3 hashtags (#siliconverdict first); the title is a specific question or a duel ("What If a CPU Ran at 100 GHz?", "PS5 vs Xbox Series X"), never a catalogue line ("X Ranked From Worst to Best"), description 2 sentences, 6-8 tags, pinned_comment = the two-option vote of the outro.
screen_title <= 24 characters. accent = always #00F0FF (channel electric cyan)."""

RETENTION_RULES = """
RETENTION RULES (they decide whether people keep watching; the validator checks them):
- COLD OPEN. Scene 1 is the claim that breaks a belief, or the most surprising number, said in at most 14 words with NO context before it. Never open with a greeting, "today", "in this video",
  "did you know", "have you ever wondered", "let's" or a definition. Example: "Your three nanometer chip has no three nanometer part inside." When a figure or a contrast makes the claim stronger, show it in scene 1 or 2.
- OPEN LOOP. In scene 2, 3, 4 or 5 the narration promises something that comes later ("And the last reason is the one nobody checks.", "Stay to the end, the last step matters most.",
  "But the real catch comes in a moment."). Pay it off in the last third, before the outro, with a scene that clearly delivers it. Never promise something the video does not deliver. The validator looks for a phrase like these in the narration of scene 2, 3, 4 or 5, so use one VERBATIM: "Stay to the end, the catch comes last." / "And the last one is the one most people miss." / "But the real twist comes in a moment." / "Wait for the last part, nobody expects it."
- PATTERN BREAK. Never more than two headline scenes (bigText / textWithAccent) in a row: break the rhythm with a card, counter, list, codeBlock, progressBar, curve, flash or footage scene at least every third scene.
- PACE. No scene narration is longer than 16 words (about 6 seconds): when a thought needs more, split it across two scenes so something on screen changes at least every 5 seconds. The video must still last MORE than 60 seconds (monetisation), so keep the whole script at 150-190 words: use more scenes of 8-16 words, never fewer words.
- VOTE. The outro narration ends with a TWO-OPTION question the viewer can answer in one word ("Would you buy it, or skip it?", "Team DDR4 or team DDR5?") and `pinned_comment` repeats the SAME choice
  as "A or B? Reply with one word." (at most 120 characters). Never an open question such as "What do you think?".
  The two options are NAMED in the question and belong to THIS video ("Team 7800X3D or team 9800X3D?"): never the generic "Did that surprise you or did you know it?" nor "Tell me below and follow for more", which every video used to end with.
- HOOK. Scene 1 opens with a number, a concrete claim or a tension ("One of these seven cards is worth its price."), never "Let us", "Let's", "What if" (unless the format is whatif) or "Did you know".
  It states a conflict or a verdict, not the topic: "Six USB generations ranked by speed" is a label; "That new USB-C cable might run at year-2000 speed" is a hook.
- YOU. Speak to the viewer: say what each fact does to THEIR PC, money or time ("your SSD becomes the bottleneck"), not to "users" or "the system".
- ACCENT. `accentText` adds words that are NOT in `text` (the headline and the accent are drawn one under the other): never repeat the headline's last word in the accent."""

def ui_rules() -> str:
    """Prompt block for the `ui` scene: the catalogue of drawn interfaces and how each one takes its data."""
    lines = "\n".join(f"  * {name}: {spec['doc']}" for name, spec in UI_PRESETS.items())
    return f"""
UI SCENES (optional, at most {MAX_UI_SCENES} per video, never two in a row, never in tier / versus / myth / evolution videos): a scene of type `ui` shows a DRAWN INTERFACE that the mouse pointer uses, so the viewer SEES the change instead of hearing about it
(a refresh-rate menu, a task manager, a slider that costs FPS...). Use one when the topic is a setting, a panel, a shortcut or a measurable change; skip it otherwise. Set `preset` to one of the names below and fill the fields it names;
`text` is a short headline (at most 7 words) shown above the interface; the narration says what the pointer does and says every figure shown. The pointer's action is chosen by the preset, leave `cursor` empty.
{lines}
Facts in a ui scene (menu names, values, figures) follow the same rule as everywhere else: only real, generic, well documented things; no vendor logos, no invented figures."""


GAME_RULES = """
GAME VIDEO. This video is about the game {game}: tell ONE true engineering fact about it (engine behaviour, physics, streaming, rendering trick,
netcode, optimisation, design). SOURCE TEXT: every claim about {game} (what it does, how it works, dates, names, figures) must come from the SOURCE TEXT below; do not use
outside knowledge about this game and do not invent. If the text has no technical angle you like, pick the most technical thing it does say (development, engine, design).
General computing explanations that are not specific to the game (what LOD or frame time is) are fine.
SOURCE TEXT:
{facts}
EVIDENCE: every scene that states something about {game} must carry `evidence`: a VERBATIM quote (6-30 words, copied exactly) from the SOURCE TEXT that supports it. At least 6 scenes
need evidence, and the validator checks that each quote really appears in the SOURCE TEXT. Scenes with no claim about the game leave evidence empty.
Mix the motion-graphic scenes above with REAL FOOTAGE scenes: type "footage", `mediaId` = EXACTLY one id from the list below (ids look like m01, m02...; each id at most once),
`text` = a 2-6 word UPPERCASE callout naming the technical detail.
CRUCIAL: the footage must show what the narrator mentions. For every footage scene, first read the item's description, then write the narration so that it STARTS by
naming what is visible ("Here, a man and a woman drive through a neon street...") and only then links it to the engineering fact. Never claim an item shows something its
description does not contain (no "ray-traced reflections" over a picture of two people in a car).
Use 6 to 10 footage scenes, spread through the whole video, and open with a hook that names the game.
NUMBERS: a counter / progressBar scene may ONLY use a figure that is written in the SOURCE TEXT (the validator rejects any other). Never invent internals such as object
counts, memory percentages or tick rates; if the text has no suitable figure, use text, list or footage scenes instead.
FOOTAGE AVAILABLE for {game} (each can be shown once):
{catalog}"""

GAME_RESTRICTIVE = """
GAME VIDEO (NO SOURCE TEXT AVAILABLE). This video is about the game {game}. No reference text could be loaded, so be strictly conservative: state ONLY facts about {game} that are
very well known and that you are completely sure of, hedged ("roughly", "reportedly"), and prefer explaining general techniques (what LOD, streaming, frame pacing or physics
steps are) over specific claims about this game. NEVER use numbers, dates or counts about the game; counter and progressBar scenes are forbidden in this video; leave evidence empty.
Mix the motion-graphic scenes above with REAL FOOTAGE scenes: type "footage", `mediaId` = EXACTLY one id from the list below (ids like m01; each at most once), `text` = 2-6 word
UPPERCASE callout. Start each footage narration by naming what the item VISIBLY shows (read its description first), then connect it to the idea. Use 6 to 10 footage scenes.
FOOTAGE AVAILABLE for {game} (each can be shown once):
{catalog}"""

CURIOSITY_RULES = "\nCURIOSITY VIDEO: no footage scenes; use the motion-graphic scene types only."

CURIOSITY_FACTS_RULES = """
SOURCE TEXT. This video is about a specific, real subject. Every claim about it (what it does, how it works, dates, names, figures, who said what) must come from the SOURCE TEXT below;
do not use outside knowledge about the subject and do not invent. Say "reportedly" for anything the text says is reported. General computing explanations that are not specific to the subject
(what an animation rig, a cloud layer or memory budget is) are fine. A counter / progressBar scene may ONLY use a figure that is written in the SOURCE TEXT (the validator rejects any other).
Never say how many days are left before a release or use relative dates ("this week", "tomorrow"): write the date itself.
SOURCE TEXT:
{facts}"""

FORMAT_COMMON = """
CONTENT FORMAT. This video follows a fixed format. The scene-type variety rule below does NOT apply to the format's own scene types (tier, versus, verdict, timeline),
which may follow each other. Everything else stays the same: a hook first, an outro last, a narration on every scene, 150-190 words in total, and NEVER two consecutive scenes of the same type unless it is one of the format's own types.
Number of scenes: 13 to 19 (tier and versus videos: 9 to 19, with narrations of 14-24 words per scene so the video still reaches 150-190 words)."""

FORMAT_RULES = {
    "myth": FORMAT_COMMON + """
FORMAT = MYTH OR FACT. Pick a theme (a component, a habit, a setting) and test 4 or 5 widespread beliefs about it.
- Each belief is a `verdict` scene: `text` = the claim exactly as people say it (max 7 words), `verdict` = myth | fact | partly, `accentText` = the one-line truth (max 6 words, REQUIRED on every verdict scene, never empty), `kicker` = "myth or fact".
- After each verdict scene put ONE supporting scene (counter, progressBar, list, codeBlock or curve) that shows the evidence for the correction; its narration explains WHY.
- Mix the verdicts: at least 2 myths and at least 1 fact or partly. Never pick a belief you are not sure about; "partly" is the honest answer when it depends.
- Scene 1 is the hook ("Five things you believe about your SSD. Some are wrong."), the last scene before the outro is a textWithAccent with the takeaway ("Check before you believe"). NEVER state a score or count of myths/facts anywhere (models miscount, and the reviewer rejects it).""",
    "tier": FORMAT_COMMON + """
FORMAT = TIER LIST. Rank 6 to 8 items of ONE category (kinds of RAM, SSD types, cooling methods, PC cases, GPU features...) from S (best) to F (worst) by ONE stated criterion
(say it in the hook: "ranked by value for gaming").
- The board fills up over consecutive `tier` scenes (one per item). EVERY tier scene repeats the items already placed, in the same order, and adds exactly ONE new item at the END of `items`.
  Item format "S|label": tier letter S, A, B, C, D or F, a bar, a SHORT label of at most 22 characters. `text` = the category ("Ranking SSDs"), `accentText` = the criterion, `kicker` = "tier list".
- EVERY tier scene sets `value` and `unit` = the figure of the NEW item on the ranking's criterion (USB 2.0 ranked by speed: value 480, unit "Mbps"; a GPU ranked by price: value 629, unit "€"),
  and its narration says that figure. It is drawn big next to the item, so the viewer sees WHY it lands in its tier; a ranking without numbers reads as an opinion.
- The narration of each tier scene names the NEW item and justifies its tier with a TRUE, concrete reason (a figure or a mechanism). Use the full range: at least 4 different tiers in the final board.
- Each tier line also carries an OPINION or a consequence for the viewer, never the same sentence shape twice ("Eight gigabytes in 2026? That's a trap for you.", "You'd pay double for ten percent more.").
  Say long figures rounded ("about eighteen hundred euros"); the exact figure is on screen.
- ORDER: the S-tier item is placed in the LAST tier scene (the reveal is the climax), and the hook names the conflict ("Seven cards, and the most expensive one gets an F."), never just the topic
  ("USB ranked by speed" is a label, not a hook). Title: a question the video answers ("Which USB Is Actually Fast?"), never "X Ranked From Worst to Best".
- Structure: hook (bigText), 6 to 8 tier scenes, one textWithAccent that gives the surprise or the lesson, outro.""",
    "whatif": FORMAT_COMMON + """
FORMAT = WHAT IF. One absurd but physically meaningful hypothetical about computing ("What if your PC had no cache?", "What if an SSD never erased data?", "What if RAM was as slow as a hard drive?").
- Scene 1: bigText with kicker "what if" and the hypothetical in 2-4 words. Scene 2 restates it as a question in textWithAccent.
- Then walk through the consequences step by step, ESCALATING each time, alternating the scene types (never two of the same type in a row), with real mechanisms and real approximate figures (counter, progressBar, curve, list, codeBlock). Say "roughly" when a figure is approximate.
- The consequences must follow from how the hardware or software really works; never invent figures. Close with what the real design does to avoid this, and why that is clever.
- OPTIONAL: ONE `split` scene to compare normal against the hypothetical: `demo` = speed or size, `left` / `right` = the labels, `leftValue` / `rightValue` = the figures (spoken in the narration), `unit` shared.""",
    "evolution": FORMAT_COMMON + """
FORMAT = EVOLUTION. How ONE thing evolved over time (GPUs, storage, CPUs, game graphics, memory, the web...).
- Use at least 2 `timeline` scenes: `items` = 3 to 5 chronological "year|label" entries, each year EXACTLY four digits ("1999", never "1990s" or "late 90s"; label at most 28 characters), only milestones you are SURE about, with the exact year. `kicker` = "evolution".
- Between timeline scenes use counter, progressBar or curve scenes that show the growth (transistors, capacity, price, speed) with real, approximate figures spoken in the narration.
- Hook with the span ("Thirty years of storage in sixty seconds"), end with what the trend means for the future.
- OPTIONAL: ONE `split` scene with `demo` = "ago" for a then-versus-now: `left` / `right` = the two years ("2012", "2025"), `leftValue` / `rightValue` = how many days ago each was (spoken as rounded years), `unit` = "days ago".""",
    "versus": FORMAT_COMMON + """
FORMAT = VERSUS. Two contenders (two consoles, two technologies, two standards) fought over 3 to 5 ROUNDS, each round one `versus` scene about ONE metric.
- `left` and `right` = the contender names (max 16 characters, IDENTICAL in every round), `leftValue` / `rightValue` = real approximate positive figures for that metric, `unit` shared by both,
  `text` = the metric ("Memory bandwidth"), `accentText` = a short tag ("per second"), `kicker` = "round 1", "round 2"... When LOWER is better (latency, price, power) set `winner` to the contender that wins.
  Both figures MUST be spoken in that scene's narration (digits are fine: "twenty-five point six versus forty-eight"). If you are not sure of a figure, pick another metric.
- Scene 1 is the hook that names both contenders, the last scene before the outro is a textWithAccent that names the overall winner and the catch ("but it depends on...").
- OPTIONAL: for ONE round you may use a `split` scene instead of `versus` (two stacked panels): `demo` = bars, speed or size, `left` / `right` = the labels, `leftValue` / `rightValue` = the figures (spoken in the narration), `unit` shared.""",
    "hardware": FORMAT_COMMON + """
FORMAT = HARDWARE DEEP DIVE (the old Hardware category, now in the Motion style). ONE surprising, well documented fact about silicon, memory, storage, networking, displays, power or engineering infrastructure
(cache and RAM latency, EUV lithography, why clocks stalled near 5 GHz, SSD wear, GPS and atomic clocks, fiber optics, thermal paste, power supplies, GPUs versus CPUs, ECC memory, data centers...).
- Explain HOW it really works: the mechanism first, then the real approximate figures (counter, progressBar, codeBlock, curve scenes are the evidence); physics and engineering, never opinions or benchmarks you cannot be sure of.
- Cursor: only as an accent, in 1 or 2 scenes and only where it means something: `drag` on a progressBar, `select` on the key phrase.""",
    "simple": FORMAT_COMMON + """
FORMAT = EVERYDAY TECH MYSTERY (the old Everyday category, now in the Motion style, hosted by the mouse cursor). A small, relatable mystery almost everyone has lived but few can explain:
USB plugs, Bluetooth and Wi-Fi quirks, batteries and charging, touchscreens, cameras, QR codes, GPS, headphones, microwaves, passwords, e-readers, smart homes, airplane mode...
- Friendly, conversational, with an analogy and a twist ("But there is more."); the closing line loops back to the hook.
- Cursor: the mouse pointer helps only when it means something: `select` on one key phrase, `drag` on a progressBar, `click` on a setting or a step. 2 or 3 scenes in all, never decorative.""",
    "fix": FORMAT_COMMON + """
FORMAT = FIX IT NOW. A symptom almost everyone has felt (a slow PC, stutter, a washed-out monitor, high ping, loud fans, a battery that drains, a blurry screen) fixed with ONE concrete setting or habit.
- Scene 1 (bigText or textWithAccent) is the symptom as the viewer feels it ("Your PC feels slow?"). Scene 2 gives the real cause in one line: what is actually happening.
- Then the fix in 2 or 3 steps. Each step names the EXACT place: a `codeBlock` whose 2-6 lines are the menu path or the command ("Settings > System > Display"), and a `list` of the steps. At least one codeBlock and one list.
- The mouse pointer is the hand that does the fix: `click` on the codeBlock (the setting, the menu path) and on the list (the first step), `select` on the key phrase of the symptom or the payoff. 2 to 4 scenes, never decorative.
- Say what usually improves, hedged ("often", "up to", "a few percent"); never promise a number you cannot back. Say "in Windows 11" when the menu differs by version.
- SAFETY: only built-in Windows settings, BIOS options or physical habits. Never a third-party "optimizer", never a registry edit, never disable antivirus, updates or any security feature. If a step is risky (BIOS), tell the viewer to note the old value first.
- Last scene before the outro is a textWithAccent recap ("Check this first"). The outro asks a question.""",
    "decode": FORMAT_COMMON + """
FORMAT = DECODED. A name or spec string everyone sees and few can read ("RTX 5070 Ti", "DDR5-6000 CL30", "Ryzen 7 7800X3D", "AX3000", "USB 3.2 Gen 2x2", "80 Plus Gold").
- Scene 1 shows the label itself as the hook ("What does Ti mean?"). Put the cursor action `select` on the scene that shows the label.
- Then split it into parts: ONE scene per part that matters (textWithAccent: the part in white, its meaning as the accent) and a `codeBlock` that shows the label broken apart, one part per line ("DDR5   = memory generation"). At least one codeBlock and one list.
- Make ONE number concrete with a counter or progressBar that is said in the narration (what 6000 transfers per second, 20 Gbps or 750 watts really means).
- Only naming schemes that are stable and well documented. Say "roughly" for any rule with exceptions ("vendors bend this pattern now and then"). No prices, no benchmarks, no rumours about unreleased products.
- Last scene before the outro is a textWithAccent takeaway ("Now you can read the next one"). The outro asks a question.""",
    "top5": FORMAT_COMMON + """
FORMAT = TOP 5. A countdown of exactly five items of ONE category, from number 5 to number 1 (the most surprising or most impressive last): five tiny PC components, five tricks inside a game engine, five reasons a phone gets slow...
- Scene 1 is the hook that names the category and the criterion ("Five reasons your PC stutters, ranked."). Never state a score.
- Then five consecutive `rank` scenes: `value` = the position (5, 4, 3, 2, 1 in that order), `text` = the item (max 6 words), `accentText` = the one-line why (max 3 words), `kicker` = "top 5". The narration of each rank scene gives ONE true, concrete reason or figure.
- Between ranks 3 and 2 you may put one counter, card or list scene as a breather. The last scene before the outro is a textWithAccent that sums it up.""",
    "eli5": FORMAT_COMMON + """
FORMAT = EXPLAINED SIMPLY. ONE hard idea (cache, a GPU, encryption, an SSD, the cloud, a compiler, latency) explained with a single everyday analogy (a library, a kitchen, a postal service, traffic).
- Scene 1 is the hook as a question a child would ask. Then 2 or 3 `card` scenes: each card states a piece of the ANALOGY (text) and the matching technical piece (accentText, at most 3 words). Keep the same analogy throughout.
- At least one `list` scene that maps analogy to reality (2-4 items "kitchen = CPU" style), and one counter or progressBar with a real figure said in the narration.
- Say where the analogy breaks down in one honest line. Last scene before the outro: a textWithAccent that gives the one-sentence version.""",
    "fails": FORMAT_COMMON + """
FORMAT = TECH FAILS. ONE famous, well documented technology failure or bug (a crash, a recall, a bad update, a naming mistake, a lost spacecraft) told as a story: what happened, why, what it cost, what changed.
- At least one `timeline` scene (3-5 "year|label" items, four-digit years, only dates you are SURE about) and at least one counter or progressBar with a real approximate figure said in the narration (cost, units, minutes).
- Tone: curious, never mocking people. Only events you know very well; hedge anything uncertain ("roughly", "reportedly"). End with the lesson engineers drew from it.""",
    "numbers": FORMAT_COMMON + """
FORMAT = BY THE NUMBERS. ONE subject (a CPU, a data center, a console, Wi-Fi, a game engine) told only through 4 to 6 striking figures.
- At least 4 scenes of type counter or progressBar, each with a different real, approximate figure said in the narration (value > 0, unit filled in). Between them put a textWithAccent or card that gives the figure meaning ("That is a stadium of people").
- Scene 1 is the biggest figure as the hook. Never invent a figure: use only numbers you know well and say "roughly".""",
    "quiz": FORMAT_COMMON + """
FORMAT = TECH QUIZ. Two or three questions about technology, each answered with a reveal.
- Each question is ONE `quiz` scene: `text` = the question (max 7 words), `items` = exactly 3 options (max 4 words each), `value` = the correct option (1, 2 or 3), `kicker` = "question 1", "question 2"... The narration reads the question and the three options, then reveals the answer and the one-line reason (the reveal happens in the second half of the scene).
- Put one explanation scene (card, counter or list) after each quiz scene. Questions must have ONE unambiguous, well documented answer. Spread the correct answers over different positions.
- Scene 1 is the hook ("Most people fail the second one."). The outro asks which question was harder.""",
    "stop": FORMAT_COMMON + """
FORMAT = STOP DOING THIS. Three habits that quietly hurt a PC, phone or setup (leaving it charging overnight, closing every background app, keeping 40 browser tabs, cheap cables...), each with the cost and the better habit.
- Scene 1 is the claim ("Three habits are killing your laptop battery."). Then for each habit: a headline scene naming the habit (textWithAccent: the habit in white, the cost as the accent) and a supporting scene (counter, progressBar, list or card) with a real, hedged figure or mechanism.
- Only habits with solid evidence; hedge ("often", "a few percent"). SAFETY: no registry edits, no disabling security. Last scene before the outro: a list of the three better habits.""",
    "rumor": FORMAT_COMMON + """
FORMAT = RUMOR MILL. ONE widely repeated tech rumour or claim, weighed.
- Scene 1 states the rumour as people say it. Then 2 or 3 `card` or `list` scenes with the evidence for and against (what is documented, what is only claimed), and ONE `progressBar` scene whose `value` is how plausible the claim is (0-100, said in the narration as "roughly seventy percent plausible"; `text` = "plausibility").
- Only rumours with a documented basis in the SOURCE TEXT when one is given; never a rumour about a real person. Make the final call hedged and clear. The outro asks the viewer to vote.""",
    "review": FORMAT_COMMON + """
FORMAT = WORTH IT? A quick verdict on ONE well-known kind of tech purchase decision (a 1440p monitor, a second SSD, an RTX upgrade over two generations, a mesh Wi-Fi kit, a mechanical keyboard).
- Two `list` scenes: what you get (2-4 items) and what it costs you or who it is for (2-4 items), plus one counter or progressBar with a real approximate figure said in the narration.
- The last content scene is a `verdict` scene: `verdict` = buy, wait or skip, `text` = the decision as a question ("Upgrade to 1440p?", max 7 words), `accentText` = the reason in at most 6 words, `kicker` = "worth it?". No prices of specific retailers, no brand favouritism, no benchmarks you cannot be sure of.""",
    "news": FORMAT_COMMON + """
FORMAT = TECH BRIEFING (a news bulletin, the channel's news section). A calm, authoritative anchor reads the three or four most important tech stories of the SOURCE TEXT, each in two beats.
- Scene 1 is the cold open: the single biggest story as a claim. Then ONE `headline` scene per story (3 or 4 stories): `text` = the headline in your own words (max 10 words), `kicker` = the outlet you rely on, in capitals ("THE VERGE", from the "reported by" list), `accentText` = what it means in at most 4 words, `unit` = how fresh ("TODAY", "THIS WEEK"). After each headline scene put ONE supporting scene (card, list or counter) that gives the key fact or figure.
- Use ONLY stories and facts of the SOURCE TEXT. Paraphrase in your own words, never copy sentences, no quotes. Name the outlet in the narration ("according to The Verge"). Anything the outlets only report or allege gets "reportedly" or "allegedly". Never add prices, dates or numbers that the text does not state.
- Last scene before the outro: a textWithAccent that names the day's theme. The outro vote asks which story matters more.""",
    "priced": FORMAT_COMMON + """
FORMAT = PRICED IN X. ONE unit of measure (a graphics card, a phone, a CPU, an SSD, a stick of RAM, a dollar, a watt) and 4 to 6 surprising things whose price or size is told IN THAT UNIT.
- Scene 1 is the hook that names the unit and the first surprise ("A tank round costs five graphics cards."). Never state a total.
- Then 4 to 6 `units` scenes, one per thing: `unit` = the unit's name, IDENTICAL in every units scene (max 3 words, plural: "RTX 5090 cards"), `text` = the thing (max 6 words, "One 120 mm tank round"), `value` = how many units it equals (a positive number up to 60; a decimal under 1 is fine for something cheaper than one unit, a decimal above 1 is rounded on screen so use whole numbers), `accentText` = the thing's own price or size (max 3 words, "$27,800 each"), `kicker` = "cost in units of".
- The unit's real price or size and EVERY figure must be well documented and said in the narration ("a tank round is roughly twenty-eight thousand dollars, about five of these cards"). Say "roughly". If you are not sure of a figure, pick another thing. No prices of specific retailers.
- Between units scenes put at most one counter, card or list scene as a breather; two units scenes may follow each other. The last scene before the outro is a textWithAccent that gives the surprise. The outro asks which one surprised the viewer most.""",
    "easter": FORMAT_COMMON + """
FORMAT = HIDDEN DETAIL (the 'easter egg' format). Tell the most surprising, little-known detail the SOURCE TEXT gives about the game's development, design or technology, as a reveal:
setup ("You have played this a hundred times"), clue, then the reveal. Open scene 1 with the game name and the promise of a secret, put kicker "hidden detail" on the reveal scenes, and show the
reveal over the footage scene that matches it best. Everything stays strictly inside the SOURCE TEXT: never present a rumour, a glitch or a secret that the text does not state.""",
}

_EN_STOP = {"the", "a", "an", "is", "are", "to", "of", "and", "in", "it", "your", "you", "for", "on", "with", "that", "this", "can", "no", "not", "one", "every", "more", "how", "why", "what", "from", "by", "at", "be", "its", "we", "just", "all", "up", "than", "into", "or", "so", "but", "if", "as"}


def looks_english(text: str) -> bool:
    """Heuristic language gate: rejects accents/Spanish function words and text with almost no English function words."""
    words = re.findall(r"[A-Za-zÀ-ÿ']+", text)
    if len(words) < 4:
        return not re.search(r"[ñ¿¡áéíóúü]", text, re.I)
    if re.search(r"[ñ¿¡áéíóúü]", text, re.I):
        return False
    spanish = sum(1 for w in words if w.lower() in {"el", "la", "los", "las", "de", "del", "que", "para", "con", "una", "por", "como", "más", "es", "y", "tu", "su"})
    english = sum(1 for w in words if w.lower() in _EN_STOP)
    return spanish <= max(1, len(words) // 12) and english >= max(1, len(words) // 14)


def strip_markers(p: MotionProject) -> None:
    """Removes markdown emphasis marks (*word*, **word**) from everything shown, spoken or published: the renderer draws them as literal asterisks."""
    clean = lambda t: re.sub(r"\s{2,}", " ", t.replace("*", "")).strip() if isinstance(t, str) else t
    for f in ("title", "description", "pinned_comment", "screen_title"):
        setattr(p, f, clean(getattr(p, f)))
    p.tags = [clean(t) for t in p.tags]
    for s in p.scenes:
        for f in ("text", "accentText", "kicker", "narration", "unit", "left", "right", "callout"):
            if getattr(s, f, None):
                setattr(s, f, clean(getattr(s, f)))
        if s.items:
            s.items = [clean(i) for i in s.items]
        if s.code:
            s.code = [i.replace("*", "") for i in s.code] if s.type != "codeBlock" else s.code  # a code block may legitimately contain * (pointers, multiplication)


def _repair(p: MotionProject) -> None:
    """Fixes what can be fixed without asking again: clamps scene lengths, trims overlong lists/code, forces the brand accent."""
    strip_markers(p)
    for s in p.scenes:
        s.durationInFrames = max(60, min(150, int(s.durationInFrames)))
        if s.items:
            s.items = s.items[:{"tier": 10, "timeline": 5, "ui": 6}.get(s.type, 4)]
        if s.code:
            s.code = [ln[:38] for ln in s.code[:8]]
        if s.value is not None and s.type == "progressBar":
            s.value = max(0.0, min(100.0, s.value))
        if s.type != "footage":
            s.mediaId = None
        if len(s.narration.split()) < 3 and s.type in ("flash", "bigText", "outro"):  # a one-word punch scene may simply speak its own text
            s.narration = " ".join(x for x in (s.text, s.accentText) if x)
    swap = {"bigText": "textWithAccent", "textWithAccent": "bigText"}  # visually interchangeable headline types
    for prev, cur in zip(p.scenes, p.scenes[1:]):
        if prev.type == cur.type and cur.type in swap:
            if cur.type == "textWithAccent" and len(cur.text.split()) > 4:
                continue  # bigText allows at most 4 words: leave it for the validator instead of breaking that rule
            cur.type = swap[cur.type]
    if (p.accent or "").upper() not in ("#00F0FF", "#007AFF"):  # the channel palette is blue/cyan: never any other colour
        p.accent = "#00F0FF"


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def quote_supported(quote: str, norm_facts: str) -> bool:
    """True when the quote (normalised) is in the source text, tolerating small differences (>= 88% of it must match one contiguous stretch)."""
    q = _norm(quote)
    if len(q.split()) < 4:
        return False
    if q in norm_facts:
        return True
    m = difflib.SequenceMatcher(None, norm_facts, q, autojunk=False).find_longest_match(0, len(norm_facts), 0, len(q))
    return m.size / len(q) >= 0.88


_NUM_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
              "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000, "million": 1_000_000, "billion": 1_000_000_000}


def _spoken(s: MotionSceneModel) -> bool:
    """True when the scene's figure is actually said in its narration (as digits or as number words)."""
    text = s.narration.lower().replace(",", "")
    if not text.strip():
        return False
    v = float(s.value or 0)
    digits = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    if any(abs(d - v) < 1e-6 or (v and abs(d - v) / v < 0.06) for d in digits):
        return True
    teens = re.findall(r"\b(?:eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen)\b", text)
    return bool([w for w in re.findall(r"[a-z]+", text) if w in _NUM_WORDS] or teens)


def _tier_board_problems(tiers: list) -> List[str]:
    """Every tier scene shows the board so far: the previous items in the same order plus exactly one new "S|label" item at the end."""
    out: List[str] = []
    prev: List[str] = []
    for i, s in tiers:
        items = s.items or []
        bad = [it for it in items if "|" not in it or it.split("|", 1)[0].strip().upper() not in TIER_LETTERS or not 0 < len(it.split("|", 1)[1].strip()) <= 22]
        if bad or not items:
            out.append(f"scene {i}: tier items must look like \"S|label\" (letter S A B C D F, label up to 22 characters): {bad[:2]}")
            continue
        if prev and (len(items) != len(prev) + 1 or [x.strip() for x in items[:-1]] != [x.strip() for x in prev]):
            out.append(f"scene {i}: a tier scene must repeat the previous board in the same order and add exactly ONE item at the end")
        prev = items
    return out


def _two_sided_problems(i: int, s: MotionSceneModel, noun: str) -> List[str]:
    """versus and split scenes: two short names, two positive figures, at least one of them said aloud."""
    out: List[str] = []
    if not (s.left and s.right and len(s.left) <= 16 and len(s.right) <= 16):
        out.append(f"scene {i}: {noun} needs `left` and `right` {'names' if noun == 'versus' else 'labels'} of at most 16 characters")
    if not (s.leftValue and s.rightValue and s.leftValue > 0 and s.rightValue > 0):
        out.append(f"scene {i}: {noun} needs positive leftValue and rightValue")
    elif not (_said(s.leftValue, s.narration) or _said(s.rightValue, s.narration)):
        out.append(f"scene {i}: the {noun} figures must be said in that scene's narration" + (" (no decorative figures)" if noun == "versus" else ""))
    return out


def _timeline_problems(i: int, s: MotionSceneModel) -> List[str]:
    rows = [it.split("|", 1) for it in (s.items or []) if "|" in it]
    years = [r[0].strip() for r in rows]
    if not (3 <= len(s.items or []) <= 5) or len(rows) != len(s.items or []) or not all(re.fullmatch(r"\d{4}", y) for y in years):
        return [f"scene {i}: timeline needs 3-5 \"year|label\" items with a four-digit year"]
    if years != sorted(years):
        return [f"scene {i}: timeline years must be in chronological order"]
    if any(len(r[1].strip()) > 28 for r in rows):
        return [f"scene {i}: timeline labels are at most 28 characters"]
    return []


def _verdict_problems(i: int, s: MotionSceneModel, fmt: Optional[str]) -> List[str]:
    out: List[str] = []
    if not s.verdict:
        out.append(f"scene {i}: verdict scenes need `verdict` (myth, fact or partly)")
    if not (s.accentText or "").strip():
        out.append(f"scene {i}: a verdict scene needs accentText: the one-line truth shown under the stamp")
    if s.accentText and len(s.accentText.split()) > 6:
        out.append(f"scene {i}: a verdict's accentText is at most 6 words")
    if fmt == "review" and s.verdict not in ("buy", "wait", "skip"):
        out.append(f"scene {i}: in a review the verdict is buy, wait or skip")
    elif fmt != "review" and s.verdict in ("buy", "wait", "skip"):
        out.append(f"scene {i}: buy / wait / skip stamps belong only to the review format")
    return out


def _units_problems(i: int, s: MotionSceneModel) -> List[str]:
    out: List[str] = []
    if not (s.value is not None and 0 < s.value <= 200):
        out.append(f"scene {i}: a units scene needs `value` = how many units (a positive number up to 200)")
    if not (s.unit or "").strip():
        out.append(f"scene {i}: a units scene needs `unit` = the unit's name")
    elif s.value is not None and not _said(s.value, s.narration):
        out.append(f"scene {i}: the units figure must be said in that scene's narration")
    return out


def _scene_problems(i: int, s: MotionSceneModel, fmt: Optional[str]) -> List[str]:
    """The fields each format scene type needs (see the prompts), whatever the format of the video."""
    t = s.type
    if t == "versus":
        return _two_sided_problems(i, s, "versus")
    if t == "split":
        demo = [] if (s.demo or "bars") in SPLIT_DEMOS else [f"scene {i}: split `demo` must be one of {', '.join(SPLIT_DEMOS)}"]
        return demo + _two_sided_problems(i, s, "split")
    if t == "verdict":
        return _verdict_problems(i, s, fmt)
    if t == "timeline":
        return _timeline_problems(i, s)
    if t == "units":
        return _units_problems(i, s)
    if t == "rank" and not (s.value and 1 <= s.value <= 9 and float(s.value).is_integer()):
        return [f"scene {i}: a rank scene needs `value` = its position (5, 4, 3, 2, 1)"]
    if t == "quiz":
        out = [] if (s.items and len(s.items) == 3) else [f"scene {i}: a quiz scene needs exactly 3 options in `items`"]
        return out + ([] if (s.value and int(s.value) in (1, 2, 3)) else [f"scene {i}: a quiz scene needs `value` = the correct option (1, 2 or 3)"])
    if t == "headline" and not (s.kicker or "").strip():
        return [f"scene {i}: a headline scene needs `kicker` = the outlet"]
    return []


# What each format demands of its own scenes: name -> function(scenes, count_of_type, tier_scenes) -> list of problems
def _needs_myth(sc, n, tiers):
    v = [s.verdict for s in sc if s.type == "verdict"]
    out = [f"myth format needs 4-5 verdict scenes, got {len(v)}"] if len(v) < 4 else []
    if v.count("myth") < 2 or not (v.count("fact") + v.count("partly")):
        out.append("mix the verdicts: at least 2 myths and at least 1 fact or partly")
    return out


def _needs_tier(sc, n, tiers):
    if not 6 <= len(tiers) <= 9:
        return [f"tier format needs 6-9 tier scenes (one per item), got {len(tiers)}"]
    if len({it.split("|", 1)[0].strip().upper() for it in (tiers[-1][1].items or []) if "|" in it}) < 4:
        return ["the final tier board must use at least 4 different tiers"]
    missing = [i for i, s in tiers if not (s.value and s.value > 0 and (s.unit or "").strip())]
    if missing:
        return [f"scenes {missing[:4]}: every tier scene needs `value` > 0 and `unit` (the new item's figure on the ranking's criterion, drawn next to it)"]
    unsaid = [i for i, s in tiers if not _spoken(s)]
    if unsaid:
        return [f"scenes {unsaid[:4]}: the tier scene's value must be said in its narration"]
    last_new = ((tiers[-1][1].items or [""])[-1].split("|", 1)[0]).strip().upper()
    if last_new != "S":
        return ["the S-tier item must be the one placed in the LAST tier scene (the reveal is the climax)"]
    return []


def _needs_codeblock_and_list(fmt: str, steps: str, parts: str):
    def check(sc, n, tiers):
        out = []
        if not n("codeBlock"):
            out.append(f"{fmt} format needs a codeBlock scene ({steps if fmt == 'fix' else parts})")
        if not n("list"):
            out.append(f"{fmt} format needs a list scene ({'the steps' if fmt == 'fix' else 'what each part tells you'})")
        return out
    return check


def _needs_review(sc, n, tiers):
    out = []
    if n("verdict") != 1 or sc[-2].type != "verdict" and not any(x.type == "verdict" for x in sc[-4:]):
        out.append("review format needs ONE verdict scene near the end (buy, wait or skip)")
    if n("list") < 2:
        out.append("review format needs two list scenes (what you get, what it costs)")
    return out


def _needs_priced(sc, n, tiers):
    units = [s.unit.strip().lower() for s in sc if s.type == "units" and s.unit]
    if not 4 <= n("units") <= 6:
        return [f"priced format needs 4-6 units scenes (one per thing), got {n('units')}"]
    if len(set(units)) > 1:
        return ["the unit must have the SAME name in every units scene"]
    return []


def _needs(condition_failed, message: str):
    """A format rule of the form "needs X": `condition_failed(sc, n)` is True when the script breaks it."""
    return lambda sc, n, tiers: [message] if condition_failed(sc, n) else []


FORMAT_NEEDS = {
    "myth": _needs_myth,
    "tier": _needs_tier,
    "evolution": _needs(lambda sc, n: n("timeline") < 2, "evolution format needs at least 2 timeline scenes"),
    "versus": lambda sc, n, tiers: [f"versus format needs 3-5 versus scenes (rounds), got {n('versus')}"] if not 3 <= n("versus") <= 5 else [],
    "whatif": _needs(lambda sc, n: sum(n(t) for t in ("counter", "progressBar", "curve", "list", "codeBlock")) < 3,
                     "what-if format needs at least 3 consequence scenes (counter, progressBar, curve, list or codeBlock)"),
    "fix": _needs_codeblock_and_list("fix", "the exact menu path or command", "the label broken into its parts"),
    "decode": _needs_codeblock_and_list("decode", "the exact menu path or command", "the label broken into its parts"),
    "top5": lambda sc, n, tiers: [f"top5 format needs five rank scenes with values 5, 4, 3, 2, 1 in that order, got {[s.value for s in sc if s.type == 'rank']}"]
    if [s.value for s in sc if s.type == "rank"] != [5, 4, 3, 2, 1] else [],
    "quiz": lambda sc, n, tiers: [f"quiz format needs 2-3 quiz scenes, got {n('quiz')}"] if not 2 <= n("quiz") <= 3 else [],
    "news": lambda sc, n, tiers: [f"news format needs 3-4 headline scenes (one per story), got {n('headline')}"] if not 3 <= n("headline") <= 4 else [],
    "review": _needs_review,
    "fails": _needs(lambda sc, n: not n("timeline") or not (n("counter") or n("progressBar")), "fails format needs a timeline scene and a counter or progressBar scene"),
    "numbers": _needs(lambda sc, n: n("counter") + n("progressBar") < 4, "numbers format needs at least 4 counter or progressBar scenes"),
    "eli5": _needs(lambda sc, n: n("card") < 2 or not n("list"), "eli5 format needs at least 2 card scenes (the analogy) and a list scene (analogy = reality)"),
    "stop": _needs(lambda sc, n: not n("list") or not (n("counter") or n("progressBar") or n("card")), "stop format needs a list scene and a counter, progressBar or card scene"),
    "rumor": _needs(lambda sc, n: not n("progressBar") or n("card") + n("list") < 2, "rumor format needs a progressBar (plausibility) and at least 2 card or list scenes"),
    "priced": _needs_priced,
}

# The scene types that belong to one format only, and the formats that may use the "format scenes" (tier, versus, verdict, timeline)
OWN_SCENES = {"units": ("priced",), "rank": ("top5",), "quiz": ("quiz",), "headline": ("news",)}
OWN_SCENE_MESSAGES = {"units": "units scenes belong only to the priced format", "rank": "rank scenes belong only to the top5 format", "quiz": "quiz scenes belong only to the quiz format",
                      "headline": "headline scenes belong only to the news format"}
FORMAT_SCENE_TYPES = ("tier", "versus", "verdict", "timeline")
FORMAT_ONLY_SCENES = {  # format -> (the one kind of format scene it uses, message)
    "myth": ("verdict", "a myth video uses only verdict scenes among the format scenes"),
    "tier": ("tier", "a tier video uses only tier scenes among the format scenes"),
    "versus": ("versus", "a versus video uses only versus scenes among the format scenes"),
    "evolution": ("timeline", "an evolution video uses only timeline scenes among the format scenes"),
    "review": ("verdict", "a review uses only a verdict scene among the format scenes"),
    "fails": ("timeline", "a fails video uses only timeline scenes among the format scenes"),
}


def _format_problems(p: MotionProject, fmt: Optional[str]) -> List[str]:
    """Checks of the format's own scene types (tier boards, versus rounds, verdict stamps, timelines...), whatever the format of the video, and of what each format demands."""
    sc = p.scenes
    tiers = [(i, s) for i, s in enumerate(sc, 1) if s.type == "tier"]

    def n(t: str) -> int:
        return sum(1 for s in sc if s.type == t)

    out = _tier_board_problems(tiers)
    for i, s in enumerate(sc, 1):
        out += _scene_problems(i, s, fmt)
    if len({(s.left or "").strip().lower() for s in sc if s.type == "versus"}) > 1 or len({(s.right or "").strip().lower() for s in sc if s.type == "versus"}) > 1:
        out.append("the versus contenders must have the SAME names in every round")
    if fmt in FORMAT_NEEDS:
        out += FORMAT_NEEDS[fmt](sc, n, tiers)
    for scene_type, formats in OWN_SCENES.items():
        if fmt not in formats and n(scene_type):
            out.append(OWN_SCENE_MESSAGES[scene_type])
    if n("split") and fmt not in (None, "versus", "evolution", "whatif", "numbers", "fails", "hardware", "priced"):
        out.append("split scenes belong only to versus, evolution, whatif, numbers, fails, hardware and priced videos")
    present = {t: n(t) for t in FORMAT_SCENE_TYPES}
    if fmt not in ("myth", "tier", "versus", "evolution", "review", "fails") and any(present.values()):
        out.append("tier / versus / verdict / timeline scenes belong only to their own format")
    if fmt in FORMAT_ONLY_SCENES:
        own, message = FORMAT_ONLY_SCENES[fmt]
        if any(count for t, count in present.items() if t != own):
            out.append(message)
    return out


BAD_OPENER = re.compile(r"^\W*(so\b|welcome|hey\b|hi\b|hello|today|in this video|did you know|have you ever|do you know|let(?:'?s| us)|ever wonder)", re.I)
GENERIC_CLOSER = re.compile(r"surprise you or|tell me below|know it or|did you know it|do you agree with this", re.I)  # the closers 9 in 10 scripts shared: a vote must name this video's own two options
OPEN_LOOP = re.compile(
    r"\b(wait for|stay (?:to|till|until|for|with)|by the end|until the end|in a moment|in a second|before we (?:finish|end)|later on|catch|twist|nobody|no one|most people|secret|"
    r"gets (?:worse|weirder|stranger|better)|the (?:last|final|third|second|next) (?:one|reason|part|step|round|rule|trick)|you will not believe|that is not even|that is not the)\b", re.I)
HEADLINE = ("bigText", "textWithAccent")
HOOK_MAX_WORDS = 16  # the prompt asks for 14; two more words of tolerance
SCENE_MAX_WORDS = 17  # about 6.5 s of speech: beyond that the screen sits still for too long (the audit found 6 s on average)


def retention_problems(p: MotionProject) -> List[str]:
    """Style checks from the Nov 2026 content study (notes/content_style_study_2026-11.md): a cold open, an open loop early on, a visual break at least every third scene and a two-option vote at the end.
    Only generated scripts are held to these; the hand-written banks are measured with `scripts/lint_retention.py`."""
    out: List[str] = []
    if not p.scenes:
        return out
    hook = p.scenes[0].narration.strip()
    if BAD_OPENER.search(hook):
        out.append("scene 1 must be a cold open: the claim itself, never a greeting, \"so\", \"today\", \"in this video\", \"did you know\" or \"have you ever wondered\"")
    if len(hook.split()) > HOOK_MAX_WORDS:
        out.append(f"scene 1 narration has {len(hook.split())} words: the cold open is at most 14 words, the claim and nothing else")
    if not any(OPEN_LOOP.search(s.narration) for s in p.scenes[1:5]):
        out.append("scenes 2-5 need an open loop: one narration line that promises a later payoff (for example \"And the last step is the one most people skip.\" or \"Stay to the end, the catch comes last.\")")
    if not re.search(r"\bor\b[^?]*\?", p.scenes[-1].narration):
        out.append("the outro narration must end with a two-option vote (\"A or B?\"), not an open question")
    if GENERIC_CLOSER.search(p.scenes[-1].narration + " " + p.pinned_comment):
        out.append("the closing vote is the generic one (\"did that surprise you or did you know it\", \"tell me below\"): ask a question about THIS video's own two options, named in the question (\"Team DDR4 or team DDR5?\")")
    if not (re.search(r"\bor\b", p.pinned_comment) and "?" in p.pinned_comment) or len(p.pinned_comment) > 120:
        out.append("pinned_comment must be the same two-option vote (\"A or B? Reply with one word.\"), at most 120 characters")
    cap = 24 if any(s.type in ("tier", "versus") for s in p.scenes) else SCENE_MAX_WORDS  # scenes of the table formats carry two figures, so they may be wordier
    long_ones = [i for i, s in enumerate(p.scenes, 1) if len(s.narration.split()) > cap]
    if long_ones:
        out.append(f"scene {long_ones[0]} narration is longer than {cap} words: a visual change at least every 5 seconds, so split it across two scenes")
    run = 0
    for i, s in enumerate(p.scenes, 1):
        run = run + 1 if s.type in HEADLINE else 0
        if run > 2:
            out.append(f"scenes {i - 2}-{i} are three headline scenes in a row: break the rhythm with a card, counter, list, codeBlock, progressBar, curve or flash scene")
            break
    return out


def _said(value: float, narration: str) -> bool:
    """True when `value` appears in the narration as digits or as a spoken number (loose: any digit within 6 % or any number word)."""
    text = narration.lower().replace(",", "")
    digits = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    if any(abs(d - value) < 1e-6 or (value and abs(d - value) / value < 0.06) for d in digits):
        return True
    return any(w in _NUM_WORDS for w in re.findall(r"[a-z]+", text)) or bool(re.search(r"\b(?:eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen)\b", text))


def make_validator(catalog: Optional[Dict[str, dict]] = None, facts: Optional[str] = None, fmt: Optional[str] = None, retention: bool = False):
    """Validator for generate_structured. `catalog` (media id -> entry) and `facts` (source dossier) are given for game videos; `fmt` is the content format;
    `retention` adds the cold-open / open-loop / pattern-break style checks (on for generated scripts, off for the hand-written banks)."""
    known = figures_in(facts) if facts else None
    norm_facts = _norm(facts) if facts else None
    def validate_project(p: MotionProject) -> List[str]:
        _repair(p)
        out: List[str] = _format_problems(p, fmt)
        out += _ui_problems(p, fmt)
        if retention:
            out += retention_problems(p)
        n = len(p.scenes)
        compact = fmt in ("tier", "versus")  # these formats are built from a fixed run of format scenes, so they have fewer, wordier scenes
        if not (8 if compact else 10) <= n <= 21:
            out.append(f"{n} scenes (need {'9-19' if compact else '11-19'})")
        words, est = p.narration_words, estimated_seconds(p)
        if any(len(s.narration.split()) < 3 for s in p.scenes):
            out.append("every scene needs a narration (3-16 words; short is fine for a one-word flash scene)")
        if any(len(s.narration.split()) > (26 if compact else 20) for s in p.scenes):
            out.append(f"a scene narration is longer than {26 if compact else 20} words")
        if not 61.0 <= est <= MAX_SECONDS:  # just over 60 s is enough for monetisation
            out.append(f"narration has {words} words across {n} scenes (about {est:.0f} s): it must come to 61-{MAX_SECONDS:.0f} s (aim for roughly 135-190 words, about 11 per scene)")
        if p.scenes and p.scenes[-1].type != "outro":
            out.append("the last scene must be type outro")
        if p.scenes and p.scenes[0].type not in ("bigText", "textWithAccent"):
            out.append("the first scene must be bigText or textWithAccent")
        flashes = [i for i, s in enumerate(p.scenes) if s.type == "flash"]
        if len(flashes) > 2 or any(b - a < 4 for a, b in zip(flashes, flashes[1:])):
            out.append("at most two flash scenes, at least four scenes apart")
        if sum(1 for s in p.scenes if s.light) > 1:
            out.append("at most one light scene")
        for sc_ in p.scenes:  # an unknown effect is simply dropped, the scene stays
            fx_ = (sc_.fx or "").strip().lower()
            sc_.fx = fx_ if fx_ in FX_NAMES else None
        fix_duplicate_accents(p.scenes)
        sanitize_cursors(p.scenes, fmt)  # actions that mean nothing (a tab, a hover, a click on a headline...) are dropped; the budget and spacing are enforced
        cursor_acts = [sc_.cursor for sc_ in p.scenes if sc_.cursor]
        if fmt == "fix" and len(cursor_acts) < 2:
            out.append("fix format needs the pointer on at least 2 scenes (click on the codeBlock or the list, select on a headline pair): it is the hand that does the fix")
        if fmt == "decode" and "select" not in cursor_acts:
            out.append("decode format needs a `select` cursor on the scene that shows the label")
        used_media = [s.mediaId for s in p.scenes if s.type == "footage"]
        if catalog is None and used_media:
            out.append("footage scenes are only allowed in game videos")
        if catalog is not None and norm_facts is not None:
            cited = [s for s in p.scenes if s.evidence and s.evidence.strip()]
            for s in cited:
                if not quote_supported(s.evidence, norm_facts):
                    out.append(f"evidence quote not found in the SOURCE TEXT: \"{s.evidence[:70]}\" (copy it exactly)")
            if len(cited) < 6:
                out.append(f"only {len(cited)} scenes carry evidence from the SOURCE TEXT (need 6+)")
        if catalog is not None and norm_facts is None and any(s.type in ("counter", "progressBar") for s in p.scenes):
            out.append("no counter / progressBar scenes in a game video without source text")
        if catalog is not None:
            bad = [m for m in used_media if m not in catalog]
            if bad:
                out.append(f"unknown footage ids {bad[:3]}: use only ids from the list")
            if len(used_media) != len(set(used_media)):
                out.append("a footage id was used twice")
            if not 5 <= len(used_media) <= 11:
                out.append(f"{len(used_media)} footage scenes (need 6-10)")
        for i, s in enumerate(p.scenes, 1):
            limit = 4 if s.type == "bigText" else 10 if s.type == "headline" else 7
            if len(s.text.split()) > limit and s.type != "footage":
                out.append(f"scene {i}: text longer than {limit} words")
            if s.type == "footage" and (len(s.text.split()) > 7 or not s.mediaId):
                out.append(f"scene {i}: footage needs a mediaId and a callout of at most 6 words")
            if s.accentText and len(s.accentText.split()) > (6 if s.type in ("verdict", "ui") else 3):
                out.append(f"scene {i}: accentText longer than 3 words")
            if s.type == "counter" and (s.value is None or s.value <= 0):
                out.append(f"scene {i}: counter needs a positive value")
            if known is not None and s.type in ("counter", "progressBar") and s.value is not None and not any(abs(k - s.value) < 1e-6 or (k and abs(k - s.value) / k < 0.01) for k in known):
                out.append(f"scene {i}: the figure {s.value:g} is not in the SOURCE TEXT: use a figure written there or a different scene type")
            if s.type in ("counter", "progressBar") and s.value is not None and not _spoken(s):
                out.append(f"scene {i}: the number {s.value:g} must be mentioned in that scene's narration (no decorative figures)")
            if s.type == "progressBar" and s.value is None:
                out.append(f"scene {i}: progressBar needs value")
            if s.type == "list" and not (s.items and 2 <= len(s.items) <= 4):
                out.append(f"scene {i}: list needs 2-4 items")
            if s.type == "codeBlock" and not (s.code and len(s.code) >= 2):
                out.append(f"scene {i}: codeBlock needs 2+ code lines")
            if i > 1 and s.type == p.scenes[i - 2].type and s.type not in ("outro", "footage", "tier", "versus", "verdict", "timeline", "rank", "units", "split"):
                out.append(f"scenes {i - 1} and {i} have the same type")
        if not looks_english(p.all_text):
            out.append("the text is not English: everything must be American English")
        return out
    return validate_project


class _Issue(BaseModel):
    scene: int
    problem: str
    definitely_wrong: bool
    fixed_verdict: Optional[Literal["myth", "fact", "partly"]] = Field(default=None, description="For a verdict scene whose stamp is wrong: the correct stamp (the narration is then rewritten to agree with it)")
    fixed_narration: Optional[str] = Field(default=None, description="For a definitely_wrong issue: a replacement narration for that scene (8-16 words) that is TRUE and, for footage scenes, mentions only what the footage visibly shows")


class _Review(BaseModel):
    errors: List[_Issue] = Field(default_factory=list)


def _review_prompt(p: MotionProject, catalog, facts):
    rows = []
    for i, s in enumerate(p.scenes, 1):
        shows = f" | FOOTAGE SHOWS: {catalog[s.mediaId]['caption']}" if catalog and s.type == "footage" and s.mediaId in catalog else ""
        extra = ""
        if s.type == "versus":
            extra = f" | VERSUS: {s.left} = {s.leftValue:g}{s.unit or ''} vs {s.right} = {s.rightValue:g}{s.unit or ''}, winner: {s.winner or 'the bigger figure'}" if s.leftValue and s.rightValue else " | VERSUS (figures missing)"
        elif s.type == "verdict":
            extra = f" | CLAIM VERDICT: the claim is shown as {(s.verdict or '?').upper()}; the correction on screen is \"{s.accentText}\""
        ev = f" | EVIDENCE QUOTE: \"{s.evidence}\"" if s.evidence else ""
        rows.append(f"{i}. [{s.type}] {s.text} | narration: \"{s.narration}\" | accent: {s.accentText or '-'} | value: {s.value if s.value is not None else '-'}{s.unit or ''} | items: {s.items or '-'} | code: {s.code or '-'}{extra}{shows}{ev}")
    footage_rule = (" For footage scenes, flag (definitely_wrong=true) ONLY when the narration or callout names a specific thing (creature, place, character, object) that the "
                    "FOOTAGE SHOWS description clearly does not contain." if catalog else "")
    if facts:
        game_rule = (" You are given the SOURCE TEXT about the game. Any claim about the game itself (its engine, techniques, figures, dates, names, behaviour) that the SOURCE TEXT "
                     "does not state or clearly imply is definitely_wrong, even if it sounds plausible; a scene whose narration says more than its EVIDENCE QUOTE supports is "
                     "definitely_wrong; fixed_narration must then use only what the text supports.")
    elif p.game:
        game_rule = (" No source text exists for this game: any specific claim about the game itself (figures, dates, counts, named internals) is definitely_wrong; only widely known, "
                     "hedged statements and general technique explanations are acceptable.")
    else:
        game_rule = ""
    fmt_rule = (" The scenes of type verdict state a claim and stamp it MYTH, FACT or PARTLY: flag a verdict that is wrong. versus scenes compare two contenders on one metric: flag any figure that is "
                "clearly wrong, and a winner that contradicts the figures. tier scenes rank items: flag a placement whose stated reason is false. timeline scenes list milestones as year|label: flag a wrong year.")
    system = ("You are a strict but fair technical fact-checker. List in `errors` only statements that are clearly FALSE or misleading, or numbers that are clearly wrong "
              "(check arithmetic). Simplifications for beginners are fine: mark definitely_wrong=false for those or leave them out. Code lines must be valid and do what the scene "
              "says. For every definitely_wrong issue also give fixed_narration (and fixed_verdict when a verdict stamp is the error)." + game_rule + footage_rule + fmt_rule)
    prompt = f"Topic: {p.topic}" + (f" (game: {p.game})" if p.game else "") + (f"\nSOURCE TEXT:\n{facts}\n" if facts else "") + "\nScenes:\n" + "\n".join(rows) + "\n\nFact-check this motion-graphics script."
    return prompt, system


def fact_check(p: MotionProject, catalog: Optional[Dict[str, dict]] = None, facts: Optional[str] = None) -> List[_Issue]:
    """Second pass: the blocking issues (false claims, wrong figures, unsupported or mismatched footage claims), each with a replacement narration.

    Tiered so that it keeps working whatever fails: (1) the strongest reviewer, retried once after a pause if its per-minute window is full; (2) a PANEL of every other
    reviewer that answers, whose issues are merged (stricter than any one of them); raises GeminiUnavailable only when no reviewer answered at all."""
    prompt, system = _review_prompt(p, catalog, facts)
    kw = dict(prompt=prompt, system_instruction=system, schema=_Review, temperature=0.1, max_output_tokens=2500)  # small: the free tier meters prompt + reserved output per minute
    for attempt in (1, 2):
        try:
            review, _t, model = generate_structured(**kw, provider_first="cloudflare", provider_models=STRONG_REVIEWERS, strict_provider=True)
            bad = [e for e in review.errors if e.definitely_wrong]
            logger.info("Fact-check via %s: %d blocking issue(s).", model, len(bad))
            return bad
        except GeminiUnavailable as exc:
            logger.warning("Strong reviewer unavailable (%s)%s", str(exc)[:100], "; retrying in 25 s." if attempt == 1 else ".")
            if attempt == 1:
                time.sleep(25)
    merged: Dict[tuple, _Issue] = {}
    answered: List[str] = []
    panel = [dict(provider_first="cloudflare", provider_models=["@cf/meta/llama-3.3-70b-instruct-fp8-fast"], strict_provider=True),
             dict()]  # last: the default chain (Gemini first)
    for opts in panel:
        try:
            review, _t, model = generate_structured(**kw, **opts)
        except GeminiUnavailable as exc:
            logger.warning("Panel reviewer %s unavailable: %s", opts.get("provider_first", "gemini"), str(exc)[:80])
            continue
        answered.append(model)
        for e in review.errors:
            if e.definitely_wrong:
                merged.setdefault((e.scene, e.problem[:40]), e)
    if not answered:
        raise GeminiUnavailable("no reviewer answered")
    logger.info("Fact-check by panel %s: %d blocking issue(s) merged.", answered, len(merged))
    return list(merged.values())


def _apply_fixes(p: MotionProject, issues: List[_Issue]) -> int:
    """Replaces the narration of the flagged scenes with the reviewer's corrected text. Returns how many were applied."""
    done = 0
    for e in issues:
        if not 1 <= e.scene <= len(p.scenes):
            continue
        sc = p.scenes[e.scene - 1]
        if e.fixed_verdict and sc.type == "verdict" and e.fixed_verdict != sc.verdict:
            sc.verdict = e.fixed_verdict
            done += 1
        if e.fixed_narration and 3 <= len(e.fixed_narration.split()) <= 20:
            sc.narration = e.fixed_narration.strip()
            done += 1
    return done


def generate_motion_project(topic: Optional[str] = None, avoid_topics: Optional[List[str]] = None, kind: str = "curiosity",
                            game: Optional[str] = None, catalog: Optional[Dict[str, dict]] = None, facts: Optional[str] = None, attempts: int = 3,
                            fmt: Optional[str] = None) -> MotionProject:
    """A validated, fact-checked project. For kind='game' pass the chosen `game` and its footage `catalog` (id -> entry).
    Raises GeminiUnavailable when no provider answers, RuntimeError if every attempt fails the checks."""
    avoid = [t for t in (avoid_topics or []) if t][-25:]
    if fmt is not None and fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt!r}: use one of {FORMATS}")
    if fmt == "easter" and kind != "game":
        raise ValueError("the easter (hidden detail) format needs a game video")
    system = SYSTEM_PROMPT + RETENTION_RULES
    if fmt not in UI_FORMATS_OFF and kind != "game":
        system += ui_rules()
    if kind == "game":
        lines = "\n".join(f"  * id={k} [{e['kind']}] {e['caption']}" for k, e in (catalog or {}).items())
        system += (GAME_RULES.format(game=game, catalog=lines, facts=facts) if facts else GAME_RESTRICTIVE.format(game=game, catalog=lines))
        base = f"Make a motion-graphics video about an engineering fact of the game {game}" + (f", specifically: {topic}" if topic else "") + ".\n"
    else:
        system += CURIOSITY_RULES + (CURIOSITY_FACTS_RULES.format(facts=facts) if facts else "")
        base = (f"Make a motion-graphics explainer about: {topic}\n" if topic
                else "Pick ONE fascinating idea about computers, hardware, coding, AI or tech that works well as animated typography (a surprising fact, a counter-intuitive mechanism, a tip).\n")
    if fmt:
        system += FORMAT_RULES[fmt]
        base = base.replace("motion-graphics explainer", f"{fmt} video").replace("motion-graphics video", f"{fmt} video")
        if not topic and kind != "game":
            hint = {"hardware": "Pick ONE well documented fact about silicon, memory, storage, networking, displays, power or engineering that you know very well.",
                    "simple": "Pick ONE small everyday tech mystery that almost everyone has experienced and that you can explain truthfully."}.get(fmt, "Pick a topic about computers, hardware, coding, games, AI or tech that fits it perfectly and that you know well.")
            base = f"Make a {fmt} video (the format is described in the rules). {hint}\n"
    if avoid:
        base += "Do NOT repeat or resemble these topics: " + "; ".join(avoid) + "\n"
    feedback = ""
    for attempt in range(1, attempts + 1):
        project, tokens, model = generate_structured(prompt=base + feedback + "Return a JSON object matching the schema.", system_instruction=system, schema=MotionProject,
                                                     temperature=0.8, validate=make_validator(catalog if kind == "game" else None, facts, fmt, retention=True), max_output_tokens=12000, max_passes=3)
        project.kind, project.game, project.format = kind, (game if kind == "game" else None), fmt
        project.gemini_input_tokens, project.gemini_output_tokens = tokens
        validator = make_validator(catalog if kind == "game" else None, facts, fmt, retention=True)
        problems: List[_Issue] = []
        try:
            for rnd in range(1, 4):  # the reviewer both flags and fixes narration: apply its fixes and look again before giving up on the script
                problems = fact_check(project, catalog if kind == "game" else None, facts)
                if not problems:
                    break
                logger.warning("Fact-check round %d (attempt %d): %s", rnd, attempt, " | ".join(f"scene {e.scene}: {e.problem}" for e in problems)[:300])
                if rnd == 3 or not _apply_fixes(project, problems) or validator(project):
                    break
        except GeminiUnavailable as exc:
            logger.warning("Fact-check unavailable (%s): the video will not be uploaded automatically.", str(exc)[:100])
            project.fact_checked = False
            return project
        if not problems and not validator(project):
            logger.info("Motion project '%s' ready via %s: %d scenes, about %.0f s.", project.topic, model, len(project.scenes), estimated_seconds(project))
            return project
        feedback = "A previous attempt was rejected by the fact-checker for: " + "; ".join(f"scene {e.scene}: {e.problem}" for e in problems) + ". Write a different, accurate script.\n"
    raise RuntimeError(f"{attempts} consecutive scripts failed the fact-check; nothing produced.")
