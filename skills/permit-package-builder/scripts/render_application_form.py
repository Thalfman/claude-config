"""
Render an entity-specific application_form.md by slotting values from
project_facts.json and the entity registry into a markdown template.

Templates live in `assets/forms/<entity_id>.md` and use `{{slot}}`
syntax. The renderer flattens facts + entity + registry defaults into
a single namespace, then substitutes every `{{slot}}` with its value
or `(pending)` if the slot is unset.

HTML comment blocks (`<!-- ... -->`) inside templates are stripped from
the rendered output. Template authors can use them freely to document
field provenance, source URLs, or maintenance notes inline; reviewers
never see scaffolding.

CLI
---
    python -m scripts.render_application_form --jb JB########## --entity <entity_id>
    python -m scripts.render_application_form --facts <path> --entity <entity_id>

Output: output/<JB>/<entity_id>/application_form.md
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = SKILL_ROOT / "references" / "mi_entity_registry.json"
FORMS_DIR = SKILL_ROOT / "assets" / "forms"

PENDING = "(pending)"
SLOT_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->\s*\n?", re.DOTALL)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def find_entity(entity_id: str, registry: dict) -> dict | None:
    for bucket_name in ("county_road_commissions", "municipalities", "pole_owners",
                         "railroad_operators_mi", "environmental_overlays_mi"):
        bucket = registry.get(bucket_name, {})
        if entity_id in bucket and not entity_id.startswith("_"):
            return bucket[entity_id]
    regions = registry.get("mdot", {}).get("regions", {})
    if entity_id in regions:
        return regions[entity_id]
    return None


def find_facts(jb: str | None, facts_path: Path | None, search_root: Path) -> tuple[Path, dict]:
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
    raise SystemExit(f"project_facts.json not found for {jb}.")


# ---------------------------------------------------------------------------
# Slot keyspace builder
# ---------------------------------------------------------------------------


def _join_addr(lines: Any) -> str:
    if isinstance(lines, list):
        return ", ".join(str(x) for x in lines if x)
    if lines:
        return str(lines)
    return ""


def build_keyspace(facts: dict, entity_id: str, entity: dict, registry: dict) -> dict[str, str]:
    """Build a flat dict that maps every {{slot}} name to a stringified value."""
    today = _dt.date.today().isoformat()
    project = facts.get("project") or {}
    scope = facts.get("scope") or {}
    mdot_facts = facts.get("mdot") or {}
    coi = entity.get("coi") or {}
    fee = entity.get("fee") or {}
    submission = entity.get("submission") or {}
    addressee = entity.get("addressee") or {}

    contacts = registry.get("default_contacts", {}) or {}
    submitting = contacts.get("mastec_submitting", {}) or {}
    office = contacts.get("mastec_office_of_record", {}) or {}
    applicant = contacts.get("applicant_block_for_forms", {}) or {}

    applicant_addr = applicant.get("applicant_address") or office.get("address") or []
    applicant_addr_l1 = applicant_addr[0] if len(applicant_addr) >= 1 else ""
    applicant_addr_l2 = applicant_addr[1] if len(applicant_addr) >= 2 else ""

    coi_verbatim = coi.get("additional_insured_verbatim")
    coi_text = " ".join(coi_verbatim) if isinstance(coi_verbatim, list) else (coi_verbatim or "")

    coi_min = coi.get("minimum_general_liability_usd")
    coi_min_str = f"${coi_min:,.0f} GL" if coi_min else ""
    if "minimum_general_liability_usd" not in coi and "city_published_minimum_general_liability_usd" in coi:
        coi_min_str = f"${coi.get('city_published_minimum_general_liability_usd'):,.0f} GL (City minimum); $1,000,000 GL issued by MasTec broker"

    keys: dict[str, Any] = {
        # Date
        "date_today": today,

        # JB & project (from facts)
        "jb": (facts.get("jb") or {}).get("number") or "",
        "project_name": project.get("name") or "",
        "address": project.get("address") or "",
        "city": project.get("city") or "",
        "state": project.get("state") or "",
        "zip": project.get("zip") or "",
        "county": project.get("county") or "",
        "lat": project.get("lat_decimal") if project.get("lat_decimal") is not None else "",
        "lon": project.get("lon_decimal") if project.get("lon_decimal") is not None else "",
        "township": project.get("township") or "",
        "range": project.get("range") or "",
        "section": project.get("section") or "",
        "qtr_section": project.get("qtr_section") or "",

        # Scope (from facts)
        "lf_aerial": scope.get("lf_aerial_primary_ft") if scope.get("lf_aerial_primary_ft") is not None else "",
        "lf_underground": scope.get("lf_underground_ft") if scope.get("lf_underground_ft") is not None else "",
        "poles_count": scope.get("poles_count") if scope.get("poles_count") is not None else "",
        "ug_pole_stations_count": scope.get("ug_pole_stations_count") if scope.get("ug_pole_stations_count") is not None else "",
        "primary_construction_type": scope.get("primary_construction_type") or "",
        "scope_clause": scope.get("summary_clause_for_cover_letter") or "",

        # MDOT (from facts; entity-resolved)
        "mdot_region": mdot_facts.get("region") or "",
        "mdot_region_office_city": mdot_facts.get("region_office_city") or "",

        # Applicant block
        "applicant_legal_name": applicant.get("applicant_legal_name") or "MasTec Communications Group, Inc.",
        "applicant_role": applicant.get("applicant_role") or "Authorized agent of Comcast",
        "franchise_utility": applicant.get("franchise_utility_on_file") or "Comcast Cable Communications, LLC",
        "applicant_address_line_1": applicant_addr_l1,
        "applicant_address_line_2": applicant_addr_l2,
        "submitting_contact_name": submitting.get("name") or "",
        "submitting_contact_phone": submitting.get("phone") or "",
        "submitting_contact_email": submitting.get("email") or "",

        # Entity
        "entity_legal_name": entity.get("legal_name") or entity_id.replace("_", " "),
        "entity_addressee_name": addressee.get("name_placeholder") or addressee.get("office") or "",
        "entity_addressee_address": _join_addr(addressee.get("address")),
        "entity_portal_name": submission.get("portal_name") or submission.get("primary_method") or "",
        "entity_portal_url": submission.get("portal_url") or "",
        "entity_review_window": entity.get("review_window_days") or entity.get("review_window") or "",

        # Fee schedule
        "entity_fee_schedule_url": fee.get("schedule_url") or "",
        "entity_fee_schedule_effective": fee.get("schedule_effective") or "",
        "entity_fee_schedule_retrieved": fee.get("schedule_retrieved") or "",
        "entity_online_payment_url": submission.get("online_payment_url") or "",
        "entity_online_payment_limit": (
            f"{submission.get('online_payment_limit_usd'):,.0f}"
            if submission.get("online_payment_limit_usd") else ""
        ),

        # COI
        "coi_min_gl": coi_min_str,
        "coi_additional_insured": coi_text,
        "coi_source": coi.get("additional_insured_source") or "",
        "coi_cancel_days": str(coi.get("notice_of_cancellation_days") or "") if coi.get("notice_of_cancellation_days") else "",
    }

    return {k: ("" if v is None else str(v)) for k, v in keys.items()}


def render(template: str, keyspace: dict[str, str]) -> tuple[str, list[str]]:
    """Substitute slots; return rendered + list of slots that were missing.

    HTML comment blocks are stripped before slot substitution so internal
    template documentation never reaches the reviewer-facing output.
    """
    missing: list[str] = []

    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name in keyspace and keyspace[name] != "":
            return keyspace[name]
        if name not in keyspace:
            missing.append(name)
        return PENDING

    stripped = HTML_COMMENT_RE.sub("", template)
    out = SLOT_RE.sub(replace, stripped)
    return out, sorted(set(missing))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--jb", type=str, help="JB number")
    g.add_argument("--facts", type=Path, help="project_facts.json path")
    p.add_argument("--entity", type=str, required=True, help="Entity ID (must match a template in assets/forms/)")
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--search-root", type=Path, default=Path("output"))
    args = p.parse_args()

    registry = load_registry()
    entity = find_entity(args.entity, registry)
    if entity is None:
        print(f"error: entity {args.entity!r} not found in registry", file=sys.stderr)
        return 1

    # Resolve template — direct match first, then known aliases.
    # All MDOT regions share Form 2205-1; small-cities can map to a generic municipal form
    # if no per-city template exists yet (future).
    template_aliases = {
        "MDOT_Superior_Region": "MDOT_2205-1",
        "MDOT_North_Region": "MDOT_2205-1",
        "MDOT_Bay_Region": "MDOT_2205-1",
        "MDOT_Grand_Region": "MDOT_2205-1",
        "MDOT_Southwest_Region": "MDOT_2205-1",
        "MDOT_University_Region": "MDOT_2205-1",
        "MDOT_Metro_Region": "MDOT_2205-1",
    }
    template_name = template_aliases.get(args.entity, args.entity)
    template_path = FORMS_DIR / f"{template_name}.md"
    if not template_path.is_file():
        print(f"error: no template at {template_path} (entity {args.entity!r}, alias-resolved to {template_name!r}).", file=sys.stderr)
        print("Available templates:", file=sys.stderr)
        for t in sorted(FORMS_DIR.glob("*.md")):
            print(f"  - {t.stem}", file=sys.stderr)
        return 1

    facts_path, facts = find_facts(args.jb, args.facts, args.search_root)
    keyspace = build_keyspace(facts, args.entity, entity, registry)
    template = template_path.read_text(encoding="utf-8")
    rendered, missing_slots = render(template, keyspace)

    out_dir = args.output_dir or (facts_path.parent / args.entity)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / "application_form.md"
    out_md.write_text(rendered, encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"  Template: {template_path.relative_to(SKILL_ROOT)}")
    print(f"  Slots filled: {sum(1 for v in keyspace.values() if v)} / {len(keyspace)}")
    if missing_slots:
        print(f"  Slots in template not in keyspace ({len(missing_slots)}): {missing_slots}")
    # Count remaining (pending) markers in output
    remaining = rendered.count(PENDING)
    if remaining:
        print(f"  Output contains {remaining} '(pending)' markers — these need manual fill or open_items.md note.")
    if entity.get("stub") or not entity.get("verified_date"):
        print(f"  WARN: Entity is a stub (verified_date={entity.get('verified_date')!r}). Verify entity-derived fields before submission.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
