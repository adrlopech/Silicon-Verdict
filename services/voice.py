"""ElevenLabs Voice Management and Round-Robin Rotation Service.

Manages the rotating pool of 3 distinct, active ElevenLabs voices:
- ELEVENLABS_VOICE_1: onwK4e9ZLuTAKqWW03F9 (Voice 1: Daniel - Steady Broadcaster)
- ELEVENLABS_VOICE_2: pNInz6obpgDQGcFmaJgB (Voice 2: Adam - Dominant, Firm)
- ELEVENLABS_VOICE_3: TX3LPaxmHKxFdv7VOQHJ (Voice 3: Liam - Energetic, Social Media Creator)

Implements strict sequential Round-Robin rotation (1 -> 2 -> 3 -> 1)
persisted in SQLite (data/history.db) so no consecutive shorts share the same voice.

Blacklisted voices (e.g. Roger / CwhRBWXzGAHq8TQ4Fs17) are permanently barred from generation.
"""
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple

from config.settings import settings
from services.history import get_last_used_voice

logger = logging.getLogger(__name__)

# Permanently blacklisted voice IDs that must NEVER be used in any video production
BLACKLISTED_VOICE_IDS: Set[str] = {
    "CwhRBWXzGAHq8TQ4Fs17",  # Roger - Laid-Back, Casual, Resonant (permanently banned)
    "QIhD5ivPGEoYZQDocuHI",  # Deprecated invalid voice ID
    "4N8zjn9tVNuDEBFWVHAq",  # Deprecated invalid voice ID
    "Nhs7eitvQWFTQBsf0yiT",  # Deprecated invalid voice ID
}

DEFAULT_APPROVED_POOL: List[str] = [
    "onwK4e9ZLuTAKqWW03F9",  # Daniel - Steady Broadcaster
    "pNInz6obpgDQGcFmaJgB",  # Adam - Dominant, Firm
    "TX3LPaxmHKxFdv7VOQHJ",  # Liam - Energetic, Social Media Creator
]


def get_ffmpeg_bin() -> str:
    return shutil.which("ffmpeg") or str(Path(sys.executable).parent / "ffmpeg") or "ffmpeg"


def get_ffprobe_bin() -> str:
    return shutil.which("ffprobe") or str(Path(sys.executable).parent / "ffprobe") or "ffprobe"


def measure_audio_duration(audio_path: Path) -> float:
    """Measures precise audio duration in seconds using ffprobe."""
    ffprobe_bin = get_ffprobe_bin()
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(res.stdout.strip())
    except Exception as exc:
        logger.warning("ffprobe measurement failed for %s (%s). Falling back.", audio_path, exc)
        return 0.0


def validate_and_enforce_long_video_duration(
    audio_path: Path,
    output_path: Path,
    min_duration: float = 60.5,
    target_min: float = 61.0,
    target_max: float = 68.0,
    total_words: int = 150,
) -> Tuple[Path, float, bool]:
    """Validates and enforces strict >60.5s duration (61.0s - 68.0s) for TikTok Creator Rewards.

    - If duration < 61.0s and between 59.0s and 60.9s: applies atempo=0.96 with FFmpeg
      to naturally extend the narration without acoustic pitch distortion.
    - If duration < 59.0s or total_words < 140: returns success=False indicating
      Gemini must regenerate and expand the technical explanation block.
    - If duration > 68.0s: applies minor speed adjustment to calibrate into 61.0s - 68.0s.

    Returns:
        (resulting_audio_path, final_duration_sec, is_compliant)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_duration = measure_audio_duration(audio_path)
    logger.info("TikTok Long Audio Duration Check: %.2fs (Words: %d)", raw_duration, total_words)

    # 1. Deficit check: if words < 140 or duration severely under 59.0s -> trigger regeneration
    if total_words < 140 or raw_duration < 59.0:
        logger.warning(
            "Audio duration (%.2fs) or word count (%d) is strictly below TikTok Creator Rewards threshold. "
            "Requires Gemini technical expansion.",
            raw_duration,
            total_words,
        )
        return audio_path, raw_duration, False

    # 2. Minimal difference (59.0s - 60.9s): stretch with atempo=0.96
    if raw_duration < target_min:
        ffmpeg_bin = get_ffmpeg_bin()
        logger.info(
            "Audio slightly under 61.0s (%.2fs). Applying atempo=0.96 to reach TikTok >60.5s threshold...",
            raw_duration,
        )
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(audio_path),
            "-filter:a", "atempo=0.96",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        new_dur = measure_audio_duration(output_path)
        logger.info("Duration calibrated via atempo=0.96: %.2fs -> %.2fs (>60.5s compliant)", raw_duration, new_dur)
        return output_path, new_dur, new_dur >= min_duration

    # 3. Excess duration (> 68.0s): gently compress into 61-68s
    if raw_duration > target_max:
        speed_factor = min(1.10, raw_duration / 65.0)
        ffmpeg_bin = get_ffmpeg_bin()
        logger.info(
            "Audio exceeds target window (%.2fs > %.2fs). Applying atempo=%.3f to fit 61-68s window...",
            raw_duration,
            target_max,
            speed_factor,
        )
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(audio_path),
            "-filter:a", f"atempo={speed_factor:.3f}",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        new_dur = measure_audio_duration(output_path)
        logger.info("Duration compressed: %.2fs -> %.2fs (61-68s compliant)", raw_duration, new_dur)
        return output_path, new_dur, new_dur >= min_duration

    # 4. Perfectly in 61.0s - 68.0s target window
    shutil.copy2(audio_path, output_path)
    logger.info("Audio duration %.2fs is strictly within the 61-68s TikTok monetization window.", raw_duration)
    return output_path, raw_duration, True


def get_voice_pool() -> List[str]:
    """Returns the ordered list of 3 ElevenLabs voice IDs configured for rotation,
    strictly excluding any blacklisted voice IDs.
    """
    raw_pool = [
        settings.ELEVENLABS_VOICE_1,
        settings.ELEVENLABS_VOICE_2,
        settings.ELEVENLABS_VOICE_3,
    ]
    # Filter out blacklisted or empty voice IDs
    clean_pool = [v for v in raw_pool if v and v not in BLACKLISTED_VOICE_IDS]

    # If all configured voices were invalid or blacklisted, enforce DEFAULT_APPROVED_POOL
    if len(clean_pool) < 3:
        for approved_id in DEFAULT_APPROVED_POOL:
            if approved_id not in clean_pool and approved_id not in BLACKLISTED_VOICE_IDS:
                clean_pool.append(approved_id)
            if len(clean_pool) == 3:
                break

    return clean_pool


def get_voice_label(voice_id: str) -> str:
    """Returns a readable label for the voice ID."""
    labels = {
        "onwK4e9ZLuTAKqWW03F9": "VOICE_1 (Daniel - Steady Broadcaster)",
        "pNInz6obpgDQGcFmaJgB": "VOICE_2 (Adam - Dominant, Firm)",
        "TX3LPaxmHKxFdv7VOQHJ": "VOICE_3 (Liam - Energetic, Social Media Creator)",
    }
    if voice_id in labels:
        return labels[voice_id]

    pool = get_voice_pool()
    if voice_id in pool:
        idx = pool.index(voice_id) + 1
        return f"VOICE_{idx} ({voice_id})"
    return f"VOICE_CUSTOM ({voice_id})"


def get_next_voice(db_path: Optional[Path] = None) -> str:
    """Selects the next ElevenLabs voice ID in strict Round-Robin sequence (1 -> 2 -> 3 -> 1).

    Queries data/history.db for the last used voice and advances by exactly 1 position.
    Guarantees no blacklisted voice is ever returned.

    Args:
        db_path: Optional custom path to SQLite database.

    Returns:
        str: Selected ElevenLabs voice ID.
    """
    pool = get_voice_pool()
    last_voice = get_last_used_voice(db_path=db_path)

    if not last_voice or last_voice not in pool or last_voice in BLACKLISTED_VOICE_IDS:
        selected_voice = pool[0]
        logger.info("Starting / resetting voice rotation with VOICE_1: %s", get_voice_label(selected_voice))
        return selected_voice

    last_index = pool.index(last_voice)
    next_index = (last_index + 1) % len(pool)
    selected_voice = pool[next_index]

    # Defensive check against blacklisted voice
    if selected_voice in BLACKLISTED_VOICE_IDS:
        logger.warning("Selected voice %s is blacklisted! Falling back to safe pool[0]", selected_voice)
        selected_voice = pool[0]

    logger.info(
        "Round-Robin Voice Rotation: Advancing from %s (Index %d) to %s (Index %d)",
        get_voice_label(last_voice),
        last_index + 1,
        get_voice_label(selected_voice),
        next_index + 1,
    )
    return selected_voice
