"""
Generate the per-package transmittal index (submission cover sheet) listing
every artifact in the package with page counts and revision dates.

I/O contract
============

Inputs
------
- A package folder path: output/<JB>/<NN_Entity>/
- The folder contains the drafted artifacts; this script enumerates them.

Output
------
A PDF (transmittal_index.pdf) and a DOCX intermediate
(transmittal_index.docx) at the package folder root.

Layout
------
The transmittal index is a single sheet (or first page of a multi-sheet
package) that the entity uses to confirm the package is complete on receipt.
Columns:

| #  | Artifact                  | File                       | Pages | Revision Date | Notes                                  |
|----|---------------------------|----------------------------|-------|---------------|----------------------------------------|
| 1  | Cover Letter              | cover_letter.pdf           | 1     | 2026-04-27    |                                        |
| 2  | Application Form          | application_form.pdf       | 4     | 2026-04-25    | MDOT v2026-03                          |
| 3  | Construction Drawings     | construction_drawings.pdf  | 20    | 2026-04-14    | 811 callout updated to Miss Dig 811    |
| 4  | Route Map                 | route_map.pdf              | 1     | 2026-04-27    |                                        |
| 4a | KML                       | route.kml                  |       | 2026-04-14    |                                        |
| 5  | Traffic Control Plan      | traffic_control_plan.pdf   | 2     | 2026-04-27    | MUTCD typical TA-10                    |
| 6  | COI                       | coi.pdf                    | 1     | 2026-04-20    | $1M GL, MDOT additional insured        |
| 7  | Bond / Surety             |                            |       |               | Not required for this entity           |
| 8  | Fee Calculation           | fee_calculation.md         | 1     | 2026-04-27    | Fee schedule retrieved 2026-04-25      |
| 9  | Supporting Attachments    | (per attachment list)      | n     | n             |                                        |
| 10 | This Transmittal Index    | transmittal_index.pdf      | 1     | 2026-04-27    |                                        |

The index also carries (header):
- JB number
- Entity name
- Project address
- Submitted by (MasTec submitting contact)
- Submission date

And (footer):
- Total package page count
- Submission method (online portal URL, email, paper, hand delivery)

CLI
---

    python -m scripts.build_transmittal_index \
        --package-dir output/JB0002479252/01_MDOT_Grand_Region/ \
        --jb-meta cd_meta.json \
        --entity-research output/JB0002479252/01_MDOT_Grand_Region/research.md

This is a stub in v1. Full implementation enumerates the package folder,
reads page counts from each PDF (via pymupdf), parses revision dates from
each artifact's title block where applicable, and renders the index from
assets/transmittal_index_template.docx (or .md source).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--jb-meta", type=Path, required=True)
    parser.add_argument("--entity-research", type=Path, required=True)
    args = parser.parse_args()

    placeholder = args.package_dir / "transmittal_index.md"
    placeholder.write_text(
        "<!-- Stub: transmittal index. Real implementation enumerates "
        "the package folder, pulls page counts and revision dates per "
        "the I/O contract in scripts/build_transmittal_index.py. -->\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
