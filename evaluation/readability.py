"""
Deterministic readability checks — no LLM call, fully unit-testable.

This is the programmatic half of the beginner_language checkpoint.
It is a signal, not proof — a lesson can score Flesch 70 and still be
full of undefined jargon. That's why it's combined with the LLM
pedagogical check; neither part alone is sufficient.
"""

import re
from dataclasses import dataclass

from config import (
    READABILITY_FLESCH_MIN,
    READABILITY_AVG_SENTENCE_MAX,
    READABILITY_LONG_SENTENCE_RATE_MAX,
)


@dataclass
class ReadabilityResult:
    """Result of the deterministic readability check."""
    flesch_score: float
    avg_sentence_length: float
    long_sentence_rate: float
    passed: bool
    detail: str  # human-readable explanation of the result


def check_readability(text: str) -> ReadabilityResult:
    """
    Run all three readability gates and return a combined result.
    
    PASS requires all three:
      - Flesch Reading Ease >= READABILITY_FLESCH_MIN
      - Average sentence length < READABILITY_AVG_SENTENCE_MAX words
      - Long-sentence rate (>25 words) < READABILITY_LONG_SENTENCE_RATE_MAX
    """
    sentences = _split_sentences(text)
    words = _split_words(text)

    flesch = _flesch_reading_ease(sentences, words)
    avg_len = _avg_sentence_length(sentences, words)
    long_rate = _long_sentence_rate(sentences, threshold_words=25)

    passed = (
        flesch >= READABILITY_FLESCH_MIN
        and avg_len < READABILITY_AVG_SENTENCE_MAX
        and long_rate < READABILITY_LONG_SENTENCE_RATE_MAX
    )

    if passed:
        detail = (
            f"Readability OK: Flesch={flesch:.1f} (≥{READABILITY_FLESCH_MIN}), "
            f"avg sentence={avg_len:.1f} words (<{READABILITY_AVG_SENTENCE_MAX}), "
            f"long-sentence rate={long_rate:.0%} (<{READABILITY_LONG_SENTENCE_RATE_MAX:.0%})."
        )
    else:
        parts = []
        if flesch < READABILITY_FLESCH_MIN:
            parts.append(f"Flesch={flesch:.1f} (need ≥{READABILITY_FLESCH_MIN})")
        if avg_len >= READABILITY_AVG_SENTENCE_MAX:
            parts.append(
                f"avg sentence={avg_len:.1f} words (need <{READABILITY_AVG_SENTENCE_MAX})"
            )
        if long_rate >= READABILITY_LONG_SENTENCE_RATE_MAX:
            parts.append(
                f"long-sentence rate={long_rate:.0%} "
                f"(need <{READABILITY_LONG_SENTENCE_RATE_MAX:.0%})"
            )
        detail = "Readability too complex: " + ", ".join(parts) + "."

    return ReadabilityResult(
        flesch_score=flesch,
        avg_sentence_length=avg_len,
        long_sentence_rate=long_rate,
        passed=passed,
        detail=detail,
    )


# ── Internal helpers ──────────────────────────────────────────────────


def _split_sentences(text: str) -> list[str]:
    """
    Split text into sentences. Handles common abbreviations,
    markdown headers, and bullet points.
    """
    # Strip markdown headers and bullet markers for cleaner sentence splitting
    cleaned = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*[-*]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)

    # Split on sentence-ending punctuation followed by whitespace or end
    raw = re.split(r"(?<=[.!?])\s+", cleaned.strip())
    return [s.strip() for s in raw if s.strip() and len(s.split()) >= 2]


def _split_words(text: str) -> list[str]:
    """Extract all alphabetic words from text."""
    return re.findall(r"\b[a-zA-Z]+\b", text)


def _count_syllables(word: str) -> int:
    """Estimate syllable count for an English word."""
    word = word.lower().strip()
    if not word:
        return 0
    if len(word) <= 3:
        return 1

    # Remove trailing silent 'e'
    if word.endswith("e") and not word.endswith("le"):
        word = word[:-1]

    # Count vowel groups
    count = 0
    prev_vowel = False
    for char in word:
        is_vowel = char in "aeiouy"
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel

    return max(1, count)


def _flesch_reading_ease(sentences: list[str], words: list[str]) -> float:
    """
    Flesch Reading Ease score.
    Higher = easier to read. 60+ is the target for this use case.
    """
    if not sentences or not words:
        return 0.0

    total_syllables = sum(_count_syllables(w) for w in words)
    asl = len(words) / len(sentences)       # average sentence length
    asw = total_syllables / len(words)       # average syllables per word

    return 206.835 - (1.015 * asl) - (84.6 * asw)


def _avg_sentence_length(sentences: list[str], words: list[str]) -> float:
    """Average number of words per sentence."""
    if not sentences:
        return 0.0
    return len(words) / len(sentences)


def _long_sentence_rate(sentences: list[str], threshold_words: int = 25) -> float:
    """Fraction of sentences exceeding the word threshold."""
    if not sentences:
        return 0.0
    long_count = sum(1 for s in sentences if len(s.split()) > threshold_words)
    return long_count / len(sentences)
