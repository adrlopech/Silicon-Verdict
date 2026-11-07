"""Generates the reference clips the local backup voice is cloned from: assets/voice_refs/{daniel,adam,liam}.mp3.

Uses the three ElevenLabs voices of the rotation pool (one ~15 s clip each, ~230 characters of credit per voice).
The clips are git-ignored; run this once per machine, then `scripts/voicestudio_server.sh start`.

    .venv/bin/python scripts/make_voice_refs.py
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import settings  # noqa: E402

REFS = settings.BASE_DIR / "assets" / "voice_refs"
VOICES = {"daniel": settings.ELEVENLABS_VOICE_1, "adam": settings.ELEVENLABS_VOICE_2, "liam": settings.ELEVENLABS_VOICE_3}


def main() -> int:
    if not settings.ELEVENLABS_API_KEY or settings.ELEVENLABS_API_KEY.startswith("your_"):
        print("ELEVENLABS_API_KEY is not set")
        return 1
    text = (REFS / "reference_text.txt").read_text(encoding="utf-8").strip()
    for name, voice in VOICES.items():
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
            headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
            json={"text": text, "model_id": "eleven_multilingual_v2"},
            timeout=120,
        )
        r.raise_for_status()
        (REFS / f"{name}.mp3").write_bytes(r.content)
        print(f"wrote {name}.mp3 ({len(r.content) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
