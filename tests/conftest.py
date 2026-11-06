import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, ROOT.as_posix())


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Point the history database at a throwaway file so tests never touch data/history.db."""
    from services import history

    monkeypatch.setattr(history, "DEFAULT_DB_PATH", tmp_path / "history.db")
    return tmp_path / "history.db"
