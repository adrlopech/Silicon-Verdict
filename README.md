# Silicon Verdict

<p align="center">
  <strong>Automated vertical-video studio for PC hardware, gaming tech and computing curiosities</strong><br>
  Python • Remotion • ElevenLabs • Gemini • YouTube Shorts &amp; TikTok
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

Silicon Verdict is the internal production pipeline behind the official **@siliconverdict** channels. One command picks a topic, writes the
script with Gemini, narrates it with ElevenLabs, renders a 1080×1920 video with Remotion, runs automatic quality checks and, when everything
passes, publishes it to YouTube Shorts. TikTok-ready files and metadata are exported alongside.

It is a single-owner automation suite: no public accounts, no multi-tenant service, no third-party data processing.

## Content series

| # | Series | What you get |
|---|--------|--------------|
| 1 | **Hardware Deep Dive** | Microarchitecture and benchmark explainers with glass-style charts and kinetic subtitles |
| 2 | **Gaming & Optimization** | Frametime, 1% lows and settings guidance for competitive play |
| 3 | **Tech Curiosities** | Three sub-series: `hardware` (engineering paradoxes), `game` (game tech with real Steam screenshots), `simple` (everyday tech told by a mascot) |
| 4 | **Automatic** | The AI picks the category with the longest rest, using `data/history.db` and retention analytics |
| 5 | **Minecraft explainers** | A computing concept acted out inside Minecraft (~64 s), narrated, always from a brand-new Gemini script |
| 6 | **Motion Graphics** | Kinetic-typography explainers (20-45 s): big words, one accent word in electric cyan, counters, code, bars and an outro. Always vertical, always English, always in the channel's blue/cyan palette |

## How a video is made

```
topic ─► Gemini script ─► fact-check gate ─► ElevenLabs voice ─► Remotion render ─► QA gate ─► YouTube / TikTok export
            │                                                                                      │
       story bank (SQLite)                                                      output/<platform>/<title>/<date-time>.mp4
```

* **Scripts**: structured output from Gemini through a resilient client (model chain, quota-aware cooldowns, validators). If no Gemini model is available,
  the same request is answered automatically by the configured fallback providers (Groq today; adding another OpenAI-compatible API is one line). The *simple*,
  *game* and *minecraft* series draw from a **story bank**: below 30 ready scripts, a batch of 20 new ones is generated; an empty bank pauses production.
* **Voice**: ElevenLabs with word-level timestamps; natural mode (no time-stretching). Minecraft videos synthesize one line per scene in parallel and
  place each at its scene's start frame. A robotic local voice is never published.
* **Visuals**: Remotion compositions (`MainScene`, `StoryScene`, `McStory`) at 1080×1920 / 30 fps with safe-zone-aware layouts, kinetic subtitles, a
  mascot with synced vectors, Steam screenshots integrated into the brand look, and a Minecraft director that turns a script into animation, camera and sound.
* **Fact-check gate (Minecraft)**: a second Gemini pass looks for false technical claims, wrong figures, a metaphor that changes midway and misuse of
  "but there is a catch"; it rewrites faulty lines and re-checks. Scripts that cannot be fixed are discarded.
* **QA gate (Minecraft)**: duration, 1080×1920, 48 kHz audio, peak level, dead air, word count and subtitle length are verified with ffmpeg.
  Anything that fails stays local and is **not** uploaded.
* **Resilient LLM layer**: one client (`services/gemini_client.py`) for every call: Gemini first (quota-aware cooldowns persisted in `data/gemini_state.json`), then Groq and Cloudflare Workers AI as automatic fallbacks, with batch generation for the script banks.
* **Game series media**: official Steam screenshots *and trailer clips*, each described once by a vision model. A video only shows footage whose caption fits what the
  narration says at that moment; every item is used in a single video and then deleted, and a game stays blacklisted for 14 days after it appears
  (`python -m services.game_registry` lists the blacklist).
* **Output layout**: one folder per video named after its title, files named by creation date-time, cover and metadata `.txt` included.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd remotion_studio && npm install && cd ..
cp .env.example .env        # fill in the Gemini, ElevenLabs and YouTube credentials
```

Minecraft videos also need the game assets extracted once (see `docs/minecraft_assets.md`):

```bash
python3 scripts/extract_minecraft_assets.py
```

### Everyday commands

```bash
.venv/bin/python main.py help                              # command reference
.venv/bin/python main.py --category 1                      # hardware | 2 gaming | 3 curiosities | 4 auto
.venv/bin/python main.py --category 3 --series simple      # simple | game | hardware
.venv/bin/python main.py --series minecraft                # Minecraft explainer
.venv/bin/python main.py --series minecraft --export-only  # render without uploading
.venv/bin/python scripts/upload_existing.py "<video.mp4>"  # upload an already rendered video
.venv/bin/python scripts/refill_story_bank.py              # top up the story bank
.venv/bin/python scripts/cleanup.py                        # wipe generated output (also run by the "limpieza" chat command)
```

`GEMINI.md` documents the chat triggers (`genera`, `corregir`, `limpieza`, `help`).

## Motion Graphics (series 6)

```bash
.venv/bin/python main.py --series motion --export-only                      # random idea, render only
.venv/bin/python main.py --series motion --topic "How TRIM keeps SSDs fast"  # chosen topic, uploads to YouTube when it passes the checks
```

* The video is a Remotion composition, `MotionGraphic` (`remotion_studio/src/motion/`), driven only by JSON props: `title`, `theme` (accent, background, text) and `scenes`
  (`bigText`, `textWithAccent`, `counter`, `list`, `codeBlock`, `progressBar`, `outro`, plus `curve` and `flash`; set `light: true` on at most one scene for a light variant), each with `text`, optional `accentText`, `value`, `items`, `code`
  and `durationInFrames`. Look at `remotion_studio/src/motion/sample.json`.
* Always 1080×1920 (9:16) at 30 fps, H.264: the render script refuses any other size. Top 12% and bottom 20% are kept free for the Shorts / TikTok interface.
* Brand look: obsidian background (`#05070C`) with a blue (`#007AFF`) glow, electric-cyan (`#00F0FF`) accent words, counters and bars. The generator can never pick another accent colour.
  Every text auto-fits: a long word, headline, list item, code line or number shrinks instead of leaving the frame.
* Gemini writes the scene JSON (structured output, validated and retried); a language gate rejects anything that is not English, and a second pass fact-checks it.
* Rendering goes through `@remotion/renderer` (`scripts/render_motion.mjs`: bundle → selectComposition → renderMedia, progress in the logs).
  Sound is a quiet ambient bed plus a soft whoosh per scene, both from `assets/audio/` (no external assets; fonts are Google Fonts only).
* Preview and tweak the design live: `cd remotion_studio && npx remotion studio`, then open the **MotionGraphic** composition and edit its props.
* Render a JSON by hand: `node scripts/render_motion.mjs props.json out.mp4`.

## Repository map

| Path | Purpose |
|------|---------|
| `main.py` | Pipeline entry point and CLI |
| `core/` | Schemas, topic engine, content pillars |
| `services/` | Script generation, Gemini client, story bank, voice, Remotion renderers, QA, YouTube / TikTok, cleanup, output layout |
| `services/mc_*.py` | Minecraft series: story generator, director bridge, voice, renderer, review/QA gate, pipeline |
| `engine/` | Chart and legacy rendering engine |
| `remotion_studio/` | Remotion project (React): compositions, mascot, Minecraft kit |
| `scripts/` | Maintenance, authentication, scheduler, analytics, tests |
| `docs/` | Design notes (Minecraft kit and assets) |
| `data/` | History database and quality rules (private data is git-ignored) |

## Privacy & platform compliance

Silicon Verdict follows the **TikTok Developer Terms of Service**, **TikTok Partner Policies** and the **Google API Services User Data Policy**.

* **No user data collected**: no personal data, IP addresses or browsing behavior of visitors or viewers is collected, tracked, sold or profiled.
* **No tracking**: the web portal uses no tracking pixels, advertising trackers or fingerprinting.
* **Local credentials**: API keys and OAuth tokens (TikTok, YouTube) stay in local, git-ignored files.
* **API use**: the TikTok Content Posting API and YouTube Data API are used only to publish authorized videos to the official channels; no profiles, comments or audience data are scraped or stored.

Full documents: [Terms of Service](https://adrlopech.github.io/Silicon-Verdict/terms.html) • [Privacy Policy](https://adrlopech.github.io/Silicon-Verdict/privacy.html)

## Trademark & fair use notice

Product names, logos, hardware architectures and game titles mentioned in the content (including AMD, NVIDIA, Intel, Ryzen, GeForce,
Cyberpunk 2077, Starfield, Baldur's Gate 3, Steam and Minecraft) belong to their respective owners. Their appearance implies no affiliation,
sponsorship or endorsement. Analysis and commentary are produced independently for educational and informational purposes under nominative fair use;
game screenshots come from official store pages and are credited in each video description.

## Contact & official links

* **Web Portal**: [https://adrlopech.github.io/Silicon-Verdict/](https://adrlopech.github.io/Silicon-Verdict/)
* **Terms of Service**: [https://adrlopech.github.io/Silicon-Verdict/terms.html](https://adrlopech.github.io/Silicon-Verdict/terms.html)
* **Privacy Policy**: [https://adrlopech.github.io/Silicon-Verdict/privacy.html](https://adrlopech.github.io/Silicon-Verdict/privacy.html)
* **Official TikTok**: [@siliconverdict](https://www.tiktok.com/@siliconverdict)
* **Official YouTube**: [@SiliconVerdictHQ](https://www.youtube.com/@SiliconVerdictHQ)
* **Developer & Contact Email**: `imnotchego@gmail.com`

---

<p align="center">
  <sub>&copy; 2026 Silicon Verdict. All rights reserved.</sub>
</p>
