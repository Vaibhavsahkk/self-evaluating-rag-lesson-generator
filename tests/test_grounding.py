import pytest
from evaluation.grounding import check_absolute_claims

def test_no_absolute_claims():
    text = "RAG can reduce the chance of unsupported answers."
    res = check_absolute_claims(text)
    assert res.passed is True

def test_stops_hallucinations_fails():
    text = "Because it uses a database, RAG stops hallucinations entirely."
    res = check_absolute_claims(text)
    assert res.passed is False
    assert "stops hallucinations" in res.detail

def test_guarantees_factual_correctness_fails():
    text = "The retrieval process guarantees factual correctness."
    res = check_absolute_claims(text)
    assert res.passed is False
    assert "guarantees factual correctness" in res.detail

def test_multiple_failures():
    text = "RAG stops hallucinations and guarantees accurate answers."
    res = check_absolute_claims(text)
    assert res.passed is False
    assert "stops hallucinations" in res.detail
    assert "guarantees accurate answers" in res.detail
