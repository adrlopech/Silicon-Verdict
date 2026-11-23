# Silicon Verdict

<p align="center">
  <strong>Automated vertical-video studio for PC hardware, gaming tech and computing curiosities</strong><br>
  Python • Remotion • ElevenLabs (+ local voice backup) • Gemini • YouTube Shorts &amp; TikTok
</p>

<p align="center">
  <a href="https://adrlopech.github.io/Silicon-Verdict/">Web Portal</a> •
  <a href="https://adrlopech.github.io/Silicon-Verdict/terms.html">Terms of Service</a> •
  <a href="https://adrlopech.github.io/Silicon-Verdict/privacy.html">Privacy Policy</a> •
  <a href="https://www.tiktok.com/@siliconverdict">TikTok</a> •
  <a href="https://www.youtube.com/@SiliconVerdictHQ">YouTube</a>
</p>

---

## What it is

The internal production pipeline behind the official **@siliconverdict** channels. One command picks a format and a topic, writes a structured script with an LLM, checks the facts, narrates it
with ElevenLabs, renders a 1080×1920 video with Remotion (narrated kinetic typography, 62-90 s, English, channel palette), mixes the sound, runs a quality gate and uploads it. A cover and
TikTok-ready files come with every video. A single-owner automation suite: no public accounts, no multi-tenant service, no third-party data processing.

```
format + topic ─► script ─► validators ─► fact-check ─► ElevenLabs voice ─► Remotion render ─► sound mix ─► QA gate ─► cover ─► YouTube / TikTok
```

## Content

Twenty formats on top of the classic explainer, each with its own scenes, prompt rules and validator:

| Group | Formats |
|---|---|
| Verdicts and rankings | `myth` · `tier` · `top5` · `versus` · `review` |
| Explainers | `hardware` · `simple` · `eli5` · `decode` · `fix` · `stop` |
| Stories and numbers | `evolution` · `fails` · `numbers` · `priced` · `whatif` · `rumor` · `quiz` |
| News | `news` (Tech Briefing, today's headlines from live RSS feeds) |
| Games | `easter` and the `game` kind: an engineering fact told over real Steam footage |

Details of every format: [guide/formats.md](guide/formats.md).

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd remotion_studio && npm install && cd ..
cp .env.example .env        # Gemini, ElevenLabs and YouTube credentials (required); Cloudflare Workers AI is the optional LLM fallback
.venv/bin/python scripts/authenticate_yt.py
.venv/bin/python main.py --motion-format myth --export-only   # a first video, nothing uploaded
```

## Everyday commands

```bash
PYTHONPATH=. .venv/bin/python scripts/genera_batch.py --plan     # plan four videos of four formats (add --date YYYY-MM-DD)
PYTHONPATH=. .venv/bin/python scripts/genera_batch.py            # produce them and schedule them on YouTube; then schedule TikTok (see the guide)
.venv/bin/python main.py --motion-format any     # one video of a weighted random format
.venv/bin/python scripts/upload_existing.py "<video.mp4>"        # upload a rendered video (sets its cover as thumbnail)
.venv/bin/python scripts/report_retention.py                     # real YouTube retention by video, format and look
.venv/bin/python scripts/cleanup.py                              # wipe generated output ("limpieza")
.venv/bin/python main.py help                                    # command reference
```

## Documentation

All the documentation lives in [`guide/`](guide/README.md):

| Page | Contents |
|---|---|
| [Quick start](guide/quick-start.md) | Install, keys, first video |
| [Daily workflow](guide/daily-workflow.md) | `genera`: plan, produce, schedule, retry, clean up |
| [Formats](guide/formats.md) | The 20 formats and what their validators demand |
| [Pipeline](guide/pipeline.md) | Script, fact-check, voice, render, sound, QA, cover, files |
| [Motion engine](guide/motion-engine.md) | Scenes, looks, camera, stage visuals, cursor, UI presets, retention rules |
| [Game videos](guide/games.md) | Footage, dossiers, one-use ledger |
| [Voice](guide/voice.md) | Narrator rotation, ElevenLabs, local backup |
| [Publishing](guide/publishing.md) | YouTube OAuth and uploads, TikTok Studio steps, hours, hashtags |
| [Analytics](guide/analytics.md) | Reading the numbers, how `genera` chooses formats and hours |
| [Development](guide/development.md) | Tests, CI, repository map, troubleshooting |

Instructions for the AI assistant that operates the repository: [`CLAUDE.md`](CLAUDE.md) (Claude Code).

## Development

```bash
.venv/bin/python -m pytest && .venv/bin/ruff check .
cd remotion_studio && npx tsc --noEmit -p .
python3 docs/check_portal.py
```

GitHub Actions (`.github/workflows/ci.yml`) runs lint, tests, the TypeScript check and the portal link check on every push and pull request.

## Privacy & platform compliance

Silicon Verdict follows the **TikTok Developer Terms of Service**, **TikTok Partner Policies** and the **Google API Services User Data Policy**.

* **No user data collected**: no personal data, IP addresses or browsing behavior of visitors or viewers is collected, tracked, sold or profiled.
* **No tracking**: the web portal uses no tracking pixels, advertising trackers or fingerprinting.
* **Local credentials**: API keys and OAuth tokens (TikTok, YouTube) stay in local, git-ignored files.
* **API use**: the TikTok Content Posting API and YouTube Data API are used only to publish authorized videos to the official channels; no profiles, comments or audience data are scraped or stored.

Full documents: [Terms of Service](https://adrlopech.github.io/Silicon-Verdict/terms.html) • [Privacy Policy](https://adrlopech.github.io/Silicon-Verdict/privacy.html)

## Trademark & fair use notice

Product names, logos, hardware architectures and game titles mentioned in the content (including AMD, NVIDIA, Intel, Ryzen, GeForce,
Cyberpunk 2077, Starfield, Baldur's Gate 3, Steam) belong to their respective owners. Their appearance implies no affiliation,
sponsorship or endorsement. Analysis and commentary are produced independently for educational and informational purposes under nominative fair use;
game screenshots and trailer clips come from official Steam store pages and are credited in each video description.

## Contact & official links

* **Web Portal**: [https://adrlopech.github.io/Silicon-Verdict/](https://adrlopech.github.io/Silicon-Verdict/)
* **Official TikTok**: [@siliconverdict](https://www.tiktok.com/@siliconverdict)
* **Official YouTube**: [@SiliconVerdictHQ](https://www.youtube.com/@SiliconVerdictHQ)
* **Developer & Contact Email**: `imnotchego@gmail.com`

---

<p align="center">
  <sub>&copy; 2026 Silicon Verdict. All rights reserved.</sub>
</p>
