"""
Extract title-block fields and quality-check signals from a CD PDF.

I/O contract
============

Input
-----
A path to a per-JB CD PDF (multi-page, title-block on every page).

Output
------
A JSON document with this shape:

{
  "pdf_path": "<absolute path>",
  "page_count": <int>,
  "title_block": {
    "jb_number": "JB0002479252",
    "project_name": "<text>",
    "address": "1860 Alpine Ave NW, Grand Rapids, MI 49504",
    "city": "Grand Rapids",
    "state": "MI",
    "zip": "49504",
    "county": "Kent",
    "township": "City of Grand Rapids",
    "range": "<text or null>",
    "section": "<text or null>",
    "lat": 42.9956,
    "lon": -85.6803,
    "scale_text": "1 INCH = 40 FEET",
    "drafter_block": "MasTec Communications Group ...",
    "client_block": "Comcast",
    "revision_date": "2026-04-14"
  },
  "contacts_block": {
    "comcast": {"name": "Don Carr", "phone": "(317) 914-9071", "email": "doncarr@cable.comcast.com"},
    "mastec":  {"name": "Thomas Halfman", "phone": "224-277-1041", "email": "thomas.halfman@mastec.com"}
  },
  "sheet_index": [
    {"page": 1, "sheet_label": "COVER",       "type": "cover"},
    {"page": 2, "sheet_label": "VICINITY",    "type": "vicinity_index"},
    {"page": 3, "sheet_label": "GEN NOTES",   "type": "notes"},
    {"page": 4, "sheet_label": "LEGEND",      "type": "legend"},
    {"page": 5, "sheet_label": "SITE PLAN - 1", "type": "site_plan", "ordinal": 1},
    ...
  ],
  "description_of_work": [
    {"sheet_label": "SITE PLAN - 1", "lf_aerial": 425, "lf_ug": 0,
     "poles": 6, "vaults": 0, "bores": 0, "notes": "Overlash on existing GR strand"},
    ...
  ],
  "totals": {"lf_aerial": <int>, "lf_ug": <int>, "poles": <int>, "vaults": <int>, "bores": <int>},
  "qc_signals": {
    "found_811_callout": "Indiana 811",                   # exact text matched
    "expected_811_for_state": "Miss Dig 811",             # from references/state_811_systems.md
    "boilerplate_company_names": ["SEFNCO Communication, Inc."],
    "rail_crossings_detected": [],
    "water_wetland_crossings_detected": [],
    "state_route_labels_detected": ["M-37", "US-131"]
  }
}

CLI
---

    python -m scripts.extract_cd_titleblock <pdf_path> --output cd_meta.json

Optional flag:
    --scrub  Apply boilerplate scrubs and write a corrected PDF beside the
             input (`<stem>_scrubbed.pdf`). Driven by
             references/known_boilerplate_errors.md and the QC signals.

This is a stub in v1. The full implementation uses pymupdf to read text per
page, locate the title block (bottom-right of the rendered page given the
typical 270-degree rotation flag), parse the description-of-work table, and
fire the QC signals listed above.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scrub", action="store_true",
                        help="Apply boilerplate scrubs and write a corrected PDF.")
    args = parser.parse_args()

    if not args.pdf_path.is_file():
        print(f"error: {args.pdf_path} not found", file=sys.stderr)
        return 1

    skeleton = {
        "pdf_path": str(args.pdf_path.resolve()),
        "page_count": 0,
        "title_block": {},
        "contacts_block": {},
        "sheet_index": [],
        "description_of_work": [],
        "totals": {},
        "qc_signals": {},
        "_note": (
            "Stub. Real implementation: pymupdf to read pages 1-3 for title-block "
            "metadata, vicinity contacts block, and general notes. Parse "
            "description-of-work table on page 2. QC scrubs per "
            "references/known_boilerplate_errors.md and references/state_811_systems.md."
        ),
    }
    args.output.write_text(json.dumps(skeleton, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
