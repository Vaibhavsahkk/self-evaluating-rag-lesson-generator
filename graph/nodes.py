"""
LangGraph node implementations — one function per node in the pipeline.

Each node reads specific fields from GraphState and returns a dict of
fields to update.
"""

import json
import os
import re
import time
from datetime import datetime, timezone

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from config import (
    GOOGLE_API_KEY,
    GENERATOR_MODEL,
    MAX_RETRIES,
    API_RETRY_ATTEMPTS,
    API_RETRY_BACKOFF_BASE,
    LEARNER_PROFILE,
    OUTPUT_DIR,
    LESSON_OUTPUT_PATH,
    REJECTION_LOG_PATH,
)
from evaluation.checkpoints import run_evaluation
from evaluation.rubric import EvaluationResult, RejectionLog, RejectionEntry
from graph.prompts import build_generator_messages
from memory.learning_store import (
    get_learned_guidance,
    write_run_result,
    generate_run_id,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NODE: load_memory
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_memory(state: dict) -> dict:
    """
    Query SQLite for recurring failure patterns from past runs.
    Translates them to guidance strings for the generator prompt.
    """
    guidance = get_learned_guidance()
    if guidance:
        print(f"[MEMORY] Loaded {len(guidance)} learned guidance rule(s) from past runs.")
    else:
        print("[MEMORY] No learned guidance yet (fresh install or insufficient history).")
    return {"learned_guidance": guidance}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NODE: generate_lesson
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_lesson(state: dict) -> dict:
    """
    Call the generator model to produce a lesson.
    Same node handles first attempt and regeneration — the prompt
    differs based on whether retry_feedback is populated.
    """
    attempt_count = state.get("attempt_count", 0) + 1
    retry_count = attempt_count - 1
    
    print(f"\n{'='*60}")
    print(f"[GENERATE] Attempt {attempt_count} — generating lesson on: {state['topic']}")
    print(f"{'='*60}")

    system_msg, user_msg = build_generator_messages(
        topic=state["topic"],
        learner_profile=state.get("learner_profile", LEARNER_PROFILE),
        learned_guidance=state.get("learned_guidance"),
        retry_feedback=state.get("retry_feedback"),
        inject_error_mode=state.get("inject_error_mode") if attempt_count == 1 else None,
    )

    llm = ChatGoogleGenerativeAI(
        model=GENERATOR_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )

    lesson = _invoke_with_retry(llm, system_msg, user_msg)

    # ── Deterministic Hook for --inject-error jargon (Attempt 1 only) ──
    if state.get("inject_error_mode") == "jargon" and attempt_count == 1:
        print("[GENERATE] ⚠️ Creating a deterministic jargon violation for demo mode...")
        # Prepending guarantees these terms appear first without definition, reliably triggering both heuristic and LLM checks.
        lesson = (
            "Note: The hyper-dimensional manifold computes cosine distance across un-normalized non-Euclidean vector spaces. Advanced mathematics are required to understand this.\n\n"
            + lesson
        )

    print(f"[GENERATE] Lesson generated ({len(lesson)} chars).")

    return {
        "current_lesson": lesson,
        "attempt_count": attempt_count,
        "retry_count": retry_count,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NODE: evaluate_lesson
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def evaluate_lesson(state: dict) -> dict:
    """
    Run the 6-checkpoint evaluation. Readability and jargon are checked
    deterministically; tone, flow, grounding, examples via LLM.
    Python merges and computes overall_pass.
    """
    print(f"\n[EVALUATE] Running 6-checkpoint evaluation...")

    result = run_evaluation(state["current_lesson"])

    if result.overall_pass:
        print(f"[EVALUATE] ✅ ALL 6 CHECKPOINTS PASSED")
    else:
        failed = [c.name for c in result.failed_checkpoints]
        print(f"[EVALUATE] ❌ FAILED checkpoint(s): {', '.join(failed)}")
        for c in result.failed_checkpoints:
            print(f"  - {c.name}: {c.reason}")

    return {"evaluation_result": result.model_dump()}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NODE: log_failure
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def log_failure(state: dict) -> dict:
    """
    Log a failed evaluation attempt. Increments retry_count and
    replaces retry_feedback with THIS attempt's failure reasons only.
    """
    eval_result = EvaluationResult(**state["evaluation_result"])
    current_retry = state.get("retry_count", 0)
    attempt_number = state.get("attempt_count", 1)

    print(f"\n[LOG_FAILURE] Logging failure for attempt {attempt_number}")

    entry = RejectionEntry(
        attempt_number=attempt_number,
        timestamp=datetime.now(timezone.utc).isoformat(),
        overall_pass=False,
        failed_checkpoints=[
            {"name": c.name, "reason": c.reason}
            for c in eval_result.failed_checkpoints
        ],
        retry_instructions=eval_result.retry_instructions,
        instruction_given_for_next_attempt=(
            "Generator was instructed to apply retry instruction: "
            + "; ".join(eval_result.retry_instructions)
            if eval_result.retry_instructions
            else None
        ),
    )

    new_retry_count = current_retry + 1
    
    if current_retry < MAX_RETRIES:
        print(f"[LOG_FAILURE] Attempt {attempt_number} failed. Preparing retry {new_retry_count} of {MAX_RETRIES}...")
    else:
        print(f"[LOG_FAILURE] Attempt {attempt_number} failed. Max retries ({MAX_RETRIES}) reached across {attempt_number} total attempts.")

    return {
        "rejection_log": [entry.model_dump()],
        "retry_feedback": eval_result.retry_instructions,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NODE: finalize
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def finalize(state: dict) -> dict:
    """
    Ship the result. Write lesson and rejection log.
    """
    eval_result = EvaluationResult(**state["evaluation_result"])
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    retry_count = state.get("retry_count", 0)
    attempt_count = state.get("attempt_count", 1)

    if eval_result.overall_pass:
        final_status = "passed"
        lesson_content = state["current_lesson"]
        print(f"\n[FINALIZE] ✅ Lesson PASSED after {retry_count} retry(ies) ({attempt_count} total attempt(s)) — writing approved output.")
    else:
        final_status = "failed_quality_bar"
        lesson_content = (
            "<!-- ⚠️ DIAGNOSTIC DRAFT — NOT APPROVED ⚠️ -->\n"
            f"<!-- This lesson did not pass all quality checkpoints after {retry_count} retries ({attempt_count} total attempts). -->\n"
            "<!-- See rejection_log.json for details. -->\n\n"
            + state["current_lesson"]
        )
        print(f"\n[FINALIZE] ❌ Lesson FAILED quality bar after {retry_count} retries ({attempt_count} total attempts) — writing diagnostic draft.")

    with open(LESSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(lesson_content)
    print(f"[FINALIZE] Lesson written to {LESSON_OUTPUT_PATH}")

    rejection_log_entries = list(state.get("rejection_log", []))
    if eval_result.overall_pass:
        final_entry = RejectionEntry(
            attempt_number=attempt_count,
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall_pass=True,
            failed_checkpoints=[],
            retry_instructions=[],
            instruction_given_for_next_attempt=None,
        )
        rejection_log_entries.append(final_entry.model_dump())

    # Build formatted trace log for reviewer
    formatted_log = {
        "final_status": final_status,
        "total_attempts": attempt_count,
        "max_retries_configured": MAX_RETRIES,
        "corrections": []
    }

    for i, entry in enumerate(rejection_log_entries):
        if entry["overall_pass"]:
            continue
            
        for failed_cp in entry["failed_checkpoints"]:
            cp_name = failed_cp["name"]
            
            # Determine result in the next attempt
            next_result = "no_retry_remaining"
            if i + 1 < len(rejection_log_entries):
                next_entry = rejection_log_entries[i + 1]
                if next_entry["overall_pass"]:
                    next_result = f"{cp_name} PASSED"
                else:
                    # check if this specific checkpoint failed again
                    failed_again = any(c["name"] == cp_name for c in next_entry["failed_checkpoints"])
                    if failed_again:
                        next_result = f"{cp_name} FAILED AGAIN"
                    else:
                        next_result = f"{cp_name} PASSED"
                        
            formatted_log["corrections"].append({
                "failed_checkpoint": cp_name,
                "why": failed_cp["reason"],
                "retry_instruction": entry["instruction_given_for_next_attempt"],
                "next_attempt_result": next_result
            })

    with open(REJECTION_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(formatted_log, f, indent=2)
    print(f"[FINALIZE] Rejection log written to {REJECTION_LOG_PATH}")

    return {"final_status": final_status}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NODE: write_memory
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def write_memory_node(state: dict) -> dict:
    """
    Persist this run's outcome to SQLite for future
    get_learned_guidance() calls. Memory errors don't crash the run.
    """
    print(f"\n[MEMORY] Writing run result to learning store...")

    all_failures = []
    for entry_dict in state.get("rejection_log", []):
        entry = RejectionEntry(**entry_dict)
        for fc in entry.failed_checkpoints:
            all_failures.append({
                "attempt_number": entry.attempt_number,
                "checkpoint_name": fc["name"],
                "reason": fc["reason"],
            })

    write_run_result(
        run_id=state["run_id"],
        topic=state["topic"],
        final_status=state["final_status"],
        total_attempts=state.get("attempt_count", 1),
        failures=all_failures,
    )

    print(f"[MEMORY] Run result persisted ({len(all_failures)} failure(s) logged).")
    return {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ROUTING FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━




# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HELPER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _invoke_with_retry(llm, system_msg: str, user_msg: str) -> str:
    """Call the LLM with exponential backoff on failure."""
    last_error = None
    for attempt in range(API_RETRY_ATTEMPTS + 1):
        try:
            response = llm.invoke([
                SystemMessage(content=system_msg),
                HumanMessage(content=user_msg),
            ])
            content = response.content
            if isinstance(content, list):
                return "".join(p.get("text", "") for p in content if isinstance(p, dict) and "text" in p)
            return str(content)
        except Exception as e:
            error_str = str(e).lower()
            if any(x in error_str for x in ["api_key", " 401", " 403", "unauthenticated"]):
                print(f"[GENERATE] Non-retryable authentication error: {e}")
                raise RuntimeError(f"Authentication failed: {e}")
                
            if "quota exceeded" in error_str or "429 resource_exhausted" in error_str and "free_tier_requests" in error_str:
                print(f"[GENERATE] Non-retryable quota exhaustion error: {e}")
                raise RuntimeError(f"Quota exhausted: {e}")
                
            last_error = e
            if attempt < API_RETRY_ATTEMPTS:
                wait = API_RETRY_BACKOFF_BASE ** (attempt + 1)
                print(f"[RETRY] API call failed ({e}), retrying in {wait}s...")
                time.sleep(wait)

    raise RuntimeError(
        f"API call failed after {API_RETRY_ATTEMPTS + 1} attempts: {last_error}"
    )
