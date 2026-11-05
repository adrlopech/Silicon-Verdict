"""Series 6 - Motion Graphics: a short kinetic-typography video (20-45 s, vertical 1080x1920, always English).

Gemini (or a fallback provider) writes the scene list as structured JSON; this module validates and repairs it (language, lengths, durations,
scene rules), has a second pass fact-check it, and hands the result to the MotionGraphic Remotion composition.
"""
import logging
import re
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from services.gemini_client import GeminiUnavailable, generate_structured

logger = logging.getLogger(__name__)

FPS = 30
MIN_FRAMES, MAX_FRAMES = 20 * FPS, 45 * FPS
SceneType = Literal["bigText", "textWithAccent", "counter", "list", "codeBlock", "progressBar", "outro", "curve", "flash"]


class MotionSceneModel(BaseModel):
    type: SceneType
    text: str = Field(..., description="Main line, at most 7 words (bigText: at most 4)")
    accentText: Optional[str] = Field(default=None, description="ONE accent word or short phrase (max 3 words) shown in colour, italic serif")
    kicker: Optional[str] = Field(default=None, description="Optional tiny label above the text, 1-3 words")
    value: Optional[float] = Field(default=None, description="counter: final number; progressBar: percentage 0-100")
    unit: Optional[str] = Field(default=None, description="counter/progressBar suffix such as %, ms, GB")
    items: Optional[List[str]] = Field(default=None, description="list: 2-4 items of at most 5 words")
    code: Optional[List[str]] = Field(default=None, description="codeBlock: 2-8 short real code or shell lines (max 38 characters each)")
    light: bool = Field(default=False, description="Light background variant, use for at most one scene")
    durationInFrames: int = Field(..., description="Scene length in frames at 30 fps: 60-150")


class MotionProject(BaseModel):
    topic: str
    screen_title: str = Field(..., description="Short title shown in the HUD, at most 24 characters")
    title: str = Field(..., max_length=100, description="YouTube Shorts title in English, at most 80 characters, plus 2-3 hashtags")
    description: str = Field(..., description="Two English sentences")
    tags: List[str] = Field(..., description="6-8 English tags")
    pinned_comment: str = Field(..., description="An English question that invites debate")
    accent: str = Field(default="#00F0FF", description="Accent colour: always the channel electric cyan #00F0FF (or the channel blue #007AFF)")
    scenes: List[MotionSceneModel]
    fact_checked: bool = Field(default=True, description="Set by the pipeline; False when no model could run the fact-check")
    gemini_input_tokens: int = Field(default=0)
    gemini_output_tokens: int = Field(default=0)

    def to_props(self) -> dict:
        """The JSON the MotionGraphic composition receives as inputProps."""
        return {
            "title": self.screen_title,
            "theme": {"accent": self.accent, "background": "#05070C", "text": "#FFFFFF"},
            "scenes": [s.model_dump(exclude_none=True, exclude_defaults=False) for s in self.scenes],
        }

    @property
    def total_frames(self) -> int:
        return sum(s.durationInFrames for s in self.scenes)

    @property
    def all_text(self) -> str:
        parts = [self.title, self.description, self.pinned_comment, self.screen_title, " ".join(self.tags)]
        for s in self.scenes:
            parts += [s.text, s.accentText or "", s.kicker or "", s.unit or "", " ".join(s.items or [])]
        return " ".join(p for p in parts if p)


SYSTEM_PROMPT = """You write 20-45 second vertical motion-graphics explainers for the channel 'Silicon Verdict' (PC, hardware, coding and tech).
The video is pure kinetic typography on a deep obsidian background with electric-cyan and blue glow (the channel's blue palette), in the style of premium product reels: one big idea per scene, a single ACCENT word
in electric cyan (italic serif), smooth eased motion, counters, bars, code and a punchy outro. There is NO narrator: the words on screen tell the story.

LANGUAGE: everything (scene text, title, description, tags, comment) MUST be natural American English. Never any other language.
FACTS: only TRUE, verifiable statements; figures must be real and approximate (about / roughly) - never invent numbers.

STORY (8 to 11 scenes, 20-45 s in total, each scene 60-150 frames at 30 fps):
1. First scene: a hook (bigText or textWithAccent) that creates curiosity.
2. Then build the idea step by step, ONE idea per scene, using a variety of scene types:
   - bigText: 1-4 words, huge. textWithAccent: a short white line (max 7 words) + accentText (1-3 words, the emotional/key word).
   - counter: caption text + accentText, value = a REAL final number, optional unit.
   - list: heading text + 2-4 short items. codeBlock: 2-8 real, short code/shell lines + headline text. progressBar: caption + value 0-100 + unit.
   - curve: caption about acceleration / easing / growth. flash: ONE word on a full accent-coloured screen (use at most once, as a rhythm break).
3. Last scene: type outro, text = a punchy 1-3 word closer, accentText = a short call to action (e.g. Follow for more).
Rules: never repeat the same scene type back to back; at most one scene with light=true; text is short and readable in 2 seconds; no emojis.
Metadata: title <= 80 characters + 2-3 hashtags (#siliconverdict first), description 2 sentences, 6-8 tags, pinned_comment = a debate question.
screen_title <= 24 characters. accent = always #00F0FF (channel electric cyan)."""

_ES = re.compile(r"[ñ¿¡áéíóúü]|\b(el|la|los|las|de|del|que|para|con|una|uno|por|como|más|es|en|y)\b", re.I)
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


def _repair(p: MotionProject) -> None:
    """Fixes what can be fixed without asking again: clamps scene lengths, rescales the total into 20-45 s, trims overlong lists."""
    for s in p.scenes:
        s.durationInFrames = max(60, min(150, int(s.durationInFrames)))
        if s.items:
            s.items = s.items[:4]
        if s.code:
            s.code = [ln[:38] for ln in s.code[:8]]
        if s.value is not None and s.type == "progressBar":
            s.value = max(0.0, min(100.0, s.value))
    total = p.total_frames
    target = min(MAX_FRAMES - 15, max(MIN_FRAMES + 15, total))
    if total != target and total:
        k = target / total
        for s in p.scenes:
            s.durationInFrames = max(45, int(round(s.durationInFrames * k)))
    if (p.accent or "").upper() not in ("#00F0FF", "#007AFF"):  # the channel palette is blue/cyan: never any other colour
        p.accent = "#00F0FF"


def validate_project(p: MotionProject) -> List[str]:
    _repair(p)
    out: List[str] = []
    n = len(p.scenes)
    if not 7 <= n <= 12:
        out.append(f"{n} scenes (need 8-11)")
    if not MIN_FRAMES <= p.total_frames <= MAX_FRAMES:
        out.append(f"total {p.total_frames / FPS:.1f}s outside 20-45 s")
    if p.scenes and p.scenes[-1].type != "outro":
        out.append("the last scene must be type outro")
    if p.scenes and p.scenes[0].type not in ("bigText", "textWithAccent"):
        out.append("the first scene must be bigText or textWithAccent")
    if sum(1 for s in p.scenes if s.type == "flash") > 1:
        out.append("at most one flash scene")
    if sum(1 for s in p.scenes if s.light) > 1:
        out.append("at most one light scene")
    for i, s in enumerate(p.scenes, 1):
        limit = 4 if s.type == "bigText" else 7
        if len(s.text.split()) > limit:
            out.append(f"scene {i}: text longer than {limit} words")
        if s.accentText and len(s.accentText.split()) > 3:
            out.append(f"scene {i}: accentText longer than 3 words")
        if s.type == "counter" and (s.value is None or s.value <= 0):
            out.append(f"scene {i}: counter needs a positive value")
        if s.type == "progressBar" and s.value is None:
            out.append(f"scene {i}: progressBar needs value")
        if s.type == "list" and not (s.items and 2 <= len(s.items) <= 4):
            out.append(f"scene {i}: list needs 2-4 items")
        if s.type == "codeBlock" and not (s.code and len(s.code) >= 2):
            out.append(f"scene {i}: codeBlock needs 2+ code lines")
        if i > 1 and s.type == p.scenes[i - 2].type and s.type not in ("outro",):
            out.append(f"scenes {i - 1} and {i} have the same type")
    if not looks_english(p.all_text):
        out.append("the text is not English: everything must be American English")
    return out


class _Issue(BaseModel):
    scene: int
    problem: str
    definitely_wrong: bool


class _Review(BaseModel):
    errors: List[_Issue] = Field(default_factory=list)


def fact_check(p: MotionProject) -> List[str]:
    """Second pass: returns the blocking problems (false claims, clearly wrong figures). Raises GeminiUnavailable if no model answers."""
    lines = "\n".join(
        f"{i}. [{s.type}] {s.text} | accent: {s.accentText or '-'} | value: {s.value if s.value is not None else '-'}{s.unit or ''} | items: {s.items or '-'} | code: {s.code or '-'}"
        for i, s in enumerate(p.scenes, 1)
    )
    review, _t, model = generate_structured(
        prompt=f"Topic: {p.topic}\nScenes:\n{lines}\n\nFact-check this motion-graphics script.",
        system_instruction=("You are a strict but fair technical fact-checker. List in `errors` only statements that are clearly FALSE or misleading, or numbers that "
                            "are clearly wrong (check arithmetic). Simplifications for beginners are fine: mark definitely_wrong=false for those or leave them out. "
                            "Code lines must be valid and do what the scene says."),
        schema=_Review, temperature=0.1, provider_first="groq",
    )
    bad = [f"scene {e.scene}: {e.problem}" for e in review.errors if e.definitely_wrong]
    logger.info("Fact-check via %s: %d blocking issue(s).", model, len(bad))
    return bad


def generate_motion_project(topic: Optional[str] = None, avoid_topics: Optional[List[str]] = None, attempts: int = 3) -> MotionProject:
    """A validated, fact-checked project. Raises GeminiUnavailable when no provider answers, RuntimeError if every attempt fails the checks."""
    avoid = [t for t in (avoid_topics or []) if t][-25:]
    base = (f"Make a motion-graphics explainer about: {topic}\n" if topic
            else "Pick ONE fascinating idea about computers, hardware, coding, AI or tech that works well as animated typography (a surprising fact, a counter-intuitive mechanism, a tip).\n")
    if avoid:
        base += "Do NOT repeat or resemble these topics: " + "; ".join(avoid) + "\n"
    feedback = ""
    for attempt in range(1, attempts + 1):
        project, tokens, model = generate_structured(prompt=base + feedback + "Return a JSON object matching the schema.", system_instruction=SYSTEM_PROMPT,
                                                     schema=MotionProject, temperature=0.8, validate=validate_project)
        project.gemini_input_tokens, project.gemini_output_tokens = tokens
        try:
            problems = fact_check(project)
        except GeminiUnavailable as exc:
            logger.warning("Fact-check unavailable (%s): the video will not be uploaded automatically.", str(exc)[:100])
            project.fact_checked = False
            return project
        if not problems:
            logger.info("Motion project '%s' ready via %s: %d scenes, %.1f s.", project.topic, model, len(project.scenes), project.total_frames / FPS)
            return project
        logger.warning("Fact-check rejected attempt %d: %s", attempt, " | ".join(problems)[:300])
        feedback = "A previous attempt was rejected by the fact-checker for: " + "; ".join(problems) + ". Write a different, accurate script.\n"
    raise RuntimeError(f"{attempts} consecutive scripts failed the fact-check; nothing produced.")
