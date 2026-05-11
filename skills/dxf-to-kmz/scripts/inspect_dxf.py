"""Walk a DXF file, classify layers, write layer_mapping.json."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

import ezdxf

from scripts.detect_crs import detect_crs
from scripts.layer_conventions import classify


def _count_entities_per_layer(doc) -> dict[str, Counter]:
    counts: dict[str, Counter] = {}
    for entity in doc.modelspace():
        layer = entity.dxf.layer
        counts.setdefault(layer, Counter())[entity.dxftype()] += 1
    # Ensure every defined layer is in the result, even with zero entities
    for layer in doc.layers:
        counts.setdefault(layer.dxf.name, Counter())
    return counts


def inspect_dxf(dxf_path: Path,
                output_path: Optional[Path] = None,
                defaults_path: Optional[Path] = None) -> dict:
    """Inspect a DXF, return a layer_mapping dict, optionally write to disk."""
    dxf_path = Path(dxf_path)

    doc = ezdxf.readfile(str(dxf_path))
    counts = _count_entities_per_layer(doc)

    layers_out = []
    for layer_name in sorted(counts.keys()):
        ent_counts = dict(counts[layer_name])
        cls = classify(layer_name)

        layer_entry = {
            "name": layer_name,
            "entity_counts": ent_counts,
            "publish": cls["publish"],
            "feature": cls["feature"],
            "subtype": cls["subtype"],
            "folder": cls["folder"],
            "style": cls["style"],
            "matched_rule": cls["matched_rule"],
        }
        if cls["feature"] is None:
            layer_entry["_note"] = (
                "Unmapped - no convention matched. "
                "Set feature + style to publish."
            )
        elif cls["subtype"] == "existing":
            layer_entry["_note"] = (
                "Existing - default off; flip publish:true to include for context"
            )

        layers_out.append(layer_entry)

    crs_kwargs = {}
    if defaults_path is not None:
        crs_kwargs["defaults_path"] = defaults_path
    crs = detect_crs(dxf_path, **crs_kwargs)

    mapping = {
        "source_dxf": dxf_path.name,
        "crs": crs,
        "kmz_meta": {
            "title": dxf_path.stem,
            "description": (
                "Generated from DXF for contractor work-area handoff. "
                "Not for engineering layout."
            ),
        },
        "layers": layers_out,
    }

    if output_path:
        Path(output_path).write_text(json.dumps(mapping, indent=2))

    return mapping


def main():
    parser = argparse.ArgumentParser(description="Inspect a DXF and emit layer_mapping.json")
    parser.add_argument("dxf_path", type=Path)
    parser.add_argument("--output", type=Path, default=Path("layer_mapping.json"))
    parser.add_argument("--defaults", type=Path, default=None,
                        help="Override default regional CRS table")
    args = parser.parse_args()

    mapping = inspect_dxf(args.dxf_path, output_path=args.output,
                          defaults_path=args.defaults)

    print(f"Wrote {args.output}")
    print(f"  Source DXF: {mapping['source_dxf']}")
    print(f"  CRS tier {mapping['crs']['tier']}: "
          f"{mapping['crs'].get('epsg') or 'manual anchors required'} "
          f"({mapping['crs']['confidence']})")
    print(f"  Layers: {len(mapping['layers'])}")
    publish_count = sum(1 for L in mapping["layers"] if L["publish"])
    print(f"  Default-publish: {publish_count}, default-off: {len(mapping['layers']) - publish_count}")


if __name__ == "__main__":
    sys.exit(main())
