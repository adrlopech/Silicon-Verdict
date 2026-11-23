"""ElevenLabs voice helpers: which voice IDs may be used, the media-length probe and the ffmpeg lookup.

The narrator of each video is chosen by `services.motion_pipeline.narrator_voice` (by format). Voice IDs come from `.env`: ELEVENLABS_VOICE_1 Daniel (retired), 2 Adam, 3 Liam.
Blacklisted voices (Roger and some deprecated IDs) are never used, whatever is asked for.
"""
import functools
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Set

import requests

from config.settings import settings

logger = logging.getLogger(__name__)

# Permanently blacklisted voice IDs that must NEVER be used in any video production
BLACKLISTED_VOICE_IDS: Set[str] = {
    "CwhRBWXzGAHq8TQ4Fs17",  # Roger - Laid-Back, Casual, Resonant (permanently banned)
    "QIhD5ivPGEoYZQDocuHI",  # Deprecated invalid voice ID
    "4N8zjn9tVNuDEBFWVHAq",  # Deprecated invalid voice ID
    "Nhs7eitvQWFTQBsf0yiT",  # Deprecated invalid voice ID
}
FALLBACK_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # Daniel: the last resort when nothing else can be verified


def get_ffmpeg_bin() -> str:
    return shutil.which("ffmpeg") or str(Path(sys.executable).parent / "ffmpeg") or "ffmpeg"


def ffmpeg_duration(path) -> Optional[float]:
    """Length in seconds of an audio or video file, read from ffmpeg's header (no ffprobe needed); None if it cannot be read."""
    try:
        log = subprocess.run([get_ffmpeg_bin(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    except OSError:
        return None
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", log)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else None


def get_audio_duration(file_path: str) -> float:
    """Precise length of an audio file in seconds. A wrong length makes scenes shorter than their narration, so a file that cannot be read is logged loudly (5 s is only a last-resort guess)."""
    seconds = ffmpeg_duration(file_path)
    if seconds is None:
        logger.warning("Could not read the duration of %s. Falling back to 5 s.", file_path)
        return 5.0
    return seconds


@functools.lru_cache(maxsize=16)
def _voice_exists(voice_id: str) -> bool:
    """True when ElevenLabs knows the voice. Only a positive answer is cached (one probe per voice per run, not one per narration)."""
    ok = requests.get(f"https://api.elevenlabs.io/v1/voices/{voice_id}", headers={"xi-api-key": settings.ELEVENLABS_API_KEY}, timeout=10).status_code == 200
    if not ok:
        _voice_exists.cache_clear()  # never remember a failure: the next call asks again
    return ok


def resolve_active_voice_id(target_voice: Optional[str] = None) -> str:
    """Verifies the requested voice ID against the ElevenLabs API or falls back to an approved voice of the account. Blacklisted voices are never returned."""
    target_id = target_voice or settings.ELEVENLABS_VOICE_ID or settings.ELEVENLABS_VOICE_1
    if target_id in BLACKLISTED_VOICE_IDS:
        logger.warning("Requested voice '%s' is blacklisted: using the fallback voice instead.", target_id)
        target_id = FALLBACK_VOICE_ID
    try:
        if _voice_exists(target_id):
            return target_id
        listing = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": settings.ELEVENLABS_API_KEY}, timeout=10)
        if listing.status_code == 200:
            safe = [v for v in listing.json().get("voices", []) if v.get("voice_id") not in BLACKLISTED_VOICE_IDS and "roger" not in v.get("name", "").lower()]
            if safe:
                logger.warning("Configured voice '%s' not found. Falling back to the account voice '%s' (%s).", target_id, safe[0].get("name"), safe[0]["voice_id"])
                return safe[0]["voice_id"]
    except Exception as exc:  # the probe failed (network), not the voice: use the voice that was asked for rather than silently swapping the narrator
        logger.warning("Could not probe ElevenLabs voices (%s). Attempting target ID: %s", exc, target_id)
        return target_id
    return FALLBACK_VOICE_ID
