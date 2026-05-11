"""
Compute the actual fee for one (JB, entity) pair and write
fee_calculation.md ready for render.

Reads:
  - output/<JB>/project_facts.json (from extract_project_facts.py)
  - references/mi_entity_registry.json (canonical entity data)

Writes:
  - output/<JB>/<entity_id>/fee_calculation.md

Three calculation strategies are supported, dispatched on the
registry entry's `fee.calculation_method`:

  1. `line_items_lookup` — explicit per-line-item rules driven by
     project facts (LF aerial, LF UG, pole counts, etc.). Produces
     real dollar amounts. Verified for Kent CRC.

  2. `engineering_computes_at_submission` — entity engineer or portal
     computes the fee at submission from submitted scope. Output is
     a placeholder fee_calculation that explains the framework and
     references the schedule URL; no synthetic dollar amount is
     invented. Used for City of Grand Rapids (Accela portal),
     MDOT (MPG calculator), and similar.

  3. `portal_calculator` — same shape as #2; alias for compatibility.

Entities with `verified_date == null` (stubs) produce a clearly-marked
output that warns the specialist to confirm before submission.

CLI
---
    python -m scripts.compute_fee --jb JB##########  --entity <entity_id>
    python -m scripts.compute_fee --facts <path>     --entity <entity_id>
    python -m scripts.compute_fee --jb JB##########  --entity <entity_id> --output-dir <path>

Examples:
    python -m scripts.compute_fee --jb JB0002431561 --entity Kent_CRC
    python -m scripts.compute_fee --jb JB0002431561 --entity MDOT_Grand_Region
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SKILL_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = SKILL_ROOT / "references" / "mi_entity_registry.json"
DEFAULT_FACTS_ROOT = Path("output")  # relative to working dir

# ---------------------------------------------------------------------------
# Registry & facts loaders
# ---------------------------------------------------------------------------


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def find_entity(entity_id: str, registry: dict) -> dict | None:
    """Locate an entity in the registry across the top-level buckets."""
    candidates = [
        registry.get("mdot", {}).get("regions", {}),
        registry.get("county_road_commissions", {}),
        registry.get("municipalities", {}),
        registry.get("pole_owners", {}),
        registry.get("railroad_operators_mi", {}),
        registry.get("environmental_overlays_mi", {}),
    ]
    for bucket in candidates:
        if entity_id in bucket and not entity_id.startswith("_"):
            return bucket[entity_id]
    return None


def find_facts(jb: str | None, facts_path: Path | None, search_root: Path) -> tuple[Path, dict]:
    """Locate project_facts.json by JB number or explicit path."""
    if facts_path:
        return facts_path, json.loads(facts_path.read_text(encoding="utf-8"))
    if not jb:
        raise SystemExit("Provide either --jb or --facts.")
    candidates = [
        search_root / jb / "project_facts.json",
        Path.cwd() / "output" / jb / "project_facts.json",
        Path("output") / jb / "project_facts.json",
    ]
    for c in candidates:
        if c.is_file():
            return c, json.loads(c.read_text(encoding="utf-8"))
    raise SystemExit(
        f"Could not find project_facts.json for {jb}. Tried: {[str(c) for c in candidates]}\n"
        f"Run 'python -m scripts.extract_project_facts' first, or pass --facts <path>."
    )


# ---------------------------------------------------------------------------
# Inheritance resolution (entities use {"inherits": "<dotted-path>"})
# ---------------------------------------------------------------------------


def deref(value: Any, registry: dict) -> Any:
    if isinstance(value, dict) and set(value.keys()) == {"inherits"}:
        cur = registry
        import re
        for part in re.findall(r"[^.\[\]]+|\[\d+\]", value["inherits"]):
            cur = cur[int(part[1:-1])] if part.startswith("[") else cur[part]
        return cur
    return value


# ---------------------------------------------------------------------------
# Line-item rules
# ---------------------------------------------------------------------------

# Each rule decides if a line item applies given project_facts and computes
# the quantity. unit_label is shown in the rendered table.
#
# Quantity computation should return None when the rule can't decide
# (e.g., bore counts not yet detected from KML); the line item is then
# emitted as "(scope-conditional — confirm before submission)" with
# zero dollar contribution.


def _scope(facts: dict) -> dict:
    return facts.get("scope") or {}


LineItemRule = dict[str, Any]
RULES: dict[str, LineItemRule] = {
    # Kent CRC line items
    "aerial_existing_poles": {
        "applies_when": lambda f: (_scope(f).get("lf_aerial_primary_ft") or 0) > 0
                                  and (_scope(f).get("poles_count") or 0) > 0,
        "quantity": lambda f: 1,
        "unit_label": "1 project (≤2 mi, single Township)",
        "_rationale": "Aerial cable to existing poles is a flat per-project fee when the route is contained per KCRC's per-project definition.",
    },
    "ug_mainline_le_1000lf": {
        "applies_when": lambda f: 0 < (_scope(f).get("lf_underground_ft") or 0) <= 1000,
        "quantity": lambda f: 1,
        "unit_label": "1 project (≤1,000 LF)",
        "_rationale": "Underground mainline ≤1,000 LF flat fee per KCRC schedule.",
    },
    "ug_mainline_gt_1000lf": {
        "applies_when": lambda f: (_scope(f).get("lf_underground_ft") or 0) > 1000,
        "quantity": lambda f: 1,
        "unit_label": "1 project (>1,000 LF)",
        "_rationale": "Underground mainline >1,000 LF flat fee per KCRC schedule.",
    },
    "pole_anchor_gt_3": {
        "applies_when": lambda f: (_scope(f).get("new_poles_count") or 0) > 3,
        "quantity": lambda f: 1,
        "unit_label": "1 batch",
        "_rationale": "Applies when more than 3 new poles or anchors are added; current run has no detection of NEW poles separate from EXISTING surveyed poles. If new poles are part of scope, surface in open_questions and add the line manually.",
    },
    # The remaining KCRC line items require facts the script doesn't yet
    # extract (open-cut crossings, bores, soil borings, service taps,
    # annual blanket type). They emit deferred lines.
    "annual_blanket": {
        "applies_when": lambda f: False,  # specialist-elected, not auto-derived
        "_deferred_reason": "Annual blanket is a permit-type election, not a per-project line item; surface manually if applicable.",
    },
    "service_tap": {
        "applies_when": lambda f: False,
        "_deferred_reason": "Service tap detection requires CD scope-of-work table extraction; not auto-derived.",
    },
    "open_cut_2lane": {
        "applies_when": lambda f: False,
        "_deferred_reason": "Open-cut crossings not auto-detected from KML; transcribe from CD.",
    },
    "open_cut_multi_lane": {
        "applies_when": lambda f: False,
        "_deferred_reason": "Open-cut crossings not auto-detected from KML; transcribe from CD.",
    },
    "bore_le_4in": {
        "applies_when": lambda f: False,
        "_deferred_reason": "Bore count not auto-detected from KML; transcribe from CD.",
    },
    "bore_gt_4in": {
        "applies_when": lambda f: False,
        "_deferred_reason": "Bore count not auto-detected from KML; transcribe from CD.",
    },
    "soil_borings_minimum": {
        "applies_when": lambda f: False,
        "_deferred_reason": "Soil borings not detected.",
    },
    "soil_borings_gt_25": {
        "applies_when": lambda f: False,
        "_deferred_reason": "Soil borings not detected.",
    },

    # City of Grand Rapids — known fixed line items (small-cell etc. don't
    # apply to typical fiber permit but are in the registry)
    "encroachment_permit": {
        "applies_when": lambda f: False,  # specialist-elected
        "_deferred_reason": "Encroachment Permit is a separate filing for permanent ROW features; surface manually if scope qualifies.",
    },
    # Anything else — let the registry data flow through with applies_when=False.
}


# ---------------------------------------------------------------------------
# Fee computation
# ---------------------------------------------------------------------------


def compute_line_items(facts: dict, entity: dict) -> dict:
    """For an entity using line_items_lookup, evaluate every rule against
    project_facts, build the line list and the total. Any registry line
    item not in RULES is included as a deferred line."""
    fee_block = entity.get("fee", {}) or {}
    declared = fee_block.get("line_items") or []
    rendered: list[dict] = []
    notes: list[str] = []
    total = 0.0
    for li in declared:
        lid = li.get("id")
        rule = RULES.get(lid, {})
        amount = li.get("amount_usd")
        applies = False
        qty = 0
        rationale = ""
        deferred_reason = rule.get("_deferred_reason")
        if rule and "applies_when" in rule:
            try:
                applies = bool(rule["applies_when"](facts))
            except Exception as e:
                applies = False
                deferred_reason = f"rule evaluation error: {e}"
        if applies:
            qty_fn: Callable[[dict], int] = rule.get("quantity") or (lambda f: 1)
            qty = qty_fn(facts)
            rationale = rule.get("_rationale", "")
            subtotal = (amount or 0) * qty
            total += subtotal
            rendered.append({
                "id": lid,
                "description": li.get("description", lid),
                "quantity": qty,
                "unit_label": rule.get("unit_label", li.get("unit", "")),
                "rate_usd": amount,
                "subtotal_usd": subtotal,
                "applied": True,
                "rationale": rationale,
            })
        else:
            rendered.append({
                "id": lid,
                "description": li.get("description", lid),
                "quantity": 0,
                "unit_label": "(does not apply)",
                "rate_usd": amount,
                "subtotal_usd": 0,
                "applied": False,
                "deferred_reason": deferred_reason,
            })
            if deferred_reason and lid not in {"annual_blanket"}:
                # annual_blanket isn't worth surfacing every time
                notes.append(f"{lid}: {deferred_reason}")

    return {
        "method": "line_items_lookup",
        "lines": rendered,
        "total_usd": round(total, 2),
        "schedule_url": fee_block.get("schedule_url"),
        "schedule_effective": fee_block.get("schedule_effective"),
        "schedule_retrieved": fee_block.get("schedule_retrieved"),
        "framework": fee_block.get("framework"),
        "deferred_line_notes": notes,
    }


def compute_deferred(facts: dict, entity: dict, method_label: str) -> dict:
    """For entities whose fee is computed at submission (engineer or portal),
    produce a placeholder fee_calculation that explains the framework and
    references the schedule. No synthetic dollars."""
    fee_block = entity.get("fee", {}) or {}
    declared = fee_block.get("line_items") or []
    # Surface any fixed-amount line items in the schedule that might apply
    # (e.g., GR Encroachment Permit at $330) as informational rows.
    informational: list[dict] = []
    for li in declared:
        if li.get("amount_usd") is not None:
            informational.append({
                "description": li.get("description"),
                "amount_usd": li.get("amount_usd"),
                "unit": li.get("unit"),
                "conditions": li.get("conditions"),
            })
    return {
        "method": method_label,
        "lines": [],
        "total_usd": None,
        "schedule_url": fee_block.get("schedule_url"),
        "schedule_retrieved": fee_block.get("schedule_retrieved"),
        "framework": fee_block.get("framework") or fee_block.get("calculation_method"),
        "calculation_explanation": (
            "Fee computed by the entity's portal or engineer at submission. "
            "Submit the application; the portal returns the fee for payment. "
            "This run does not synthesize a dollar amount — doing so would risk "
            "shipping a wrong number on the cover-of-fee line."
        ),
        "informational_known_amounts": informational,
    }


def compute_fee(facts: dict, entity: dict, registry: dict) -> dict:
    fee_block = entity.get("fee", {}) or {}
    method = fee_block.get("calculation_method") or ""
    method = method.lower().strip()
    if "line_items_lookup" in method:
        result = compute_line_items(facts, entity)
    elif "engineering_computes_at_submission" in method:
        result = compute_deferred(facts, entity, "engineering_computes_at_submission")
    elif "portal_calculator" in method or "mpg portal" in method:
        result = compute_deferred(facts, entity, "portal_calculator")
    else:
        # MDOT regions inherit fee from mdot.fee_framework — pull through
        if isinstance(fee_block, dict) and fee_block.get("inherits"):
            resolved = deref(fee_block, registry)
            result = compute_deferred(facts, {"fee": resolved}, "portal_calculator")
            result["framework"] = resolved.get("statutory_authority") or resolved.get("calculation_method")
            result["schedule_url"] = resolved.get("schedule_url")
        else:
            result = {
                "method": "unknown",
                "lines": [],
                "total_usd": None,
                "calculation_explanation": (
                    "Fee calculation_method not declared in registry. Specialist must compute by hand using "
                    "the entity's published fee schedule."
                ),
                "schedule_url": fee_block.get("schedule_url"),
                "framework": None,
            }

    # Verify-before-submission warning for stubs
    if entity.get("stub") or not entity.get("verified_date"):
        result["entity_is_stub"] = True
        result.setdefault("warnings", []).append(
            f"Entity is a stub (verified_date={entity.get('verified_date')!r}). "
            f"Verify fee schedule URL, fee math, and payment instructions before submission. "
            f"Do not ship this fee_calculation without confirming the dollar amounts against "
            f"the entity's current fee schedule."
        )
    return result


# ---------------------------------------------------------------------------
# Render fee_calculation.md
# ---------------------------------------------------------------------------


def fmt_money(amount) -> str:
    if amount is None:
        return "(computed at submission)"
    return f"${amount:,.2f}"


def render_fee_calculation_md(facts: dict, entity_id: str, entity: dict, fee: dict) -> str:
    jb = facts.get("jb", {}).get("number") or "?"
    legal_name = entity.get("legal_name") or entity_id.replace("_", " ")

    lines: list[str] = []
    lines.append(f"# Fee Calculation — {legal_name} ({jb})")
    lines.append("")
    method = fee.get("method", "unknown")

    if method == "line_items_lookup":
        lines.append("| # | Item | Quantity | Rate | Subtotal |")
        lines.append("|---|------|----------|------|----------|")
        idx = 0
        for li in fee.get("lines", []):
            if not li.get("applied"):
                continue
            idx += 1
            lines.append(
                f"| {idx} | {li['description']} | {li.get('unit_label') or li.get('quantity', 1)} "
                f"| {fmt_money(li.get('rate_usd'))} | {fmt_money(li.get('subtotal_usd'))} |"
            )
        if idx == 0:
            lines.append("| — | (no line items applied based on current project facts) | — | — | — |")
        lines.append("")
        lines.append(f"**Total: {fmt_money(fee.get('total_usd'))}**")
    else:
        lines.append("| # | Item | Quantity | Rate | Subtotal |")
        lines.append("|---|------|----------|------|----------|")
        explanation = fee.get("calculation_explanation") or "Computed at submission."
        lines.append(f"| 1 | Permit fee — {explanation} | 1 application | (computed) | (computed) |")
        info = fee.get("informational_known_amounts") or []
        for i, item in enumerate(info, start=2):
            cond = item.get("conditions") or ""
            cond_str = f" — {cond}" if cond else ""
            lines.append(
                f"| {i} | {item.get('description')}{cond_str} | per {item.get('unit') or 'item'} "
                f"| {fmt_money(item.get('amount_usd'))} | (if applicable) |"
            )
        lines.append("")
        lines.append(f"**Total: (computed by entity at submission)**")

    lines.append("")
    sched_url = fee.get("schedule_url")
    if sched_url:
        eff = fee.get("schedule_effective")
        retrieved = fee.get("schedule_retrieved")
        bits = [f"[{sched_url}]({sched_url})"]
        if eff: bits.append(f"effective {eff}")
        if retrieved: bits.append(f"retrieved {retrieved}")
        lines.append("Fee schedule: " + ", ".join(bits))
    if fee.get("framework"):
        lines.append(f"Authority: {fee['framework']}")

    # Payment instructions per registry
    submission = entity.get("submission") or {}
    online_pay = submission.get("online_payment_url")
    online_pay_limit = submission.get("online_payment_limit_usd")
    mail_addr = submission.get("mail_payment_address")
    payee = entity.get("legal_name") or entity_id.replace("_", " ")
    payment_lines = []
    if online_pay:
        cap = f" (up to ${online_pay_limit:,.0f})" if online_pay_limit else ""
        payment_lines.append(f"online via [{online_pay}]({online_pay}){cap}")
    if mail_addr:
        payment_lines.append("by mail to: " + " ".join(mail_addr) if isinstance(mail_addr, list) else f"by mail to {mail_addr}")
    if not payment_lines:
        payment_lines.append("per the portal at submission")
    lines.append(
        f"Payment: " + " or ".join(payment_lines) + f", payable to \"{payee}\", reference \"{jb} — Comcast/MasTec\""
    )

    # Notes & warnings
    if fee.get("warnings"):
        lines.append("")
        lines.append("> **Verification required before submission:**")
        for w in fee["warnings"]:
            lines.append(f"> - {w}")

    if fee.get("deferred_line_notes"):
        lines.append("")
        lines.append("Deferred line items (not auto-applied; surface manually if scope qualifies):")
        for n in fee["deferred_line_notes"]:
            lines.append(f"- {n}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--jb", type=str, help="JB number, e.g. JB0002431561")
    g.add_argument("--facts", type=Path, help="Path to project_facts.json")
    p.add_argument("--entity", type=str, required=True, help="Entity ID (e.g. Kent_CRC, MDOT_Grand_Region, City_of_Grand_Rapids)")
    p.add_argument("--output-dir", type=Path, default=None, help="Override output directory")
    p.add_argument("--search-root", type=Path, default=None, help="Where to look for output/<JB>/project_facts.json (default: ./output and Deliverables/output)")
    args = p.parse_args()

    registry = load_registry()
    entity = find_entity(args.entity, registry)
    if entity is None:
        print(f"error: entity {args.entity!r} not found in registry. Top-level keys: county_road_commissions, municipalities, mdot.regions, pole_owners, etc.", file=sys.stderr)
        return 1

    search_root = args.search_root or Path("output")
    facts_path, facts = find_facts(args.jb, args.facts, search_root)

    fee = compute_fee(facts, entity, registry)
    md = render_fee_calculation_md(facts, args.entity, entity, fee)

    jb = facts.get("jb", {}).get("number") or args.jb or "UNKNOWN"
    if args.output_dir:
        out_dir = args.output_dir
    else:
        # Default: <facts_parent>/<entity_id>/  (i.e., output/JB#/<entity_id>/)
        out_dir = facts_path.parent / args.entity
    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / "fee_calculation.md"
    out_md.write_text(md, encoding="utf-8")

    # Console summary
    print(f"Wrote {out_md}")
    print(f"  Method: {fee.get('method')}")
    if fee.get("total_usd") is not None:
        print(f"  Total:  {fmt_money(fee['total_usd'])}")
    else:
        print(f"  Total:  (computed at submission)")
    if fee.get("warnings"):
        print(f"  Warnings ({len(fee['warnings'])}):")
        for w in fee["warnings"]:
            print(f"    - {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
