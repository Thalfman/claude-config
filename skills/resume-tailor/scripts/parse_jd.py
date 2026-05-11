"""Parse a job description into structured analysis JSON.

Usage:
    python -m scripts.parse_jd <path_or_text> [--output FILE]
    python -m scripts.parse_jd ./posting.pdf --output jd_analysis.json
    python -m scripts.parse_jd "Senior Backend Engineer ..." --output jd_analysis.json

The parser is heuristic. It will miss things and over-extract things. The
SKILL.md workflow tells Claude (or the user) to verify the result before
moving to relevance scoring.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from . import _common
from ._common import (
    canonicalize,
    err,
    load_synonyms,
    read_text_input,
    save_json,
)


# ---------- Section detection ----------

# Patterns ranked roughly by specificity. First match per line wins.
SECTION_HEADERS: dict[str, re.Pattern[str]] = {
    "required":     re.compile(r"^\s*(required|must[\s-]?have|minimum|basic)\s*(qualifications?|requirements?|skills?|experience)?\s*[:.]?\s*$", re.I),
    "preferred":    re.compile(r"^\s*(preferred|nice[\s-]?to[\s-]?have|bonus|plus|desirable|ideal)\s*(qualifications?|skills?|experience)?\s*[:.]?\s*$", re.I),
    "responsibilities": re.compile(r"^\s*(responsibilities|what\s+you('?ll|\s+will)\s+do|the\s+role|your\s+role|day[\s-]?to[\s-]?day|duties|key\s+responsibilities)\s*[:.]?\s*$", re.I),
    "about":        re.compile(r"^\s*(about\s+(us|the\s+role|the\s+team|the\s+company|the\s+job)|company\s+overview|who\s+we\s+are)\s*[:.]?\s*$", re.I),
    "benefits":     re.compile(r"^\s*(benefits|perks|compensation|what\s+we\s+offer|why\s+(join|work)\s+(us|here))\s*[:.]?\s*$", re.I),
    "qualifications": re.compile(r"^\s*(qualifications?|requirements?|what\s+you('?ll|\s+will)\s+bring|what\s+we('?re|\s+are)\s+looking\s+for|skills?\s+and\s+experience|you\s+have)\s*[:.]?\s*$", re.I),
}

# Sentence-level cues for required/preferred when no section header is present.
REQUIRED_CUE = re.compile(r"\b(required|must\s+have|need|minimum|at\s+least|\d+\+?\s+years)\b", re.I)
PREFERRED_CUE = re.compile(r"\b(preferred|nice\s+to\s+have|bonus|plus|ideally|familiarity\s+with|exposure\s+to|a\s+plus)\b", re.I)

# ---------- Level inference ----------

LEVEL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("director",        re.compile(r"\b(director|head\s+of|vp\b|vice\s+president|chief\b|cto|cio|ceo|cpo)\b", re.I)),
    ("principal",       re.compile(r"\bprincipal\b", re.I)),
    ("staff",           re.compile(r"\b(staff|architect)\b", re.I)),
    ("senior",          re.compile(r"\b(senior|sr\.?|lead|tech\s+lead)\b", re.I)),
    ("junior",          re.compile(r"\b(junior|jr\.?|entry[\s-]?level|associate|new\s+grad|recent\s+grad|level\s*[I1]\b|graduate)\b", re.I)),
    ("intern",          re.compile(r"\b(intern|internship|co[\s-]?op)\b", re.I)),
]

YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*years?", re.I)

# ---------- Dealbreakers ----------

DEALBREAKER_PATTERNS: dict[str, re.Pattern[str]] = {
    "clearance":   re.compile(r"\b(security\s+clearance|secret\s+clearance|top\s+secret|TS/SCI|clearance\s+required)\b", re.I),
    "citizenship": re.compile(r"\b(US\s+citizen|citizenship\s+required|no\s+sponsorship|cannot\s+sponsor|unable\s+to\s+sponsor)\b", re.I),
    "onsite":      re.compile(r"\b(on[\s-]?site|in[\s-]?office|in\s+person|hybrid\s+\d|days?\s+(per|/)?\s*week\s+in\s+office)\b", re.I),
    "travel":      re.compile(r"\b(\d{1,2}\s*%\s+travel|travel\s+\d{1,2}\s*%|frequent\s+travel|extensive\s+travel)\b", re.I),
    "shift":       re.compile(r"\b(night\s+shift|on[\s-]?call\s+rotation|24/7|shift\s+work|weekends\s+required)\b", re.I),
}


def parse_jd(text: str) -> dict[str, Any]:
    """Run the full JD analysis pipeline and return the analysis dict."""
    text = text.strip()
    if not text:
        return _empty_analysis()

    sections = _sectionize(text)
    role_title = _infer_role_title(text)
    level = _infer_level(role_title or "", text, sections)

    required = _extract_bullets(sections.get("required", []) + sections.get("qualifications", []))
    preferred = _extract_bullets(sections.get("preferred", []))
    # Sentence-cue split if no preferred section was found.
    if not preferred and "qualifications" in sections:
        cued_required, cued_preferred = _split_by_cues(sections["qualifications"])
        # Only override required if cue-split actually found splits.
        if cued_preferred:
            required = cued_required
            preferred = cued_preferred

    responsibilities = _extract_bullets(sections.get("responsibilities", []))

    keywords = _extract_keywords(text)
    dealbreakers = _detect_dealbreakers(text)

    return {
        "role_title": role_title,
        "level": level,
        "required": required,
        "preferred": preferred,
        "responsibilities": responsibilities,
        "keywords": keywords,
        "dealbreakers": dealbreakers,
        "_raw_text_length": len(text),
        "_section_keys_found": sorted(sections.keys()),
        "_disclaimer": "Heuristic extraction. Verify before scoring relevance.",
    }


# ---------- Internal helpers ----------

def _empty_analysis() -> dict[str, Any]:
    return {
        "role_title": None,
        "level": None,
        "required": [],
        "preferred": [],
        "responsibilities": [],
        "keywords": [],
        "dealbreakers": {},
        "_raw_text_length": 0,
        "_section_keys_found": [],
        "_disclaimer": "Empty input.",
    }


def _sectionize(text: str) -> dict[str, list[str]]:
    """Walk lines top-to-bottom; assign each line to the most-recent header bucket."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    sections: dict[str, list[str]] = {}
    current = "header"
    sections[current] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            sections[current].append(line)
            continue
        matched_section = None
        for sec_name, pat in SECTION_HEADERS.items():
            if pat.match(stripped):
                matched_section = sec_name
                break
        if matched_section:
            current = matched_section
            sections.setdefault(current, [])
        else:
            sections[current].append(line)
    return sections


def _infer_role_title(text: str) -> str | None:
    """Heuristic: first non-empty line ≤ 80 chars that looks title-cased / role-y."""
    role_words = (
        "engineer", "developer", "scientist", "analyst", "manager", "designer",
        "architect", "director", "lead", "specialist", "consultant", "technician",
        "administrator", "coordinator", "officer", "associate", "intern",
        "drafter", "estimator", "permitting", "permitter", "project",
    )
    for line in text.splitlines()[:25]:
        s = line.strip()
        if not s or len(s) > 80:
            continue
        if any(w in s.lower() for w in role_words):
            # Strip leading "Title:" prefix if present
            s = re.sub(r"^(?:job\s+title|title|position|role)\s*:\s*", "", s, flags=re.I)
            return s
    return None


def _infer_level(title: str, text: str, sections: dict[str, list[str]]) -> str | None:
    """Combine title patterns + 'X+ years' cues to guess level."""
    haystack = title + "\n" + text
    for level, pat in LEVEL_PATTERNS:
        if pat.search(haystack):
            return level

    # Fall back to years-based heuristic
    years_hits = [int(m.group(1)) for m in YEARS_RE.finditer(text)]
    if not years_hits:
        return None
    max_years = max(years_hits)
    if max_years >= 10:
        return "staff"
    if max_years >= 6:
        return "senior"
    if max_years >= 3:
        return "mid"
    return "junior"


def _extract_bullets(lines: list[str]) -> list[str]:
    """Pull bulleted/numbered/standalone-sentence items from a section."""
    out: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            joined = " ".join(b.strip() for b in buf).strip()
            if joined:
                out.append(joined)
            buf.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        # Bullet markers
        if re.match(r"^[\-\*•·▪◦‣⁃]\s+", stripped) or re.match(r"^\d+[.)]\s+", stripped):
            flush()
            buf.append(re.sub(r"^[\-\*•·▪◦‣⁃]\s+|^\d+[.)]\s+", "", stripped))
        else:
            # continuation line, but only if it looks like a continuation (lowercase start
            # or starts with conjunction). Otherwise treat as new sentence.
            if buf and (stripped[0].islower() or stripped.startswith(("and ", "or ", "with "))):
                buf.append(stripped)
            else:
                flush()
                # capture as-is if it ends with a sentence terminator
                if stripped.endswith((".", "!", "?")) or len(stripped) > 30:
                    out.append(stripped)
                else:
                    buf.append(stripped)
    flush()
    # de-duplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for s in out:
        key = re.sub(r"\s+", " ", s.lower())
        if key not in seen:
            seen.add(key)
            deduped.append(s)
    return deduped


def _split_by_cues(lines: list[str]) -> tuple[list[str], list[str]]:
    """When we have a generic 'qualifications' block, split by required vs preferred sentence cues."""
    bullets = _extract_bullets(lines)
    required: list[str] = []
    preferred: list[str] = []
    for b in bullets:
        if PREFERRED_CUE.search(b) and not REQUIRED_CUE.search(b):
            preferred.append(b)
        else:
            required.append(b)
    return required, preferred


def _extract_keywords(text: str) -> list[dict[str, Any]]:
    """Match against synonyms.json keys to find recognized tech/skill keywords.

    Returns each keyword once, with a count of mentions and the section
    (if any) where it first appeared. Sorted by count descending.
    """
    syn = load_synonyms()
    text_lower = text.lower()
    counts: dict[str, int] = {}
    for alias, canonical in syn.items():
        # Use word-boundary match unless the alias contains tech punctuation.
        if any(c in alias for c in "+#./"):
            n = text_lower.count(alias)
        else:
            n = len(re.findall(rf"\b{re.escape(alias)}\b", text_lower))
        if n > 0:
            counts[canonical] = max(counts.get(canonical, 0), n)
    items = [{"keyword": k, "count": v} for k, v in counts.items()]
    items.sort(key=lambda x: (-x["count"], x["keyword"].lower()))
    return items


def _detect_dealbreakers(text: str) -> dict[str, str]:
    """Surface any dealbreaker patterns hit in the text."""
    out: dict[str, str] = {}
    for name, pat in DEALBREAKER_PATTERNS.items():
        m = pat.search(text)
        if m:
            out[name] = m.group(0)
    return out


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Parse a job description into structured JSON.")
    ap.add_argument("input", help="Path to JD file (.txt/.md/.pdf/.docx) or inline JD text")
    ap.add_argument("--output", "-o", default="jd_analysis.json", help="Output JSON path")
    args = ap.parse_args(argv)

    text = read_text_input(args.input)
    if not text.strip():
        err("No JD text found.")
        return 2

    analysis = parse_jd(text)
    save_json(analysis, args.output)
    print(f"Wrote {args.output}")
    print(f"  role_title:       {analysis['role_title']}")
    print(f"  level:            {analysis['level']}")
    print(f"  required count:   {len(analysis['required'])}")
    print(f"  preferred count:  {len(analysis['preferred'])}")
    print(f"  responsibilities: {len(analysis['responsibilities'])}")
    print(f"  keywords:         {len(analysis['keywords'])}")
    if analysis["dealbreakers"]:
        print(f"  dealbreakers:     {list(analysis['dealbreakers'].keys())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
