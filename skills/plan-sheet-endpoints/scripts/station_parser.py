"""Parse construction-drawing station markers like 'B 21+37' or 'STA 5+00'."""
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Station:
    prefix: Optional[str]   # e.g. "B", "STA", or None for bare "21+37"
    value: int              # position along route in feet (21+37 -> 2137)
    original: str           # the matched substring


_PREFIXED_RE = re.compile(
    r"\b(?P<prefix>STA(?:TION)?|[A-Z])\s+(?P<station>\d{1,4}\+\d{2}(?:\.\d+)?)",
    re.IGNORECASE,
)

_BARE_RE = re.compile(r"\b(?P<station>\d{1,4}\+\d{2}(?:\.\d+)?)\b")


def station_to_value(station_text: str) -> int:
    """Convert '21+37' or '21+37.5' to feet (2137). Truncates fractional feet."""
    plus_split = station_text.split("+", 1)
    hundreds = int(plus_split[0])
    feet = float(plus_split[1])
    return hundreds * 100 + int(feet)


def parse_stations(text: str) -> List[Station]:
    """Find all station markers in text. Prefixed forms take priority over bare."""
    found: List[Station] = []
    consumed_spans: List[tuple] = []

    for m in _PREFIXED_RE.finditer(text):
        prefix = m.group("prefix").upper()
        station = m.group("station")
        found.append(Station(prefix=prefix, value=station_to_value(station), original=m.group(0)))
        consumed_spans.append(m.span())

    for m in _BARE_RE.finditer(text):
        # Skip bare matches that overlap a prefixed match
        if any(start <= m.start() < end for start, end in consumed_spans):
            continue
        station = m.group("station")
        found.append(Station(prefix=None, value=station_to_value(station), original=m.group(0)))

    return found
