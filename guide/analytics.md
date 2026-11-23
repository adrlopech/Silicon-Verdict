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


## What the numbers say

Read them with `scripts/report_retention.py`: besides format and look it groups the videos by **title pattern** ("Spec Duel", "What If", "Every X (prices)"...), **publish hour** and **weekday**, with views per video.
Fewer than about ten videos per group is noise, so use the groups to decide what to test next, not to declare winners.

Lessons of the reference channel analysed on 2026-11-23 (a tech account with 3 videos, 472K views on one of them and only 287 followers):

- The hit was a **product-intent list** ("Every RTX 50 Series Graphics Card Explained": name, memory, launch price, use and games for each card, 98 s, 5,272 saves, 588 comments, 935 shares).
  Search keeps feeding it weeks later. That is the shape of the "Every X at today's price" videos ([Prices](prices.md)).
- **Comments:** people list the card they own or want, ask for the one that was left out ("where is the 5050?") and complain about prices; the left-out card's comment got 3,285 likes. A product list should leave out, or only mention,
  the product people argue about, and the pinned comment should ask which one they own.
- **Followers come from identity, not reach:** 472K views gave 0.06 % followers; the channel had no bio, a generic name and, in its third video, changed subject. Keep one niche, one series name on screen
  (the title strip already does it), a bio that says what the channel does and an outro that names the series ("follow for every processor explained").
- Their second video of the same kind got 17.6K (4 % of the first): reach belongs to the topic, so each product family is a new bet and the family that is searched most gets the first slot.

Ideas that need the account owner (the API token cannot change them): the YouTube channel description and the TikTok bio, for example
*"Every GPU, CPU and spec decoded in 60 seconds, with today's real prices. New videos daily."*

## First-three-days numbers and the cover test

- **Same window for every video.** `services/yt_analytics.early_report` reads each public video's views and average view % over its first three days (cached in `data/early_stats.json`, so only new videos cost a call). `report_retention.py` prints them by format, title pattern and cover style, and `genera_batch.py` ranks "proven" formats by views per video in those three days (the plan reason shows `n=`; fewer than ~5 videos is still a hint, not a result).
- **Cover styles.** The cover of each video is style `a` (the cold open, as before) or `b` (the second scene), chosen by a hash of the title, so half of the videos of each format get each. `cover_style` is recorded in `data/batches/log.json`; the report compares both styles. Judge it only after 15+ videos per style. YouTube allows changing a thumbnail later, so a losing style costs nothing to drop.
