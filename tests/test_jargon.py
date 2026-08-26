"""
Tests for term-specific, sentence-local heuristic jargon checker.
Zero API calls — fully offline.
"""

import pytest
from evaluation.jargon import check_jargon_heuristically, CANONICAL_TECHNICAL_TERMS


class TestJargonHeuristics:
    def test_term_is_a_passes(self):
        text = "A vector database is a special type of database."
        res = check_jargon_heuristically(text)
        assert "vector database" not in res.missing_definitions

    def test_term_which_is_passes(self):
        text = "It uses an embedding, which is a mathematical representation."
        res = check_jargon_heuristically(text)
        assert "embedding" not in res.missing_definitions

    def test_term_parenthetical_passes(self):
        text = "The system uses a knowledge base (your collection of documents)."
        res = check_jargon_heuristically(text)
        assert "knowledge base" not in res.missing_definitions

    def test_parenthetical_term_passes(self):
        text = "Large Language Models (LLMs) are very powerful."
        res = check_jargon_heuristically(text)
        assert "LLM" not in res.missing_definitions

    def test_term_em_dash_passes(self):
        text = "These numbers are stored in a vector database—a special filing system."
        res = check_jargon_heuristically(text)
        assert "vector database" not in res.missing_definitions

    def test_known_as_passes(self):
        text = "This process is known as an embedding."
        res = check_jargon_heuristically(text)
        assert "embedding" not in res.missing_definitions

    def test_think_of_as_passes(self):
        text = "You can think of a vector as an array of numbers."
        res = check_jargon_heuristically(text)
        assert "vector" not in res.missing_definitions

    def test_plural_term_passes(self):
        text = "Embeddings are mathematical representations of text."
        res = check_jargon_heuristically(text)
        assert "embedding" not in res.missing_definitions

    def test_markdown_term_passes(self):
        text = "An **embedding** is a representation of text."
        res = check_jargon_heuristically(text)
        assert "embedding" not in res.missing_definitions

    def test_followup_sentence_definition_passes(self):
        text = "The system relies on an embedding. It is a mathematical way to represent text."
        res = check_jargon_heuristically(text)
        assert "embedding" not in res.missing_definitions

    def test_unexplained_term_fails(self):
        text = "We use an embedding to process the data."
        res = check_jargon_heuristically(text)
        assert "embedding" in res.missing_definitions

    def test_unrelated_is_fails(self):
        text = "The embedding process is utilizing vector spaces."
        res = check_jargon_heuristically(text)
        assert "embedding" in res.missing_definitions
        assert "vector" in res.missing_definitions

    def test_multiple_failures(self):
        text = "RAG systems use a context window and a knowledge base."
        res = check_jargon_heuristically(text)
        assert "RAG" in res.missing_definitions
        assert "context window" in res.missing_definitions
        assert "knowledge base" in res.missing_definitions

    def test_all_canonical_terms_defined(self):
        """Verify CANONICAL_TECHNICAL_TERMS list is non-empty and accessible."""
        assert len(CANONICAL_TECHNICAL_TERMS) >= 8
        assert "RAG" in CANONICAL_TECHNICAL_TERMS
        assert "embedding" in CANONICAL_TECHNICAL_TERMS
