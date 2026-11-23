# Content formats

A **format** is a recipe: its own scene types, prompt rules and validator (`FORMAT_RULES` and `_format_problems` in `services/motion_generator.py`). There are the classic explainer plus
20 named formats. Every format shares the same rules: a hook first, an outro last, a narration on every scene, 150-190 spoken words, 13-19 scenes (tier and versus may use 9-19),
and the [retention rules](motion-engine.md#retention-rules). The same fact-check pass applies to all of them.

Call one with `--motion-format <name>`:

```bash
.venv/bin/python main.py --motion-format myth --export-only
.venv/bin/python main.py --motion-format any      # weighted random pick, never news
```


## Overview

| Format | What the video is | Key scene types | Voice | Weight in `any` |
|---|---|---|---|---|
| `classic` (`auto`) | The default explainer: one tech idea with words, counters, code, bars, curves | bigText, textWithAccent, counter, codeBlock, curve | Liam | 1 |
| `myth` | 4-5 widespread beliefs, each stamped MYTH, FACT or PARTLY | verdict | Adam | 1 |
| `tier` | S-F tier list of 6-8 items that fills up item by item | tier | Adam | 1 |
| `whatif` | A computing hypothetical with escalating consequences | bigText, counter, flash | Liam | 3 |
| `evolution` | How one technology changed over the years | timeline, counter, progressBar | Adam | 3 |
| `versus` | Two contenders, 3-5 rounds of bars, a winner per round | versus | Adam | 3 |
| `hardware` | Silicon / memory / storage / networking deep dive, cursor as an accent | codeBlock, progressBar, curve | Adam | 2 |
| `simple` | An everyday tech mystery hosted by the cursor | cursor scenes | Liam | 1 |
| `fix` | A symptom fixed with one exact setting; the cursor does the clicks | codeBlock + list | Liam | 3 |
| `decode` | What a product name or spec label really means (RTX 5070 Ti, DDR5-6000 CL30) | codeBlock + list, select | Liam | 3 |
| `top5` | A countdown from 5 to 1 | rank | Liam | 2 |
| `eli5` | One hard idea explained with one everyday analogy | card + list | Liam | 2 |
| `fails` | One famous tech failure told as a story | timeline + counter/progressBar | Adam | 2 |
| `numbers` | One subject told through 4-6 striking figures | counter / progressBar (4+) | Adam | 2 |
| `quiz` | Two or three three-option questions, each revealed | quiz | Liam | 2 |
| `stop` | Three habits that quietly hurt a device, each with a better one | list + counter/progressBar/card | Liam | 2 |
| `rumor` | One rumour weighed, with a plausibility bar | progressBar + card/list | Adam | 2 |
| `review` | "Worth it?" verdict: buy, wait or skip | list x2, verdict | Adam | 1 |
| `priced` | The price or size of 4-6 surprising things told in units of one object ("Priced in PS5s") | units | Liam | 2 |
| `news` | Tech Briefing: today's headlines from live RSS feeds | headline | Adam | never picked |
| `easter` | A game's hidden detail, told over real footage | footage | Liam (all game videos) | 1 (only if a game has unused footage) |

Narrators come from `VOICE_BY_FORMAT` in `services/motion_pipeline.py` (Daniel is retired: his formats went to Adam or Liam). `any` also picks `curiosity` and `game` kinds (weight 1 each).
`easter` and every game video use Liam. The `genera` command draws from the same weights but excludes `easter` and `news` (see [Daily workflow](daily-workflow.md)).

## What each validator demands

Beyond the shared rules, `_format_problems` rejects a script when:

- **myth**: it has fewer than 4 `verdict` scenes, fewer than 2 myths, or no fact/partly. A verdict needs `accentText` of at most 6 words (the one-line truth).
- **tier**: it does not have 6-9 `tier` scenes, a scene does not repeat the previous board and add exactly one item at the end, or the final board uses fewer than 4 different tiers. Items are `"S|label"`, labels up to 22 characters.
- **evolution**: fewer than 2 `timeline` scenes. A timeline has 3-5 items `"1999|label"`: four-digit years in chronological order, labels up to 28 characters.
- **versus**: not 3-5 `versus` scenes, contender names that differ between rounds or exceed 16 characters, non-positive values, or figures not said in the narration.
- **whatif**: fewer than 3 consequence scenes (counter, progressBar, curve, list or codeBlock).
- **fix** and **decode**: no `codeBlock` or no `list`. The prompt also asks for the cursor: `click` on the code and the list in `fix` (2-4 scenes), `select` on the label scene in `decode`.
- **top5**: the `rank` scenes are not exactly 5, 4, 3, 2, 1 in order (`value` is the position).
- **eli5**: fewer than 2 `card` scenes or no `list`.
- **fails**: no `timeline`, or no counter/progressBar.
- **numbers**: fewer than 4 `counter`/`progressBar` scenes.
- **quiz**: not 2-3 `quiz` scenes, or one without exactly 3 `items` and `value` 1-3.
- **stop**: no `list`, or none of counter/progressBar/card.
- **rumor**: no `progressBar`, or fewer than 2 `card`/`list` scenes.
- **review**: not exactly one `verdict` near the end, fewer than 2 `list` scenes, or a verdict other than buy/wait/skip. Buy/wait/skip stamps are only valid in `review`.
- **priced**: not 4-6 `units` scenes, or the `unit` name differs between them. A units figure must be said in the narration (up to 200, whole numbers recommended).
- **news**: not 3-4 `headline` scenes, or a headline without a `kicker` (the outlet). Headlines allow 10 words; three headline scenes in a row are rejected.
- Scene types that belong to one format are rejected in the others: `rank` (top5), `quiz` (quiz), `headline` (news), and tier / versus / verdict / timeline (their own formats, plus review and fails for verdict and timeline).

## Scene fields used by formats

| Scene type | Fields |
|---|---|
| `tier` | `items` as `"S\|label"`; every scene repeats the board and adds one item |
| `versus` | `left`, `right`, `leftValue`, `rightValue`, `unit`, optional `winner` |
| `verdict` | `verdict` = myth / fact / partly (myth format) or buy / wait / skip (review), `accentText` = the one-line truth |
| `timeline` | `items` as `"year\|label"` |
| `rank` | `value` = position 5..1, `text` = item, `accentText` = why |
| `quiz` | `items` = 3 options, `value` = correct option 1-3 |
| `units` | `unit` = the unit's name (same in every scene), `value` = how many units, `text` = the thing, `accentText` = its own price or size |
| `split` | `demo` = bars / res / speed / size / ago, `left` / `right` labels, `leftValue` / `rightValue`, `unit`. Allowed in versus, evolution, whatif, numbers, fails, hardware and priced |
| `headline` | `text` = headline, `kicker` = outlet in capitals, `accentText` = meaning, `unit` = how long ago |

Demos: `remotion_studio/src/motion/sample_formats.json` (tier, versus, verdict, timeline) and `sample_ui.json`. Hand-written samples of the newer formats are in `data/scripts/sample_*.json`.

## The news format (Tech Briefing)

`services/tech_news.py` reads the RSS feeds of The Verge, Ars Technica, TechCrunch, Engadget, Tom's Hardware and Hacker News (stories from the last 48 hours), groups headlines about the same story,
and ranks stories covered by more outlets first. `build_source_text()` turns the top 8 into the source text of the script (it raises if fewer than 3 stories can be read).
The script must paraphrase, name the outlet it relies on, and hedge anything only reported. Preview the text with `.venv/bin/python -m services.tech_news`.

## Series numbers

`services/series.py` names each format ("Fix It Now #4", "Decoded #4", "Spec Duel #7", "Silicon Files #5", "Evolution #10", "Top 5", "Explained Simply", "Tech Fails", "By the Numbers", "Tech Quiz",
"Stop Doing This", "Rumor Mill", "Worth It", "Tech Briefing"). The number goes in the title and on the first frame, with a one-word series hashtag. The number is the count of distinct topics of that
format in `shorts_history` plus one. Hashtags are always one joined word.

## Adding a format

1. Add the name to `FORMATS`, a weight to `FORMAT_WEIGHTS`, a `FORMAT_RULES` prompt block and the validator branch in `_format_problems` (`services/motion_generator.py`).
2. Add its narrator to `VOICE_BY_FORMAT` and its music to `MUSIC_BY_FORMAT` (`services/motion_pipeline.py`), its series name to `services/series.py` and its look affinities to `services/looks.py`.
3. If it needs a new scene type: add it to `SceneType`, to `remotion_studio/src/motion/types.ts` and draw it (`scenes2.tsx` or `formats.tsx`).
4. Add it to `--motion-format` choices in `main.py` and a test in `tests/test_motion_validators.py`.
5. Write a sample in `data/scripts/` and check it with `scripts/render_silent_preview.py`.
