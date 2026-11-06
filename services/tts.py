import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import requests

from config.settings import settings
from core.schemas import Scene
from services.voice import BLACKLISTED_VOICE_IDS

logger = logging.getLogger(__name__)


@dataclass
class SceneAudio:
    """Metadata container for synthesized scene audio."""
    scene_id: int
    audio_path: str
    duration_seconds: float


def get_audio_duration(file_path: str) -> float:
    """Measures precise audio duration in seconds using ffprobe.

    Args:
        file_path: Path to the audio file.

    Returns:
        float: Duration in seconds.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as exc:
        # No ffprobe on this machine (only the bundled ffmpeg): read the real length from ffmpeg's header instead of guessing,
        # because a wrong length makes scenes shorter than their narration and the voice runs over the next scene.
        try:
            import re
            from services.voice import get_ffmpeg_bin
            log = subprocess.run([get_ffmpeg_bin(), "-hide_banner", "-i", file_path], capture_output=True, text=True).stderr
            m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", log)
            if m:
                return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
        except Exception:
            pass
        logger.warning("Could not read duration for %s (%s). Falling back to approximation.", file_path, exc)
        return 5.0


def resolve_active_voice_id(target_voice: Optional[str] = None) -> str:
    """Verifies requested voice ID against ElevenLabs API or falls back to an available approved voice.
    Permanently excludes any blacklisted voice (e.g. Roger / CwhRBWXzGAHq8TQ4Fs17).
    """
    target_id = target_voice or settings.ELEVENLABS_VOICE_ID or settings.ELEVENLABS_VOICE_1

    # Immediate rejection if requested voice is blacklisted
    if target_id in BLACKLISTED_VOICE_IDS:
        logger.warning(
            "Requested voice '%s' is in BLACKLISTED_VOICE_IDS! Barring usage and searching safe approved alternative.",
            target_id,
        )
        target_id = "onwK4e9ZLuTAKqWW03F9"  # Daniel default

    headers = {"xi-api-key": settings.ELEVENLABS_API_KEY}
    try:
        check = requests.get(f"https://api.elevenlabs.io/v1/voices/{target_id}", headers=headers, timeout=10)
        if check.status_code == 200:
            return target_id

        # Fallback: query account voices excluding blacklisted
        list_res = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers, timeout=10)
        if list_res.status_code == 200:
            voices = list_res.json().get("voices", [])
            # Filter out blacklisted voices and Roger specifically
            safe_voices = [
                v for v in voices
                if v.get("voice_id") not in BLACKLISTED_VOICE_IDS and "roger" not in v.get("name", "").lower()
            ]
            if safe_voices:
                fallback_id = safe_voices[0]["voice_id"]
                logger.warning(
                    "Configured Voice ID '%s' not found. Falling back to approved account voice '%s' (ID: %s)",
                    target_id, safe_voices[0].get("name"), fallback_id
                )
                return fallback_id
    except Exception as exc:
        logger.warning("Could not probe ElevenLabs voices (%s). Attempting target ID: %s", exc, target_id)

    return "onwK4e9ZLuTAKqWW03F9"


def synthesize_scene_audio(scene: Scene, output_dir: Path, voice_id: Optional[str] = None) -> SceneAudio:
    """Synthesizes voiceover for a single scene using ElevenLabs REST API.

    Args:
        scene: Scene schema object containing voiceover_text and scene_id.
        output_dir: Directory where the .mp3 file will be saved.
        voice_id: Optional ElevenLabs voice ID to use.

    Returns:
        SceneAudio: Dataclass with the file path and verified duration.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_file = output_dir / f"scene_{scene.scene_id:03d}.mp3"

    active_voice_id = resolve_active_voice_id(target_voice=voice_id)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{active_voice_id}"
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": scene.voiceover_text,
        "model_id": settings.ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.1,
            "use_speaker_boost": True,
        },
    }

    logger.info("Generating ElevenLabs TTS for scene %d (words: %d)", scene.scene_id, len(scene.voiceover_text.split()))

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        error_msg = f"ElevenLabs API error (status {response.status_code}): {response.text}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    with open(audio_file, "wb") as f:
        f.write(response.content)

    duration = get_audio_duration(str(audio_file))
    logger.info("Audio saved for scene %d: %s (duration: %.2fs)", scene.scene_id, audio_file.name, duration)

    return SceneAudio(scene_id=scene.scene_id, audio_path=str(audio_file), duration_seconds=duration)


def synthesize_all_scenes(scenes: List[Scene], output_dir: Path) -> List[SceneAudio]:
    """Iterates through all scenes and generates sequential narration audio files.

    Args:
        scenes: List of Scene definitions.
        output_dir: Target directory for audio assets.

    Returns:
        List[SceneAudio]: List of scene audio metadata objects.
    """
    audio_results: List[SceneAudio] = []
    for scene in scenes:
        audio = synthesize_scene_audio(scene, output_dir)
        audio_results.append(audio)
    return audio_results


def synthesize_speech(
    text: str,
    output_file: Path,
    voice_id: Optional[str] = None,
) -> float:
    """Synthesizes text using ElevenLabs REST API with graceful local fallback.

    Args:
        text: Text to narrate.
        output_file: Target .mp3 file path.
        voice_id: ElevenLabs voice ID or None for active default.

    Returns:
        float: Verified audio duration in seconds.
    """
    output_file = Path(output_file).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    active_voice_id = resolve_active_voice_id(target_voice=voice_id)

    if settings.ELEVENLABS_API_KEY and not settings.ELEVENLABS_API_KEY.startswith("your_"):
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{active_voice_id}"
        headers = {
            "xi-api-key": settings.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": settings.ELEVENLABS_MODEL_ID,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.1,
                "use_speaker_boost": True,
            },
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200 and len(response.content) > 1000:
                with open(output_file, "wb") as f:
                    f.write(response.content)
                dur = get_audio_duration(str(output_file))
                logger.info("ElevenLabs TTS synthesized successfully (%d words, %.2fs, voice=%s)", len(text.split()), dur, active_voice_id)
                return dur
            else:
                logger.warning("ElevenLabs API returned HTTP %d: %s. Using local fallback.", response.status_code, response.text[:120])
        except Exception as exc:
            logger.warning("ElevenLabs TTS network failure (%s). Using local fallback.", exc)

    # Local fallback: try macOS 'say' command if available, otherwise synthesize via ffmpeg
    if shutil.which("say"):
        aiff_tmp = output_file.with_suffix(".aiff")
        try:
            subprocess.run(["say", "-r", "148", "-o", str(aiff_tmp), text], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["ffmpeg", "-y", "-i", str(aiff_tmp), "-c:a", "libmp3lame", "-b:a", "192k", str(output_file)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if aiff_tmp.exists():
                aiff_tmp.unlink()
            return get_audio_duration(str(output_file))
        except Exception:
            pass

    # Pure fallback: generate calibrated silence
    est_dur = max(3.0, len(text.split()) / 2.3)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{est_dur:.2f}", "-c:a", "libmp3lame", "-b:a", "192k", str(output_file)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return est_dur
