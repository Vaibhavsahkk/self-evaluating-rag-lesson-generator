"""
Self-Evaluating Lesson Content Generator — CLI entry point.

Usage:
    python main.py --topic "Introduction to RAG"
    python main.py --topic "Introduction to RAG" --inject-error jargon
"""

import argparse
import sys

# Configure stdout to handle emojis on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from config import LEARNER_PROFILE, REFERENCES_PATH
from graph.graph import build_graph
from memory.learning_store import generate_run_id


def main():
    parser = argparse.ArgumentParser(
        description="Generate a self-evaluating beginner lesson."
    )
    parser.add_argument(
        "--topic",
        type=str,
        default="Introduction to RAG",
        help='Topic for the lesson (default: "Introduction to RAG")',
    )
    parser.add_argument(
        "--inject-error",
        type=str,
        choices=["jargon"],
        default=None,
        help='Inject a deliberate error for demo/testing (e.g. "jargon")',
    )
    args = parser.parse_args()

    # ── Pre-flight check: reference file must exist ──
    try:
        with open(REFERENCES_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            print(f"ERROR: Reference file at {REFERENCES_PATH} is empty.")
            sys.exit(1)
    except FileNotFoundError:
        print(f"ERROR: Reference file not found at {REFERENCES_PATH}")
        print("The accurate_grounded checkpoint cannot run without it.")
        sys.exit(1)

    # ── Build initial state ──
    run_id = generate_run_id()
    initial_state = {
        "topic": args.topic,
        "learner_profile": LEARNER_PROFILE,
        "learned_guidance": [],
        "current_lesson": "",
        "evaluation_result": None,
        "retry_feedback": [],
        "retry_count": 0,
        "attempt_count": 0,
        "inject_error_mode": args.inject_error,
        "rejection_log": [],
        "final_status": "pending",
        "run_id": run_id,
    }

    print(f"\n{'#'*60}")
    print(f"# Self-Evaluating Lesson Content Generator")
    print(f"# Topic: {args.topic}")
    print(f"# Run ID: {run_id}")
    if args.inject_error:
        print(f"# ⚠️  Demo mode: injecting '{args.inject_error}' error")
    print(f"{'#'*60}")

    # ── Build and run the graph ──
    app = build_graph()
    final_state = app.invoke(initial_state)

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"RUN COMPLETE")
    print(f"{'='*60}")
    print(f"  Topic:         {args.topic}")
    print(f"  Final status:  {final_state['final_status']}")
    print(f"  Total attempts: {final_state.get('attempt_count', 0)}")
    print(f"  Run ID:        {run_id}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
