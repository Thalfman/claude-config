#!/usr/bin/env python3
"""build_overlays.py - Convert multi-page CD PDFs into KMZ ground overlays.

USAGE
    Single PDF:
        python build_overlays.py /path/to/drawing.pdf --output /path/to/out.kmz

    Whole JB folder (auto-detect PRM[id]/*.pdf children):
        python build_overlays.py /path/to/JB123 --multi-prm
        python build_overlays.py /path/to/JB123 --multi-prm --combined

    With manual anchors:
        python build_overlays.py /path/to/drawing.pdf \\
            --manual-anchors anchors.json \\
            --output out.kmz

    Override scale (default 1" = 40'):
        python build_overlays.py /path/to/drawing.pdf --scale-feet-per-inch 50

WHAT IT DOES
    1. Identifies SITE PLAN pages (skips cover, vicinity, notes, legend,
       typical details, traffic control plans).
    2. Renders each site plan to PNG at --dpi (default 600) with PDF rotation
       applied so north points up in the rendered image.
    3. Anchors each page from the embedded "lat, lon" stamp (gold) when present,
       chains route-endpoint match-line continuity for the rest.
    4. Computes per-page lat/lon bounding box (north/south/east/west) and emits
       a KMZ with one named GroundOverlay per sheet.

CROSS-PRM ORDINAL CHAINING (multi-PRM mode only)
    SITE PLAN ordinals are global to a route, not local to a PRM. When run
    against a JB folder containing multiple PRMs, the script flattens every
    site plan across every PRM into a single sequence keyed by the parsed
    "SITE PLAN - N" title-block ordinal, then runs the same forward + backward
    chain math used within a PRM, but across PRM boundaries. A PRM with no
    embedded lat/lon now anchors off the prior PRM's exit endpoint instead of
    falling back to whatever local seed it could find. Behavior is identical
    to the pre-change code when only one PRM is present in the JB folder.

GEOGRAPHIC AXES (for 270-deg rotated, north-up rendered pages):
    +x_pdf (unrotated) -> NORTH (rendered up)
    +y_pdf (unrotated) -> EAST  (rendered right)
"""
import argparse
import json
import math
import re
import shutil
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageFilter


# ----- Constants you may override per-job -----
# 600 DPI is the floor for downstream LLM-vision triangulation: street labels
# remain legible at this density. Override with --dpi 800 for demanding cases.
DEFAULT_DPI = 600
DEFAULT_SCALE_FT_PER_INCH = 40.0
PT_PER_INCH = 72.0
FEET_PER_DEG_LAT = 364320.0
METERS_PER_FOOT = 0.3048
DEFAULT_RECONCILIATION_THRESHOLD_M = 50.0

# Render-quality knobs. Defaults are tuned for CD line-work over off-white paper
# rendered onto satellite imagery in Google Earth Pro.
SUPERSAMPLE_FACTOR = 1  # 1 = off; >1 renders dpi*factor then Lanczos-downsamples
UNSHARP_RADIUS = 1.0
UNSHARP_PERCENT = 160
UNSHARP_THRESHOLD = 2
CONTRAST_BOOST = 1.10  # pulls line work off the paper without crushing callouts

# Fixed ZipInfo date for byte-identical idempotent KMZ output. Identical inputs
# produce identical output bytes regardless of when the script is rerun.
ZIP_DATE = (1980, 1, 1, 0, 0, 0)


# ----- Page classification regexes (mirror cd-route-stitcher) -----
LATLON_RE = re.compile(r'(-?\d{1,2}\.\d{4,8})\s*,\s*(-?\d{1,3}\.\d{4,8})')
LAT_LINE_RE = re.compile(r'\bLAT(?:ITUDE)?\s*[:\-]?\s*(-?\d{1,2}\.\d{4,8})', re.IGNORECASE)
LON_LINE_RE = re.compile(r'\bLON(?:G(?:ITUDE)?)?\s*[:\-]?\s*(-?\d{1,3}\.\d{4,8})', re.IGNORECASE)
ADDRESS_RE = re.compile(
    r'\b(\d{1,6})\s+([NSEW]\s+)?([A-Z0-9][A-Z0-9 .]+?)\s*,\s*([A-Z][A-Z ]+?)\s*,\s*([A-Z]{2})\s+(\d{5})',
    re.IGNORECASE,
)
MATCH_LINE_RE = re.compile(
    r'MATCH(?:\s+(?:TO|LINE))?\s*[:\-]?\s*SITE\s*PLAN\s*[-#]?\s*(\d+)', re.IGNORECASE,
)
SHEET_NUM_RE = re.compile(r'(?:SHEET|SITE\s*PLAN)\s*[-#:]?\s*(\d+)', re.IGNORECASE)
# Title-block ordinal: "SITE PLAN - N" without a leading "MATCH" qualifier.
SITE_PLAN_ORDINAL_RE = re.compile(r'\bSITE\s*PLAN\s*[-#:]?\s*(\d+)\b', re.IGNORECASE)

# Route stroke red palette (pure red and dark red used by Civil 3D)
ROUTE_R_MIN, ROUTE_GB_MAX = 0.80, 0.20
ROUTE_W_MIN, ROUTE_W_MAX = 0.40, 1.10

# Title block occupies the rightmost TITLE_BLOCK_X_FRAC of the rendered (rotated)
# page, which under the standard 270-deg CW rotation maps to the LEFTMOST
# (1 - TITLE_BLOCK_X_FRAC) of the unrotated MediaBox x-axis. So in_title_block's
# predicate is x_orig <= w * (1 - TITLE_BLOCK_X_FRAC) [small unrotated x = display
# right] AND y_orig >= h * TITLE_BLOCK_Y_FRAC [large unrotated y = display bottom].
TITLE_BLOCK_X_FRAC = 0.65
TITLE_BLOCK_Y_FRAC = 0.75


def feet_per_deg_lon(lat_deg):
    return FEET_PER_DEG_LAT * math.cos(math.radians(lat_deg))


def is_route_color(c):
    return c is not None and len(c) >= 3 and c[0] >= ROUTE_R_MIN and c[1] <= ROUTE_GB_MAX and c[2] <= ROUTE_GB_MAX


def is_route_width(w):
    return w is not None and ROUTE_W_MIN <= w <= ROUTE_W_MAX


def text_blocks(page):
    """Flat list of text spans with center positions (in unrotated PDF coords)."""
    out = []
    for blk in page.get_text("dict").get("blocks", []):
        if blk.get("type") != 0:
            continue
        for line in blk.get("lines", []):
            text = ""
            bbox = None
            for span in line.get("spans", []):
                text += span.get("text", "")
                b = span.get("bbox")
                if b:
                    if bbox is None:
                        bbox = list(b)
                    else:
                        bbox[0] = min(bbox[0], b[0])
                        bbox[1] = min(bbox[1], b[1])
                        bbox[2] = max(bbox[2], b[2])
                        bbox[3] = max(bbox[3], b[3])
            if text.strip() and bbox:
                out.append({
                    "text": text.strip(),
                    "x": (bbox[0] + bbox[2]) / 2,
                    "y": (bbox[1] + bbox[3]) / 2,
                })
    return out


def in_title_block(x, y, page_w_unrotated, page_h_unrotated):
    """True when (x, y) sits in the title-block region of an unrotated MediaBox.

    For the standard MasTec/Comcast layout the title block prints at the
    *display* bottom-right of the rendered landscape page. Under the 270-deg
    PDF rotation that corresponds to *unrotated bottom-left* in PyMuPDF's
    y-down MediaBox space — small x_orig, large y_orig.

    Pass page.mediabox dimensions (NOT page.rect.width/height — those are
    rotated and don't match the coord system that get_text/get_drawings
    returns).
    """
    return (x <= page_w_unrotated * (1.0 - TITLE_BLOCK_X_FRAC)
            and y >= page_h_unrotated * TITLE_BLOCK_Y_FRAC)


def extract_embedded_latlon(blocks, page_w, page_h):
    """Return (x_pdf, y_pdf, lat, lon) for the first US-range coord outside the title block."""
    for blk in blocks:
        if in_title_block(blk["x"], blk["y"], page_w, page_h):
            continue
        for m in LATLON_RE.finditer(blk["text"]):
            lat = float(m.group(1)); lon = float(m.group(2))
            if 24.0 <= lat <= 50.0 and -130.0 <= lon <= -65.0:
                return blk["x"], blk["y"], lat, lon
    return None


def extract_split_latlon(blocks, page_w, page_h):
    """Return (x_pdf, y_pdf, lat, lon) for a `LAT: X` / `LONG: Y` pair on separate spans.

    Used when the drawing labels latitude and longitude on different text spans
    (common on Comcast railroad-permit crossing diagrams). Returns the first lat
    and the closest-by-PDF-distance lon, anchored at the midpoint between them.
    Both spans must fall outside the title block.
    """
    lats, lons = [], []
    for b in blocks:
        if in_title_block(b["x"], b["y"], page_w, page_h):
            continue
        for ml in LAT_LINE_RE.finditer(b["text"]):
            v = float(ml.group(1))
            if 24.0 <= v <= 50.0:
                lats.append((b["x"], b["y"], v))
        for mo in LON_LINE_RE.finditer(b["text"]):
            v = float(mo.group(1))
            if -130.0 <= v <= -65.0:
                lons.append((b["x"], b["y"], v))
    if not lats or not lons:
        return None
    lx, ly, lat = lats[0]
    best = min(lons, key=lambda o: abs(o[0] - lx) + abs(o[1] - ly))
    ox, oy, lon = best
    if abs(lx - ox) + abs(ly - oy) > 200:
        return None
    return (lx + ox) / 2, (ly + oy) / 2, lat, lon


def extract_any_latlon(blocks, page_w, page_h):
    """Inline `lat, lon` first; fall back to split `LAT: X` / `LONG: Y`."""
    return (extract_embedded_latlon(blocks, page_w, page_h)
            or extract_split_latlon(blocks, page_w, page_h))


def parse_site_plan_ordinal(blocks, page_w, page_h):
    """Return the page's "SITE PLAN - N" ordinal from the title block, or None.

    Skips blocks that contain MATCH callouts (those reference neighboring
    sheets, not the current one). When multiple non-MATCH "SITE PLAN - N"
    candidates exist, prefers the one whose center falls in the title-block
    region of the unrotated page.
    """
    candidates = []  # list of (x_pdf, y_pdf, ordinal, in_title)
    for blk in blocks:
        text = blk["text"]
        if MATCH_LINE_RE.search(text):
            continue
        m = SITE_PLAN_ORDINAL_RE.search(text)
        if not m:
            continue
        try:
            ordinal = int(m.group(1))
        except ValueError:
            continue
        in_title = in_title_block(blk["x"], blk["y"], page_w, page_h)
        candidates.append((blk["x"], blk["y"], ordinal, in_title))
    if not candidates:
        return None
    title_block_candidates = [c for c in candidates if c[3]]
    if title_block_candidates:
        return title_block_candidates[0][2]
    return candidates[0][2]


def extract_route_endpoints(page):
    """Return (entry_pdf, exit_pdf) for the longest connected red polyline.

    entry = endpoint with smallest y_pdf (rendered LEFT under standard
    270-rotation), exit = endpoint with largest y_pdf (rendered RIGHT).
    Restricting to the longest polyline keeps callouts, underlines, and
    title-block accents from polluting the global y-range.
    """
    polylines = []
    for d in page.get_drawings():
        if d.get("type") not in ("s", "sf", "fs"):
            continue
        if not is_route_color(d.get("color")) or not is_route_width(d.get("width")):
            continue
        current = []
        for item in d.get("items", []):
            op = item[0]
            if op == "l":
                p1 = (item[1].x, item[1].y); p2 = (item[2].x, item[2].y)
            elif op == "c":
                # Cubic bezier: take only the endpoints (item[1] start, item[4] end)
                p1 = (item[1].x, item[1].y); p2 = (item[4].x, item[4].y)
            else:
                if current:
                    polylines.append(current); current = []
                continue
            if not current or current[-1] != p1:
                if current:
                    polylines.append(current)
                current = [p1, p2]
            else:
                current.append(p2)
        if current:
            polylines.append(current)
    if not polylines:
        return None, None
    best = max(polylines, key=_polyline_length)
    ymin = min(p[1] for p in best); ymax = max(p[1] for p in best)
    entry = next(p for p in best if p[1] == ymin)
    exit_ = next(p for p in best if p[1] == ymax)
    return entry, exit_


def _polyline_length(points):
    return sum(math.hypot(points[i + 1][0] - points[i][0],
                          points[i + 1][1] - points[i][1])
               for i in range(len(points) - 1))


def closest_route_endpoint(text_pdf, entry_pdf, exit_pdf):
    """Return the route polyline endpoint closer to the text bbox centroid, or None.

    text_pdf: (x, y) in unrotated PDF coords (the bbox centroid of the lat/lon stamp).
    entry_pdf, exit_pdf: route endpoints from extract_route_endpoints (either may be None).
    """
    candidates = [p for p in (entry_pdf, exit_pdf) if p is not None]
    if not candidates:
        return None
    tx, ty = text_pdf
    return min(candidates, key=lambda p: (p[0] - tx) ** 2 + (p[1] - ty) ** 2)


def is_site_plan(blocks, page_idx, page_w=None, page_h=None):
    if page_idx < 3:
        return False
    has_match = any(MATCH_LINE_RE.search(b["text"]) for b in blocks)
    if has_match:
        return True
    has_addr = any(ADDRESS_RE.search(b["text"]) for b in blocks)
    has_sheet = any(SHEET_NUM_RE.search(b["text"]) for b in blocks)
    if has_addr and has_sheet:
        return True
    # Pages carrying their own embedded lat/lon (inline or split LAT/LONG) are
    # site plans even without a MATCH callout. Catches single-page railroad-permit
    # crossing diagrams that the older heuristic missed.
    if page_w is not None and page_h is not None:
        if extract_any_latlon(blocks, page_w, page_h):
            return True
    return False


# ----- Geographic transform (north-up rendered) -----
def pdf_to_latlon(x_pdf, y_pdf, anchor, scale_ft_per_inch):
    """Convert unrotated PDF coords to (lat, lon).

    For a 270-deg rotated, north-up rendered page:
        +x_pdf -> NORTH, +y_pdf -> EAST.
    Optional rotation_deg in anchor allows fine adjustment if the drawing's
    north arrow is not exactly aligned with the page edge.
    """
    fpp = scale_ft_per_inch / PT_PER_INCH
    lat0, lon0 = anchor["lat0"], anchor["lon0"]
    x0, y0 = anchor["x0"], anchor["y0"]
    north_ft = (x_pdf - x0) * fpp
    east_ft = (y_pdf - y0) * fpp
    rot = anchor.get("rotation_deg", 0.0)
    if rot:
        rad = math.radians(rot)
        nf = north_ft * math.cos(rad) - east_ft * math.sin(rad)
        ef = north_ft * math.sin(rad) + east_ft * math.cos(rad)
        north_ft, east_ft = nf, ef
    lat = lat0 + north_ft / FEET_PER_DEG_LAT
    lon = lon0 + east_ft / feet_per_deg_lon(lat0)
    return lat, lon


def page_corner_bounds(anchor, page_w_pdf, page_h_pdf, scale_ft_per_inch):
    """Return north/south/east/west of the rendered PNG corners.

    page_size from PyMuPDF's page.rect on a rotated page is the rotated rect
    (width=1224, height=792 for these jobs). Rendered PNG covers the full
    rotated rect; inverse-rotate each rendered corner to unrotated PDF coords:
        rendered TL (rx=0, ry=0)         <-> (page_h, 0)
        rendered TR (rx=W, ry=0)         <-> (page_h, page_w)
        rendered BL (rx=0, ry=H)         <-> (0, 0)
        rendered BR (rx=W, ry=H)         <-> (0, page_w)
    where W=page_w_pdf, H=page_h_pdf, page_h=page_w_pdf (rotated width).
    """
    corners = [
        (page_h_pdf, 0),
        (page_h_pdf, page_w_pdf),
        (0, 0),
        (0, page_w_pdf),
    ]
    lats, lons = [], []
    for x, y in corners:
        lat, lon = pdf_to_latlon(x, y, anchor, scale_ft_per_inch)
        lats.append(lat); lons.append(lon)
    return {"north": max(lats), "south": min(lats), "east": max(lons), "west": min(lons)}


def apply_two_corner_anchor(corner_a, corner_b, scale_ft_per_inch):
    """Build an anchor dict from two (x_pdf, y_pdf, lat, lon) reference points.

    Anchors at corner_a and computes the rotation that makes corner_b's
    geographic position consistent with the +x_pdf=NORTH/+y_pdf=EAST
    convention at the given scale.

    Returns None if the two corners are too close to fit (<10 PDF points).
    """
    xa, ya, lat_a, lon_a = corner_a
    xb, yb, lat_b, lon_b = corner_b
    dx_pdf = xb - xa
    dy_pdf = yb - ya
    if math.hypot(dx_pdf, dy_pdf) < 10.0:
        return None
    fpp = scale_ft_per_inch / PT_PER_INCH

    # Predicted (north_ft, east_ft) under zero rotation
    pred_north = dx_pdf * fpp
    pred_east = dy_pdf * fpp

    # Observed (north_ft, east_ft) from geographic delta
    obs_north = (lat_b - lat_a) * FEET_PER_DEG_LAT
    obs_east = (lon_b - lon_a) * feet_per_deg_lon(lat_a)

    # Rotation that takes predicted -> observed (in feet-space)
    pred_angle = math.atan2(pred_east, pred_north)
    obs_angle = math.atan2(obs_east, obs_north)
    rot_deg = math.degrees(obs_angle - pred_angle)

    return {
        "x0": xa, "y0": ya,
        "lat0": lat_a, "lon0": lon_a,
        "rotation_deg": rot_deg,
    }


# ----- Page rendering -----
def render_site_plan(
    page,
    dpi,
    supersample=SUPERSAMPLE_FACTOR,
    sharpen=True,
    unsharp_radius=UNSHARP_RADIUS,
    unsharp_percent=UNSHARP_PERCENT,
    unsharp_threshold=UNSHARP_THRESHOLD,
    contrast_boost=CONTRAST_BOOST,
):
    """Render one PDF page to a PIL.Image with optional sharpen + contrast pass.

    Page rotation is applied implicitly by PyMuPDF's get_pixmap so the rendered
    image is north-up for the common 270-rotated CD pages; the geographic
    transform downstream depends on that orientation, so do not override it
    here. When supersample > 1, the page is rendered at dpi * supersample and
    Lanczos-downsampled to dpi.
    """
    render_dpi = dpi * supersample
    matrix = fitz.Matrix(render_dpi / PT_PER_INCH, render_dpi / PT_PER_INCH)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    if supersample > 1:
        target_w = int(round(pix.width / supersample))
        target_h = int(round(pix.height / supersample))
        img = img.resize((target_w, target_h), Image.LANCZOS)
    if sharpen:
        img = img.filter(ImageFilter.UnsharpMask(
            radius=unsharp_radius,
            percent=unsharp_percent,
            threshold=unsharp_threshold,
        ))
        img = ImageEnhance.Contrast(img).enhance(contrast_boost)
    return img


# ----- Pipeline helpers (reusable across single-PDF and multi-PRM modes) -----
def _extract_pdf_pages_metadata(pdf_path):
    """Open a PDF and walk every page collecting site / non-site metadata.

    Returns (pages_meta, cover_anchors, doc) where:
      pages_meta: list of dicts (one per page in PDF order). Site pages carry
        embedded latlon, route endpoints, parsed SITE PLAN ordinal.
      cover_anchors: list of (page_no, x_pdf, y_pdf, lat, lon) harvested from
        non-site pages; used as a last-resort seed.
      doc: the open fitz.Document (caller responsible for closing).
    """
    doc = fitz.open(str(pdf_path))
    pages_meta = []
    cover_anchors = []
    for i, page in enumerate(doc):
        blocks = text_blocks(page)
        # MediaBox = unrotated; matches the coord system get_text returns.
        mb = page.mediabox
        page_w_un, page_h_un = mb.width, mb.height
        site = is_site_plan(blocks, i, page_w_un, page_h_un)
        meta = {
            "page_number": i + 1,
            "is_site": site,
            "page_size_unrotated": [page_w_un, page_h_un],
            "page_size": [page.rect.width, page.rect.height],  # rotated; kept for page_corner_bounds
            "rotation": page.rotation,
        }
        if site and page.rotation != 270:
            print(f"WARN: page {i + 1}: rotation={page.rotation} (expected 270 for "
                  f"the standard MasTec/Comcast portrait-stored layout). The "
                  f"+x_pdf=NORTH/+y_pdf=EAST geographic transform is only valid "
                  f"for rotation=270; this page's overlay will be misoriented. "
                  f"Supply a manual two-corner anchor for this page or convert "
                  f"the source PDF to rotation=270 before re-running.",
                  file=sys.stderr)
        if site:
            meta["embedded"] = extract_any_latlon(blocks, page_w_un, page_h_un)
            meta["entry_pdf"], meta["exit_pdf"] = extract_route_endpoints(page)
            meta["site_plan_ordinal"] = parse_site_plan_ordinal(blocks, page_w_un, page_h_un)
        else:
            cov = extract_any_latlon(blocks, page_w_un, page_h_un)
            if cov:
                x, y, lat, lon = cov
                cover_anchors.append((i + 1, x, y, lat, lon))
        pages_meta.append(meta)
    return pages_meta, cover_anchors, doc


def _render_site_pages(doc, pages_meta, image_dir, **render_kwargs):
    """Render site plan pages to PNG and stamp image_path back into pages_meta."""
    image_dir = Path(image_dir); image_dir.mkdir(parents=True, exist_ok=True)
    for m in pages_meta:
        if not m["is_site"]:
            continue
        n = m["page_number"]
        page = doc[n - 1]
        img = render_site_plan(page, **render_kwargs)
        m["image_path"] = image_dir / f"sheet_{n:02d}.png"
        img.save(str(m["image_path"]), format="PNG", optimize=True, compress_level=9)


def _anchor_one_site_page(m, manual_anchors, cover_pool, scale_ft_per_inch, state, current_label,
                          legacy_text_anchor=False):
    """Run the precedence ladder (manual > embedded > forward-chain > cover > none).

    Returns (anchor, note, new_state, used_cover):
      anchor: dict with x0/y0/lat0/lon0/rotation_deg/_page or None
      note: human-readable description text
      new_state: dict for chaining {prev_anchor, prev_exit, prev_label}
                 or the input state if no anchor was found
      used_cover: True if the cover_pool was consumed
    """
    n = m["page_number"]
    anchor = None
    note = ""
    used_cover = False

    # 1. Manual anchor (highest priority)
    ma = manual_anchors.get(f"page_{n}") or manual_anchors.get(str(n))
    if ma:
        if "two_corner" in ma and len(ma["two_corner"]) == 2:
            ca = ma["two_corner"][0]; cb = ma["two_corner"][1]
            anchor = apply_two_corner_anchor(
                (ca["x_pdf"], ca["y_pdf"], ca["lat"], ca["lon"]),
                (cb["x_pdf"], cb["y_pdf"], cb["lat"], cb["lon"]),
                scale_ft_per_inch,
            )
            if anchor is not None:
                note = (f"Two-corner manual anchor: A=PDF ({ca['x_pdf']:.1f},{ca['y_pdf']:.1f})->"
                        f"({ca['lat']:.6f},{ca['lon']:.6f}); B=PDF ({cb['x_pdf']:.1f},"
                        f"{cb['y_pdf']:.1f})->({cb['lat']:.6f},{cb['lon']:.6f}); "
                        f"rotation_deg={anchor['rotation_deg']:.3f}. Confidence: HIGH.")
        elif "lat" in ma and "lon" in ma:
            anchor = {
                "x0": ma.get("x_pdf", 0),
                "y0": ma.get("y_pdf", 0),
                "lat0": ma["lat"],
                "lon0": ma["lon"],
                "rotation_deg": ma.get("rotation_deg", 0.0),
            }
            note = (f"Manual anchor PDF ({anchor['x0']:.1f}, {anchor['y0']:.1f}) "
                    f"-> ({anchor['lat0']:.6f}, {anchor['lon0']:.6f}). Confidence: HIGH.")
    # 2. Embedded latlon on this page (inline or split LAT/LONG)
    if anchor is None and m.get("embedded"):
        x, y, lat, lon = m["embedded"]
        rep = closest_route_endpoint((x, y), m.get("entry_pdf"), m.get("exit_pdf"))
        if rep is not None and not legacy_text_anchor:
            anchor = {"x0": rep[0], "y0": rep[1],
                      "lat0": lat, "lon0": lon, "rotation_deg": 0.0}
            note = (f"Embedded lat/lon stamp at PDF ({x:.1f}, {y:.1f}) bound to "
                    f"nearest route endpoint PDF ({rep[0]:.1f}, {rep[1]:.1f}) -> "
                    f"({lat:.6f}, {lon:.6f}). Confidence: HIGH.")
        else:
            anchor = {"x0": x, "y0": y, "lat0": lat, "lon0": lon, "rotation_deg": 0.0}
            reason = ("legacy mode" if legacy_text_anchor
                      else "no route polyline endpoint detected on this page")
            note = (f"Embedded lat/lon stamp at PDF ({x:.1f}, {y:.1f}) -> "
                    f"({lat:.6f}, {lon:.6f}); anchored at text centroid "
                    f"({reason}). Confidence: MEDIUM.")
    # 3. Forward chain from prior anchored page (state)
    if anchor is None and state and state.get("prev_anchor") and state.get("prev_exit"):
        prev_anchor = state["prev_anchor"]
        prev_exit = state["prev_exit"]
        prev_label = state.get("prev_label", f"page {prev_anchor.get('_page', '?')}")
        entry = m.get("entry_pdf")
        if entry:
            ex_lat, ex_lon = pdf_to_latlon(prev_exit[0], prev_exit[1], prev_anchor, scale_ft_per_inch)
            anchor = {
                "x0": entry[0], "y0": entry[1],
                "lat0": ex_lat, "lon0": ex_lon,
                "rotation_deg": prev_anchor.get("rotation_deg", 0.0),
            }
            note = (f"Chained from {prev_label} route exit "
                    f"PDF ({prev_exit[0]:.1f}, {prev_exit[1]:.1f}) -> ({ex_lat:.6f}, {ex_lon:.6f}); "
                    f"aligned to page {n} route entry PDF ({entry[0]:.1f}, {entry[1]:.1f}). "
                    f"Confidence: MEDIUM (errors compound through chain). If satellite imagery does "
                    f"not line up, right-click the overlay -> Properties -> Location, adjust corners.")
    # 4. Cover-page lat/lon harvested from a non-site page
    if anchor is None and cover_pool:
        cp_page, _cx, _cy, cp_lat, cp_lon = cover_pool[0]
        entry = m.get("entry_pdf")
        if entry:
            anchor = {"x0": entry[0], "y0": entry[1],
                      "lat0": cp_lat, "lon0": cp_lon, "rotation_deg": 0.0}
            note = (f"Anchored from cover/notes lat/lon stamp on page {cp_page} "
                    f"-> ({cp_lat:.6f}, {cp_lon:.6f}); attached to route entry PDF "
                    f"({entry[0]:.1f}, {entry[1]:.1f}). Confidence: MEDIUM. If satellite "
                    f"imagery does not line up, right-click the overlay -> Properties -> "
                    f"Location, adjust corners.")
        else:
            cx_pdf = m["page_size_unrotated"][0] / 2  # was m["page_size"][1] / 2
            cy_pdf = m["page_size_unrotated"][1] / 2  # was m["page_size"][0] / 2
            anchor = {"x0": cx_pdf, "y0": cy_pdf,
                      "lat0": cp_lat, "lon0": cp_lon, "rotation_deg": 0.0}
            note = (f"Anchored at page center using cover/notes lat/lon stamp on page "
                    f"{cp_page} -> ({cp_lat:.6f}, {cp_lon:.6f}); no route polyline "
                    f"detected on this page. Confidence: LOW (rough). Right-click the "
                    f"overlay -> Properties -> Location, adjust corners.")
        used_cover = True

    if anchor is None:
        note = ("NO ANCHOR available. Sheet placed at default position; "
                "manual placement of all 4 corners required in Google Earth Pro. Confidence: LOW.")
        return None, note, state, False

    anchor["_page"] = n
    new_state = {
        "prev_anchor": anchor,
        "prev_exit": m.get("exit_pdf"),
        "prev_label": current_label or f"page {n}",
    }
    return anchor, note, new_state, used_cover


def _backward_chain_one(cur_meta, nxt_meta, anchors, notes, scale_ft_per_inch,
                        cur_key, nxt_key, nxt_label, debug=False):
    """Fill in cur's anchor by chaining backward from nxt's anchor + entry endpoint.

    cur_key / nxt_key are the keys used in the anchors / notes dicts
    (page_number for single-PDF, (prm_name, page_number) for cross-PRM).
    nxt_label is the human-readable label for nxt used in the note text.
    Returns True if an anchor was assigned to cur.
    """
    if anchors.get(cur_key) is not None:
        return False
    nxt_anchor = anchors.get(nxt_key)
    if nxt_anchor is None:
        return False
    nxt_entry = nxt_meta.get("entry_pdf")
    cur_exit = cur_meta.get("exit_pdf")
    if not nxt_entry or not cur_exit:
        return False
    en_lat, en_lon = pdf_to_latlon(nxt_entry[0], nxt_entry[1], nxt_anchor, scale_ft_per_inch)
    cur_n = cur_meta["page_number"]
    anchor = {
        "x0": cur_exit[0], "y0": cur_exit[1],
        "lat0": en_lat, "lon0": en_lon,
        "rotation_deg": nxt_anchor.get("rotation_deg", 0.0),
        "_page": cur_n,
    }
    anchors[cur_key] = anchor
    notes[cur_key] = (
        f"Back-chained from {nxt_label} route entry PDF "
        f"({nxt_entry[0]:.1f}, {nxt_entry[1]:.1f}) -> ({en_lat:.6f}, {en_lon:.6f}); "
        f"aligned to page {cur_n} route exit PDF ({cur_exit[0]:.1f}, {cur_exit[1]:.1f}). "
        f"Confidence: MEDIUM (errors compound through chain). If satellite imagery does "
        f"not line up, right-click the overlay -> Properties -> Location, adjust corners."
    )
    if debug:
        print(f"  page {cur_n}: {notes[cur_key]}", file=sys.stderr)
    return True


def _build_overlays(site_pages, anchors, notes, scale_ft_per_inch,
                    sheet_label_fn=None, anchor_key_fn=None, note_key_fn=None):
    """Assemble overlay records from anchored site pages.

    sheet_label_fn(meta) returns the integer/string used in the overlay name;
    defaults to the parsed "SITE PLAN - N" title-block ordinal when present,
    falling back to (page_number - 4) — the existing single-PDF heuristic
    for the validated MasTec/Comcast CD layout (4 non-site preamble pages,
    site plans starting at page 5).
    """
    if sheet_label_fn is None:
        def sheet_label_fn(m):
            ord_ = m.get("site_plan_ordinal")
            return ord_ if ord_ is not None else m["page_number"] - 4
    if anchor_key_fn is None:
        anchor_key_fn = lambda m: m["page_number"]
    if note_key_fn is None:
        note_key_fn = anchor_key_fn

    fallback_lat, fallback_lon = 0.0, 0.0
    if any(a for a in anchors.values()):
        any_anchor = next(a for a in anchors.values() if a)
        fallback_lat, fallback_lon = any_anchor["lat0"], any_anchor["lon0"]

    overlays = []
    for m in site_pages:
        a = anchors.get(anchor_key_fn(m))
        if a is None:
            bounds = {"north": fallback_lat + 0.001, "south": fallback_lat - 0.001,
                      "east": fallback_lon + 0.001, "west": fallback_lon - 0.001}
        else:
            bounds = page_corner_bounds(a, m["page_size"][0], m["page_size"][1], scale_ft_per_inch)
        sheet_label = sheet_label_fn(m)
        overlays.append({
            "page": m["page_number"],
            "sheet_label": sheet_label,
            "name": f"SITE PLAN - {sheet_label} (PDF page {m['page_number']})",
            "description": notes.get(note_key_fn(m), ""),
            "image_path": m.get("image_path"),
            "north": bounds["north"], "south": bounds["south"],
            "east": bounds["east"], "west": bounds["west"],
            "rotation": 0.0,
        })
    return overlays


def _dump_debug_coords(label, overlays, anchors, notes):
    """Print a one-line-per-page diagnostic of anchor source, PDF coords, and bounds.

    label: e.g. "single PDF" or a PRM name.
    anchors and notes must be keyed by overlay page number (ov["page"]).
    """
    print(f"== DEBUG COORDS: {label} ==", file=sys.stderr)
    print(f"  {'page':>4}  {'sheet':>5}  {'anchor_x':>9}  {'anchor_y':>9}  "
          f"{'anchor_lat':>11}  {'anchor_lon':>12}  {'N':>9}  {'S':>9}  "
          f"{'E':>10}  {'W':>10}  source", file=sys.stderr)
    for ov in overlays:
        a = anchors.get(ov["page"])
        if a is None:
            print(f"  {ov['page']:>4}  {ov['sheet_label']:>5}  "
                  f"{'(none)':>9}  {'(none)':>9}  {'-':>11}  {'-':>12}  "
                  f"{ov['north']:>9.6f}  {ov['south']:>9.6f}  "
                  f"{ov['east']:>10.6f}  {ov['west']:>10.6f}  NO ANCHOR",
                  file=sys.stderr)
            continue
        note = notes.get(ov["page"], "")
        # First few words of the note encode the source
        source = note.split(".", 1)[0][:48] if note else "?"
        print(f"  {ov['page']:>4}  {ov['sheet_label']:>5}  "
              f"{a['x0']:>9.1f}  {a['y0']:>9.1f}  "
              f"{a['lat0']:>11.6f}  {a['lon0']:>12.6f}  "
              f"{ov['north']:>9.6f}  {ov['south']:>9.6f}  "
              f"{ov['east']:>10.6f}  {ov['west']:>10.6f}  {source}",
              file=sys.stderr)


# ----- Single-PDF orchestrator -----
def process_pdf(
    pdf_path,
    dpi,
    scale_ft_per_inch,
    manual_anchors,
    image_dir,
    debug=False,
    legacy_text_anchor=False,
    supersample=SUPERSAMPLE_FACTOR,
    sharpen=True,
    unsharp_radius=UNSHARP_RADIUS,
    unsharp_percent=UNSHARP_PERCENT,
    unsharp_threshold=UNSHARP_THRESHOLD,
    contrast_boost=CONTRAST_BOOST,
):
    """Process one PDF. Render site plans, build anchors, and return results.

    Returns (overlays, anchors, notes) where:
      overlays: list of overlay dicts (the original return).
      anchors: dict mapping page_number -> anchor dict (or None for unanchored pages).
      notes:   dict mapping page_number -> human-readable description string.
    """
    pages_meta, cover_anchors, doc = _extract_pdf_pages_metadata(pdf_path)

    render_kwargs = dict(
        dpi=dpi, supersample=supersample, sharpen=sharpen,
        unsharp_radius=unsharp_radius, unsharp_percent=unsharp_percent,
        unsharp_threshold=unsharp_threshold, contrast_boost=contrast_boost,
    )
    _render_site_pages(doc, pages_meta, image_dir, **render_kwargs)

    site_pages = [m for m in pages_meta if m["is_site"]]
    site_pages.sort(key=lambda x: x["page_number"])

    anchors, notes = {}, {}
    state = None
    cover_used = False
    for m in site_pages:
        cover_pool = cover_anchors if not cover_used else []
        anchor, note, new_state, used_cover = _anchor_one_site_page(
            m, manual_anchors, cover_pool, scale_ft_per_inch, state,
            current_label=None,  # single-PDF mode uses default "page N" label
            legacy_text_anchor=legacy_text_anchor,
        )
        if used_cover:
            cover_used = True
        n = m["page_number"]
        anchors[n] = anchor
        notes[n] = note
        if anchor is not None:
            state = new_state
        if debug:
            print(f"  page {n}: {note}", file=sys.stderr)

    # Backward chain
    for i in reversed(range(len(site_pages) - 1)):
        cur = site_pages[i]
        nxt = site_pages[i + 1]
        _backward_chain_one(
            cur, nxt, anchors, notes, scale_ft_per_inch,
            cur_key=cur["page_number"], nxt_key=nxt["page_number"],
            nxt_label=f"page {nxt['page_number']}",
            debug=debug,
        )

    overlays = _build_overlays(site_pages, anchors, notes, scale_ft_per_inch)
    doc.close()
    return overlays, anchors, notes


# ----- Multi-PRM orchestrator with cross-PRM ordinal chaining -----
def process_multi_prm(
    jb_dir,
    dpi,
    scale_ft_per_inch,
    manual,
    nested_manual,
    debug=False,
    reconciliation_threshold_m=DEFAULT_RECONCILIATION_THRESHOLD_M,
    legacy_text_anchor=False,
    supersample=SUPERSAMPLE_FACTOR,
    sharpen=True,
    unsharp_radius=UNSHARP_RADIUS,
    unsharp_percent=UNSHARP_PERCENT,
    unsharp_threshold=UNSHARP_THRESHOLD,
    contrast_boost=CONTRAST_BOOST,
):
    """Multi-PRM pipeline with cross-PRM ordinal chaining.

    Returns list of (prm_name, pdf_path, overlays, prm_anchors, prm_notes) tuples in iteration order.
    prm_anchors and prm_notes are per-PRM dicts keyed by page_number, suitable for passing to _dump_debug_coords.

    Cross-PRM ordinal chaining:
      Every site plan across every PRM is flattened into a single sequence
      keyed by the parsed "SITE PLAN - N" title-block ordinal. The forward +
      backward chain math is run across this global sequence so a PRM with
      no embedded lat/lon anchors off the prior PRM's exit endpoint instead
      of a local fallback. State resets at ordinal gaps (no interpolation).
      Pages with no parseable ordinal fall back to per-PRM behavior in an
      isolated leftover pass. Multiple-embedded reconciliation logs a
      warning when chain prediction at a meet point differs from the
      embedded coord by more than reconciliation_threshold_m meters; embedded
      anchors always win per page (no silent averaging).
    """
    jb_dir = Path(jb_dir)
    render_kwargs = dict(
        dpi=dpi, supersample=supersample, sharpen=sharpen,
        unsharp_radius=unsharp_radius, unsharp_percent=unsharp_percent,
        unsharp_threshold=unsharp_threshold, contrast_boost=contrast_boost,
    )

    # ----- Phase 1: per-PRM extraction + render -----
    prm_results = []  # list of dicts: {prm_name, pdf_path, doc, pages_meta, cover_anchors, prm_manual}
    for prm_name, pdf in find_prm_pdfs(jb_dir):
        prm_manual = manual.get(prm_name, {}) if nested_manual else manual
        if debug:
            print(f"== Extracting {prm_name}: {pdf.name} ==", file=sys.stderr)
        pages_meta, cover_anchors, doc = _extract_pdf_pages_metadata(pdf)
        img_dir = pdf.parent / "_overlay_images"
        _render_site_pages(doc, pages_meta, img_dir, **render_kwargs)
        prm_results.append({
            "prm_name": prm_name,
            "pdf_path": pdf,
            "doc": doc,
            "pages_meta": pages_meta,
            "cover_anchors": cover_anchors,
            "prm_manual": prm_manual,
        })

    if not prm_results:
        return []

    # ----- Phase 2: build global ordered list keyed by SITE PLAN ordinal -----
    global_sites = []   # list of (ordinal, prm_idx, prm_name, page_meta)
    leftover = {}       # prm_name -> list of site pages with no parseable ordinal
    for prm_idx, res in enumerate(prm_results):
        for m in res["pages_meta"]:
            if not m["is_site"]:
                continue
            ord_val = m.get("site_plan_ordinal")
            if ord_val is None:
                print(f"WARN: {res['prm_name']}/page {m['page_number']}: "
                      f"no parseable SITE PLAN ordinal; falling back to per-PRM "
                      f"behavior for this page", file=sys.stderr)
                leftover.setdefault(res["prm_name"], []).append(m)
            else:
                global_sites.append((ord_val, prm_idx, res["prm_name"], m))

    # ----- Phase 3: sort + detect gaps -----
    # Sort by (ordinal, prm_idx). Tie-break on prm_idx is the documented overlap
    # rule: if two PRMs share an ordinal, lower-prm-index PRM is processed first
    # and the higher-prm-index PRM's same-ordinal sheet anchors off the first's
    # exit endpoint geometry. Both overlays are kept.
    global_sites.sort(key=lambda x: (x[0], x[1]))

    # gap_indices: indices in the sorted list where the prior entry has a
    # smaller ordinal that is NOT N-1 (i.e., an ordinal hole exists). Chain
    # state is reset before processing this index. Overlapping pairs (same
    # ordinal) do NOT count as gaps.
    gap_indices = set()
    prev_ord = None
    for i, (ord_val, _, _, _) in enumerate(global_sites):
        if prev_ord is not None and ord_val > prev_ord + 1:
            gap_indices.add(i)
            print(f"WARN: ordinal gap detected between SITE PLAN - {prev_ord} "
                  f"and SITE PLAN - {ord_val}; missing ordinals {prev_ord + 1}..{ord_val - 1}; "
                  f"chain will reset at this boundary", file=sys.stderr)
        prev_ord = ord_val

    # ----- Phase 4: forward chain across global sequence -----
    # Anchor / note storage keyed by (prm_name, page_number) so leftover
    # pass can use the same dicts safely.
    anchors = {}
    notes = {}
    cover_used_by_prm = {res["prm_name"]: False for res in prm_results}

    state = None
    for i, (ord_val, prm_idx, prm_name, m) in enumerate(global_sites):
        if i in gap_indices:
            state = None  # reset chain across ordinal gap

        prm_manual = next(r["prm_manual"] for r in prm_results if r["prm_name"] == prm_name)
        cover_pool = (next(r["cover_anchors"] for r in prm_results if r["prm_name"] == prm_name)
                      if not cover_used_by_prm[prm_name] else [])
        current_label = f"{prm_name}/SITE PLAN - {ord_val}"

        anchor, note, new_state, used_cover = _anchor_one_site_page(
            m, prm_manual, cover_pool, scale_ft_per_inch, state, current_label,
            legacy_text_anchor=legacy_text_anchor,
        )
        if used_cover:
            cover_used_by_prm[prm_name] = True

        key = (prm_name, m["page_number"])
        anchors[key] = anchor
        notes[key] = note
        if anchor is not None:
            state = new_state
        if debug:
            print(f"  {prm_name}/SITE PLAN - {ord_val}: {note}", file=sys.stderr)

    # ----- Phase 5: backward chain across global sequence (gap-aware) -----
    for i in reversed(range(len(global_sites) - 1)):
        if (i + 1) in gap_indices:
            continue
        ord_val, _, prm_name, cur = global_sites[i]
        nxt_ord, _, nxt_prm, nxt = global_sites[i + 1]
        cur_key = (prm_name, cur["page_number"])
        nxt_key = (nxt_prm, nxt["page_number"])
        nxt_label = f"{nxt_prm}/SITE PLAN - {nxt_ord}"
        _backward_chain_one(cur, nxt, anchors, notes, scale_ft_per_inch,
                            cur_key=cur_key, nxt_key=nxt_key, nxt_label=nxt_label,
                            debug=debug)

    # ----- Phase 6: multiple-embedded reconciliation -----
    embedded_entries = [
        (idx, e) for idx, e in enumerate(global_sites) if e[3].get("embedded")
    ]
    for j in range(len(embedded_entries) - 1):
        idx1, e1 = embedded_entries[j]
        idx2, e2 = embedded_entries[j + 1]
        # Skip if a gap lies between them
        if any((g > idx1) and (g <= idx2) for g in gap_indices):
            continue
        ord1, _, prm1, m1 = e1
        ord2, _, prm2, m2 = e2
        a1 = anchors.get((prm1, m1["page_number"]))
        if a1 is None:
            continue
        # Walk the chain forward from a1 through every intervening entry to
        # produce a hypothetical anchor that would apply to m2. Then compute
        # what that hypothetical anchor predicts for m2's embedded location
        # and compare to the actual embedded coord.
        cur_anchor = a1
        cur_exit = m1.get("exit_pdf")
        ok = True
        for k in range(idx1 + 1, idx2 + 1):
            _, _, _, k_m = global_sites[k]
            k_entry = k_m.get("entry_pdf")
            if not cur_exit or not k_entry:
                ok = False
                break
            seg_lat, seg_lon = pdf_to_latlon(cur_exit[0], cur_exit[1], cur_anchor, scale_ft_per_inch)
            cur_anchor = {
                "x0": k_entry[0], "y0": k_entry[1],
                "lat0": seg_lat, "lon0": seg_lon,
                "rotation_deg": cur_anchor.get("rotation_deg", 0.0),
            }
            cur_exit = k_m.get("exit_pdf")
        if not ok:
            continue
        embx, emby, emblat, emblon = m2["embedded"]
        pred_lat, pred_lon = pdf_to_latlon(embx, emby, cur_anchor, scale_ft_per_inch)
        d_north_ft = (pred_lat - emblat) * FEET_PER_DEG_LAT
        d_east_ft = (pred_lon - emblon) * feet_per_deg_lon(emblat)
        delta_m = math.sqrt(d_north_ft * d_north_ft + d_east_ft * d_east_ft) * METERS_PER_FOOT
        if delta_m > reconciliation_threshold_m:
            print(f"WARN: embedded-anchor reconciliation: chain from "
                  f"{prm1}/SITE PLAN - {ord1} predicts {prm2}/SITE PLAN - {ord2} "
                  f"embedded position {delta_m:.1f} m off (threshold "
                  f"{reconciliation_threshold_m:.1f} m); embedded anchor wins, "
                  f"no averaging applied", file=sys.stderr)

    # ----- Phase 7: leftover pages (no ordinal) get isolated per-PRM passes -----
    for prm_name, leftover_pages in leftover.items():
        leftover_pages.sort(key=lambda m: m["page_number"])
        sub_state = None
        sub_cover_used = cover_used_by_prm[prm_name]
        for m in leftover_pages:
            res = next(r for r in prm_results if r["prm_name"] == prm_name)
            cover_pool = res["cover_anchors"] if not sub_cover_used else []
            anchor, note, new_state, used_cover = _anchor_one_site_page(
                m, res["prm_manual"], cover_pool, scale_ft_per_inch, sub_state,
                current_label=None,
                legacy_text_anchor=legacy_text_anchor,
            )
            if used_cover:
                sub_cover_used = True
            key = (prm_name, m["page_number"])
            anchors[key] = anchor
            notes[key] = note
            if anchor is not None:
                sub_state = new_state

    # ----- Phase 8: build overlays per-PRM -----
    out = []
    for res in prm_results:
        prm_name = res["prm_name"]
        site_pages = [m for m in res["pages_meta"] if m["is_site"]]
        site_pages.sort(key=lambda x: x["page_number"])
        prm_anchors = {m["page_number"]: anchors.get((prm_name, m["page_number"])) for m in site_pages}
        prm_notes = {m["page_number"]: notes.get((prm_name, m["page_number"]), "") for m in site_pages}
        overlays = _build_overlays(site_pages, prm_anchors, prm_notes, scale_ft_per_inch)
        res["doc"].close()
        out.append((prm_name, res["pdf_path"], overlays, prm_anchors, prm_notes))
    return out


# ----- KMZ assembly -----
def _zip_writestr(zf, arcname, data, compress_type=zipfile.ZIP_DEFLATED):
    """Add a file to the KMZ with a fixed date_time so reruns are byte-identical."""
    info = zipfile.ZipInfo(filename=arcname, date_time=ZIP_DATE)
    info.compress_type = compress_type
    info.external_attr = 0o644 << 16
    zf.writestr(info, data)


def write_kmz(overlays, kmz_path, doc_name, doc_description, image_subdir="images",
              source_pdf=None, pdf_subdir="pdfs"):
    """Write per-PRM (or per-PDF) KMZ.

    If source_pdf is supplied, it is embedded inside the KMZ at
    `<pdf_subdir>/<source_pdf.name>` and a clickable link is added to the
    Document description.
    """
    pdf_link_html = ""
    if source_pdf is not None:
        pdf_link_html = (
            f'<p><a href="{escape(pdf_subdir)}/{escape(source_pdf.name)}">'
            f'Open original drawing PDF: {escape(source_pdf.name)}</a></p>'
        )
    kml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>',
        f'<name>{escape(doc_name)}</name>',
        f'<description><![CDATA[{doc_description}{pdf_link_html}]]></description>',
        '<open>1</open>',
        '<Folder>',
        f'<name>Site Plan Sheets ({len(overlays)})</name>',
    ]
    for ov in overlays:
        img_name = Path(ov["image_path"]).name
        kml_lines += [
            '<GroundOverlay>',
            f'  <name>{escape(ov["name"])}</name>',
            f'  <description><![CDATA[{ov.get("description", "")}]]></description>',
            '  <Icon>',
            f'    <href>{image_subdir}/{img_name}</href>',
            '    <viewBoundScale>0.75</viewBoundScale>',
            '  </Icon>',
            '  <LatLonBox>',
            f'    <north>{ov["north"]:.8f}</north>',
            f'    <south>{ov["south"]:.8f}</south>',
            f'    <east>{ov["east"]:.8f}</east>',
            f'    <west>{ov["west"]:.8f}</west>',
            f'    <rotation>{ov["rotation"]:.4f}</rotation>',
            '  </LatLonBox>',
            '</GroundOverlay>',
        ]
    kml_lines += ['</Folder>', '</Document>', '</kml>']
    kml_text = "\n".join(kml_lines)

    kmz_path = Path(kmz_path)
    kmz_path.parent.mkdir(parents=True, exist_ok=True)
    if kmz_path.exists():
        kmz_path.unlink()
    with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        _zip_writestr(zf, 'doc.kml', kml_text.encode("utf-8"))
        for ov in overlays:
            _zip_writestr(zf, f"{image_subdir}/{Path(ov['image_path']).name}",
                          Path(ov["image_path"]).read_bytes())
        if source_pdf is not None and Path(source_pdf).exists():
            _zip_writestr(zf, f"{pdf_subdir}/{Path(source_pdf).name}",
                          Path(source_pdf).read_bytes())
    return kmz_path


def write_combined_kmz(jb_overlays, kmz_path, jb_name):
    """Combine multiple PRMs' overlays into one KMZ, organized by PRM folder.

    Each entry in jb_overlays is a tuple (prm_name, ovs) or
    (prm_name, ovs, source_pdf). When source_pdf is supplied it is embedded
    inside the combined KMZ at `pdfs/<source_pdf.name>` and a clickable link
    is added to the per-PRM Folder description.
    """
    kml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>',
        f'<name>{escape(jb_name)} - Combined Site Plan Overlays</name>',
        f'<description><![CDATA[Combined ground overlays for all PRMs in {jb_name}.]]></description>',
        '<open>1</open>',
    ]
    image_paths = []
    pdf_paths = []
    for entry in jb_overlays:
        if len(entry) == 3:
            prm_name, ovs, source_pdf = entry
        else:
            prm_name, ovs = entry
            source_pdf = None
        folder_desc = ""
        if source_pdf is not None:
            pdf_paths.append((source_pdf, Path(source_pdf).name))
            folder_desc = (
                f'<a href="pdfs/{escape(Path(source_pdf).name)}">'
                f'Open original drawing PDF: {escape(Path(source_pdf).name)}</a>'
            )
        kml_lines += [
            '<Folder>',
            f'<name>{escape(prm_name)} ({len(ovs)} sheets)</name>',
            f'<description><![CDATA[{folder_desc}]]></description>',
        ]
        for ov in ovs:
            img_name = f"{prm_name}__{Path(ov['image_path']).name}"
            image_paths.append((ov["image_path"], img_name))
            kml_lines += [
                '<GroundOverlay>',
                f'  <name>{escape(prm_name)} - {escape(ov["name"])}</name>',
                f'  <description><![CDATA[{ov.get("description", "")}]]></description>',
                '  <Icon>',
                f'    <href>images/{img_name}</href>',
                '    <viewBoundScale>0.75</viewBoundScale>',
                '  </Icon>',
                '  <LatLonBox>',
                f'    <north>{ov["north"]:.8f}</north>',
                f'    <south>{ov["south"]:.8f}</south>',
                f'    <east>{ov["east"]:.8f}</east>',
                f'    <west>{ov["west"]:.8f}</west>',
                f'    <rotation>{ov["rotation"]:.4f}</rotation>',
                '  </LatLonBox>',
                '</GroundOverlay>',
            ]
        kml_lines.append('</Folder>')
    kml_lines += ['</Document>', '</kml>']
    kml_text = "\n".join(kml_lines)

    kmz_path = Path(kmz_path)
    if kmz_path.exists():
        kmz_path.unlink()
    with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        _zip_writestr(zf, 'doc.kml', kml_text.encode("utf-8"))
        for src, dest in image_paths:
            _zip_writestr(zf, f"images/{dest}", Path(src).read_bytes())
        for src, dest in pdf_paths:
            _zip_writestr(zf, f"pdfs/{dest}", Path(src).read_bytes())
    return kmz_path


# ----- Main entry -----
def find_prm_pdfs(jb_dir):
    """Walk a JB folder and yield (prm_name, pdf_path) for each PRM*/*.pdf child.

    Filters out renamed-copy PDFs of the form `PRM<digits>.pdf` (created by this
    script) so the original drawing is always selected on subsequent runs.
    """
    jb = Path(jb_dir)
    renamed_copy = re.compile(r'(?i)^PRM\d+\.pdf$')
    for prm in sorted(jb.iterdir()):
        if not prm.is_dir():
            continue
        if not re.match(r'(?i)PRM', prm.name):
            continue
        pdfs = [p for p in sorted(prm.glob("*.pdf")) if not renamed_copy.match(p.name)]
        if not pdfs:
            continue
        # Take the first PDF; warn if multiple
        if len(pdfs) > 1:
            print(f"WARN: multiple PDFs in {prm}; using {pdfs[0].name}", file=sys.stderr)
        yield prm.name, pdfs[0]


def main():
    ap = argparse.ArgumentParser(
        description="Convert multi-page CD PDFs into per-sheet KMZ ground overlays.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("input_path", help="PDF path OR JB[id] directory containing PRM[id]/*.pdf")
    ap.add_argument("--output", help="Output KMZ path (single-PDF mode). Default: <input>_overlays.kmz")
    ap.add_argument("--multi-prm", action="store_true",
                    help="Treat input_path as a JB folder; emit one KMZ per PRM child")
    ap.add_argument("--combined", action="store_true",
                    help="With --multi-prm, also emit JB-level combined KMZ")
    ap.add_argument("--manual-anchors", help="Optional JSON with per-page manual anchors")
    ap.add_argument("--scale-feet-per-inch", type=float, default=DEFAULT_SCALE_FT_PER_INCH,
                    help=f"Drawing scale (default {DEFAULT_SCALE_FT_PER_INCH})")
    ap.add_argument("--dpi", type=int, default=DEFAULT_DPI,
                    help=f"Render DPI (default {DEFAULT_DPI}; 600 is the floor for "
                         f"downstream LLM-vision triangulation, --dpi 800 for the "
                         f"most demanding cases)")
    ap.add_argument("--sharpen", action=argparse.BooleanOptionalAction, default=True,
                    help="Apply UnsharpMask + contrast boost after rendering (default on). "
                         "--no-sharpen skips both passes.")
    ap.add_argument("--unsharp-radius", type=float, default=UNSHARP_RADIUS,
                    help=f"UnsharpMask radius (default {UNSHARP_RADIUS})")
    ap.add_argument("--unsharp-percent", type=int, default=UNSHARP_PERCENT,
                    help=f"UnsharpMask percent (default {UNSHARP_PERCENT})")
    ap.add_argument("--unsharp-threshold", type=int, default=UNSHARP_THRESHOLD,
                    help=f"UnsharpMask threshold (default {UNSHARP_THRESHOLD})")
    ap.add_argument("--contrast-boost", type=float, default=CONTRAST_BOOST,
                    help=f"Contrast multiplier applied after sharpening "
                         f"(default {CONTRAST_BOOST}; ignored with --no-sharpen)")
    ap.add_argument("--reconciliation-threshold-m", type=float,
                    default=DEFAULT_RECONCILIATION_THRESHOLD_M,
                    help=f"In multi-PRM mode, log a warning when the chain prediction at "
                         f"a meet point between two embedded anchors differs by more than "
                         f"this distance in meters (default {DEFAULT_RECONCILIATION_THRESHOLD_M}). "
                         f"Embedded anchors always win per page; this flag controls only "
                         f"the diagnostic warning threshold.")
    ap.add_argument("--legacy-text-anchor", action="store_true",
                    help="Restore pre-fix behavior: anchor embedded lat/lon stamps at "
                         "the text bbox centroid instead of binding them to the nearest "
                         "route polyline endpoint. The default (off) is more accurate "
                         "for real CDs where the stamp text sits in a margin away from "
                         "the route. Use this only to reproduce older outputs.")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--debug-coords", action="store_true",
                    help="After building overlays, print a per-page table of anchor "
                         "source, PDF coords, lat/lon, and final LatLonBox to stderr. "
                         "Use this to diagnose 'placements look wrong in Google Earth' "
                         "without re-rendering — the table tells you which anchor source "
                         "won and which (x_pdf, y_pdf) it bound to.")
    args = ap.parse_args()

    render_kwargs = dict(
        sharpen=args.sharpen,
        unsharp_radius=args.unsharp_radius,
        unsharp_percent=args.unsharp_percent,
        unsharp_threshold=args.unsharp_threshold,
        contrast_boost=args.contrast_boost,
    )

    manual = {}
    if args.manual_anchors:
        manual = json.loads(Path(args.manual_anchors).read_text())

    inp = Path(args.input_path)
    # Manual anchors may be flat ({"page_N": {...}}) or nested per-PRM
    # ({"PRM0001388163": {"page_5": {...}}, ...}). Auto-detect via top-level keys.
    nested_manual = bool(manual) and any(re.match(r"(?i)^PRM", k) for k in manual)
    if args.multi_prm:
        if not inp.is_dir():
            sys.exit(f"--multi-prm requires a directory, got {inp}")
        prm_results = process_multi_prm(
            inp, args.dpi, args.scale_feet_per_inch, manual, nested_manual,
            debug=args.debug,
            reconciliation_threshold_m=args.reconciliation_threshold_m,
            legacy_text_anchor=args.legacy_text_anchor,
            **render_kwargs,
        )
        jb_overlays = []
        for prm_name, pdf, ovs, prm_anchors, prm_notes in prm_results:
            print(f"== Wrote overlays for {prm_name}: {pdf.name} ({len(ovs)} sheets) ==", file=sys.stderr)
            renamed_pdf = pdf.parent / f"{prm_name}.pdf"
            if renamed_pdf.resolve() != pdf.resolve():
                shutil.copy2(pdf, renamed_pdf)
            kmz_out = pdf.parent / f"{prm_name}_overlays.kmz"
            write_kmz(ovs, kmz_out,
                      doc_name=f"{inp.name} / {prm_name} - Site Plan Overlays",
                      doc_description=f"Ground overlays for {pdf.name}.",
                      source_pdf=renamed_pdf)
            print(f"  -> {kmz_out} ({len(ovs)} overlays, embedded {renamed_pdf.name})", file=sys.stderr)
            if args.debug_coords:
                _dump_debug_coords(prm_name, ovs, prm_anchors, prm_notes)
            jb_overlays.append((prm_name, ovs, renamed_pdf))
        if args.combined and jb_overlays:
            combined = inp / f"{inp.name}_combined_overlays.kmz"
            write_combined_kmz(jb_overlays, combined, jb_name=inp.name)
            print(f"== Combined KMZ -> {combined} ==", file=sys.stderr)
    else:
        if not inp.is_file():
            sys.exit(f"Single-PDF mode requires a file, got {inp}")
        out = Path(args.output) if args.output else inp.with_suffix("").with_name(inp.stem + "_overlays.kmz")
        img_dir = out.parent / f"{out.stem}_images"
        ovs, anchors, notes = process_pdf(inp, args.dpi, args.scale_feet_per_inch, manual, img_dir,
                                          args.debug, legacy_text_anchor=args.legacy_text_anchor,
                                          **render_kwargs)
        write_kmz(ovs, out,
                  doc_name=f"{inp.stem} - Site Plan Overlays",
                  doc_description=f"Ground overlays for {inp.name}.",
                  source_pdf=inp)
        print(f"Wrote {out} ({len(ovs)} overlays, embedded {inp.name})", file=sys.stderr)
        if args.debug_coords:
            _dump_debug_coords(inp.stem, ovs, anchors, notes)


if __name__ == "__main__":
    main()
