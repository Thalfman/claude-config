"""
Mode C entity derivation: derive permit entities from a CD alone (no route geometry).

I/O contract
============

Input
-----
- inventory.json from `inventory_inputs.py`
- per-JB cd_meta.json from `extract_cd_titleblock.py` (one per JB in scope)

Output
------
A JSON document:

{
  "mode": "C",
  "pairs": [
    {
      "jb": "JB0002479252",
      "entities": [
        {
          "name": "City of Grand Rapids",
          "kind": "municipality",
          "rationale": "Project address 1860 Alpine Ave NW, Grand Rapids resolves to the City of Grand Rapids (Kent County, incorporated)",
          "confidence": "HIGH"
        },
        {
          "name": "Kent County Road Commission",
          "kind": "county_road_commission",
          "rationale": "Kent County is the project county; CRC is default road authority for unincorporated portions and shared corridors",
          "confidence": "HIGH"
        },
        {
          "name": "MDOT Grand Region",
          "kind": "state_dot_region",
          "rationale": "Site plan road labels include 'M-37' (state trunkline); MDOT Grand Region per references/mdot_regions_by_county.md (Kent County)",
          "confidence": "MEDIUM_VERIFY_MDOT_TABLE"
        }
      ],
      "open_items": [
        "Confirm MDOT Grand Region against current MDOT region map at https://www.michigan.gov/mdot",
        "Verify whether route remains within City of Grand Rapids or briefly enters Walker (verify per address lookup or supplemental site-plan review)"
      ]
    }
  ]
}

Derivation rules
----------------
For each JB in scope:

1. Address lookup:
   - Resolve cd_meta.title_block.address to the incorporating municipality.
   - If address is unincorporated, the County Road Commission (in MI) is the default road jurisdiction.

2. State-route detection on site plans:
   - Scan cd_meta.qc_signals.state_route_labels_detected for I-, US-, M-, BL,
     BR designators (Michigan; extensible per state).
   - For any state-route label found, add the matching state DOT region.
   - For Michigan, look up the region per references/mdot_regions_by_county.md
     keyed by cd_meta.title_block.county.

3. County:
   - Always add the County Road Commission for cd_meta.title_block.county.
   - For MI township-only roads (rare), keep the township OFF the entity list
     and emit a verification Open Item; townships do not issue road permits in MI.

4. Rail / water / wetland crossings:
   - For each entry in cd_meta.qc_signals.rail_crossings_detected,
     add an Open Item to obtain the rail operator's encroachment package
     (license, not permit).
   - For each entry in water_wetland_crossings_detected, add an Open Item
     for the appropriate environmental permit (USACE Section 404, EGLE in MI).

CLI
---

    python -m scripts.derive_entities_modeC inventory.json --cd-meta-dir cd_meta/ --output entity_pairs.json

This is a stub in v1. The full implementation reads cd_meta.json files for
every JB declared as Mode C in inventory.json and runs the four-rule
derivation above.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("inventory_json", type=Path)
    parser.add_argument("--cd-meta-dir", type=Path, default=Path("cd_meta"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    skeleton = {
        "mode": "C",
        "pairs": [],
        "_note": (
            "Stub. Real implementation: load inventory.json, filter JBs declared "
            "Mode C, read each cd_meta.json, run the four derivation rules, "
            "and emit one pairs[] entry per JB with entities + open_items."
        ),
    }
    args.output.write_text(json.dumps(skeleton, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
