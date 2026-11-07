"""Local narration through VoiceStudio (VoxCPM2, Apache-2.0 weights) with word timestamps from its local ASR.

Runs headless: the backend is started on demand with scripts/voicestudio_server.sh, no app window.
Each ElevenLabs voice used by the project is mapped to a cloned VoiceStudio profile ("SV liam", ...),
built from reference clips in assets/voice_refs/ (see ensure_profiles).
"""
import logging
import re
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from config.settings import settings
from services.voice import get_ffmpeg_bin

logger = logging.getLogger(__name__)

BASE_URL = settings.LOCAL_TTS_URL.rstrip("/")
REFS_DIR = settings.BASE_DIR / "assets" / "voice_refs"
SERVER_SCRIPT = settings.BASE_DIR / "scripts" / "voicestudio_server.sh"
MLX_URL = settings.MLX_TTS_URL.rstrip("/")
USE_MLX = settings.LOCAL_TTS_ENGINE.lower() == "mlx"  # VoxCPM2 8-bit on MLX: ~6x faster than the PyTorch engine
MAX_CHARS = 1500  # VoxCPM2 stays stable on a few sentences at a time; longer text is split on sentence boundaries
_lock = threading.Lock()  # one generation at a time: the model holds the whole GPU
_profile_cache: Dict[str, str] = {}


def _voice_name(voice_id: Optional[str]) -> str:
    """Maps an ElevenLabs voice id to the matching cloned profile name."""
    table = {
        settings.ELEVENLABS_VOICE_1: "SV daniel",
        settings.ELEVENLABS_VOICE_2: "SV adam",
        settings.ELEVENLABS_VOICE_3: "SV liam",
    }
    return table.get(voice_id or "", settings.LOCAL_TTS_VOICE)


def _up(url: str) -> bool:
    try:
        return requests.get(f"{url}/health", timeout=2).ok
    except requests.RequestException:
        return False


def ensure_server() -> None:
    """Starts the headless backends (VoiceStudio for ASR/timestamps, plus the MLX narration server) if they are not answering."""
    if _up(BASE_URL) and (not USE_MLX or _up(MLX_URL)):
        return
    logger.info("Starting the VoiceStudio backend (headless)...")
    res = subprocess.run([str(SERVER_SCRIPT), "start"], capture_output=True, text=True, timeout=180)
    if res.returncode != 0:
        raise RuntimeError(f"VoiceStudio backend did not start: {res.stdout.strip()} {res.stderr.strip()}")


def ensure_profiles() -> None:
    """Creates the cloned voice profiles from assets/voice_refs/*.mp3 when they do not exist yet."""
    ensure_server()
    existing = {p["name"] for p in requests.get(f"{BASE_URL}/profiles", timeout=10).json()}
    ref_text = (REFS_DIR / "reference_text.txt").read_text(encoding="utf-8").strip()
    for ref in sorted(REFS_DIR.glob("*.mp3")):
        name = f"SV {ref.stem}"
        if name in existing:
            continue
        with open(ref, "rb") as fh:
            r = requests.post(f"{BASE_URL}/profiles", data={"name": name, "ref_text": ref_text, "language": "en"},
                              files={"ref_audio": (ref.name, fh, "audio/mpeg")}, timeout=60)
        r.raise_for_status()
        logger.info("Created voice profile %s", name)


def _split(text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: List[str] = []
    cur = ""
    for s in sentences:
        if cur and len(cur) + len(s) + 1 > MAX_CHARS:
            chunks.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def _speech(text: str, voice: str, out_wav: Path) -> None:
    if USE_MLX:
        r = requests.post(f"{MLX_URL}/speak", json={"text": text, "voice": voice.removeprefix("SV ")}, timeout=1800)
        if r.status_code != 200 or len(r.content) < 2000:
            raise RuntimeError(f"MLX speech failed (HTTP {r.status_code}): {r.text[:200]}")
        out_wav.write_bytes(r.content)
        return
    r = requests.post(
        f"{BASE_URL}/v1/audio/speech",
        json={"model": settings.LOCAL_TTS_MODEL, "input": text, "voice": voice, "response_format": "wav", "language": "en"},
        timeout=1800,
    )
    if r.status_code != 200 or len(r.content) < 2000:
        raise RuntimeError(f"VoiceStudio speech failed (HTTP {r.status_code}): {r.text[:200]}")
    out_wav.write_bytes(r.content)


def _word_timestamps(wav: Path) -> List[Dict[str, Any]]:
    with open(wav, "rb") as fh:
        r = requests.post(
            f"{BASE_URL}/v1/audio/transcriptions",
            files={"file": (wav.name, fh, "audio/wav")},
            data={"model": "whisper-1", "response_format": "verbose_json", "timestamp_granularities[]": "word"},
            timeout=600,
        )
    r.raise_for_status()
    out = []
    for w in r.json().get("words", []):
        token = re.sub(r"[^\w\+\%\$\#\-\'\.]", "", w["word"]).strip()
        if token:
            out.append({"word": token, "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3)})
    return out


def synthesize(text: str, raw_mp3: Path, voice_id: Optional[str] = None, timestamps: bool = True) -> List[Dict[str, Any]]:
    """Writes the narration to raw_mp3 (192k) and returns word timestamps ([] when timestamps=False)."""
    raw_mp3 = Path(raw_mp3)
    raw_mp3.parent.mkdir(parents=True, exist_ok=True)
    voice = _voice_name(voice_id)
    with _lock:
        ensure_server()
        if not USE_MLX and voice not in _profile_cache:
            ensure_profiles()
            _profile_cache[voice] = voice
        wavs: List[Path] = []
        for i, chunk in enumerate(_split(text)):
            wav = raw_mp3.with_name(f"{raw_mp3.stem}_part{i}.wav")
            _speech(chunk, voice, wav)
            wavs.append(wav)
        joined = raw_mp3.with_suffix(".wav") if len(wavs) == 1 else raw_mp3.with_name(f"{raw_mp3.stem}_joined.wav")
        if len(wavs) == 1:
            if wavs[0] != joined:
                wavs[0].replace(joined)
        else:
            listing = raw_mp3.with_name(f"{raw_mp3.stem}_list.txt")
            listing.write_text("".join(f"file '{w.resolve()}'\n" for w in wavs))
            subprocess.run([get_ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(joined)],
                           check=True, capture_output=True)
            for w in wavs:
                w.unlink(missing_ok=True)
            listing.unlink(missing_ok=True)
        words = _word_timestamps(joined) if timestamps else []
    subprocess.run([get_ffmpeg_bin(), "-y", "-i", str(joined), "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", str(raw_mp3)],
                   check=True, capture_output=True)
    joined.unlink(missing_ok=True)
    return words
