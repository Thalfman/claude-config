"""Score-based page classifier for CD pages.

Each page text is scored against keyword rules for each PageType. The
highest-scoring type with a score >= MIN_SCORE wins; otherwise OTHER.

The classifier is intentionally permissive: the goal is to keep clearly
non-plan-profile pages out of the per-sheet output, not to perfectly tag
every page.
"""
import re
from enum import Enum
from typing import List

from scripts.page_text import TextBlock
from scripts.sheet_id_parser import parse_continuation_refs
from scripts.station_parser import parse_stations


class PageType(str, Enum):
    PLAN_PROFILE = "plan_profile"
    COVER = "cover"
    VICINITY = "vicinity"
    LEGEND = "legend"
    NOTES = "notes"
    DETAIL = "detail"
    TRAFFIC_CONTROL = "traffic_control"
    RASTER = "raster"
    OTHER = "other"


_MIN_SCORE = 3


_KEYWORD_RULES = {
    PageType.COVER: [
        (re.compile(r"\bCOVER\s+SHEET\b", re.IGNORECASE), 5),
        (re.compile(r"\bTITLE\s+SHEET\b", re.IGNORECASE), 5),
        (re.compile(r"\bCONSTRUCTION\s+DRAWINGS?\b", re.IGNORECASE), 2),
    ],
    PageType.VICINITY: [
        (re.compile(r"\bVICINITY\b", re.IGNORECASE), 5),
        (re.compile(r"\bOVERVIEW(?:\s+MAP)?\b", re.IGNORECASE), 4),
        (re.compile(r"\bINDEX\s+OF\s+SHEETS\b", re.IGNORECASE), 3),
        (re.compile(r"\bKEY\s+MAP\b", re.IGNORECASE), 4),
    ],
    PageType.LEGEND: [
        (re.compile(r"\bLEGEND\b", re.IGNORECASE), 5),
        (re.compile(r"\bSYMBOLS?\b", re.IGNORECASE), 3),
        (re.compile(r"\bABBREVIATIONS?\b", re.IGNORECASE), 3),
    ],
    PageType.NOTES: [
        (re.compile(r"\bGENERAL\s+NOTES\b", re.IGNORECASE), 5),
        (re.compile(r"\bCONSTRUCTION\s+NOTES\b", re.IGNORECASE), 5),
        (re.compile(r"\bSPECIFICATIONS?\b", re.IGNORECASE), 2),
    ],
    PageType.DETAIL: [
        (re.compile(r"\bTYPICAL\s+DETAILS?\b", re.IGNORECASE), 5),
        (re.compile(r"\bDETAIL\s+SHEET\b", re.IGNORECASE), 5),
        (re.compile(r"\bSTANDARD\s+DETAILS?\b", re.IGNORECASE), 4),
    ],
    PageType.TRAFFIC_CONTROL: [
        (re.compile(r"\bTRAFFIC\s+CONTROL\b", re.IGNORECASE), 5),
        (re.compile(r"\bMAINTENANCE\s+OF\s+TRAFFIC\b", re.IGNORECASE), 5),
        (re.compile(r"\bMOT\b", re.IGNORECASE), 3),
        (re.compile(r"\bMUTCD\b", re.IGNORECASE), 3),
    ],
}


def _score_plan_profile(text: str, blocks: List[TextBlock]) -> int:
    """Plan-profile heuristic: stations + match refs + structures."""
    score = 0
    stations = parse_stations(text)
    score += min(len(stations), 4) * 2  # cap at 8 from stations alone

    refs = parse_continuation_refs(text)
    score += min(len(refs), 2) * 2

    # Structures (rough count)
    structure_re = re.compile(r"\b(?:POLE\s*\d+|P-\d+|STR\s*#?\s*\d+)\b", re.IGNORECASE)
    score += min(len(structure_re.findall(text)), 4)

    # Penalty for clear non-plan keywords
    for penalty_re, penalty in (
        (re.compile(r"\bCOVER\s+SHEET\b", re.IGNORECASE), -10),
        (re.compile(r"\bVICINITY\b", re.IGNORECASE), -10),
        (re.compile(r"\bOVERVIEW(?:\s+MAP)?\b", re.IGNORECASE), -10),
        (re.compile(r"\bGENERAL\s+NOTES\b", re.IGNORECASE), -10),
        (re.compile(r"\bTYPICAL\s+DETAILS?\b", re.IGNORECASE), -10),
        (re.compile(r"\bTRAFFIC\s+CONTROL\b", re.IGNORECASE), -10),
        (re.compile(r"\bLEGEND\b", re.IGNORECASE), -10),
    ):
        if penalty_re.search(text):
            score += penalty

    return score


def classify_page(text: str, blocks: List[TextBlock]) -> PageType:
    """Return the most likely PageType for this page."""
    if not text or len(text.strip()) < 10:
        return PageType.RASTER

    scores = {pt: 0 for pt in PageType if pt not in (PageType.OTHER, PageType.RASTER)}

    for pt, rules in _KEYWORD_RULES.items():
        for pattern, weight in rules:
            if pattern.search(text):
                scores[pt] += weight

    scores[PageType.PLAN_PROFILE] = _score_plan_profile(text, blocks)

    best = max(scores.items(), key=lambda kv: kv[1])
    if best[1] >= _MIN_SCORE:
        return best[0]
    return PageType.OTHER
