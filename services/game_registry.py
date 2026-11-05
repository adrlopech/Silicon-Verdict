"""Registry of the games already covered (blacklisted for BLACKLIST_DAYS) and of the game media already used (never reused).

Lives in data/history.db next to the rest of the history.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Set

from services.history import get_db_connection, init_db

logger = logging.getLogger(__name__)
BLACKLIST_DAYS = 14


def _ensure() -> None:
    init_db()
    with get_db_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS game_registry (id INTEGER PRIMARY KEY AUTOINCREMENT, game TEXT NOT NULL, used_at TEXT NOT NULL, video_title TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS game_media_used (media_key TEXT PRIMARY KEY, game TEXT, used_at TEXT NOT NULL)")


def record_game(game: str, video_title: str = "") -> None:
    """Marks a game as covered now; it stays blacklisted for BLACKLIST_DAYS."""
    _ensure()
    with get_db_connection() as conn:
        conn.execute("INSERT INTO game_registry (game, used_at, video_title) VALUES (?, ?, ?)", (game, datetime.now(timezone.utc).isoformat(), video_title))
    logger.info("Game registry: '%s' blacklisted for %d days.", game, BLACKLIST_DAYS)


def blacklisted_games(days: int = BLACKLIST_DAYS) -> List[str]:
    """Games covered within the last `days` days (display names as recorded)."""
    _ensure()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with get_db_connection() as conn:
        return sorted({r["game"] for r in conn.execute("SELECT game FROM game_registry WHERE used_at >= ?", (since,))})


def blacklist_status() -> List[dict]:
    """[{game, used_at, free_on}] for the games still blacklisted (diagnostics)."""
    _ensure()
    since = datetime.now(timezone.utc) - timedelta(days=BLACKLIST_DAYS)
    out = {}
    with get_db_connection() as conn:
        for r in conn.execute("SELECT game, used_at FROM game_registry WHERE used_at >= ? ORDER BY used_at", (since.isoformat(),)):
            out[r["game"]] = datetime.fromisoformat(r["used_at"])
    return [{"game": g, "used_at": t.isoformat(), "free_on": (t + timedelta(days=BLACKLIST_DAYS)).date().isoformat()} for g, t in out.items()]


def mark_media_used(keys: Iterable[str], game: str = "") -> None:
    _ensure()
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        conn.executemany("INSERT OR IGNORE INTO game_media_used (media_key, game, used_at) VALUES (?, ?, ?)", [(k, game, now) for k in keys])


def used_media_keys() -> Set[str]:
    _ensure()
    with get_db_connection() as conn:
        return {r["media_key"] for r in conn.execute("SELECT media_key FROM game_media_used")}


if __name__ == "__main__":  # python -m services.game_registry
    rows = blacklist_status()
    print("Blacklisted games (14 days):" if rows else "No game is blacklisted.")
    for r in rows:
        print(f"  {r['game']}: covered {r['used_at'][:10]}, free again on {r['free_on']}")
