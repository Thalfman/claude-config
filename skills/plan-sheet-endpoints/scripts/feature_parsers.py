"""Per-sheet feature regex extractors: roads, structures, spans, construction type, cable specs."""
import re
from typing import List, Optional


_ROAD_SUFFIXES = (
    "RD", "ROAD", "ST", "STREET", "AVE", "AVENUE", "BLVD", "BOULEVARD",
    "CT", "COURT", "DR", "DRIVE", "LN", "LANE", "PKWY", "HWY", "HIGHWAY",
    "WAY", "TER", "TERRACE", "CIR", "CIRCLE", "PL", "PLACE",
)

_ROAD_RE = re.compile(
    r"\b(?P<name>[A-Z][A-Z0-9 \-]{1,40}?\s+(?:" + "|".join(_ROAD_SUFFIXES) + r"))\b"
)


def parse_road_names(text: str) -> List[str]:
    """Find all road/street names in text (deduplicated, original casing preserved)."""
    seen = []
    for m in _ROAD_RE.finditer(text):
        name = m.group("name").strip()
        if name not in seen:
            seen.append(name)
    return seen


_STRUCTURE_RE = re.compile(
    r"\b(?:POLE\s*\d+|P-\d+|STR\s*#?\s*\d+|STRUCTURE\s*\d+|MH\s*\d+|VLT\s*\d+|VAULT\s*\d+)\b",
    re.IGNORECASE,
)


def parse_structures(text: str) -> List[str]:
    """Find all structure/pole/vault labels (deduplicated, original casing preserved)."""
    seen = []
    for m in _STRUCTURE_RE.finditer(text):
        s = m.group(0).upper().replace("  ", " ").strip()
        if s not in seen:
            seen.append(s)
    return seen


_SPAN_RE = re.compile(r"\b(?P<feet>\d{2,4})\s*(?:'|FT\b|FEET\b)", re.IGNORECASE)


def parse_span_lengths(text: str) -> List[float]:
    """Find all span/length annotations as feet."""
    spans = []
    for m in _SPAN_RE.finditer(text):
        feet = float(m.group("feet"))
        if 10.0 <= feet <= 5000.0:  # reject obvious non-spans
            spans.append(feet)
    return spans


_CONSTRUCTION_KEYWORDS = [
    ("direct_bore", re.compile(r"\b(?:DIR(?:ECTIONAL)?\s+BORE|HDD)\b", re.IGNORECASE)),
    ("trench", re.compile(r"\bOPEN\s+TRENCH|\bTRENCH\b", re.IGNORECASE)),
    ("underground", re.compile(r"\b(?:UNDERGROUND|UG\b|BORE|CONDUIT|DUCT)\b", re.IGNORECASE)),
    ("overlash", re.compile(r"\bOVERLASH\b", re.IGNORECASE)),
    ("aerial", re.compile(r"\bAERIAL\b", re.IGNORECASE)),
]


def parse_construction_type(text: str) -> Optional[str]:
    """Pick the most specific construction-type keyword found.

    Priority order: direct_bore > trench > underground > overlash > aerial.
    Direct bore wins over generic underground; overlash and aerial both signal
    aerial construction but overlash is the more specific Comcast term, so we
    map both to "aerial" for the CSV column.
    """
    for label, pattern in _CONSTRUCTION_KEYWORDS:
        if pattern.search(text):
            if label == "overlash":
                return "aerial"
            return label
    return None


_CABLE_RE_FIBER_F = re.compile(r"\b(?P<count>\d{2,4})F\b")
_CABLE_RE_FIBER_COUNT = re.compile(r"\b(?P<count>\d{2,4})\s+COUNT\b", re.IGNORECASE)
_CABLE_RE_OPGW = re.compile(r"\b(?:OPGW|ADSS)\b", re.IGNORECASE)


def parse_cable_specs(text: str) -> Optional[str]:
    """Best-effort cable spec string. Picks the first matching pattern."""
    m = _CABLE_RE_FIBER_F.search(text)
    if m:
        return f"{m.group('count')}F"
    m = _CABLE_RE_FIBER_COUNT.search(text)
    if m:
        return f"{m.group('count')} COUNT"
    m = _CABLE_RE_OPGW.search(text)
    if m:
        return m.group(0).upper()
    return None
