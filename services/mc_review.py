"""Pre-upload quality gate for the Minecraft series.

1. review_and_fix(story): a second Gemini pass (before rendering) checks technical accuracy, figures, metaphor consistency, misuse of
   "but there is a catch", whether what Steve DOES matches each line, hook and ending. It rewrites faulty lines (same number of beats);
   the result is re-reviewed. A script that cannot be made clean is rejected.
2. qa_video(path, story): objective checks on the rendered file (format, length, loudness, dead air, voice, subtitles).
Upload only happens when both pass.
"""
import logging
import re
import subprocess
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from core.schemas import McStory
from services.gemini_client import generate_structured
from services.voice import get_ffmpeg_bin

logger = logging.getLogger(__name__)
MAX_LINE = 70
REVIEW_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.7-flash", "gemini-3.8-flash"]  # fact-checking deserves a stronger model than the lite generators


class ReviewIssue(BaseModel):
    line: int = Field(..., description="1-based line number")
    problem: str = Field(..., description="What exactly is wrong, in one sentence")
    definitely_wrong: bool = Field(..., description="true ONLY if the line is clearly false/misleading/contradictory. false if it is acceptable, a simplification, a matter of taste or you are unsure")


class McReview(BaseModel):
    errors: List[ReviewIssue] = Field(default_factory=list, description="Candidate blocking problems: false or misleading technical claims, clearly wrong figures, metaphor that switches midway, 'catch' introducing an advantage. Do NOT list things that are fine.")
    nits: List[str] = Field(default_factory=list, description="Non-blocking polish: style, wording, hook strength, on-screen action not ideal")
    corrected_texts: List[str] = Field(..., description="One line per beat, same order and count: the original line if fine, otherwise the fixed line (7-11 words, max 70 chars)")


REVIEW_SYSTEM = """You are a strict technical fact-checker and editor for 60-second explainer Shorts about computing, where the concept is explained by a
metaphor acted out in Minecraft. Review the script. Put in `errors` ONLY the blocking problems (first four bullets, when real and clear-cut); everything else goes in `nits`. Simplifications that an explainer for beginners naturally makes (rounding, analogies) are NOT errors. Check arithmetic carefully before claiming a figure is wrong. Be fair, not picky: slightly clunky wording or a hook that could be stronger is a nit, never an error. Bullets:
- a technically false, misleading or expert-flaggable statement (wrong component names, wrong mechanism, exaggeration like "always", "zero latency");
- a figure that is wrong or not roughly correct (figures must be approximate and hedged with about/roughly);
- the metaphor changing midway, or the metaphor not actually mapping onto the concept;
- "but there is a catch" (or similar) used to introduce an advantage instead of a drawback;
- a line whose on-screen ACTION contradicts or does not illustrate the words (e.g. narrator talks about walking while Steve mines);
- a hook that is a vague question with no surprise or figure; an ending that does not close the loop;
- repeated words/phrases, grammar errors, or a line that is not natural spoken English.
Then output corrected_texts: the SAME number of lines in the SAME order. Keep lines that are fine unchanged; fix faulty ones with the minimum change
(7-11 words, max 70 characters, natural spoken English, true). Never add or remove lines. Fix a wrong or exaggerated figure by CORRECTING it to an accurate, hedged one (about/roughly); never delete figures: the finished script must keep 2-3 approximate numbers. If nothing is wrong, errors and nits are empty and corrected_texts equals the original lines."""


def _render_script(story: McStory) -> str:
    rows = []
    for i, b in enumerate(story.beats):
        acts = "; ".join(f"{(a.actor or 'steve')} {a.act}" + (f" -> {a.target}" if a.target else "") for a in b.actions) or "idle"
        rows.append(f"{i + 1}. \"{b.text}\"   [on screen: {acts}]")
    stations = ", ".join(f"{s.id}({s.type}{': ' + ' / '.join(s.label) if s.label else ''})" for s in story.stations)
    return f"Topic: {story.topic}\nStations: {stations}\nCall to action (spoken at the end): {story.cta}\nLines:\n" + "\n".join(rows)


def _check(texts_len: int):
    def validate(r: McReview) -> List[str]:
        out = []
        if len(r.corrected_texts) != texts_len:
            out.append(f"corrected_texts must have exactly {texts_len} lines, got {len(r.corrected_texts)}")
        if any(not t.strip() or len(t) > MAX_LINE for t in r.corrected_texts):
            out.append(f"every corrected line must be non-empty and at most {MAX_LINE} characters")
        return out
    return validate


def review_and_fix(story: McStory, rounds: int = 2) -> bool:
    """True when the (possibly corrected) script passes the review. Mutates the story's texts. Raises GeminiUnavailable if Gemini is down."""
    for rnd in range(1, rounds + 1):
        rev, _tok, model = generate_structured(
            prompt=_render_script(story) + "\n\nReview this script.", system_instruction=REVIEW_SYSTEM, schema=McReview,
            temperature=0.1, validate=_check(len(story.beats)), prefer=REVIEW_MODELS, provider_first="groq",
        )
        blocking = [e for e in rev.errors if e.definitely_wrong]
        if not blocking:
            logger.info("Script review passed (%s, round %d)%s.", model, rnd, f"; {len(rev.nits)} non-blocking note(s)" if rev.nits else "")
            return True
        logger.warning("Script review found %d blocking error(s) (round %d): %s", len(blocking), rnd, " | ".join(f"L{e.line}: {e.problem}" for e in blocking)[:400])
        for b, new in zip(story.beats, rev.corrected_texts):
            new = new.strip()
            if new != b.text:
                b.text = new
                if b.hl and b.hl.lower() not in new.lower():
                    b.hl = next((w for w in re.findall(r"[\w.%]+", new) if len(w) > 4), None)
    logger.error("Script still has issues after %d review rounds: rejected.", rounds)
    return False


def _ffmpeg_stats(path: Path, af: str) -> str:
    proc = subprocess.run([get_ffmpeg_bin(), "-hide_banner", "-i", str(path), "-af", af, "-f", "null", "-"], capture_output=True, text=True)
    return proc.stderr


def qa_video(path: Path, story: McStory) -> List[str]:
    """Objective checks on the rendered mp4. Returns the list of failures (empty = pass)."""
    fails: List[str] = []
    path = Path(path)
    if not path.is_file() or path.stat().st_size < 1_000_000:
        return ["video file missing or suspiciously small"]
    log = _ffmpeg_stats(path, "volumedetect,silencedetect=n=-45dB:d=2.5")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", log)
    dur = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0
    if dur < 61:
        fails.append(f"duration {dur:.1f}s is under 61 s (TikTok monetisation)")
    if dur > 90:
        fails.append(f"duration {dur:.1f}s is too long for a Short")
    if "1080x1920" not in log:
        fails.append("video is not 1080x1920")
    if "48000 Hz" not in log:
        fails.append("audio is not 48 kHz")
    peak = re.search(r"max_volume: (-?[\d.]+) dB", log)
    if peak and float(peak[1]) > -1.0:
        fails.append(f"audio peak {peak[1]} dB is too close to clipping")
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", log)
    if mean and float(mean[1]) < -30:
        fails.append(f"audio mean {mean[1]} dB is too quiet (voice missing?)")
    if "silence_duration" in log:
        fails.append("dead air: a silent gap longer than 2.5 s")
    words = sum(len(b.text.split()) for b in story.beats)
    if words < 110:
        fails.append(f"only {words} spoken words (video would feel empty)")
    if any(len(b.text) > MAX_LINE for b in story.beats):
        fails.append("a subtitle is longer than 70 characters")
    if not any(ch.isdigit() for b in story.beats for ch in b.text):
        fails.append("the script contains no figure")
    return fails
