"""
Pydantic v2 models for evaluation results and rejection log entries.

These are pure data contracts — no LLM logic lives here.
overall_pass is computed in Python, never trusted as a raw LLM field.
Checkpoint names are enforced via Literal type — no free text allowed.
"""

from pydantic import BaseModel, Field, model_validator
from typing import Literal


# ── Checkpoint name types ─────────────────────────────────────────────
# LLM checkpoint names (what the evaluator model returns)
LLMCheckpointName = Literal[
    "accurate_grounded",
    "beginner_language_pedagogical",
    "teaches_by_example",
    "no_unexplained_jargon",
    "covers_key_points",
    "coherent_flow",
]

LLM_CHECKPOINT_NAMES: set[str] = {
    "accurate_grounded",
    "beginner_language_pedagogical",
    "teaches_by_example",
    "no_unexplained_jargon",
    "covers_key_points",
    "coherent_flow",
}

# Final checkpoint names (after Python merges beginner_language)
FinalCheckpointName = Literal[
    "accurate_grounded",
    "beginner_language",
    "teaches_by_example",
    "no_unexplained_jargon",
    "covers_key_points",
    "coherent_flow",
]

FINAL_CHECKPOINT_NAMES: set[str] = {
    "accurate_grounded",
    "beginner_language",
    "teaches_by_example",
    "no_unexplained_jargon",
    "covers_key_points",
    "coherent_flow",
}


# ── LLM-side models ──────────────────────────────────────────────────

class LLMCheckpointResult(BaseModel):
    """A single checkpoint result as returned by the evaluator LLM."""
    name: LLMCheckpointName = Field(
        description="One of the 6 LLM checkpoint names (Literal-enforced)"
    )
    passed: bool
    reason: str = Field(
        min_length=1,
        description="One-sentence explanation — required and non-empty even when passed=True"
    )


class LLMEvaluationResponse(BaseModel):
    """
    Schema the LLM is asked to return.
    Validated to contain exactly 6 unique checkpoints.
    Does NOT include overall_pass — that is computed in Python.
    """
    checkpoints: list[LLMCheckpointResult]
    retry_instructions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_checkpoint_set(self) -> "LLMEvaluationResponse":
        """Enforce exactly 6 unique, expected checkpoint names."""
        names = [c.name for c in self.checkpoints]

        if len(names) != 6:
            raise ValueError(
                f"Expected exactly 6 checkpoints, got {len(names)}: {names}"
            )

        name_set = set(names)
        if len(name_set) != 6:
            dupes = [n for n in names if names.count(n) > 1]
            raise ValueError(
                f"Duplicate checkpoint names found: {dupes}"
            )

        if name_set != LLM_CHECKPOINT_NAMES:
            missing = LLM_CHECKPOINT_NAMES - name_set
            unknown = name_set - LLM_CHECKPOINT_NAMES
            raise ValueError(
                f"Checkpoint set mismatch. "
                f"Missing: {missing or 'none'}. "
                f"Unknown: {unknown or 'none'}."
            )

        return self


# ── Python-side models (after merge) ─────────────────────────────────

class CheckpointResult(BaseModel):
    """A single checkpoint result after Python-side merging."""
    name: FinalCheckpointName = Field(
        description="One of the 6 final checkpoint names (Literal-enforced)"
    )
    passed: bool
    reason: str = Field(
        min_length=1,
        description="One-sentence explanation — required and non-empty"
    )


class EvaluationResult(BaseModel):
    """
    Full evaluation result with Python-computed overall_pass.
    Created from LLMEvaluationResponse after merging beginner_language.
    """
    overall_pass: bool = Field(
        description="True only if ALL 6 final checkpoints pass — computed in Python"
    )
    checkpoints: list[CheckpointResult]
    retry_instructions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_final_checkpoint_set(self) -> "EvaluationResult":
        """Enforce exactly 6 unique final checkpoint names."""
        names = [c.name for c in self.checkpoints]
        name_set = set(names)

        if len(names) != 6 or name_set != FINAL_CHECKPOINT_NAMES:
            raise ValueError(
                f"Final checkpoint set invalid. "
                f"Got: {names}. Expected: {FINAL_CHECKPOINT_NAMES}"
            )
        return self

    @property
    def failed_checkpoints(self) -> list[CheckpointResult]:
        return [c for c in self.checkpoints if not c.passed]


# ── Rejection log models ─────────────────────────────────────────────

class RejectionEntry(BaseModel):
    """One entry in the rejection log — represents a single attempt."""
    attempt_number: int
    timestamp: str
    overall_pass: bool
    failed_checkpoints: list[dict] = Field(default_factory=list)
    retry_instructions: list[str] = Field(default_factory=list)
    instruction_given_for_next_attempt: str | None = Field(
        default=None,
        description=(
            "Records the retry instruction passed to the generator for the next "
            "attempt. The next evaluation determines if this instruction resolved the failure."
        ),
    )


class RejectionLog(BaseModel):
    """Full rejection log for one run."""
    run_id: str
    topic: str
    attempts: list[RejectionEntry] = Field(default_factory=list)
    final_status: Literal["passed", "failed_quality_bar"] = "passed"
