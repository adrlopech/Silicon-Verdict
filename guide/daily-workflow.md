# Daily workflow: `genera`

`genera` makes **four videos of four different formats** and schedules them on YouTube and TikTok at the best hours. It is the normal way to publish.
In a chat with Claude Code the word `genera` (or `/genera`) runs the whole flow without questions: the operator has authorized publishing.
The steps the assistant follows are in `.claude/commands/genera.md`; this page explains what each step does and how to do it by hand.

## 1. Plan

```bash
PYTHONPATH=. .venv/bin/python scripts/genera_batch.py --plan                   # tomorrow
PYTHONPATH=. .venv/bin/python scripts/genera_batch.py --plan --date 2026-11-17 # a given UTC date (use today's date to publish today)
```

The plan shows four rows: hour in UTC and Madrid, format and why it was chosen.

**How formats are chosen** (see [Analytics](analytics.md)): the two best proven formats (score = 60 % average percentage viewed + 40 % engaged views, with at least 100 views),
one exploration (the format with the fewest published videos) and one weighted draw (`FORMAT_WEIGHTS`). `easter` is never picked (it needs game footage) and `news` is never drawn.
With no analytics available the four are weighted draws. Pass `--avoid fix,top5` to leave out the formats of the previous day.

**How hours are chosen:** the default slots are 13:00, 16:00, 19:00 and 22:00 UTC (8-9 am, noon, 3 pm and 6 pm in New York; 14:00, 17:00, 20:00 and 23:00 in Madrid, which is UTC+1).
`data/batches/log.json` remembers the slot of every scheduled video; once two or more slots have at least two videos with views, slots are ranked by average views.
The best formats get the best slots.

## 2. Produce and schedule on YouTube

```bash
PYTHONPATH=. .venv/bin/python scripts/genera_batch.py --date 2026-11-17 > /tmp/genera.log 2>&1
```

It takes ten to twenty minutes and nothing needs watching. For every slot it renders the video with the normal pipeline (export only), uploads it to YouTube as **private with `publishAt`**
(YouTube publishes it at that time), sets the cover as the thumbnail, makes a copy under 10 MB for TikTok, and appends the entry to `data/batches/latest.json`:
title, TikTok caption, hashtags, TikTok copy, cover, slot and YouTube id. The manifest is saved after every video, so a crash loses nothing.

Options: `--seed`, `--avoid`, `--out FILE` (manifest path), `--topics FILE` (see below), `--public-first` (the first video of the plan, whose slot has already passed, is uploaded public right away instead of scheduled; its TikTok copy is published with "Ahora").

### When a slot fails

The LLM layer sometimes cannot give a script that passes the validators (Gemini 503 or 504, validator rejections), especially for the newer formats
(`fails`, `eli5`, `rumor`). **The batch fills such a slot by itself**: it takes a banked script of a proven format that is not already in the plan (order: versus, myth, whatif, evolution, decode, tier,
hardware, fix, simple) and prints `slot filled with a banked <format> script`; the manifest and `data/batches/log.json` record the format that was really made. Keep the bank stocked
(`scripts/refill_story_bank.py`, `count_ready` in `services/story_bank.py`): a slot is only lost when no banked script is left. A hand-written script is never replaced.
If a slot is still lost (`FAILED (nothing uploaded for this slot)`), fill the gap with a topics file:

```json
[
  {"format": "evolution", "why": "retry", "slot": "13:00"},
  {"format": "top5", "why": "hand-written script", "slot": "16:00", "script": "data/scripts/sample_top5.json"},
  {"format": "decode", "topic": "What does RTX 5070 Ti mean", "source": "data/topic_facts/rtx.txt", "slot": "22:00"}
]
```

```bash
PYTHONPATH=. .venv/bin/python scripts/genera_batch.py --date 2026-11-17 --topics /tmp/retry.json --out data/batches/retry.json
```

Each entry takes `format` (use `classic` for the explainer), optionally `slot` (UTC `HH:MM`), `topic` and `source` (a text file the script must be grounded on), or `script`
(a hand-written `MotionProject` JSON, checked by the same validator). Formats that rarely fail: evolution, versus, myth, whatif, hardware, decode, fix.
YouTube can also refuse uploads for a daily limit (`uploadLimitExceeded`); `scripts/retry_youtube_uploads.py <manifest>` sends the missing ones again a day later.

## 3. Verify YouTube

Every video must be `private` with the right `publishAt`:

```bash
PYTHONPATH=. .venv/bin/python - <<'EOF'
from services.youtube import youtube_service
y = youtube_service.get_authenticated_client()
for v in y.videos().list(part="status,snippet", id="ID1,ID2,ID3,ID4").execute()["items"]:
    print(v["id"], v["status"]["privacyStatus"], v["status"].get("publishAt"), v["snippet"]["title"][:50])
EOF
```

## 4. Schedule on TikTok

TikTok has no API access here, so the assistant drives TikTok Studio in the browser with Claude in Chrome, one entry of `data/batches/latest.json` at a time:
upload `tiktok_copy`, write `caption`, pick every hashtag from the dropdown, upload `cover`, choose "Programación" and the hour, press "Programar".
The exact clicks and the traps are in [Publishing](publishing.md#tiktok-studio-step-by-step). Finally check `tiktokstudio/content`: all four must appear with their hour.

## 5. Report

A table with video, format, Madrid hour and YouTube link, and a note of anything that could not be checked. If another video is already scheduled for the same hour, move the new one.

## Fixed rules

- Hashtags are a single joined word (`#pcbuild`, never `#pc build`).
- Videos last more than 60 seconds (monetisation).
- Official channels: YouTube `@SiliconVerdictHQ` (a brand account of the Google login NotChego) and TikTok `@siliconverdict`. Never publish to the unrelated YouTube channel `@siliconverdict` ("Frame Floor").
- Code changes go straight to `main` (commit and push, no feature branches).

## Other daily tasks

| Task | Command |
|---|---|
| One video by hand | `.venv/bin/python main.py --motion-format <format> --export-only` (omit `--export-only` to upload as well) |
| Upload a rendered video | `.venv/bin/python scripts/upload_existing.py "<video.mp4>" [--privacy private --publish-at 2026-11-17T13:00:00Z]` |
| Today's headlines video | `.venv/bin/python main.py --motion-format news` |
| Top up the story bank | `.venv/bin/python scripts/refill_story_bank.py --series motion --format <format>` |
| Clean generated output (`limpieza`) | `.venv/bin/python scripts/cleanup.py` (`--dry-run` to preview) |
| Retention report | `.venv/bin/python scripts/report_retention.py` |
| Renew the YouTube token (only after `invalid_grant`) | see [Publishing](publishing.md#youtube-oauth) |

`limpieza` empties `output/tiktok/`, `output/tiktok_small/`, `output/youtube/` and `temp/`; it keeps `data/`, `assets/`, `.env`, credentials and logs. Nothing deletes `output/tiktok/` automatically, because
the TikTok copies wait there for manual upload until you ask.
