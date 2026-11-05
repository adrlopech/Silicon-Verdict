"""Series 6 - Motion Graphics: kinetic-typography explainers, 62-84 s (YouTube monetisation needs MORE than 60 s), vertical 1080x1920, always English.

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
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from services.game_facts import figures_in
from services.gemini_client import GeminiUnavailable, generate_structured

STRONG_REVIEWERS = ["openai/gpt-oss-120b"]  # game claims are checked only by the strongest reviewer; if it is unavailable the video is held, not published

logger = logging.getLogger(__name__)

FPS = 30
MIN_SECONDS, MAX_SECONDS = 62.0, 84.0   # final video: > 60 s for monetisation, short enough to hold attention
MIN_FRAMES, MAX_FRAMES = int(MIN_SECONDS * FPS), int(MAX_SECONDS * FPS)
WORDS_PER_SECOND = 2.5                  # natural narration pace used to estimate the final length
SceneType = Literal["bigText", "textWithAccent", "counter", "list", "codeBlock", "progressBar", "outro", "curve", "flash", "footage"]


class MotionSceneModel(BaseModel):
    type: SceneType
    text: str = Field(..., description="Main line, at most 7 words (bigText: at most 4). For 'footage': a 2-6 word callout naming the technical detail")
    accentText: Optional[str] = Field(default=None, description="ONE accent word or short phrase (max 3 words) shown in colour, italic serif")
    kicker: Optional[str] = Field(default=None, description="Optional tiny label above the text, 1-3 words")
    value: Optional[float] = Field(default=None, description="counter: final number (> 0); progressBar: percentage 0-100")
    unit: Optional[str] = Field(default=None, description="counter/progressBar suffix such as %, ms, GB")
    items: Optional[List[str]] = Field(default=None, description="list: 2-4 items of at most 5 words")
    code: Optional[List[str]] = Field(default=None, description="codeBlock: 2-8 short real code or shell lines (max 38 characters each)")
    light: bool = Field(default=False, description="Light background variant, use for at most one scene")
    mediaId: Optional[str] = Field(default=None, description="footage scenes only: the id of ONE item of the footage list; never reuse an id")
    mediaSrc: Optional[str] = Field(default=None, description="Set by the pipeline, never by the model")
    mediaKind: Optional[str] = Field(default=None, description="Set by the pipeline, never by the model")
    mediaSeconds: Optional[float] = Field(default=None, description="Set by the pipeline, never by the model")
    credit: Optional[str] = Field(default=None, description="Set by the pipeline, never by the model")
    evidence: Optional[str] = Field(default=None, description="GAME videos only: a VERBATIM quote (6-30 words) copied from the SOURCE TEXT that supports this scene's claim about the game; empty if the scene makes no claim about the game")
    narration: str = Field(default="", description="What the narrator SAYS during this scene: one or two natural spoken sentences, 8-16 words, that explain the idea on screen")
    durationInFrames: int = Field(..., description="Minimum scene length in frames at 30 fps (60-150); the pipeline stretches it to fit the narration")


class MotionProject(BaseModel):
    topic: str
    screen_title: str = Field(..., description="Short title shown in the HUD, at most 24 characters")
    title: str = Field(..., max_length=100, description="YouTube title in English, at most 80 characters, plus 2-3 hashtags")
    description: str = Field(..., description="Two English sentences")
    tags: List[str] = Field(..., description="6-8 English tags")
    pinned_comment: str = Field(..., description="An English question that invites debate")
    accent: str = Field(default="#00F0FF", description="Accent colour: always the channel electric cyan #00F0FF (or the channel blue #007AFF)")
    scenes: List[MotionSceneModel]
    kind: str = Field(default="curiosity", description="Set by the pipeline: curiosity | game")
    game: Optional[str] = Field(default=None, description="Set by the pipeline for game videos")
    fact_checked: bool = Field(default=True, description="Set by the pipeline; False when no model could run the fact-check")
    gemini_input_tokens: int = Field(default=0)
    gemini_output_tokens: int = Field(default=0)

    def to_props(self) -> dict:
        """The JSON the MotionGraphic composition receives as inputProps."""
        return {
            "title": self.screen_title,
            "theme": {"accent": self.accent, "background": "#05070C", "text": "#FFFFFF"},
            "scenes": [s.model_dump(exclude_none=True) for s in self.scenes],
        }

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
            parts += [s.text, s.accentText or "", s.kicker or "", s.unit or "", " ".join(s.items or []), s.narration]
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
(for example "sixteen point seven milliseconds"). The last scene's narration ends with a short call to action such as "Follow for more tech."

LANGUAGE: everything (scene text, narration, title, description, tags, comment) MUST be natural American English. Never any other language.
FACTS: only TRUE, verifiable statements; figures must be real and approximate (about / roughly) - never invent numbers.

STORY (13 to 19 scenes, each 60-150 frames at 30 fps):
1. First scene: a hook (bigText or textWithAccent) that creates curiosity.
2. Then build the idea step by step, ONE idea per scene, using a variety of scene types:
   - bigText: 1-4 words, huge. textWithAccent: a short white line (max 7 words) + accentText (1-3 words, the emotional/key word).
   - counter: caption text + accentText, value = a REAL final number > 0, optional unit.
   - list: heading text + 2-4 short items. codeBlock: 2-8 real, short code/shell lines + headline text. progressBar: caption + value 0-100 + unit.
   - curve: caption about acceleration / easing / growth. flash: ONE word on a full accent-coloured screen (use at most once, as a rhythm break).
3. Last scene: type outro, text = a punchy 1-3 word closer, accentText = a short call to action (e.g. Follow for more).
Rules: never repeat the same scene type back to back (footage scenes may follow each other); at most one scene with light=true; on-screen text is short and
readable in 2 seconds; no emojis.
Metadata: title <= 80 characters + 2-3 hashtags (#siliconverdict first), description 2 sentences, 6-8 tags, pinned_comment = a debate question.
screen_title <= 24 characters. accent = always #00F0FF (channel electric cyan)."""

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
    """Fixes what can be fixed without asking again: clamps scene lengths, trims overlong lists/code, forces the brand accent."""
    for s in p.scenes:
        s.durationInFrames = max(60, min(150, int(s.durationInFrames)))
        if s.items:
            s.items = s.items[:4]
        if s.code:
            s.code = [ln[:38] for ln in s.code[:8]]
        if s.value is not None and s.type == "progressBar":
            s.value = max(0.0, min(100.0, s.value))
        if s.type != "footage":
            s.mediaId = None
        if len(s.narration.split()) < 3 and s.type in ("flash", "bigText", "outro"):  # a one-word punch scene may simply speak its own text
            s.narration = " ".join(x for x in (s.text, s.accentText) if x)
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


def make_validator(catalog: Optional[Dict[str, dict]] = None, facts: Optional[str] = None):
    """Validator for generate_structured. `catalog` (media id -> entry) and `facts` (source dossier) are given for game videos."""
    known = figures_in(facts) if facts else None
    norm_facts = _norm(facts) if facts else None
    def validate_project(p: MotionProject) -> List[str]:
        _repair(p)
        out: List[str] = []
        n = len(p.scenes)
        if not 12 <= n <= 21:
            out.append(f"{n} scenes (need 13-19)")
        words, est = p.narration_words, estimated_seconds(p)
        if any(len(s.narration.split()) < 3 for s in p.scenes):
            out.append("every scene needs a narration (3-16 words; short is fine for a one-word flash scene)")
        if any(len(s.narration.split()) > 20 for s in p.scenes):
            out.append("a scene narration is longer than 20 words")
        if not MIN_SECONDS + 1 <= est <= MAX_SECONDS:
            out.append(f"narration has {words} words across {n} scenes (about {est:.0f} s): it must come to {MIN_SECONDS + 1:.0f}-{MAX_SECONDS:.0f} s (roughly 150-190 words, about 11 per scene)")
        if p.scenes and p.scenes[-1].type != "outro":
            out.append("the last scene must be type outro")
        if p.scenes and p.scenes[0].type not in ("bigText", "textWithAccent"):
            out.append("the first scene must be bigText or textWithAccent")
        if sum(1 for s in p.scenes if s.type == "flash") > 1:
            out.append("at most one flash scene")
        if sum(1 for s in p.scenes if s.light) > 1:
            out.append("at most one light scene")
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
            limit = 4 if s.type == "bigText" else 7
            if len(s.text.split()) > limit and s.type != "footage":
                out.append(f"scene {i}: text longer than {limit} words")
            if s.type == "footage" and (len(s.text.split()) > 7 or not s.mediaId):
                out.append(f"scene {i}: footage needs a mediaId and a callout of at most 6 words")
            if s.accentText and len(s.accentText.split()) > 3:
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
            if i > 1 and s.type == p.scenes[i - 2].type and s.type not in ("outro", "footage"):
                out.append(f"scenes {i - 1} and {i} have the same type")
        if not looks_english(p.all_text):
            out.append("the text is not English: everything must be American English")
        return out
    return validate_project


class _Issue(BaseModel):
    scene: int
    problem: str
    definitely_wrong: bool
    fixed_narration: Optional[str] = Field(default=None, description="For a definitely_wrong issue: a replacement narration for that scene (8-16 words) that is TRUE and, for footage scenes, mentions only what the footage visibly shows")


class _Review(BaseModel):
    errors: List[_Issue] = Field(default_factory=list)


def _review_prompt(p: MotionProject, catalog, facts):
    rows = []
    for i, s in enumerate(p.scenes, 1):
        shows = f" | FOOTAGE SHOWS: {catalog[s.mediaId]['caption']}" if catalog and s.type == "footage" and s.mediaId in catalog else ""
        ev = f" | EVIDENCE QUOTE: \"{s.evidence}\"" if s.evidence else ""
        rows.append(f"{i}. [{s.type}] {s.text} | narration: \"{s.narration}\" | accent: {s.accentText or '-'} | value: {s.value if s.value is not None else '-'}{s.unit or ''} | items: {s.items or '-'} | code: {s.code or '-'}{shows}{ev}")
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
    system = ("You are a strict but fair technical fact-checker. List in `errors` only statements that are clearly FALSE or misleading, or numbers that are clearly wrong "
              "(check arithmetic). Simplifications for beginners are fine: mark definitely_wrong=false for those or leave them out. Code lines must be valid and do what the scene "
              "says. For every definitely_wrong issue also give fixed_narration." + game_rule + footage_rule)
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
            review, _t, model = generate_structured(**kw, provider_first="groq", provider_models=STRONG_REVIEWERS, strict_provider=True)
            bad = [e for e in review.errors if e.definitely_wrong]
            logger.info("Fact-check via %s: %d blocking issue(s).", model, len(bad))
            return bad
        except GeminiUnavailable as exc:
            logger.warning("Strong reviewer unavailable (%s)%s", str(exc)[:100], "; retrying in 25 s." if attempt == 1 else ".")
            if attempt == 1:
                time.sleep(25)
    merged: Dict[tuple, _Issue] = {}
    answered: List[str] = []
    panel = [dict(provider_first="groq", provider_models=["openai/gpt-oss-20b"], strict_provider=True),
             dict(provider_first="cloudflare", provider_models=["@cf/openai/gpt-oss-120b"], strict_provider=True),
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
        if e.fixed_narration and 1 <= e.scene <= len(p.scenes) and 3 <= len(e.fixed_narration.split()) <= 20:
            p.scenes[e.scene - 1].narration = e.fixed_narration.strip()
            done += 1
    return done


def generate_motion_project(topic: Optional[str] = None, avoid_topics: Optional[List[str]] = None, kind: str = "curiosity",
                            game: Optional[str] = None, catalog: Optional[Dict[str, dict]] = None, facts: Optional[str] = None, attempts: int = 3) -> MotionProject:
    """A validated, fact-checked project. For kind='game' pass the chosen `game` and its footage `catalog` (id -> entry).
    Raises GeminiUnavailable when no provider answers, RuntimeError if every attempt fails the checks."""
    avoid = [t for t in (avoid_topics or []) if t][-25:]
    system = SYSTEM_PROMPT
    if kind == "game":
        lines = "\n".join(f"  * id={k} [{e['kind']}] {e['caption']}" for k, e in (catalog or {}).items())
        system += (GAME_RULES.format(game=game, catalog=lines, facts=facts) if facts else GAME_RESTRICTIVE.format(game=game, catalog=lines))
        base = f"Make a motion-graphics video about an engineering fact of the game {game}" + (f", specifically: {topic}" if topic else "") + ".\n"
    else:
        system += CURIOSITY_RULES
        base = (f"Make a motion-graphics explainer about: {topic}\n" if topic
                else "Pick ONE fascinating idea about computers, hardware, coding, AI or tech that works well as animated typography (a surprising fact, a counter-intuitive mechanism, a tip).\n")
    if avoid:
        base += "Do NOT repeat or resemble these topics: " + "; ".join(avoid) + "\n"
    feedback = ""
    for attempt in range(1, attempts + 1):
        project, tokens, model = generate_structured(prompt=base + feedback + "Return a JSON object matching the schema.", system_instruction=system, schema=MotionProject,
                                                     temperature=0.8, validate=make_validator(catalog if kind == "game" else None, facts), max_output_tokens=12000, max_passes=3)
        project.kind, project.game = kind, (game if kind == "game" else None)
        project.gemini_input_tokens, project.gemini_output_tokens = tokens
        validator = make_validator(catalog if kind == "game" else None, facts)
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
