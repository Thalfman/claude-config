"""
Pre-flight render linter — last gate before shipping a permit package.

Scans every reviewer-facing markdown file in the output tree for content that
should never reach a permit reviewer: internal QC tags, status banners,
skill-author scaffolding language, and bureaucratic enclosure narratives the
iron-rule discipline rejects.

Reviewer-facing files (scanned by default):
  output/<JB>/<entity>/cover_letter.md
  output/<JB>/<entity>/application_form.md
  output/<JB>/<entity>/fee_calculation.md
  output/<JB>/<entity>/transmittal*.md

Internal files (skipped by default; pass --strict to also scan):
  output/<JB>/job_aid.md, submission_order.md   (submitter-only)
  output/MASTER_TRACKER.md                       (internal dashboard)
  output/<JB>/project_facts.json                 (data, not prose)
  output/<JB>/<entity>/qc_report.md              (intentionally internal)

Pattern catalog
---------------
HARD failures (always exit nonzero):
  PFL-QC-TAG       Internal QC tag like 'QC-001' leaked into reviewer copy.
  PFL-STATUS-BANNER 'Status: Placeholder|Estimate|Prefill draft|...' banner.
  PFL-FIELD-SCAN   'Field-completeness scan' internal heading.
  PFL-VERIFY-NOTE  'Verify before submission' skill-author note.
  PFL-TODO         'TODO', 'FIXME', 'TBD', 'XXX' marker.
  PFL-BP-CODE      Boilerplate signal code 'BP-001' / 'BP-002' / etc.
  PFL-INTERNAL-TERM Internal scripting term like 'scrub_cd', 'open_questions'.
  PFL-STUB         Word 'stub' used as a status label.

SOFT findings (warn; --strict promotes to failures):
  PFL-NARRATIVE-OF-ENCLOSURE  Bureaucratic filler ('We are pleased to enclose',
                              'Please find enclosed', 'Pursuant to your
                              request', 'Attached for your review', etc.).

Whitelist
---------
The placeholder `(pending)` is the SKILL.md iron-rule sentinel for unknown
slots and is explicitly NOT flagged.

CLI
---
    python -m scripts.preflight_lint --root output/
    python -m scripts.preflight_lint --package-dir output/JB0002431561/Kent_CRC/
    python -m scripts.preflight_lint --root output/ --strict
    python -m scripts.preflight_lint --root output/ --json findings.json

Exit code: 0 = clean, 1 = HARD findings present (or any in --strict mode).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Pattern catalog
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Pattern:
    code: str
    severity: str           # 'hard' | 'soft'
    regex: re.Pattern
    why: str


PATTERNS: list[Pattern] = [
    Pattern("PFL-QC-TAG", "hard",
            re.compile(r"\bQC-\d{3}\b"),
            "Internal QC tag must not appear in reviewer-facing copy."),
    Pattern("PFL-STATUS-BANNER", "hard",
            re.compile(r"(?im)^\s*\**\s*Status:\s*(Placeholder|Estimate|Prefill\s+draft|Stub|Draft|TODO|TBD)\b"),
            "Internal status banner — output should be final or use the (pending) sentinel."),
    Pattern("PFL-FIELD-SCAN", "hard",
            re.compile(r"(?i)Field[- ]completeness scan"),
            "Internal QC heading; remove from reviewer-facing files."),
    Pattern("PFL-VERIFY-NOTE", "hard",
            re.compile(r"(?i)\bVerify before submission\b"),
            "Skill-author reminder; not for the reviewer."),
    Pattern("PFL-TODO", "hard",
            re.compile(r"\b(TODO|FIXME|TBD|XXX)\b"),
            "Open marker that must be resolved before shipping."),
    Pattern("PFL-BP-CODE", "hard",
            re.compile(r"\bBP-\d{3}\b"),
            "Boilerplate signal code is internal taxonomy."),
    Pattern("PFL-INTERNAL-TERM", "hard",
            re.compile(r"\b(scrub_cd|extract_project_facts|build_master_tracker|render_application_form|open_questions?|boilerplate_signals?)\b"),
            "Internal script or schema name leaked into reviewer copy."),
    Pattern("PFL-STUB", "hard",
            re.compile(r"(?i)\bstub\b"),
            "Word 'stub' indicates incomplete content."),
    Pattern("PFL-NARRATIVE-OF-ENCLOSURE", "soft",
            re.compile(r"(?i)\b("
                       r"we\s+are\s+pleased\s+to\s+enclose"
                       r"|please\s+find\s+(enclosed|attached)"
                       r"|enclosed\s+please\s+find"
                       r"|attached\s+please\s+find"
                       r"|find\s+herewith"
                       r"|pursuant\s+to\s+your\s+request"
                       r"|attached\s+for\s+your\s+review"
                       r"|please\s+do\s+not\s+hesitate\s+to\s+contact"
                       r")\b"),
            "Bureaucratic filler; iron-rule discipline strips this out."),
]


REVIEWER_FACING_GLOBS = (
    "JB*/**/cover_letter.md",
    "JB*/**/application_form.md",
    "JB*/**/fee_calculation.md",
    "JB*/**/transmittal*.md",
)

# Files explicitly internal — never scanned even in --strict.
INTERNAL_NEVER_SCAN = {
    "MASTER_TRACKER.md",
    "qc_report.md",
}


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    file: str
    line: int
    code: str
    severity: str
    snippet: str
    why: str


def _scan_text(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        # Whitelist the (pending) sentinel — iron-rule says it's correct usage.
        # Strip it before pattern checks so it can't be matched accidentally.
        scrub_line = line.replace("(pending)", "")
        for pat in PATTERNS:
            for m in pat.regex.finditer(scrub_line):
                findings.append(Finding(
                    file=str(path),
                    line=lineno,
                    code=pat.code,
                    severity=pat.severity,
                    snippet=line.rstrip()[:200],
                    why=pat.why,
                ))
    return findings


def _discover_files(root: Path, strict: bool) -> list[Path]:
    out: list[Path] = []
    for g in REVIEWER_FACING_GLOBS:
        out.extend(root.glob(g))
    if strict:
        # In strict mode, also scan submitter-only job aids and submission orders.
        for g in ("JB*/job_aid.md", "JB*/submission_order.md", "JB*/**/job_aid.md"):
            out.extend(root.glob(g))
    return sorted({p for p in out if p.name not in INTERNAL_NEVER_SCAN})


def lint_paths(paths: Iterable[Path]) -> list[Finding]:
    all_findings: list[Finding] = []
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8")
        except Exception as e:
            all_findings.append(Finding(
                file=str(p), line=0, code="PFL-READ-ERROR", severity="hard",
                snippet=f"could not read: {e}",
                why="File not readable.",
            ))
            continue
        all_findings.extend(_scan_text(p, text))
    return all_findings


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _print_report(findings: list[Finding], strict: bool) -> bool:
    """Return True iff the run should be considered failed."""
    if not findings:
        print("preflight_lint: clean. No findings.")
        return False

    by_file: dict[str, list[Finding]] = {}
    for f in findings:
        by_file.setdefault(f.file, []).append(f)

    hard_count = sum(1 for f in findings if f.severity == "hard")
    soft_count = sum(1 for f in findings if f.severity == "soft")

    for file, fs in by_file.items():
        print(f"\n{file}")
        for f in fs:
            tag = "HARD" if f.severity == "hard" else "SOFT"
            print(f"  L{f.line:>4}  [{tag}] {f.code}: {f.why}")
            print(f"          {f.snippet}")

    print(f"\npreflight_lint: {hard_count} hard, {soft_count} soft finding(s).")
    failed = hard_count > 0 or (strict and soft_count > 0)
    if failed:
        print("Result: FAIL — packages must not ship with hard findings"
              + (" (strict: soft findings also fail)." if strict else "."))
    else:
        print("Result: PASS — soft findings are advisory; rerun with --strict to enforce.")
    return failed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--root", type=Path, help="Scan output/ root recursively.")
    src.add_argument("--package-dir", type=Path,
                     help="Scan a single (JB, entity) folder.")
    p.add_argument("--strict", action="store_true",
                   help="Promote soft findings to failures.")
    p.add_argument("--json", type=Path, default=None,
                   help="Also write findings as a JSON file.")
    args = p.parse_args()

    if args.root:
        if not args.root.is_dir():
            print(f"error: {args.root} is not a directory", file=sys.stderr)
            return 2
        paths = _discover_files(args.root, args.strict)
    else:
        d = args.package_dir
        if not d.is_dir():
            print(f"error: {d} is not a directory", file=sys.stderr)
            return 2
        paths = sorted(p for p in d.glob("*.md") if p.name not in INTERNAL_NEVER_SCAN)

    if not paths:
        print("preflight_lint: no reviewer-facing markdown files found.")
        return 0

    findings = lint_paths(paths)

    if args.json:
        args.json.write_text(json.dumps(
            [asdict(f) for f in findings], indent=2), encoding="utf-8")

    failed = _print_report(findings, strict=args.strict)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
