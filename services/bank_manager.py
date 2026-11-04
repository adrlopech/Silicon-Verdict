"""Story bank policy.

- Whenever the bank has fewer than LOW_WATERMARK (30) ready scripts for a series ('simple', 'game'),
  a batch of BATCH (20) new scripts is generated.
- After every video, the bank is checked and, if below the watermark, the batch is generated.
- If the bank is empty before a video, production pauses until a batch is generated.
- Scripts already in the bank are never deleted, and the bank may grow above the watermark.
"""
import logging
from typing import Any, Optional

from services.gemini_client import GeminiUnavailable
from services.history import get_recently_used_topics_safe
from services.story_bank import add_story, count_ready, pop_story, topics_in_bank

logger = logging.getLogger(__name__)

LOW_WATERMARK = 30
BATCH = 20
SERIES = ("simple", "game")


def generate_one(series: str) -> Any:
    """One new validated script straight from Gemini. Raises GeminiUnavailable if it cannot be produced."""
    avoid = topics_in_bank(series) + get_recently_used_topics_safe()
    if series == "simple":
        from services.story_generator import generate_story_live
        return generate_story_live(avoid_topics=avoid)
    from services.content_generator import generate_motion_story
    return generate_motion_story(3, series="game", live_only=True, avoid_topics=avoid)


def refill(series: str, count: int = BATCH) -> int:
    """Generates up to `count` new scripts. Stops early if Gemini cannot produce more. Returns how many were added."""
    added = 0
    while added < count:
        try:
            story = generate_one(series)
        except GeminiUnavailable as exc:
            logger.warning("Could not generate a new %s script (%s). Added %d of %d.", series, str(exc)[:120], added, count)
            break
        add_story(series, story)
        added += 1
        logger.info("Banked new %s script %d/%d: %s (%d ready)", series, added, count, story.topic, count_ready(series))
    return added


def take_or_refill(series: str) -> Optional[Any]:
    """Pops a banked script. If the bank is empty, stops to generate a batch first."""
    story = pop_story(series)
    if story is not None:
        return story
    logger.warning("The %s bank is EMPTY. Pausing production to generate %d new scripts...", series, BATCH)
    refill(series, BATCH)
    return pop_story(series)


def replenish_after_use(series: str) -> int:
    """Called after a video: if fewer than LOW_WATERMARK scripts are ready, generates a batch of BATCH (best effort)."""
    try:
        ready = count_ready(series)
        if ready >= LOW_WATERMARK:
            logger.info("%s bank has %d ready (watermark %d); no new scripts needed.", series, ready, LOW_WATERMARK)
            return 0
        logger.warning("%s bank is down to %d (< %d). Generating %d new scripts...", series, ready, LOW_WATERMARK, BATCH)
        return refill(series, BATCH)
    except Exception as exc:  # never break a finished video because of the refill
        logger.warning("Bank replenishment failed: %s", str(exc)[:150])
        return 0
