"""
Evaluation checkpoints — the 6-checkpoint rubric + merge logic.

Enforces:
1. Deterministic readability gate + LLM pedagogical check for beginner_language.
2. Deterministic heuristic jargon gate + LLM check for no_unexplained_jargon.
3. Strict Pydantic validation (exactly 6 unique checkpoints).
4. Python-computed overall_pass.

4. Python-computed overall_pass.
"""

import json
import time

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from config import (
    EVALUATOR_MODEL,
    GOOGLE_API_KEY,
    REFERENCES_PATH,
    API_RETRY_ATTEMPTS,
    API_RETRY_BACKOFF_BASE,
    LEARNER_PROFILE,
)
from evaluation.readability import check_readability
from evaluation.jargon import check_jargon_heuristically
from evaluation.grounding import check_absolute_claims
from evaluation.rubric import (
    CheckpointResult,
    EvaluationResult,
    LLMEvaluationResponse,
)
from evaluation.merge import _merge_checkpoints
from graph.prompts import build_evaluator_messages


def load_reference_text() -> str:
    """
    Load rag_facts.md. Fail fast if missing or empty —
    evaluating 'accurate & grounded' against nothing is meaningless.
    """
    try:
        with open(REFERENCES_PATH, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Reference file not found at {REFERENCES_PATH}. "
            f"The accurate_grounded checkpoint cannot run without it."
        )

    if not text:
        raise ValueError(
            f"Reference file at {REFERENCES_PATH} is empty. "
            f"The accurate_grounded checkpoint cannot run without content."
        )

    return text


def run_evaluation(lesson_text: str) -> EvaluationResult:
    """
    Full evaluation pipeline:
      1. Deterministic readability check (no LLM)
      2. Deterministic heuristic jargon check (no LLM)
      3. LLM evaluation (5 checkpoints + pedagogical beginner_language)
      4. Merge:
         - beginner_language = readability.passed AND llm_pedagogical.passed
         - no_unexplained_jargon = heuristic_jargon.passed AND llm_jargon.passed
      5. overall_pass = all 6 passed (computed in Python, validated by Pydantic)
    """
    readability = check_readability(lesson_text)
    heuristic_jargon = check_jargon_heuristically(lesson_text)
    heuristic_grounding = check_absolute_claims(lesson_text)

    reference_text = load_reference_text()
    llm_response = _call_evaluator_model(lesson_text, reference_text)

    merged_checkpoints = _merge_checkpoints(
        llm_response, readability, heuristic_jargon, heuristic_grounding
    )

    retry_instructions = list(llm_response.retry_instructions)

    if not readability.passed:
        retry_instructions.append(f"Simplify sentence structures: {readability.detail}")

    if not heuristic_jargon.passed:
        retry_instructions.append(
            f"Define missing terms immediately at first use: {heuristic_jargon.detail}"
        )

    if not heuristic_grounding.passed:
        retry_instructions.append(
            f"Remove absolute claims about RAG: {heuristic_grounding.detail}"
        )

    overall_pass = all(c.passed for c in merged_checkpoints)

    return EvaluationResult(
        overall_pass=overall_pass,
        checkpoints=merged_checkpoints,
        retry_instructions=retry_instructions,
    )


def _call_evaluator_model(
    lesson_text: str,
    reference_text: str,
) -> LLMEvaluationResponse:
    """
    Call the evaluator LLM using native structured output.
    Distinguishes between non-retryable errors (auth/config) and
    retryable infrastructure/network errors.
    """
    system_msg, user_msg = build_evaluator_messages(
        lesson_text=lesson_text,
        reference_text=reference_text,
    )

    llm = ChatGoogleGenerativeAI(
        model=EVALUATOR_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )
    structured_llm = llm.with_structured_output(LLMEvaluationResponse)

    last_error = None
    for attempt in range(API_RETRY_ATTEMPTS + 1):
        try:
            response = structured_llm.invoke([
                SystemMessage(content=system_msg),
                HumanMessage(content=user_msg),
            ])
            if isinstance(response, LLMEvaluationResponse):
                return response
            else:
                # LLM returned something unexpected, treat as retryable parsing issue
                raise ValueError(f"Expected LLMEvaluationResponse, got {type(response)}")
                
        except Exception as e:
            error_str = str(e).lower()
            if any(x in error_str for x in ["api_key", " 401", " 403", "unauthenticated"]):
                print(f"[EVALUATOR] Non-retryable authentication error: {e}")
                raise RuntimeError(f"Authentication failed: {e}")
                
            last_error = e
            if attempt < API_RETRY_ATTEMPTS:
                wait = API_RETRY_BACKOFF_BASE ** (attempt + 1)
                print(f"[RETRY] Evaluator API call failed ({e}), retrying in {wait}s...")
                time.sleep(wait)

    raise RuntimeError(
        f"Evaluator API call failed after {API_RETRY_ATTEMPTS + 1} attempts: {last_error}"
    )
