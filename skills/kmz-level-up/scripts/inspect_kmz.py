"""Stage 1: walk the input KMZ, classify attributes, write attribute_mapping.json.

Usage:
    python -m scripts.inspect_kmz input.kmz --output attribute_mapping.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from scripts.attribute_conventions import (
    classify_attribute_name,
    classify_construction_value,
    classify_feature,
)
from scripts.kml_model import StyleRole
from scripts.parse_kml import parse_kmz


_BOUNDARY_NAME_INSPECT = re.compile(r"permit|boundary|work\s*area|easement|row\s*lim", re.I)


# Patterns that suggest an attribute is a job-level grouper.
_JOB_KEY_PATTERNS = [
    re.compile(r"^(JBNumber|JB_?Number|JobNumber|Job_?Number|JobID|Job_?ID)$", re.I),
    re.compile(r"^(Project|ProjectNumber|Project_?ID)$", re.I),
]
# Patterns that suggest an attribute is a permit-level grouper. Listed
# from most-specific to least-specific so Unique_ID (a stable permit key)
# wins over Permit_Number (often "Null" or "BLANKET PERMIT" in Sphere
# exports) when both are present.
_PERMIT_KEY_PATTERNS = [
    re.compile(r"^Unique_?ID$", re.I),
    re.compile(r"^PRM$", re.I),
    re.compile(r"^Permit_?ID$", re.I),
    re.compile(r"^Permit_?Number$", re.I),
    re.compile(r"^(GlobalID|OBJECTID|FID)$", re.I),
]
# Patterns that suggest a status attribute used for color-coding.
_STATUS_KEY_PATTERNS = [
    re.compile(r"^Build_?Status$", re.I),
    re.compile(r"^Status$", re.I),
    re.compile(r"^State$", re.I),
]


def _first_match(keys: list[str], patterns: list[re.Pattern]) -> str | None:
    for pat in patterns:
        for k in keys:
            if pat.search(k):
                return k
    return None


def _suggest_polygon_handling(detected_keys: list[str]) -> dict:
    """Build a default polygon_handling block for polygon-dominant inputs.

    Picks JobNumber-ish + PermitNumber-ish attributes for `group_by`/`merge_at`,
    and a Status-ish attribute for `style_by`. When a key is missing the block
    still emits with `enabled: true` and conservative defaults; the user edits
    the JSON to fill in the gaps.
    """
    job_key = _first_match(detected_keys, _JOB_KEY_PATTERNS)
    permit_key = _first_match(detected_keys, _PERMIT_KEY_PATTERNS)
    status_key = _first_match(detected_keys, _STATUS_KEY_PATTERNS)
    jurisdiction_key = next(
        (k for k in detected_keys if re.search(r"jurisdiction", k, re.I)), None
    )

    group_by = [job_key] if job_key else []
    label_template = "{value}"
    if permit_key and jurisdiction_key:
        label_template = f"{{{permit_key}}} - {{{jurisdiction_key}}}"
    elif permit_key:
        label_template = f"{{{permit_key}}}"

    return {
        "enabled": True,
        "top_folder_name": None,  # null = no wrapper folder above the JB folders
        "group_by": group_by,
        "merge_at": permit_key,
        "folder_label_templates": {
            **({job_key: "{value}"} if job_key else {}),
        },
        "placemark_label_template": label_template,
        "style_by": status_key,
        "default_style": {"line": "ff00ff00", "fill": "8000ff00", "line_width": 4},
        "status_styles": {},
    }


def inspect(kmz_path: str | Path) -> dict:
    doc = parse_kmz(kmz_path)

    # Collect all attribute keys.
    all_keys = set()
    for f in doc.all_features():
        all_keys.update(f.attributes.keys())

    polygon_dominant = (
        len(doc.polygons) > 0
        and len(doc.linestrings) == 0
        and len(doc.points) == 0
    )

    if not all_keys and not doc.polygons:
        raise SystemExit(
            "No attributes found on any placemark and no polygons to organize. "
            "Use a builder skill (cd-route-stitcher / dxf-to-kmz / permit-to-kmz) "
            "to build a KMZ from source."
        )

    # CRS sanity check: bail if coords look projected (any |x| > 360 or |y| > 90).
    for f in doc.all_features():
        coords = []
        if hasattr(f, "coordinates") and isinstance(f.coordinates, list):
            coords = f.coordinates
        elif hasattr(f, "coordinates") and isinstance(f.coordinates, tuple):
            coords = [f.coordinates]
        elif hasattr(f, "outer_ring"):
            coords = f.outer_ring
        for x, y in coords:
            if abs(x) > 360 or abs(y) > 90:
                raise SystemExit(
                    f"Non-WGS84 coords detected (x={x}, y={y}). KMZ should always "
                    f"be EPSG:4326 (lat/lon). Use dxf-to-kmz for projected sources."
                )

    # Classify attribute names -> roles.
    attribute_roles: dict[str, str] = {}
    for k in sorted(all_keys):
        role = classify_attribute_name(k)
        if role:
            attribute_roles[k] = role

    # Build value-classification table for the construction_type attribute.
    value_classifications = {"construction_type": {}}
    construction_attr = next((k for k, r in attribute_roles.items() if r == "construction_type"), None)
    if construction_attr:
        seen_values = set()
        for f in doc.all_features():
            v = f.attributes.get(construction_attr)
            if v is not None and v != "":
                seen_values.add(str(v))
        for v in sorted(seen_values):
            role = classify_construction_value(v)
            if role is not StyleRole.UNMAPPED:
                value_classifications["construction_type"][v] = role.value

    # Per-placemark auto-roles.
    placemarks = []
    for f in doc.all_features():
        auto = classify_feature(f, attribute_roles)
        placemarks.append({
            "id": f.id,
            "name": f.name,
            "auto_role": auto.value,
            "override_role": None,
            "publish": True,
        })

    # Detection of what's already present.
    has_permit_area = any(
        _BOUNDARY_NAME_INSPECT.search(p.name or "") for p in doc.polygons
    )
    has_poles = any(
        "pole" in (pt.name or "").lower() or
        any("pole" in fp.lower() for fp in pt.folder_path)
        for pt in doc.points
    )
    has_ticks = any(
        "sta" in (pt.name or "").lower() or "station" in (pt.name or "").lower()
        for pt in doc.points
    )

    polygon_handling = (
        _suggest_polygon_handling(sorted(all_keys))
        if polygon_dominant and all_keys
        else {"enabled": False}
    )

    return {
        "input_summary": {
            "kmz_path": str(kmz_path),
            "linestring_count": len(doc.linestrings),
            "polygon_count": len(doc.polygons),
            "point_count": len(doc.points),
            "detected_attribute_keys": sorted(all_keys),
            "already_has_permit_area": has_permit_area,
            "already_has_poles": has_poles,
            "already_has_station_ticks": has_ticks,
            "polygon_dominant": polygon_dominant,
        },
        "attribute_roles": attribute_roles,
        "value_classifications": value_classifications,
        "derive": {
            # Skip permit_area inference when polygons themselves are the
            # permit areas (polygon-dominant input).
            "permit_area": (not has_permit_area) and not polygon_dominant,
            "permit_area_buffer_ft": 50,
            "poles": not has_poles,
            "pole_deflection_deg": 5,
            "station_ticks": not has_ticks,
        },
        "balloon": {
            # Polygon-dominant inputs (Sphere/ESRI) ship raw HTML tables in
            # description CDATA -- replace those with the generated balloon
            # so empty / Null fields are suppressed.
            "preserve_existing_descriptions": not polygon_dominant,
            "display_attributes": sorted(all_keys) if polygon_dominant else list(attribute_roles.keys()),
        },
        "polygon_handling": polygon_handling,
        "placemarks": placemarks,
    }


def _print_summary(mapping: dict) -> None:
    """Stdout summary table; matches dxf-to-kmz's inspect output style."""
    s = mapping["input_summary"]
    print(f"Input: {s['kmz_path']}")
    print(f"  {s['linestring_count']} LineStrings, {s['polygon_count']} polygons, {s['point_count']} points")
    print(f"  Detected attribute keys: {', '.join(s['detected_attribute_keys'])}")
    print()
    print("Classified attribute roles:")
    for k, r in mapping["attribute_roles"].items():
        print(f"  {k:20} -> {r}")
    print()
    print("Detection:")
    print(f"  Permit Area present: {s['already_has_permit_area']}")
    print(f"  Poles present:       {s['already_has_poles']}")
    print(f"  Station ticks present: {s['already_has_station_ticks']}")
    print()
    role_counts = {}
    for pm in mapping["placemarks"]:
        role_counts[pm["auto_role"]] = role_counts.get(pm["auto_role"], 0) + 1
    print("Placemark auto-classification:")
    for role, count in sorted(role_counts.items()):
        print(f"  {role:15} {count}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Inspect a KMZ and emit attribute_mapping.json.")
    parser.add_argument("kmz_path", help="Path to input KMZ or KML file")
    parser.add_argument("--output", required=True, help="Output mapping JSON path")
    args = parser.parse_args(argv)

    mapping = inspect(args.kmz_path)
    _print_summary(mapping)
    Path(args.output).write_text(json.dumps(mapping, indent=2))
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
