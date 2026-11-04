"""Audio synthesis and modulation service for Silicon Verdict single master videos.

Calibrated for:
- tech_curiosities (Storytelling / Tecnología Desmontada):
  * Speed: 0.92x (measured, serene, didactic rhythm).
  * ElevenLabs Voice Settings:
      - stability: 0.75
      - similarity_boost: 0.80
      - style: 0.12 (calm/intellectual)
      - use_speaker_boost: True
- Hardware Benchmarks / Gaming:
  * Speed: 1.00x - 1.02x
  * Standard energetic narration settings.
- Generates a SINGLE master audio track per execution.
- Validates and enforces runtime strictly between 60.0 and 120.0 seconds.
"""
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from config.settings import settings
from services.tts import get_audio_duration, resolve_active_voice_id
from services.voice import get_ffmpeg_bin

logger = logging.getLogger(__name__)


def normalize_phonetics_us_english(text: str) -> str:
    """Normalizes acronyms and technical terms according to standard US English phonetic rules."""
    replacements = [
        (r"\b1440p\b", "fourteen-forty p"),
        (r"\b1080p\b", "ten-eighty p"),
        (r"\b4[kK]\b", "4-K"),
        (r"\bFPS\b", "F-P-S"),
        (r"\bfps\b", "F-P-S"),
        (r"\bRTX\b", "R-T-X"),
        (r"\bDLSS\b", "D-L-S-S"),
        (r"\bFSR\b", "F-S-R"),
        (r"\bPCIe\b", "P-C-I-e"),
        (r"\bVCSEL\b", "V-C-S-E-L"),
        (r"\bMEMS\b", "M-E-M-S"),
        (r"\bNFC\b", "N-F-C"),
        (r"\bGPS\b", "G-P-S"),
        (r"\bASML\b", "A-S-M-L"),
        (r"\bTSMC\b", "T-S-M-C"),
        (r"\bCCD\b", "C-C-D"),
        (r"\bCCDs\b", "C-C-Ds"),
        (r"\bSoIC\b", "S-O-I-C"),
        (r"\bIHS\b", "I-H-S"),
        (r"\bVRM\b", "V-R-M"),
        (r"\bVRMs\b", "V-R-Ms"),
        (r"\bGHz\b", "gigahertz"),
        (r"\bMHz\b", "megahertz"),
        (r"\bGbps\b", "gigabits per second"),
        (r"\bTbps\b", "terabits per second"),
        (r"\bnanoseconds\b", "nano-seconds"),
        (r"\bnanosecond\b", "nano-second"),
        (r"\bns\b", "nano-seconds"),
        (r"\bSRAM\b", "S-RAM"),
        (r"\bsub-11\b", "sub eleven"),
        (r"\bsub-eleven\b", "sub eleven"),
        (r"\bms\b", "milliseconds"),
    ]
    norm = text
    for pattern, repl in replacements:
        norm = re.sub(pattern, repl, norm)
    return norm


def synthesize_master_narration(
    text: str,
    output_path: Path,
    category: str = "tech_curiosities",
    voice_id: Optional[str] = None,
    speed: Optional[float] = None,
    min_duration: Optional[float] = None,
    max_duration: Optional[float] = None,
) -> Tuple[Path, float]:
    """Synthesizes the complete single master audio track with ElevenLabs modulation.

    Parameters:
    - text: Full text of the narration (approx 130-160 words for 55-70s tech_curiosities; 150-240 for 60-120s benchmarks).
    - output_path: Destination path for the master .mp3 audio.
    - category: Thematic category key (adjusts tone, speed, voice settings, and target duration).
    - voice_id: Optional voice ID override.
    - speed: Optional speed factor (defaults to 0.96 for tech_curiosities, 1.0 otherwise).
    - min_duration: Strict lower bound in seconds (defaults to 55.0s for tech_curiosities, 60.5s for others).
    - max_duration: Strict upper bound in seconds (defaults to 70.0s for tech_curiosities, 120.0s for others).

    Returns:
    - (final_audio_path, duration_seconds)
    """
    from services.voice_synthesizer import synthesize_voice_with_timestamps
    final_p, final_dur, _ = synthesize_voice_with_timestamps(
        text=text,
        output_audio_path=output_path,
        voice_id=voice_id,
        category=category,
        speed=speed,
        min_duration=min_duration,
        max_duration=max_duration,
    )
    return final_p, final_dur

    is_curiosity = (category == "tech_curiosities")
    effective_min_dur = min_duration if min_duration is not None else 55.0
    effective_max_dur = max_duration if max_duration is not None else 70.0
    effective_speed = speed if speed is not None else 1.02

    voice_settings = {
        "stability": 0.38,
        "similarity_boost": 0.85,
        "style": 0.32,
        "use_speaker_boost": True,
    }

    active_voice = resolve_active_voice_id(target_voice=voice_id)
    word_count = len(normalized_text.split())

    logger.info(
        "Synthesizing Master Narration (%d words | Category: %s | Target Duration: %.1fs-%.1fs | Speed: %.2fx)...",
        word_count, category, effective_min_dur, effective_max_dur, effective_speed,
    )

    synthesized_remotely = False
    if settings.ELEVENLABS_API_KEY and not settings.ELEVENLABS_API_KEY.startswith("your_"):
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{active_voice}"
        headers = {
            "xi-api-key": settings.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": normalized_text,
            "model_id": settings.ELEVENLABS_MODEL_ID or "eleven_turbo_v2_5",
            "voice_settings": voice_settings,
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=75)
            if res.status_code == 200 and len(res.content) > 1000:
                with open(raw_path, "wb") as f:
                    f.write(res.content)
                synthesized_remotely = True
                logger.info("ElevenLabs Master Audio synthesized successfully (%d bytes)", len(res.content))
            else:
                logger.warning(
                    "ElevenLabs API returned HTTP %d (%s). Falling back to local synthesizer.",
                    res.status_code, res.text[:120],
                )
        except Exception as exc:
            logger.warning("ElevenLabs connection error (%s). Falling back to local synthesizer.", exc)

    if not synthesized_remotely:
        # Local TTS fallback: macOS 'say' with native US English voice
        if shutil.which("say"):
            aiff_tmp = output_path.with_suffix(".aiff")
            try:
                rate = "172"
                subprocess.run(
                    ["say", "-v", "Samantha", "-r", rate, "-o", str(aiff_tmp), normalized_text],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                ffmpeg_bin = get_ffmpeg_bin()
                subprocess.run(
                    [ffmpeg_bin, "-y", "-i", str(aiff_tmp), "-c:a", "libmp3lame", "-b:a", "192k", str(raw_path)],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                if aiff_tmp.exists():
                    aiff_tmp.unlink()
                synthesized_remotely = True
                logger.info("macOS 'say' synthesizer generated raw audio successfully.")
            except Exception as exc:
                logger.warning("macOS 'say' fallback failed: %s", exc)

    if not synthesized_remotely:
        # Ultimate fallback: calibrated silence
        ffmpeg_bin = get_ffmpeg_bin()
        fallback_dur = max(65.0, word_count / 1.9)
        subprocess.run(
            [ffmpeg_bin, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{fallback_dur:.2f}", "-c:a", "libmp3lame", "-b:a", "192k", str(raw_path)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        logger.info("Generated calibrated fallback audio track (%.2fs)", fallback_dur)

    # Apply tempo modulation and enforce [min_duration, max_duration]
    ffmpeg_bin = get_ffmpeg_bin()
    raw_dur = get_audio_duration(str(raw_path))
    logger.info("Raw audio duration: %.2fs (Target speed: %.2fx)", raw_dur, effective_speed)

    # If speed adjustment is needed and duration allows:
    # Notice: speed < 1.0 (e.g. 0.92) lengthens audio (atempo=0.92)
    # Notice: speed > 1.0 (e.g. 1.05) shortens audio (atempo=1.05)
    atempo = effective_speed
    projected_dur = raw_dur / atempo

    # Check bounds against category-calibrated targets
    if projected_dur < effective_min_dur:
        # Need to slow down more to hit min_duration
        atempo = max(0.65, raw_dur / (effective_min_dur + 1.0))
        logger.info("Adjusting atempo to %.3f to ensure duration exceeds %.1fs", atempo, effective_min_dur)
    elif projected_dur > effective_max_dur:
        # Need to speed up to fit within max_duration
        atempo = min(1.40, raw_dur / (effective_max_dur - 1.5))
        logger.info("Adjusting atempo to %.3f to fit within %.1fs ceiling", atempo, effective_max_dur)

    # Process with FFmpeg atempo and trailing room buffer to prevent syllable cutoffs
    mod_dur = raw_dur / atempo
    filter_parts = []
    if abs(atempo - 1.0) > 0.01:
        filter_parts.append(f"atempo={atempo:.3f}")
    # Add trailing buffer (400ms) so final syllables/words are never truncated by audio cutoffs
    filter_parts.append("apad=pad_dur=0.40")
    total_pad_dur = mod_dur + 0.40
    fade_st = max(0.0, total_pad_dur - 0.15)
    filter_parts.append(f"afade=t=out:st={fade_st:.2f}:d=0.15")

    filter_str = ",".join(filter_parts)
    cmd_process = [
        ffmpeg_bin, "-y",
        "-i", str(raw_path),
        "-filter:a", filter_str,
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        str(output_path),
    ]
    subprocess.run(cmd_process, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    final_dur = get_audio_duration(str(output_path))
    logger.info(
        "Master audio finalized: %s (Duration: %.2fs | Monitored: %.1fs - %.1fs)",
        output_path.name, final_dur, effective_min_dur, effective_max_dur,
    )
    return output_path, final_dur


def mix_schematic_soundtrack(
    voice_audio_path: Path,
    output_audio_path: Path,
    act_durations: List[float],
) -> Path:
    """Mixes a serene background synthwave ambient track (-22 dB) and synchronized tech SFX at act transitions.

    - Audio Bed: assets/audio/schematic_ambient.wav looped at -22 dB (volume ~0.08) with gentle outro fade.
    - Synchronized UI SFX:
        * Act 1 (0.0s): sfx_whoosh.wav (kinetic card slide in)
        * Act 2: sfx_blip.wav (specs telemetry card)
        * Act 3: sfx_blip.wav (human analogy comparison)
        * Act 4: sfx_whoosh.wav (engineering resolution card)
        * Act 5: sfx_blip.wav (community debate poll card)
    """
    output_audio_path = Path(output_audio_path).resolve()
    ffmpeg_bin = get_ffmpeg_bin()
    voice_dur = get_audio_duration(str(voice_audio_path))

    ambient_path = settings.BASE_DIR / "assets" / "audio" / "schematic_ambient.wav"
    sfx_whoosh = settings.BASE_DIR / "assets" / "audio" / "sfx_whoosh.wav"
    sfx_blip = settings.BASE_DIR / "assets" / "audio" / "sfx_blip.wav"

    if not ambient_path.is_file() or not sfx_whoosh.is_file() or not sfx_blip.is_file():
        logger.warning("Schematic audio assets not found. Copying voice narration directly.")
        shutil.copyfile(voice_audio_path, output_audio_path)
        return output_audio_path

    # Compute exact act start offsets in milliseconds
    act_starts_ms = [0]
    cumulative = 0.0
    for d in act_durations[:-1]:
        cumulative += d
        act_starts_ms.append(int(cumulative * 1000))

    t1 = act_starts_ms[0] + 50
    t2 = act_starts_ms[1] + 50 if len(act_starts_ms) > 1 else 12000
    t3 = act_starts_ms[2] + 50 if len(act_starts_ms) > 2 else 24000
    t4 = act_starts_ms[3] + 50 if len(act_starts_ms) > 3 else 38000
    t5 = act_starts_ms[4] + 50 if len(act_starts_ms) > 4 else 52000

    filter_complex = (
        f"[0:a]volume=1.0[voice];"
        f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{voice_dur:.2f},volume=0.08,afade=t=out:st={max(0.0, voice_dur - 1.5):.2f}:d=1.5[amb];"
        f"[2:a]adelay={t1}|{t1},volume=0.25[sfx1];"
        f"[3:a]adelay={t2}|{t2},volume=0.20[sfx2];"
        f"[3:a]adelay={t3}|{t3},volume=0.20[sfx3];"
        f"[2:a]adelay={t4}|{t4},volume=0.25[sfx4];"
        f"[3:a]adelay={t5}|{t5},volume=0.20[sfx5];"
        f"[voice][amb][sfx1][sfx2][sfx3][sfx4][sfx5]amix=inputs=7:duration=first:dropout_transition=2[out]"
    )

    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(voice_audio_path),
        "-i", str(ambient_path),
        "-i", str(sfx_whoosh),
        "-i", str(sfx_blip),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        str(output_audio_path),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        logger.info("Schematic sound design mixed successfully: ambient at -22 dB + 5 synchronized SFX cues.")
        return output_audio_path
    except Exception as exc:
        logger.warning("Failed to mix soundtrack (%s). Reverting to clean voice track.", exc)
        shutil.copyfile(voice_audio_path, output_audio_path)
        return output_audio_path
