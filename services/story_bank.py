"""Bank of pre-generated, validated scripts stored in data/history.db.

Refilled off-peak by scripts/refill_story_bank.py; consumed when Gemini is unavailable at publish time.
Series: 'simple' -> StoryProject, 'minecraft' -> McStory.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from core.schemas import McStory, StoryProject
from services.history import get_db_connection, init_db

logger = logging.getLogger(__name__)

MODELS = {"simple": StoryProject, "minecraft": McStory}


def _ensure() -> None:
    init_db()
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS story_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                series TEXT NOT NULL,
                topic TEXT NOT NULL,
                payload TEXT NOT NULL,
                model TEXT,
                created_at TEXT NOT NULL,
                used_at TEXT
            )
            """
        )


def add_story(series: str, story: Any, model: Optional[str] = None) -> int:
    _ensure()
    with get_db_connection() as conn:
        cur = conn.execute(
            "INSERT INTO story_bank (series, topic, payload, model, created_at) VALUES (?, ?, ?, ?, ?)",
            (series, story.topic, story.model_dump_json(), model, datetime.now(timezone.utc).isoformat()),
        )
        return int(cur.lastrowid)


def topics_in_bank(series: str) -> list:
    """Topics already banked or used, so refills do not repeat themselves."""
    _ensure()
    with get_db_connection() as conn:
        return [r["topic"] for r in conn.execute("SELECT topic FROM story_bank WHERE series = ?", (series,))]


def count_ready(series: str) -> int:
    _ensure()
    with get_db_connection() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM story_bank WHERE series = ? AND used_at IS NULL", (series,)).fetchone()[0])


def pop_story(series: str, accept=None) -> Optional[Any]:
    """Returns the oldest unused banked story (and marks it used), or None.
    With `accept(story) -> bool`, stories it rejects are skipped and stay in the bank (e.g. a game blacklisted for now)."""
    _ensure()
    cls = MODELS[series]
    with get_db_connection() as conn:
        rows = conn.execute("SELECT id, payload FROM story_bank WHERE series = ? AND used_at IS NULL ORDER BY id", (series,)).fetchall()
        for row in rows:
            story = cls.model_validate_json(row["payload"])
            if accept is not None and not accept(story):
                continue
            conn.execute("UPDATE story_bank SET used_at = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), row["id"]))
            logger.info("Using banked %s story #%d: '%s'", series, row["id"], story.topic)
            return story
    return None
