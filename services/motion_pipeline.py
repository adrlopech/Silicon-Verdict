"""End-to-end pipeline for series 6 (Motion Graphics): script -> render (@remotion/renderer) -> sound -> QA -> output folders -> optional YouTube upload."""
import logging
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import settings

logger = logging.getLogger(__name__)
FPS = 30
MIN_VIDEO_SECONDS = 62.0  # final length floor (YouTube monetisation: more than 60 s)
VOICE_LEAD = 0.12  # seconds after a scene starts before the narrator speaks (the text lands first)
# One narrator per format (content study, Nov 2026: viewers had already commented on hearing the same voice in every video). The numbers match ELEVENLABS_VOICE_1/2/3:
# Daniel was dropped on 2026-11-15 (the user dislikes the voice): his formats went to Adam (hardware, evolution) and Liam (decode, the classic explainer). Game videos keep Liam.
VOICE_BY_FORMAT = {"hardware": 2, "evolution": 2, "decode": 3, None: 3, "versus": 2, "myth": 2, "tier": 2, "whatif": 3, "fix": 3, "simple": 3, "easter": 3,
                   "top5": 3, "eli5": 3, "fails": 2, "numbers": 2, "quiz": 3, "stop": 3, "rumor": 2, "review": 2, "news": 2, "priced": 3}


def narrator_voice(project: Any) -> str:
    """ElevenLabs voice id for a project: rotates by format unless MOTION_VOICE_ROTATION is off (then always Liam, as before)."""
    liam = settings.ELEVENLABS_VOICE_3
    if not settings.MOTION_VOICE_ROTATION or getattr(project, "kind", "curiosity") == "game":
        return liam
    number = VOICE_BY_FORMAT.get(getattr(project, "format", None), 3)
    return {1: settings.ELEVENLABS_VOICE_1, 2: settings.ELEVENLABS_VOICE_2, 3: liam}[number]


def render_motion(props: dict, out_mp4: Path, public_dir: Optional[Path] = None) -> Path:
    """Renders the MotionGraphic composition with scripts/render_motion.mjs. Always 1080x1920 (the script refuses anything else)."""
    import json
    out_mp4 = Path(out_mp4).resolve()
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    props_path = out_mp4.with_suffix(".props.json")
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    cmd = ["node", str(settings.BASE_DIR / "scripts" / "render_motion.mjs"), str(props_path), str(out_mp4)] + ([str(public_dir)] if public_dir else [])
    proc = subprocess.Popen(cmd, cwd=str(settings.BASE_DIR),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tail = []
    for line in proc.stdout:  # progress goes straight to the logs
        line = line.rstrip()
        if line.startswith("[motion]"):
            logger.info(line)
        tail.append(line)
    proc.wait()
    props_path.unlink(missing_ok=True)
    if proc.returncode != 0 or not out_mp4.is_file():
        raise RuntimeError("Motion render failed: " + " | ".join(tail[-6:])[-600:])
    return out_mp4


COVER_STYLES = {"a": (0, 42), "b": (1, 100)}  # style -> (scene index, frame in it): "a" the cold open (the claim), "b" the second scene once its first element is in place


def cover_style(title: str) -> str:
    """The cover style of a video, fixed by its title so a rerun gives the same cover; the two halves of the videos are compared in scripts/report_retention.py (cover style table)."""
    import zlib
    return "ab"[zlib.crc32(title.encode("utf-8")) % 2]


def render_cover(props: dict, out_png: Path, public_dir: Optional[Path] = None, style: str = "a") -> Optional[Path]:
    """The cover (thumbnail) of a video: a still without subtitles (scripts/render_cover.mjs) of its cold open (style "a") or of its second scene (style "b").
    Best effort: None when it cannot be made, the video never waits on it."""
    import json
    out_png = Path(out_png).resolve()
    props_path = out_png.with_suffix(".props.json")
    try:
        props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        cmd = ["node", str(settings.BASE_DIR / "scripts" / "render_cover.mjs"), str(props_path), str(out_png), str(public_dir or ""), str(COVER_STYLES.get(style, COVER_STYLES["a"])[1]), str(COVER_STYLES.get(style, COVER_STYLES["a"])[0])]
        proc = subprocess.run(cmd, cwd=str(settings.BASE_DIR), capture_output=True, text=True, timeout=300)
        if proc.returncode != 0 or not out_png.is_file():
            logger.warning("Cover not rendered: %s", (proc.stdout + proc.stderr)[-300:])
            return None
        return out_png
    except Exception as exc:
        logger.warning("Cover not rendered: %s", exc)
        return None
    finally:
        props_path.unlink(missing_ok=True)


_TOKEN = re.compile(r"[^\w\+\%\$\#\-\'\.]")


def _tokens(text: str) -> list:
    """The words ElevenLabs alignment reports for a text (same cleaning as services.voice_synthesizer.align_characters_to_words)."""
    return [t for t in text.split() if _TOKEN.sub("", t).strip()]


def _norm_word(w: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", w.lower())


def cursor_cues(project: Any, words: list, counts: list, cuts: list) -> None:
    """Sets scene.cursorCue (seconds after the scene starts) from the voice timing: for a select, the moment the narrator says the first word of the key phrase (the accent, or the label of a
    one-word scene); for the other actions, about a third into the scene's speech. The pointer then arrives as the phrase is spoken instead of at a fixed moment."""
    pos = 0
    for k, scene in enumerate(project.scenes):
        scene_words = words[pos:pos + counts[k]]
        pos += counts[k]
        if not scene.cursor or not scene_words:
            continue
        begin = scene_words[0]["start"]
        cue = begin + (scene_words[-1]["end"] - begin) * 0.35
        if scene.cursor == "select":
            phrase = scene.text if scene.type == "bigText" else (scene.accentText or scene.text)
            first = next((_norm_word(w) for w in phrase.split() if _norm_word(w)), "")
            hit = next((w for w in scene_words if first and _norm_word(w["word"]) == first), None)
            if hit:
                cue = hit["start"]
        scene.cursorCue = round(max(0.0, cue - cuts[k]), 2)


CALLOUT_UNITS = {"hz", "ghz", "mhz", "gb", "mb", "tb", "ms", "ns", "fps", "w", "v", "nm", "gbps", "mbps", "%", "x", "mm", "c", "k"}
CALLOUT_MIN_WORDS = 11  # a scene this long (about 4.5 s of speech) gets a second visual beat
CALLOUT_SKIP = {"flash", "tier", "ui", "footage", "outro", "counter", "progressBar"}


def pick_callout(tokens: list) -> Optional[tuple]:
    """(text, token index) of the most salient term in the SECOND half of a scene's words: a figure (with its unit), else an acronym or capitalised term. None when nothing stands out (a plain long word is not worth a tag)."""
    half = len(tokens) // 2
    clean = lambda t: re.sub(r"^[^\w%$#+]+|[^\w%$#+]+$", "", t)  # noqa: E731
    cands = [(i, clean(t)) for i, t in enumerate(tokens) if i >= half and clean(t)]
    for i, w in cands:
        if re.search(r"\d", w):
            nxt = clean(tokens[i + 1]) if i + 1 < len(tokens) else ""
            return (f"{w} {nxt}" if nxt.lower() in CALLOUT_UNITS else w, i)
    for i, w in cands:
        if i > 0 and (w.isupper() and len(w) > 1 or (w[0].isupper() and len(w) > 2 and not tokens[i - 1].endswith((".", "!", "?")))):
            return (w, i)
    return None


def _caption_tokens(scene: Any, normalised: str, count: int) -> list:
    """The words to show for a scene: the script's own text when it has as many words as the voice aligned, otherwise the (phonetically normalised) text the voice read."""
    own = _tokens(scene.narration)
    return own if len(own) == count else _tokens(normalised)[:count]


def build_captions(project: Any, words: list, texts: list, counts: list, cuts: list) -> None:
    """Sets project.captions (every spoken word with its first and last frame in the whole video) and scene.accentCue (when the narrator says the accent phrase), from the voice timing.
    Run after the scene lengths are final: a word's frame is its scene's start plus its offset inside the scene's voice slice."""
    from services.motion_generator import CaptionWord
    out, pos, start = [], 0, 0
    for k, scene in enumerate(project.scenes):
        toks = _caption_tokens(scene, texts[k], counts[k])
        sw = words[pos:pos + counts[k]]
        pos += counts[k]
        for tok, w in zip(toks, sw):
            s_ = start + round((w["start"] - cuts[k]) * FPS)
            out.append(CaptionWord(w=tok, s=max(0, s_), e=max(s_ + 1, start + round((w["end"] - cuts[k]) * FPS))))
        if scene.accentText and sw:
            first = next((_norm_word(x) for x in scene.accentText.split() if _norm_word(x)), "")
            hit = next((w for t, w in zip(toks, sw) if first and _norm_word(t) == first), None)
            if hit:
                scene.accentCue = round(max(0.0, hit["start"] - cuts[k]), 2)
        if scene.type not in CALLOUT_SKIP and len(toks) >= CALLOUT_MIN_WORDS and sw:
            found = pick_callout(toks)
            if found and found[1] < len(sw):
                scene.callout, scene.calloutCue = found[0], round(max(0.0, sw[found[1]]["start"] - cuts[k]), 2)
        start += scene.durationInFrames
    project.captions = out


def synthetic_captions(project: Any) -> None:
    """The same, without a voice (silent previews): the words are spread over each scene at a natural pace, so the captions and the accent pulse can be judged visually."""
    from services.motion_generator import CaptionWord, WORDS_PER_SECOND
    out, start = [], 0
    for scene in project.scenes:
        toks = _tokens(scene.narration)
        t0 = start + round(VOICE_LEAD * FPS)
        step = FPS / WORDS_PER_SECOND
        for i, tok in enumerate(toks):
            out.append(CaptionWord(w=tok, s=int(t0 + i * step), e=int(t0 + (i + 1) * step) - 1))
        if scene.accentText and toks:
            first = next((_norm_word(x) for x in scene.accentText.split() if _norm_word(x)), "")
            idx = next((i for i, t in enumerate(toks) if first and _norm_word(t) == first), None)
            if idx is not None:
                scene.accentCue = round((VOICE_LEAD * FPS + idx * step) / FPS, 2)
        if scene.type not in CALLOUT_SKIP and len(toks) >= CALLOUT_MIN_WORDS:
            found = pick_callout(toks)
            if found:
                scene.callout, scene.calloutCue = found[0], round((VOICE_LEAD * FPS + found[1] * step) / FPS, 2)
        start += scene.durationInFrames
    project.captions = out


def narrate_scenes(project: Any, work_dir: Path):
    """Narrates the whole script in ONE continuous ElevenLabs take (fluid intonation, no cuts mid-sentence) and slices it per scene at the natural pause between two words.
    Returns ([(scene_index, mp3, seconds)], continuous). With continuous=True each scene lasts exactly as long as its slice and the slices play back to back;
    if the alignment does not match the text, it falls back to one clip per scene (continuous=False)."""
    import math
    from concurrent.futures import ThreadPoolExecutor
    from services import voice_synthesizer
    from services.audio import normalize_phonetics_us_english
    from services.voice import get_ffmpeg_bin
    from services.voice_synthesizer import synthesize_voice_with_timestamps
    work_dir.mkdir(parents=True, exist_ok=True)
    scenes = project.scenes
    texts = [normalize_phonetics_us_english(sc.narration).strip() for sc in scenes]
    counts = [len(_tokens(t)) for t in texts]
    full_path = words = None
    total = 0.0
    for _attempt in (1, 2):  # a failed take is retried once after a pause before giving up
        before = voice_synthesizer.FALLBACK_COUNT
        full_path, total, words = synthesize_voice_with_timestamps(" ".join(texts), work_dir / "voice_full.mp3", voice_id=narrator_voice(project), model_id="eleven_multilingual_v2",
                                                                    natural=True, min_duration=None, max_duration=None, stability=0.32, style=0.5)
        if voice_synthesizer.FALLBACK_COUNT == before:
            break
        logger.warning("ElevenLabs failed for the full narration; retrying...")
        time.sleep(6)
    else:
        raise RuntimeError("ElevenLabs failed (a robotic local voice would have been used): not producing this video")
    if not words or len(words) != sum(counts) or min(counts) < 1:
        logger.warning("Alignment (%d words) does not match the script (%d): narrating scene by scene instead.", len(words or []), sum(counts))
        return _narrate_per_scene(project, work_dir), False

    if total < MIN_VIDEO_SECONDS + 0.3:  # a short script: slow the voice down a little (pitch preserved, never below 0.88x) instead of holding the screen in silence
        tempo = max(0.88, total / (MIN_VIDEO_SECONDS + 0.3))
        if tempo < 0.995:
            slow = work_dir / "voice_full_slow.mp3"
            subprocess.run([get_ffmpeg_bin(), "-y", "-i", str(full_path), "-filter:a", f"atempo={tempo:.3f}", "-c:a", "libmp3lame", "-b:a", "192k", str(slow)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            full_path, total = slow, total / tempo
            words = [{**w, "start": round(w["start"] / tempo, 3), "end": round(w["end"] / tempo, 3)} for w in words]
            logger.info("Voice slowed to %.2fx to reach the minimum length without dead air.", tempo)
    firsts, lasts, pos = [], [], 0
    for c in counts:
        firsts.append(words[pos]["start"])
        lasts.append(words[pos + c - 1]["end"])
        pos += c
    cuts = [0.0] + [(lasts[k] + firsts[k + 1]) / 2 for k in range(len(scenes) - 1)] + [total]  # every cut sits in the middle of the pause between two words
    def cut(k: int):
        start, dur = cuts[k], max(0.2, cuts[k + 1] - cuts[k])
        out = work_dir / f"scene_{k:02d}.mp3"
        af = f"afade=t=in:d=0.006,afade=t=out:st={max(0.0, dur - 0.008):.3f}:d=0.008"
        subprocess.run([get_ffmpeg_bin(), "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(full_path), "-af", af, "-c:a", "libmp3lame", "-b:a", "192k", str(out)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return k, out, dur

    with ThreadPoolExecutor(max_workers=4) as pool:  # the slices are independent ffmpeg runs
        clips = list(pool.map(cut, range(len(scenes))))
    cursor_cues(project, words, counts, cuts)
    for k, _p, dur in clips:
        scenes[k].durationInFrames = max(scenes[k].durationInFrames, math.ceil(dur * FPS))
    if project.total_frames > settings.MAX_VIDEO_SECONDS * FPS:
        raise RuntimeError(f"narrated video would last {project.total_frames / FPS:.1f}s (> {settings.MAX_VIDEO_SECONDS:.0f} s ceiling); script too long")
    deficit = int(MIN_VIDEO_SECONDS * FPS) - project.total_frames  # monetisation needs more than 60 s: the extra time is held where a sentence ends, never in the middle of one
    if deficit > 0:
        ends = [k for k, sc in enumerate(scenes) if sc.narration.strip()[-1:] in ".!?"] or [len(scenes) - 1]
        if (len(scenes) - 1) not in ends:
            ends.append(len(scenes) - 1)
        per = math.ceil(deficit / len(ends))
        for k in ends:
            scenes[k].durationInFrames += per
        logger.info("Narrated video was %.1f s: %d sentence ends held %.2f s longer to pass %.0f s.", (project.total_frames - per * len(ends)) / FPS, len(ends), per / FPS, MIN_VIDEO_SECONDS)
    build_captions(project, words, texts, counts, cuts)
    logger.info("Narration ready (continuous take): %d slices, %.1f s of speech, video %.1f s", len(clips), total, project.total_frames / FPS)
    return clips, True


def _narrate_per_scene(project: Any, work_dir: Path) -> list:
    """Fallback narration: one ElevenLabs clip per scene (parallel). Each scene is stretched to fit its line (+ a short lead). Returns [(scene_index, mp3, seconds)]."""
    import math
    from concurrent.futures import ThreadPoolExecutor
    from services import voice_synthesizer
    from services.voice_synthesizer import synthesize_voice_with_timestamps
    work_dir.mkdir(parents=True, exist_ok=True)

    def one(i: int):
        path, dur, _ = synthesize_voice_with_timestamps(
            project.scenes[i].narration, work_dir / f"scene_{i:02d}.mp3", voice_id=narrator_voice(project), model_id="eleven_multilingual_v2",
            natural=True, min_duration=None, max_duration=None, stability=0.32, style=0.5,
            previous_text=project.scenes[i - 1].narration if i > 0 else None, next_text=project.scenes[i + 1].narration if i + 1 < len(project.scenes) else None)
        return i, path, dur

    clips = []
    for workers in (2, 1):  # ElevenLabs limits concurrent requests: a failed pass is retried one line at a time before giving up
        before = voice_synthesizer.FALLBACK_COUNT
        with ThreadPoolExecutor(max_workers=workers) as pool:
            clips = list(pool.map(one, range(len(project.scenes))))
        if voice_synthesizer.FALLBACK_COUNT == before:
            break
        logger.warning("ElevenLabs failed for some lines with %d worker(s); retrying slower...", workers)
        time.sleep(6)
    else:
        raise RuntimeError("ElevenLabs failed for some lines (a robotic local voice would have been used): not producing this video")
    for i, _p, dur in clips:  # the scene lasts at least as long as its narration (+ a short breath), never less than its own minimum
        project.scenes[i].durationInFrames = max(project.scenes[i].durationInFrames, math.ceil((dur + VOICE_LEAD + 0.12) * FPS))
    if project.total_frames > settings.MAX_VIDEO_SECONDS * FPS:
        raise RuntimeError(f"narrated video would last {project.total_frames / FPS:.1f}s (> {settings.MAX_VIDEO_SECONDS:.0f} s ceiling); script too long")
    deficit = int(MIN_VIDEO_SECONDS * FPS) - project.total_frames  # YouTube monetisation needs MORE than 60 s: hold scenes a little longer if short
    if deficit > 0:
        per = math.ceil(deficit / len(project.scenes))
        for sc in project.scenes:
            sc.durationInFrames += per
        logger.info("Narrated video was %.1f s: scenes held %.2f s longer each to pass %.0f s.", (project.total_frames - per * len(project.scenes)) / FPS, per / FPS, MIN_VIDEO_SECONDS)
    logger.info("Narration ready: %d lines, %.1f s of speech, video %.1f s", len(clips), sum(c[2] for c in clips), project.total_frames / FPS)
    return clips


RISER_TYPES = ("counter", "versus", "verdict", "timeline", "units", "split")  # data reveals: a rising sweep lands on the scene start
MAX_RISERS = 4


# Music beds by format (assets/audio, made by scripts/make_motion_sfx.py). Each format has two; a hash of the topic picks one, so the channel does not sound the same every time.
MUSIC_BY_FORMAT = {
    None: ("motion_bed.wav", "bed_chill.mp3"), "hardware": ("motion_bed.wav", "bed_minimal.mp3"), "evolution": ("bed_epic.mp3", "motion_bed.wav"), "decode": ("bed_minimal.mp3", "bed_chill.mp3"),
    "versus": ("bed_drive.mp3", "bed_epic.mp3"), "myth": ("bed_dark.mp3", "bed_minimal.mp3"), "tier": ("bed_drive.mp3", "bed_bright.mp3"), "whatif": ("bed_dark.mp3", "bed_epic.mp3"),
    "fix": ("bed_bright.mp3", "bed_chill.mp3"), "simple": ("bed_chill.mp3", "bed_bright.mp3"), "easter": ("bed_epic.mp3", "bed_dark.mp3"),
    "top5": ("bed_drive.mp3", "bed_bright.mp3"), "eli5": ("bed_chill.mp3", "bed_bright.mp3"), "fails": ("bed_dark.mp3", "bed_epic.mp3"), "numbers": ("bed_minimal.mp3", "bed_drive.mp3"),
    "quiz": ("bed_bright.mp3", "bed_drive.mp3"), "stop": ("bed_drive.mp3", "bed_dark.mp3"), "rumor": ("bed_dark.mp3", "bed_minimal.mp3"), "review": ("bed_minimal.mp3", "bed_chill.mp3"), "priced": ("bed_drive.mp3", "bed_minimal.mp3"), "news": ("bed_minimal.mp3", "bed_epic.mp3"),
}
WHOOSHES = ("sfx_whoosh.wav", "sfx_whoosh_soft.wav", "sfx_swish.wav", "sfx_slide.wav")  # scene changes rotate through these


def music_bed(fmt: Optional[str], topic: str = "") -> str:
    """File name of the music bed for a format; the topic picks between the format's two."""
    import hashlib
    options = MUSIC_BY_FORMAT.get(fmt, MUSIC_BY_FORMAT[None])
    return options[int(hashlib.sha256((topic or "").lower().encode()).hexdigest(), 16) % len(options)]


def pointer_moment(scene_type: str, cursor: Optional[str], dur: int, cue: Optional[float]) -> float:
    """Seconds after the scene starts at which the pointer does its thing (presses, grabs, starts selecting): the same timing the Remotion cursor uses."""
    from math import floor
    if scene_type == "ui":
        frames = max(28, min(dur - 70, round(cue * FPS) - 2)) if cue is not None else max(28, min(46, round(dur * 0.3)))
    elif scene_type == "progressBar":
        frames = 14
    elif scene_type == "tier":
        frames = 46  # TIER_DROP: the chip lands in its row
    else:
        arrive = max(16, min(dur - 44, round(cue * FPS) - 2)) if cue is not None else min(34, round(dur * 0.34))
        frames = arrive + (5 if cursor in ("click", "toggle") else 0)
    return floor(frames) / FPS


def scene_audio_info(scenes: list) -> list:
    """What the sound design needs to know about each scene (see sound_cues)."""
    return [{"cursor": s.cursor, "dur": s.durationInFrames, "cue": getattr(s, "cursorCue", None), "verdict": getattr(s, "verdict", None),
             "callout_at": getattr(s, "calloutCue", None) if getattr(s, "callout", None) else None,
             "price": bool(getattr(s, "value", None)) and s.type == "tier"} for s in scenes]


# Mean level (dB, ffmpeg volumedetect) of each effect file, and the mean level each kind of cue is brought to. The old flat multipliers left sfx_whoosh (mean -5.9 dB) louder than the voice;
# now every cue sits well under it. Without a voice (silent previews) the effects are 6 dB louder.
SFX_MEAN = {"sfx_blip.wav": -11.8, "sfx_boom.wav": -14.3, "sfx_chime.wav": -17.9, "sfx_click.wav": -25.1, "sfx_ding.wav": -15.9, "sfx_error.wav": -10.9, "sfx_glitch.wav": -17.3, "sfx_hit.wav": -15.5,
            "sfx_pop.wav": -13.7, "sfx_riser.wav": -19.7, "sfx_slide.wav": -19.8, "sfx_sparkle.wav": -17.1, "sfx_swish.wav": -18.1, "sfx_tick.wav": -21.2, "sfx_type.wav": -24.2, "sfx_whoosh.wav": -5.9, "sfx_whoosh_soft.wav": -20.5}
CUE_TARGET_DB = {"rehook": -30, "first": -31, "flash": -30, "riser": -35, "click": -33, "select": -35, "grab": -33, "verdict": -32, "outro": -33, "tick": -37, "pop": -34}
WHOOSH_TARGET_DB = -38


def sfx_gain(fname: str, target_db: float, voiced: bool) -> float:
    """Linear gain that brings an effect file to `target_db` mean level (+6 dB when there is no narration)."""
    return 10 ** ((target_db + (0 if voiced else 6) - SFX_MEAN.get(fname, -18.0)) / 20)


def rehook_index(scene_starts: list, durations: list) -> int:
    """The scene whose start is closest to the middle of the video (never the first two or the last two), which gets the re-hook jolt; -1 for short videos. Same rule as MotionGraphic.tsx rehookIndex."""
    n = len(scene_starts)
    if n < 8:
        return -1
    total = scene_starts[-1] + durations[-1]
    return min(range(2, n - 2), key=lambda i: abs(scene_starts[i] - total / 2))


def sound_cues(scene_starts: list, kinds: Optional[list], info: Optional[list] = None) -> list:
    """Sound-design cues as (file, start seconds, kind): a soft impact on the first frame and on flash scenes, a riser before each data reveal (at most MAX_RISERS, spread out) and,
    when `info` is given (scene_audio_info), the sounds of what happens on screen: the pointer's click / swipe / grab, a tier chip landing, a verdict stamp, counter ticks and the outro chime."""
    cues = []
    if not kinds:
        return cues
    cues.append(("sfx_hit.wav", 0.05, "first"))
    reveals = [i for i, k in enumerate(kinds) if k in RISER_TYPES and i > 0]
    if len(reveals) > MAX_RISERS:
        reveals = [reveals[round(j * (len(reveals) - 1) / (MAX_RISERS - 1))] for j in range(MAX_RISERS)]
    cues += [("sfx_riser.wav", max(0.0, scene_starts[i] / FPS - 0.95), "riser") for i in reveals]
    cues += [("sfx_hit.wav", scene_starts[i] / FPS, "flash") for i, k in enumerate(kinds) if k == "flash"]
    if info:
        mid = rehook_index(scene_starts, [x["dur"] for x in info])
        if mid >= 0:
            cues.append(("sfx_boom.wav", scene_starts[mid] / FPS, "rehook"))
            cues.append(("sfx_riser.wav", max(0.0, scene_starts[mid] / FPS - 0.95), "riser"))
        for i, (kind, sc) in enumerate(zip(kinds, info)):
            at = scene_starts[i] / FPS
            act = sc.get("cursor")
            if act:
                when = at + pointer_moment(kind, act, sc["dur"], sc.get("cue"))
                cues.append({"click": ("sfx_click.wav", when, "click"), "toggle": ("sfx_click.wav", when, "click"), "select": ("sfx_swish.wav", when, "select"), "drag": ("sfx_pop.wav", when, "grab")}[act])
            elif kind == "tier":
                cues.append(("sfx_pop.wav", at + 0.55, "pop"))
                if sc.get("price"):  # the price card counts up under the board
                    cues += [("sfx_tick.wav", at + 0.95 + k * 0.1, "tick") for k in range(4)]
            if sc.get("callout_at") is not None:
                cues.append(("sfx_pop.wav", at + sc["callout_at"], "pop"))
            if kind == "verdict":
                cues.append({"myth": ("sfx_error.wav", at + 0.5, "verdict"), "fact": ("sfx_chime.wav", at + 0.5, "verdict")}.get(sc.get("verdict") or "", ("sfx_ding.wav", at + 0.5, "verdict")))
            elif kind == "counter":
                cues += [("sfx_tick.wav", at + 0.3 + k * 0.17, "tick") for k in range(5)]
            elif kind == "outro":
                cues.append(("sfx_chime.wav", at + 0.12, "outro"))
    return cues


def add_sound(raw: Path, out: Path, scene_starts: list, voice_clips: Optional[list] = None, lead: float = VOICE_LEAD, kinds: Optional[list] = None, music_file: Optional[str] = None, info: Optional[list] = None) -> Path:
    """Muxes a quiet ambient bed, a soft whoosh on every scene start and the narration (both effects are the project's own assets). The loudness is normalised in TWO passes
    (measure, then apply one fixed gain): a single dynamic pass pumps the volume and the voice seems to dip or cut at scene changes."""
    import json as _json
    from services.voice import get_ffmpeg_bin
    ff = get_ffmpeg_bin()
    audio = settings.BASE_DIR / "assets" / "audio"
    ins = ["-i", str(raw), "-stream_loop", "-1", "-i", str(audio / "schematic_ambient.wav")]
    voiced = bool(voice_clips)
    music = audio / (music_file or "motion_bed.wav")
    if not music.is_file():
        music = audio / "motion_bed.wav"
    parts = [f"[1:a]volume={(0.09 if music.is_file() else 0.12) if voiced else 0.22},afade=t=in:d=1.2[bed]"]
    labels = ["[bed]"]
    n = 2
    if music.is_file():  # a quiet electronic pulse under the ambient bed (own asset, scripts/make_motion_sfx.py)
        ins += ["-stream_loop", "-1", "-i", str(music)]
        parts.append(f"[{n}:a]volume={0.07 if voiced else 0.16},afade=t=in:d=1.5[music]")
        labels.append("[music]")
        n += 1
    for i_, start in enumerate(scene_starts):
        whoosh = WHOOSHES[i_ % len(WHOOSHES)]
        ins += ["-i", str(audio / (whoosh if (audio / whoosh).is_file() else "sfx_whoosh.wav"))]
        ms = int(start / FPS * 1000)
        parts.append(f"[{n}:a]adelay={ms}|{ms},volume={sfx_gain(whoosh, WHOOSH_TARGET_DB, voiced):.4f}[w{n}]")
        labels.append(f"[w{n}]")
        n += 1
    for fname, at, cue in sound_cues(scene_starts, kinds, info):  # pattern breaks you can hear (an impact on the cold open and on flashes, a riser into each data reveal) and what happens on screen
        if not (audio / fname).is_file():
            continue
        ins += ["-i", str(audio / fname)]
        ms = int(at * 1000)
        vol = sfx_gain(fname, CUE_TARGET_DB[cue], voiced)
        parts.append(f"[{n}:a]adelay={ms}|{ms},volume={vol}[c{n}]")
        labels.append(f"[c{n}]")
        n += 1
    for idx, clip, _d in voice_clips or []:
        ins += ["-i", str(clip)]
        ms = int((scene_starts[idx] / FPS + lead) * 1000)
        parts.append(f"[{n}:a]adelay={ms}|{ms},volume=1.6[v{n}]")
        labels.append(f"[v{n}]")
        n += 1
    dur = _duration(raw)
    mix = out.with_name(out.stem + "_mix.wav")
    graph = ";".join(parts + ["".join(labels) + f"amix=inputs={len(labels)}:duration=longest:normalize=0[mix]"])
    subprocess.run([ff, "-y", *ins, "-filter_complex", graph, "-map", "[mix]", "-t", f"{dur:.2f}", "-ar", "48000", "-ac", "2", str(mix)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    target = "loudnorm=I=-14:TP=-2:LRA=11"
    norm = target
    try:  # pass 1: measure
        log = subprocess.run([ff, "-hide_banner", "-i", str(mix), "-af", target + ":print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
        m = _json.loads(log[log.rindex("{"):log.rindex("}") + 1])
        if all(k in m and m[k] not in ("-inf", "inf") for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")):
            norm = f"{target}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Loudness measurement failed (%s): single pass normalisation.", exc)
    trim = 0.0  # dB taken off the mix when the encoded file still peaks too high (many cues landing together can push the AAC encode past the limiter)
    for _attempt in range(3):
        gain = f",volume=-{trim:.1f}dB" if trim else ""
        subprocess.run([ff, "-y", "-i", str(raw), "-i", str(mix), "-map", "0:v", "-map", "1:a", "-filter:a", norm + gain + ",alimiter=limit=0.78:level=disabled", "-t", f"{dur:.2f}",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(out)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        peak = _peak_db(out)
        if peak is None or peak <= PEAK_CEILING_DB:
            break
        trim += (peak - PEAK_CEILING_DB) + 0.6
        logger.info("Audio peak %.1f dB is above %.1f dB: encoding again %.1f dB quieter.", peak, PEAK_CEILING_DB, trim)
    mix.unlink(missing_ok=True)
    return out


PEAK_CEILING_DB = -1.2  # the QA gate refuses anything above -0.5 dB; this leaves room for the encoder


def _peak_db(path: Path) -> Optional[float]:
    """Highest sample level of the encoded file, in dB (None if it cannot be read)."""
    from services.voice import get_ffmpeg_bin
    log = subprocess.run([get_ffmpeg_bin(), "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.search(r"max_volume: (-?[\d.]+) dB", log)
    return float(m[1]) if m else None


def _duration(path: Path) -> float:
    from services.voice import ffmpeg_duration
    return ffmpeg_duration(path) or 0.0


def qa_motion(path: Path) -> list:
    """Objective checks: 1080x1920, 61-90 s, H.264, audio present and audible, file not tiny."""
    from services.voice import get_ffmpeg_bin
    fails = []
    if not path.is_file() or path.stat().st_size < 300_000:
        return ["video file missing or suspiciously small"]
    log = subprocess.run([get_ffmpeg_bin(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    if "1080x1920" not in log:
        fails.append("video is not 1080x1920")
    if "h264" not in log:
        fails.append("video is not H.264")
    if "Audio:" not in log:
        fails.append("no audio track")
    vol = subprocess.run([get_ffmpeg_bin(), "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    peak = re.search(r"max_volume: (-?[\d.]+) dB", vol)
    if peak and float(peak[1]) > -0.5:
        fails.append(f"audio peak {peak[1]} dB is clipping")
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", vol)
    if mean and float(mean[1]) < -28:
        fails.append(f"audio mean {mean[1]} dB is too quiet: the narration seems to be missing")
    d = _duration(path)
    if not 61 <= d <= settings.MAX_VIDEO_SECONDS + 1:
        fails.append(f"duration {d:.1f}s outside 61-{settings.MAX_VIDEO_SECONDS:.0f} s (monetisation needs more than 60 s; 3-minute ceiling)")
    return fails


STATIC_NOISE_DB, STATIC_SECONDS = -45, 3.0  # tuned on the Nov 24 RTX tier list: its 4-7 s stretches of an unchanged board are found, animated scenes are not


def static_stretches(path: Path, seconds: float = STATIC_SECONDS) -> list:
    """(start, end) of every stretch of at least `seconds` where the picture barely changes (ffmpeg freezedetect on a small copy). The viewer swipes away when nothing moves,
    so this is reported after every render. A warning, not a failure: the captions still change during such a stretch."""
    from services.voice import get_ffmpeg_bin
    log = subprocess.run([get_ffmpeg_bin(), "-hide_banner", "-i", str(path), "-vf", f"scale=270:-1,freezedetect=n={STATIC_NOISE_DB}dB:d={seconds}", "-an", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", log)]
    return [(round(a, 1), round(b, 1)) for a, b in zip(starts, ends + [_duration(path)] * (len(starts) - len(ends)))]


def _last_motion_choice():
    """(kind, format) of the previous Motion Graphics video, from the history (best effort), so the automatic mode does not repeat it."""
    try:
        from services.history import get_db_connection, init_db
        init_db()
        with get_db_connection() as conn:
            row = conn.execute("SELECT category FROM shorts_history WHERE category LIKE 'MOTION GRAPHICS%' ORDER BY id DESC LIMIT 1").fetchone()
        parts = (row["category"] if row else "").split()
        return ("auto", parts[2].lower()) if len(parts) > 2 else None
    except Exception:
        return None


def _draw_any_format() -> tuple:
    """`--motion-format any`: one of the topics of the Motion Graphics menu (classic, curiosity, game and every format), weighted, never the same as last time and never the news bulletin."""
    import random
    from services.game_images import available_games
    from services.motion_generator import FORMAT_WEIGHTS, FORMATS
    options = [("auto", "auto"), ("curiosity", "auto"), ("game", "auto")] + [("auto", f) for f in FORMATS if f != "news"]  # the news bulletin is a section of its own: never a random pick
    if not available_games():
        options = [o for o in options if o[0] != "game" and o[1] != "easter"]
    last = _last_motion_choice()
    pool = [o for o in options if o != last] or options

    def weight(o: tuple) -> float:  # ("auto", "auto") is the classic explainer; kinds weigh as themselves
        return FORMAT_WEIGHTS.get(o[1] if o[1] != "auto" else {"auto": "classic"}.get(o[0], o[0]), 1)

    kind, fmt = random.choices(pool, weights=[weight(o) for o in pool])[0]
    logger.info("Automatic Motion Graphics topic: kind=%s format=%s", kind, fmt)
    return kind, fmt


def _select_source(kind: str, fmt: str, topic: Optional[str], facts: Optional[str], script: Optional[Any], bank_only: bool = False) -> tuple:
    """Decides what the video is about and where its script comes from: a game (with footage) or a curiosity, a banked script, a hand-written one, or a new one from the LLM.
    With bank_only=True the LLM is never called: a format without a banked script raises RuntimeError.
    Returns (project, game, facts, catalog, banked_game, kind)."""
    import random
    from services.game_facts import get_game_facts
    from services.game_images import available_games, footage_catalog
    from services.history import get_recently_used_topics_safe
    from services.motion_generator import generate_motion_project
    from services.story_bank import pop_story

    format_name = None if fmt == "auto" else fmt
    game, project, banked_game = None, None, False
    if fmt == "auto" and kind in ("game", "auto") and not topic and (kind == "game" or random.random() < 0.5):
        # game scripts written earlier (the old Gaming category, in the bank) go first: they are shown over the game's own screenshots, no footage ledger involved
        from services.game_images import legacy_images
        project = pop_story("motion", lambda p: p.kind == "game" and bool(p.game) and len(legacy_images(p.game)) >= 5)
        if project is not None:
            banked_game, game, kind = True, project.game, "game"
    if not banked_game and kind in ("game", "auto"):
        candidates = available_games()
        random.shuffle(candidates)
        if candidates:
            game = candidates[0]
            facts = get_game_facts(game)  # paced + cached; None only when no source text exists at all -> the script is then written conservatively (no figures)
            if not facts:
                logger.warning("No source text for %s: writing the game video in conservative mode (no figures, only well-known facts).", game)
    if not banked_game and kind == "auto" and game and random.random() < 0.5:
        game, facts = None, None  # alternate between game videos and curiosities
    if kind == "game" and not game:
        raise RuntimeError("No game is available: every game with stocked footage was covered in the last 14 days, ran out of unused footage or has no source text "
                           "(fetch more: scripts/fetch_game_images.py, scripts/fetch_game_clips.py, scripts/caption_game_media.py; blacklist: python -m services.game_registry).")
    catalog = footage_catalog(game) if game and not banked_game else None
    if not topic and not game:  # curiosity videos draw on the pre-written bank first (same format), then fall back to the LLM
        recent = {t.strip().lower() for t in get_recently_used_topics_safe()}
        project = pop_story("motion", lambda p: p.format == format_name and p.kind == "curiosity" and p.topic.strip().lower() not in recent)
    if script is not None:  # a script written by hand (data/scripts/*.json): used as it is, no model involved
        project = script
    if project is None and bank_only:
        raise RuntimeError(f"no banked script for format {format_name or 'auto'}")
    if project is None:
        project = generate_motion_project(topic, avoid_topics=get_recently_used_topics_safe(), kind="game" if game else "curiosity", game=game, catalog=catalog, facts=facts, fmt=format_name)
    return project, game, facts, catalog, banked_game, kind


def _prepare_project(project: Any) -> None:
    """Cleans a script and gives it its identity: no markers, sane cursors, a look and a series number."""
    from services.looks import choose_look
    from services.motion_generator import add_vote_items, assign_cursors, fix_duplicate_accents, mark_tier_teasers, sanitize_cursors, strip_markers
    from services.series import apply_series
    strip_markers(project)  # *asterisks* around the accent word (a habit of the models) would be drawn and spoken literally
    sanitize_cursors(project.scenes, project.format)  # scripts written by hand (the banks) predate the rules: no tab, no hover, only pointer moments that mean something
    assign_cursors(project.scenes, project.format)
    fix_duplicate_accents(project.scenes)
    add_vote_items(project)  # the outro draws the two options of the vote as A / B cards
    mark_tier_teasers(project.scenes)  # a covered "?" waits in the S row until the S item is revealed
    if not project.look:
        project.look = choose_look(project.format, project.topic)  # a whole visual identity per video, never one of the last three used
    logger.info("Look: %s", project.look)
    label = apply_series(project)  # "Fix It Now #7": the title, the first frame and a series hashtag repeat from video to video
    if label:
        logger.info("Series: %s", label)


def _stage_footage(project: Any, catalog: Optional[dict], banked_game: bool, public: Path) -> list:
    """Copies the footage a game video uses into the render's own public dir; returns the catalog entries used (and adds the credits to the description)."""
    from services.game_images import build_credits, stage_legacy_footage, stage_media
    used = []
    for sc in project.scenes:
        if sc.type == "footage" and catalog and sc.mediaId in catalog:
            entry = catalog[sc.mediaId]
            sc.mediaSrc, sc.mediaKind, sc.mediaSeconds = stage_media(entry, public), entry["kind"], float(entry.get("seconds", 3.0))
            sc.credit = entry["game"]
            used.append(entry)
    if banked_game:
        stage_legacy_footage(project, public)
    if used:
        project.description = project.description.rstrip() + "\n\nGame footage: " + "; ".join(build_credits(used)) + " (official Steam store media)."
    return used


def _write_outputs(project: Any, video: Path, cover: Optional[Path]) -> tuple:
    """Copies the finished video (and its cover) into output/youtube/<title>/ and output/tiktok/<title>/ and writes the TikTok metadata file. Returns ({platform: mp4}, metadata path)."""
    from services.output_layout import timestamp_stem, video_dir
    from services.series import joined_hashtag
    stem = timestamp_stem()
    out = {}
    for platform in ("youtube", "tiktok"):
        d = video_dir(platform, project.title)
        shutil.copyfile(video, d / f"{stem}.mp4")
        out[platform] = d / f"{stem}.mp4"
        if cover:  # the cover sits next to each copy: <stem>.png (YouTube thumbnail, TikTok cover)
            shutil.copyfile(cover, d / f"{stem}.png")
    tags = list(dict.fromkeys(joined_hashtag(t) for t in project.tags))  # hashtags are always one joined word ("#techexplained", never "#tech explained")
    meta = out["tiktok"].with_suffix(".txt")
    meta.write_text(
        "=" * 80 + "\nSILICON VERDICT • MOTION GRAPHICS • TIKTOK & SHORTS METADATA\n"
        f"Creation Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\nVideo File: {out['tiktok'].name}\nTopic: {project.topic}\n" + "=" * 80
        + f"\n\n[TITLE]\n{project.title}\n\n[DESCRIPTION]\n{project.description}\n\n[HASHTAGS]\n{' '.join(tags)}\n\n[PINNED COMMENT]\n{project.pinned_comment}\n\n[SCENES]\n"
        + "\n".join(f"- {s.type}: {s.text} {s.accentText or ''}".rstrip() for s in project.scenes) + "\n",
        encoding="utf-8",
    )
    return out, meta


@dataclass
class PreparedVideo:
    """Everything that is decided before the render starts: the script, the footage and the narration. Made by `prepare_motion_video`, consumed by `finish_motion_video`."""
    project: Any
    game: Optional[str]
    catalog: Optional[dict]
    banked_game: bool
    run_id: str
    work: Path
    public: Path
    used_entries: list
    clips: list
    continuous: bool
    started: float


def prepare_motion_video(topic: Optional[str] = None, kind: str = "auto", fmt: str = "auto", source_text: Optional[str] = None, script: Optional[Any] = None, bank_only: bool = False) -> PreparedVideo:
    """First half of the pipeline (network work, no CPU-heavy rendering): chooses the subject, gets the script (bank, hand-written or LLM + fact-check), stages the footage and records the narration.
    Because it does not render, the next video of a batch can be prepared while the previous one renders. The arguments are those of `run_motion_pipeline`;
    bank_only=True takes a banked script of the format or fails (never asks the LLM)."""
    from services.motion_generator import FORMATS

    started = time.time()
    run_id = uuid.uuid4().hex[:8]
    if fmt == "any":
        kind, fmt = _draw_any_format()
    if fmt not in ("auto",) + tuple(FORMATS):
        raise ValueError(f"unknown format {fmt!r}: use auto, any or one of {FORMATS}")
    if fmt == "easter":
        kind = "game"
    elif fmt != "auto":
        kind = "curiosity"  # the other formats are told with motion graphics only
    format_name = None if fmt == "auto" else fmt
    if fmt == "news":  # the bulletin reads today's headlines (public RSS feeds) as its SOURCE TEXT
        from services.tech_news import build_source_text
        source_text = source_text or build_source_text()
        topic = topic or f"Tech briefing of {datetime.now(timezone.utc).strftime('%d %B %Y')}"
    facts = source_text if (source_text and topic and kind == "curiosity") else None

    project, game, facts, catalog, banked_game, kind = _select_source(kind, fmt, topic, facts, script, bank_only)
    logger.info("Motion Graphics (%s%s%s): '%s' (%d scenes)", project.kind, f", {game}" if game else "", f", format {format_name}" if format_name else "", project.title, len(project.scenes))
    work = Path(settings.TMP_DIR) / f"run_motion_{run_id}"
    public = work / "public"
    try:
        _prepare_project(project)
        public.mkdir(parents=True, exist_ok=True)
        used_entries = _stage_footage(project, catalog, banked_game, public)
        clips, continuous = narrate_scenes(project, work / "voice")  # the narration decides how long each scene lasts
    except BaseException:
        from services.story_bank import release_story  # a script taken from the bank is only spent by a video that was actually produced
        release_story(project)
        shutil.rmtree(work, ignore_errors=True)
        raise
    return PreparedVideo(project, game, catalog, banked_game, run_id, work, public, used_entries, clips, continuous, started)


def finish_motion_video(prep: PreparedVideo, export_only: bool = False, dry_run: bool = False, privacy: str = "public") -> Dict[str, Any]:
    """Second half: render, cover, sound, QA, output folders, optional YouTube upload and history. Always removes the work folder; a failure gives the banked script back."""
    from services.game_images import commit_media
    from services.history import record_short_history

    project, work, run_id = prep.project, prep.work, prep.run_id
    try:
        raw = render_motion(project.to_props(), work / "raw.mp4", prep.public)
        style = cover_style(project.title)
        cover = render_cover(project.to_props(), work / "cover.png", prep.public, style)
        starts, acc = [], 0
        for sc in project.scenes:
            starts.append(acc)
            acc += sc.durationInFrames
        video = add_sound(raw, work / "motion_master.mp4", starts, prep.clips, lead=0.0 if prep.continuous else VOICE_LEAD, kinds=[sc.type for sc in project.scenes],
                         music_file=music_bed(project.format, project.topic), info=scene_audio_info(project.scenes))

        fails = qa_motion(video)
        still = static_stretches(video)
        if still:
            logger.warning("Static stretches (%d s or more with almost nothing moving): %s", STATIC_SECONDS, ", ".join(f"{a:.1f}-{b:.1f}s" for a, b in still))
        if fails:
            logger.error("Video QA FAILED, it will not be uploaded: %s", "; ".join(fails))
            export_only = True  # only an objective technical failure of the video itself holds it back
        if not project.fact_checked:
            logger.warning("No reviewer could fact-check the script: publishing anyway (the script was still grounded and validated).")
        if prep.used_entries and not fails:  # the footage is spent only when a finished, checked video exists: delete it, never reuse it, blacklist the game 14 days
            commit_media([e["key"] for e in prep.used_entries], prep.game, project.title)

        out, meta = _write_outputs(project, video, cover)
        youtube_url, yt_id = f"file://{out['youtube'].resolve()}", f"local_export_{run_id}"
        if not export_only and not dry_run:
            try:
                from services.youtube import upload_video_resumable
                youtube_url = upload_video_resumable(file_path=str(out["youtube"]), title=project.title, description=project.description, tags=project.tags, privacy_status=privacy, is_short=True)
                yt_id = youtube_url.split("/")[-1]
            except Exception as exc:
                logger.error("YouTube upload failed (%s). Video kept locally.", exc)
                yt_id = f"local_{run_id}"
        try:
            record_short_history(weekday_index=datetime.now().weekday(), theme_key="motion_graphics", game_title=project.screen_title, voice_id_used="none", topic=project.topic,
                                 title=project.title, video_id=yt_id, category=("MOTION GRAPHICS " + project.format.upper()) if project.format else "MOTION GRAPHICS", tone="kinetic_typography", preset=f"remotion_motion:{project.look or 'obsidian'}")
        except Exception as exc:
            logger.warning("History not recorded: %s", exc)
        logger.info("Motion Graphics video ready in %.0fs: %s", time.time() - prep.started, out["tiktok"])
        return {"kind": project.kind, "format": project.format, "game": project.game, "youtube_video": str(out["youtube"]), "youtube_url": youtube_url, "tiktok_video": str(out["tiktok"]), "tiktok_metadata": str(meta),
                "title": project.title, "topic": project.topic, "qa_failures": fails, "uploaded": not export_only and not dry_run,
                "duration": project.total_frames / FPS, "tiktok_cover": str(out["tiktok"].with_suffix(".png")) if cover else "", "cover_style": style}
    except BaseException:
        from services.story_bank import release_story
        release_story(project)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)  # the render work dir (raw video, voice clips, staged footage) is never needed again


def run_motion_pipeline(topic: Optional[str] = None, export_only: bool = False, dry_run: bool = False, privacy: str = "public", kind: str = "auto", fmt: str = "auto",
                        source_text: Optional[str] = None, script: Optional[Any] = None) -> Dict[str, Any]:
    """Makes one video, start to finish. kind: curiosity | game | auto (a game video when a game with unused footage is not blacklisted, otherwise a curiosity).
    fmt: auto (the classic explainer) | any (a weighted random one) | one of FORMATS; `easter` is always a game video, the rest are curiosities.
    source_text: with kind='curiosity' and a topic, the real text the script must stick to (claims, dates and figures are checked against it).
    script: a MotionProject written by hand, used as it is (no model involved)."""
    prep = prepare_motion_video(topic=topic, kind=kind, fmt=fmt, source_text=source_text, script=script)
    return finish_motion_video(prep, export_only=export_only, dry_run=dry_run, privacy=privacy)
