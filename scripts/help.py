#!/usr/bin/env python3
"""Silicon Verdict command reference (python main.py help). The full documentation is in guide/README.md."""

HELP_TEXT = """================================================================================
 SILICON VERDICT: COMMAND REFERENCE   (full documentation: guide/README.md)
================================================================================

1. CHAT COMMANDS (with Claude Code, see CLAUDE.md)
--------------------------------------------------------------------------------
 genera      Four videos of four different formats, picked from the channel's own numbers,
             rendered, uploaded to YouTube (private + publishAt, with cover) and scheduled on
             TikTok Studio at the best hours. Add "de hoy" to publish today instead of tomorrow.
 limpieza    scripts/cleanup.py: wipes output/tiktok, output/tiktok_small, output/youtube and temp/. Keeps data/, assets/, .env.
 help        This reference.

2. MAKING VIDEOS
--------------------------------------------------------------------------------
 PYTHONPATH=. .venv/bin/python scripts/genera_batch.py --plan [--date YYYY-MM-DD] [--avoid a,b]
 PYTHONPATH=. .venv/bin/python scripts/genera_batch.py [--date YYYY-MM-DD]
 PYTHONPATH=. .venv/bin/python scripts/genera_batch.py --topics retry.json --out data/batches/retry.json

 .venv/bin/python main.py --motion-format <format> [--export-only]
   formats: myth tier whatif easter evolution versus hardware simple fix decode
            top5 eli5 fails numbers quiz stop rumor review news priced any
 .venv/bin/python main.py --motion-kind curiosity --topic "How TRIM keeps SSDs fast"
 .venv/bin/python main.py --motion-kind game          # needs prepared game footage

3. PUBLISHING
--------------------------------------------------------------------------------
 .venv/bin/python scripts/upload_existing.py "<video.mp4>" [--privacy private --publish-at 2026-11-17T13:00:00Z]
 .venv/bin/python scripts/retry_youtube_uploads.py data/batches/<date>.json
 .venv/bin/python scripts/authenticate_yt.py                           # renew the YouTube token (only if it fails with invalid_grant)

4. BANKS, FOOTAGE, ANALYTICS
--------------------------------------------------------------------------------
 .venv/bin/python scripts/refill_story_bank.py --series motion --format <format>
 .venv/bin/python scripts/fetch_game_images.py | fetch_game_clips.py | caption_game_media.py | build_game_facts.py
 .venv/bin/python scripts/report_retention.py [--days 28 --min-views 300]
 .venv/bin/python scripts/render_silent_preview.py <script.json> --out DIR   # no-voice preview of a script
 .venv/bin/python -m services.tech_news                                # today's headlines (news format)

5. CHECKS
--------------------------------------------------------------------------------
 .venv/bin/python -m pytest
 .venv/bin/ruff check .
 (cd remotion_studio && npx tsc --noEmit -p .)
 python3 docs/check_portal.py

6. WHERE THINGS ARE
--------------------------------------------------------------------------------
 output/youtube/<title>/<date-time>.mp4 and .png      video and cover
 output/tiktok/<title>/<date-time>.mp4 .png .txt      TikTok copy, cover and metadata (title, hashtags, pinned comment)
 output/tiktok_small/<title>.mp4                      <10 MB copy for the TikTok upload
 data/batches/latest.json                               manifest of the last genera batch
 data/batches/log.json                                  slot of every scheduled video (ranks the hours)
 data/history.db                                      history, story bank, game registry
 data/scripts/                                        hand-written scripts (MotionProject JSON)
================================================================================
"""


def print_help() -> None:
    """Prints the command reference."""
    print(HELP_TEXT)


if __name__ == "__main__":
    print_help()
