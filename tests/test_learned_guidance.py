"""
Tests for the cross-run learning store — proves self-evolution
isn't just decoration.

Key test: a seeded failure history produces the expected guidance
string, and that string would appear in the next generator prompt.
"""

import os
import tempfile
import pytest

from memory.models import init_db
from memory.learning_store import (
    get_learned_guidance,
    write_run_result,
    generate_run_id,
    GUIDANCE_MAP,
)
from config import LEARNED_GUIDANCE_THRESHOLD


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


class TestLearnedGuidance:
    """Tests that cross-run learning actually wires guidance into prompts."""

    def test_no_history_returns_empty(self, temp_db):
        """Fresh install with no history should return no guidance."""
        guidance = get_learned_guidance(db_path=temp_db)
        assert guidance == []

    def test_insufficient_failures_no_guidance(self, temp_db):
        """Failures below threshold should not trigger guidance."""
        # Write 1 run with 1 failure — below threshold of 3
        run_id = generate_run_id()
        write_run_result(
            run_id=run_id,
            topic="Test Topic",
            final_status="passed",
            total_attempts=2,
            failures=[{
                "attempt_number": 1,
                "checkpoint_name": "no_unexplained_jargon",
                "reason": "test failure",
            }],
            db_path=temp_db,
        )
        guidance = get_learned_guidance(db_path=temp_db)
        assert guidance == []

    def test_threshold_failures_triggers_guidance(self, temp_db):
        """
        Failures at or above threshold should produce the
        corresponding guidance string from GUIDANCE_MAP.
        """
        # Write enough runs to exceed threshold
        for i in range(LEARNED_GUIDANCE_THRESHOLD):
            run_id = generate_run_id()
            write_run_result(
                run_id=run_id,
                topic="Test Topic",
                final_status="failed_quality_bar",
                total_attempts=3,
                failures=[{
                    "attempt_number": 1,
                    "checkpoint_name": "no_unexplained_jargon",
                    "reason": f"test failure {i}",
                }],
                db_path=temp_db,
            )

        guidance = get_learned_guidance(db_path=temp_db)
        assert len(guidance) >= 1
        assert any(GUIDANCE_MAP["no_unexplained_jargon"] in item for item in guidance)

    def test_multiple_checkpoints_can_trigger(self, temp_db):
        """Different checkpoints can each independently trigger guidance."""
        for i in range(LEARNED_GUIDANCE_THRESHOLD + 1):
            run_id = generate_run_id()
            write_run_result(
                run_id=run_id,
                topic="Test Topic",
                final_status="failed_quality_bar",
                total_attempts=3,
                failures=[
                    {
                        "attempt_number": 1,
                        "checkpoint_name": "no_unexplained_jargon",
                        "reason": "jargon issue",
                    },
                    {
                        "attempt_number": 1,
                        "checkpoint_name": "beginner_language",
                        "reason": "too complex",
                    },
                ],
                db_path=temp_db,
            )

        guidance = get_learned_guidance(db_path=temp_db)
        assert len(guidance) >= 2
        assert any(GUIDANCE_MAP["no_unexplained_jargon"] in item for item in guidance)
        assert any(GUIDANCE_MAP["beginner_language"] in item for item in guidance)


class TestMemoryPersistence:
    """Tests that data persists across separate connections."""

    def test_write_then_read_persists(self, temp_db):
        """Data written in one call should be readable in another."""
        run_id = generate_run_id()

        # Write
        write_run_result(
            run_id=run_id,
            topic="Persistence Test",
            final_status="passed",
            total_attempts=1,
            failures=[],
            db_path=temp_db,
        )

        # Read in a new connection
        conn = init_db(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["topic"] == "Persistence Test"
        assert row["final_status"] == "passed"

    def test_failures_written_correctly(self, temp_db):
        """Each failed checkpoint should produce a row in failures table."""
        run_id = generate_run_id()

        write_run_result(
            run_id=run_id,
            topic="Failure Test",
            final_status="failed_quality_bar",
            total_attempts=3,
            failures=[
                {"attempt_number": 1, "checkpoint_name": "coherent_flow", "reason": "r1"},
                {"attempt_number": 2, "checkpoint_name": "covers_key_points", "reason": "r2"},
            ],
            db_path=temp_db,
        )

        conn = init_db(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM failures WHERE run_id = ?", (run_id,))
        count = cursor.fetchone()["cnt"]
        conn.close()

        assert count == 2
