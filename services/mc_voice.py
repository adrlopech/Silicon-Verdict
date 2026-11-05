"""ElevenLabs narration for the Minecraft series: one clip per beat, placed at the beat's start in the compiled timeline."""
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Tuple

from config.settings import settings
from core.schemas import McStory
from services import voice_synthesizer
from services.voice_synthesizer import synthesize_voice_with_timestamps

logger = logging.getLogger(__name__)
FPS = 30
TAIL = 0.35  # silence kept after each spoken line so the next beat never overlaps


def narrate_beats(story: McStory, work_dir: Path) -> List[Tuple[int, Path, float]]:
    """Synthesizes every beat's text and raises each beat's minimum on-screen time to fit its line. Returns (beat_index, mp3, duration)."""
    work_dir.mkdir(parents=True, exist_ok=True)
    spoken = [b.text for b in story.beats]
    spoken[-1] = f"{spoken[-1]} {story.cta.capitalize()}."  # the call to action is voiced, not only written

    def one(i: int) -> Tuple[int, Path, float]:
        path, dur, _ = synthesize_voice_with_timestamps(
            spoken[i], work_dir / f"beat_{i:02d}.mp3", voice_id=settings.ELEVENLABS_VOICE_3, model_id="eleven_multilingual_v2",
            natural=True, min_duration=None, max_duration=None, stability=0.32, style=0.5,
        )
        return i, path, dur

    before = voice_synthesizer.FALLBACK_COUNT
    with ThreadPoolExecutor(max_workers=4) as pool:  # independent lines: synthesize in parallel, order preserved
        clips = list(pool.map(one, range(len(story.beats))))
    if voice_synthesizer.FALLBACK_COUNT != before:
        raise RuntimeError("ElevenLabs failed for some lines (a robotic local voice would have been used): not producing this video")
    for i, _path, dur in clips:
        story.beats[i].seconds = round(max(story.beats[i].seconds or 0.0, dur + TAIL), 2)
    logger.info("Narration ready: %d lines, %.1f s of speech", len(clips), sum(c[2] for c in clips))
    return clips
