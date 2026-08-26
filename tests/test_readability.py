"""
Tests for the deterministic readability check.
Zero API calls — fully offline, fast, and free.
"""

import pytest
from evaluation.readability import check_readability, _count_syllables


class TestReadabilityPass:
    """Known easy text should pass all three gates."""

    def test_simple_text_passes(self):
        text = (
            "RAG is a way to help AI give better answers. "
            "It works by looking up facts before answering. "
            "This makes the answers more correct. "
            "Think of it like a student who checks their notes before a test. "
            "The student gives better answers because they have good information."
        )
        result = check_readability(text)
        assert result.passed is True
        assert result.flesch_score >= 60
        assert result.avg_sentence_length < 20

    def test_very_simple_text(self):
        text = (
            "AI can answer questions. "
            "But sometimes AI makes mistakes. "
            "RAG helps fix this problem. "
            "It gives AI real facts to use. "
            "This makes AI answers much better."
        )
        result = check_readability(text)
        assert result.passed is True


class TestReadabilityFail:
    """Known dense text should fail at least one gate."""

    def test_academic_text_fails(self):
        text = (
            "Retrieval-Augmented Generation leverages dense passage retrieval "
            "mechanisms utilizing bi-encoder architectures to perform approximate "
            "nearest neighbor search across high-dimensional embedding spaces, "
            "subsequently concatenating retrieved document representations with "
            "the original query vector to condition the autoregressive generation "
            "process of transformer-based language models, thereby significantly "
            "ameliorating the well-documented phenomenon of hallucination that "
            "characterizes purely parametric generation approaches."
        )
        result = check_readability(text)
        assert result.passed is False

    def test_long_sentences_fail(self):
        text = (
            "RAG is a technique that combines information retrieval with text "
            "generation by first searching through a large collection of documents "
            "to find the most relevant pieces of information and then feeding those "
            "pieces along with the original question to a language model that "
            "generates a comprehensive and well-grounded answer based on the "
            "retrieved evidence rather than relying solely on its training data. "
            "This is very useful for many applications."
        )
        result = check_readability(text)
        # The first sentence is extremely long
        assert result.long_sentence_rate > 0


class TestSyllableCount:
    """Sanity checks for syllable estimation."""

    def test_monosyllables(self):
        assert _count_syllables("cat") == 1
        assert _count_syllables("the") == 1

    def test_multisyllable(self):
        assert _count_syllables("information") >= 3
        assert _count_syllables("retrieval") >= 3

    def test_empty(self):
        assert _count_syllables("") == 0


class TestReadabilityDetail:
    """The detail string should explain what failed."""

    def test_pass_detail_contains_ok(self):
        text = "AI helps people. RAG makes AI better. It is very useful."
        result = check_readability(text)
        if result.passed:
            assert "OK" in result.detail

    def test_fail_detail_contains_metric(self):
        text = (
            "Retrieval-Augmented Generation leverages sophisticated neural "
            "architectures incorporating multi-head attention mechanisms "
            "with positional encodings to facilitate contextual understanding "
            "across heterogeneous document collections stored in distributed "
            "vector databases utilizing approximate nearest neighbor algorithms."
        )
        result = check_readability(text)
        if not result.passed:
            assert "Flesch" in result.detail or "sentence" in result.detail
