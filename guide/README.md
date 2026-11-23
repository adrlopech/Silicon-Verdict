# Silicon Verdict: guide

Everything you need to run, understand and change the studio. Start with the first two pages; the rest is reference.

| Page | Read it when you want to... |
|---|---|
| [Quick start](quick-start.md) | install the project, set the keys and render your first video |
| [Daily workflow](daily-workflow.md) | make and schedule the four videos of the day (`genera`), retry a failed slot, clean up |
| [Formats](formats.md) | know what each of the 20 content formats is, how to call it and what its validator demands |
| [Pipeline](pipeline.md) | follow a video from topic to upload: scripts, fact-check, voice, render, sound, QA, covers |
| [Motion engine](motion-engine.md) | change how videos look: scenes, looks, cursor, UI presets, stage visuals, captions |
| [Game videos](games.md) | prepare footage and source dossiers for game videos |
| [Voice](voice.md) | understand narrator rotation, ElevenLabs and the local backup voice |
| [Prices](prices.md) | the "Every X at today's price" videos: product data, collecting prices, the builder |
| [Publishing](publishing.md) | upload to YouTube and TikTok: OAuth, scheduling, covers, hashtags, TikTok Studio steps |
| [Analytics](analytics.md) | read the channel numbers and see how `genera` picks formats and hours |
| [Development](development.md) | run tests and CI, find a file, fix the usual failures |

## The studio in one paragraph

One command picks a format and a topic, asks an LLM for a structured script, checks the facts, narrates it with ElevenLabs, renders a 1080x1920 video with
Remotion, mixes the sound, runs a quality gate and uploads it. Videos last 62-90 seconds, are always in English and always use the channel palette (obsidian
`#05070C`, blue `#007AFF`, cyan `#00F0FF`). Everything is told in the **Motion Graphics** style (narrated kinetic typography).

## Vocabulary

| Term | Meaning |
|---|---|
| **Motion project** | The JSON that describes one video: title, tags, pinned comment and a list of scenes (`MotionProject` in `services/motion_generator.py`) |
| **Scene** | One screen of the video: a type (`bigText`, `counter`, `versus`...), its text, and the narration read over it |
| **Format** | A recipe with its own scene types, prompt rules and validator (myth, versus, evolution...). See [Formats](formats.md) |
| **Kind** | `curiosity` (a tech idea) or `game` (an engineering fact told over real game footage) |
| **Look** | One of eight visual identities (palette, background, camera, transitions, captions). All are blue |
| **Stage** | The animated visual behind a text scene (chip, waveform, network...) chosen from what the narration names |
| **Cursor** | The mouse pointer used as a character: it selects, drags and clicks things only when that means something |
| **Slot** | One of the four publication hours of a `genera` batch: 13:00, 16:00, 19:00, 22:00 UTC (14:00, 17:00, 20:00, 23:00 in Madrid) |
| **Story bank** | SQLite table of ready scripts that the pipeline uses before asking an LLM |
| **Validator** | The code that rejects a script that breaks a rule (length, cold open, open loop, vote...). LLM answers that fail are retried, then fall back to another provider |

## Where things live

```
main.py                    CLI entry point (always produces Motion videos)
services/motion_*.py       script generator, validators, pipeline (voice, render, sound, QA, upload)
services/looks.py          chooses one of the 14 looks per video
services/series.py         names and numbers each format ("Fix It Now #7")
services/tech_news.py      today's headlines for the news format
services/youtube.py        YouTube upload and thumbnails
services/yt_analytics.py   YouTube Analytics reader
remotion_studio/src/motion the video itself (React / Remotion)
scripts/genera_batch.py    the four-videos-a-day command
data/                      databases, manifests, hand-written scripts (private files are git-ignored)
output/                    rendered videos, one folder per title (git-ignored)
docs/                      the public web portal (GitHub Pages), not documentation
notes/                     private research notes (git-ignored)
```
