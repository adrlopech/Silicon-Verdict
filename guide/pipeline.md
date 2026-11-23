# Pipeline

`run_motion_pipeline()` in `services/motion_pipeline.py` makes one video. `main.py` is its command-line entry point.
It is two halves: `prepare_motion_video()` (subject, script, fact-check, footage, narration: network work) and `finish_motion_video()` (render, cover, sound, QA, files, upload, history: CPU work).
`scripts/genera_batch.py` overlaps them: while video N renders, video N+1 is prepared and video N-1 is uploaded. A video that may pick game footage is never prepared early (the footage ledger is only updated when a video is finished).

```
format + topic ─► script (story bank, else LLM) ─► validators ─► fact-check ─► voice ─► Remotion render ─► sound mix ─► QA gate ─► cover ─► files ─► YouTube
      │                                                                                                                              │
 FORMAT_WEIGHTS / source text                                                  output/youtube/<title>/<date-time>.mp4  (+ .png cover) │
                                                                               output/tiktok/<title>/<date-time>.mp4 / .png / .txt ◄──┘
```

## 1. Choosing format and topic

- `--motion-format X` fixes the format; `any` draws one by weight (never the same as the previous video, never `news`, no game format when no game has unused footage).
- `--motion-kind curiosity|game|auto` chooses between a tech idea and a game video. `easter` is always a game video.
- `--topic "..."` fixes the subject. A topic skips the story bank. With `source_text` (a text file passed by `genera_batch.py --topics`) the script must be grounded on it.
- `news` builds its own source text from live RSS feeds (`services/tech_news.py`).
- A hand-written script (`MotionProject` JSON) can be passed as `script=` and skips generation, but not the validators.

## 2. The script

`services/motion_generator.py` holds the schema, the prompts, the validators and the fact-check.

- **Story bank first.** For curiosity videos the pipeline takes a banked script of the requested format from the `motion` bank (SQLite `story_bank`) before asking an LLM.
  The bank is filled by hand with `scripts/refill_story_bank.py --series hardware|simple|motion --format ...`; it is never filled automatically. Taking a script is only final once a video was produced (a failure releases it).
- **LLM layer.** `services/gemini_client.py` is the single entry point for every call. Gemini first, with quota-aware cooldowns kept in `data/gemini_state.json`; then Cloudflare Workers AI
  as the automatic fallback (models are listed in `.env`). Answers are structured JSON, validated and retried; a fallback model that breaks a rule is shown its own rejected draft and the reasons (up to 3 attempts), which
  is what makes Cloudflare's gpt-oss-120b usable for scripts. Groq was removed (its free tier cannot fit a script prompt); the fact-check's strong reviewer is Cloudflare's gpt-oss-120b. A request that carries images goes to a vision model.
- **Validators** (`make_validator`) reject a script that breaks a rule. They check structure (13-19 scenes, a hook first, an outro last, no two consecutive scenes of the same type unless it is a format's own type),
  text length (7 words per scene, 4 for `bigText`, accent 3), narration length (17 words per scene, 150-190 words in all, estimated at 61 s or more), English only, the format's own rules
  (see [Formats](formats.md#what-each-validator-demands)) and the [retention rules](motion-engine.md#retention-rules).
- **Fact-check gate.** A second pass looks for false technical claims and wrong figures (and, for game videos, quotes that are not in the source dossier), rewrites faulty scenes and checks again.
  Scripts that cannot be fixed are discarded. If no reviewer answers, the video still goes out (the script was grounded and validated).
- **Clean-up.** `strip_markers` removes markdown asterisks from everything shown, spoken or published (the renderer would draw them literally). `_repair` clamps scene lengths and trims lists.
- **Source text.** With a source text, every claim about the subject must come from it, and a counter or bar may only show a figure written in it.

If every provider fails the validators, the run fails for that video. This happens most with the newer formats; see [Daily workflow](daily-workflow.md#when-a-slot-fails).

## 3. Voice

`narrate_scenes()` makes **one continuous ElevenLabs take** for the whole video and slices it per scene at the pause between two words (no cuts in the middle of a sentence). Word timestamps drive
the captions, the accent pulse and the cursor. The narrator depends on the format. If ElevenLabs fails, a local clone speaks instead. See [Voice](voice.md).

The voice decides how long each scene lasts. If the voice is shorter than 62 s (`MIN_VIDEO_SECONDS`) the pipeline holds scenes at sentence ends. Each scene starts 0.12 s before the narrator speaks (`VOICE_LEAD`) so the text lands first.

## 4. Render

`render_motion()` writes the props JSON and runs `scripts/render_motion.mjs`: bundle, `selectComposition`, `renderMedia` (H.264, 30 fps, CRF 18). The script refuses anything but 1080x1920.
A game video also stages its footage in a public directory. See [Motion engine](motion-engine.md) for what the composition draws.

Render by hand: `node scripts/render_motion.mjs props.json out.mp4 [publicDir]`.

## 5. Sound mix

`add_sound()` mixes the narration with:

- a music bed per format (`MUSIC_BY_FORMAT`; the topic picks between two beds) at low level,
- a soft whoosh under each scene transition,
- cues: an impact on the first frame and on `flash` scenes, a re-hook boom plus riser at the scene nearest the middle, a riser before each data reveal (counter, versus, verdict, timeline; at most 4),
  a pop with each callout, and short clicks and selects for the cursor.

**Levels are set per file.** Every effect file has a measured mean level (`SFX_MEAN`); `sfx_gain()` brings each cue to its target (`CUE_TARGET_DB`, whooshes at `WHOOSH_TARGET_DB`), well under the voice.
Without this, `sfx_whoosh.wav` (mean -5.9 dB) was louder than the narration. If effects sound too loud or too quiet, change those two tables in `services/motion_pipeline.py`.
The final mix goes through a two-pass loudness normalisation (`loudnorm I=-14 TP=-2 LRA=11`) and a limiter; if the AAC encode still peaks too high the mix is trimmed (`PEAK_CEILING_DB = -1.2`).
The sound files come from `scripts/make_motion_sfx.py` and live in `assets/audio/`.

## 6. QA gate

`qa_motion()` checks with ffmpeg: file exists and is over 300 KB, 1080x1920, H.264, an audio track, peak not above -0.5 dB, mean not below -28 dB (a quiet mean means the narration is missing),
and duration from 61 s up to 181 s (monetisation needs more than 60 s; `MAX_VIDEO_SECONDS` is 180). Videos normally last 62-90 s.
A video that fails stays local (export-only) and is **not** uploaded.

## 7. Cover

Right after the render, `render_cover()` (`scripts/render_cover.mjs`) renders a still of the cold open (scene 1, frame 42, with no subtitles) in the video's own look.
It is best effort: if it fails the video is not held back. The cover is saved next to both copies as `<date-time>.png` and returned as `tiktok_cover`. YouTube takes it as the thumbnail when the video is uploaded
with `scripts/upload_existing.py`; for TikTok it is uploaded by hand in TikTok Studio (see [Publishing](publishing.md)).

## 8. Files, upload and history

Each video gets one folder per platform, named after its title (`services/output_layout.py`):

```
output/youtube/<title>/<date-time>.mp4  and  .png
output/tiktok/<title>/<date-time>.mp4  .png  .txt      the .txt has title, description, hashtags, pinned comment and scene list
output/tiktok_small/<title>.mp4                        a <10 MB copy made by genera_batch.py for the upload tool
```

Hashtags are always one joined word. A game video adds the footage credits to the description ("official Steam store media"). If `--export-only` is not set, the video is uploaded to YouTube
with `--privacy` (default `public`). The run is recorded in `data/history.db` (`shorts_history`: topic, title, video id, format, look) so that series numbers, look rotation and the "never the same as last time" rule work.

## Other flags of `main.py`

`--dry-run` (everything but the upload), `--privacy public|unlisted|private`, `--from-bank` (take a banked script), `--topic`, `--motion-kind`, `--motion-format`, `--export-only`.
