"""Parse sheet identifiers and continuation references from CD-page text."""
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ContinuationRef:
    direction: str   # "from", "to", or "unknown"
    target: str
    original: str


_SHEET_ID_PATTERNS = [
    re.compile(r"SHEET\s*[#\-]?\s*(\w+)\s+OF\s+\w+", re.IGNORECASE),
    re.compile(r"SITE\s+PLAN\s*[#\-]?\s*(\d\w*)", re.IGNORECASE),
    re.compile(r"\bSP\s*[#\-]\s*(\w+)", re.IGNORECASE),
    re.compile(r"\bS\s*-\s*(\w+)\b", re.IGNORECASE),
    re.compile(r"SHEET\s*[#\-]?\s*(\d\w*)", re.IGNORECASE),
]


def parse_sheet_id(text: str) -> Optional[str]:
    """Return the first sheet identifier found, else None.

    Patterns are first-match-wins, ordered by specificity:
      "SHEET 12 OF 25" -> "12"
      "SITE PLAN - 5"  -> "5"
      "SP-12"          -> "12"
      "S-3"            -> "3"
      "SHEET 7"        -> "7"
    """
    for pattern in _SHEET_ID_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1)
    return None


_TO_RE = re.compile(
    r"(?:MATCH(?:LINE)?\s+TO|SEE|GO\s+TO|CONTINUED?\s+ON)\s+"
    r"(?:SHEET|SITE\s+PLAN|SP)\s*[#\-]?\s*(?P<target>\w+)",
    re.IGNORECASE,
)

_FROM_RE = re.compile(
    r"(?:CONTINUED?\s+FROM|FROM)\s+"
    r"(?:SHEET|SITE\s+PLAN|SP)\s*[#\-]?\s*(?P<target>\w+)",
    re.IGNORECASE,
)


def parse_continuation_refs(text: str) -> List[ContinuationRef]:
    """Find all match/continuation references. Returns list (possibly empty)."""
    refs: List[ContinuationRef] = []

    for m in _FROM_RE.finditer(text):
        refs.append(ContinuationRef(direction="from", target=m.group("target"), original=m.group(0)))

    for m in _TO_RE.finditer(text):
        # Skip if this match is contained in a from-match we already added
        if any(r.original == m.group(0) for r in refs):
            continue
        refs.append(ContinuationRef(direction="to", target=m.group("target"), original=m.group(0)))

    return refs
