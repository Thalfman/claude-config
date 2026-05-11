"""
Run the mode-conditional QC list against a (JB, entity) package.

I/O contract
============

Inputs
------
- A package folder path: output/<JB>/<NN_Entity>/
- inventory.json (for the JB's declared mode)
- jb cd_meta.json (extracted title-block + qc_signals)

Output
------
Two artifacts in the package folder:

- qc_report.md: human-readable per-check pass/fail with evidence
- (Side effect) appends rows to output/<JB>/open_items.md and
  output/open_items.md for any check that fires.

Check registry
--------------
The full list lives in references/quality_checks.md. The script implements
each check as a function that returns:

    @dataclass
    class CheckResult:
        check_id: str       # 'QC-001'
        name: str           # '811 callout matches state of work'
        applies: bool       # whether this check applies given the mode
        passed: bool
        evidence: str       # one-line summary of what was tested and what was found
        action: str | None  # what to do next, if failed

Core checks (all modes): QC-001 through QC-008
Mode A specific:        QC-101 through QC-103
Mode B specific:        QC-201 through QC-202
Mode C specific:        QC-301 through QC-302

CLI
---

    python -m scripts.run_quality_checks \
        --package-dir output/JB0002479252/01_MDOT_Grand_Region/ \
        --inventory inventory.json \
        --cd-meta cd_meta_JB0002479252.json

The script exits 0 if every applicable check passes, 1 if any fail. Failed
checks are also surfaced via Open Items so the human reviewer sees them in
both places.

This is a stub in v1. Each check function will be implemented in turn,
starting with QC-001 (811 callout) and QC-002 (boilerplate company name)
since they fire on the JB0002479252 reference set.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--cd-meta", type=Path, required=True)
    args = parser.parse_args()

    report = args.package_dir / "qc_report.md"
    report.write_text(
        "# QC Report (stub)\n\n"
        "Real implementation runs the check registry and writes per-check "
        "rows here. See references/quality_checks.md for the full list.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
