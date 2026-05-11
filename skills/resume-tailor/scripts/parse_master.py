"""Helper for normalizing a master resume into the inventory schema.

This script does the format-conversion bit (read .docx/.pdf/.md to text) and
emits a *partial* inventory skeleton that captures section breaks and obvious
job blocks. It is intentionally conservative — Claude / the user fills in the
structured details (skills, scope, metrics) that the script can't reliably
extract.

Usage:
    python -m scripts.parse_master <path> [--output FILE]

The output is a partial inventory JSON that matches templates/resume_master_starter.json
where possible, with TODOs where information needs human judgment.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from ._common import err, read_text_input, save_json


HEADER_PATTERNS: dict[str, re.Pattern[str]] = {
    "experience": re.compile(r"^\s*(work\s+)?experience|professional\s+experience|employment(\s+history)?\s*$", re.I),
    "education":  re.compile(r"^\s*education\s*$", re.I),
    "skills":     re.compile(r"^\s*(technical\s+)?skills(\s+and\s+(tools|technologies))?\s*$", re.I),
    "certs":      re.compile(r"^\s*(certifications?|licenses?\s+and\s+certifications?)\s*$", re.I),
    "projects":   re.compile(r"^\s*(projects?|selected\s+projects?|side\s+projects?)\s*$", re.I),
    "summary":    re.compile(r"^\s*(summary|profile|professional\s+summary|about\s+me|objective)\s*$", re.I),
    "publications": re.compile(r"^\s*(publications?|talks?|presentations?)\s*$", re.I),
    "awards":     re.compile(r"^\s*(awards?|honors?|recognitions?)\s*$", re.I),
}

DATE_RANGE_RE = re.compile(
    r"""
    (?P<start>
        (?:\d{4}|\d{1,2}/\d{4}|[A-Z][a-z]{2,8}\.?\s+\d{4}|[A-Z][a-z]{2,8}\.?\s*'?\d{2,4})
    )
    \s*[-–—to]+\s*
    (?P<end>
        (?:\d{4}|\d{1,2}/\d{4}|[A-Z][a-z]{2,8}\.?\s+\d{4}|[A-Z][a-z]{2,8}\.?\s*'?\d{2,4}|present|current|now)
    )
    """,
    re.VERBOSE | re.I,
)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,2}\s*)?(?:\(\d{3}\)\s*|\d{3}[\-.\s])\d{3}[\-.\s]?\d{4}")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/[A-Za-z0-9\-_/]+", re.I)
GITHUB_RE = re.compile(r"github\.com/[A-Za-z0-9\-_/.]+", re.I)


def normalize_master(text: str) -> dict[str, Any]:
    """Build a partial inventory skeleton from a resume text blob."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    sections = _sectionize(lines)

    candidate = _extract_candidate(lines[:20], text)
    summary = _extract_summary(sections.get("summary", []))
    experiences = _extract_experiences(sections.get("experience", []))
    education = _extract_education(sections.get("education", []))
    certifications = _extract_certifications(sections.get("certs", []))
    skills = _extract_skills(sections.get("skills", []))
    projects = _extract_projects(sections.get("projects", []))

    return {
        "_schema_version": "1.0",
        "_source": "parse_master.py (heuristic extraction — fill TODO fields manually)",
        "candidate": candidate,
        "summary": summary,
        "experiences": experiences,
        "education": education,
        "certifications": certifications,
        "skills": skills,
        "projects": projects,
        "publications_talks": [],
        "awards": [],
        "languages_spoken": [],
        "preferences": {
            "target_roles": [],
            "target_industries": [],
            "deal_breakers": [],
            "voice": "TODO: describe your preferred voice",
        },
        "_user_notes": "",
    }


def _sectionize(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"_header": []}
    current = "_header"
    for line in lines:
        s = line.strip()
        matched = None
        for name, pat in HEADER_PATTERNS.items():
            if pat.match(s):
                matched = name
                break
        if matched:
            current = matched
            sections.setdefault(current, [])
        else:
            sections[current].append(line)
    return sections


def _extract_candidate(top_lines: list[str], full_text: str) -> dict[str, Any]:
    name = None
    for ln in top_lines:
        s = ln.strip()
        if not s:
            continue
        # name heuristic: 2-4 capitalized words, no "@", no digits
        if (
            "@" not in s and not any(c.isdigit() for c in s)
            and 1 <= len(s.split()) <= 4
            and all(w[:1].isupper() for w in s.split() if w)
        ):
            name = s
            break

    email_m = EMAIL_RE.search(full_text)
    phone_m = PHONE_RE.search(full_text)
    li_m = LINKEDIN_RE.search(full_text)
    gh_m = GITHUB_RE.search(full_text)

    return {
        "name": name or "TODO",
        "headline": None,
        "email": email_m.group(0) if email_m else "TODO",
        "phone": phone_m.group(0) if phone_m else "TODO",
        "location": "TODO",
        "links": {
            "linkedin": li_m.group(0) if li_m else None,
            "github": gh_m.group(0) if gh_m else None,
            "portfolio": None,
            "other": [],
        },
        "work_authorization": None,
        "willing_to_relocate": None,
        "remote_preference": None,
    }


def _extract_summary(lines: list[str]) -> str | None:
    text = " ".join(ln.strip() for ln in lines if ln.strip())
    return text or None


def _extract_experiences(lines: list[str]) -> list[dict[str, Any]]:
    """Group bullet lines under inferred (company, title, dates) headers."""
    experiences: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def flush() -> None:
        if current is not None and (current["bullets"] or current["title"] or current["company"]):
            experiences.append(current)

    for line in lines:
        s = line.strip()
        if not s:
            continue

        date_m = DATE_RANGE_RE.search(s)
        is_bullet = bool(re.match(r"^[\-\*•·▪◦‣⁃]\s+|^\d+[.)]\s+", s))

        if date_m and not is_bullet:
            flush()
            cleaned = (s[: date_m.start()] + s[date_m.end():]).strip(" |·,—–-")
            company, title = _split_company_title(cleaned)
            current = {
                "company": company,
                "title": title,
                "location": "TODO",
                "start": date_m.group("start").strip(),
                "end": date_m.group("end").strip(),
                "context": "TODO",
                "bullets": [],
            }
        elif is_bullet:
            text = re.sub(r"^[\-\*•·▪◦‣⁃]\s+|^\d+[.)]\s+", "", s)
            if current is None:
                current = {
                    "company": "TODO",
                    "title": "TODO",
                    "location": "TODO",
                    "start": "TODO",
                    "end": "TODO",
                    "context": "TODO",
                    "bullets": [],
                }
            current["bullets"].append({
                "text": text,
                "verbs": _guess_verbs(text),
                "scope": {"team_size": None, "scale": None, "duration": None, "users": None, "geography": None},
                "metrics": _guess_metrics(text),
                "skills": [],
                "tags": [],
            })
        else:
            # title-only or company-only line; attach to current header if open
            if current and not current.get("company"):
                current["company"] = s
            elif current and not current.get("title"):
                current["title"] = s
    flush()
    return experiences


def _split_company_title(s: str) -> tuple[str, str]:
    for sep in (" — ", " – ", " | ", " - ", ", "):
        if sep in s:
            a, b = s.split(sep, 1)
            return a.strip(), b.strip()
    return s.strip(), "TODO"


def _guess_verbs(text: str) -> list[str]:
    first_word = (text.split() or [""])[0].rstrip(",.;:")
    return [first_word.lower()] if first_word.isalpha() else []


def _guess_metrics(text: str) -> list[str]:
    from ._common import extract_numbers
    return extract_numbers(text)


def _extract_education(lines: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        year_m = re.search(r"\b(19|20)\d{2}\b", s)
        out.append({
            "school": s,
            "degree": "TODO",
            "field": "TODO",
            "graduated": year_m.group(0) if year_m else "TODO",
            "gpa": None,
            "honors": None,
            "location": None,
            "relevant_coursework": [],
        })
    return out


def _extract_certifications(lines: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in lines:
        s = re.sub(r"^[\-\*•·▪◦‣⁃]\s+|^\d+[.)]\s+", "", line.strip())
        if not s:
            continue
        year_m = re.search(r"\b(19|20)\d{2}\b", s)
        out.append({
            "name": s,
            "issuer": "TODO",
            "year": year_m.group(0) if year_m else None,
            "expires": None,
            "id": None,
        })
    return out


def _extract_skills(lines: list[str]) -> dict[str, Any]:
    """Best-effort: split by category labels, fall back to a flat 'tools' list."""
    out: dict[str, list[str]] = {
        "languages": [], "frameworks": [], "databases": [],
        "cloud": [], "tools": [], "domains": [],
    }
    for line in lines:
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^([\w /]+?)\s*[:\-]\s*(.+)$", s)
        if m:
            label = m.group(1).strip().lower()
            items = [t.strip() for t in re.split(r"[,;|/]", m.group(2)) if t.strip()]
            bucket = _map_skill_label_to_bucket(label)
            out[bucket].extend(items)
        else:
            items = [t.strip() for t in re.split(r"[,;|/]", s) if t.strip()]
            out["tools"].extend(items)
    out["_note"] = "Verify and re-bucket. parse_master.py uses keyword heuristics."
    return out


def _map_skill_label_to_bucket(label: str) -> str:
    if "lang" in label:
        return "languages"
    if "framework" in label or "library" in label:
        return "frameworks"
    if "db" in label or "data" in label or "storage" in label:
        return "databases"
    if "cloud" in label or "infra" in label or "devops" in label:
        return "cloud"
    if "domain" in label or "industr" in label:
        return "domains"
    return "tools"


def _extract_projects(lines: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in lines:
        s = line.strip()
        if not s:
            continue
        is_bullet = bool(re.match(r"^[\-\*•·▪◦‣⁃]\s+|^\d+[.)]\s+", s))
        if not is_bullet:
            if current:
                out.append(current)
            current = {
                "name": s,
                "year": None,
                "description": "",
                "skills": [],
                "link": None,
                "context": None,
            }
        else:
            txt = re.sub(r"^[\-\*•·▪◦‣⁃]\s+|^\d+[.)]\s+", "", s)
            if current is None:
                current = {"name": "TODO", "year": None, "description": txt, "skills": [], "link": None, "context": None}
            else:
                current["description"] = (current["description"] + " " + txt).strip()
    if current:
        out.append(current)
    return out


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Normalize a master resume into a partial inventory JSON.")
    ap.add_argument("input", help="Path to master resume (.md/.pdf/.docx/.txt)")
    ap.add_argument("--output", "-o", default="master_inventory.json", help="Output JSON path")
    args = ap.parse_args(argv)

    text = read_text_input(args.input)
    if not text.strip():
        err("No master resume text found.")
        return 2

    inventory = normalize_master(text)
    save_json(inventory, args.output)

    todo_count = json.dumps(inventory).count('"TODO"')
    print(f"Wrote {args.output}")
    print(f"  experiences: {len(inventory['experiences'])}")
    print(f"  education:   {len(inventory['education'])}")
    print(f"  certs:       {len(inventory['certifications'])}")
    print(f"  TODOs to fill: {todo_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
