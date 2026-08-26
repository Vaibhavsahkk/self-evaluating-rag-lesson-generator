import re
from dataclasses import dataclass


@dataclass
class HeuristicGroundingResult:
    passed: bool
    detail: str


ABSOLUTE_PATTERNS = [
    r"stops\s+(the\s+ai\s+from\s+)?(guessing\s+)?(fake\s+facts?|hallucinations?)",
    r"stops\s+the\s+ai\s+from\s+guessing",
    r"prevents\s+(this|that|fake\s+answers?|hallucinations?)",
    r"completely\s+correct\s+answers?",
    r"always\s+gives\s+correct\s+answers?",
    r"guarantees\s+factual\s+correctness",
    r"completely\s+prevents\s+hallucinations?",
    r"eliminates\s+hallucinations?",
    r"guarantees\s+(accurate\s+answers?|accuracy)",
    r"never\s+(hallucinates?|makes\s+things\s+up|guesses)",
]


def check_absolute_claims(text: str) -> HeuristicGroundingResult:
    """
    Deterministically check if the text contains prohibited absolute claims
    about RAG capabilities.
    """
    failures = []
    text_lower = text.lower()
    
    for pattern in ABSOLUTE_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            failures.append(f'"{match.group(0)}"')

    if failures:
        return HeuristicGroundingResult(
            passed=False,
            detail=f"Contains prohibited absolute claims: {', '.join(failures)}"
        )
    
    return HeuristicGroundingResult(passed=True, detail="No absolute claims found.")
