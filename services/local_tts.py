"""Local backup narration: VoxCPM2 8-bit on MLX (Apache-2.0 weights) cloned from the ElevenLabs voices, with word timestamps from VoiceStudio's local ASR.

Both services run headless (no app window) and are started on demand by scripts/voicestudio_server.sh:
  - scripts/mlx_tts_server.py  (port 3901) speaks the text using assets/voice_refs/<voice>.mp3 as the voice to clone
  - the VoiceStudio backend    (port 3900) transcribes the result to get word timings
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

ASR_URL = settings.LOCAL_TTS_URL.rstrip("/")
MLX_URL = settings.MLX_TTS_URL.rstrip("/")
SERVER_SCRIPT = settings.BASE_DIR / "scripts" / "voicestudio_server.sh"
MAX_CHARS = 1500  # longer text is split on sentence boundaries and the parts are joined
_lock = threading.Lock()  # one generation at a time: the model holds the whole GPU


def _voice_name(voice_id: Optional[str]) -> str:
    """Maps an ElevenLabs voice id to its reference clip name (assets/voice_refs/<name>.mp3)."""
    table = {settings.ELEVENLABS_VOICE_1: "daniel", settings.ELEVENLABS_VOICE_2: "adam", settings.ELEVENLABS_VOICE_3: "liam"}
    return table.get(voice_id or "", "liam")


def _up(url: str) -> bool:
    try:
        return requests.get(f"{url}/health", timeout=2).ok
    except requests.RequestException:
        return False


def ensure_server() -> None:
    """Starts the headless backends if they are not answering."""
    if _up(ASR_URL) and _up(MLX_URL):
        return
    logger.info("Starting the local voice backends (headless)...")
    res = subprocess.run([str(SERVER_SCRIPT), "start"], capture_output=True, text=True, timeout=240)
    if res.returncode != 0:
        raise RuntimeError(f"local voice backends did not start: {res.stdout.strip()} {res.stderr.strip()}")


def _split(text: str) -> List[str]:
    chunks: List[str] = []
    cur = ""
    for s in re.split(r"(?<=[.!?])\s+", text.strip()):
        if cur and len(cur) + len(s) + 1 > MAX_CHARS:
            chunks.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def _speech(text: str, voice: str, out_wav: Path) -> None:
    r = requests.post(f"{MLX_URL}/speak", json={"text": text, "voice": voice}, timeout=1800)
    if r.status_code != 200 or len(r.content) < 2000:
        raise RuntimeError(f"local speech failed (HTTP {r.status_code}): {r.text[:200]}")
    out_wav.write_bytes(r.content)


def _word_timestamps(wav: Path) -> List[Dict[str, Any]]:
    with open(wav, "rb") as fh:
        r = requests.post(
            f"{ASR_URL}/v1/audio/transcriptions",
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
    joined = raw_mp3.with_name(f"{raw_mp3.stem}_local.wav")
    with _lock:
        ensure_server()
        wavs = []
        for i, chunk in enumerate(_split(text)):
            wav = raw_mp3.with_name(f"{raw_mp3.stem}_part{i}.wav")
            _speech(chunk, voice, wav)
            wavs.append(wav)
        if len(wavs) == 1:
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
