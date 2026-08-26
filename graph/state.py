"""
LangGraph state definition — the single data structure that flows
through every node in the graph.

"""

from typing import TypedDict, Literal, Annotated
import operator


class GraphState(TypedDict):
    """Complete state flowing through the LangGraph pipeline."""

    # ── Input ──
    topic: str
    learner_profile: str

    # ── Cross-run memory (loaded once at start) ──
    learned_guidance: list[str]

    # ── Generator output ──
    current_lesson: str

    # ── Evaluator output (dict form of EvaluationResult) ──
    evaluation_result: dict | None

    # ── Retry tracking ──
    attempt_count: int
    retry_count: int
    retry_feedback: list[str]
    inject_error_mode: str | None

    # ── Rejection log (append-only via Annotated reducer) ──
    rejection_log: Annotated[list[dict], operator.add]

    # ── Final output ──
    final_status: Literal["pending", "passed", "failed_quality_bar"]
    run_id: str
