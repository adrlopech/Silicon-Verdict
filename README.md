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
| 3 | **Tech Curiosities** | Two sub-series: `hardware` (engineering paradoxes) and `simple` (everyday tech told by a mascot) |
| 4 | **Automatic** | The AI picks the category with the longest rest, using `data/history.db` and retention analytics |
| 5 | **Minecraft explainers** | A computing concept acted out inside Minecraft (~64 s), narrated, always from a brand-new Gemini script |
| 6 | **Motion Graphics** | Narrated kinetic-typography explainers of 62-84 s (YouTube monetisation needs more than 60 s): big words, one accent word in electric cyan, counters, code, bars and an outro. Two kinds: tech *curiosities* and *games* (an engineering fact told with real game footage). Always vertical, always English, always in the channel's blue/cyan palette |

## How a video is made

```
topic ─► Gemini script ─► fact-check gate ─► ElevenLabs voice ─► Remotion render ─► QA gate ─► YouTube / TikTok export
            │                                                                                      │
       story bank (SQLite)                                                      output/<platform>/<title>/<date-time>.mp4
```

* **Scripts**: structured output from Gemini through a resilient client (model chain, quota-aware cooldowns, validators). If no Gemini model is available,
  the same request is answered automatically by the configured fallback providers (Groq today; adding another OpenAI-compatible API is one line). The *simple*
  and *minecraft* series draw from a **story bank**: below 30 ready scripts, a batch of 20 new ones is generated; an empty bank pauses production.
* **Voice**: ElevenLabs with word-level timestamps; natural mode (no time-stretching). Minecraft videos synthesize one line per scene in parallel and
  place each at its scene's start frame. A robotic local voice is never published.
* **Visuals**: Remotion compositions (`MainScene`, `StoryScene`, `McStory`) at 1080×1920 / 30 fps with safe-zone-aware layouts, kinetic subtitles, a
  mascot with synced vectors, Steam screenshots integrated into the brand look, and a Minecraft director that turns a script into animation, camera and sound.
* **Fact-check gate (Minecraft)**: a second Gemini pass looks for false technical claims, wrong figures, a metaphor that changes midway and misuse of
  "but there is a catch"; it rewrites faulty lines and re-checks. Scripts that cannot be fixed are discarded.
* **QA gate (Minecraft)**: duration, 1080×1920, 48 kHz audio, peak level, dead air, word count and subtitle length are verified with ffmpeg.
  Anything that fails stays local and is **not** uploaded.
* **Resilient LLM layer**: one client (`services/gemini_client.py`) for every call: Gemini first (quota-aware cooldowns persisted in `data/gemini_state.json`), then Groq and Cloudflare Workers AI as automatic fallbacks, with batch generation for the script banks.
* **Output layout**: one folder per video named after its title, files named by creation date-time, cover and metadata `.txt` included.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd remotion_studio && npm install && cd ..
cp .env.example .env        # Gemini, ElevenLabs and YouTube credentials (required); GROQ_API_KEY / CLOUDFLARE_* are optional LLM fallbacks
```

Game videos (Motion Graphics, `--motion-kind game`) need their footage and source dossiers prepared once, then topped up when games run out of unused items:

```bash
python3 scripts/fetch_game_images.py      # official Steam screenshots
python3 scripts/fetch_game_clips.py       # clips cut from the official trailers
python3 scripts/caption_game_media.py     # vision-model description of every item (what each one shows)
python3 scripts/build_game_facts.py       # Wikipedia + Steam source dossier per game (paced, cached)
```

Minecraft videos also need the game assets extracted once (see `docs/minecraft_assets.md`) and the original background music generated once:

```bash
python3 scripts/extract_minecraft_assets.py   # textures, sounds, skins (also converts the extra skins in assets/skins/)
python3 scripts/make_mc_music.py              # writes assets/audio/mc_bed.wav (without it the old ambient bed is used)
```

### Everyday commands

```bash
.venv/bin/python main.py help                              # command reference
.venv/bin/python main.py --category 1                      # hardware | 2 gaming | 3 curiosities | 4 auto
.venv/bin/python main.py --category 3 --series simple      # simple | hardware
.venv/bin/python main.py --series minecraft                # Minecraft explainer
.venv/bin/python main.py --series minecraft --export-only  # render without uploading
.venv/bin/python scripts/upload_existing.py "<video.mp4>"  # upload an already rendered video
.venv/bin/python scripts/refill_story_bank.py              # top up the story bank
.venv/bin/python scripts/cleanup.py                        # wipe generated output (also run by the "limpieza" chat command)
```

`GEMINI.md` documents the chat triggers (`genera`, `corregir`, `limpieza`, `help`).

## Minecraft explainers (series 5)

A computing concept acted out in a small Minecraft village, ~64 s, vertical, narrated, always from a brand-new Gemini script. Gemini writes an `McStory`
(`core/schemas.py`); the director (`remotion_studio/src/mc/director.ts`) compiles it into layout, choreography, camera, props and sounds. Full reference: `docs/minecraft_video_kit.md`.

```bash
.venv/bin/python main.py --series minecraft --topic "what a CPU cache is" --export-only
.venv/bin/python scripts/test_mc_director.py            # director tests (incl. "the camera keeps the hero in frame")
node scripts/mc_compile.mjs script.json                 # compile a script and print errors, warnings, quality notes and camera framing
```

* **Stations** (the world the script is built from): `sign`, `mine`, `chest`, `pond`, `door`, `ladder`, `pen`, plus **`stall`** (village market stall with a shopkeeper, optional counter items,
  per-beat `stock` that pops new items in with sparkles and `tag` value plaques with the old value struck through) and **`library`** (a wall of bookshelves, always full of books).
  Village houses are added in the background automatically. Every station must be used by an action: unused stations are rejected, so nothing in the video is decorative.
* **Actions with a purpose**: besides walking, mining, opening and swimming there are `give` and `fetch` (take an item from one station and hand it over at another: it flies in an arc),
  `show`, `search`, `read`, `take_book` / `put_book`, `point`, `pace`, `cheer`. A beat the script leaves empty gets an action chosen from the meaning of its line and from what exists in the world;
  long gaps are filled with reading, a short walk or looking around, so the hero is never frozen.
* **Cast**: extra characters with `cast.skin`: nine vanilla player skins, six character skins from NameMC (`assets/skins/namemc/`, see its `SOURCES.md`) and eight villager professions.
* **Look**: `time: day | dusk | night` (night adds torches with warm light that also reaches the actors), chunked subtitles of 2-3 words that follow the narration word by word
  (ElevenLabs timestamps), a giant pixel-font concept title, held items drawn at their real size.
* **Camera**: planned from the real animation tracks; whenever the hero moves, the shot follows him, so he never leaves the frame (`low` is an extra low-angle close-up).
* **Audio**: game sounds + narration + an original music loop (`scripts/make_mc_music.py`) that ducks under the voice. The call to action is voiced once.
* **Assets are not in git**: textures, sounds and skins are generated or downloaded locally (`remotion_studio/public/` and `*.png` are ignored). The NameMC skins are creations of their authors: check their terms before using them in monetised videos.

## Motion Graphics (series 6)

```bash
.venv/bin/python main.py --series motion --export-only                              # alternates curiosity / game, render only
.venv/bin/python main.py --series motion --motion-kind game                         # an engineering fact about a game, with real footage
.venv/bin/python main.py --series motion --motion-kind curiosity --topic "How TRIM keeps SSDs fast"
```

### Content formats (`--motion-format`)

The motion series also speaks six fixed formats, each with its own scene types, prompt rules and validators (the same fact-check pass applies to every one):

```bash
.venv/bin/python main.py --series motion --motion-format myth --export-only       # MYTH / FACT: claim on screen, then a stamp slams down
.venv/bin/python main.py --series motion --motion-format tier --export-only       # S-F tier list that fills up item by item
.venv/bin/python main.py --series motion --motion-format whatif --export-only     # a hypothetical about computing, escalating consequences
.venv/bin/python main.py --series motion --motion-format evolution --export-only  # timelines + growth counters
.venv/bin/python main.py --series motion --motion-format versus --export-only     # two contenders, 3-5 rounds of bars, a winner per round
.venv/bin/python main.py --series motion --motion-format easter --export-only     # a game's hidden detail (needs a game with unused footage and a source dossier)
.venv/bin/python main.py --series motion --motion-format any                      # a random one
```

New scene types (`remotion_studio/src/motion/formats.tsx`): `tier` (`items`: `"S|label"`, every scene repeats the board and adds one item), `versus` (`left`, `right`, `leftValue`,
`rightValue`, `unit`, optional `winner` for lower-is-better metrics), `verdict` (`verdict`: myth | fact | partly, `accentText` = the one-line truth) and `timeline` (`items`: `"year|label"`).
A demo of all four: `remotion_studio/src/motion/sample_formats.json`. `easter` is always a game video; the others are curiosities.

* **Length: 62-84 s.** YouTube monetisation needs more than 60 s, so the script has 13-19 scenes and about 150-190 narrated words, every scene lasts as long as its narration
  and the pipeline holds scenes a little longer if the voice still comes to less than 62 s. The QA gate rejects anything outside 61-92 s.
* **Two kinds, one engine.** *Curiosity*: a tech/hardware/coding idea told with words, counters, code, bars and curves. *Game*: the script is written against the
  captions of the footage available for one game, and `footage` scenes show it inside the channel look (blue/cyan grade, scan line, corner brackets, game tag).
* **Game footage rules.** Footage is official Steam screenshots and trailer clips (`scripts/fetch_game_images.py`, `scripts/fetch_game_clips.py`; `scripts/build_game_facts.py` prepares the source dossiers), each described once by a
  vision model (`scripts/caption_game_media.py`). A footage scene must show what its narration mentions (checked by the fact-check pass). Every item is used in ONE video and
  then deleted (its key goes to a ledger, so it is never downloaded again), and a game stays blacklisted for 14 days after it appears (`python -m services.game_registry`).
  A game with fewer than 6 unused items is skipped until you fetch more. The footage is only spent when a finished video passes the checks, and near-black shots are never used.
* **Game roster.** The 15 classic games plus 93 current ones (65 from 2025, 28 from 2026) listed in `data/games_catalog.json` (real Steam appids and release dates). To add a game, add its entry there, then run `scripts/fetch_game_images.py --appid <id>`, `scripts/caption_game_media.py` and `scripts/build_game_facts.py`.
* **Game facts are grounded, quoted and verified; the video is always produced and uploaded.**
  * *Sources*: each game has a dossier (`services/game_facts.py`: the sections of its Wikipedia article on development / technology / design plus the Steam store description),
    prebuilt and cached by `scripts/build_game_facts.py` so production never depends on Wikipedia being reachable. Live lookups are paced, honour `Retry-After` and fall back to the REST API.
  * *Quotes checked by code*: the script may only state facts about the game that its dossier supports, every claim-bearing scene must carry a verbatim `evidence` quote (at least 6
    scenes), and the validator rejects any quote that is not really in the dossier. A counter or bar may only show a figure written in the dossier.
  * *Review*: the fact-check sees the dossier and the quotes and runs on the strongest reviewer (`gpt-oss-120b`), retried once if its per-minute window is full. If it is unavailable, a
    panel of the other reviewers answers and their issues are merged (stricter than any single one). Flagged scenes are rewritten from the dossier and re-checked.
  * *When something fails anyway*: no source text at all means a conservative script (no figures or dates, only well-known facts, no counters); no reviewer answering means the video is still
    published. Provider requests size their output reserve to fit the per-minute token limits, so a token overflow cannot happen.
* The video is a Remotion composition, `MotionGraphic` (`remotion_studio/src/motion/`), driven only by JSON props: `title`, `theme` (accent, background, text) and `scenes`
  (`bigText`, `textWithAccent`, `counter`, `list`, `codeBlock`, `progressBar`, `outro`, `curve`, `flash` and `footage`; set `light: true` on at most one scene), each with `text`,
  optional `accentText`, `value`, `items`, `code`, `mediaSrc` and `durationInFrames`. See `remotion_studio/src/motion/sample.json`.
* Always 1080×1920 (9:16) at 30 fps, H.264: the render script refuses any other size. Top 12% and bottom 20% are kept free for the Shorts / TikTok interface.
* Brand look: obsidian background (`#05070C`) with a blue (`#007AFF`) glow, electric-cyan (`#00F0FF`) accents. The generator can never pick another accent colour.
  Every text auto-fits: a long word, headline, list item, code line or number shrinks instead of leaving the frame.
* The script is structured JSON from the LLM layer (validated and retried); a language gate rejects anything that is not English, and a second pass fact-checks it.
* **Voice**: ElevenLabs narration, one line per scene; the voice decides each scene's length. Sound is that narration over a quiet ambient bed and a soft whoosh per scene
  (own assets in `assets/audio/`; fonts are Google Fonts only).
* Rendering goes through `@remotion/renderer` (`scripts/render_motion.mjs`: bundle → selectComposition → renderMedia, progress in the logs).
* Preview and tweak the design live: `cd remotion_studio && npx remotion studio`, then open the **MotionGraphic** composition and edit its props.
* Render a JSON by hand: `node scripts/render_motion.mjs props.json out.mp4 [publicDir]` (`publicDir` holds the footage a game video references).

## Repository map

| Path | Purpose |
|------|---------|
| `main.py` | Pipeline entry point and CLI |
| `core/` | Schemas, topic engine, content pillars |
| `services/` | Script generation, Gemini client, story bank, voice, Remotion renderers, QA, YouTube / TikTok, cleanup, output layout |
| `services/mc_*.py` | Minecraft series: story generator, director bridge, voice, renderer, review/QA gate, pipeline |
| `services/motion_*.py` | Motion Graphics: script generator (validation, evidence quotes, fact-check panel), pipeline (voice, render, sound, QA, upload) |
| `services/game_*.py` | Game media and facts: footage manifest, captions, one-use consumption, 14-day blacklist (`game_registry`), source dossiers (`game_facts`) |
| `services/gemini_client.py` | The single LLM entry point: Gemini + Groq + Cloudflare fallbacks, cooldowns, batching, image input |
| `engine/` | Chart and legacy rendering engine |
| `remotion_studio/` | Remotion project (React): compositions (`MotionGraphic`, mascot story, Minecraft kit, hardware main scene) |
| `scripts/` | Maintenance (cleanup, bank refill, footage fetch/caption, facts), `render_motion.mjs`, Minecraft assets / music / director tests, authentication, scheduler, analytics |
| `docs/` | Design notes (Minecraft kit and assets) |
| `assets/` | Fonts, audio beds and effects, B-roll manifest, `skins/` (extra Minecraft skins with their sources) |
| `data/` | History database, quality rules, `game_facts/` and `gemini_state.json` caches (private data is git-ignored) |

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
game screenshots and trailer clips come from official Steam store pages and are credited in each video description.

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
