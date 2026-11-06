from datetime import datetime, timedelta, timezone

from services import game_registry
from services.history import get_db_connection


def test_recorded_game_is_blacklisted(tmp_db):
    game_registry.record_game("Control", "title")
    assert game_registry.blacklisted_games() == ["Control"]


def test_old_games_are_released(tmp_db):
    game_registry._ensure()
    old = (datetime.now(timezone.utc) - timedelta(days=game_registry.BLACKLIST_DAYS + 1)).isoformat()
    with get_db_connection() as conn:
        conn.execute("INSERT INTO game_registry (game, used_at, video_title) VALUES (?, ?, ?)", ("Old Game", old, ""))
    assert "Old Game" not in game_registry.blacklisted_games()


def test_media_is_consumed_once(tmp_db):
    game_registry.mark_media_used(["a.jpg", "b.jpg"], "Control")
    game_registry.mark_media_used(["a.jpg"], "Control")
    assert game_registry.used_media_keys() == {"a.jpg", "b.jpg"}
