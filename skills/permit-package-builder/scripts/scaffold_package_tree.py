"""
Create the output folder tree for every (JB, entity) pair.

Reads the entity_pairs.json shape produced by derive_entities_mode{A,B,C}.py
(``{"mode": "A", "pairs": [{"jb": "...", "entities": [...]}]}``) and creates:

    output/
        open_items.md                      # project-wide
        <JB>/
            open_items.md                  # per-JB
            <NN>_<EntityName>/             # NN ordered by submission priority
                research.md (touched)
                fee_calculation.md (touched)

Re-running is idempotent. Existing open_items.md, research.md, and
fee_calculation.md files are NOT clobbered.

Submission priority order (used to pick NN ordinal):
    1. State DOT region offices  (NN starts at 01)
    2. County road commissions
    3. Cities (alphabetical)
    4. Villages (alphabetical)
    5. Townships
    6. Railroads / environmental tracks (last)

CLI:
    python -m scripts.scaffold_package_tree entity_pairs.json --output-root output/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List


def entity_priority(name_or_kind: str, kind: str = "") -> int:
    n = (name_or_kind or "").lower()
    k = (kind or "").lower()
    if "mdot" in n or "department of transportation" in n or "state_dot" in k:
        return 1
    if "road commission" in n or k == "county_road_commission":
        return 2
    if k == "county":
        return 3
    if "city of " in n or k == "municipality":
        return 4
    if "village of " in n:
        return 5
    if "township" in n or k == "township":
        return 6
    return 7


def slugify(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9 ]+", "", name)
    s = re.sub(r"\s+", "_", s.strip())
    return s


PROJECT_OPEN_ITEMS_HEADER = (
    "# Open Items — Project Wide\n\n"
    "Sort: most recent first. Status values: `Open`, `In progress`, "
    "`Resolved`, `Escalated`.\n\n"
    "| Date | JB | Entity | Category | Description | Action / Escalation | Status |\n"
    "|------|----|---------|----------|-------------|---------------------|--------|\n"
)

JB_OPEN_ITEMS_HEADER = (
    "# Open Items — {jb}\n\n"
    "Entity-derivation override lines (specialist initial each before submission):\n\n"
    "| Date | Entity | Category | Description | Action / Escalation | Status |\n"
    "|------|--------|----------|-------------|---------------------|--------|\n"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("entity_pairs_json", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("output"))
    args = parser.parse_args()

    args.output_root.mkdir(parents=True, exist_ok=True)
    project_oi = args.output_root / "open_items.md"
    if not project_oi.exists():
        project_oi.write_text(PROJECT_OPEN_ITEMS_HEADER)

    try:
        data = json.loads(args.entity_pairs_json.read_text())
    except FileNotFoundError:
        print(f"warning: {args.entity_pairs_json} not found; emitting skeleton tree only",
              file=sys.stderr)
        data = {"pairs": []}

    pairs = data.get("pairs", [])
    n_folders = 0
    for pair in pairs:
        jb = pair["jb"]
        jb_dir = args.output_root / jb
        jb_dir.mkdir(exist_ok=True)
        per_jb_oi = jb_dir / "open_items.md"
        if not per_jb_oi.exists():
            per_jb_oi.write_text(JB_OPEN_ITEMS_HEADER.format(jb=jb))

        ents: List[Dict] = pair.get("entities", [])
        ents_sorted = sorted(
            ents,
            key=lambda e: (entity_priority(e["name"], e.get("kind", "")), e["name"])
        )
        for nn, ent in enumerate(ents_sorted, start=1):
            slug = f"{nn:02d}_{slugify(ent['name'])}"
            ent_dir = jb_dir / slug
            ent_dir.mkdir(exist_ok=True)
            (ent_dir / "research.md").touch(exist_ok=True)
            (ent_dir / "fee_calculation.md").touch(exist_ok=True)
            n_folders += 1
        print(f"scaffolded {jb_dir}  ({len(ents_sorted)} entit{'ies' if len(ents_sorted) != 1 else 'y'})")

    print(f"\nTotal entity folders created or confirmed: {n_folders}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
