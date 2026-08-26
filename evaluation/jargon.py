"""
Canonical technical terms and precise sentence-local heuristic jargon checking.

Complements the LLM check for the no_unexplained_jargon checkpoint.
Maintains ONE single canonical source of truth for technical terms used across
prompts, heuristic checks, evaluator rubrics, and tests.
"""

import re
from dataclasses import dataclass

# ── Single Canonical Source of Truth for Technical Terms ──────────────
CANONICAL_TECHNICAL_TERMS: list[str] = [
    "RAG",
    "LLM",
    "retrieval",
    "embedding",
    "vector",
    "vector database",
    "context window",
    "hallucination",
    "knowledge base",
]

# Patterns for a follow-up definition sentence (e.g. "It is...", "This means...")
FOLLOWUP_DEF_PATTERNS = [
    r"^(it|this|that|these|they)\s+(is|are|means?|refers? to|acts as|stands? for)\b",
]

def build_term_definition_patterns(term: str) -> list[str]:
    """Build regex patterns that specifically tie a definition to the given term."""
    # Match the term, possibly with markdown bold/italic, possibly pluralized
    term_patt = r"[*_]*" + re.escape(term) + r"(?:s|es)?[*_]*"
    
    return [
        # term is/are/means/refers to/stands for
        rf"\b{term_patt}\s+(is|are|means?|refers? to|defined as|stands? for)\b",
        # term, which is/are
        rf"\b{term_patt}\s*,\s*(which is|which are)\b",
        # term (explanation)
        rf"\b{term_patt}\s*\([^)]+\)",
        # (term)
        rf"\(\s*{term_patt}\s*\)",
        # think of (a) term as
        rf"\bthink of\s+(a|an|the)?\s*{term_patt}\s+as\b",
        # term - a/an/the
        rf"\b{term_patt}\s*[-—]\s*(a|an|the|is|are|means?|refers? to|which)\b",
        # known as / called term
        rf"\b(known as|called|referred to as)\s+(a|an|the)?\s*{term_patt}\b",
    ]

@dataclass
class JargonCheckResult:
    passed: bool
    missing_definitions: list[str]
    detail: str


def check_jargon_heuristically(text: str) -> JargonCheckResult:
    """
    Term-specific, sentence-local heuristic jargon check.

    For each canonical term present in the text:
    1. Find the sentence of first occurrence.
    2. Check if THAT SPECIFIC SENTENCE contains a definition tied to the term.
    3. If not, check if the immediately next sentence is an explicit follow-up definition
       (e.g. starting with "It is...", "This means...").
    """
    missing = []
    sentences = _split_into_sentences(text)

    for term in CANONICAL_TECHNICAL_TERMS:
        term_pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)

        has_def = False
        term_def_patterns = build_term_definition_patterns(term)
        
        for idx, sentence in enumerate(sentences):
            if term_pattern.search(sentence):
                # Check current sentence for specific term definition
                if any(re.search(pat, sentence, re.IGNORECASE) for pat in term_def_patterns):
                    has_def = True
                    break
                
                # Check next sentence
                if idx + 1 < len(sentences):
                    next_sentence = sentences[idx + 1]
                    has_followup = any(re.search(pat, next_sentence, re.IGNORECASE) for pat in FOLLOWUP_DEF_PATTERNS)
                    has_term_and_def = term_pattern.search(next_sentence) and any(re.search(pat, next_sentence, re.IGNORECASE) for pat in term_def_patterns)
                    
                    if has_followup or has_term_and_def:
                        has_def = True
                        break

        if not has_def and term_pattern.search(text):
            missing.append(term)

    passed = len(missing) == 0
    if passed:
        detail = "Heuristic check OK: All technical terms have definitions near first use."
    else:
        detail = f"Heuristic check FAILED: Terms missing definitions near first use: {', '.join(missing)}."

    return JargonCheckResult(
        passed=passed,
        missing_definitions=missing,
        detail=detail,
    )


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences while removing markdown headers and list bullets."""
    cleaned = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*[-*]\s+", "", cleaned, flags=re.MULTILINE)
    raw = re.split(r"(?<=[.!?])\s+", cleaned.strip())
    return [s.strip() for s in raw if s.strip() and len(s.split()) >= 2]
