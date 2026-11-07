"""Persistent VoxCPM2 8-bit (MLX, Apache-2.0) narration server, ~6x faster than the PyTorch engine on Apple Silicon.

Run with VoiceStudio's Python (it ships mlx-audio):  <VoiceStudio venv>/bin/python scripts/mlx_tts_server.py
POST /speak  {"text": "...", "voice": "liam"}  ->  audio/wav (48 kHz mono).  GET /health.
Voices are the reference clips in assets/voice_refs/<voice>.mp3 with assets/voice_refs/reference_text.txt as transcript.
"""
import io
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "assets" / "voice_refs"
MODEL_ID = "mlx-community/VoxCPM2-8bit"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3901

from mlx_audio.tts.utils import load_model  # noqa: E402

model = load_model(MODEL_ID)
ref_text = (REFS / "reference_text.txt").read_text(encoding="utf-8").strip()


def speak(text: str, voice: str) -> bytes:
    ref = REFS / f"{voice}.mp3"
    if not ref.exists():
        raise FileNotFoundError(f"no reference clip for voice '{voice}'")
    parts = [np.array(r.audio).reshape(-1) for r in model.generate(
        text=text, ref_audio=str(ref), prompt_audio=str(ref), prompt_text=ref_text)]
    buf = io.BytesIO()
    sf.write(buf, np.concatenate(parts), model.sample_rate, format="WAV")
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        self._send(200, b'{"status":"ok"}', "application/json") if self.path == "/health" else self._send(404, b"{}", "application/json")

    def do_POST(self):  # noqa: N802
        if self.path != "/speak":
            return self._send(404, b"{}", "application/json")
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            self._send(200, speak(req["text"], req.get("voice", "liam")), "audio/wav")
        except Exception as exc:  # report to the caller instead of dropping the connection
            self._send(500, json.dumps({"error": str(exc)}).encode(), "application/json")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"mlx tts ready on 127.0.0.1:{PORT}", flush=True)
    HTTPServer((  # single thread on purpose: MLX streams belong to the thread that loaded the model
        "127.0.0.1", PORT), Handler).serve_forever()
