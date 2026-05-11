"""Stage 2: orchestrator. Apply transformers + emit upgraded KMZ.

Usage:
    python -m scripts.build_kmz input.kmz attribute_mapping.json --output upgraded.kmz
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.kml_model import Document, StyleRole
from scripts.parse_kml import parse_kmz
from scripts.emit_kml import write_kmz
from scripts.transformers import (
    style_restyler,
    permit_area_inferer,
    pole_derivator,
    station_tick_derivator,
    polygon_merger,
    folder_refolder,
    balloon_enricher,
    doc_describer,
)


def build(kmz_path: str | Path, mapping: dict, out_path: str | Path) -> Document:
    doc = parse_kmz(kmz_path)

    # Per-feature override roles from mapping JSON.
    overrides: dict[str, StyleRole] = {}
    for pm in mapping.get("placemarks", []):
        if pm.get("override_role"):
            try:
                overrides[pm["id"]] = StyleRole(pm["override_role"])
            except ValueError:
                pass

    # Filter: drop placemarks marked publish=false.
    drop_ids = {pm["id"] for pm in mapping.get("placemarks", []) if pm.get("publish") is False}
    doc.linestrings = [ls for ls in doc.linestrings if ls.id not in drop_ids]
    doc.points = [p for p in doc.points if p.id not in drop_ids]
    doc.polygons = [p for p in doc.polygons if p.id not in drop_ids]

    role_map = mapping.get("attribute_roles", {})
    derive = mapping.get("derive", {})
    balloon_cfg = mapping.get("balloon", {})
    polygon_handling = mapping.get("polygon_handling", {})

    derivation_log: dict[str, str] = {}

    # 1. Style restyler -- assign style_role + polygon style_override.
    style_restyler.apply(
        doc,
        role_map=role_map,
        overrides=overrides,
        polygon_handling=polygon_handling,
    )

    # 2. Permit area inferer. Skipped automatically when polygon_handling is
    # active (the input polygons themselves are the permit areas).
    polys_before = len(doc.polygons)
    permit_area_inferer.apply(
        doc,
        derive=derive.get("permit_area", True) and not polygon_handling.get("enabled"),
        buffer_ft=derive.get("permit_area_buffer_ft", 50),
    )
    if len(doc.polygons) > polys_before:
        derivation_log["permit_area"] = (
            f"inferred from buffered route hull "
            f"({derive.get('permit_area_buffer_ft', 50)}ft)"
        )

    # 3. Pole derivator.
    pts_before = len([p for p in doc.points if p.style_role is StyleRole.POLE])
    pole_derivator.apply(
        doc,
        derive=derive.get("poles", True),
        deflection_deg=derive.get("pole_deflection_deg", 5),
    )
    pts_after = len([p for p in doc.points if p.style_role is StyleRole.POLE])
    if pts_after > pts_before:
        derivation_log["poles"] = f"derived {pts_after - pts_before} from aerial vertex deflection"

    # 4. Station-tick derivator.
    ticks_before = len([p for p in doc.points if p.style_role is StyleRole.STATION])
    station_tick_derivator.apply(
        doc,
        derive=derive.get("station_ticks", True),
        role_map=role_map,
    )
    ticks_after = len([p for p in doc.points if p.style_role is StyleRole.STATION])
    if ticks_after > ticks_before:
        derivation_log["station_ticks"] = f"derived {ticks_after - ticks_before} from chainage attributes"

    # 5. Polygon merger -- collapse same-PRM polygons into MultiGeometry.
    merged_count = polygon_merger.apply(doc, polygon_handling=polygon_handling)
    if merged_count:
        derivation_log["polygon_merger"] = (
            f"merged {merged_count} polygons into shared MultiGeometry placemarks "
            f"keyed on `{polygon_handling.get('merge_at')}`"
        )

    # 6. Folder refolder.
    folder_refolder.apply(doc, polygon_handling=polygon_handling)

    # 7. Balloon enricher.
    balloon_enricher.apply(
        doc,
        display_attributes=balloon_cfg.get("display_attributes", []),
        preserve_existing=balloon_cfg.get("preserve_existing_descriptions", True),
    )

    # 8. Doc describer.
    doc_describer.apply(doc, derivation_log=derivation_log)

    # Emit.
    write_kmz(doc, out_path)
    return doc


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the upgraded KMZ from input + mapping.")
    parser.add_argument("kmz_path", help="Path to input KMZ or KML file")
    parser.add_argument("mapping_path", help="Path to attribute_mapping.json")
    parser.add_argument("--output", required=True, help="Output upgraded KMZ path")
    args = parser.parse_args(argv)

    mapping = json.loads(Path(args.mapping_path).read_text())
    build(args.kmz_path, mapping, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
