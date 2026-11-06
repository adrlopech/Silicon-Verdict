"""Story bank policy.

- Whenever the bank has fewer than LOW_WATERMARK (30) ready scripts for the Minecraft series,
  a batch of BATCH (20) new scripts is generated.
- After every video, the bank is checked and, if below the watermark, the batch is generated.
- If the bank is empty before a video, production pauses until a batch is generated.
- Scripts already in the bank are never deleted, and the bank may grow above the watermark.
"""
import logging
from typing import Any

from services.gemini_client import GeminiUnavailable
from services.history import get_recently_used_topics_safe
from services.story_bank import add_story, count_ready, topics_in_bank

logger = logging.getLogger(__name__)

LOW_WATERMARK = 30
BATCH = 20
SERIES = ("minecraft",)  # the Motion bank (every Motion format, incl. hardware and simple) is filled with scripts/refill_story_bank.py, never automatically


def generate_one(series: str) -> Any:
    """One new validated script straight from Gemini. Raises GeminiUnavailable if it cannot be produced."""
    avoid = topics_in_bank(series) + get_recently_used_topics_safe()
    if series == "minecraft":
        from services.mc_story_generator import generate_story_live as generate_mc
        return generate_mc(avoid_topics=avoid)
    raise ValueError(f"unknown series {series!r}")


BATCH_CHUNK = 4  # scripts requested per Gemini call: 20 scripts cost ~5 requests of the (tiny) free-tier daily quota instead of 20+


def _generate_chunk(series: str, want: int) -> list:
    avoid = topics_in_bank(series) + get_recently_used_topics_safe()
    if series == "minecraft" and want > 0:
        from services.mc_story_generator import generate_stories_batch as batch
        try:
            return batch(want, avoid)
        except GeminiUnavailable as exc:
            if want == 1 or "too large" in str(exc) or "per-minute" in str(exc):  # a smaller provider cannot take a batch: one script per request
                if want == 1:
                    raise
                logger.info("Batch not possible right now (%s); asking for one script at a time.", str(exc)[:100])
                return batch(1, avoid)
            raise
    return [generate_one(series)]


def refill(series: str, count: int = BATCH) -> int:
    """Generates up to `count` new scripts, several per Gemini request. Stops as soon as Gemini cannot produce more
    (quota exhausted / saturated: retrying would only waste time). Returns how many were added."""
    added = 0
    while added < count:
        try:
            stories = _generate_chunk(series, min(BATCH_CHUNK, count - added))
        except GeminiUnavailable as exc:
            logger.warning("Could not generate more %s scripts (%s). Added %d of %d.", series, str(exc)[:200], added, count)
            break
        for story in stories[: count - added]:
            add_story(series, story)
            added += 1
            logger.info("Banked new %s script %d/%d: %s (%d ready)", series, added, count, story.topic, count_ready(series))
    return added



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
