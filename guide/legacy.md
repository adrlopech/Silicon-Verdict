# Legacy code

Before November 2026 the studio made 25-45 second infographic Shorts (Apple "Liquid Glass" and "Schematic Tech" presets, 60 fps, hand-rolled subtitles) from a 30-topic queue and a six-day rotation.
Everything is now made by the Motion pipeline, but the old code is still in the repository. **You can ignore it for daily work.** This page says what it is so that nobody mistakes it for the current system.

## What is current and what is not

| Old thing | Status |
|---|---|
| `main.py --category 1 / 2 / 3 / auto` | Still accepted, but `motion_route()` turns it into a Motion video: 1 is `hardware`, 2 is a game video (hardware if no footage), 3 and auto end up as `simple` |
| `--series hardware`, `--series simple` | Shortcuts for the Motion formats of the same name |
| `main.py --format short\|master\|long`, `--preset liquid_glass\|schematic_tech`, `--choice`, `--interactive` | Belong to the old pipeline. The Motion flow does not use them |
| `core/` (`generator.py`, `pillars.py`, `topic_engine.py`, `schemas.py`) | Old topic and category engine: pillars, 10 categories, 6-day rotation |
| `engine/` (`charts.py`, `renderer.py`) | Old chart and card renderer (Pillow / ffmpeg) |
| `services/content_generator.py`, `renderer.py`, `media.py`, `tts.py`, `subtitles.py`, `debug_overlay.py`, `notifier.py` | Old script generator, renderer, B-roll search, subtitle burner, Discord / Telegram notifier. Still imported by `main.py`, so they must keep importing |
| `scripts/scheduler.py`, `produce_autonomous_short.py` | Old daily scheduler and short producer (weekday rotation, 14:00 publish time) |
| `scripts/test_*.py` | Manual experiments for the old pipeline (not pytest tests) |
| `services/qa_inspector.py`, `main.py --audit-latest`, `--apply-fixes` | The old on-demand audit ("corregir"): subtitle and Whisper phonetics, cover frame. The Motion QA gate is `qa_motion()` inside the pipeline |
| The `topics_queue` and `generation_metrics` tables of `data/history.db`, `data/category_weights.json`, `data/qa_rules.json`, `topics.txt`, `history.json` | State of the old pipeline |
| `services/tiktok.py`, `scripts/auth_tiktok.py`, `scripts/demo_server.py`, `scripts/record_local_demo.py` | The TikTok Content Posting API client and the demo built for the TikTok developer review. Publishing runs through TikTok Studio instead |
| `Dockerfile`, `docker-compose.yml`, `scripts/setup_server.sh` | VPS provisioning for the old scheduler |
| `assets/schematics`, `assets/broll`, `bed_*.mp3` | Assets of the old presets |

## Old design decisions that no longer apply

- The "master video" of 60-120 s at 60 fps with a cover frame inserted at 00:00.00 and public upload by default. Now: 62-90 s at 30 fps, covers are separate files, `genera` uploads private with `publishAt`.
- The five-act structure (hook, naive versus real, human magnitudes, root cause, looping close) and the 145-260 word guardrail. Now: the Motion format rules and 150-190 words.
- The Liquid Glass / Schematic Tech palettes (`#07090E`, `#38BDF8`). Now: the eight blue looks on obsidian `#05070C`.
- The interactive menus ("genera" with 5 options, then 21). Now: `genera` is a fully automatic batch.
- ElevenLabs speed 0.92x with fixed stability settings and strict voice round-robin. Now: continuous take, no time-stretching, narrator by format.
- A cost formula (ElevenLabs characters and Gemini tokens) logged in `generation_metrics`. The table still exists in `data/history.db`.

## If you want to retire it

Removing the old code needs three steps, none of which has been done: take the legacy imports out of `main.py`, delete the modules above and their tests (`tests/test_subtitles.py` covers `services/subtitles.py`),
and drop the Docker files. Run the full checks afterwards.
