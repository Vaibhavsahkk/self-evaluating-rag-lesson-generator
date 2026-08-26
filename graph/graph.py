"""
LangGraph wiring — connects nodes and routing into the executable pipeline.

Flow:
  load_memory → generate_lesson → evaluate_lesson → [route]
                                                       │
                                         PASS ────────→ finalize → write_memory → END
                                                       │
                                         FAIL ────────→ log_failure → [route]
                                                                        │
                                                   retry ──────────────→ generate_lesson
                                                                        │
                                                   exhausted ──────────→ finalize → write_memory → END
"""

from langgraph.graph import StateGraph, END

from graph.state import GraphState
from graph.nodes import (
    load_memory,
    generate_lesson,
    evaluate_lesson,
    log_failure,
    finalize,
    write_memory_node,
)
from graph.routing import (
    route_after_evaluation,
    route_after_failure,
)


def build_graph() -> StateGraph:
    """Build and compile the lesson content generator graph."""

    graph = StateGraph(GraphState)

    # ── Add nodes ──
    graph.add_node("load_memory", load_memory)
    graph.add_node("generate_lesson", generate_lesson)
    graph.add_node("evaluate_lesson", evaluate_lesson)
    graph.add_node("log_failure", log_failure)
    graph.add_node("finalize", finalize)
    graph.add_node("write_memory", write_memory_node)

    # ── Set entry point ──
    graph.set_entry_point("load_memory")

    # ── Fixed edges ──
    graph.add_edge("load_memory", "generate_lesson")
    graph.add_edge("generate_lesson", "evaluate_lesson")
    graph.add_edge("finalize", "write_memory")
    graph.add_edge("write_memory", END)

    # ── Conditional edges ──
    graph.add_conditional_edges(
        "evaluate_lesson",
        route_after_evaluation,
        {
            "finalize": "finalize",
            "log_failure": "log_failure",
        },
    )

    graph.add_conditional_edges(
        "log_failure",
        route_after_failure,
        {
            "generate_lesson": "generate_lesson",
            "finalize": "finalize",
        },
    )

    return graph.compile()
