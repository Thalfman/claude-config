"""
Build a cross-JB submission tracker by walking every project_facts.json
under an output/ root and aggregating into a single MASTER_TRACKER.md.

Reads:
  output/JB##########/project_facts.json (one or more)

Writes:
  <root>/MASTER_TRACKER.md (and a JSON sidecar for downstream tooling)

The tracker is the user's at-a-glance dashboard for "this week's batch."
It surfaces:
  - Per-JB scope (LF aerial, LF UG, primary construction type)
  - Per-JB jurisdictional context (county, MDOT region, city)
  - Per-JB boilerplate signals (BP-001 wrong-state 811, BP-002 SEFNCO legacy)
  - Per-JB open-question count
  - Per-JB status verdict (auto-derived: READY_TO_DRAFT, NEEDS_RESEARCH, NEEDS_SCRUB, BLOCKED)
  - Aggregate boilerplate stats across the batch (e.g., "all 6 CDs need BP-001 scrub")
  - Per-drafter quality summary

CLI
---
    python -m scripts.build_master_tracker --root <output_dir>
    python -m scripts.build_master_tracker --root output/

Output: <root>/MASTER_TRACKER.md and <root>/MASTER_TRACKER.json
"""

from __future__ import annotations

import argparse
import collections
import datetime as _dt
import json
import sys
from pathlib import Path


def fmt_int(v) -> str:
    if v is None or v == "":
        return "—"
    if isinstance(v, (int, float)):
        return f"{int(v):,}"
    return str(v)


def derive_status(facts: dict, scrubbed_pdf: Path | None = None) -> tuple[str, str]:
    """Return (status_label, one_clause_reason).

    If `scrubbed_pdf` is supplied and the file exists with non-zero size, a
    BP-001/BP-002-flagged CD is treated as already scrubbed (status SCRUBBED)
    rather than NEEDS_SCRUB.
    """
    open_qs = facts.get("open_questions") or []
    bp = facts.get("boilerplate_signals") or {}
    scope = facts.get("scope") or {}
    has_kml_scope = scope.get("lf_aerial_primary_ft") is not None and scope.get("lf_aerial_primary_ft") != 0 \
                    or scope.get("lf_underground_ft") is not None and scope.get("lf_underground_ft") != 0
    no_kml_signal = any("No KML" in q or "Mode C" in q for q in open_qs)

    scrub_present = bool(scrubbed_pdf and scrubbed_pdf.exists() and scrubbed_pdf.stat().st_size > 0)

    if no_kml_signal and not has_kml_scope:
        return ("NEEDS_CD_TRANSCRIBE",
                "No KML; transcribe scope from CD page 2 description-of-work table")

    issues = []
    if bp.get("_811_scrub_required"):
        issues.append("BP-001")
    if bp.get("_legacy_company_scrub_required"):
        issues.append("BP-002")
    if issues and not scrub_present:
        return ("NEEDS_SCRUB", "CD scrub required: " + ", ".join(issues))

    if not (facts.get("project") or {}).get("county"):
        return ("NEEDS_RESEARCH", "County not auto-extracted; resolve manually")

    if not (facts.get("mdot") or {}).get("region"):
        return ("NEEDS_RESEARCH", "MDOT region lookup miss; verify county spelling")

    if issues and scrub_present:
        return ("SCRUBBED", "CD scrubbed (" + ", ".join(issues) + " corrected); ready for fee/form/exhibit")

    if has_kml_scope:
        return ("READY_TO_DRAFT", "Scope, county, MDOT region, BP signals all clean")

    return ("NEEDS_REVIEW", "Edge case; inspect project_facts.json")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True, help="Path to output/ directory containing JB#/project_facts.json")
    args = p.parse_args()

    if not args.root.is_dir():
        print(f"error: {args.root} is not a directory", file=sys.stderr)
        return 1

    facts_files = sorted(args.root.glob("JB*/project_facts.json"))
    if not facts_files:
        print(f"error: no JB*/project_facts.json under {args.root}", file=sys.stderr)
        return 1

    rows = []
    for ff in facts_files:
        try:
            f = json.loads(ff.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"warn: skipping {ff} — {e}", file=sys.stderr)
            continue
        rows.append((ff, f))

    # Aggregate stats
    total = len(rows)
    bp001_count = sum(1 for _, f in rows if (f.get("boilerplate_signals") or {}).get("_811_scrub_required"))
    bp002_count = sum(1 for _, f in rows if (f.get("boilerplate_signals") or {}).get("_legacy_company_scrub_required"))
    drafters = collections.Counter()
    for _, f in rows:
        drafter = (f.get("drafter_block") or {}).get("engineer") or "unknown"
        drafters[drafter] += 1

    def _scrubbed_pdf_for(ff: Path) -> Path:
        # Project facts live at <root>/<jb>/project_facts.json; the scrubbed
        # PDF, if any, lives next to it as <jb>_scrubbed.pdf.
        jb_dir = ff.parent
        return jb_dir / f"{jb_dir.name}_scrubbed.pdf"

    scrubbed_count = sum(
        1 for ff, _ in rows if _scrubbed_pdf_for(ff).exists() and _scrubbed_pdf_for(ff).stat().st_size > 0
    )

    today = _dt.date.today().isoformat()
    out_md_lines: list[str] = []
    out_md_lines.append(f"# Master Submission Tracker — Permit Batch")
    out_md_lines.append("")
    out_md_lines.append(f"Generated {today} from `{args.root}`. Source of truth: per-JB `project_facts.json` files. Re-run after each `extract_project_facts` to refresh.")
    out_md_lines.append("")
    out_md_lines.append(f"**Batch summary:** {total} JB(s)")

    if bp001_count:
        out_md_lines.append(f"- ⚠ **{bp001_count} of {total} CDs flag BP-001** (state-mismatched 811 callout) — `scrub_cd.py` required before render.")
    if bp002_count:
        out_md_lines.append(f"- ⚠ **{bp002_count} of {total} CDs flag BP-002** (legacy company name in legal boilerplate) — `scrub_cd.py` required before render.")
    if scrubbed_count:
        out_md_lines.append(f"- ✓ **{scrubbed_count} of {total} CDs already scrubbed** (sibling `<jb>_scrubbed.pdf` present).")
    if drafters:
        out_md_lines.append("- Drafter origins:")
        for drafter, count in drafters.most_common():
            out_md_lines.append(f"  - `{drafter}`: {count} JB(s)")
    out_md_lines.append("")

    # Main per-JB table
    out_md_lines.append("## Per-JB status")
    out_md_lines.append("")
    out_md_lines.append("| JB | County | City/Township | MDOT | LF aerial | LF UG | Type | BP-001 | BP-002 | Scrub | Open Q | Status |")
    out_md_lines.append("|----|--------|---------------|------|-----------|-------|------|--------|--------|-------|--------|--------|")

    json_rows = []
    for ff, f in rows:
        jb = (f.get("jb") or {}).get("number") or ff.parent.name
        project = f.get("project") or {}
        scope = f.get("scope") or {}
        mdot = f.get("mdot") or {}
        bp = f.get("boilerplate_signals") or {}
        scrubbed_pdf = _scrubbed_pdf_for(ff)
        scrub_present = scrubbed_pdf.exists() and scrubbed_pdf.stat().st_size > 0
        status, _reason = derive_status(f, scrubbed_pdf)
        bp001 = "Y" if bp.get("_811_scrub_required") else "—"
        bp002 = "Y" if bp.get("_legacy_company_scrub_required") else "—"
        scrub_cell = "✓" if scrub_present else "—"
        out_md_lines.append(
            f"| {jb} | {project.get('county') or '—'} | {project.get('city') or '—'} "
            f"| {mdot.get('region') or '—'} | {fmt_int(scope.get('lf_aerial_primary_ft'))} "
            f"| {fmt_int(scope.get('lf_underground_ft'))} | {scope.get('primary_construction_type') or '—'} "
            f"| {bp001} | {bp002} | {scrub_cell} | {len(f.get('open_questions') or [])} | **{status}** |"
        )
        json_rows.append({
            "jb": jb,
            "project_facts_path": str(ff),
            "scrubbed_cd_pdf": str(scrubbed_pdf) if scrub_present else None,
            "county": project.get("county"),
            "city": project.get("city"),
            "address": project.get("address"),
            "mdot_region": mdot.get("region"),
            "lf_aerial_primary_ft": scope.get("lf_aerial_primary_ft"),
            "lf_underground_ft": scope.get("lf_underground_ft"),
            "poles_count": scope.get("poles_count"),
            "primary_construction_type": scope.get("primary_construction_type"),
            "bp001_scrub_required": bool(bp.get("_811_scrub_required")),
            "bp002_scrub_required": bool(bp.get("_legacy_company_scrub_required")),
            "scrubbed": scrub_present,
            "open_questions_count": len(f.get("open_questions") or []),
            "status": status,
            "status_reason": _reason,
        })

    out_md_lines.append("")

    # Per-JB next-action block
    out_md_lines.append("## Per-JB next action")
    out_md_lines.append("")
    for ff, f in rows:
        jb = (f.get("jb") or {}).get("number") or ff.parent.name
        scrubbed_pdf = _scrubbed_pdf_for(ff)
        scrub_present = scrubbed_pdf.exists() and scrubbed_pdf.stat().st_size > 0
        status, reason = derive_status(f, scrubbed_pdf)
        out_md_lines.append(f"### {jb} — {status}")
        out_md_lines.append("")
        out_md_lines.append(f"**Reason:** {reason}")
        if scrub_present:
            out_md_lines.append("")
            out_md_lines.append(f"**Scrubbed CD:** `{scrubbed_pdf.relative_to(args.root)}`")
        out_md_lines.append("")
        # Filter open questions: scrub-prerequisite reminders are obsolete once the scrubbed PDF exists.
        open_qs = list(f.get("open_questions") or [])
        if scrub_present:
            open_qs = [
                q for q in open_qs
                if "Run scrub_cd" not in q
            ]
        if open_qs:
            out_md_lines.append("**Open questions:**")
            for q in open_qs:
                out_md_lines.append(f"- {q}")
            out_md_lines.append("")

    # Footer with cross-references
    out_md_lines.append("---")
    out_md_lines.append("")
    out_md_lines.append("**Workflow:**")
    out_md_lines.append("1. Run `python -m scripts.extract_project_facts --all <Deliverables_root>` whenever new JB folders land.")
    out_md_lines.append("2. Run `python -m scripts.build_master_tracker --root output/` to refresh this tracker.")
    out_md_lines.append("3. For each `READY_TO_DRAFT` JB, run `compute_fee` and `render_application_form` per (JB, entity) pair.")
    out_md_lines.append("4. For `NEEDS_SCRUB` JBs, run `scrub_cd.py` first. For `NEEDS_CD_TRANSCRIBE`, transcribe scope from the CD page 2 description-of-work table into project_facts.json then re-run this tracker.")
    out_md_lines.append("")

    out_md = args.root / "MASTER_TRACKER.md"
    out_md.write_text("\n".join(out_md_lines), encoding="utf-8")

    out_json = args.root / "MASTER_TRACKER.json"
    out_json.write_text(json.dumps({
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "total_jbs": total,
        "bp001_scrub_count": bp001_count,
        "bp002_scrub_count": bp002_count,
        "scrubbed_count": scrubbed_count,
        "drafters": dict(drafters),
        "rows": json_rows,
    }, indent=2), encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")
    print(f"  {total} JB(s) | {bp001_count} BP-001 | {bp002_count} BP-002")
    by_status = collections.Counter(r["status"] for r in json_rows)
    for st, n in by_status.most_common():
        print(f"  {st}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
