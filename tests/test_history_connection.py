import sqlite3

import pytest

from services.history import get_db_connection


def test_connection_is_closed_after_with_block(tmp_db):
    with get_db_connection() as conn:
        conn.execute("CREATE TABLE t (x)")
        conn.execute("INSERT INTO t VALUES (1)")
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_commit_happens_on_exit(tmp_db):
    with get_db_connection() as conn:
        conn.execute("CREATE TABLE t (x)")
        conn.execute("INSERT INTO t VALUES (7)")
    with get_db_connection() as conn:
        assert conn.execute("SELECT x FROM t").fetchone()[0] == 7


def test_rollback_on_error(tmp_db):
    with get_db_connection() as conn:
        conn.execute("CREATE TABLE t (x)")
    with pytest.raises(RuntimeError):
        with get_db_connection() as conn:
            conn.execute("INSERT INTO t VALUES (1)")
            raise RuntimeError
    with get_db_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0
