"""
Regression tests for the 2026-09-05 fix round.

Locks in the exact behaviors that previously caused live-run failures:
1. Jargon heuristic recognizes Markdown definition styles that real lessons
   use: bold-colon bullets, acronym expansions, bridge-word parentheticals.
2. Jargon heuristic no longer false-flags terms used inside compounds
   ("retrieval" inside "Retrieval-Augmented Generation", "vector" inside
   "vector database").
3. A non-defining follow-up sentence ("This is a key step.") does NOT
   excuse an undefined term; a real definitional follow-up does.
4. Demo runs are stored with a "DEMO:" topic prefix and excluded from
   learned-guidance derivation.
5. The finalize rejection log records attempt_number per correction.
6. create_docx refuses to build the submission DOCX from a diagnostic draft.
"""

import json
import os
import sqlite3
import sys
from unittest.mock import patch

import pytest

from evaluation.jargon import check_jargon_heuristically


class TestJargonDefinitionStyles:
    """Real generated lessons define terms with these Markdown styles."""

    def test_bold_colon_bullet_passes(self):
        # The exact style that caused the 2026-09-05 live-run failures:
        # every retry produced "* **Retrieval**: This means ..." and failed.
        text = "* **Retrieval**: This means searching for and finding information from a collection of documents or files."
        res = check_jargon_heuristically(text)
        assert "retrieval" not in res.missing_definitions

    def test_plain_colon_definition_passes(self):
        text = "RAG has two steps. Retrieval: finding the right facts before answering."
        res = check_jargon_heuristically(text)
        assert "retrieval" not in res.missing_definitions

    def test_bridge_word_parenthetical_passes(self):
        # "**non-Euclidean** mathematics (geometry where ...)" — the
        # parenthesis sits one word after the term.
        text = "using **non-Euclidean** mathematics (geometry where straight lines can bend) to compare meaning."
        res = check_jargon_heuristically(text)
        assert "non-Euclidean" not in res.missing_definitions

    def test_full_realistic_lesson_passes(self):
        text = (
            "RAG stands for **Retrieval-Augmented Generation**.\n\n"
            "* **Retrieval**: This means searching for and finding information from a collection of documents or files.\n"
            "* **Augmented**: This means adding something to make it better or stronger.\n"
            "* **Generation**: This means creating text or an answer.\n\n"
            "An **LLM** is a type of AI trained on massive amounts of text.\n\n"
            "The system uses a **knowledge base** (a stored collection of facts).\n\n"
            "It places text into the AI's **context window**. A context window is the amount of information a model can consider at one time.\n\n"
            "Systems use **embeddings**. An embedding is a piece of text turned into a list of numbers.\n\n"
            "These are stored in a **vector database**. A vector database is a special software tool for searching number lists."
        )
        res = check_jargon_heuristically(text)
        assert res.passed, f"expected pass, missing: {res.missing_definitions}"


class TestJargonCompoundExclusions:
    """Terms inside larger compounds are not standalone jargon uses."""

    def test_retrieval_in_acronym_expansion_not_jargon(self):
        text = "RAG stands for **Retrieval-Augmented Generation**. It is a technique for AI."
        res = check_jargon_heuristically(text)
        assert "retrieval" not in res.missing_definitions

    def test_vector_inside_vector_database_not_standalone(self):
        text = "These numbers are stored in a vector database—a special filing system."
        res = check_jargon_heuristically(text)
        assert "vector" not in res.missing_definitions

    def test_bare_vector_still_requires_definition(self):
        text = "We compute a vector for each word. This is a key step."
        res = check_jargon_heuristically(text)
        assert "vector" in res.missing_definitions


class TestFollowupDefinitionJudgment:
    """A follow-up sentence must actually define, not merely comment."""

    def test_real_definitional_followup_passes(self):
        text = "The system relies on an embedding. It is a mathematical way to represent text."
        res = check_jargon_heuristically(text)
        assert "embedding" not in res.missing_definitions

    def test_non_defining_followup_does_not_excuse(self):
        text = "The model performs retrieval. This is a key step."
        res = check_jargon_heuristically(text)
        assert "retrieval" in res.missing_definitions

    def test_demo_poison_still_caught(self):
        # The deliberate demo-mode paragraph must always fail the check.
        text = (
            "Note: The hyper-dimensional manifold computes cosine distance across "
            "un-normalized non-Euclidean vector spaces. Advanced mathematics are required "
            "to understand this."
        )
        res = check_jargon_heuristically(text)
        assert "hyper-dimensional manifold" in res.missing_definitions
        assert "non-Euclidean" in res.missing_definitions


class TestDemoRunMemoryIsolation:
    """Demo runs must not contaminate learned guidance."""

    def test_write_memory_node_prefixes_demo_topic(self, tmp_path):
        from graph.nodes import write_memory_node

        state = {
            "run_id": "demo-run-1",
            "topic": "Introduction to RAG",
            "final_status": "failed_quality_bar",
            "attempt_count": 3,
            "inject_error_mode": "jargon",
            "rejection_log": [
                {
                    "attempt_number": 1,
                    "timestamp": "2026-09-05T00:00:00+00:00",
                    "overall_pass": False,
                    "failed_checkpoints": [
                        {"name": "no_unexplained_jargon", "reason": "demo failure"}
                    ],
                    "retry_instructions": ["Fix it"],
                    "instruction_given_for_next_attempt": "Fix it",
                }
            ],
        }
        test_db = str(tmp_path / "store.db")
        with patch("memory.learning_store.DB_PATH", test_db):
            write_memory_node(state)
            conn = sqlite3.connect(test_db)
            row = conn.execute(
                "SELECT topic FROM runs WHERE run_id = 'demo-run-1'"
            ).fetchone()
            conn.close()
        assert row is not None
        assert row[0].startswith("DEMO:")

    def test_normal_run_topic_not_prefixed(self, tmp_path):
        from graph.nodes import write_memory_node

        state = {
            "run_id": "normal-run-1",
            "topic": "Introduction to RAG",
            "final_status": "passed",
            "attempt_count": 1,
            "inject_error_mode": None,
            "rejection_log": [],
        }
        test_db = str(tmp_path / "store.db")
        with patch("memory.learning_store.DB_PATH", test_db):
            write_memory_node(state)
            conn = sqlite3.connect(test_db)
            row = conn.execute(
                "SELECT topic FROM runs WHERE run_id = 'normal-run-1'"
            ).fetchone()
            conn.close()
        assert row is not None
        assert row[0] == "Introduction to RAG"

    def test_guidance_derivation_excludes_demo_runs(self, tmp_path):
        """Failures from 3+ DEMO runs must NOT trigger learned guidance."""
        from memory.learning_store import get_learned_guidance, write_run_result, generate_run_id
        from config import LEARNED_GUIDANCE_THRESHOLD

        test_db = str(tmp_path / "store.db")
        for _ in range(LEARNED_GUIDANCE_THRESHOLD + 2):
            write_run_result(
                run_id=generate_run_id(),
                topic="DEMO: Introduction to RAG",
                final_status="failed_quality_bar",
                total_attempts=3,
                failures=[{
                    "attempt_number": 1,
                    "checkpoint_name": "no_unexplained_jargon",
                    "reason": "injected demo failure",
                }],
                db_path=test_db,
            )
        assert get_learned_guidance(db_path=test_db) == []

    def test_guidance_derivation_still_fires_for_real_failures(self, tmp_path):
        """Failures from 3+ REAL runs must still trigger learned guidance."""
        from memory.learning_store import get_learned_guidance, write_run_result, generate_run_id
        from config import LEARNED_GUIDANCE_THRESHOLD

        test_db = str(tmp_path / "store.db")
        for _ in range(LEARNED_GUIDANCE_THRESHOLD):
            write_run_result(
                run_id=generate_run_id(),
                topic="Introduction to RAG",
                final_status="failed_quality_bar",
                total_attempts=3,
                failures=[{
                    "attempt_number": 1,
                    "checkpoint_name": "no_unexplained_jargon",
                    "reason": "genuinely undefined term",
                }],
                db_path=test_db,
            )
        guidance = get_learned_guidance(db_path=test_db)
        assert len(guidance) >= 1


class TestRejectionLogAttemptNumbers:
    """The finalize rejection log must carry attempt_number per correction."""

    @patch("graph.nodes.ChatGoogleGenerativeAI")
    @patch("evaluation.checkpoints.ChatGoogleGenerativeAI")
    @patch("graph.nodes._invoke_with_retry", return_value="Fake lesson text.")
    @patch("evaluation.checkpoints._call_evaluator_model")
    def test_corrections_have_attempt_numbers(
        self, mock_evaluator, mock_gen, mock_cls1, mock_cls2, tmp_path
    ):
        from graph.graph import build_graph
        from evaluation.rubric import LLMEvaluationResponse, LLMCheckpointResult

        names = [
            "accurate_grounded", "beginner_language_pedagogical", "teaches_by_example",
            "no_unexplained_jargon", "covers_key_points", "coherent_flow",
        ]

        def resp(pass_set):
            return LLMEvaluationResponse(
                checkpoints=[
                    LLMCheckpointResult(
                        name=n,
                        passed=n not in pass_set,
                        reason="ok" if n not in pass_set else "bad",
                    )
                    for n in names
                ],
                retry_instructions=["Fix it."] if pass_set else [],
            )

        mock_evaluator.side_effect = [
            resp({"beginner_language_pedagogical", "no_unexplained_jargon"}),
            resp(set()),
        ]

        rejection_path = str(tmp_path / "rejection_log.json")
        lesson_path = str(tmp_path / "lesson_output.md")
        with patch("graph.nodes.LESSON_OUTPUT_PATH", lesson_path), \
             patch("graph.nodes.REJECTION_LOG_PATH", rejection_path), \
             patch("graph.nodes.OUTPUT_DIR", str(tmp_path)), \
             patch("memory.learning_store.DB_PATH", str(tmp_path / "store.db")):
            app = build_graph()
            final_state = app.invoke({
                "topic": "Test", "learner_profile": "B", "run_id": "t1",
                "learned_guidance": [], "current_lesson": "",
                "evaluation_result": None, "retry_feedback": [],
                "retry_count": 0, "attempt_count": 0,
                "inject_error_mode": None, "rejection_log": [],
                "final_status": "pending",
            })

        assert final_state["final_status"] == "passed"
        log = json.loads(open(rejection_path, encoding="utf-8").read())
        assert log["final_status"] == "passed"
        # Both corrections came from attempt 1 — the log must say so.
        assert len(log["corrections"]) == 2
        for c in log["corrections"]:
            assert c["attempt_number"] == 1


class TestDocxDraftGuard:
    """create_docx must refuse diagnostic drafts."""

    def test_refuses_diagnostic_draft(self, tmp_path, capsys):
        sys.path.insert(0, str(tmp_path))
        from assets.create_docx import main as docx_main

        draft_path = tmp_path / "lesson_output.md"
        draft_path.write_text(
            "<!-- ⚠️ DIAGNOSTIC DRAFT — NOT APPROVED ⚠️ -->\nSome lesson text.",
            encoding="utf-8",
        )
        with patch("assets.create_docx.LESSON_PATH", draft_path), \
             patch("assets.create_docx.OUTPUT_PATH", tmp_path / "out.docx"):
            with pytest.raises(SystemExit):
                docx_main()
        assert (tmp_path / "out.docx").exists() is False

    def test_builds_from_accepted_lesson(self, tmp_path):
        sys.path.insert(0, str(tmp_path))
        from assets.create_docx import main as docx_main

        lesson_path = tmp_path / "lesson_output.md"
        lesson_path.write_text(
            "# Introduction to RAG\n\nRAG is a helpful technique. "
            "An **embedding** is a list of numbers.\n",
            encoding="utf-8",
        )
        out_path = tmp_path / "out.docx"
        with patch("assets.create_docx.LESSON_PATH", lesson_path), \
             patch("assets.create_docx.OUTPUT_PATH", out_path):
            docx_main()
        assert out_path.exists()
