"""
Canonical technical terms and definition-detection heuristics.

Complements the LLM check for the no_unexplained_jargon checkpoint.
Maintains ONE single canonical source of truth for technical terms used across
prompts, heuristic checks, evaluator rubrics, and tests.

The checker is line-aware: lessons are Markdown, and terms are typically
defined either in the sentence that introduces them or in a bullet line
("term — definition", "term: definition", "term (definition)"). Splitting on
raw sentence punctuation alone loses that structure, so lines are first
split structurally (newlines / bullets / headers) and only then into
sentences.
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
    "hyper-dimensional manifold",
    "non-Euclidean",
]

# Terms whose bare word is also ordinary English (e.g. "vector" inside the
# acronym expansion "Retrieval-Augmented Generation" is not a standalone use
# of the technical term "retrieval"). Occurrences inside a hyphenated
# compound or an expanded acronym are ignored when judging whether the term
# was used as jargon.
_COMPOUND_NEIGHBOURS = {
    # term: regex of compounds/acronyms in which it does not count as a use
    "retrieval": r"Retrieval-Augmented|retrieval-augmented",
    "vector": r"vector database|vector databases|Vector Database",
}


def build_term_definition_patterns(term: str) -> list[str]:
    """Build regex patterns that specifically tie a definition to the given term."""
    # Match the term, possibly with markdown bold/italic, possibly pluralized
    term_patt = r"[*_]*" + re.escape(term) + r"(?:s|es)?[*_]*"

    return [
        # term is/are/means/refers to/stands for
        rf"\b{term_patt}\s+(is|are|means?|refers? to|defined as|stands? for)\b",
        # term, which is/are
        rf"\b{term_patt}\s*,\s*(which is|which are)\b",
        # term (explanation) — allow a short bridge word before the parenthesis
        rf"\b{term_patt}\s*(?:\w+\s+)?\([^)]+\)",
        # (term)
        rf"\(\s*{term_patt}\s*\)",
        # think of (a) term as
        rf"\bthink of\s+(a|an|the)?\s*{term_patt}\s+as\b",
        # term - a/an/the/is/are  (dash style, incl. bullet "Term — a ...")
        rf"\b{term_patt}\s*[-—]\s*(a|an|the|is|are|means?|refers? to|which)\b",
        # term: definition  (colon style — the standard Markdown bullet form)
        rf"\b{term_patt}\s*:\s+\S",
        # known as / called term
        rf"\b(known as|called|referred to as)\s+(a|an|the)?\s*{term_patt}\b",
    ]


def _term_used_as_jargon(sentence: str, term: str) -> bool:
    """
    True if the sentence uses `term` as a standalone technical term.
    Occurrences glued into a larger hyphenated compound (e.g. "retrieval"
    inside "Retrieval-Augmented Generation") are not standalone uses.
    """
    compound = _COMPOUND_NEIGHBOURS.get(term)
    if compound:
        # Strip compound occurrences first, then look for a standalone use.
        remainder = re.sub(compound, "", sentence)
        return bool(re.search(r"\b" + re.escape(term) + r"\b", remainder, re.IGNORECASE))
    return bool(re.search(r"\b" + re.escape(term) + r"\b", sentence, re.IGNORECASE))


# A follow-up sentence counts as a definition when its pronoun-subject
# copula introduces a real descriptive explanation ("It is a list of
# numbers that ..."), not a bare evaluation ("This is a key step.").
_FOLLOWUP_DEF_RE = re.compile(
    r"^(it|this|that|these|they)\s+"
    r"(is|are|means?|refers? to|acts as|stands? for)\s+"
    r"(a|an|the)?\s*"
    r"(way|method|process|technique|type|kind|form|list|collection|amount|number|"
    r"representation|database|model|tool|system|piece|technology|concept|"
    r"computer program|mathematical|special|software|search|amount)\b",
    re.IGNORECASE,
)


def _followup_defines(next_line: str) -> bool:
    """True if the next line reads as an explicit definition of the previous term."""
    return bool(_FOLLOWUP_DEF_RE.search(next_line.strip()))


@dataclass
class JargonCheckResult:
    passed: bool
    missing_definitions: list[str]
    detail: str


def check_jargon_heuristically(text: str) -> JargonCheckResult:
    """
    Term-specific, definition-detection heuristic jargon check.

    For each canonical term used in the text:
    1. Find the first structural line whose sentences use the term as
       standalone jargon.
    2. Accept a definition if THAT line, the line's other sentences, or the
       next line contains a definition tied to the term (covering sentence,
       bullet-colon, dash, parenthetical, and follow-up definition styles).
    """
    missing = []
    lines = _split_into_lines(text)

    for term in CANONICAL_TECHNICAL_TERMS:
        term_def_patterns = [re.compile(p, re.IGNORECASE) for p in build_term_definition_patterns(term)]
        has_def = False
        used_anywhere = False

        for idx, line in enumerate(lines):
            if not _term_used_as_jargon(line, term):
                continue
            used_anywhere = True

            # 1) Definition anywhere within the same structural line
            if any(p.search(line) for p in term_def_patterns):
                has_def = True
                break

            # 2) Follow-up definition on the immediately next line. A pronoun
            #    follow-up ("It is ...", "This means ...") counts only when it
            #    reads as an actual definition (copula + descriptive content),
            #    not a mere comment like "This is a key step."
            if idx + 1 < len(lines):
                nxt = lines[idx + 1]
                if any(p.search(nxt) for p in term_def_patterns):
                    has_def = True
                    break
                if _followup_defines(nxt):
                    has_def = True
                    break

        if used_anywhere and not has_def:
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


# Patterns for a follow-up definition sentence (e.g. "It is...", "This means...")
FOLLOWUP_DEF_PATTERNS = [
    r"(^|\n)\s*(it|this|that|these|they)\s+(is|are|means?|refers? to|acts as|stands? for)\b",
]


def _split_into_lines(text: str) -> list[str]:
    """
    Split Markdown text into structural lines, then each line into sentences.

    Bullet markers, numbering, and header hashes are removed so pattern
    matching works on the content. Headings are kept as lines because
    "## How Retrieval Works" style headings often pair with a defining
    sentence in the same visual block.
    """
    cleaned_lines = []
    for raw_line in text.split("\n"):
        line = re.sub(r"^#{1,6}\s+", "", raw_line)
        line = re.sub(r"^\s*[-*]\s+", "", line)
        line = re.sub(r"^\s*\d+[.)]\s+", "", line)
        line = line.strip()
        if not line:
            continue
        sentences = re.split(r"(?<=[.!?])\s+", line)
        for s in sentences:
            s = s.strip()
            if s and len(s.split()) >= 2:
                cleaned_lines.append(s)
    return cleaned_lines


# Kept for backwards compatibility with older imports/tests.
def _split_into_sentences(text: str) -> list[str]:
    return _split_into_lines(text)
