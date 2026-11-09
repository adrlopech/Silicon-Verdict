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
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from services.game_facts import figures_in
from services.gemini_client import GeminiUnavailable, generate_structured

STRONG_REVIEWERS = ["openai/gpt-oss-120b"]  # game claims are checked only by the strongest reviewer; if it is unavailable the video is held, not published

logger = logging.getLogger(__name__)

FPS = 30
from config.settings import settings as _settings
MIN_SECONDS, MAX_SECONDS = 62.0, _settings.MAX_VIDEO_SECONDS   # final video: > 60 s for monetisation, never more than the 3-minute ceiling (the script itself aims for 65-80 s)
MIN_FRAMES, MAX_FRAMES = int(MIN_SECONDS * FPS), int(MAX_SECONDS * FPS)
WORDS_PER_SECOND = 2.5                  # natural narration pace used to estimate the final length
CURSOR_ACTIONS = ("hover", "click", "select", "drag", "tab", "toggle", "busy")
TOGGLE_KEYS = ("airplane", "wifi", "bluetooth", "airdrop")
FX_NAMES = ("plane", "rocket", "satellite", "waves", "bolts", "embers", "snow", "drops", "packets", "coins", "equalizer", "signalbars", "notifications", "batteryfill", "clock", "padlock", "magnify", "bits")


def limit_cursor(scenes, fmt: Optional[str]) -> None:
    """The cursor only appears when it DOES something: the tab that opens the video, a drag on a list or code, a click on the reveal, a selection of the key phrase, a hover on a number.
    Keeps the most useful moments up to a small budget (4 in the everyday and fix-it formats, 3 elsewhere) and drops the decorative ones (waiting, loading, repeated clicks)."""
    budget = 4 if fmt in ("simple", "fix") else 3
    n = len(scenes)
    want = {"tab": [], "toggle": [], "drag": [], "click": [], "select": [], "hover": []}
    for i, sc in enumerate(scenes):
        if sc.cursor in want:
            want[sc.cursor].append(i)
    keep: list = []
    keep += (want["toggle"] or want["tab"])[:1]
    keep += want["drag"][:2]
    target = (2 * n) // 3  # the reveal sits in the last third
    keep += sorted(want["click"], key=lambda i: abs(i - target))[:1]
    keep += sorted(want["select"], key=lambda i: abs(i - n // 3))[:1]
    keep += [i for i in want["hover"] if scenes[i].type in ("counter", "progressBar")][:1]
    keep = sorted(set(keep[:budget]))
    if fmt == "simple" and len(keep) < 3:  # the everyday format is hosted by the cursor: give it a few more purposeful things to do
        for i, sc in enumerate(scenes):
            if len(keep) >= 3:
                break
            if i in keep or sc.type in ("flash", "footage", "outro") or any(abs(i - j) <= 2 for j in keep):
                continue
            act = {"counter": "hover", "progressBar": "drag", "list": "drag", "codeBlock": "drag", "textWithAccent": "select", "bigText": "click"}.get(sc.type)
            if act:
                sc.cursor = act
                keep.append(i)
    for i, sc in enumerate(scenes):
        if i not in keep:
            sc.cursor = None


def cursor_from_pose(pose: Optional[str], scene_type: str, index: int, total: int) -> Optional[str]:
    """Which cursor action fits a scene that used to carry a mascot pose (used when old scripts are moved to the cursor character)."""
    if not pose or scene_type in ("flash", "footage", "outro"):
        return None
    if index == 0:
        return "tab"  # the video opens a new browser tab
    if scene_type in ("list", "codeBlock", "progressBar", "tier"):
        return "drag"
    if scene_type in ("counter", "versus", "curve", "timeline"):
        return "hover"
    return {"surprised": "click", "cheer": "click", "point": "select"}.get(pose)


SceneType = Literal["bigText", "textWithAccent", "counter", "list", "codeBlock", "progressBar", "outro", "curve", "flash", "footage", "tier", "versus", "verdict", "timeline"]
FORMATS = ("myth", "tier", "whatif", "easter", "evolution", "versus", "hardware", "simple", "fix", "decode")   # content formats on top of the two kinds (curiosity / game); "easter" is always a game video; "hardware" and "simple" are the old Hardware / Everyday-with-mascot categories, now told in the Motion style; "fix" and "decode" come from the Nov 2026 niche research (notes/niche_research_2026-11.md)
TIER_LETTERS = ("S", "A", "B", "C", "D", "F")
# How often `--motion-format any` picks each topic. Our three TikTok breakouts (800+ views) were the number-driven formats (what-if, versus, evolution) and the niche research
# found "fix it now" and "decoded" to be the biggest unserved clusters; tier lists and myths stalled at the first test wave (notes/content_style_study_2026-11.md).
FORMAT_WEIGHTS = {"whatif": 3, "versus": 3, "evolution": 3, "fix": 3, "decode": 3, "hardware": 2, "simple": 1, "myth": 1, "tier": 1, "easter": 1, "classic": 1, "curiosity": 1, "game": 1}


class MotionSceneModel(BaseModel):
    type: SceneType
    text: str = Field(..., description="Main line, at most 7 words (bigText: at most 4). For 'footage': a 2-6 word callout naming the technical detail")
    accentText: Optional[str] = Field(default=None, description="ONE accent word or short phrase (max 3 words) shown in colour, italic serif")
    kicker: Optional[str] = Field(default=None, description="Optional tiny label above the text, 1-3 words")
    value: Optional[float] = Field(default=None, description="counter: final number (> 0); progressBar: percentage 0-100")
    unit: Optional[str] = Field(default=None, description="counter/progressBar suffix such as %, ms, GB")
    items: Optional[List[str]] = Field(default=None, description="list: 2-4 items of at most 5 words. tier: the board so far as \"S|label\" entries (tier letter S A B C D F, label at most 22 characters). timeline: 3-5 chronological \"year|label\" entries (label at most 28 characters)")
    left: Optional[str] = Field(default=None, description="versus: name of the left contender, at most 16 characters (the same in every versus scene)")
    right: Optional[str] = Field(default=None, description="versus: name of the right contender, at most 16 characters (the same in every versus scene)")
    leftValue: Optional[float] = Field(default=None, description="versus: the left contender's real, approximate figure for this scene's metric (> 0); `unit` is shared by both")
    rightValue: Optional[float] = Field(default=None, description="versus: the right contender's real, approximate figure for the same metric (> 0)")
    winner: Optional[Literal["left", "right", "none"]] = Field(default=None, description="versus: who wins this round; leave empty when the BIGGER figure wins, set it when lower is better")
    verdict: Optional[Literal["myth", "fact", "partly"]] = Field(default=None, description="verdict scenes only: is the claim a myth, a fact or partly true")
    code: Optional[List[str]] = Field(default=None, description="codeBlock: 2-8 short real code or shell lines (max 38 characters each)")
    light: bool = Field(default=False, description="Light background variant, use for at most one scene")
    mediaId: Optional[str] = Field(default=None, description="footage scenes only: the id of ONE item of the footage list; never reuse an id")
    mediaSrc: Optional[str] = Field(default=None, description="Set by the pipeline, never by the model")
    mediaKind: Optional[str] = Field(default=None, description="Set by the pipeline, never by the model")
    mediaSeconds: Optional[float] = Field(default=None, description="Set by the pipeline, never by the model")
    credit: Optional[str] = Field(default=None, description="Set by the pipeline, never by the model")
    evidence: Optional[str] = Field(default=None, description="GAME videos only: a VERBATIM quote (6-30 words) copied from the SOURCE TEXT that supports this scene's claim about the game; empty if the scene makes no claim about the game")
    fx: Optional[str] = Field(default=None, description="An animated element that illustrates the line (plane, rocket, satellite, waves, bolts, embers, snow, drops, packets, coins, equalizer). Optional: it is picked automatically from the scene's words when empty")
    toggle: Optional[str] = Field(default=None, description="With cursor=toggle: the switch of the Control Center panel the cursor flips: airplane, wifi, bluetooth or airdrop")
    cursor: Optional[str] = Field(default=None, description="The mouse-cursor character acts in this scene: click (presses the key text), hover (rests on it), select (drags across the headline like selecting text), drag (grabs a list item, code panel or bar), tab (opens a browser tab: only on the first scene), toggle (opens a macOS Control Center panel and flips a switch: only on the first scene, only for videos about a phone/computer setting), busy (loading ring), Empty = no cursor in this scene")
    icons: Optional[List[str]] = Field(default=None, description="1-3 thematic objects floating around the text, chosen from: chip gpu ram battery bolt wifi globe cloud server disk lock key shield thermometer flame fan gauge clock code brain bulb dollar skull warning controller monitor phone camera wave planet rocket atom magnet droplet snow heart search check cross gear star net arrow. Pick what the scene is ABOUT; leave empty to let the renderer choose from the words")
    narration: str = Field(default="", description="What the narrator SAYS during this scene: one or two natural spoken sentences, 8-16 words, that explain the idea on screen")
    durationInFrames: int = Field(..., description="Minimum scene length in frames at 30 fps (60-150); the pipeline stretches it to fit the narration")


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
(for example "sixteen point seven milliseconds"). The narrations are ONE continuous monologue, not separate captions: each line picks up from the previous one and flows into the next, opening with a connective such as "So", "And", "But", "Here's the thing", "That's why", "Now" or "Which means" (never a stand-alone fact, and never the same opener twice in a row), with questions answered in the following line. The last scene's narration ends with a short call to action such as "Follow for more tech."

LANGUAGE: everything (scene text, narration, title, description, tags, comment) MUST be natural American English. Never any other language.
FACTS: only TRUE, verifiable statements; figures must be real and approximate (about / roughly) - never invent numbers.

STORY (11 to 19 scenes, aim for 13+, each 60-150 frames at 30 fps):
1. First scene: a COLD OPEN hook (bigText or textWithAccent), see the RETENTION RULES at the end.
2. Then build the idea step by step, ONE idea per scene, using a variety of scene types:
   - bigText: 1-4 words, huge. textWithAccent: a short white line (max 7 words) + accentText (1-3 words, the emotional/key word).
   - counter: caption text + accentText, value = a REAL final number > 0, optional unit.
   - list: heading text + 2-4 short items. codeBlock: 2-8 real, short code/shell lines + headline text. progressBar: caption + value 0-100 + unit.
   - curve: caption about acceleration / easing / growth. flash: ONE word on a full accent-coloured screen (use at most once, as a rhythm break).
3. Last scene: type outro, text = a punchy 1-3 word closer, accentText = a short call to action (e.g. Follow for more).
Every scene except footage/flash/tier/timeline/versus/verdict floats 1-3 eye-catching `icons` (neon objects) that visually match what that scene is about
(e.g. a scene on heat: thermometer, flame, fan; on speed: gauge, bolt). Always fill `icons` for scenes about a concrete thing.
Rules: never repeat the same scene type back to back (footage scenes may follow each other); at most one scene with light=true; on-screen text is short and
readable in 2 seconds; no emojis.
CURSOR (optional, use it SPARINGLY): the channel's character is a MOUSE CURSOR that uses the screen like a person uses a web page. It appears only when it does something that helps the line; never as decoration, never waiting.
Set `cursor` on a scene only for: tab (opens a new browser tab: ONLY the first scene, as the video opens), toggle (ONLY the first scene and ONLY when the whole video is about a phone or computer setting such as airplane mode: opens a macOS-style Control Center panel and flips the switch named in `toggle`: airplane, wifi, bluetooth or airdrop; it replaces `tab`), drag (grabs a list item, code panel or bar: list, codeBlock, progressBar scenes), click (presses the key text: THE reveal or payoff, once),
select (drags across the headline like selecting text: one key phrase), hover (rests on a key number), busy (a loading ring: at most once, for a real "working it out" beat). Never on flash scenes. At most 4 scenes per video, usually 2 or 3.
On-screen effects appear automatically when the narration names them, each only once or rarely: plane/rocket/satellite fly-bys, signal waves and bars, lightning, embers, snow, drops, data packets, coins, equalizer, notification banners, a filling battery, a clock, a padlock, a magnifier, binary rain. Set `fx` only to force one.
Metadata: title <= 80 characters + 2-3 hashtags (#siliconverdict first), description 2 sentences, 6-8 tags, pinned_comment = the two-option vote of the outro.
screen_title <= 24 characters. accent = always #00F0FF (channel electric cyan)."""

RETENTION_RULES = """
RETENTION RULES (they decide whether people keep watching; the validator checks them):
- COLD OPEN. Scene 1 is the claim that breaks a belief, or the most surprising number, said in at most 14 words with NO context before it. Never open with a greeting, "today", "in this video",
  "did you know", "have you ever wondered", "let's" or a definition. Example: "Your three nanometer chip has no three nanometer part inside." When a figure or a contrast makes the claim stronger, show it in scene 1 or 2.
- OPEN LOOP. In scene 2, 3, 4 or 5 the narration promises something that comes later ("And the last reason is the one nobody checks.", "Stay to the end, the last step matters most.",
  "But the real catch comes in a moment."). Pay it off in the last third, before the outro, with a scene that clearly delivers it. Never promise something the video does not deliver.
- PATTERN BREAK. Never more than two headline scenes (bigText / textWithAccent) in a row: break the rhythm with a counter, list, codeBlock, progressBar, curve, flash or footage scene at least every third scene.
- VOTE. The outro narration ends with a TWO-OPTION question the viewer can answer in one word ("Would you buy it, or skip it?", "Team DDR4 or team DDR5?") and `pinned_comment` repeats the SAME choice
  as "A or B? Reply with one word." (at most 120 characters). Never an open question such as "What do you think?"."""

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
- The narration of each tier scene names the NEW item and justifies its tier with a TRUE, concrete reason (a figure or a mechanism). Use the full range: at least 4 different tiers in the final board.
- Structure: hook (bigText), 6 to 8 tier scenes, one textWithAccent that gives the surprise or the lesson, outro.""",
    "whatif": FORMAT_COMMON + """
FORMAT = WHAT IF. One absurd but physically meaningful hypothetical about computing ("What if your PC had no cache?", "What if an SSD never erased data?", "What if RAM was as slow as a hard drive?").
- Scene 1: bigText with kicker "what if" and the hypothetical in 2-4 words. Scene 2 restates it as a question in textWithAccent.
- Then walk through the consequences step by step, ESCALATING each time, alternating the scene types (never two of the same type in a row), with real mechanisms and real approximate figures (counter, progressBar, curve, list, codeBlock). Say "roughly" when a figure is approximate.
- The consequences must follow from how the hardware or software really works; never invent figures. Close with what the real design does to avoid this, and why that is clever.""",
    "evolution": FORMAT_COMMON + """
FORMAT = EVOLUTION. How ONE thing evolved over time (GPUs, storage, CPUs, game graphics, memory, the web...).
- Use at least 2 `timeline` scenes: `items` = 3 to 5 chronological "year|label" entries, each year EXACTLY four digits ("1999", never "1990s" or "late 90s"; label at most 28 characters), only milestones you are SURE about, with the exact year. `kicker` = "evolution".
- Between timeline scenes use counter, progressBar or curve scenes that show the growth (transistors, capacity, price, speed) with real, approximate figures spoken in the narration.
- Hook with the span ("Thirty years of storage in sixty seconds"), end with what the trend means for the future.""",
    "versus": FORMAT_COMMON + """
FORMAT = VERSUS. Two contenders (two consoles, two technologies, two standards) fought over 3 to 5 ROUNDS, each round one `versus` scene about ONE metric.
- `left` and `right` = the contender names (max 16 characters, IDENTICAL in every round), `leftValue` / `rightValue` = real approximate positive figures for that metric, `unit` shared by both,
  `text` = the metric ("Memory bandwidth"), `accentText` = a short tag ("per second"), `kicker` = "round 1", "round 2"... When LOWER is better (latency, price, power) set `winner` to the contender that wins.
  Both figures MUST be spoken in that scene's narration (digits are fine: "twenty-five point six versus forty-eight"). If you are not sure of a figure, pick another metric.
- Scene 1 is the hook that names both contenders, the last scene before the outro is a textWithAccent that names the overall winner and the catch ("but it depends on...").""",
    "hardware": FORMAT_COMMON + """
FORMAT = HARDWARE DEEP DIVE (the old Hardware category, now in the Motion style). ONE surprising, well documented fact about silicon, memory, storage, networking, displays, power or engineering infrastructure
(cache and RAM latency, EUV lithography, why clocks stalled near 5 GHz, SSD wear, GPS and atomic clocks, fiber optics, thermal paste, power supplies, GPUs versus CPUs, ECC memory, data centers...).
- Explain HOW it really works: the mechanism first, then the real approximate figures (counter, progressBar, codeBlock, curve scenes are the evidence); physics and engineering, never opinions or benchmarks you cannot be sure of.
- Cursor: only as an accent, in 2 or 3 scenes: `tab` on the hook, plus `drag` on a list or code scene or `click` on the reveal (only where it helps).""",
    "simple": FORMAT_COMMON + """
FORMAT = EVERYDAY TECH MYSTERY (the old Everyday category, now in the Motion style, hosted by the mouse cursor). A small, relatable mystery almost everyone has lived but few can explain:
USB plugs, Bluetooth and Wi-Fi quirks, batteries and charging, touchscreens, cameras, QR codes, GPS, headphones, microwaves, passwords, e-readers, smart homes, airplane mode...
- Friendly, conversational, with an analogy and a twist ("But there is more."); the closing line loops back to the hook.
- Cursor: the mouse cursor is the host, but it acts only when it helps the line: `tab` on the hook, `select` on one key phrase, `drag` on a list or code scene, `click` on the reveal, `hover` on a key number. 3 or 4 scenes in all, never idle, never decorative.""",
    "fix": FORMAT_COMMON + """
FORMAT = FIX IT NOW. A symptom almost everyone has felt (a slow PC, stutter, a washed-out monitor, high ping, loud fans, a battery that drains, a blurry screen) fixed with ONE concrete setting or habit.
- Scene 1 (bigText or textWithAccent) is the symptom as the viewer feels it ("Your PC feels slow?"). Scene 2 gives the real cause in one line: what is actually happening.
- Then the fix in 2 or 3 steps. Each step names the EXACT place: a `codeBlock` whose 2-6 lines are the menu path or the command ("Settings > System > Display"), and a `list` of the steps. At least one codeBlock and one list.
- The mouse cursor is the hand that does the fix: `click`, `select` or `drag` on 2 to 4 scenes (the steps, the setting, the payoff). Never idle, never decorative.
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


def _repair(p: MotionProject) -> None:
    """Fixes what can be fixed without asking again: clamps scene lengths, trims overlong lists/code, forces the brand accent."""
    for s in p.scenes:
        s.durationInFrames = max(60, min(150, int(s.durationInFrames)))
        if s.items:
            s.items = s.items[:{"tier": 10, "timeline": 5}.get(s.type, 4)]
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


def _format_problems(p: MotionProject, fmt: Optional[str]) -> List[str]:
    """Checks of the format's own scene types (tier boards, versus rounds, verdict stamps, timelines), whatever the format of the video."""
    out: List[str] = []
    sc = p.scenes
    tiers = [(i, s) for i, s in enumerate(sc, 1) if s.type == "tier"]
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
    for i, s in enumerate(sc, 1):
        if s.type == "versus":
            if not (s.left and s.right and len(s.left) <= 16 and len(s.right) <= 16):
                out.append(f"scene {i}: versus needs `left` and `right` names of at most 16 characters")
            if not (s.leftValue and s.rightValue and s.leftValue > 0 and s.rightValue > 0):
                out.append(f"scene {i}: versus needs positive leftValue and rightValue")
            elif not (_said(s.leftValue, s.narration) or _said(s.rightValue, s.narration)):
                out.append(f"scene {i}: the versus figures must be said in that scene's narration (no decorative figures)")
        elif s.type == "verdict":
            if not s.verdict:
                out.append(f"scene {i}: verdict scenes need `verdict` (myth, fact or partly)")
            if not (s.accentText or "").strip():
                out.append(f"scene {i}: a verdict scene needs accentText: the one-line truth shown under the stamp")
            if s.accentText and len(s.accentText.split()) > 6:
                out.append(f"scene {i}: a verdict's accentText is at most 6 words")
        elif s.type == "timeline":
            rows = [it.split("|", 1) for it in (s.items or []) if "|" in it]
            years = [r[0].strip() for r in rows]
            if not (3 <= len(s.items or []) <= 5) or len(rows) != len(s.items or []) or not all(re.fullmatch(r"\d{4}", y) for y in years):
                out.append(f"scene {i}: timeline needs 3-5 \"year|label\" items with a four-digit year")
            elif years != sorted(years):
                out.append(f"scene {i}: timeline years must be in chronological order")
            elif any(len(r[1].strip()) > 28 for r in rows):
                out.append(f"scene {i}: timeline labels are at most 28 characters")
    lefts = {(s.left or "").strip().lower() for s in sc if s.type == "versus"}
    rights = {(s.right or "").strip().lower() for s in sc if s.type == "versus"}
    if len(lefts) > 1 or len(rights) > 1:
        out.append("the versus contenders must have the SAME names in every round")
    count = lambda t: sum(1 for s in sc if s.type == t)
    if fmt == "myth":
        v = [s.verdict for s in sc if s.type == "verdict"]
        if len(v) < 4:
            out.append(f"myth format needs 4-5 verdict scenes, got {len(v)}")
        if v.count("myth") < 2 or not (v.count("fact") + v.count("partly")):
            out.append("mix the verdicts: at least 2 myths and at least 1 fact or partly")
    elif fmt == "tier":
        if not 6 <= len(tiers) <= 9:
            out.append(f"tier format needs 6-9 tier scenes (one per item), got {len(tiers)}")
        elif len({it.split("|", 1)[0].strip().upper() for it in (tiers[-1][1].items or []) if "|" in it}) < 4:
            out.append("the final tier board must use at least 4 different tiers")
    elif fmt == "evolution":
        if count("timeline") < 2:
            out.append("evolution format needs at least 2 timeline scenes")
    elif fmt == "versus":
        if not 3 <= count("versus") <= 5:
            out.append(f"versus format needs 3-5 versus scenes (rounds), got {count('versus')}")
    elif fmt == "whatif":
        if sum(count(t) for t in ("counter", "progressBar", "curve", "list", "codeBlock")) < 3:
            out.append("what-if format needs at least 3 consequence scenes (counter, progressBar, curve, list or codeBlock)")
    if fmt in ("fix", "decode"):
        if not count("codeBlock"):
            out.append(f"{fmt} format needs a codeBlock scene ({'the exact menu path or command' if fmt == 'fix' else 'the label broken into its parts'})")
        if not count("list"):
            out.append(f"{fmt} format needs a list scene ({'the steps' if fmt == 'fix' else 'what each part tells you'})")
    if fmt not in ("myth", "tier", "versus", "evolution") and (tiers or count("versus") or count("verdict") or count("timeline")):
        out.append("tier / versus / verdict / timeline scenes belong only to their own format")
    if fmt == "myth" and (tiers or count("versus") or count("timeline")):
        out.append("a myth video uses only verdict scenes among the format scenes")
    if fmt == "tier" and (count("versus") or count("verdict") or count("timeline")):
        out.append("a tier video uses only tier scenes among the format scenes")
    if fmt == "versus" and (tiers or count("verdict") or count("timeline")):
        out.append("a versus video uses only versus scenes among the format scenes")
    if fmt == "evolution" and (tiers or count("versus") or count("verdict")):
        out.append("an evolution video uses only timeline scenes among the format scenes")
    return out


BAD_OPENER = re.compile(r"^\W*(so\b|welcome|hey\b|hi\b|hello|today|in this video|did you know|have you ever|do you know|let'?s|ever wonder)", re.I)
OPEN_LOOP = re.compile(
    r"\b(wait for|stay (?:to|till|until|for|with)|by the end|until the end|in a moment|in a second|before we (?:finish|end)|later on|catch|twist|nobody|no one|most people|secret|"
    r"gets (?:worse|weirder|stranger|better)|the (?:last|final|third|second|next) (?:one|reason|part|step|round|rule|trick)|you will not believe|that is not even|that is not the)\b", re.I)
HEADLINE = ("bigText", "textWithAccent")
HOOK_MAX_WORDS = 16  # the prompt asks for 14; two more words of tolerance


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
    if not (re.search(r"\bor\b", p.pinned_comment) and "?" in p.pinned_comment) or len(p.pinned_comment) > 120:
        out.append("pinned_comment must be the same two-option vote (\"A or B? Reply with one word.\"), at most 120 characters")
    run = 0
    for i, s in enumerate(p.scenes, 1):
        run = run + 1 if s.type in HEADLINE else 0
        if run > 2:
            out.append(f"scenes {i - 2}-{i} are three headline scenes in a row: break the rhythm with a counter, list, codeBlock, progressBar, curve or flash scene")
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
        if sum(1 for s in p.scenes if s.type == "flash") > 1:
            out.append("at most one flash scene")
        if sum(1 for s in p.scenes if s.light) > 1:
            out.append("at most one light scene")
        for sc_ in p.scenes:  # an unknown action or effect is simply dropped, the scene stays
            act = (sc_.cursor or "").strip().lower()
            sc_.cursor = act if act in CURSOR_ACTIONS and sc_.type not in ("flash", "footage") else None
            if sc_.cursor == "drag" and sc_.type not in ("list", "codeBlock", "progressBar", "tier"):
                sc_.cursor = "hover"
            fx_ = (sc_.fx or "").strip().lower()
            sc_.fx = fx_ if fx_ in FX_NAMES else None
        for sc_ in p.scenes:
            tg = (sc_.toggle or "").strip().lower()
            sc_.toggle = tg if tg in TOGGLE_KEYS else None
            if sc_.cursor == "toggle" and not sc_.toggle:
                sc_.toggle = "airplane"
            if sc_.cursor != "toggle":
                sc_.toggle = None
        openers = [i for i, sc_ in enumerate(p.scenes) if sc_.cursor in ("tab", "toggle")]  # a tab or a settings panel opens only as the video starts
        for i in openers:
            if i != 0 or i != openers[0]:
                p.scenes[i].cursor, p.scenes[i].toggle = "click", None
        busy = [i for i, sc_ in enumerate(p.scenes) if sc_.cursor == "busy"]
        for i in busy[1:]:
            p.scenes[i].cursor = None
        if sum(1 for sc_ in p.scenes if sc_.cursor) > 4:
            limit_cursor(p.scenes, fmt)  # a generation that over-uses the cursor is trimmed to its most useful moments instead of being rejected
        cursor_acts = [sc_.cursor for sc_ in p.scenes if sc_.cursor]
        if fmt == "fix" and len(cursor_acts) < 2:
            out.append("fix format needs the cursor on at least 2 scenes (click, select or drag): it is the hand that does the fix")
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
            limit = 4 if s.type == "bigText" else 7
            if len(s.text.split()) > limit and s.type != "footage":
                out.append(f"scene {i}: text longer than {limit} words")
            if s.type == "footage" and (len(s.text.split()) > 7 or not s.mediaId):
                out.append(f"scene {i}: footage needs a mediaId and a callout of at most 6 words")
            if s.accentText and len(s.accentText.split()) > (6 if s.type == "verdict" else 3):
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
            if i > 1 and s.type == p.scenes[i - 2].type and s.type not in ("outro", "footage", "tier", "versus", "verdict", "timeline"):
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
    if kind == "game":
        lines = "\n".join(f"  * id={k} [{e['kind']}] {e['caption']}" for k, e in (catalog or {}).items())
        system += (GAME_RULES.format(game=game, catalog=lines, facts=facts) if facts else GAME_RESTRICTIVE.format(game=game, catalog=lines))
        base = f"Make a motion-graphics video about an engineering fact of the game {game}" + (f", specifically: {topic}" if topic else "") + ".\n"
    else:
        system += CURIOSITY_RULES
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
