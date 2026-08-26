"""
Tests for the retry/regeneration logic.

These test the state transitions and routing functions
without making actual LLM calls.
"""

import pytest
from graph.routing import route_after_evaluation, route_after_failure
from evaluation.rubric import EvaluationResult, CheckpointResult
from config import MAX_RETRIES


def _make_eval_result(overall_pass: bool) -> dict:
    """Helper to create a minimal EvaluationResult dict."""
    checkpoints = [
        CheckpointResult(name="accurate_grounded", passed=overall_pass, reason="test"),
        CheckpointResult(name="beginner_language", passed=overall_pass, reason="test"),
        CheckpointResult(name="teaches_by_example", passed=overall_pass, reason="test"),
        CheckpointResult(name="no_unexplained_jargon", passed=overall_pass, reason="test"),
        CheckpointResult(name="covers_key_points", passed=overall_pass, reason="test"),
        CheckpointResult(name="coherent_flow", passed=overall_pass, reason="test"),
    ]
    result = EvaluationResult(
        overall_pass=overall_pass,
        checkpoints=checkpoints,
        retry_instructions=[] if overall_pass else ["Fix something."],
    )
    return result.model_dump()


class TestRouteAfterEvaluation:
    def test_pass_routes_to_finalize(self):
        state = {"evaluation_result": _make_eval_result(True)}
        assert route_after_evaluation(state) == "finalize"

    def test_fail_routes_to_log_failure(self):
        state = {"evaluation_result": _make_eval_result(False)}
        assert route_after_evaluation(state) == "log_failure"


class TestRouteAfterFailure:
    def test_retry_available_routes_to_generate(self):
        state = {"retry_count": 0}
        assert route_after_failure(state) == "generate_lesson"

    def test_retry_at_one_routes_to_generate(self):
        state = {"retry_count": 1}
        assert route_after_failure(state) == "generate_lesson"

    def test_max_retries_routes_to_finalize(self):
        state = {"retry_count": MAX_RETRIES}
        assert route_after_failure(state) == "finalize"

    def test_over_max_routes_to_finalize(self):
        state = {"retry_count": MAX_RETRIES + 1}
        assert route_after_failure(state) == "finalize"

class TestRetryCount:
    """Verify retry_count semantics match the implementation plan."""

    def test_max_retries_means_n_plus_one_total_attempts(self):
        """
        MAX_RETRIES=2 means 3 total attempts: initial + 2 retries.
        """
        assert MAX_RETRIES == 2

        # After 2 failures, we have consumed 2 retries. Stop.
        state_after_two_failures = {"retry_count": 2}
        assert route_after_failure(state_after_two_failures) == "finalize"

        # After 1 failure, we have consumed 1 retry. Keep going.
        state_after_one_failure = {"retry_count": 1}
        assert route_after_failure(state_after_one_failure) == "generate_lesson"
