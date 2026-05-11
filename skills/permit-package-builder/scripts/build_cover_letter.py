"""
Generate a cover letter from the parameterized template for one (JB, entity) pair.

I/O contract
============

Inputs
------
- jb_meta.json (output of extract_cd_titleblock.py for the JB)
- entity_research.md (output of the per-entity research step; key fields parsed
  for permit administrator name + address)
- contacts source (working-folder contacts.md if present, else CD title-block
  contacts, else standing references in references/canonical_cd_format.md)
- assets/cover_letter_template.docx (or assets/cover_letter_template.md, which
  this script uses as the source-of-truth in v1)

Substitution fields (mapped 1:1 from template placeholders to runtime values):

| Placeholder            | Source                                       |
|------------------------|----------------------------------------------|
| {{date}}               | today, ISO 8601                              |
| {{entity_name}}        | entity_research.md "Entity legal name"       |
| {{permit_admin_name}}  | entity_research.md "Permit administrator name" |
| {{permit_admin_title}} | entity_research.md "Permit administrator title" |
| {{permit_admin_addr}}  | entity_research.md office address            |
| {{jb_number}}          | jb_meta.title_block.jb_number                |
| {{project_address}}    | jb_meta.title_block.address                  |
| {{scope_summary}}      | computed from jb_meta.totals partitioned by entity |
| {{work_window}}        | "to be coordinated with permit issuance" or OPE-confirmed |
| {{submitting_name}}    | contacts source MasTec lead                  |
| {{submitting_phone}}   | contacts source MasTec lead phone            |
| {{submitting_email}}   | contacts source MasTec lead email            |
| {{office_address}}     | contacts source MasTec office of record      |

Output
------
A PDF (cover_letter.pdf) and a DOCX intermediate (cover_letter.docx) saved to
the package folder.

CLI
---

    python -m scripts.build_cover_letter \
        --jb-meta cd_meta.json \
        --entity-research output/JB0002479252/01_MDOT_Grand_Region/research.md \
        --contacts contacts.md \
        --output-dir output/JB0002479252/01_MDOT_Grand_Region/

Style guardrails enforced by the template
-----------------------------------------
- Three short paragraphs maximum
- Professional plain prose; no marketing language
- No committed start date unless OPE-confirmed; placeholder otherwise
- "Comcast, by MasTec Communications Group as agent" applicant statement

This is a stub in v1. The asset templates live at
assets/cover_letter_template.md (markdown source-of-truth) and
assets/cover_letter_template.docx (the DOCX target generated from the .md
via pandoc or python-docx). When the .docx version exists, the script uses it
directly; when only the .md exists, the script renders to .docx via python-docx.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--jb-meta", type=Path, required=True)
    parser.add_argument("--entity-research", type=Path, required=True)
    parser.add_argument("--contacts", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    placeholder = args.output_dir / "cover_letter.md"
    placeholder.write_text(
        "<!-- Stub: cover letter for ${entity} on ${jb}. "
        "Real implementation substitutes the template placeholders per the "
        "I/O contract in scripts/build_cover_letter.py. -->\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
