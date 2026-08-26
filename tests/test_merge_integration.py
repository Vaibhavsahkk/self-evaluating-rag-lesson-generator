"""
Integration-style tests for the evaluator merge logic.

Tests the _merge_checkpoints function directly with fake LLM responses
and fake deterministic gate results. No real API calls.

This covers the critical gap: proving the merge logic produces correct
final EvaluationResult objects for all pass/fail gate combinations.
"""

import pytest
from dataclasses import dataclass
from evaluation.merge import _merge_checkpoints
from evaluation.rubric import (
    LLMEvaluationResponse,
    LLMCheckpointResult,
    CheckpointResult,
    EvaluationResult,
    FINAL_CHECKPOINT_NAMES,
)


@dataclass
class FakeReadability:
    passed: bool
    detail: str = "test detail"
    flesch_score: float = 70.0
    avg_sentence_length: float = 14.0
    long_sentence_rate: float = 0.1


@dataclass
class FakeJargon:
    passed: bool
    missing_definitions: list = None
    detail: str = "test detail"

    def __post_init__(self):
        if self.missing_definitions is None:
            self.missing_definitions = []


@dataclass
class FakeGrounding:
    passed: bool
    detail: str = "test detail"


def _make_llm_response(all_pass=True, fail_checkpoints=None):
    """Build a valid LLMEvaluationResponse with specified failures."""
    fail_checkpoints = fail_checkpoints or []
    checkpoints = [
        LLMCheckpointResult(
            name="accurate_grounded",
            passed="accurate_grounded" not in fail_checkpoints,
            reason="test reason",
        ),
        LLMCheckpointResult(
            name="beginner_language_pedagogical",
            passed="beginner_language_pedagogical" not in fail_checkpoints,
            reason="test reason",
        ),
        LLMCheckpointResult(
            name="teaches_by_example",
            passed="teaches_by_example" not in fail_checkpoints,
            reason="test reason",
        ),
        LLMCheckpointResult(
            name="no_unexplained_jargon",
            passed="no_unexplained_jargon" not in fail_checkpoints,
            reason="test reason",
        ),
        LLMCheckpointResult(
            name="covers_key_points",
            passed="covers_key_points" not in fail_checkpoints,
            reason="test reason",
        ),
        LLMCheckpointResult(
            name="coherent_flow",
            passed="coherent_flow" not in fail_checkpoints,
            reason="test reason",
        ),
    ]
    return LLMEvaluationResponse(
        checkpoints=checkpoints,
        retry_instructions=["Fix it."] if fail_checkpoints else [],
    )


class TestMergeAllPass:
    """All gates pass → overall_pass = True"""

    def test_all_pass_produces_6_final_checkpoints(self):
        llm = _make_llm_response(all_pass=True)
        readability = FakeReadability(passed=True)
        jargon = FakeJargon(passed=True)
        grounding = FakeGrounding(passed=True)

        merged = _merge_checkpoints(llm, readability, jargon, grounding)

        assert len(merged) == 6
        names = {c.name for c in merged}
        assert names == FINAL_CHECKPOINT_NAMES
        assert all(c.passed for c in merged)

    def test_all_pass_builds_valid_evaluation_result(self):
        llm = _make_llm_response(all_pass=True)
        readability = FakeReadability(passed=True)
        jargon = FakeJargon(passed=True)
        grounding = FakeGrounding(passed=True)

        merged = _merge_checkpoints(llm, readability, jargon, grounding)
        result = EvaluationResult(
            overall_pass=all(c.passed for c in merged),
            checkpoints=merged,
            retry_instructions=[],
        )

        assert result.overall_pass is True
        assert len(result.failed_checkpoints) == 0


class TestMergeBeginnerLanguage:
    """beginner_language = readability AND pedagogical"""

    def test_readability_fail_overrides_pedagogical_pass(self):
        llm = _make_llm_response(all_pass=True)
        readability = FakeReadability(passed=False, detail="Flesch too low")
        jargon = FakeJargon(passed=True)
        grounding = FakeGrounding(passed=True)

        merged = _merge_checkpoints(llm, readability, jargon, grounding)
        bl = next(c for c in merged if c.name == "beginner_language")

        assert bl.passed is False
        assert "readability" in bl.reason.lower()

    def test_pedagogical_fail_overrides_readability_pass(self):
        llm = _make_llm_response(fail_checkpoints=["beginner_language_pedagogical"])
        readability = FakeReadability(passed=True)
        jargon = FakeJargon(passed=True)
        grounding = FakeGrounding(passed=True)

        merged = _merge_checkpoints(llm, readability, jargon, grounding)
        bl = next(c for c in merged if c.name == "beginner_language")

        assert bl.passed is False
        assert "pedagogical" in bl.reason.lower()

    def test_both_fail_records_both(self):
        llm = _make_llm_response(fail_checkpoints=["beginner_language_pedagogical"])
        readability = FakeReadability(passed=False, detail="Flesch too low")
        jargon = FakeJargon(passed=True)
        grounding = FakeGrounding(passed=True)

        merged = _merge_checkpoints(llm, readability, jargon, grounding)
        bl = next(c for c in merged if c.name == "beginner_language")

        assert bl.passed is False
        assert "readability" in bl.reason.lower()
        assert "pedagogical" in bl.reason.lower()


class TestMergeJargon:
    """no_unexplained_jargon = heuristic AND LLM"""

    def test_heuristic_fail_overrides_llm_pass(self):
        llm = _make_llm_response(all_pass=True)
        readability = FakeReadability(passed=True)
        jargon = FakeJargon(passed=False, detail="embedding not defined")
        grounding = FakeGrounding(passed=True)

        merged = _merge_checkpoints(llm, readability, jargon, grounding)
        nj = next(c for c in merged if c.name == "no_unexplained_jargon")

        assert nj.passed is False
        assert "heuristic" in nj.reason.lower()

    def test_llm_fail_overrides_heuristic_pass(self):
        llm = _make_llm_response(fail_checkpoints=["no_unexplained_jargon"])
        readability = FakeReadability(passed=True)
        jargon = FakeJargon(passed=True)
        grounding = FakeGrounding(passed=True)

        merged = _merge_checkpoints(llm, readability, jargon, grounding)
        nj = next(c for c in merged if c.name == "no_unexplained_jargon")

        assert nj.passed is False
        assert "llm" in nj.reason.lower()

    def test_both_fail_records_both(self):
        llm = _make_llm_response(fail_checkpoints=["no_unexplained_jargon"])
        readability = FakeReadability(passed=True)
        jargon = FakeJargon(passed=False, detail="embedding not defined")
        grounding = FakeGrounding(passed=True)

        merged = _merge_checkpoints(llm, readability, jargon, grounding)
        nj = next(c for c in merged if c.name == "no_unexplained_jargon")

        assert nj.passed is False
        assert "heuristic" in nj.reason.lower()
        assert "llm" in nj.reason.lower()


class TestMergeOverallPass:
    """overall_pass computed in Python from merged checkpoints"""

    def test_one_checkpoint_fail_means_overall_fail(self):
        llm = _make_llm_response(fail_checkpoints=["accurate_grounded"])
        readability = FakeReadability(passed=True)
        jargon = FakeJargon(passed=True)
        grounding = FakeGrounding(passed=True)

        merged = _merge_checkpoints(llm, readability, jargon, grounding)
        overall = all(c.passed for c in merged)

        assert overall is False

    def test_deterministic_gate_fail_means_overall_fail(self):
        """Even if LLM says all pass, a failed readability gate → overall fail."""
        llm = _make_llm_response(all_pass=True)
        readability = FakeReadability(passed=False)
        jargon = FakeJargon(passed=True)
        grounding = FakeGrounding(passed=True)

        merged = _merge_checkpoints(llm, readability, jargon, grounding)
        overall = all(c.passed for c in merged)

        assert overall is False


class TestMergeGrounding:
    """accurate_grounded = heuristic AND LLM"""

    def test_heuristic_fail_overrides_llm_pass(self):
        llm = _make_llm_response(all_pass=True)
        readability = FakeReadability(passed=True)
        jargon = FakeJargon(passed=True)
        grounding = FakeGrounding(passed=False, detail="stops hallucinations")

        merged = _merge_checkpoints(llm, readability, jargon, grounding)
        ag = next(c for c in merged if c.name == "accurate_grounded")

        assert ag.passed is False
        assert "heuristic" in ag.reason.lower()

    def test_llm_fail_overrides_heuristic_pass(self):
        llm = _make_llm_response(fail_checkpoints=["accurate_grounded"])
        readability = FakeReadability(passed=True)
        jargon = FakeJargon(passed=True)
        grounding = FakeGrounding(passed=True)

        merged = _merge_checkpoints(llm, readability, jargon, grounding)
        ag = next(c for c in merged if c.name == "accurate_grounded")

        assert ag.passed is False
        assert "llm" in ag.reason.lower()

    def test_both_fail_records_both(self):
        llm = _make_llm_response(fail_checkpoints=["accurate_grounded"])
        readability = FakeReadability(passed=True)
        jargon = FakeJargon(passed=True)
        grounding = FakeGrounding(passed=False, detail="stops hallucinations")

        merged = _merge_checkpoints(llm, readability, jargon, grounding)
        ag = next(c for c in merged if c.name == "accurate_grounded")

        assert ag.passed is False
        assert "heuristic" in ag.reason.lower()
        assert "llm" in ag.reason.lower()
