"""Score the master inventory's bullets against each JD requirement.

Usage:
    python -m scripts.score_relevance master_inventory.json jd_analysis.json [--output FILE]

For each JD requirement (required + preferred), pick the top-N bullets from the
inventory ranked by:
    - Direct skill match (skill in bullet.skills matches a JD keyword)        +10
    - Synonym match (resolves to same canonical via synonyms.json)             +6
    - Token overlap between bullet text and requirement text                   +1 per significant token, cap +5
    - Recency boost (job ended <= 3 years ago, or is current)                  +2
    - Verb match (action verb in bullet.verbs is mentioned in requirement)     +2

Coverage labels:
    STRONG  if top score >= 12
    PARTIAL if top score in 5..11
    GAP     otherwise

Outputs relevance.json with per-requirement evidence and aggregate stats.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from ._common import (
    canonicalize,
    err,
    load_json,
    load_synonyms,
    save_json,
    tokenize,
)


# Tokens that aren't useful for matching (extend as needed).
STOPWORDS = {
    "a", "an", "the", "of", "and", "or", "for", "to", "in", "on", "at", "by",
    "with", "from", "as", "is", "are", "be", "been", "being", "this", "that",
    "these", "those", "we", "you", "your", "our", "their", "they", "i",
    "have", "has", "had", "do", "does", "did", "will", "would", "should",
    "could", "may", "might", "can", "must", "than", "then", "into", "over",
    "experience", "work", "working", "skills", "ability", "able", "strong",
    "good", "great", "excellent", "deep", "solid", "proven", "minimum",
    "year", "years", "plus", "preferred", "required", "must", "have",
    "such", "etc", "including", "include", "any", "some", "all", "many",
}


def score_relevance(inventory: dict[str, Any], jd: dict[str, Any]) -> dict[str, Any]:
    syn = load_synonyms()
    today = date.today()

    requirements = _normalize_requirements(jd)
    bullets = _flatten_bullets(inventory, today, syn)

    scored_requirements: list[dict[str, Any]] = []
    for req in requirements:
        req_tokens = _significant_tokens(req["text"])
        req_keyword_canonicals = {
            canonicalize(t, syn) for t in req_tokens if canonicalize(t, syn) != t
        } | {canonicalize(t, syn) for t in tokenize(req["text"])}
        req_keyword_canonicals = {k for k in req_keyword_canonicals if k}
        req_verbs = _verbs_in_text(req["text"])

        scored_bullets: list[dict[str, Any]] = []
        for b in bullets:
            score = 0
            reasons: list[str] = []

            # 1. Direct skill match
            skill_matches = req_keyword_canonicals & b["skill_canonicals"]
            if skill_matches:
                score += 10 * len(skill_matches)
                reasons.append(f"skill match: {sorted(skill_matches)}")

            # 2. Synonym match (canonical equivalence beyond direct skill listing)
            extra_canonicals = req_keyword_canonicals & b["text_canonicals"]
            extra = extra_canonicals - skill_matches
            if extra:
                score += 6 * len(extra)
                reasons.append(f"synonym: {sorted(extra)}")

            # 3. Token overlap (capped)
            overlap = req_tokens & b["text_tokens"]
            if overlap:
                bonus = min(len(overlap), 5)
                score += bonus
                reasons.append(f"+{bonus} token overlap ({sorted(overlap)[:5]})")

            # 4. Recency
            if b["recent"]:
                score += 2
                reasons.append("recent role")

            # 5. Verb match
            verb_overlap = req_verbs & b["verbs"]
            if verb_overlap:
                score += 2
                reasons.append(f"verb: {sorted(verb_overlap)}")

            if score > 0:
                scored_bullets.append({
                    "bullet_text": b["text"],
                    "company": b["company"],
                    "title": b["title"],
                    "score": score,
                    "reasons": reasons,
                })

        scored_bullets.sort(key=lambda x: -x["score"])
        top = scored_bullets[:5]
        top_score = top[0]["score"] if top else 0
        coverage = "STRONG" if top_score >= 12 else ("PARTIAL" if top_score >= 5 else "GAP")

        scored_requirements.append({
            "requirement": req["text"],
            "kind": req["kind"],
            "coverage": coverage,
            "top_score": top_score,
            "evidence": top,
        })

    summary = _summarize(scored_requirements)
    return {
        "requirements": scored_requirements,
        "summary": summary,
        "_disclaimer": "Heuristic scoring. Coverage labels are starting points — review with the user.",
    }


# ---------- Helpers ----------

def _normalize_requirements(jd: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for r in jd.get("required", []):
        out.append({"text": r, "kind": "required"})
    for r in jd.get("preferred", []):
        out.append({"text": r, "kind": "preferred"})
    # Optionally also score against responsibilities (sometimes the only signal)
    for r in jd.get("responsibilities", []):
        out.append({"text": r, "kind": "responsibility"})
    return out


def _flatten_bullets(inventory: dict[str, Any], today: date, syn: dict[str, str]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for exp in inventory.get("experiences", []):
        company = exp.get("company") or ""
        title = exp.get("title") or ""
        recent = _is_recent(exp.get("end"), today)
        for b in exp.get("bullets", []):
            text = b.get("text") or ""
            skills = b.get("skills") or []
            verbs = set(v.lower() for v in (b.get("verbs") or []))
            tokens = set(tokenize(text)) - STOPWORDS
            text_canonicals = {canonicalize(t, syn) for t in tokens}
            text_canonicals = {c for c in text_canonicals if c and c != ""}
            skill_canonicals = {canonicalize(s, syn) for s in skills}
            flat.append({
                "text": text,
                "company": company,
                "title": title,
                "recent": recent,
                "verbs": verbs,
                "text_tokens": tokens,
                "text_canonicals": skill_canonicals | text_canonicals,
                "skill_canonicals": skill_canonicals,
            })
    return flat


def _is_recent(end: str | None, today: date) -> bool:
    if not end:
        return False
    s = str(end).strip().lower()
    if s in {"present", "current", "now", ""}:
        return True
    m = re.match(r"(\d{4})", s)
    if not m:
        m = re.search(r"(\d{4})", s)
    if not m:
        return False
    year = int(m.group(1))
    return (today.year - year) <= 3


def _significant_tokens(text: str) -> set[str]:
    return set(t for t in tokenize(text) if t not in STOPWORDS and len(t) > 1)


def _verbs_in_text(text: str) -> set[str]:
    """Best-effort: pull the action verbs we care about from a requirement string."""
    verbs = {
        "build", "design", "develop", "lead", "drive", "own", "ship", "deliver",
        "improve", "reduce", "scale", "optimize", "architect", "implement",
        "manage", "mentor", "coach", "review", "test", "automate", "integrate",
        "deploy", "monitor", "operate", "analyze", "investigate", "research",
        "communicate", "collaborate", "partner", "support", "present", "document",
    }
    found = set()
    lowered = text.lower()
    for v in verbs:
        if re.search(rf"\b{v}(?:s|ed|ing)?\b", lowered):
            found.add(v)
    return found


def _summarize(requirements: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(requirements)
    strong = sum(1 for r in requirements if r["coverage"] == "STRONG")
    partial = sum(1 for r in requirements if r["coverage"] == "PARTIAL")
    gap = sum(1 for r in requirements if r["coverage"] == "GAP")
    required = [r for r in requirements if r["kind"] == "required"]
    required_strong = sum(1 for r in required if r["coverage"] == "STRONG")
    required_partial = sum(1 for r in required if r["coverage"] == "PARTIAL")
    required_gap = sum(1 for r in required if r["coverage"] == "GAP")
    return {
        "total_requirements": total,
        "strong": strong,
        "partial": partial,
        "gap": gap,
        "required_total": len(required),
        "required_strong": required_strong,
        "required_partial": required_partial,
        "required_gap": required_gap,
        "required_coverage_pct": (
            round(100 * (required_strong + 0.5 * required_partial) / max(1, len(required)), 1)
        ),
    }


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score master inventory bullets against JD requirements.")
    ap.add_argument("inventory", help="Path to master_inventory.json")
    ap.add_argument("jd", help="Path to jd_analysis.json")
    ap.add_argument("--output", "-o", default="relevance.json", help="Output JSON path")
    args = ap.parse_args(argv)

    inventory = load_json(args.inventory)
    jd = load_json(args.jd)
    relevance = score_relevance(inventory, jd)
    save_json(relevance, args.output)

    s = relevance["summary"]
    print(f"Wrote {args.output}")
    print(f"  required:  {s['required_strong']}/{s['required_total']} STRONG, "
          f"{s['required_partial']} PARTIAL, {s['required_gap']} GAP "
          f"({s['required_coverage_pct']}% weighted coverage)")
    print(f"  total:     {s['strong']} STRONG, {s['partial']} PARTIAL, {s['gap']} GAP "
          f"of {s['total_requirements']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
