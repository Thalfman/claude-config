"""
Extract a single source-of-truth `project_facts.json` for one JB from its
CD PDF + (optional) KML. Every reviewer-facing draft (cover letter,
application form, fee calculation, transmittal, route exhibit) reads
from this JSON instead of re-extracting facts on each render.

CLI
---
    python -m scripts.extract_project_facts <JB_folder> [--output-dir DIR]
    python -m scripts.extract_project_facts --all <Deliverables_root>

Single-JB mode reads the .pdf and .kml from the supplied folder. Output
lands at `output/<JB#>/project_facts.json` by default; override with
`--output-dir`. Multi-JB (`--all`) walks the root, processes every
sub-folder containing a CD PDF, and writes one project_facts.json per JB.

Output schema is at references/project_facts_schema.md (companion doc;
this script's JSON-writer is the canonical reference).

Provenance philosophy
---------------------
Every populated field carries an implicit provenance chain. When a value
is null, it's either genuinely absent in the inputs or the extractor
couldn't find it. Stuff in `open_questions` calls out the gaps so the
specialist knows what to verify by hand.

Failure mode: if the script can't extract something, it sets the field
to null and adds a line to `open_questions`. It does not invent data.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0.0"
M_TO_FT = 3.280839895013123
JB_RE = re.compile(r"\bJB(\d{10})\b")

# 5-character pole-tag patterns (Consumers Energy MI). 6-7 digit (AT&T MI).
# Pole-tag patterns are documented in the registry; this script doesn't
# attempt owner classification — that's pole-attachment-package work.

# DMS like 43°23'13.1"N or 86°05'54.0"W (also tolerate plain ASCII deg/min/sec)
DMS_RE = re.compile(
    r"(\d+)\s*[°\xb0d]\s*(\d+)\s*[′'’m]\s*([\d.]+)\s*[″\"”s]?\s*([NSEW])",
    re.IGNORECASE,
)

# 811 callouts seen in CDs that we know are wrong on a Michigan project.
CD_811_PATTERNS = {
    "MI": "Miss Dig 811",
    "IN": "Indiana 811",
    "IL": "JULIE",
    "OH": "OHIO811",
    "WI": "Diggers Hotline",
    "PA": "PA One Call",
    "WA_legacy": "1-800-424-5555",  # SEFNCO leftover
}


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def parse_kml_coords(text: str) -> list[tuple[float, float]]:
    out = []
    for tok in (text or "").strip().split():
        parts = tok.split(",")
        if len(parts) >= 2:
            try:
                lon, lat = float(parts[0]), float(parts[1])
                out.append((lat, lon))
            except ValueError:
                continue
    return out


def line_length_m(coords_text: str) -> float:
    pts = parse_kml_coords(coords_text)
    return sum(haversine_m(a[0], a[1], b[0], b[1]) for a, b in zip(pts, pts[1:]))


def dms_to_decimal(dms: str) -> float | None:
    m = DMS_RE.search(dms or "")
    if not m:
        return None
    deg, mn, sec, hemi = m.group(1), m.group(2), m.group(3), m.group(4).upper()
    val = int(deg) + int(mn) / 60 + float(sec) / 3600
    if hemi in ("S", "W"):
        val = -val
    return round(val, 6)


# ---------------------------------------------------------------------------
# Registry loader (canonical entity data; see references/mi_entity_registry.json)
# ---------------------------------------------------------------------------

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "references" / "mi_entity_registry.json"


def load_registry() -> dict:
    return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# CD PDF title-block reader
# ---------------------------------------------------------------------------

def read_pdf_pages_text(pdf_path: Path, max_pages: int = 5) -> tuple[int, list[str]]:
    """Return (total_page_count, [text per page] up to max_pages)."""
    import fitz  # pymupdf
    pdf = fitz.open(str(pdf_path))
    pages_text = []
    for i in range(min(len(pdf), max_pages)):
        pages_text.append(pdf.load_page(i).get_text())
    page_count = len(pdf)
    pdf.close()
    return page_count, pages_text


def parse_cd_titleblock(pages: list[str]) -> dict:
    """Parse the cover sheet (page 1) plus a slice of page 2/3 for context."""
    p1 = pages[0] if pages else ""
    p2 = pages[1] if len(pages) > 1 else ""
    p3 = pages[2] if len(pages) > 2 else ""
    p1_p2 = p1 + "\n" + p2
    full = p1 + "\n" + p2 + "\n" + p3

    out: dict[str, Any] = {
        "jb_number": None,
        "project_name": None,
        "address": None,
        "city": None,
        "state": None,
        "zip": None,
        "county": None,
        "township": None,
        "range": None,
        "section": None,
        "qtr_section": None,
        "lat_dms": None,
        "lat_decimal": None,
        "lon_dms": None,
        "lon_decimal": None,
        "title_clause": None,
        "drafter_block": {
            "drawn_by": None,
            "engineer": None,
            "engineer_phone": None,
            "drafter_company": None,
            "drafter_address": None,
            "title_block_date": None,
        },
        "_provenance": "cd_pages_1-3_text",
    }

    m = JB_RE.search(full)
    if m:
        out["jb_number"] = "JB" + m.group(1)

    pn = re.search(r"PROJECT NAME\s*:\s*([^\n]+)", p1, re.IGNORECASE)
    if pn:
        out["project_name"] = pn.group(1).strip()

    addr = re.search(r"\b(\d{1,6}[^\n]+,\s*[A-Z][A-Za-z .'-]+,\s*[A-Z]{2}\s*\d{5}(?:,\s*USA)?)", p1)
    if addr:
        a = addr.group(1).strip().rstrip(",")
        out["address"] = a
        am = re.search(r",\s*([A-Z][A-Za-z .'-]+),\s*([A-Z]{2})\s*(\d{5})", a)
        if am:
            out["city"] = am.group(1).strip()
            out["state"] = am.group(2)
            out["zip"] = am.group(3)

    cn = re.search(r"\b([A-Z][A-Z .'-]+?)\s+COUNTY\b", p1)
    if cn:
        out["county"] = cn.group(1).strip().title().replace("'S", "'s")

    sec = re.search(r"SECTION\s*:?\s*\n?\s*(S?\d{1,3}[A-Z]?)", p1)
    if sec: out["section"] = sec.group(1).strip()
    rng = re.search(r"RANGE\s*:?\s*\n?\s*(R\d{1,3}[EW])", p1)
    if rng: out["range"] = rng.group(1).strip()
    twp = re.search(r"TOWNSHIP\s*:?\s*\n?\s*(T\d{1,3}[NS])", p1)
    if twp: out["township"] = twp.group(1).strip()
    qtr = re.search(r"QTR\s+SECTION\s*:?\s*\n?\s*(NW|NE|SW|SE)", p1)
    if qtr: out["qtr_section"] = qtr.group(1).strip()

    lat_match = DMS_RE.search(p1)
    if lat_match and lat_match.group(4).upper() in ("N", "S"):
        out["lat_dms"] = lat_match.group(0)
        out["lat_decimal"] = dms_to_decimal(lat_match.group(0))
        rest = p1[lat_match.end():]
        lon_match = DMS_RE.search(rest)
        if lon_match and lon_match.group(4).upper() in ("E", "W"):
            out["lon_dms"] = lon_match.group(0)
            out["lon_decimal"] = dms_to_decimal(lon_match.group(0))

    title = re.search(r"TITLE\s*:?\s*([^\n]+(?:\n[^\n]+)?)", p1, re.IGNORECASE)
    if title:
        clause = " ".join(title.group(1).split())
        out["title_clause"] = clause

    drawn = re.search(r"DRAWN BY\s*:?\s*\n?\s*([^\s\n]+)", p1, re.IGNORECASE)
    if drawn: out["drafter_block"]["drawn_by"] = drawn.group(1).strip()
    eng_email = re.search(r"\b([A-Z0-9._-]+@[A-Z0-9._-]+\.[A-Z]{2,})\b", p1, re.IGNORECASE)
    if eng_email: out["drafter_block"]["engineer"] = eng_email.group(1)
    eng_phone = re.search(r"PHONE\s*:?\s*\n?\s*(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})", p1, re.IGNORECASE)
    if eng_phone: out["drafter_block"]["engineer_phone"] = eng_phone.group(1).strip()
    if re.search(r"MASTEC\s+COMMUNICATIONS", p1, re.IGNORECASE):
        out["drafter_block"]["drafter_company"] = "MasTec Communications Group"
    addr_drafter = re.search(r"(\d{4,5}[^\n]+(?:STREET|ST|AVE|AVENUE|ROAD|RD|BLVD|BOULEVARD)[^\n]*\n[^\n]+,\s*IN\s*\d{5})", p1, re.IGNORECASE)
    if addr_drafter: out["drafter_block"]["drafter_address"] = " ".join(addr_drafter.group(1).split())
    date = re.search(r"DATE\s*:?\s*\n?\s*(\d{2}/\d{2}/\d{2,4})", p1, re.IGNORECASE)
    if date: out["drafter_block"]["title_block_date"] = date.group(1)

    return out


def detect_boilerplate_signals(pages: list[str], project_state: str | None) -> dict:
    """Run BP-001 (state-mismatched 811) and BP-002 (legacy company)."""
    full = "\n".join(pages)
    out = {
        "_811_callout_in_cd": None,
        "_811_callout_in_cd_state": None,
        "_811_callout_expected_for_state": None,
        "_811_scrub_required": False,
        "_legacy_company_in_cd": None,
        "_legacy_company_scrub_required": False,
        "_known_boilerplate_errors_detected": [],
    }
    # 811 detection
    for state, pattern in CD_811_PATTERNS.items():
        if re.search(re.escape(pattern), full, re.IGNORECASE):
            out["_811_callout_in_cd"] = pattern
            out["_811_callout_in_cd_state"] = state.split("_")[0]
            break
    # `indiana811-logo.png` is a definitive signal (image filename embedded as text)
    if "indiana811" in full.lower():
        out["_811_callout_in_cd"] = "Indiana 811"
        out["_811_callout_in_cd_state"] = "IN"
    if "missdig" in full.lower() or "miss dig" in full.lower():
        out["_811_callout_in_cd"] = "Miss Dig 811"
        out["_811_callout_in_cd_state"] = "MI"

    if project_state == "MI":
        out["_811_callout_expected_for_state"] = "Miss Dig 811"
        if out["_811_callout_in_cd_state"] and out["_811_callout_in_cd_state"] != "MI":
            out["_811_scrub_required"] = True
            out["_known_boilerplate_errors_detected"].append(
                f"BP-001: {out['_811_callout_in_cd']} callout on {project_state} project"
            )
    # BP-002: SEFNCO Communication, Inc. or other legacy boilerplate
    for legacy in ("SEFNCO Communication, Inc.", "SEFNCO Communications", "SEFNCO"):
        if legacy.lower() in full.lower():
            out["_legacy_company_in_cd"] = legacy
            out["_legacy_company_scrub_required"] = True
            out["_known_boilerplate_errors_detected"].append(
                f"BP-002: '{legacy}' legacy company name detected"
            )
            break
    return out


# ---------------------------------------------------------------------------
# KML analyzer
# ---------------------------------------------------------------------------

def walk_with_path(elem, path: list[str]) -> list[tuple[list[str], ET.Element]]:
    """Yield (folder_path, placemark) pairs walking the doc subtree."""
    out = []
    for child in list(elem):
        tag = child.tag
        if tag == "Folder":
            name = (child.findtext("name") or "").strip()
            out.extend(walk_with_path(child, path + [name]))
        elif tag == "Placemark":
            out.append((path, child))
    return out


def analyze_kml(kml_path: Path) -> dict:
    tree = ET.parse(str(kml_path))
    root = tree.getroot()
    doc = root.find("Document")
    if doc is None:
        doc = root

    flat = walk_with_path(doc, [])

    # Per-style aggregates
    length_by_style: dict[str, float] = {}
    placemarks_by_style: dict[str, int] = {}

    # Classified totals
    totals = {
        "lf_aerial_primary_m": 0.0,         # #vector-span (Fore Span — actual fiber)
        "lf_aerial_p2p_m": 0.0,              # #p2p (point-to-point connectors)
        "lf_underground_m": 0.0,             # any LineString under a folder named "UG ..."
        "lf_anchor_leads_m": 0.0,            # #vector-other (down-guy lead lengths)
        "lf_unclassified_m": 0.0,
    }

    poles_count = 0
    pole_locations: list[tuple[float, float, str]] = []  # (lat, lon, name)
    ug_pole_stations = set()

    bbox_lats: list[float] = []
    bbox_lons: list[float] = []

    for folder_path, pm in flat:
        style = (pm.findtext("styleUrl") or "").strip()
        is_ug = any(p.upper().startswith("UG ") for p in folder_path)

        # Track UG stations: any folder name in path beginning with "UG "
        for p in folder_path:
            if p.upper().startswith("UG "):
                ug_pole_stations.add(p)

        placemarks_by_style[style] = placemarks_by_style.get(style, 0) + 1

        # Sum per-LineString lengths
        for ls in pm.findall(".//LineString"):
            coords_text = (ls.findtext("coordinates") or "").strip()
            if not coords_text:
                continue
            length_m = line_length_m(coords_text)
            length_by_style[style] = length_by_style.get(style, 0.0) + length_m
            for lat, lon in parse_kml_coords(coords_text):
                bbox_lats.append(lat); bbox_lons.append(lon)

            if is_ug:
                totals["lf_underground_m"] += length_m
            elif style == "#vector-span":
                totals["lf_aerial_primary_m"] += length_m
            elif style == "#p2p":
                totals["lf_aerial_p2p_m"] += length_m
            elif style == "#vector-other":
                totals["lf_anchor_leads_m"] += length_m
            else:
                totals["lf_unclassified_m"] += length_m

        # Count poles: any Point geometry under "Collection" folder OR with #collection style
        for pt in pm.findall(".//Point/coordinates"):
            for lat, lon in parse_kml_coords(pt.text or ""):
                bbox_lats.append(lat); bbox_lons.append(lon)
            if style == "#collection" or "Collection" in folder_path:
                poles_count += 1
                name = (pm.findtext("name") or "").strip()
                pts = parse_kml_coords(pt.text or "")
                if pts:
                    pole_locations.append((pts[0][0], pts[0][1], name))

    # Build summary
    out = {
        "kml_path": str(kml_path.resolve()),
        "kml_size_bytes": kml_path.stat().st_size,
        "total_placemarks": len(flat),
        "placemarks_by_style": placemarks_by_style,
        "length_by_style_ft": {k: round(v * M_TO_FT, 1) for k, v in length_by_style.items()},
        "lf_aerial_primary_ft": int(round(totals["lf_aerial_primary_m"] * M_TO_FT)),
        "lf_aerial_p2p_ft": int(round(totals["lf_aerial_p2p_m"] * M_TO_FT)),
        "lf_underground_ft": int(round(totals["lf_underground_m"] * M_TO_FT)),
        "lf_anchor_leads_ft": int(round(totals["lf_anchor_leads_m"] * M_TO_FT)),
        "lf_unclassified_ft": int(round(totals["lf_unclassified_m"] * M_TO_FT)),
        "poles_count": poles_count,
        "ug_pole_stations": sorted(ug_pole_stations),
        "ug_pole_stations_count": len(ug_pole_stations),
        "_lf_methodology": (
            "Aerial primary = sum of #vector-span LineStrings (the drafter's Fore Span — "
            "the actual new fiber span between adjacent poles). Aerial p2p = sum of #p2p "
            "LineStrings (point-to-point connectors; may include alternate routings, back "
            "spans, or supplementary geometry). Underground = sum of LineStrings under any "
            "folder whose name begins with 'UG '. Anchor leads = #vector-other (excluded "
            "from route LF totals). Unclassified = anything not matching the above; if "
            "non-zero, inspect the KML."
        ),
        "_classification_advice": (
            "For the cover letter scope clause and fee calculation, use lf_aerial_primary "
            "as the headline aerial figure. Cross-check against the CD's description-of-"
            "work table on page 2; if they disagree, prefer the CD value and note the "
            "delta in open_questions."
        ),
        "_provenance": "kml_geometry",
    }

    if bbox_lats:
        out["bbox"] = {
            "lat_min": round(min(bbox_lats), 6),
            "lat_max": round(max(bbox_lats), 6),
            "lon_min": round(min(bbox_lons), 6),
            "lon_max": round(max(bbox_lons), 6),
        }
        out["centroid"] = {
            "lat": round(sum(bbox_lats) / len(bbox_lats), 6),
            "lon": round(sum(bbox_lons) / len(bbox_lons), 6),
        }
    else:
        out["bbox"] = None
        out["centroid"] = None

    return out


# ---------------------------------------------------------------------------
# Inference: scope clause, MDOT region, primary construction type
# ---------------------------------------------------------------------------

def infer_construction_type(scope: dict) -> str:
    aerial = scope.get("lf_aerial_primary_ft", 0) or 0
    ug = scope.get("lf_underground_ft", 0) or 0
    if aerial == 0 and ug == 0:
        return "unknown"
    if aerial > 10 * ug:
        return "aerial_fiber_overlash"
    if ug > 10 * aerial:
        return "underground_fiber_install"
    return "mixed_aerial_and_underground"


def infer_summary_clause(scope: dict, construction_type: str) -> str:
    aerial = scope.get("lf_aerial_primary_ft", 0) or 0
    ug = scope.get("lf_underground_ft", 0) or 0
    poles = scope.get("poles_count", 0) or 0
    if construction_type == "aerial_fiber_overlash":
        if poles:
            return f"approximately {aerial:,} LF of aerial fiber overlash on existing pole plant ({poles} surveyed poles)"
        return f"approximately {aerial:,} LF of aerial fiber overlash on existing pole plant"
    if construction_type == "underground_fiber_install":
        return f"approximately {ug:,} LF of underground fiber installation"
    if construction_type == "mixed_aerial_and_underground":
        return f"approximately {aerial:,} LF of aerial fiber overlash plus {ug:,} LF of underground installation"
    return "(scope clause pending — KML did not yield route lengths; pull from CD description-of-work table)"


def normalize_county_for_registry(county: str | None, registry: dict) -> str | None:
    """Match a parsed county name to the registry's canonical key.

    The CD title block writes counties in various forms ("Saint Joseph",
    "ST. JOSEPH", "St Joseph", "St. Joseph") but the registry uses one
    canonical spelling per county (e.g., "St. Joseph"). This normalizer
    looks up the registry keys and finds the closest match.
    """
    if not county:
        return None
    table = registry["mdot"]["county_to_region"]
    if county in table:
        return county
    # Build candidates: case-insensitive match, then with prefix swaps.
    lookup = {k.lower(): k for k in table}
    cand = county.lower().strip()
    if cand in lookup:
        return lookup[cand]
    # Common abbreviation swaps
    swaps = [
        ("saint ", "st. "),
        ("st ", "st. "),
        ("st. ", "saint "),
    ]
    for old, new in swaps:
        if cand.startswith(old):
            alt = new + cand[len(old):]
            if alt in lookup:
                return lookup[alt]
    # Fall back: substring match against any key (handles e.g. "St. Joseph County" -> "St. Joseph")
    for key_lc, key in lookup.items():
        if cand == key_lc.replace(".", "").replace(" ", "") or cand.replace(".", "").replace(" ", "") == key_lc.replace(".", "").replace(" ", ""):
            return key
    return None


def lookup_mdot_region(county: str | None, registry: dict) -> dict:
    out = {
        "region": None,
        "region_office_city": None,
        "registry_entity_id": None,
        "county_resolved_to_registry_key": None,
        "_provenance": None,
    }
    if not county:
        return out
    canonical = normalize_county_for_registry(county, registry)
    if not canonical:
        out["_provenance"] = f"registry lookup miss: parsed county {county!r} did not match any of the 83 MI county keys"
        return out
    out["county_resolved_to_registry_key"] = canonical
    table = registry["mdot"]["county_to_region"]
    region = table[canonical]
    out["region"] = region
    out["registry_entity_id"] = f"MDOT_{region}_Region"
    region_entry = registry["mdot"]["regions"].get(out["registry_entity_id"], {})
    out["region_office_city"] = region_entry.get("region_office_city")
    out["_provenance"] = f"registry.mdot.county_to_region[{canonical!r}]" + (f" (parsed as {county!r})" if canonical != county else "")
    return out


# ---------------------------------------------------------------------------
# Main facts assembly
# ---------------------------------------------------------------------------

def build_project_facts(jb_folder: Path) -> dict:
    files = list(jb_folder.iterdir())
    pdf_path = next((f for f in files if f.suffix.lower() == ".pdf"), None)
    kml_path = next((f for f in files if f.suffix.lower() == ".kml"), None)

    if not pdf_path:
        raise RuntimeError(f"No CD PDF found in {jb_folder}")

    # JB number from filename (fall back to title block)
    jb_from_filename = JB_RE.search(pdf_path.name)
    jb_provenance = "filename" if jb_from_filename else "cd_titleblock"

    # Read CD PDF
    page_count, pages = read_pdf_pages_text(pdf_path, max_pages=5)
    titleblock = parse_cd_titleblock(pages)
    if jb_from_filename and not titleblock["jb_number"]:
        titleblock["jb_number"] = "JB" + jb_from_filename.group(1)

    boilerplate = detect_boilerplate_signals(pages, titleblock.get("state"))

    # Analyze KML if present
    kml = analyze_kml(kml_path) if kml_path else None

    # Lookup MDOT region from county
    registry = load_registry()
    mdot = lookup_mdot_region(titleblock.get("county"), registry)

    # Build scope object (prefer KML; fall back to "(unknown — Mode C)" if no KML)
    if kml:
        scope = {
            "lf_aerial_primary_ft": kml["lf_aerial_primary_ft"],
            "lf_aerial_p2p_ft": kml["lf_aerial_p2p_ft"],
            "lf_underground_ft": kml["lf_underground_ft"],
            "lf_anchor_leads_ft": kml["lf_anchor_leads_ft"],
            "lf_unclassified_ft": kml["lf_unclassified_ft"],
            "poles_count": kml["poles_count"],
            "ug_pole_stations_count": kml["ug_pole_stations_count"],
            "_lf_methodology": kml["_lf_methodology"],
            "_classification_advice": kml["_classification_advice"],
            "_provenance": "kml_geometry",
        }
    else:
        scope = {
            "lf_aerial_primary_ft": None,
            "lf_aerial_p2p_ft": None,
            "lf_underground_ft": None,
            "lf_anchor_leads_ft": None,
            "lf_unclassified_ft": None,
            "poles_count": None,
            "ug_pole_stations_count": None,
            "_lf_methodology": "No KML found in JB folder. Scope must be transcribed from CD page 2 description-of-work table by hand.",
            "_provenance": "no_kml_mode_c",
        }
    construction_type = infer_construction_type(scope)
    scope["primary_construction_type"] = construction_type
    scope["summary_clause_for_cover_letter"] = infer_summary_clause(scope, construction_type)
    if titleblock.get("title_clause"):
        scope["title_clause_from_cd"] = titleblock["title_clause"]

    # Build geographic_extent from KML; fall back to CD lat/lon as a single point
    geo_extent = None
    if kml and kml.get("centroid"):
        geo_extent = {
            "bbox": kml["bbox"],
            "centroid": kml["centroid"],
            "_provenance": "kml_all_coordinates",
        }
    elif titleblock.get("lat_decimal") and titleblock.get("lon_decimal"):
        geo_extent = {
            "bbox": None,
            "centroid": {"lat": titleblock["lat_decimal"], "lon": titleblock["lon_decimal"]},
            "_provenance": "cd_titleblock_lat_lon",
        }

    # Derive open questions
    open_questions: list[str] = []
    if not titleblock.get("address"):
        open_questions.append("CD title-block address not parsed; verify by hand.")
    if not titleblock.get("county"):
        open_questions.append("CD title-block county not parsed; resolve via address or lat/lon and confirm.")
    if not kml:
        open_questions.append("No KML in JB folder. Scope (LF aerial/UG, pole counts) must come from CD description-of-work table; this run is Mode C (CD only).")
    if kml and scope.get("lf_unclassified_ft", 0) > 0:
        open_questions.append(f"KML contains {scope['lf_unclassified_ft']:,} LF of geometry not matching #vector-span / #p2p / #vector-other / UG-folder rules. Inspect KML for new style conventions.")
    if boilerplate.get("_811_scrub_required"):
        open_questions.append(f"BP-001 detected: CD shows {boilerplate.get('_811_callout_in_cd')!r}, project state is {titleblock.get('state')!r}. Run scrub_cd before package render.")
    if boilerplate.get("_legacy_company_scrub_required"):
        open_questions.append(f"BP-002 detected: CD contains '{boilerplate.get('_legacy_company_in_cd')}'. Run scrub_cd to replace with MasTec/Comcast.")
    drafter_engineer = (titleblock.get("drafter_block") or {}).get("engineer")
    if drafter_engineer and "thomas.halfman" not in drafter_engineer.lower():
        open_questions.append(f"CD title block names drafter engineer {drafter_engineer!r} (not Thomas Halfman). This is the drafter, not the permit submitting contact — Thomas remains submitting contact unless contacts.md overrides.")

    facts = {
        "schema_version": SCHEMA_VERSION,
        "extracted_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "jb_folder": str(jb_folder.resolve()),
            "cd_pdf": str(pdf_path.resolve()),
            "cd_pdf_size_bytes": pdf_path.stat().st_size,
            "cd_pdf_page_count": page_count,
            "kml": str(kml_path.resolve()) if kml_path else None,
            "kml_size_bytes": kml_path.stat().st_size if kml_path else None,
            "registry_schema_version": registry.get("schema_version"),
        },
        "jb": {
            "number": titleblock["jb_number"],
            "provenance": jb_provenance,
        },
        "project": {
            "name": titleblock.get("project_name"),
            "address": titleblock.get("address"),
            "city": titleblock.get("city"),
            "state": titleblock.get("state"),
            "zip": titleblock.get("zip"),
            "county": titleblock.get("county"),
            "township": titleblock.get("township"),
            "range": titleblock.get("range"),
            "section": titleblock.get("section"),
            "qtr_section": titleblock.get("qtr_section"),
            "lat_decimal": titleblock.get("lat_decimal"),
            "lon_decimal": titleblock.get("lon_decimal"),
            "lat_dms": titleblock.get("lat_dms"),
            "lon_dms": titleblock.get("lon_dms"),
            "_provenance": "cd_page_1_titleblock",
        },
        "scope": scope,
        "geographic_extent": geo_extent,
        "mdot": mdot,
        "boilerplate_signals": boilerplate,
        "drafter_block": titleblock.get("drafter_block"),
        "open_questions": open_questions,
    }
    return facts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def write_facts(jb_folder: Path, output_dir: Path | None) -> Path:
    facts = build_project_facts(jb_folder)
    jb = facts["jb"]["number"] or "UNKNOWN_JB"
    if output_dir is None:
        output_dir = jb_folder.parent / "output" / jb
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "project_facts.json"
    out_path.write_text(json.dumps(facts, indent=2), encoding="utf-8")
    return out_path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="JB folder (single-JB mode) or Deliverables root (with --all)")
    p.add_argument("--all", action="store_true", help="Process every sub-folder containing a CD PDF")
    p.add_argument("--output-dir", type=Path, default=None, help="Override default output location")
    args = p.parse_args()

    if not args.path.is_dir():
        print(f"error: {args.path} is not a directory", file=sys.stderr)
        return 1

    if args.all:
        folders = [p for p in sorted(args.path.iterdir()) if p.is_dir() and any(f.suffix.lower() == ".pdf" for f in p.iterdir())]
        if not folders:
            print(f"error: no JB sub-folders with PDFs found under {args.path}", file=sys.stderr)
            return 1
        print(f"Processing {len(folders)} JB folder(s):")
        results: list[tuple[str, str | None, str | None]] = []
        for f in folders:
            try:
                out = write_facts(f, args.output_dir)
                facts = json.loads(out.read_text(encoding="utf-8"))
                jb = facts["jb"]["number"] or "?"
                lf_a = (facts["scope"] or {}).get("lf_aerial_primary_ft")
                lf_u = (facts["scope"] or {}).get("lf_underground_ft")
                county = (facts["project"] or {}).get("county") or "?"
                region = (facts["mdot"] or {}).get("region") or "?"
                summary = f"{jb}: {county} County / MDOT {region} / {lf_a or 0:,} LF aerial / {lf_u or 0:,} LF UG"
                print(f"  {summary} -> {out}")
                results.append((jb, str(out), None))
            except Exception as e:
                print(f"  FAIL on {f.name}: {e}", file=sys.stderr)
                results.append((f.name, None, str(e)))
        bad = sum(1 for _, _, err in results if err)
        return 1 if bad else 0

    out = write_facts(args.path, args.output_dir)
    facts = json.loads(out.read_text(encoding="utf-8"))
    jb = facts["jb"]["number"] or "?"
    scope = facts["scope"] or {}
    print(f"Wrote {out}")
    print(f"  JB:       {jb}")
    print(f"  County:   {(facts['project'] or {}).get('county')}")
    print(f"  Address:  {(facts['project'] or {}).get('address')}")
    print(f"  MDOT:     {(facts['mdot'] or {}).get('region')} (office: {(facts['mdot'] or {}).get('region_office_city')})")
    print(f"  LF aerial primary:        {scope.get('lf_aerial_primary_ft')}")
    print(f"  LF aerial p2p:            {scope.get('lf_aerial_p2p_ft')}")
    print(f"  LF underground:           {scope.get('lf_underground_ft')}")
    print(f"  Poles:                    {scope.get('poles_count')}")
    print(f"  UG pole stations:         {scope.get('ug_pole_stations_count')}")
    print(f"  Construction type:        {scope.get('primary_construction_type')}")
    print(f"  Cover-letter scope:       {scope.get('summary_clause_for_cover_letter')}")
    if facts.get("open_questions"):
        print(f"  Open questions ({len(facts['open_questions'])}):")
        for q in facts["open_questions"]:
            print(f"    - {q}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
