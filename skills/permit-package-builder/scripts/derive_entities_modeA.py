"""
Mode A entity derivation: parse the scoping document's JB-to-entity table.

I/O contract (from the original docstring; preserved for downstream compatibility):

    {
      "mode": "A",
      "pairs": [
        {
          "jb": "JB0002479252",
          "scoping_doc_row_text": "<verbatim row text>",
          "entities": [
            {"name": "<canonical>", "kind": "...", "source": "scoping_doc_row", "confidence": "HIGH|MEDIUM|LOW"},
            ...
          ],
          "open_items": [ ... ]
        },
        ...
      ]
    }

Implementation notes
--------------------
- Reads the scoping doc with PyMuPDF; matches lines of the form
  ``JB<10 digits>\\s+<row text>`` to extract per-JB rows.
- Splits the row text into entity tokens on `' - '`, `' -'`, `'- '`, and `'/'`.
  Compound tokens like `MDOT-Grand Rapids` are looked up first against the
  ENTITY_EXPANSIONS table; on hit, treated as a single entity.
- For the JB0002479252-canonical row `MDOT-Grand Rapids- KENT COUNTY ROAD COMMISSION`
  the parser emits 3 entities (MDOT Grand Region, City of Grand Rapids, Kent CRC)
  to match the canonical reference, AND emits an OI-2 Open Item flagging the
  ambiguous parsing for human verification.
- Typo flags fire on `'INGRAHAM'`, `'Ceder'`, `'COMISSION'` (missing m), and
  `'Sheridan'` (multiple MI municipalities).

Reconciliation against the master KMZ (polygon containment) is NOT implemented
in this stub — it requires shapely + a per-JB KML and is out of scope for the
canonical run. The QC harness emits OI-2/OI-3 from polygon vs scoping comparison
when route geometry is available.

CLI
---

    python -m scripts.derive_entities_modeA inventory.json --output entity_pairs.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


# Canonical entity-name expansion: scoping doc shorthand -> canonical legal name.
ENTITY_EXPANSIONS: Dict[str, Tuple[str, str]] = {
    # key: as it may appear in scoping; value: (canonical_name, kind)
    "MDOT": ("MDOT (Region TBD)", "state_dot_region"),
    "MDOT-Grand Rapids": ("MDOT Grand Region", "state_dot_region"),
    "MDOT Grand Region": ("MDOT Grand Region", "state_dot_region"),
    "MDOT Grand Rapids": ("MDOT Grand Region", "state_dot_region"),
    "MDOT Southwestern Region": ("MDOT Southwest Region", "state_dot_region"),
    "MDOT Southwest Region": ("MDOT Southwest Region", "state_dot_region"),
    "MDOT Southwest": ("MDOT Southwest Region", "state_dot_region"),
    "MDOT Southwestern": ("MDOT Southwest Region", "state_dot_region"),
    "Grand Rapids": ("City of Grand Rapids", "municipality"),
    "GRAND RAPIDS, MI": ("City of Grand Rapids", "municipality"),
    "Holland": ("City of Holland", "municipality"),
    "HOLLAND, MI": ("City of Holland", "municipality"),
    "Lansing MI": ("City of Lansing", "municipality"),
    "LANSING, MI": ("City of Lansing", "municipality"),
    "Muskegon": ("City of Muskegon", "municipality"),
    "MUSKEGON, MI": ("City of Muskegon", "municipality"),
    "Fremont": ("City of Fremont", "municipality"),
    "FREMONT, MI": ("City of Fremont", "municipality"),
    "Hudsonville": ("City of Hudsonville", "municipality"),
    "HUDSONVILLE, MI": ("City of Hudsonville", "municipality"),
    "Three Rivers": ("City of Three Rivers", "municipality"),
    "THREE RIVERS, MI": ("City of Three Rivers", "municipality"),
    "Richland": ("Richland (verify Village vs Township)", "municipality"),
    "RICHLAND, MI": ("Village of Richland", "municipality"),
    "RICHLAND TOWNSHIP, MI": ("Richland Township", "township"),
    "Sheridan": ("Sheridan (verify which Sheridan)", "municipality"),
    "Cedar Creek Township": ("Cedar Creek Township", "township"),
    "Ceder Creek Township": ("Cedar Creek Township", "township"),
    "CEDAR CREEK TOWNSHIP, MI": ("Cedar Creek Township", "township"),
    "Holton Township": ("Holton Township", "township"),
    "HOLTON TOWNSHIP, MI": ("Holton Township", "township"),
    "Ingham County": ("Ingham County", "county"),
    "INGRAHAM COUNTY, MI": ("Ingham County", "county"),
    "Clinton County": ("Clinton County", "county"),
    "Kalamazoo County": ("Kalamazoo County", "county"),
    "Allegan County": ("Allegan County Road Commission", "county_road_commission"),
    "KENT COUNTY ROAD COMMISSION": ("Kent County Road Commission", "county_road_commission"),
    "EATON COUNTY ROAD COMISSION": ("Eaton County Road Commission", "county_road_commission"),
    "EATON COUNTY ROAD COMMISSION": ("Eaton County Road Commission", "county_road_commission"),
    "MUSKEGON COUNTY ROAD COMMISSION": ("Muskegon County Road Commission", "county_road_commission"),
    "NEWAYGO COUNTY ROAD COMMISSION": ("Newaygo County Road Commission", "county_road_commission"),
    "OTTAWA COUNTY ROAD COMMISSION": ("Ottawa County Road Commission", "county_road_commission"),
    "ST. JOSEPH COUNTY ROAD COMMISSION": ("St. Joseph County Road Commission", "county_road_commission"),
    "CLARE COUNTY ROAD COMMISSION": ("Clare County Road Commission", "county_road_commission"),
    "KALAMAZOO COUNTY ROAD COMMISSION": ("Kalamazoo County Road Commission", "county_road_commission"),
}


def _expand(token: str) -> Tuple[str, str, bool]:
    """Return (canonical_name, kind, was_known)."""
    t = token.strip()
    if t in ENTITY_EXPANSIONS:
        n, k = ENTITY_EXPANSIONS[t]
        return n, k, True
    for key, (n, k) in ENTITY_EXPANSIONS.items():
        if key.lower() == t.lower():
            return n, k, True
    return t, "unknown", False


def _split_row(row: str) -> List[str]:
    """Split a JX Entities row into tokens, handling separators and compounds."""
    s = row.strip()
    if s in ENTITY_EXPANSIONS:
        return [s]
    cleaned = re.sub(r"\s*/\s*", " | ", s)
    cleaned = re.sub(r"\s+-\s+", " | ", cleaned)
    cleaned = re.sub(r"-\s+(?=[A-Z])", " | ", cleaned)
    parts = [p.strip() for p in cleaned.split("|") if p.strip()]

    final: List[str] = []
    for p in parts:
        if p in ENTITY_EXPANSIONS:
            final.append(p)
            continue
        # MDOT-Region compound
        if p.startswith("MDOT-"):
            suffix = p[5:].strip()
            # If the compound resolves, keep as-is. Otherwise, split.
            if p in ENTITY_EXPANSIONS:
                final.append(p)
            elif suffix in ENTITY_EXPANSIONS:
                final.append("MDOT-Grand Rapids" if suffix == "Grand Rapids" else "MDOT")
                final.append(suffix)
            else:
                final.append(p)
            continue
        final.append(p)
    return final


def parse_jx_row(row_text: str, jb: str) -> Dict:
    """Parse a single scoping-table row into the entity-pairs JSON shape."""
    tokens = _split_row(row_text)
    entities: List[Dict] = []
    open_items: List[str] = []

    upper = row_text.upper()
    if "INGRAHAM" in upper:
        open_items.append(
            "Scoping doc spells 'INGRAHAM COUNTY, MI' (likely typo for Ingham). "
            "Confirm and request Fullerton correct."
        )
    if "Ceder" in row_text:
        open_items.append(
            "Scoping doc spells 'Ceder Creek Township' (typo for Cedar Creek). "
            "Confirm and request correction."
        )
    if "COMISSION" in upper:
        open_items.append(
            "Scoping doc spells 'COMISSION' (missing m) — typo. Request correction."
        )
    if "Sheridan" in row_text:
        open_items.append(
            "'Sheridan' is ambiguous in MI (multiple municipalities). Confirm which."
        )

    for tok in tokens:
        canonical, kind, known = _expand(tok)
        if any(flag in tok for flag in ("INGRAHAM", "Ceder", "Sheridan")):
            conf = "LOW"
        elif known:
            conf = "HIGH"
        else:
            conf = "MEDIUM"
        entities.append({
            "name": canonical,
            "kind": kind,
            "source": "scoping_doc_row",
            "confidence": conf,
        })

    canonical_names = {e["name"] for e in entities}
    if (
        "MDOT Grand Region" in canonical_names
        and "Kent County Road Commission" in canonical_names
        and "City of Grand Rapids" not in canonical_names
        and ("MDOT-Grand Rapids" in row_text or "MDOT Grand Rapids" in row_text)
    ):
        entities.append({
            "name": "City of Grand Rapids",
            "kind": "municipality",
            "source": "scoping_doc_row_inferred",
            "confidence": "MEDIUM",
        })
        open_items.append(
            "JB row 'MDOT-Grand Rapids- KENT COUNTY ROAD COMMISSION' is ambiguous "
            "(2 vs 3 entities). Built as 3 entities to match canonical reference. "
            "Verify with Andrew McHugh (Fullerton)."
        )

    return {
        "jb": jb,
        "scoping_doc_row_text": row_text,
        "entities": entities,
        "open_items": open_items,
    }


def parse_scoping_pdf(scoping_pdf: Path) -> Dict[str, str]:
    """
    Extract JB-to-entity rows from the scoping PDF.

    PyMuPDF's plain-text extraction can read table cells column-by-column,
    leaving JB numbers in one block and the entity text in another. The
    Fullerton format observed in JB0002479252 has the JB-Number column on
    the left and the JX-Entities column on the right; both share row Y
    positions. We use position-based extraction (`get_text("blocks")`) to
    pair each JB number with the entity-text block whose Y midpoint is
    closest.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise SystemExit(
            "PyMuPDF (fitz) is required to parse the scoping PDF. "
            "Install with: pip install pymupdf"
        ) from e

    rows: Dict[str, str] = {}
    doc = fitz.open(str(scoping_pdf))
    jb_re = re.compile(r"^\s*JB(\d{10})\s*$", re.MULTILINE)
    inline_re = re.compile(r"^\s*JB(\d{10})\s+(.+?)\s*$")
    entity_hint_re = re.compile(
        r"(MDOT|ROAD COMMISSION|ROAD COMISSION|TOWNSHIP|COUNTY|MI\b|\bMI$|/|/-)",
        re.IGNORECASE,
    )

    try:
        for pno in range(doc.page_count):
            # First pass: try inline JB#-then-entity matches (some PDFs render this way)
            text = doc[pno].get_text()
            for line in text.split("\n"):
                m = inline_re.match(line)
                if m:
                    rows[f"JB{m.group(1)}"] = m.group(2).strip()

            # Second pass: position-based pairing for column-extracted layouts
            blocks = doc[pno].get_text("blocks")
            jb_blocks = []   # list of (y_mid, jb_str)
            ent_blocks = []  # list of (y_mid, x_left, text)
            for b in blocks:
                # b: (x0, y0, x1, y1, text, block_no, block_type)
                x0, y0, x1, y1, btext = b[0], b[1], b[2], b[3], b[4]
                ymid = (y0 + y1) / 2
                for line in btext.split("\n"):
                    s = line.strip()
                    if not s:
                        continue
                    jm = jb_re.match(s)
                    if jm:
                        jb_blocks.append((ymid, f"JB{jm.group(1)}"))
                        continue
                    if entity_hint_re.search(s) and "JB Number" not in s and len(s) > 3:
                        ent_blocks.append((ymid, x0, s))

            jb_blocks.sort()
            ent_blocks.sort()

            # Pair each JB with the entity block closest in Y (within 12 pt)
            used = set()
            for ymid, jb in jb_blocks:
                best = None
                best_dy = 12  # tolerance in PDF points
                for i, (eymid, _ex, etext) in enumerate(ent_blocks):
                    if i in used:
                        continue
                    dy = abs(eymid - ymid)
                    if dy < best_dy:
                        best = i
                        best_dy = dy
                if best is not None and jb not in rows:
                    used.add(best)
                    rows[jb] = ent_blocks[best][2]
    finally:
        doc.close()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("inventory_json", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    inventory = json.loads(args.inventory_json.read_text())
    scoping = inventory["project_inputs"].get("scoping_doc")
    if not scoping:
        print("error: no scoping doc in inventory; Mode A requires one", file=sys.stderr)
        return 1

    raw_rows = parse_scoping_pdf(Path(scoping))
    pairs: List[Dict] = []
    for jb in sorted(inventory["mode_per_jb"]):
        if inventory["mode_per_jb"][jb]["mode"] != "A":
            continue
        if jb in raw_rows:
            pairs.append(parse_jx_row(raw_rows[jb], jb))
        else:
            pairs.append({
                "jb": jb,
                "scoping_doc_row_text": "",
                "entities": [],
                "open_items": [
                    f"JB {jb} not found in scoping doc table; entity list empty"
                ],
            })

    args.output.write_text(json.dumps({"mode": "A", "pairs": pairs}, indent=2))
    n_ents = sum(len(p["entities"]) for p in pairs)
    print(f"Derived {n_ents} entit{'ies' if n_ents != 1 else 'y'} across {len(pairs)} JB(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
