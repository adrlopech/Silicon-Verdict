# Development

## Checks

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest                      # unit tests in tests/
.venv/bin/ruff check .                          # lint (pyproject.toml)
cd remotion_studio && npx tsc --noEmit -p .     # type-check the Remotion project
python3 docs/check_portal.py                    # every local link, script and #anchor of the web portal exists
```

`tests/` covers the Motion validators (including every format and every banked script), the story bank, the game registry, output layout and the database connection.
`tests/test_motion_validators.py` also runs two ffmpeg tests of the audio mix, so ffmpeg must be installed.

**CI** (`.github/workflows/ci.yml`) runs on every push to `main` and every pull request, in three jobs: *python* (installs ffmpeg and all of `requirements.txt` plus `requirements-dev.txt`, then `ruff check .` and `pytest`),
*remotion* (`npm ci` and `tsc --noEmit`) and *portal* (`docs/check_portal.py`). A failing job sends an email: fix it rather than muting it.
A second workflow, `latest-video.yml`, runs every 15 minutes, reads the channel's public feed and updates the "Latest video" card of the portal (`scripts/update_latest_video.py`); it commits only when a new public video appeared.

## Repository map

| Path | Purpose |
|---|---|
| `main.py` | Command-line entry point for one video (calls `run_motion_pipeline`) |
| `config/settings.py` | All settings (read from `.env`): keys, models, voices, token path, video sizes |
| `services/motion_generator.py` | Schema (`MotionProject`, `MotionSceneModel`), prompts, `FORMATS`, validators, fact-check, cursor and UI rules |
| `services/motion_pipeline.py` | `prepare_motion_video` (script, footage, voice) and `finish_motion_video` (render, cover, sound, QA, files, upload); `run_motion_pipeline` runs both |
| `services/gemini_client.py` | The single LLM entry point: Gemini, Cloudflare, cooldowns, batching, images |
| `services/looks.py`, `services/series.py` | Look choice; series names and numbers |
| `services/tech_news.py` | RSS headlines for the news format |
| `services/game_*.py` | Game footage, one-use ledger, 14-day blacklist, source dossiers |
| `services/story_bank.py`, `services/history.py` | The script bank and `data/history.db` (history, registry, bank) |
| `services/youtube.py`, `services/yt_analytics.py` | Upload and thumbnails; Analytics reader |
| `services/notify.py`, `scripts/health_check.py` | macOS/webhook notifications (`NOTIFY_WEBHOOK`); pre-batch health check |
| `services/voice.py`, `voice_synthesizer.py`, `local_tts.py` | ElevenLabs and the local backup |
| `services/output_layout.py`, `services/cleaner.py` | Folders per video; the `limpieza` cleaner |
| `remotion_studio/src/motion/` | The video (see [Motion engine](motion-engine.md)) |
| `scripts/genera_batch.py` | The four-videos-a-day command |
| `services/prices.py`, `scripts/build_every_script.py`, `scripts/save_prices.py`, `scripts/pccomponentes_prices.js`, `data/products/`, `data/prices/` | Product datasets, price files and the "Every X at today's price" builder ([Prices](prices.md)) |
| `scripts/` (others) | Upload, bank, footage, analytics, auth, previews, brand assets, portal tools (see `main.py help`) |
| `data/` | `history.db`, manifests (`batches/`, git-ignored), `scripts/` (hand-written MotionProjects), `topic_facts/` (source texts), `game_facts/`, `games_catalog.json`, token (git-ignored) |
| `assets/` | Fonts, audio beds and effects, voice references, game footage, brand art |
| `docs/` | The public portal (GitHub Pages from `/docs`), terms and privacy pages, the banked scripts in `docs/generated_scripts/` |
| `guide/` | This documentation |
| `notes/` | Private research notes (git-ignored) |
| `tests/` | pytest suite |

## Conventions

- The project commits and pushes straight to `main`; there are no feature branches.
- Python modules start with a docstring that says what they do and how to run them. Keep it true when you change behaviour.
- A new script rule goes in the prompt **and** in a validator, and gets a test.
- Never apply camera transforms to the text layer of a scene (see [Motion engine](motion-engine.md#layers-camera-and-legibility)).
- Avoid decimals in counter scenes: the counter rounds them.
- Use `requests` for HTTP (plain `urllib` fails with SSL certificates on this Mac).
- Use Python (or the editor) to edit files in scripts: macOS `sed -i` needs a backup argument.
- ffmpeg is `.venv/bin/ffmpeg` (found by `get_ffmpeg_bin()`), not on `PATH`; `scripts/genera_batch.py` uses the same one for the TikTok copy.

## The portal

`docs/` is a static site (GitHub Pages, `.nojekyll`): `index.html` (hero, formats, cursor, looks), `changelog.html` (built from `git log` by `scripts/build_updates_page.py`), `terms.html`, `privacy.html`,
`callback.html` and the TikTok developer verification files. Pages rebuild on every push. After editing, run `python3 docs/check_portal.py`.
Assets of the portal come from `scripts/make_portal_assets.py` and `scripts/make_brand_assets.py`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `invalid_grant: Token has been expired or revoked` | The OAuth token was revoked or expired (the app is in Production since 2026-11-23, so this should be rare). Renew it: [Publishing](publishing.md#youtube-oauth) |
| A `genera` slot says `FAILED (nothing uploaded for this slot)` | Gemini 503/504 and validator rejections. Retry with a topics file, a proven format or a hand-written script: [Daily workflow](daily-workflow.md#when-a-slot-fails) |
| `FileNotFoundError: .../bin/ffmpeg` | ffmpeg is not installed where `get_ffmpeg_bin()` looks. Install it (CI installs it with apt) |
| YouTube `uploadLimitExceeded` | Daily upload limit. Wait about 24 hours, then `scripts/retry_youtube_uploads.py <manifest>` |
| Text in a video vibrates | A camera transform reached the text layer. It belongs on the backdrop only |
| Sound effects louder than the voice | Adjust `CUE_TARGET_DB` / `WHOOSH_TARGET_DB` in `services/motion_pipeline.py` |
| TikTok hashtag is plain text | It was typed but not picked from the dropdown. Retype it and click the first row |
| TikTok says "¿Seguir con la publicación?" | Review still running; "Publicar ahora" continues the scheduled post |
| ElevenLabs out of credits | The local clone takes over on Apple Silicon ([Voice](voice.md)); otherwise top up credits |
| A video has no cover | The cover is best effort (`render_cover`); render it by hand with `scripts/render_cover.mjs` and upload it |
| CI email "Run failed" | Open the run with `gh run view <id> --log-failed` and fix the cause |

## Render speed (measured 2026-11-23)

A 75 s video renders in about 55 s (x264 `veryfast`). Switching off the BigFx layer or the Ambient layer changed nothing (53 s, 53 s and 54 s against 53-56 s), and neither did the bundle cache (bundling takes 0.9 s),
the concurrency setting or memoising the scene plan. So those effects are not worth lightening: the time goes to Chrome painting the frames and to encoding. Measure with a temporary edit and the same props before touching them.
