"""
Tests for the memory persistence layer.
"""

import os
import tempfile
import pytest

from memory.models import init_db
from memory.learning_store import write_run_result, generate_run_id


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


class TestDatabaseInit:
    def test_creates_tables(self, temp_db):
        conn = init_db(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in cursor.fetchall()]
        conn.close()
        assert "runs" in tables
        assert "failures" in tables

    def test_idempotent_init(self, temp_db):
        """Calling init_db twice should not error or duplicate tables."""
        conn1 = init_db(temp_db)
        conn1.close()
        conn2 = init_db(temp_db)
        cursor = conn2.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM runs")
        assert cursor.fetchone()["cnt"] == 0
        conn2.close()


class TestWriteRunResult:
    def test_writes_run_row(self, temp_db):
        run_id = generate_run_id()
        write_run_result(
            run_id=run_id,
            topic="Test",
            final_status="passed",
            total_attempts=1,
            failures=[],
            db_path=temp_db,
        )
        conn = init_db(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM runs")
        rows = cursor.fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0]["run_id"] == run_id

    def test_writes_failure_rows(self, temp_db):
        run_id = generate_run_id()
        write_run_result(
            run_id=run_id,
            topic="Test",
            final_status="failed_quality_bar",
            total_attempts=3,
            failures=[
                {"attempt_number": 1, "checkpoint_name": "accurate_grounded", "reason": "r1"},
                {"attempt_number": 1, "checkpoint_name": "coherent_flow", "reason": "r2"},
                {"attempt_number": 2, "checkpoint_name": "accurate_grounded", "reason": "r3"},
            ],
            db_path=temp_db,
        )
        conn = init_db(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM failures WHERE run_id = ?", (run_id,))
        rows = cursor.fetchall()
        conn.close()
        assert len(rows) == 3

    def test_run_id_is_unique(self):
        ids = {generate_run_id() for _ in range(100)}
        assert len(ids) == 100
