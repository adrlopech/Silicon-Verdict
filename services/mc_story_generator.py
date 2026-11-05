"""Minecraft series: a concept explained INSIDE the game (Craftonomista-style), ~64 s (TikTok monetisation needs > 60 s), subtitles + real game sounds.

Gemini writes a structured script (metaphor mapping + stations + beats with actions); the Remotion director
(remotion_studio/src/mc/director.ts) turns it into animation, camera, props and sounds. Every script is compiled
before it is accepted, so a script that cannot be directed is rejected and the next model is tried.
Every video uses a NEW Gemini script (live or banked ahead of time); there is no hand-written fallback.
"""
import logging
from typing import List, Optional

from config.settings import settings
from core.schemas import McStory
from services.gemini_client import generate_structured
from services.mc_director import compile_script

logger = logging.getLogger(__name__)

LANGS = {"es": "natural, conversational Spanish (neutral Latin American)", "en": "natural, conversational US English"}


def system_prompt(lang: str) -> str:
    return f"""You write 64-second vertical videos (TikTok only monetises videos longer than 60 s, so never shorter) where a computing or gaming concept is explained with a METAPHOR built inside Minecraft,
for the channel 'Silicon Verdict'. Steve (the hero) walks through a small world and DOES things that stand for the parts of the concept
(mining = work, chest = far storage, inventory = fast memory, pond = obstacle, door = permission, ladder = layers...).
Every beat's text is BOTH the on-screen subtitle and the line a narrator speaks aloud, so write it as natural spoken language, punchy, 7-11 words (max 70 characters).

LANGUAGE of all on-screen text, title, description and comments: {LANGS.get(lang, LANGS['en'])}.
Facts must be TRUE and technically precise: never say anything an expert would flag (e.g. a hard drive has spinning platters and a moving head, NOT gears).
Include 2-3 real, approximate figures that make the idea memorable ("about 10 ms vs 0.1 ms, roughly 100x faster"), always with "about/roughly"; never invent precise numbers.

STRUCTURE (14 to 18 beats, about 130-160 spoken words in total, a dense video with no dead air):
1. Hook beat: a surprising claim WITH a figure, not a question the viewer never asked ("Your old hard drive makes your PC wait 100 times longer.") with a sign station in view (shot 'sign', focus = that station).
2. 11-15 explanation beats that build tension: ONE consistent metaphor from start to finish (never switch metaphor midway), each beat tied to one Minecraft object or action. Use "but there is a catch" ONLY to introduce a real drawback, never an advantage. Escalate: problem, why it happens, the twist, the payoff with figures.
3. Final beats: the takeaway with the key figure, then a last line that echoes the hook so the loop replays naturally.
Text: no emojis. hl = the ONE term or number worth remembering in that line (e.g. the concept name or "100x"), not a filler verb.
VISUALS MUST MATCH THE WORDS: what Steve does in a beat must be exactly what the line says (a line about walking = a walk; never mine something unrelated while the narrator talks about walking). Use a different station or camera shot for each new idea; never leave Steve idle on a line that describes an action.

STATIONS are laid out left to right along a path, in the order you list them (3 to 5 stations; a station's id is a short lowercase slug):
- sign: a sign with up to 4 lines (12 characters max per line, uppercase for headings). label = the lines.
- mine: a wall of ore blocks the hero mines (label optional, ores optional: coal, iron, gold, redstone, lapis, diamond). Max 2 mine actions per mine station.
- chest: a chest the hero opens (open_chest). Only one opening per chest.
- pond: water the hero swims across (swim).
- door: a door the hero opens and walks through (open_door).
- ladder: a ladder the hero climbs (climb). Put it LAST: the hero ends in the air, so the climb must happen in the FINAL beat(s) and NO action of any kind (walk, mine, wave...) may follow it. If you cannot guarantee that, do not use a ladder.
- pen: mobs standing around (kinds: pig, cow, chicken, sheep, villager, spider, zombie, skeleton, creeper; up to 4). The hero can 'attack' them or just pass by; 'look' makes him notice them.
Any station can carry a label (sign next to it). Stations farther apart make the hero walk (about 2-3 seconds per gap), which makes a good pause for a subtitle.

ACTIONS inside a beat (they run in order; the director auto-walks to the target station first, so 'go' is only needed to walk without doing anything):
go, mine (target, swings 1-6, fast), open_chest, swim, open_door, climb, wave (seconds), jump, use (seconds), attack (target pen), look (target station or actor), wait (seconds).
Rules the director enforces: acts consume real time (mine ~3-6 s, chest 1.5 s, swim ~3 s); a beat lasts as long as its slowest action, so do not put
a 6 s action under a 2 s subtitle. Give beats with long actions a long-ish subtitle or let them run across 2 beats. Total target: 64 seconds: use 5-8 big actions (walks between stations count) and fill the rest with short beats (wave, look, wait, jump).
Optional cast: extra actors (villager, zombie...) with an id and a starting station 'at'; they act when you give them actions with actor=<id>.
Camera: set 'shot' only when you need it (sign, close, orbit, wide, follow, pan) and at most on 3 beats; otherwise leave it empty, the director plans cuts by itself.
Inventory: set inventory.grow_at_beat (index of a beat, from 0) ONLY when the metaphor is "more space / more slots", e.g. RAM upgrade.

METADATA: title <= 70 chars + 2-3 hashtags (include #minecraft and #siliconverdict); description 2 sentences; tags 6-8; pinned_comment: a question that invites debate.
screen_title: uppercase, <= 28 chars, shown for the first 2 seconds. cta: uppercase, <= 32 chars (e.g. follow to understand your PC); it is also spoken aloud at the end, so it must sound natural. seconds = 64. script_id: lowercase slug.
header_banner: same as screen_title."""


def _repair_ladder(story: McStory) -> None:
    """Gemini often keeps acting after the climb (the hero is then in the air). Fix it instead of rejecting the script:
    climb in the last 3 beats -> drop everything the climber does afterwards; earlier climb -> drop the ladder altogether."""
    n = len(story.beats)
    first = {}  # actor -> (beat, action) of its first climb
    for bi, b in enumerate(story.beats):
        for ai, a in enumerate(b.actions):
            if a.act == "climb":
                first.setdefault(a.actor, (bi, ai))
    if not first:
        return
    if any(bi < n - 3 for bi, _ in first.values()):  # climb too early: remove the ladder and every reference to it
        ladders = {st.id for st in story.stations if st.type == "ladder"}
        story.stations = [st for st in story.stations if st.type != "ladder"]
        for b in story.beats:
            b.actions = [a for a in b.actions if a.act != "climb" and a.target not in ladders]
            if b.focus in ladders:
                b.focus = None
        return
    for actor, (bi, ai) in first.items():
        story.beats[bi].actions = [a for k, a in enumerate(story.beats[bi].actions) if k <= ai or a.actor != actor]
        for b in story.beats[bi + 1:]:
            b.actions = [a for a in b.actions if a.actor != actor]
    ladders = [st for st in story.stations if st.type == "ladder"]  # the ladder station goes last
    story.stations = [st for st in story.stations if st.type != "ladder"] + ladders


def _problems(story: McStory) -> List[str]:
    out: List[str] = []
    _repair_ladder(story)
    if not 13 <= len(story.beats) <= 20:
        out.append(f"{len(story.beats)} beats (need 13-20)")
    words = sum(len(b.text.split()) for b in story.beats)
    if words < 110:
        out.append(f"only {words} spoken words (need at least 110: the video must have no dead air)")
    if not any(ch.isdigit() for b in story.beats for ch in b.text):
        out.append("no figure anywhere: include 2-3 approximate real numbers (e.g. about 10 ms vs 0.1 ms)")
    if not 2 <= len(story.stations) <= 6:
        out.append(f"{len(story.stations)} stations (need 2-6)")
    story.seconds = 64.0
    if story.inventory is not None:  # hotbar items must be real textures, otherwise the render crashes; unknown ones are dropped
        valid = {"torch", "item_diamond_pickaxe", "item_iron_pickaxe", "item_iron_sword", "item_coal", "item_raw_iron", "item_gold_ingot",
                 "item_redstone", "item_lapis_lazuli", "item_diamond", "item_apple", "item_stick"}
        story.inventory.items = [i for i in story.inventory.items if i in valid]
    for b in story.beats:
        b.text = b.text.strip()
    try:
        rep = compile_script(story.to_script())
    except Exception as exc:  # node missing etc.: do not block the pipeline on the checker itself
        logger.warning("Script checker unavailable (%s); accepting without compile.", str(exc)[:120])
        return out
    out += rep["errors"]
    for w in rep["warnings"]:
        if w.startswith("length is"):
            continue
        elif not w.startswith("length is") and "never" not in w:
            out.append(w)
    if rep["ok"] and not 61 <= rep["seconds"] <= 80:
        out.append(f"length {rep['seconds']:.1f}s outside 61-80s (TikTok monetisation needs > 60 s)")
    return out


def generate_story_live(topic: Optional[str] = None, avoid_topics: Optional[List[str]] = None, lang: Optional[str] = None) -> McStory:
    """One validated Minecraft script straight from Gemini. Raises GeminiUnavailable."""
    lang = lang or getattr(settings, "MC_LANGUAGE", "es")
    avoid = [t for t in (avoid_topics or []) if t][-25:]
    prompt = (
        f"Explain this concept: {topic}\n" if topic
        else "Pick ONE basic computing or gaming concept that people use daily but rarely understand (RAM, cache, CPU cores, GPU, FPS, "
             "latency, ping, SSD, bits and bytes, resolution, refresh rate, VRAM, drivers, operating system, compression, encryption, cloud...).\n"
    )
    if avoid:
        prompt += "Do NOT repeat or closely resemble these topics: " + "; ".join(avoid) + "\n"
    prompt += "Return a JSON object matching the McStory schema."
    story, tokens, model = generate_structured(
        prompt=prompt, system_instruction=system_prompt(lang), schema=McStory, temperature=0.8, validate=_problems,
    )
    story.gemini_input_tokens, story.gemini_output_tokens = tokens
    logger.info("McStory ready via %s: %d beats | %d stations", model, len(story.beats), len(story.stations))
    return story


def generate_stories_batch(count: int, avoid_topics: Optional[List[str]] = None, lang: Optional[str] = None) -> List[McStory]:
    """`count` validated Minecraft scripts from ONE Gemini request (refills the bank without burning the daily quota)."""
    from services.gemini_client import generate_structured_list
    lang = lang or getattr(settings, "MC_LANGUAGE", "es")
    avoid = [t for t in (avoid_topics or []) if t][-40:]
    prompt = ("Pick basic computing or gaming concepts that people use daily but rarely understand (RAM, cache, CPU cores, GPU, FPS, latency, ping, SSD, "
              "bits and bytes, resolution, refresh rate, VRAM, drivers, operating system, compression, encryption, cloud...).\nEach script needs 14-18 beats and 130-160 spoken words.\n")
    if avoid:
        prompt += "Do NOT repeat or closely resemble these topics: " + "; ".join(avoid) + "\n"
    stories, tokens, _model = generate_structured_list(prompt, system_prompt(lang), McStory, count, _problems)
    for st in stories:
        st.gemini_input_tokens, st.gemini_output_tokens = tokens[0] // len(stories), tokens[1] // len(stories)
    return stories


class McScriptUnavailable(RuntimeError):
    """No new Gemini script could be produced (Gemini down and the bank is empty)."""


def generate_story(topic: Optional[str] = None, prefer_bank: bool = True) -> McStory:
    """A NEW Gemini script: from the bank (scripts Gemini wrote ahead of time, never used) or live from Gemini.
    There is no hand-written fallback: if neither is available the video is not produced."""
    from services.gemini_client import GeminiUnavailable
    from services.history import get_recently_used_topics_safe
    from services.story_bank import pop_story
    if prefer_bank and not topic:
        banked = pop_story("minecraft")
        if banked is not None:
            return banked
    try:
        return generate_story_live(topic, avoid_topics=get_recently_used_topics_safe())
    except GeminiUnavailable as exc:
        logger.warning("Gemini unavailable (%s).", str(exc)[:150])
    if not topic:  # a specific topic must come from Gemini; otherwise any unused banked script will do
        banked = pop_story("minecraft")
        if banked is not None:
            return banked
    raise McScriptUnavailable("Gemini is unavailable and the Minecraft script bank is empty: no video produced "
                              "(refill it with `scripts/refill_story_bank.py --series minecraft`).")
