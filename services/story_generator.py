"""Mascot-led story videos ('simple' series): natural spoken script + scenes built from animated primitives."""
import logging
import re
from typing import List, Optional

from core.schemas import StoryProject, StoryScene
from services.gemini_client import generate_structured

logger = logging.getLogger(__name__)

VALID_POSES = {"idle", "surprised", "point", "shrug", "think", "wave", "cheer"}
VALID_VECTORS = {"none", "counter", "bars", "gauge", "trio", "flow", "icon", "big_text"}
ICON_NAMES = [
    "bulb", "mirror", "clock", "building", "phone", "wifi", "chip", "battery", "cable", "eye",
    "smile", "lock", "bolt", "cloud", "magnifier", "gear", "heart", "arrow", "question", "star",
    "box", "plane", "wave", "thermometer", "drop", "hand", "fire", "sun",
]
ICON_ALIASES = {"water": "drop", "raindrop": "drop", "finger": "hand", "touch": "hand", "heat": "fire", "flame": "fire", "temperature": "thermometer", "light": "bulb", "signal": "wifi", "power": "bolt", "electric": "bolt", "screen": "phone", "time": "clock", "processor": "chip", "cpu": "chip"}

SYSTEM_PROMPT = f"""You write short, addictive explainer videos for the TikTok/YouTube Shorts channel 'Silicon Verdict'.
A friendly chip-headed mascot narrates while simple line-art animations appear exactly when each idea is spoken.

LANGUAGE: natural, conversational American English, written to be SPOKEN, not read.
- 150 to 175 words total (about 60 to 65 seconds).
- Short sentences. Mix in a question, a sentence fragment, and a casual interjection ("Here's the thing.", "Wild, right?").
- Structure: provocative hook (first sentence, under 14 words) -> the surprising truth -> how it really works (story or analogy)
  -> a parallel real-world example or twist ("But there's more.") -> a closing line that loops back to the hook and asks a question.
- Only TRUE, verifiable facts. If you are not certain of a number, do not use it. Never invent statistics.

SCENES: 12 to 16 scenes, each starting on an exact word from full_script (word_anchor, must appear in the script, 3+ letters),
in the order spoken, at least 2.5 seconds apart. Use vector_type 'none' for 2 or 3 scenes so the mascot is alone on screen.
vector_type options and the fields they use:
- counter: value_from, value_to (numbers said in the script), label
- bars: label + a (0..1) for row 1, label2 + b (0..1) for row 2
- gauge: a (0..1), label
- trio: icon/label, icon2/label2, icon3/label3
- flow: icon -> icon2, label
- icon: icon, label
- big_text: text (max 6 words)
Labels are max 3 words. Valid icons: {', '.join(ICON_NAMES)}.
pose per scene: idle, surprised, point, shrug, think, wave, cheer. Match the emotion of the line.
Set flash=true on exactly ONE scene: the key reveal.
header_banner: 3 to 5 uppercase words, the hook.
title: under 70 characters plus 2 to 3 hashtags. description: 2 sentences. pinned_comment: a debate question."""


def _clean_word(w: str) -> str:
    return re.sub(r"[^\w]", "", w.lower())


def validate_story(story: StoryProject) -> List[str]:
    """Normalizes fields in place and returns blocking problems."""
    problems: List[str] = []
    words = story.full_script.split()
    if not 125 <= len(words) <= 190:
        problems.append(f"word count {len(words)} outside 125-190")
    script_words = {_clean_word(w) for w in words}
    if not 10 <= len(story.scenes) <= 18:
        problems.append(f"{len(story.scenes)} scenes (need 10-18)")
    for sc in story.scenes:
        sc.pose = sc.pose if sc.pose in VALID_POSES else "idle"
        sc.vector_type = sc.vector_type if sc.vector_type in VALID_VECTORS else "icon"
        for attr in ("icon", "icon2", "icon3"):
            val = getattr(sc, attr)
            if val:
                val = ICON_ALIASES.get(val.lower(), val.lower())
                setattr(sc, attr, val if val in ICON_NAMES else "star")
        if sc.vector_type == "icon" and not sc.icon:
            sc.icon = "star"
    # Drop scenes whose anchor word is not in the script instead of rejecting the whole story
    kept = [sc for sc in story.scenes if _clean_word(sc.word_anchor) in script_words]
    if len(kept) != len(story.scenes):
        logger.info("Dropped %d scene(s) with unknown anchors", len(story.scenes) - len(kept))
        story.scenes = kept
        if not 10 <= len(story.scenes) <= 18:
            problems.append(f"{len(story.scenes)} scenes after dropping bad anchors (need 10-18)")
    if sum(1 for s in story.scenes if s.flash) != 1:
        flashes = [s for s in story.scenes if s.flash]
        for extra in flashes[1:]:
            extra.flash = False
        if not flashes and story.scenes:
            story.scenes[len(story.scenes) * 2 // 3].flash = True
    return problems


def get_emergency_story(topic: Optional[str] = None) -> StoryProject:
    """Deterministic story (why phones charge slowly after 80%) so the pipeline never ships empty."""
    script = (
        "Why does your phone charge to eighty percent in half an hour, and then take forever to finish? "
        "Your phone isn't broken. It's protecting itself. "
        "Here's the thing. A lithium battery hates two things: heat, and being pushed to its limit. "
        "So the charger works in two stages. "
        "In the first stage, it pours in as much current as it safely can, and the battery fills fast. "
        "But as it fills, its voltage climbs, until it hits a hard ceiling, just over four volts per cell. "
        "Go past that, and the battery starts to degrade. "
        "So the charger holds the voltage steady, and lets the current shrink. "
        "Less current means slower charging. "
        "Think of filling a glass of water. You blast the tap at first, then slow to a trickle near the top, so you don't spill. "
        "That last twenty percent can take almost as long as the first eighty. "
        "That's also why many phones now offer optimized charging, which pauses at eighty until you actually need the rest. "
        "Wild, right? So, would you rather charge slowly, or have a battery that lasts for years?"
    )
    S = lambda anchor, pose, vt="none", **kw: StoryScene(word_anchor=anchor, pose=pose, vector_type=vt, **kw)
    return StoryProject(
        topic=topic or "Why Phones Charge Slowly After 80%",
        header_banner="WHY THE LAST 20% TAKES FOREVER",
        title="Why Your Phone Charges Slower After 80% #Tech #Battery #SiliconVerdict",
        description="Phones don't slow down because they're broken. Lithium batteries switch from fast charging to a slow top-off to protect themselves.",
        tags=["SiliconVerdict", "Battery", "Phones", "TechCuriosities", "Explained", "Shorts"],
        pinned_comment="Do you charge to 100% every night, or stop at 80%?",
        full_script=script,
        scenes=[
            S("phone", "surprised", "counter", value_from=0, value_to=80, label="percent fast"),
            S("broken", "shrug", "icon", icon="phone", label="Not broken"),
            S("protecting", "point", "big_text", text="It protects itself"),
            S("lithium", "think", "trio", icon="thermometer", label="Heat", icon2="bolt", label2="Pushed too far", icon3="battery", label3="Lithium cell"),
            S("stages", "point", "flow", icon="bolt", icon2="battery", label="Two stages"),
            S("fast", "cheer", "gauge", a=0.92, label="Fast charging"),
            S("ceiling", "idle", "big_text", text="Voltage ceiling"),
            S("degrade", "surprised", "icon", icon="battery", label="Degrades"),
            S("current", "point", "bars", label="Voltage (held)", a=1.0, label2="Current (shrinks)", b=0.2),
            S("glass", "idle"),
            S("trickle", "think", "gauge", a=0.15, label="Trickle"),
            S("twenty", "surprised", "big_text", text="Last 20% = slow", flash=True),
            S("optimized", "point", "icon", icon="phone", label="Optimized charging"),
            S("years", "cheer", "icon", icon="smile", label="Lasts years"),
        ],
    )


def generate_story_live(topic: Optional[str] = None, avoid_topics: Optional[List[str]] = None) -> StoryProject:
    """One validated story straight from Gemini (retries + model rotation). Raises GeminiUnavailable."""
    avoid = [t for t in (avoid_topics or []) if t][-25:]
    prompt = (
        f"Write a video about: {topic}\n" if topic
        else "Pick a small, relatable everyday-tech mystery that almost nobody can explain (USB, Bluetooth, batteries, "
             "touchscreens, cameras, Wi-Fi, headphones, QR codes, GPS, speakers).\n"
    )
    if avoid:
        prompt += "Do NOT repeat or closely resemble these topics: " + "; ".join(avoid) + "\n"
    prompt += "Return a JSON object matching the StoryProject schema."

    story, tokens, model = generate_structured(
        prompt=prompt,
        system_instruction=SYSTEM_PROMPT,
        schema=StoryProject,
        temperature=0.8,
        validate=validate_story,
    )
    story.gemini_input_tokens, story.gemini_output_tokens = tokens
    logger.info("StoryProject ready via %s: %d words | %d scenes", model, story.get_total_words(), len(story.scenes))
    return story


def generate_story(topic: Optional[str] = None, prefer_bank: bool = False) -> StoryProject:
    """Live Gemini -> banked story -> deterministic fallback (flagged with is_fallback).
    With prefer_bank=True the banked (hand-written) stories are used first.
    """
    from services.gemini_client import GeminiUnavailable
    from services.history import get_recently_used_topics_safe
    if prefer_bank and not topic:
        from services.bank_manager import take_or_refill
        banked = take_or_refill("simple")
        if banked is not None:
            return banked
        logger.info("Story bank is empty and could not be refilled; generating live.")
    try:
        return generate_story_live(topic, avoid_topics=get_recently_used_topics_safe())
    except GeminiUnavailable as exc:
        logger.warning("Gemini unavailable after retries (%s). Trying the story bank...", str(exc)[:150])

    from services.story_bank import pop_story
    banked = pop_story("simple")
    if banked is not None:
        return banked

    logger.warning("Story bank is empty. Using deterministic fallback story.")
    story = get_emergency_story(topic)
    story.category_name = "EVERYDAY CURIOSITIES"
    story.is_fallback = True
    return story
