#!/usr/bin/env python3
"""Fills the story bank (data/history.db) with validated scripts so publishing never depends on a Gemini spike.

Run it off-peak (e.g. nightly via cron/launchd):
  python scripts/refill_story_bank.py                          # top up the hardware / simple Motion formats to 8 ready scripts each
  python scripts/refill_story_bank.py --series simple --target 12
  python scripts/refill_story_bank.py --series motion --format myth --target 10
Series: motion (needs --format), hardware / simple (= motion with that format), all.
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


def refill_motion(fmt: str, target: int) -> int:
    """Curiosity Motion scripts of one format ('auto' = classic explainer), fact-checked like a live generation."""
    from services.motion_generator import generate_motion_project
    added = 0
    while count_ready("motion", fmt) < target:
        avoid = topics_in_bank("motion") + get_recently_used_topics_safe()
        try:
            project = generate_motion_project(None, avoid_topics=avoid, kind="curiosity", fmt=None if fmt == "auto" else fmt)
        except (GeminiUnavailable, RuntimeError) as exc:
            log.warning("Stopping: no script possible right now (%s)", str(exc)[:120])
            break
        add_story("motion", project)
        added += 1
        log.info("Banked %s Motion script: %s (%d ready)", fmt, project.topic, count_ready("motion", fmt))
    return added


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", choices=["hardware", "simple", "motion", "all"], default="all")
    ap.add_argument("--format", default=None, help="With --series motion: auto, hardware, simple, myth, tier, whatif, evolution or versus")
    ap.add_argument("--target", type=int, default=8, help="Ready scripts to keep per series / format")
    args = ap.parse_args()

    total = 0
    if args.series in ("hardware", "simple"):
        total += refill_motion(args.series, args.target)
    elif args.series == "motion":
        if not args.format:
            ap.error("--series motion needs --format")
        total += refill_motion(args.format, args.target)
    elif args.series == "all":
        total += refill_motion("hardware", args.target) + refill_motion("simple", args.target)
    log.info("Done: %d new scripts banked. Ready: hardware=%d, simple=%d", total, count_ready("motion", "hardware"), count_ready("motion", "simple"))


if __name__ == "__main__":
    main()
