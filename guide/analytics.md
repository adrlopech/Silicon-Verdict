# Analytics

## What can be read

| Source | How | What you get |
|---|---|---|
| **YouTube Analytics API** | `services/yt_analytics.py` with the OAuth token | Views, engaged views, average percentage viewed, retention curve (r20 / r50 / r80), traffic sources, per day. Lags one to two days behind: the newest videos show 0 |
| **YouTube Data API** | `videos().list(part="statistics")` | Views, likes, comments right now (no retention) |
| **TikTok Studio** | Browser, `https://www.tiktok.com/tiktokstudio/content` | Views, likes, comments per post (no API here). The list loads lazily: scroll to see older posts |

The token needs `youtube.upload`, `youtube.readonly` and `yt-analytics.readonly`. The Google Cloud app is in Production, so it does not expire weekly; to renew it see [Publishing](publishing.md#youtube-oauth).

## The retention report

```bash
.venv/bin/python scripts/report_retention.py                       # last 90 days
.venv/bin/python scripts/report_retention.py --days 28 --min-views 300
```

It joins every video with `data/history.db` to know its format and look, prints a summary, one row per video, **averages by format and by look**, traffic sources and the last days,
and writes `notes/analytics_report_<date>.md` and `data/analytics_report.json` (both private). Reading the columns:

- `engaged` = engaged views / views, the closest the API gets to "viewed instead of swiped away".
- `avg%` = average percentage viewed (a replayed loop can pass 100).
- `r20 r50 r80` = audience still watching a fifth, half and four fifths of the way in.
- With fewer than about **10 videos per format or look the averages are noise**, not a result.

## How `genera` uses the numbers

`scripts/genera_batch.py` calls `format_stats()` (from the same report) and scores each format: `0.6 x min(avg%, 100) + 0.4 x engaged%`, weighted by views and joined with `shorts_history`.
A format counts as **proven** with at least one video and 100 views. The batch is the two best proven formats, one exploration and one weighted draw. With no data (token missing, offline) it prints
`analytics unavailable` and falls back to `FORMAT_WEIGHTS`. Slots are re-ordered by average views once two slots have two or more videos each. Details in [Daily workflow](daily-workflow.md#1-plan).

## What the channel has shown so far (Nov 2026, small samples)

- Shorts feed is the main source of YouTube views (about 80 %).
- Best average percentage viewed by format over 90 days: `evolution` (about 65 %), `versus` (58 %), classic explainer (57 %); `whatif` and `decode` sit around 45 %.
- On TikTok almost every video flattens at about 750 views whatever the format; GTA VI videos did well on TikTok and poorly on YouTube.
- Treat all of this as hypotheses: the channels are small and most videos are days old. The background studies are in the private `notes/` folder (`content_style_study_2026-11.md`, `niche_research_2026-11.md`, `viral_playbook.md`, `competitor_playbook.md`, `video_audit_2026-11.md`).

## Older tools

