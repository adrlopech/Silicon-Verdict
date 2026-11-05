#!/usr/bin/env python3
"""Builds (or refreshes) the source dossiers of every game that has footage, paced so Wikipedia never rate-limits.
Run it ahead of time so video production never depends on Wikipedia being reachable at that moment.   python scripts/build_game_facts.py [--force]
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.game_facts import CACHE_DIR, _slug, get_game_facts  # noqa: E402
from services.game_images import available_games  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="rebuild dossiers that already exist")
    args = ap.parse_args()
    for g in available_games(include_blacklisted=True):
        if args.force:
            (CACHE_DIR / f"{_slug(g)}.txt").unlink(missing_ok=True)
        f = get_game_facts(g)
        print(f"{g}: {'no source text' if not f else str(len(f)) + ' chars'}")


if __name__ == "__main__":
    main()
