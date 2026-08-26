"""
Pure Python merge logic for evaluation checkpoints.

This module is decoupled from any LLM SDK or external network calls.
It solely handles the boolean logic of merging deterministic heuristic
gates with LLM-based pedagogical judgments.
"""

from evaluation.rubric import (
    CheckpointResult,
    LLMEvaluationResponse,
)


def _merge_checkpoints(
    llm_response: LLMEvaluationResponse,
    readability,
    heuristic_jargon,
    heuristic_grounding,
) -> list[CheckpointResult]:
    """Merge LLM results with programmatic gates."""
    merged = []

    for cp in llm_response.checkpoints:
        if cp.name == "beginner_language_pedagogical":
            both_pass = readability.passed and cp.passed
            if not readability.passed and cp.passed:
                reason = f"Pedagogical check OK, but readability gate failed: {readability.detail}"
            elif readability.passed and not cp.passed:
                reason = f"Readability gate OK, but pedagogical check failed: {cp.reason}"
            elif not readability.passed and not cp.passed:
                reason = f"Both failed — readability: {readability.detail}; pedagogical: {cp.reason}"
            else:
                reason = f"Passed — readability score OK and pedagogical quality confirmed: {cp.reason}"

            merged.append(CheckpointResult(
                name="beginner_language",
                passed=both_pass,
                reason=reason,
            ))

        elif cp.name == "no_unexplained_jargon":
            both_pass = heuristic_jargon.passed and cp.passed
            if not heuristic_jargon.passed and cp.passed:
                reason = f"LLM check OK, but heuristic jargon check failed: {heuristic_jargon.detail}"
            elif heuristic_jargon.passed and not cp.passed:
                reason = f"Heuristic check OK, but LLM flagged unexplained jargon: {cp.reason}"
            elif not heuristic_jargon.passed and not cp.passed:
                reason = f"Both failed — heuristic: {heuristic_jargon.detail}; LLM: {cp.reason}"
            else:
                reason = f"Passed — both heuristic pattern check and LLM jargon check passed: {cp.reason}"

            merged.append(CheckpointResult(
                name="no_unexplained_jargon",
                passed=both_pass,
                reason=reason,
            ))

        elif cp.name == "accurate_grounded":
            both_pass = heuristic_grounding.passed and cp.passed
            if not heuristic_grounding.passed and cp.passed:
                reason = f"LLM check OK, but heuristic absolute claims check failed: {heuristic_grounding.detail}"
            elif heuristic_grounding.passed and not cp.passed:
                reason = f"Heuristic check OK, but LLM flagged grounding issue: {cp.reason}"
            elif not heuristic_grounding.passed and not cp.passed:
                reason = f"Both failed — heuristic: {heuristic_grounding.detail}; LLM: {cp.reason}"
            else:
                reason = f"Passed — no absolute claims found and LLM confirmed grounding: {cp.reason}"

            merged.append(CheckpointResult(
                name="accurate_grounded",
                passed=both_pass,
                reason=reason,
            ))

        else:
            merged.append(CheckpointResult(
                name=cp.name,
                passed=cp.passed,
                reason=cp.reason,
            ))

    return merged
