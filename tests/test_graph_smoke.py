"""
End-to-end smoke tests for the LangGraph workflow.

These tests prove that `build_graph()` correctly wires the nodes
and state transitions together without relying on the actual Gemini API.
"""

from unittest.mock import patch
import sqlite3

import pytest

from config import DB_PATH
from graph.graph import build_graph
from evaluation.rubric import LLMEvaluationResponse, LLMCheckpointResult


@pytest.fixture()
def isolated_output_paths(tmp_path):
    """
    Redirect finalize's output writes to a temp directory.

    Without this, graph smoke tests overwrite the real
    output/lesson_output.md and output/rejection_log.json artifacts.
    """
    lesson_path = str(tmp_path / "lesson_output.md")
    rejection_path = str(tmp_path / "rejection_log.json")
    with patch("graph.nodes.LESSON_OUTPUT_PATH", lesson_path), \
         patch("graph.nodes.REJECTION_LOG_PATH", rejection_path), \
         patch("graph.nodes.OUTPUT_DIR", str(tmp_path)):
        yield lesson_path, rejection_path


# We patch ChatGoogleGenerativeAI to prevent Pydantic from trying to validate
# the API key during instantiation since it's not set in test environments.
@patch("graph.nodes.ChatGoogleGenerativeAI")
@patch("evaluation.checkpoints.ChatGoogleGenerativeAI")
@patch("graph.nodes._invoke_with_retry")
@patch("evaluation.checkpoints._call_evaluator_model")
def test_successful_path_graph_smoke(mock_evaluator, mock_generator, mock_llm_eval, mock_llm_gen, tmp_path, isolated_output_paths):
    """Test the graph routes correctly when the evaluator immediately passes."""
    mock_generator.return_value = "This is a simple fake lesson."
    
    # Fake LLM returning all PASS
    mock_evaluator.return_value = LLMEvaluationResponse(
        checkpoints=[
            LLMCheckpointResult(name="accurate_grounded", passed=True, reason="ok"),
            LLMCheckpointResult(name="beginner_language_pedagogical", passed=True, reason="ok"),
            LLMCheckpointResult(name="teaches_by_example", passed=True, reason="ok"),
            LLMCheckpointResult(name="no_unexplained_jargon", passed=True, reason="ok"),
            LLMCheckpointResult(name="covers_key_points", passed=True, reason="ok"),
            LLMCheckpointResult(name="coherent_flow", passed=True, reason="ok"),
        ],
        retry_instructions=[]
    )

    app = build_graph()
    
    test_db = str(tmp_path / "test_store.db")
    with patch("memory.learning_store.DB_PATH", test_db):
        final_state = app.invoke({
            "topic": "Test RAG",
            "learner_profile": "Beginner",
            "run_id": "test_run_123"
        })

    assert final_state["final_status"] == "passed"
    assert final_state.get("retry_count", 0) == 0
    assert final_state.get("attempt_count") == 1
    assert mock_generator.call_count == 1
    assert mock_evaluator.call_count == 1


@patch("graph.nodes.ChatGoogleGenerativeAI")
@patch("evaluation.checkpoints.ChatGoogleGenerativeAI")
@patch("graph.nodes._invoke_with_retry")
@patch("evaluation.checkpoints._call_evaluator_model")
def test_retry_path_graph_smoke(mock_evaluator, mock_generator, mock_llm_eval, mock_llm_gen, tmp_path, isolated_output_paths):
    """Test the graph routes back to generation on failure, then passes."""
    mock_generator.return_value = "This is a simple fake lesson."

    # First call fails, second call passes
    mock_evaluator.side_effect = [
        LLMEvaluationResponse(
            checkpoints=[
                LLMCheckpointResult(name="accurate_grounded", passed=True, reason="ok"),
                LLMCheckpointResult(name="beginner_language_pedagogical", passed=True, reason="ok"),
                LLMCheckpointResult(name="teaches_by_example", passed=False, reason="no example"),
                LLMCheckpointResult(name="no_unexplained_jargon", passed=True, reason="ok"),
                LLMCheckpointResult(name="covers_key_points", passed=True, reason="ok"),
                LLMCheckpointResult(name="coherent_flow", passed=True, reason="ok"),
            ],
            retry_instructions=["Add an example"]
        ),
        LLMEvaluationResponse(
            checkpoints=[
                LLMCheckpointResult(name="accurate_grounded", passed=True, reason="ok"),
                LLMCheckpointResult(name="beginner_language_pedagogical", passed=True, reason="ok"),
                LLMCheckpointResult(name="teaches_by_example", passed=True, reason="added example"),
                LLMCheckpointResult(name="no_unexplained_jargon", passed=True, reason="ok"),
                LLMCheckpointResult(name="covers_key_points", passed=True, reason="ok"),
                LLMCheckpointResult(name="coherent_flow", passed=True, reason="ok"),
            ],
            retry_instructions=[]
        )
    ]

    app = build_graph()
    
    test_db = str(tmp_path / "test_store.db")
    with patch("memory.learning_store.DB_PATH", test_db):
        final_state = app.invoke({
            "topic": "Test RAG",
            "learner_profile": "Beginner",
            "run_id": "test_run_456"
        })

    assert final_state["final_status"] == "passed"
    assert final_state["retry_count"] == 1
    assert final_state.get("attempt_count") == 2
    assert mock_generator.call_count == 2
    assert mock_evaluator.call_count == 2


@patch("graph.nodes.ChatGoogleGenerativeAI")
@patch("evaluation.checkpoints.ChatGoogleGenerativeAI")
@patch("graph.nodes._invoke_with_retry")
@patch("evaluation.checkpoints._call_evaluator_model")
def test_retry_exhaustion_graph_smoke(mock_evaluator, mock_generator, mock_llm_eval, mock_llm_gen, tmp_path, isolated_output_paths):
    """Test the graph exits with failed_quality_bar after max retries."""
    mock_generator.return_value = "This is a simple fake lesson."

    # Always fails
    mock_evaluator.return_value = LLMEvaluationResponse(
        checkpoints=[
            LLMCheckpointResult(name="accurate_grounded", passed=True, reason="ok"),
            LLMCheckpointResult(name="beginner_language_pedagogical", passed=True, reason="ok"),
            LLMCheckpointResult(name="teaches_by_example", passed=False, reason="never adds example"),
            LLMCheckpointResult(name="no_unexplained_jargon", passed=True, reason="ok"),
            LLMCheckpointResult(name="covers_key_points", passed=True, reason="ok"),
            LLMCheckpointResult(name="coherent_flow", passed=True, reason="ok"),
        ],
        retry_instructions=["Add an example"]
    )

    app = build_graph()
    
    test_db = str(tmp_path / "test_store.db")
    with patch("memory.learning_store.DB_PATH", test_db):
        final_state = app.invoke({
            "topic": "Test RAG",
            "learner_profile": "Beginner",
            "run_id": "test_run_789"
        })

    assert final_state["final_status"] == "failed_quality_bar"
    assert final_state.get("retry_count") == 2
    assert final_state.get("attempt_count") == 3
    # Log entries should exactly match the attempt count, without final failure duplicated
    assert len(final_state.get("rejection_log", [])) == 3
    # Initial attempt + 2 retries = 3 calls
    assert mock_generator.call_count == 3
    assert mock_evaluator.call_count == 3

    # Explicit memory verification for the attempt count
    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT total_attempts FROM runs WHERE run_id = ?", ("test_run_789",))
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == 3
