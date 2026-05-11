"""
Walk a working folder and detect the input mode (A / B / C) per JB.

I/O contract: see this module's docstring at the bottom of the file.
Mode rules:
  - Mode A: project has scoping doc + master KMZ AND the JB has its own KML.
  - Mode B: JB has its own KML but scoping doc or master KMZ are missing.
  - Mode C: JB has only a CD; no KML.

CLI:
    python -m scripts.inventory_inputs <working_folder> --output inventory.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


JB_RE = re.compile(r"JB(\d{10})")
SCOPING_DOC_HINTS = ("scoping", "jx", "fullerton", "project")
MASTER_KMZ_HINTS = ("projects", "master", "mastec_michigan", "permit_polygons")


def _classify_file(path: Path) -> Tuple[str, Optional[str]]:
    """
    Return (kind, jb_or_none) for a single file.
    kind ∈ {'cd_pdf', 'kml', 'master_kmz', 'scoping_doc', 'contacts_md', 'other'}.
    """
    name = path.name
    name_lower = name.lower()
    suffix = path.suffix.lower()
    jb_match = JB_RE.search(name)
    jb = f"JB{jb_match.group(1)}" if jb_match else None

    if suffix == ".pdf" and jb:
        return ("cd_pdf", jb)
    if suffix in (".kml",) and jb:
        return ("kml", jb)
    if suffix == ".kmz" and not jb:
        return ("master_kmz", None)
    if suffix == ".pdf" and not jb:
        # Scoping doc heuristic: a PDF without a JB number that sits near multiple
        # JB-numbered PDFs. We confirm later in the main inventory pass.
        return ("scoping_doc_candidate", None)
    if name_lower == "contacts.md":
        return ("contacts_md", None)
    return ("other", None)


def _select_master_kmz(candidates: List[Path]) -> Optional[Path]:
    """Pick the most-likely master jurisdictional KMZ from a list of candidates."""
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    # Prefer files whose name matches the master-KMZ hints.
    for c in candidates:
        n = c.name.lower()
        if any(h in n for h in MASTER_KMZ_HINTS):
            return c
    # Fall back to the largest KMZ (master polygons tend to be substantial).
    return max(candidates, key=lambda p: p.stat().st_size)


def _select_scoping_doc(candidates: List[Path], cd_count: int) -> Optional[Path]:
    """
    Pick the most-likely scoping PDF. Heuristic: a non-JB-named PDF in the
    presence of multiple JB-named CDs is the scoping document. If exactly one
    candidate exists, return it.
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    for c in candidates:
        n = c.name.lower()
        if any(h in n for h in SCOPING_DOC_HINTS):
            return c
    # If multiple candidates and no strong hint, prefer the smallest (scoping
    # docs are typically a few pages; CDs are dozens of pages).
    return min(candidates, key=lambda p: p.stat().st_size)


def _declare_mode(jb: str, cd_pdf: Optional[Path], kml: Optional[Path],
                  scoping_doc: Optional[Path], master_kmz: Optional[Path]) -> Tuple[str, str]:
    """Return (mode, rationale) per the rules in SKILL.md."""
    if not cd_pdf:
        return ("MISSING_CD", f"{jb}: CD PDF not found in working folder")
    if scoping_doc and master_kmz and kml:
        return ("A", "scoping doc, master KMZ, KML, and CD all present")
    if kml:
        missing = []
        if not scoping_doc: missing.append("scoping doc")
        if not master_kmz: missing.append("master KMZ")
        return ("B", f"KML and CD present; falling back from Mode A (missing: {', '.join(missing)})")
    return ("C", "only CD present; no KML")


def inventory(working_folder: Path) -> Dict:
    """Walk the folder and return the inventory dict."""
    cd_pdfs: Dict[str, Path] = {}
    kmls: Dict[str, Path] = {}
    master_kmz_candidates: List[Path] = []
    scoping_candidates: List[Path] = []
    contacts_md: Optional[Path] = None
    other: List[Path] = []

    for entry in working_folder.iterdir():
        if not entry.is_file():
            continue
        kind, jb = _classify_file(entry)
        if kind == "cd_pdf":
            cd_pdfs[jb] = entry
        elif kind == "kml":
            kmls[jb] = entry
        elif kind == "master_kmz":
            master_kmz_candidates.append(entry)
        elif kind == "scoping_doc_candidate":
            scoping_candidates.append(entry)
        elif kind == "contacts_md":
            contacts_md = entry
        else:
            other.append(entry)

    master_kmz = _select_master_kmz(master_kmz_candidates)
    scoping_doc = _select_scoping_doc(scoping_candidates, cd_count=len(cd_pdfs))

    mode_per_jb = {}
    missing: List[str] = []
    for jb in sorted(set(list(cd_pdfs.keys()) + list(kmls.keys()))):
        cd = cd_pdfs.get(jb)
        kml = kmls.get(jb)
        mode, rationale = _declare_mode(jb, cd, kml, scoping_doc, master_kmz)
        if mode == "MISSING_CD":
            missing.append(rationale)
            continue
        mode_per_jb[jb] = {
            "mode": mode,
            "cd_pdf": str(cd) if cd else None,
            "kml": str(kml) if kml else None,
            "scoping_doc": str(scoping_doc) if scoping_doc else None,
            "master_kmz": str(master_kmz) if master_kmz else None,
            "rationale": f"Mode {mode}: {rationale}",
        }

    return {
        "working_folder": str(working_folder.resolve()),
        "mode_per_jb": mode_per_jb,
        "project_inputs": {
            "scoping_doc": str(scoping_doc) if scoping_doc else None,
            "master_kmz": str(master_kmz) if master_kmz else None,
            "contacts_md": str(contacts_md) if contacts_md else None,
        },
        "missing": missing,
        "all_jbs_seen": sorted(set(list(cd_pdfs.keys()) + list(kmls.keys()))),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("working_folder", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not args.working_folder.is_dir():
        print(f"error: {args.working_folder} is not a directory", file=sys.stderr)
        return 1

    result = inventory(args.working_folder)
    args.output.write_text(json.dumps(result, indent=2))
    n = len(result["mode_per_jb"])
    modes = sorted(set(v["mode"] for v in result["mode_per_jb"].values()))
    print(f"Inventoried {n} JB(s); mode(s) {modes}; missing {len(result['missing'])} input(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
