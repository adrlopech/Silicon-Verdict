"""Database storage and query service for Silicon Verdict short production history.

Stores historical production telemetry in SQLite (data/history.db) tracking:
- weekday_index (INTEGER: 0=Lunes to 4=Viernes)
- theme_key (TEXT: 'theme_a' or 'theme_b')
- game_title (TEXT: benchmark title)
- voice_id_used (TEXT: ElevenLabs voice ID)
- topic, title, video_id, created_at
"""
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from config.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = settings.BASE_DIR / "data" / "history.db"


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Returns a connection to the SQLite history database, creating directories if needed."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> Path:
    """Initializes the database schema if it doesn't already exist."""
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
                created_at TEXT NOT NULL
            )
        """)
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
    db_path: Optional[Path] = None,
) -> int:
    """Inserts a completed short execution into the history database."""
    init_db(db_path)
    now_iso = created_at or datetime.now(timezone.utc).isoformat()
    with get_db_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO shorts_history (
                weekday_index, theme_key, game_title, voice_id_used, topic, title, video_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_last_used_voice(db_path: Optional[Path] = None) -> Optional[str]:
    """Queries the most recently used ElevenLabs voice ID from history."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT voice_id_used FROM shorts_history ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row:
            return str(row["voice_id_used"])
    return None


def get_last_theme_for_weekday(weekday_index: int, db_path: Optional[Path] = None) -> Optional[str]:
    """Queries the last theme_key ('theme_a' or 'theme_b') used for a specific weekday."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT theme_key FROM shorts_history
            WHERE weekday_index = ?
            ORDER BY id DESC LIMIT 1
            """,
            (int(weekday_index),),
        ).fetchone()
        if row:
            return str(row["theme_key"])
    return None


def get_recently_used_games(
    days: int = 14,
    db_path: Optional[Path] = None,
    ref_date: Optional[datetime] = None,
) -> List[str]:
    """Retrieves all distinct game titles used within the specified time window (default: 14 days).

    Args:
        days: Window in days to look back.
        db_path: Optional custom path to SQLite database.
        ref_date: Optional reference datetime for calculation (defaults to current UTC time).
    """
    init_db(db_path)
    base_dt = ref_date or datetime.now(timezone.utc)
    cutoff = (base_dt - timedelta(days=days)).isoformat()

    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT game_title FROM shorts_history
            WHERE created_at >= ?
            ORDER BY created_at DESC
            """,
            (cutoff,),
        ).fetchall()
        return [str(r["game_title"]) for r in rows]


def get_all_history(limit: int = 50, db_path: Optional[Path] = None) -> List[dict]:
    """Fetches the latest recorded short entries."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM shorts_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
