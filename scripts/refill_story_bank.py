#!/usr/bin/env python3
"""Fills the story bank (data/history.db) with validated scripts so publishing never depends on a Gemini spike.

Run it off-peak (e.g. nightly via cron/launchd):
  python scripts/refill_story_bank.py                    # top up the series to 8 ready stories
  python scripts/refill_story_bank.py --series simple --target 12
  python scripts/refill_story_bank.py --series minecraft --target 20
"""
import argparse
import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.gemini_client import GeminiUnavailable  # noqa: E402
from services.history import get_recently_used_topics_safe  # noqa: E402
from services.story_bank import add_story, count_ready, topics_in_bank  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("refill_story_bank")


def refill_simple(target: int) -> int:
    from services.story_generator import generate_story_live
    added = 0
    while count_ready("simple") < target:
        avoid = topics_in_bank("simple") + get_recently_used_topics_safe()
        try:
            story = generate_story_live(avoid_topics=avoid)
        except GeminiUnavailable as exc:
            log.warning("Stopping: Gemini unavailable (%s)", str(exc)[:120])
            break
        add_story("simple", story)
        added += 1
        log.info("Banked simple story: %s (%d ready)", story.topic, count_ready("simple"))
    return added


def refill_minecraft(target: int) -> int:
    from services.mc_story_generator import generate_story_live
    added = 0
    while count_ready("minecraft") < target:
        avoid = topics_in_bank("minecraft") + get_recently_used_topics_safe()
        try:
            story = generate_story_live(avoid_topics=avoid)
        except GeminiUnavailable as exc:
            log.warning("Stopping: Gemini unavailable (%s)", str(exc)[:120])
            break
        add_story("minecraft", story)
        added += 1
        log.info("Banked minecraft script: %s (%d ready)", story.topic, count_ready("minecraft"))
    return added


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", choices=["simple", "minecraft", "all"], default="all")
    ap.add_argument("--target", type=int, default=8, help="Ready stories to keep per series")
    args = ap.parse_args()

    total = 0
    if args.series in ("simple", "all"):
        total += refill_simple(args.target)
    if args.series in ("minecraft", "all"):
        total += refill_minecraft(args.target)
    log.info("Done: %d new stories banked. Ready: simple=%d, minecraft=%d", total, count_ready("simple"), count_ready("minecraft"))


if __name__ == "__main__":
    main()
