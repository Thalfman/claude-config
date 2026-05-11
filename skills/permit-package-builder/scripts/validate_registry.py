"""
Sanity-check references/mi_entity_registry.json.

Run as:
    python -m scripts.validate_registry

Exits 0 on success, 1 on any failure. Intended to run after every edit
to the registry JSON, and as a precondition before any script that
consumes the registry is allowed to run.

Checks:
  1. JSON parses.
  2. Top-level keys match expected schema.
  3. All 83 Michigan counties appear in mdot.county_to_region.
  4. Every region used in county_to_region has a corresponding
     entry under mdot.regions.
  5. Per-region county counts match MDOT's published distribution
     (Superior=15, North=21, Bay=14, Grand=11, Southwest=9,
     University=9, Metro=4).
  6. Every "inherits" reference resolves to a valid path in the
     registry (no dangling pointers).
  7. Every entity's category is in the allowed set.
  8. Every verified entity has a verified_date; every stub flags
     stub=true OR has verified_date=null.
"""

from __future__ import annotations
import json
import re
import sys
from collections import Counter
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "references" / "mi_entity_registry.json"

EXPECTED_TOP_KEYS = {
    "schema_version", "registry", "default_contacts", "state_811",
    "mdot", "county_road_commissions", "municipalities",
    "pole_owners", "railroad_operators_mi", "environmental_overlays_mi",
}

MI_COUNTIES = {
    "Alcona","Alger","Allegan","Alpena","Antrim","Arenac","Baraga","Barry","Bay","Benzie",
    "Berrien","Branch","Calhoun","Cass","Charlevoix","Cheboygan","Chippewa","Clare","Clinton","Crawford",
    "Delta","Dickinson","Eaton","Emmet","Genesee","Gladwin","Gogebic","Grand Traverse","Gratiot","Hillsdale",
    "Houghton","Huron","Ingham","Ionia","Iosco","Iron","Isabella","Jackson","Kalamazoo","Kalkaska",
    "Kent","Keweenaw","Lake","Lapeer","Leelanau","Lenawee","Livingston","Luce","Mackinac","Macomb",
    "Manistee","Marquette","Mason","Mecosta","Menominee","Midland","Missaukee","Monroe","Montcalm","Montmorency",
    "Muskegon","Newaygo","Oakland","Oceana","Ogemaw","Ontonagon","Osceola","Oscoda","Otsego","Ottawa",
    "Presque Isle","Roscommon","Saginaw","Sanilac","Schoolcraft","Shiawassee","St. Clair","St. Joseph","Tuscola","Van Buren",
    "Washtenaw","Wayne","Wexford",
}

EXPECTED_REGION_COUNTS = {
    "Superior": 15, "North": 21, "Bay": 14, "Grand": 11,
    "Southwest": 9, "University": 9, "Metro": 4,
}

ALLOWED_CATEGORIES = {
    "state_dot", "county_road_commission", "municipality",
    "pole_owner", "railroad", "environmental",
}


def resolve_path(root, dotted: str):
    """Resolve a dotted path with [n] indices, e.g. mdot.common_forms[0]."""
    cur = root
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", dotted):
        cur = cur[int(part[1:-1])] if part.startswith("[") else cur[part]
    return cur


def walk_collect_inherits(obj, path=""):
    refs = []
    if isinstance(obj, dict):
        if "inherits" in obj and len(obj) == 1:
            refs.append((path, obj["inherits"]))
        for k, v in obj.items():
            refs.extend(walk_collect_inherits(v, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            refs.extend(walk_collect_inherits(v, f"{path}[{i}]"))
    return refs


def walk_collect_entities(obj, path=""):
    """Walk the registry collecting real entity records.

    Convention: keys starting with `_` are metadata, schema docs, or
    generic templates — never real entities. We never descend into them
    and we never treat them as entities even if they happen to carry
    a `category` field (e.g. `_generic_template` showing the schema shape).
    """
    out = []
    if isinstance(obj, dict):
        # Skip nodes whose own leaf-key starts with `_`: they are docs.
        leaf_key = path.rsplit(".", 1)[-1] if path else ""
        if leaf_key.startswith("_"):
            return out
        if obj.get("category") in ALLOWED_CATEGORIES:
            out.append((path, obj))
        else:
            for k, v in obj.items():
                if k.startswith("_"):
                    continue
                out.extend(walk_collect_entities(v, f"{path}.{k}" if path else k))
    return out


def main() -> int:
    failures: list[str] = []

    raw = REGISTRY_PATH.read_text(encoding="utf-8")

    # 1. JSON parses.
    try:
        reg = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"FAIL: JSON parse error: {e}")
        return 1

    # 2. Top-level keys.
    actual = set(reg.keys())
    if actual != EXPECTED_TOP_KEYS:
        failures.append(f"Top-level keys mismatch. Missing: {EXPECTED_TOP_KEYS - actual}. Extra: {actual - EXPECTED_TOP_KEYS}")

    # 3. All 83 counties present.
    table = reg["mdot"]["county_to_region"]
    missing = MI_COUNTIES - set(table.keys())
    extra = set(table.keys()) - MI_COUNTIES
    if missing:
        failures.append(f"county_to_region missing counties: {sorted(missing)}")
    if extra:
        failures.append(f"county_to_region has non-MI keys: {sorted(extra)}")

    # 4. Every region used has a declared entry.
    declared = {reg["mdot"]["regions"][k]["region_name"] for k in reg["mdot"]["regions"]}
    used = set(table.values())
    if used - declared:
        failures.append(f"Regions used but not declared: {used - declared}")

    # 5. Per-region county counts.
    counts = Counter(table.values())
    for region, expected in EXPECTED_REGION_COUNTS.items():
        if counts.get(region, 0) != expected:
            failures.append(f"Region '{region}' has {counts.get(region, 0)} counties, expected {expected}")

    # 6. Inherits references resolve.
    refs = walk_collect_inherits(reg)
    for path, target in refs:
        try:
            resolve_path(reg, target)
        except (KeyError, IndexError, TypeError) as e:
            failures.append(f"Broken inherits at {path} → {target}: {e}")

    # 7 & 8. Entity category and verified/stub consistency.
    entities = walk_collect_entities(reg)
    for path, ent in entities:
        cat = ent.get("category")
        if cat not in ALLOWED_CATEGORIES:
            failures.append(f"Entity {path} has invalid category {cat!r}")
        # An entity is verified iff verified_date is non-null AND stub is not true.
        verified_date = ent.get("verified_date")
        stub = ent.get("stub", False)
        if verified_date is not None and stub is True:
            failures.append(f"Entity {path} has verified_date={verified_date} but stub=true (contradiction)")
        if verified_date is None and stub is False:
            # Only warn — possibly the schema is missing the stub flag for an unverified entry.
            failures.append(f"Entity {path} has verified_date=null but stub is not set to true")

    # Summary.
    if failures:
        print("FAIL")
        for line in failures:
            print(f"  - {line}")
        return 1

    print("PASS — registry is valid")
    print(f"  schema_version: {reg['schema_version']}")
    print(f"  last_updated:   {reg['registry']['last_updated']}")
    print(f"  counties:       {len(table)}")
    print(f"  inherits refs:  {len(refs)} (all resolve)")
    verified = sum(1 for _, e in entities if e.get("verified_date") and not e.get("stub", False))
    stubs = sum(1 for _, e in entities if e.get("stub") is True or e.get("verified_date") is None)
    print(f"  entities:       {len(entities)} total ({verified} verified, {stubs} stub)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
