import pytest
import os
from evaluation.checkpoints import run_evaluation

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

@pytest.mark.live
@pytest.mark.skipif(os.environ.get("RUN_LIVE_LLM_TESTS") != "1", reason="Live LLM tests disabled by default")
def test_evaluator_rejects_absolute_claims():
    """
    The evaluator should fail the accurate_grounded checkpoint if the lesson
    contains absolute claims (which should now be caught by heuristic checks too).
    """
    path = os.path.join(FIXTURES_DIR, "accuracy_absolute_claim.md")
    with open(path, "r", encoding="utf-8") as f:
        lesson_text = f.read()

    result = run_evaluation(lesson_text)
    print("\nRESULT:", result)
    
    ag = next(c for c in result.checkpoints if c.name == "accurate_grounded")
    assert ag.passed is False
    assert result.overall_pass is False

@pytest.mark.live
@pytest.mark.skipif(os.environ.get("RUN_LIVE_LLM_TESTS") != "1", reason="Live LLM tests disabled by default")
def test_evaluator_rejects_invented_facts():
    """
    The evaluator should fail the accurate_grounded checkpoint if the lesson
    invents specific facts that are not framed as hypothetical.
    """
    path = os.path.join(FIXTURES_DIR, "accuracy_invented_fact.md")
    with open(path, "r", encoding="utf-8") as f:
        lesson_text = f.read()

    result = run_evaluation(lesson_text)
    print("\nRESULT:", result)
    
    ag = next(c for c in result.checkpoints if c.name == "accurate_grounded")
    assert ag.passed is False
    assert result.overall_pass is False


@pytest.mark.live
@pytest.mark.skipif(os.environ.get("RUN_LIVE_LLM_TESTS") != "1", reason="Live LLM tests disabled by default")
def test_evaluator_rejects_stops_guessing():
    """
    The evaluator should fail the accurate_grounded checkpoint if the lesson
    says RAG 'stops the AI from guessing'.
    """
    path = os.path.join(FIXTURES_DIR, "accuracy_stops_guessing.md")
    with open(path, "r", encoding="utf-8") as f:
        lesson_text = f.read()

    result = run_evaluation(lesson_text)
    print("\nRESULT:", result)
    
    ag = next(c for c in result.checkpoints if c.name == "accurate_grounded")
    assert ag.passed is False
    assert result.overall_pass is False

