# Motion engine

The video is one Remotion composition, `MotionGraphic` (`remotion_studio/src/motion/`), driven only by JSON props: `title`, `theme`, `look`, `captions` and `scenes`.
It is always 1080x1920 (9:16) at 30 fps. The top 12 % and bottom 20 % of the frame stay free for the Shorts / TikTok interface (`SAFE_TOP`, `SAFE_BOTTOM` in `types.ts`).

**Brand:** obsidian background `#05070C`, blue `#007AFF`, electric cyan `#00F0FF` as the accent, Inter for text, an italic serif for accent words, JetBrains Mono for HUD lines (Google Fonts only, loaded in `fonts.ts`).
The generator can never choose another accent colour. All text auto-fits: a long word, headline or number shrinks instead of leaving the frame.

## Where the code is

| File | What it holds |
|---|---|
| `MotionGraphic.tsx` | The composition and `SceneShell`: layers, camera, text lift, transitions, HUD |
| `types.ts` | Props types, scene types, safe zones, `uiAct()` (when a UI preset's action happens) |
| `scenes.tsx` | General scenes: `bigText`, `textWithAccent`, `counter`, `list`, `codeBlock`, `progressBar`, `curve`, `flash`, `footage`, `card`, `outro` |
| `formats.tsx` | `tier`, `versus`, `verdict`, `timeline` |
| `scenes2.tsx` | `rank`, `quiz`, `headline` (the newer formats) |
| `scenes3.tsx` | `split` and `units` |
| `anim.ts`, `reveal.tsx`, `bigfx.tsx` | The animation arsenal: picker, text reveals, big on-screen elements |
| `visuals.tsx` | The **stage**: 13 animated visuals behind text scenes |
| `looks.ts` | The 14 looks |
| `decor.tsx` | Decoration of the look, callouts and the shock effects |
| `ambient.tsx` | Effects picked from what the narration names (a plane, lightning, snow...) |
| `cursor.tsx` | The mouse pointer layer |
| `ui.tsx`, `ui_kit.tsx`, `ui_presets.tsx`, `ui_presets2.tsx` | The 20 drawn interfaces |
| `captions.tsx` | Word-by-word subtitles |
| `primitives.tsx` | Shared pieces: `SafeBox`, `Words`, `Accent`, `Kicker`, the HUD |
| `transitions.ts`, `fx.tsx`, `props.tsx`, `fonts.ts` | Transitions, small effects, prop fields, fonts |

Preview and tweak live: `cd remotion_studio && npx remotion studio`, open **MotionGraphic**. Type-check: `npx tsc --noEmit -p .`

## Scene types

| Type | Use |
|---|---|
| `bigText`, `textWithAccent` | Headlines (at most 4 and 7 words). The accent word is cyan italic serif |
| `card` | A framed headline with no extra data; breaks runs of headlines |
| `counter` | A number counting up. **Counters round decimals** (16.7 shows 17): avoid decimals in scripts |
| `progressBar`, `curve`, `list`, `codeBlock` | Evidence scenes |
| `flash` | A one-word punch |
| `footage` | Real game footage, ungraded (see [Game videos](games.md)) |
| `tier`, `versus`, `verdict`, `timeline` | Table formats |
| `rank`, `quiz`, `headline` | The countdown, quiz and news formats |
| `units` | A price or size in units of an object: a grid of icons (card, chip, RAM, drive, phone, coin, bolt, console, cube) that fills one by one under a big ×N |
| `split` | Two stacked A/B panels with corner labels and a VS chip; `demo` draws bars, a pixel-resolution comparison, a race, squares by area or a "days ago" counter |
| `ui` | A drawn interface the cursor uses (at most 2 per video) |
| `outro` | Always last; ends with a two-option vote |

A scene carries `text`, optional `accentText`, `kicker`, `value`, `items`, `code`, `unit`, `left`/`right`/`leftValue`/`rightValue`, `verdict`, `callout`, `cursor`, `mediaSrc`, a `visual` hint and `durationInFrames`
(60-150 frames). Set `light: true` on at most one scene. Samples: `sample.json`, `sample_formats.json`, `sample_ui.json`.

## Looks

Eight visual identities, all blue (`looks.ts`, chosen by `services/looks.py`): *obsidian*, *ocean*, *indigo*, *cobalt*, *glass*, *paper* (light), *ice* (blue monochrome), *blueprint*.
A look sets the palette, the background (glow, aurora, gradient mesh, frosted spheres, dot matrix, grid), the particles, the headline typeface, left or centred layout, capitals,
the camera move (drift, push, orbit, handheld, still), the pool of transitions, the HUD (mono line, story segments, corner brackets, ruler ticks) and the caption style.
`choose_look` uses the format's affinities (`AFFINITY` in `services/looks.py`), never one of the last three looks (kept in `shorts_history.preset` as `remotion_motion:<look>`), and varies the pick by a hash of the topic.
Force one in a silent preview: `scripts/render_silent_preview.py <script.json> --look cobalt --out DIR`.

## The animation arsenal

Three things are picked per scene from the scene's own words (`pickSeries` in `anim.ts`: deterministic, so the same script renders the same video, and never one of the last few picks, so nothing repeats):

- **Text reveal** (`reveal.tsx`; the pool is the calm ones: pop, type, draw, mask, wave, blur; scramble, drop and slice exist but are out of the pool as too intense): `pop` (bouncy words), `type` (typewriter with a caret; the first scene always types), `draw` (outline drawn, then filled), `scramble` (random glyphs that resolve), `mask` (words rise out of a mask), `drop` (letters fall and bounce), `wave` (letters rise in a wave), `blur` (zoom-in from a blur), `slice` (two halves slide in). Every effect ends on untouched text. The accent phrase uses the letter effects too.
- **Camera move** (`MotionGraphic.tsx`): `pushIn`, `pullOut`, `panLeft`, `panRight`, `tiltUp`, `tiltDown`, `dolly`, `orbit`, `crane`, `punch`; every fifth scene also jump-cuts slightly closer halfway through. Moves are deliberately small (about 7-9 % zoom); still-camera looks get 60 % of that.
- **Big element** (`bigfx.tsx`, behind the text, moved by the camera): `rings`, `rays`, `scribble` (a hand-drawn circle and underline), `arrow`, `giantIcon`, `brackets`, `laser`, `speed`, `stars`, `diamonds`, `pie`, `crosshair`, `dotwave`, `frameDraw`. Scenes with a stage visual only get the quiet ones; flash, footage, tier, ui and outro get none, and only one scene in three gets one; they are drawn at 55 % opacity.

Add one by adding its name to the lists in `anim.ts` and drawing it.

## Layers, camera and legibility

`SceneShell` draws two separate layers:

1. **Backdrop** (stage, ambient effects, decor, props): this is the only layer the **camera** moves (drift, push, orbit, a gentle handheld drift, or still).
2. **Text**: fixed. It never gets scale, rotation or shake, only a vertical lift when it must make room for the stage.

The rule came from a bug: with the camera on the whole scene, text under a continuous scale or rotation visibly vibrated. Do not apply camera transforms to the text layer.

**Captions never touch anything.** The caption strip sits `CAPTION_DROP` (56 px) below the bottom of the content area, and everything a scene draws is faded out just above it (a mask in `SceneShell`), so no text, stage or big element can sit under a subtitle.

**Stage and text never collide.** The text block is measured (`data-safebox`, `offsetTop` / `offsetHeight`, which ignore transforms). If the block ends below `STAGE_TEXT_MAX_BOTTOM` (760 px) it is lifted
(never above `STAGE_TEXT_MIN_TOP`, 340 px, which would hit the HUD); the stage is drawn in the room left under it, scaled to fit (`DH = 560` design height), and dropped when there is none.
A scene with a stage gets no ambient fly-by or decor. The callout sits above the captions; text has a shadow; the news band stays clear of captions.

## Stage visuals

`pickVisuals` in `visuals.tsx` reads the narration and text of a scene and picks a visual: `Crowd`, `Memory`, `Cores`, `Network`, `Bars`, `Wave`, `Gauge`, `MapGrid`, `City`, `Layers`, `Matrix`, `Radar`, `Orbit`.
They appear behind `STAGE_SCENES` (`bigText`, `textWithAccent`, `card`, `counter`, `progressBar`, `curve`, `verdict`, `list`, `codeBlock`, `timeline`, `headline`). A script may suggest one with the scene's `visual` field.

## Ambient effects and decor

`ambient.tsx` adds effects chosen from what the narration names: a plane crossing the screen, signal waves, lightning, embers, snow, packets, coins, an equalizer, notification banners, a filling battery,
a clock, a padlock, a magnifier, binary rain. The big fly-bys appear once per video and no effect repeats within three scenes.
`decor.tsx` puts a design element of the look in the empty lower part of text scenes (a giant outlined scene number, concentric rings or a dimension line).

## Beats inside a video

- **Callout**: on long scenes a tag with a figure and its unit (or an acronym) from the second half of the narration pops up when the narrator says it, with a small zoom punch and a pop sound (`pick_callout`).
- **Re-hook**: at the scene nearest the middle, a flash, a wide ring, a boom and a riser (`rehook_index`).
- **Loop tease**: the last frames fade to the hook headline so the replay feels continuous (`LoopTease`).
- **Title strip**: the HUD line stays on the whole video with the series in the accent colour and the topic (`series` prop, from `MotionProject.series_label`).
- **Caption styles** per look: `pill`, `plain`, `underline`, `mono`, plus `oneword` (one huge outlined word at a time, cobalt), `wordpill` (the spoken word on a coloured pill, ocean) and `twotone` (two lines, first half in the accent colour, glass).
- **Key = value rows**: a `codeBlock` whose lines all look like `KEY = meaning` is drawn as key pills with their meaning (decode labels), not as typed code.
- **Callout leader line**: over a stage the callout tag is joined by a thin line to a pulsing ring on the visual.
- **Footage** is shown exactly as it is (no colour grade, tint, scan lines, vignette or brackets) in a rounded card over a blurred copy of itself that fills the frame.
- **Captions**: word by word from the voice timing (`build_captions`), the spoken word highlighted; skipped on `tier`, `ui`, `footage`, `flash`. The accent phrase pulses when the narrator says it (`accentCue`).
  A progress indicator in the look's style shows how much of the video is left. All colours, including tier ranks and verdict stamps, are blue.

## The cursor

The mouse pointer is a character used only when it means something (no tabs, no hovering, no waiting). A scene may carry `cursor`:

| Action | Where | What it does |
|---|---|---|
| `select` | `bigText`, `textWithAccent` | Drags across the key phrase as the narrator says it (`cursorCue` comes from the voice timing, `cursor_cues()`) |
| `drag` | `progressBar`, `tier` | Grabs the knob and pulls the bar; carries the new chip into its row |
| `click` | `codeBlock`, `list` | Presses the setting or step |
| `toggle` | first scene only | A macOS-style Control Center panel (flip Airplane Mode, watch Wi-Fi and Bluetooth switch off) |

At most 3 pointer scenes per video (4 in `fix`), never closer than two scenes. `cursor.tsx` measures the elements tagged `data-cursor="target"` every frame, so it acts on what is really on screen.
`sanitize_cursors` and `assign_cursors` (`services/motion_generator.py`) clean and complete older scripts.

## UI presets

A `ui` scene draws an interface that the cursor really uses. The data contract of each is `UI_PRESETS` in `services/motion_generator.py` (it also feeds the prompt):
`display`, `taskmgr`, `bios`, `terminal`, `gpupanel`, `gamemenu`, `frametime`, `speedtest`, `wifilist`, `router`, `keycaps`, `filemgr`, `diskbar`, `battery`, `tabmem`, `speclabel`, `leaderboard`, `partpicker`,
`dimm`, `permissions`. At most 2 per video, never consecutive. They are generic (channel palette, no logos). `UI_FORMATS_OFF` disables them in `tier`, `versus`, `myth`, `evolution`, `top5`, `quiz`, `news` and `review`, which are built from a fixed run of their own scenes. Demo of all 20: `sample_ui.json`.

## Retention rules

`retention_problems()` (`services/motion_generator.py`) enforces them on every generated script; hand-written banks are measured with `scripts/lint_retention.py`.

1. **Cold open**: scene 1 is the claim or the surprising number in about 14 words or fewer (validator limit 16), never a greeting or "so / today / did you know".
2. **Open loop**: one of scenes 2-5 promises a payoff that the last third delivers (matched by the `OPEN_LOOP` pattern; the prompt lists accepted phrasings).
3. **Visual break**: never three headline scenes in a row.
4. **Two-option vote**: the outro narration ends with "A or B?" and `pinned_comment` repeats it ("A or B? Reply with one word.", at most 120 characters).
5. **Pace**: at most 17 words of narration per scene (24 in tier/versus), so the screen changes every 5-6 seconds.

All 241 banked scripts (`docs/generated_scripts/bank/` and the unused `story_bank` rows) were brought up to these rules on 9 Nov 2026 by `scripts/update_bank_scripts.py` (idempotent; `--dry-run`, `--backup`).
`tests/test_motion_validators.py` fails if a banked script breaks a rule.

## Quality tools

- `scripts/render_silent_preview.py`: renders a script with no narration (no ElevenLabs, no upload, no history) to check a design or a script.
- `scripts/analyze_motion.py <video> --cuts 60,170`: measures pops and jitter per shot without watching.
- `scripts/render_cover.mjs <props.json> <out.png> [publicDir] [frame]`: the cover still.

## Visual options added in Nov 2026 (33)

All are picked automatically; nothing needs to be set per video (the checks in `tests/test_motion_validators.py` fail if a look names an option without code behind it).

- **6 looks** (all blue): `neon` (slanted light stripes, capitals), `midnight` (bokeh lights), `steel` (circuit board), `electric` (rolling waves), `frost` (spotlight cone), `deepsea` (falling light streaks). Each has its own typeface (Lexend, Urbanist, Rubik) and format affinities in `services/looks.py`.
- **6 backgrounds** behind them: `stripes`, `bokeh`, `circuit`, `waves`, `spotlight`, `rain`.
- **6 big effects** (`bigfx.tsx`): `hexes`, `orbitDots`, `equalizer`, `radar`, `comets`, `ripples` (the last two are light enough for stage scenes).
- **3 camera moves** (backdrop only, never the text): `rollIn`, `slideDiag`, `breathe`.
- **4 transitions**: `pushDown`, `curtain`, `cornerIris`, `shutter`.
- **3 text reveals**: `rise`, `focus`, `flip` (they end untransformed, so settled text never shimmers).
- **3 caption styles**: `karaoke` (colour sweeps through the spoken word), `box` (marker box on the word), `bounce`.
- **2 decors** for the empty lower part of text scenes: `bars` (equalizer), `arcs` (turning quarter arcs).

A neon-look test video renders in about 78 s (the obsidian benchmark takes 55 s on a quiet machine; the machine was busy), so these add no heavy layer. Check one new look with `scripts/render_cover.mjs <props> <png> "" <frame> <scene>` before changing its numbers.

## Polish pass (Nov 2026)

`remotion_studio/src/motion/polish.tsx` holds the finishing touches; the rest are small edits in the files named here.

- **Tier scenes**: bigger chips and a *product card* under the board: a drawn icon (cpu, gpu, ram, ssd or generic chip, picked from the name), the chip that just landed and its tier. When the scene carries `value` + `unit` (the "Every X" scripts set the rounded price and `€`) a counter runs up to it, with soft ticks in the sound.
- **Outro**: when the closing line is "..., A or B?" (or `items` has two entries) two A/B cards and "vote in the comments" appear. They show only what the video says: no invented poll results.
- **Accent phrases** get an underline that is drawn after the phrase lands.
- **Film finish** (every scene except real footage): a soft vignette, faint moving grain (hides banding in dark gradients) and a short dip of the light just before a data reveal (counter, versus, verdict, timeline, units, split).
- **Hook at frame 0**: the cold open is on screen immediately (it zooms in from 1.07) and its typed headline starts with the first letters already visible.
- **Transitions by scene kind** (`PREFERRED` in transitions.ts): a ranking slides in like a list, data reveals arrive with weight; the look's own set still decides which are allowed.
- **Safe margins**: content, captions and the tier board keep 96 px at the sides (TikTok's action buttons sit at the right edge); captions are 60 px.
- Click ripples already existed (`cursor.tsx`); they only appear in scenes that have a `cursor` action.

## Script style rules added in Nov 2026

- **Closing vote**: it names this video's own two options ("Team 7800X3D or team 9800X3D?"); the generic "Did that surprise you or did you know it? Tell me below" is rejected by `retention_problems` (`GENERIC_CLOSER`). The outro's A/B cards come from the pinned comment (`add_vote_items`).
- **Hook**: a number, a concrete claim or a tension; "Let us", "Let's", "So", "Today", "Did you know" are rejected (`BAD_OPENER`).
- **Accent**: the accent phrase must not repeat the headline's first or last words; `fix_duplicate_accents` removes the repeat from the headline (runs in the validator and when a script is prepared).
- **"Every X" scripts**: hooks live in `data/products/<family>.json` and use `{count}` for the number of priced items; each tier scene shows `n of N` and, when the line is short, a true price comparison with the previous item.
- `scripts/rewrite_bank_closers.py` brought the unused banked scripts up to these rules (275 closers, 29 hooks, 32 accents; copy of the database first); `--files` syncs the git-ignored mirror in `docs/generated_scripts/bank/`.
