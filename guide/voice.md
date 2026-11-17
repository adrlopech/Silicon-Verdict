# Voice

## Narrators

Three ElevenLabs voices are configured (`ELEVENLABS_VOICE_1..3` in `.env`): **Daniel**, **Adam** and **Liam**. Motion videos rotate the narrator by format when `MOTION_VOICE_ROTATION=true`
(otherwise Liam always speaks). The mapping is `VOICE_BY_FORMAT` in `services/motion_pipeline.py`:

| Narrator | Role | Formats |
|---|---|---|
| **Adam** (voice 2) | judges and explains | versus, myth, tier, hardware, evolution, fails, numbers, rumor, review, news |
| **Liam** (voice 3) | punches and guides | whatif, fix, simple, decode, top5, eli5, quiz, stop, the classic explainer, easter, every game video |
| **Daniel** (voice 1) | retired (2026-11-15) | no format uses him any more; his formats moved to Adam or Liam |

Videos uploaded before 15 Nov (some GTA VI ones) still carry Daniel's voice.

## How the narration is made

- ElevenLabs model `eleven_turbo_v2_5`, **one continuous take** per video with word-level timestamps, sliced per scene at the pause between two words. No time-stretching, so the voice always sounds natural.
- The timestamps drive each scene's length, the captions, the accent pulse and the cursor. A scene starts 0.12 s before the narrator speaks.
- Numbers are written in the script the way they are spoken.
- A robotic system voice is never published.

## Local backup voice

ElevenLabs credits are limited, so when a call fails (no credits, no network) the same three voices are served by a **local clone**. It is not a different narrator:
`services/local_tts.py` maps each ElevenLabs voice id to its reference clip in `assets/voice_refs/`.

- **Engine:** VoxCPM2 8-bit on MLX (`scripts/mlx_tts_server.py`, port 3901; Apache-2.0 weights, commercial use allowed), about 3 s of compute per second of audio on an M2. **Apple Silicon only.**
- **Timestamps:** the local ASR of [VoiceStudio](https://github.com/debpalash/voicestudio) (port 3900). Both services run headless.
- **One-time setup:** `brew tap debpalash/tap && brew install --cask debpalash/tap/voicestudio`, open VoiceStudio once, then make the reference clips with `.venv/bin/python scripts/make_voice_refs.py`
  (about 700 ElevenLabs characters; the clips are git-ignored). Do not enable the OmniVoice or NLLB models in VoiceStudio: their weights are non-commercial.
- **Run:** `scripts/voicestudio_server.sh start|stop|status`. The pipeline starts it on demand the first time ElevenLabs fails.
- **Settings (`.env`):** `TTS_BACKEND=elevenlabs` (default; `local` skips ElevenLabs), `LOCAL_TTS_FALLBACK=true`, `LOCAL_TTS_URL`, `MLX_TTS_URL`.

On a machine that is not Apple Silicon the backup does not run: keep ElevenLabs credits topped up, or port the engine (not done).
