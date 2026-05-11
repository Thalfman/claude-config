"""
Mode B entity derivation: route geometry plus published jurisdictional boundaries
(no scoping document).

I/O contract
============

Input
-----
- inventory.json (Mode B JBs and their KML paths)
- A boundary-layer cache (state DOT regions, county boundaries, municipal
  boundaries, railroad corridors, environmental layers). Format: a directory
  of GeoJSON files keyed by `<state>_<layer>.geojson`. The cache is built
  out-of-band and is not produced by this script.

Output
------
A JSON document:

{
  "mode": "B",
  "pairs": [
    {
      "jb": "JB0002479252",
      "kml": "<path>",
      "entities": [
        {"name": "City of Grand Rapids", "kind": "municipality", "containment": "fully_inside",  "confidence": "HIGH"},
        {"name": "Kent County Road Commission", "kind": "county_road_commission", "containment": "primary_county", "confidence": "HIGH"},
        {"name": "MDOT Grand Region", "kind": "state_dot_region", "containment": "state_route_overlap", "confidence": "HIGH"}
      ],
      "open_items": [
        "Route enters Walker for ~120 ft along Alpine Ave NW north of I-96; verify whether Walker requires a permit for this length or is covered by Kent CRC under a corridor agreement"
      ]
    }
  ]
}

Derivation rules
----------------
For each Mode B JB:

1. Load the per-JB KML route geometry as a shapely LineString (or
   MultiLineString) in EPSG:4326.

2. State DOT region/district:
   - Buffer the route lightly (e.g. 5 m) and intersect with each state-route
     centerline layer. If any intersection > 0, add the state DOT region
     covering the project county.

3. County:
   - Find the county containing the route's centroid. This is the primary
     county; add its County Road Commission.
   - If the route crosses a county boundary, add the secondary CRC too.

4. Municipality:
   - Buffer the route (e.g. 20 m) and intersect with municipal-boundary
     polygons. For each polygon the buffered route enters, add that
     municipality.
   - For routes outside any incorporated municipality in MI: default road
     jurisdiction is the County Road Commission (no township).

5. Railroad / environmental:
   - For railroad corridor crossings, add an Open Item to obtain the rail
     operator's encroachment package.
   - For NWI / EGLE / USACE layer crossings, add an Open Item for the
     appropriate environmental permit.

CLI
---

    python -m scripts.derive_entities_modeB inventory.json --boundary-cache boundaries/ --output entity_pairs.json

This is a stub in v1. The full implementation requires shapely + pyproj +
a populated boundary-layer cache; cache build instructions live in a future
references/boundary_cache_build.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("inventory_json", type=Path)
    parser.add_argument("--boundary-cache", type=Path, default=Path("boundaries"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    skeleton = {
        "mode": "B",
        "pairs": [],
        "_note": (
            "Stub. Real implementation: load each Mode B JB's KML, run "
            "containment checks against the boundary cache layers, emit "
            "entities with containment evidence."
        ),
    }
    args.output.write_text(json.dumps(skeleton, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
