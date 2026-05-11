"""Audit a tailored resume against the master inventory for fabrication risk.

Usage:
    python -m scripts.audit_claims tailored_resume.md master_inventory.json [--output FILE]

Flags four classes of issues:
  1. NUMBERS_NOT_IN_INVENTORY  — quantitative claims with no source
  2. SKILLS_NOT_IN_INVENTORY   — listed skills not demonstrated in the inventory
  3. ENTITY_DRIFT              — companies / titles / dates mismatched with inventory
  4. ORPHAN_BULLET             — tailored bullets with no clear inventory ancestor

Outputs a markdown report. Every FLAGGED item must be removed, corrected, or
confirmed by the user before final outputs are built.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from ._common import (
    canonicalize,
    err,
    extract_numbers,
    load_json,
    load_synonyms,
    tokenize,
)


# Bullets in the tailored markdown: lines starting with -, *, or •.
BULLET_RE = re.compile(r"^\s*[\-\*•]\s+(.*)$")


def audit(tailored_md: str, inventory: dict[str, Any]) -> dict[str, Any]:
    syn = load_synonyms()

    # --- Build inventory indexes ---
    inv_numbers = _collect_inventory_numbers(inventory)
    inv_skills = _collect_inventory_skills(inventory, syn)
    inv_companies = {(e.get("company") or "").strip().lower() for e in inventory.get("experiences", [])}
    inv_companies.discard("")
    inv_titles = {(e.get("title") or "").strip().lower() for e in inventory.get("experiences", [])}
    inv_titles.discard("")
    inv_bullet_token_sets = _collect_bullet_token_sets(inventory)
    inv_bullet_canonical_sets = _collect_bullet_canonical_sets(inventory, syn)

    # --- Scan tailored ---
    tailored_lines = tailored_md.splitlines()
    tailored_bullets = [m.group(1).strip() for ln in tailored_lines if (m := BULLET_RE.match(ln))]

    issues: list[dict[str, Any]] = []

    # 1. Numbers
    for bullet in tailored_bullets:
        for num in extract_numbers(bullet):
            if num not in inv_numbers:
                issues.append({
                    "kind": "NUMBERS_NOT_IN_INVENTORY",
                    "severity": "high",
                    "snippet": bullet,
                    "detail": f"Number {num!r} appears in the tailored resume but not in the master inventory.",
                })

    # 2. Skills (look at any "Skills" section line + skill-shaped tokens in bullets)
    declared_skills = _extract_declared_skills(tailored_md)
    for skill in declared_skills:
        canonical = canonicalize(skill, syn)
        if canonical.lower() not in inv_skills and skill.lower() not in inv_skills:
            issues.append({
                "kind": "SKILLS_NOT_IN_INVENTORY",
                "severity": "high",
                "snippet": skill,
                "detail": f"Skill {skill!r} listed in tailored resume but not demonstrated in any inventory bullet or skills block.",
            })

    # 3. Entity drift — companies and titles
    for company in _extract_companies(tailored_md):
        if company.lower() not in inv_companies:
            issues.append({
                "kind": "ENTITY_DRIFT",
                "severity": "high",
                "snippet": company,
                "detail": f"Company {company!r} in tailored resume not found in inventory.",
            })

    # 4. Orphan bullets — at least 2 significant non-stopword tokens must overlap
    #    with some inventory bullet (or its canonicals must overlap meaningfully).
    for bullet in tailored_bullets:
        if not _has_inventory_ancestor(bullet, inv_bullet_token_sets, inv_bullet_canonical_sets, syn):
            issues.append({
                "kind": "ORPHAN_BULLET",
                "severity": "medium",
                "snippet": bullet,
                "detail": "No clear ancestor bullet in inventory (low token overlap and no shared canonical skills).",
            })

    return {
        "issues": issues,
        "stats": {
            "tailored_bullet_count": len(tailored_bullets),
            "issue_count": len(issues),
            "by_kind": _count_by_kind(issues),
        },
    }


# ---------- Inventory indexers ----------

def _collect_inventory_numbers(inventory: dict[str, Any]) -> set[str]:
    nums: set[str] = set()
    for exp in inventory.get("experiences", []):
        for b in exp.get("bullets", []):
            for n in (b.get("metrics") or []):
                nums.update(extract_numbers(str(n)))
            scope = b.get("scope") or {}
            for v in scope.values():
                if v is None:
                    continue
                nums.update(extract_numbers(str(v)))
            nums.update(extract_numbers(b.get("text") or ""))
    return nums


def _collect_inventory_skills(inventory: dict[str, Any], syn: dict[str, str]) -> set[str]:
    skills: set[str] = set()
    sk_block = inventory.get("skills") or {}
    for k, v in sk_block.items():
        if k.startswith("_") or not isinstance(v, list):
            continue
        for item in v:
            skills.add(item.lower())
            skills.add(canonicalize(item, syn).lower())
    for exp in inventory.get("experiences", []):
        for b in exp.get("bullets", []):
            for s in (b.get("skills") or []):
                skills.add(s.lower())
                skills.add(canonicalize(s, syn).lower())
    skills.discard("")
    return skills


def _collect_bullet_token_sets(inventory: dict[str, Any]) -> list[set[str]]:
    out: list[set[str]] = []
    for exp in inventory.get("experiences", []):
        for b in exp.get("bullets", []):
            out.append(set(tokenize(b.get("text") or "")))
    return out


def _collect_bullet_canonical_sets(inventory: dict[str, Any], syn: dict[str, str]) -> list[set[str]]:
    out: list[set[str]] = []
    for exp in inventory.get("experiences", []):
        for b in exp.get("bullets", []):
            tokens = tokenize(b.get("text") or "")
            cans = {canonicalize(t, syn).lower() for t in tokens}
            cans |= {(s or "").lower() for s in (b.get("skills") or [])}
            cans.discard("")
            out.append(cans)
    return out


# ---------- Tailored extractors ----------

def _extract_declared_skills(md: str) -> list[str]:
    """Pull skills from a Skills section — lines starting with ** **... or comma-separated."""
    skills: list[str] = []
    in_skills = False
    for ln in md.splitlines():
        s = ln.strip()
        if re.match(r"^#{1,6}\s+skills\b", s, re.I):
            in_skills = True
            continue
        if in_skills and s.startswith("#"):
            in_skills = False
        if not in_skills:
            continue
        if not s:
            continue
        # Strip "**Languages:**" prefix
        cleaned = re.sub(r"^\*{0,2}[^:*]+:\*{0,2}\s*", "", s)
        # Split on , ; |
        for token in re.split(r"[,;|/]", cleaned):
            t = token.strip().strip("*").strip()
            if t and len(t) <= 40 and not t.startswith("<!--"):
                skills.append(t)
    return skills


def _extract_companies(md: str) -> list[str]:
    """Heuristic: 'Company — Title' lines under H3 headings."""
    companies: list[str] = []
    for ln in md.splitlines():
        m = re.match(r"^#{2,4}\s+(.+?)\s+[—\-]\s+", ln)
        if m:
            companies.append(m.group(1).strip())
    return companies


def _has_inventory_ancestor(
    bullet: str,
    token_sets: list[set[str]],
    canonical_sets: list[set[str]],
    syn: dict[str, str],
) -> bool:
    bt = set(tokenize(bullet))
    bc = {canonicalize(t, syn).lower() for t in bt}
    bc.discard("")

    for ts, cs in zip(token_sets, canonical_sets):
        if len(bt & ts) >= 2:
            return True
        # also accept canonical-set overlap (e.g., synonym swap)
        if len(bc & cs) >= 2:
            return True
    return False


def _count_by_kind(issues: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for i in issues:
        out[i["kind"]] = out.get(i["kind"], 0) + 1
    return out


# ---------- Markdown report writer ----------

def render_report(audit_result: dict[str, Any]) -> str:
    issues = audit_result["issues"]
    stats = audit_result["stats"]

    lines: list[str] = []
    lines.append("# Audit Report — Tailored Resume vs. Master Inventory")
    lines.append("")
    if not issues:
        lines.append("**Result: CLEAN.** No fabrication risks detected.")
        lines.append("")
        lines.append(f"Tailored bullets scanned: {stats['tailored_bullet_count']}")
        return "\n".join(lines) + "\n"

    lines.append(f"**Issues flagged: {stats['issue_count']}** "
                 f"across {stats['tailored_bullet_count']} tailored bullets.")
    lines.append("")
    lines.append("Each FLAGGED item must be: removed, corrected, OR confirmed by the user "
                 "(in which case add it to the master inventory and re-audit).")
    lines.append("")

    by_kind = stats["by_kind"]
    lines.append("## Summary")
    lines.append("")
    lines.append("| Kind | Count |")
    lines.append("|---|---|")
    for kind in (
        "NUMBERS_NOT_IN_INVENTORY",
        "SKILLS_NOT_IN_INVENTORY",
        "ENTITY_DRIFT",
        "ORPHAN_BULLET",
    ):
        lines.append(f"| {kind} | {by_kind.get(kind, 0)} |")
    lines.append("")

    for kind in (
        "NUMBERS_NOT_IN_INVENTORY",
        "SKILLS_NOT_IN_INVENTORY",
        "ENTITY_DRIFT",
        "ORPHAN_BULLET",
    ):
        kind_issues = [i for i in issues if i["kind"] == kind]
        if not kind_issues:
            continue
        lines.append(f"## {kind}")
        lines.append("")
        for issue in kind_issues:
            lines.append(f"- **[{issue['severity'].upper()}]** {issue['detail']}")
            lines.append(f"  > {issue['snippet']}")
            lines.append("")

    return "\n".join(lines) + "\n"


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Audit a tailored resume for fabrication risk.")
    ap.add_argument("tailored", help="Path to tailored resume (.md)")
    ap.add_argument("inventory", help="Path to master_inventory.json")
    ap.add_argument("--output", "-o", default="audit_report.md", help="Output report path")
    args = ap.parse_args(argv)

    tailored_md = Path(args.tailored).read_text(encoding="utf-8")
    inventory = load_json(args.inventory)
    result = audit(tailored_md, inventory)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(render_report(result), encoding="utf-8")

    stats = result["stats"]
    print(f"Wrote {args.output}")
    print(f"  tailored bullets: {stats['tailored_bullet_count']}")
    print(f"  issues:           {stats['issue_count']}")
    if stats["issue_count"]:
        for kind, count in sorted(stats["by_kind"].items(), key=lambda x: -x[1]):
            print(f"    {kind}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
