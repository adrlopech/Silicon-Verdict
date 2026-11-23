"""Database access for `data/history.db` and the history of produced videos.

`shorts_history` (SQLite) records every produced video: topic, title, video id, format, look, voice. The series numbers, the look rotation, the "never the same format as last time" rule
and the narrator rule read it. The other tables of the same file belong to their own modules (`story_bank`, `game_registry`, `looks`, `series`).
"""
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = settings.BASE_DIR / "data" / "history.db"


class _ClosingConnection(sqlite3.Connection):
    """sqlite3 only commits/rolls back at the end of a `with` block and leaves the connection open; this one also closes it."""

    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Returns a connection to the SQLite history database, creating directories if needed.
    Use it as `with get_db_connection() as conn:` - the transaction is committed and the connection closed on exit."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30, factory=_ClosingConnection)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> Path:
    """Creates the `shorts_history` table if it does not exist (and adds the columns older databases lack)."""
    path = db_path or DEFAULT_DB_PATH
    with get_db_connection(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shorts_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                weekday_index INTEGER NOT NULL,
                theme_key TEXT NOT NULL,
                game_title TEXT NOT NULL,
                voice_id_used TEXT NOT NULL,
                topic TEXT,
                title TEXT,
                video_id TEXT,
                created_at TEXT NOT NULL,
                category TEXT DEFAULT '',
                tone TEXT DEFAULT 'technical'
            )
        """)
        existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(shorts_history)").fetchall()]
        if "category" not in existing_cols:
            conn.execute("ALTER TABLE shorts_history ADD COLUMN category TEXT DEFAULT ''")
        if "tone" not in existing_cols:
            conn.execute("ALTER TABLE shorts_history ADD COLUMN tone TEXT DEFAULT 'technical'")
        if "preset" not in existing_cols:
            conn.execute("ALTER TABLE shorts_history ADD COLUMN preset TEXT DEFAULT 'liquid_glass'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shorts_history_weekday ON shorts_history(weekday_index)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shorts_history_created_at ON shorts_history(created_at)")
        conn.commit()
    logger.debug("History database initialized at: %s", path)
    return path


def record_short_history(
    weekday_index: int,
    theme_key: str,
    game_title: str,
    voice_id_used: str,
    topic: str = "",
    title: str = "",
    video_id: str = "",
    created_at: Optional[str] = None,
    category: str = "",
    tone: str = "",
    preset: str = "liquid_glass",
    db_path: Optional[Path] = None,
) -> int:
    """Inserts a completed short execution into the history database."""
    init_db(db_path)
    now_iso = created_at or datetime.now(timezone.utc).isoformat()
    with get_db_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO shorts_history (
                weekday_index, theme_key, game_title, voice_id_used, topic, title, video_id, created_at, category, tone, preset
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(weekday_index),
                str(theme_key),
                str(game_title),
                str(voice_id_used),
                str(topic),
                str(title),
                str(video_id),
                str(now_iso),
                str(category),
                str(tone),
                str(preset),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_recently_used_topics_safe(limit: int = 25) -> list:
    """Titles of recently produced videos (best effort; empty list on any error)."""
    try:
        init_db()
        with get_db_connection() as conn:
            rows = conn.execute("SELECT topic FROM shorts_history WHERE topic IS NOT NULL ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        seen = []
        for r in rows:
            if r["topic"] and r["topic"] not in seen:
                seen.append(r["topic"])
        return seen
    except Exception:
        return []
