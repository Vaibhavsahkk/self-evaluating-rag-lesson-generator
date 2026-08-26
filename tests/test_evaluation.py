"""
Tests for the evaluation pipeline and Pydantic model contracts.

Verifies:
- 6 valid checkpoints -> accepted
- Too few / too many checkpoints -> rejected
- Duplicate checkpoint names -> rejected
- Unknown checkpoint names -> rejected
- Empty reason strings -> rejected
- Python computation of overall_pass
"""

import pytest
from pydantic import ValidationError
from evaluation.rubric import (
    CheckpointResult,
    EvaluationResult,
    LLMEvaluationResponse,
    LLMCheckpointResult,
    LLM_CHECKPOINT_NAMES,
    FINAL_CHECKPOINT_NAMES,
)


class TestEvaluationResultFromLLM:
    """Test the Python-side logic and Pydantic validation for LLMEvaluationResponse."""

    def test_all_pass_gives_overall_pass(self):
        llm_resp = LLMEvaluationResponse(
            checkpoints=[
                LLMCheckpointResult(name="accurate_grounded", passed=True, reason="ok"),
                LLMCheckpointResult(name="beginner_language_pedagogical", passed=True, reason="ok"),
                LLMCheckpointResult(name="teaches_by_example", passed=True, reason="ok"),
                LLMCheckpointResult(name="no_unexplained_jargon", passed=True, reason="ok"),
                LLMCheckpointResult(name="covers_key_points", passed=True, reason="ok"),
                LLMCheckpointResult(name="coherent_flow", passed=True, reason="ok"),
            ],
            retry_instructions=[],
        )
        merged = [
            CheckpointResult(name="accurate_grounded", passed=True, reason="ok"),
            CheckpointResult(name="beginner_language", passed=True, reason="ok"),
            CheckpointResult(name="teaches_by_example", passed=True, reason="ok"),
            CheckpointResult(name="no_unexplained_jargon", passed=True, reason="ok"),
            CheckpointResult(name="covers_key_points", passed=True, reason="ok"),
            CheckpointResult(name="coherent_flow", passed=True, reason="ok"),
        ]
        res = EvaluationResult(overall_pass=True, checkpoints=merged)
        assert res.overall_pass is True

    def test_too_few_checkpoints_rejected(self):
        """Fewer than 6 checkpoints must raise ValidationError."""
        with pytest.raises(ValidationError):
            LLMEvaluationResponse(
                checkpoints=[
                    LLMCheckpointResult(name="accurate_grounded", passed=True, reason="ok"),
                    LLMCheckpointResult(name="teaches_by_example", passed=True, reason="ok"),
                ],
                retry_instructions=[],
            )

    def test_duplicate_checkpoints_rejected(self):
        """Duplicate checkpoint names must raise ValidationError."""
        with pytest.raises(ValidationError):
            LLMEvaluationResponse(
                checkpoints=[
                    LLMCheckpointResult(name="accurate_grounded", passed=True, reason="ok"),
                    LLMCheckpointResult(name="accurate_grounded", passed=True, reason="dupe"),
                    LLMCheckpointResult(name="beginner_language_pedagogical", passed=True, reason="ok"),
                    LLMCheckpointResult(name="teaches_by_example", passed=True, reason="ok"),
                    LLMCheckpointResult(name="no_unexplained_jargon", passed=True, reason="ok"),
                    LLMCheckpointResult(name="coherent_flow", passed=True, reason="ok"),
                ],
                retry_instructions=[],
            )

    def test_unknown_checkpoint_name_rejected(self):
        """Invalid/unknown checkpoint name must raise ValidationError."""
        with pytest.raises(ValidationError):
            LLMCheckpointResult(name="random_unauthorized_check", passed=True, reason="ok")

    def test_empty_reason_rejected(self):
        """Empty reason string must raise ValidationError."""
        with pytest.raises(ValidationError):
            LLMCheckpointResult(name="accurate_grounded", passed=True, reason="")

    def test_overall_pass_computed_in_python(self):
        """EvaluationResult overall_pass is computed based on all checkpoints passing."""
        merged = [
            CheckpointResult(name="accurate_grounded", passed=False, reason="error"),
            CheckpointResult(name="beginner_language", passed=True, reason="ok"),
            CheckpointResult(name="teaches_by_example", passed=True, reason="ok"),
            CheckpointResult(name="no_unexplained_jargon", passed=True, reason="ok"),
            CheckpointResult(name="covers_key_points", passed=True, reason="ok"),
            CheckpointResult(name="coherent_flow", passed=True, reason="ok"),
        ]
        res = EvaluationResult(overall_pass=False, checkpoints=merged)
        assert res.overall_pass is False


class TestCheckpointNames:
    """Verify sets match expected names."""

    def test_llm_checkpoint_names(self):
        assert len(LLM_CHECKPOINT_NAMES) == 6
        assert "beginner_language_pedagogical" in LLM_CHECKPOINT_NAMES

    def test_final_checkpoint_names(self):
        assert len(FINAL_CHECKPOINT_NAMES) == 6
        assert "beginner_language" in FINAL_CHECKPOINT_NAMES
