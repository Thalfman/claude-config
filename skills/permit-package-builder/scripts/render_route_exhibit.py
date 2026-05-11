"""
Render a 1-page route_exhibit.pdf for one (JB, entity) pair.

Reads:
  - the JB's KML (route geometry + pole points)
  - project_facts.json (title-block facts)
  - registry entity record (entity legal name)

Writes:
  - <output_dir>/route_exhibit.pdf

Rendering style is **vector-only** (no satellite tiles, no API
dependencies). The PDF carries:
  - Title block (top): JB#, entity, project address, date, scale
  - Route geometry (center): aerial spans (red dashed), UG spans
    (red solid), anchor leads (yellow), pole markers (green dots)
  - North arrow + scale bar (bottom-right)
  - Footer: Comcast/MasTec attribution

This is enough to satisfy permit reviewers who expect a printed
route exhibit alongside the scrubbed CD. For a fancier exhibit
(satellite imagery, parcel overlays), feed the same KML into
cd-ground-overlays or a GIS workflow.

CLI
---
    python -m scripts.render_route_exhibit --jb JB########## --entity <entity_id>
    python -m scripts.render_route_exhibit --jb JB########## --entity <entity_id> --kml <path>

Output default: output/<JB>/<entity_id>/route_exhibit.pdf
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = SKILL_ROOT / "references" / "mi_entity_registry.json"

# Page geometry (US Letter landscape, 1/72 inch units)
PAGE_W = 11 * 72   # 792 pt
PAGE_H = 8.5 * 72  # 612 pt
MARGIN = 36        # 0.5 inch
TITLE_BLOCK_H = 96 # 1.33 inch reserved at top
FOOTER_H = 24

# Map area
MAP_X0 = MARGIN
MAP_Y0 = MARGIN + FOOTER_H
MAP_X1 = PAGE_W - MARGIN
MAP_Y1 = PAGE_H - MARGIN - TITLE_BLOCK_H

# Style colors (RGB 0–1)
COLOR_AERIAL = (0.85, 0.10, 0.10)   # red, dashed
COLOR_UG = (0.85, 0.10, 0.10)        # red, solid
COLOR_ANCHOR = (0.85, 0.65, 0.10)    # yellow
COLOR_POLE = (0.10, 0.55, 0.20)      # green
COLOR_TEXT = (0, 0, 0)
COLOR_BORDER = (0.4, 0.4, 0.4)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def find_entity(entity_id: str, registry: dict) -> dict | None:
    for bucket_name in ("county_road_commissions", "municipalities", "pole_owners",
                         "railroad_operators_mi", "environmental_overlays_mi"):
        bucket = registry.get(bucket_name, {})
        if entity_id in bucket and not entity_id.startswith("_"):
            return bucket[entity_id]
    regions = registry.get("mdot", {}).get("regions", {})
    if entity_id in regions:
        return regions[entity_id]
    return None


def find_facts(jb: str, search_root: Path) -> tuple[Path, dict]:
    candidates = [
        search_root / jb / "project_facts.json",
        Path.cwd() / "output" / jb / "project_facts.json",
        Path("output") / jb / "project_facts.json",
    ]
    for c in candidates:
        if c.is_file():
            return c, json.loads(c.read_text(encoding="utf-8"))
    raise SystemExit(f"project_facts.json not found for {jb}.")


# ---------------------------------------------------------------------------
# KML feature extractor
# ---------------------------------------------------------------------------


def parse_coords(text: str) -> list[tuple[float, float]]:
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


def walk(elem, path: list[str]):
    out = []
    for child in list(elem):
        if child.tag == "Folder":
            name = (child.findtext("name") or "").strip()
            out.extend(walk(child, path + [name]))
        elif child.tag == "Placemark":
            out.append((path, child))
    return out


def extract_features(kml_path: Path) -> dict:
    """Return aerial lines, UG lines, anchor lines, pole points."""
    tree = ET.parse(str(kml_path))
    root = tree.getroot()
    doc = root.find("Document")
    if doc is None:
        doc = root

    aerial: list[list[tuple[float, float]]] = []
    ug: list[list[tuple[float, float]]] = []
    anchor: list[list[tuple[float, float]]] = []
    poles: list[tuple[float, float]] = []

    for path, pm in walk(doc, []):
        style = (pm.findtext("styleUrl") or "").strip()
        is_ug = any(p.upper().startswith("UG ") for p in path)
        for ls in pm.findall(".//LineString"):
            coords = parse_coords(ls.findtext("coordinates") or "")
            if len(coords) < 2:
                continue
            if is_ug:
                ug.append(coords)
            elif style == "#vector-span" or style == "#p2p":
                aerial.append(coords)
            elif style == "#vector-other":
                anchor.append(coords)
        for pt in pm.findall(".//Point/coordinates"):
            pts = parse_coords(pt.text or "")
            if pts and (style == "#collection" or "Collection" in path):
                poles.append(pts[0])

    # Compute bbox from EVERY coordinate (route + poles)
    all_pts = []
    for L in (aerial, ug, anchor):
        for line in L:
            all_pts.extend(line)
    all_pts.extend(poles)

    if not all_pts:
        bbox = None
        centroid = None
    else:
        lats = [p[0] for p in all_pts]
        lons = [p[1] for p in all_pts]
        bbox = (min(lats), max(lats), min(lons), max(lons))
        centroid = (sum(lats) / len(lats), sum(lons) / len(lons))

    return {
        "aerial": aerial,
        "ug": ug,
        "anchor": anchor,
        "poles": poles,
        "bbox": bbox,
        "centroid": centroid,
    }


# ---------------------------------------------------------------------------
# Coordinate transform (lat/lon → page coordinates)
# ---------------------------------------------------------------------------


def make_projector(bbox: tuple[float, float, float, float]):
    lat_min, lat_max, lon_min, lon_max = bbox

    # Use a simple equirectangular projection scaled by cos(lat) for x.
    # Keeps shapes recognizable at MI latitudes and avoids needing pyproj.
    lat_c = (lat_min + lat_max) / 2
    cos_lat = max(0.01, math.cos(math.radians(lat_c)))

    # Compute geographic span in equirectangular units
    span_y = (lat_max - lat_min)
    span_x = (lon_max - lon_min) * cos_lat

    # Pad the bbox by 5% so route doesn't hit page edges
    pad = 0.05
    span_y *= 1 + 2 * pad
    span_x *= 1 + 2 * pad

    # Available drawing area
    w = MAP_X1 - MAP_X0
    h = MAP_Y1 - MAP_Y0

    # Choose scale to fit while preserving aspect
    if span_x == 0 or span_y == 0:
        scale = 1.0
    else:
        scale = min(w / span_x, h / span_y)

    # Compute offsets to center the route
    drawn_w = span_x * scale
    drawn_h = span_y * scale
    off_x = MAP_X0 + (w - drawn_w) / 2
    off_y = MAP_Y0 + (h - drawn_h) / 2

    # Reference point is bbox SW corner with padding applied
    lat0 = lat_min - pad * (lat_max - lat_min)
    lon0 = lon_min - pad * (lon_max - lon_min)

    def project(lat: float, lon: float) -> tuple[float, float]:
        x = off_x + ((lon - lon0) * cos_lat) * scale
        # Y inverted so north-up
        y = off_y + drawn_h - ((lat - lat0)) * scale
        return x, y

    return project, scale, cos_lat


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# PDF render
# ---------------------------------------------------------------------------


def render_route_exhibit(facts: dict, entity_id: str, entity: dict, kml_path: Path, out_pdf: Path) -> None:
    import fitz  # pymupdf
    features = extract_features(kml_path)
    if not features["bbox"]:
        raise SystemExit(f"No drawable geometry in {kml_path}")

    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    project, scale, cos_lat = make_projector(features["bbox"])

    # Border around map area
    page.draw_rect(fitz.Rect(MAP_X0, MAP_Y0, MAP_X1, MAP_Y1),
                   color=COLOR_BORDER, width=0.5)

    # Aerial lines (dashed, red)
    for line in features["aerial"]:
        pts = [project(lat, lon) for (lat, lon) in line]
        for a, b in zip(pts, pts[1:]):
            page.draw_line(fitz.Point(*a), fitz.Point(*b),
                            color=COLOR_AERIAL, width=1.4, dashes="[3 2] 0")

    # UG lines (solid, red)
    for line in features["ug"]:
        pts = [project(lat, lon) for (lat, lon) in line]
        for a, b in zip(pts, pts[1:]):
            page.draw_line(fitz.Point(*a), fitz.Point(*b),
                            color=COLOR_UG, width=1.4)

    # Anchor lines (yellow, thin)
    for line in features["anchor"]:
        pts = [project(lat, lon) for (lat, lon) in line]
        for a, b in zip(pts, pts[1:]):
            page.draw_line(fitz.Point(*a), fitz.Point(*b),
                            color=COLOR_ANCHOR, width=0.7)

    # Pole markers (green dots)
    for lat, lon in features["poles"]:
        x, y = project(lat, lon)
        page.draw_circle(fitz.Point(x, y), 2.0,
                         color=COLOR_POLE, fill=COLOR_POLE, width=0.5)

    # Title block (top of page)
    title_y0 = PAGE_H - TITLE_BLOCK_H
    page.draw_rect(fitz.Rect(MARGIN, title_y0, PAGE_W - MARGIN, PAGE_H - MARGIN),
                   color=COLOR_BORDER, width=0.5)
    project_block = facts.get("project") or {}
    jb = (facts.get("jb") or {}).get("number") or "?"
    legal_name = entity.get("legal_name") or entity_id.replace("_", " ")
    address = project_block.get("address") or "(address pending)"
    today = _dt.date.today().isoformat()
    title_lines = [
        ("Route Exhibit", 18),
        (f"JB: {jb}    |    Entity: {legal_name}", 11),
        (f"Project: {address}", 10),
        (f"County: {project_block.get('county') or '?'}    "
         f"Lat/Lon: {project_block.get('lat_decimal') or '?'}, {project_block.get('lon_decimal') or '?'}", 10),
        (f"Submitted by: Thomas Halfman, MasTec Communications Group / on behalf of Comcast    "
         f"Date: {today}", 9),
    ]
    cur_y = PAGE_H - MARGIN - 6
    for text, fs in title_lines:
        cur_y -= fs + 4
        page.insert_text(fitz.Point(MARGIN + 8, cur_y), text,
                         fontsize=fs, color=COLOR_TEXT)

    # Legend (top-right of map area, just below title block)
    legend_x = MAP_X1 - 200
    legend_y = MAP_Y1 - 18
    legend_lines = [
        ("--- Aerial fiber span (existing pole plant)", COLOR_AERIAL, "dash"),
        ("─── Underground fiber", COLOR_UG, "solid"),
        ("--- Anchor / down-guy lead", COLOR_ANCHOR, "thin"),
        ("● Surveyed pole", COLOR_POLE, "dot"),
    ]
    page.insert_text(fitz.Point(legend_x, legend_y), "LEGEND", fontsize=9, color=COLOR_TEXT)
    for i, (label, color, _) in enumerate(legend_lines):
        page.insert_text(fitz.Point(legend_x + 6, legend_y - 12 - i * 11), label,
                         fontsize=8, color=color)

    # Scale bar (bottom-right of map area)
    # Compute the meters-per-page-point at this zoom.
    # 1 page point in y == (1/scale) lat-degrees == (1/scale) * 111320 meters
    # 1 page point in x == (1/(scale*cos_lat)) lon-degrees == (1/(scale*cos_lat)) * 111320*cos_lat = (1/scale) * 111320 meters
    # So m_per_pt is the same in both directions: 111320 / scale.
    m_per_pt = 111320.0 / scale if scale else 0
    if m_per_pt > 0:
        # Pick a "nice" scale-bar length (50, 100, 200, 500, 1000 ft, etc.)
        ft_per_pt = m_per_pt * 3.2808399
        target_ft = 200  # default
        for candidate in (50, 100, 200, 500, 1000, 2000, 5000):
            if candidate * 0.7 / ft_per_pt < (MAP_X1 - MAP_X0) * 0.25:
                target_ft = candidate
        bar_len_pt = target_ft / ft_per_pt
        bar_x0 = MAP_X1 - 12 - bar_len_pt
        bar_y = MAP_Y0 + 14
        page.draw_line(fitz.Point(bar_x0, bar_y), fitz.Point(bar_x0 + bar_len_pt, bar_y),
                        color=COLOR_TEXT, width=1.5)
        page.draw_line(fitz.Point(bar_x0, bar_y - 3), fitz.Point(bar_x0, bar_y + 3),
                        color=COLOR_TEXT, width=1.0)
        page.draw_line(fitz.Point(bar_x0 + bar_len_pt, bar_y - 3),
                        fitz.Point(bar_x0 + bar_len_pt, bar_y + 3),
                        color=COLOR_TEXT, width=1.0)
        page.insert_text(fitz.Point(bar_x0, bar_y - 12), f"0", fontsize=7, color=COLOR_TEXT)
        page.insert_text(fitz.Point(bar_x0 + bar_len_pt - 12, bar_y - 12),
                         f"{target_ft:,} ft", fontsize=7, color=COLOR_TEXT)

    # North arrow (above scale bar)
    nx = MAP_X1 - 24
    ny = MAP_Y0 + 50
    page.draw_line(fitz.Point(nx, ny), fitz.Point(nx, ny + 28), color=COLOR_TEXT, width=1.5)
    # Arrow head
    page.draw_line(fitz.Point(nx, ny + 28), fitz.Point(nx - 5, ny + 22), color=COLOR_TEXT, width=1.5)
    page.draw_line(fitz.Point(nx, ny + 28), fitz.Point(nx + 5, ny + 22), color=COLOR_TEXT, width=1.5)
    page.insert_text(fitz.Point(nx - 3, ny + 38), "N", fontsize=10, color=COLOR_TEXT)

    # Footer
    page.insert_text(fitz.Point(MARGIN, MARGIN - 2),
                     f"Generated by permit-package-builder skill — render_route_exhibit.py — "
                     f"source KML: {kml_path.name}",
                     fontsize=7, color=COLOR_TEXT)

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_pdf))
    doc.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jb", type=str, required=True, help="JB number")
    p.add_argument("--entity", type=str, required=True, help="Entity ID")
    p.add_argument("--kml", type=Path, default=None, help="Override KML path; default: discover from project_facts.json")
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--search-root", type=Path, default=Path("output"))
    args = p.parse_args()

    registry = load_registry()
    entity = find_entity(args.entity, registry)
    if entity is None:
        print(f"error: entity {args.entity!r} not found in registry", file=sys.stderr)
        return 1

    facts_path, facts = find_facts(args.jb, args.search_root)
    kml_path = args.kml
    if not kml_path:
        kml_path = Path((facts.get("inputs") or {}).get("kml") or "")
    if not kml_path or not kml_path.is_file():
        print(f"error: KML not found. project_facts says: {(facts.get('inputs') or {}).get('kml')!r}. Pass --kml to override.", file=sys.stderr)
        return 1

    out_dir = args.output_dir or (facts_path.parent / args.entity)
    out_pdf = out_dir / "route_exhibit.pdf"
    render_route_exhibit(facts, args.entity, entity, kml_path, out_pdf)

    size_kb = out_pdf.stat().st_size / 1024
    print(f"Wrote {out_pdf} ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
