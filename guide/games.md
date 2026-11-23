# Game videos

A **game video** (`--motion-kind game`, or the `easter` format) tells one engineering fact about a game over real footage. It is the only kind that needs prepared media and a source dossier.

```bash
.venv/bin/python main.py --motion-kind game --export-only
.venv/bin/python main.py --motion-format easter --export-only   # a hidden detail, always a game video
```

If no game has unused footage the run stops and says so. All game videos use the Liam voice.

## One-time preparation

```bash
python3 scripts/fetch_game_images.py      # official Steam screenshots into assets/games/<game>/
python3 scripts/fetch_game_clips.py       # 2-5 s clips cut from the official Steam trailers (1280 wide, no audio)
python3 scripts/caption_game_media.py     # a vision model describes what every item shows (once)
python3 scripts/build_game_facts.py       # source dossier per game: Wikipedia + Steam description (paced, cached in data/game_facts/)
```

Add a game: put its entry in `data/games_catalog.json` (real Steam appid and release date), then run `fetch_game_images.py --appid <id>`, `caption_game_media.py` and `build_game_facts.py`.
Top the footage up whenever games run out of unused items. A game with fewer than 6 unused, captioned items (`MIN_MEDIA_PER_GAME`) is skipped; near-black frames are never used.

## Rules the pipeline enforces

- **Footage is spent once.** Every item is used in ONE video and then deleted. Its key goes to a ledger (`game_media_used` in `data/history.db`) so it is never downloaded again.
  The footage is only spent when a finished video passes the QA gate.
- **Games rest 14 days.** After a game appears it is blacklisted for 14 days (`BLACKLIST_DAYS`; inspect with `python -m services.game_registry`).
- **A footage scene must show what its narration mentions.** The fact-check pass verifies it. The scene shows the footage as it is, with no colour filter, in a rounded card over a blurred copy of itself and a game tag.
- **Facts come from the dossier.** `services/game_facts.py` builds a dossier (the development, technology and design sections of the Wikipedia article plus the Steam store description), prebuilt so production never depends on Wikipedia.
  The script may only state facts the dossier supports; every claim-bearing scene (at least 6) carries a verbatim `evidence` quote, and the validator rejects any quote that is not really in the dossier.
  A counter or bar may only show a figure written in the dossier.
- **Review.** The fact-check sees the dossier and the quotes and runs on the strongest reviewer (`gpt-oss-120b`), retried once if its per-minute window is full. If unavailable, a panel of the other
  reviewers answers and their issues are merged. Flagged scenes are rewritten from the dossier and checked again.
- **When something fails anyway.** No source text at all gives a conservative script (no figures or dates, no counters). No reviewer answering still publishes the video.
- **Credits.** The description lists the games with "official Steam store media".
- **Banked game scripts** go first: they are told over screenshots of their game (`assets/games/<game>/`).

## Related files

`services/game_images.py` (manifest, captions, one-use consumption, credits), `services/game_registry.py` (blacklist and ledger), `services/game_facts.py` (dossiers),
`data/games_catalog.json`, `data/game_facts/`, `data/story_seed/game_*.py` (seed scripts).

Product names and game titles belong to their owners; footage comes from official Steam store pages and is credited in each description.
