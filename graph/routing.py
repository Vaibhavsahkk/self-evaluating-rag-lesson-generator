"""
Pure routing logic for the state machine graph.
Extracted here so tests can import routing without loading LLM SDKs.
"""

from graph.state import GraphState
from config import MAX_RETRIES


def route_after_evaluation(state: GraphState) -> str:
    """
    Route based on evaluation outcome.
    If evaluation passed, go to finalize.
    If evaluation failed, go to log_failure (which leads to retry checks).
    """
    eval_result = state.get("evaluation_result") or {}
    if eval_result.get("overall_pass", False):
        return "finalize"
    return "log_failure"


def route_after_failure(state: GraphState) -> str:
    """
    Route based on retry count.
    If under max retries, go back to generate_lesson.
    If max retries reached, go to finalize (with failed status).
    """
    if state.get("retry_count", 0) < MAX_RETRIES:
        return "generate_lesson"
    return "finalize"
