#!/usr/bin/env python3
"""
extract_routes.py — Sphere permit-map extractor (JB-grouped, markup-as-route).

Pipeline stages:
  1. Read page vectors from PyMuPDF. Bucket segments by (status, construction,
     stroke color, dash pattern) and chain connected endpoints into polylines.
  2. Read page annotations. FreeText => design notes. Line / PolyLine / Polygon
     / Ink / Circle / Square annotations become REAL route polylines with
     status=MARKUP so the drafter draws actual cable for them.
  3. Detect JB job numbers (e.g. JB0001914985) on the page. These are the real
     job numbers. INCWT codes (e.g. INCWT00900, INCW00900A1) are captured as
     sub_area labels under each JB. Title-block JB labels (top/bottom ~80 pts
     of the sheet) are excluded from spatial assignment so routes do not get
     pulled to whichever JB happened to be stamped in the corner.
  4. Each polyline is assigned to the nearest JB label within
     JB_MAX_ASSIGN_DIST, and to the nearest INCWT label within
     INCWT_MAX_ASSIGN_DIST. Polylines with no JB within range get
     job=UNASSIGNED.

Output JSON schema:
  {
    "pdf_path": str, "page": int,
    "polylines": [
      {
        "coords": [[x, y], ...],
        "status": "NEW" | "REPLACE" | "EXISTING" | "MARKUP",
        "construction": "AERIAL" | "UNDERGROUND" | "UNKNOWN",
        "job": "JB0001914985" | ... | "UNASSIGNED",
        "sub_area": "INCWT00900" | ... | None,
        "cable_count": int | null,
        "footage_ft": float | null,
        "stroke_color": [r, g, b],
        "source": "vector" | "annot_line" | "annot_polyline" |
                  "annot_polygon" | "annot_ink" | "annot_circle" |
                  "annot_square",
        "note": str,    # markup-only: original annotation content
      }
    ],
    "design_notes": [
      {"text": str, "pdf_x": float, "pdf_y": float, "rect": [x0,y0,x1,y1], "author": str}
    ],
    "jobs_jb": ["JB0001914985", ...],
    "sub_areas_incwt": ["INCWT00900", ...],
    "summary": {...}
  }

Usage:
    python extract_routes.py <pdf_path> [--page 0] [--output extracted_routes.json]
"""

import argparse
import json
import math
import re
import sys
from collections import defaultdict, Counter

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: pip install pymupdf --break-system-packages")
    sys.exit(1)


# --- Classification constants --------------------------------------------

# Vector stroke colors for NEW construction (RGB 0-1, loose match)
NEW_COLORS = [
    (1.0, 0.41, 0.12),
    (1.0, 0.0, 0.0),
    (0.929, 0.263, 0.106),
    (1.0, 0.5, 0.0),
    (1.0, 0.65, 0.0),
]
# Pink/faded red = REPLACE / abandon
REPLACE_COLORS = [
    (1.0, 0.75, 0.8),
    (0.95, 0.6, 0.65),
    (1.0, 0.6, 0.6),
]

AERIAL_HINTS = {"AER", "AERIAL", "OH", "OVERHEAD", "POLE", "STRAND", "MSGR",
                "MESSENGER", "LASH", "LASHED"}
UG_HINTS = {"UG", "U/G", "BORE", "TRENCH", "DUCT", "CONDUIT", "HDD",
            "DIRECTIONAL", "PLOW", "BURIED", "UNDERGROUND"}

# Job number regex: JB<5+digits> is the real job number.
JB_RE = re.compile(r'\b(JB\d{5,})\b')
# INCWT / INCW codes are sub-areas within a job.
INCWT_RE = re.compile(r'\b(INCWT\d{3,5}[A-Z]?\d?|INCW\d{3,5}[A-Z]?\d?)\b')

COUNT_RE = re.compile(r'(\d{2,4})\s*ct\b', re.I)
FOOTAGE_RE = re.compile(r"(\d+\.?\d*)\s*'")

SNAP_TOL = 1.5
LABEL_RADIUS = 35.0
# Keep sub-pixel reviewer tick marks; drafter decides what is meaningful.
MARKUP_MIN_LEN = 1.5

# How far a polyline centroid can be from a JB label and still be assigned.
JB_MAX_ASSIGN_DIST = 2500.0
INCWT_MAX_ASSIGN_DIST = 300.0

# Strip-height (PDF points) at top and bottom of sheet where title-block text
# lives. JB labels there are not spatial anchors.
TITLE_BLOCK_MARGIN = 80.0


# --- Helpers -------------------------------------------------------------

def _near_color(rgb, palette, tol=0.15):
    if rgb is None:
        return False
    for p in palette:
        if all(abs(a - b) <= tol for a, b in zip(rgb, p)):
            return True
    return False


def _classify_status(rgb):
    if _near_color(rgb, NEW_COLORS):
        return "NEW"
    if _near_color(rgb, REPLACE_COLORS):
        return "REPLACE"
    # Fuzzy orange/red catch-all
    if rgb is not None:
        r, g, b = rgb
        if r >= 0.8 and b <= 0.3 and g <= 0.6:
            return "NEW"
    return "EXISTING"


def _aerial_ug_from_dash(dashes_list):
    if dashes_list and any(d > 0 for d in dashes_list):
        return "UNDERGROUND"
    return "AERIAL"


def _classify_construction_by_text(coords, labels):
    cx = sum(c[0] for c in coords) / len(coords)
    cy = sum(c[1] for c in coords) / len(coords)
    joined = " ".join(
        txt.upper() for (lx, ly, txt) in labels
        if (lx - cx) ** 2 + (ly - cy) ** 2 <= LABEL_RADIUS ** 2
    )
    for h in UG_HINTS:
        if h in joined:
            return "UNDERGROUND", f"text:{h}"
    for h in AERIAL_HINTS:
        if h in joined:
            return "AERIAL", f"text:{h}"
    return None, None


# --- Chain walker --------------------------------------------------------

def snap_key(p, tol=SNAP_TOL):
    return (round(p[0] / tol) * tol, round(p[1] / tol) * tol)


def walk_chains(segments):
    """Chain compatible-style segments into polylines."""
    by_style = defaultdict(list)
    for seg in segments:
        by_style[seg["key"]].append(seg)

    polylines = []
    for key, segs in by_style.items():
        pt_to_segs = defaultdict(list)
        unused = set(range(len(segs)))
        for i, s in enumerate(segs):
            pt_to_segs[snap_key(s["a"])].append((i, "a"))
            pt_to_segs[snap_key(s["b"])].append((i, "b"))

        while unused:
            start = min(unused)
            unused.discard(start)
            s = segs[start]
            chain = [s["a"], s["b"]]
            data = dict(s["data"])

            while True:
                pk = snap_key(chain[-1])
                nxt = None
                for (i, which) in pt_to_segs[pk]:
                    if i in unused:
                        nxt = (i, which); break
                if not nxt:
                    break
                i, which = nxt
                unused.discard(i)
                sg = segs[i]
                chain.append(sg["b"] if which == "a" else sg["a"])

            while True:
                pk = snap_key(chain[0])
                nxt = None
                for (i, which) in pt_to_segs[pk]:
                    if i in unused:
                        nxt = (i, which); break
                if not nxt:
                    break
                i, which = nxt
                unused.discard(i)
                sg = segs[i]
                chain.insert(0, sg["b"] if which == "a" else sg["a"])

            polylines.append({"coords": chain, "data": data})
    return polylines


def poly_length(coords):
    return sum(
        math.hypot(coords[i + 1][0] - coords[i][0], coords[i + 1][1] - coords[i][1])
        for i in range(len(coords) - 1)
    )


# --- Job assignment ------------------------------------------------------

def nearest_label(cx, cy, points_by_label, max_dist):
    best, best_d2 = None, max_dist * max_dist
    for label, pts in points_by_label.items():
        for (x, y) in pts:
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best = label
    return best


# --- Main extraction -----------------------------------------------------

def extract(pdf_path, page_num=0):
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    page_width, page_height = page.rect.width, page.rect.height

    # --- Collect text labels + job-label centroids ---
    txt = page.get_text("dict")
    labels = []
    jb_points = defaultdict(list)
    incwt_points = defaultdict(list)
    for block in txt["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            full = " ".join(s["text"] for s in line["spans"]).strip()
            if not full:
                continue
            bb = line["bbox"]
            cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
            labels.append((cx, cy, full))

            # JB codes (real job numbers) - skip title-block occurrences.
            for m in JB_RE.finditer(full):
                if cy < TITLE_BLOCK_MARGIN or cy > page_height - TITLE_BLOCK_MARGIN:
                    continue
                jb_points[m.group(1)].append((cx, cy))
            # INCWT codes (sub-areas)
            for m in INCWT_RE.finditer(full):
                if cy < TITLE_BLOCK_MARGIN or cy > page_height - TITLE_BLOCK_MARGIN:
                    continue
                incwt_points[m.group(1)].append((cx, cy))

    # Fallback: if JB spatial centroids were all suppressed (sheet had labels
    # only in the title block), keep the title-block positions so `jobs_jb`
    # still reflects which jobs are on the sheet even though we can't spatially
    # assign to them.
    if not jb_points:
        for block in txt["blocks"]:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                full = " ".join(s["text"] for s in line["spans"]).strip()
                bb = line["bbox"]
                cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
                for m in JB_RE.finditer(full):
                    jb_points[m.group(1)].append((cx, cy))

    # --- Vector drawings ---
    vector_segments = []
    for d in page.get_drawings():
        stroke = d.get("color")
        if stroke is None:
            continue
        dashes = d.get("dashes")
        dashes_list = []
        if isinstance(dashes, str):
            dashes_list = [float(x) for x in re.findall(r"[\d.]+", dashes)]
        status = _classify_status(stroke)
        constr = _aerial_ug_from_dash(dashes_list)
        style_key = (round(stroke[0], 2), round(stroke[1], 2), round(stroke[2], 2),
                     bool(dashes_list), status, constr)

        for item in d.get("items", []):
            kind = item[0]
            if kind == "l":
                p1, p2 = item[1], item[2]
                a = (p1.x, p1.y); b = (p2.x, p2.y)
            elif kind == "c":
                p1, p4 = item[1], item[4]
                a = (p1.x, p1.y); b = (p4.x, p4.y)
            else:
                continue
            if math.hypot(a[0] - b[0], a[1] - b[1]) < 0.5:
                continue
            vector_segments.append({
                "a": a, "b": b, "key": style_key,
                "data": {
                    "status": status,
                    "construction": constr,
                    "stroke_color": [round(stroke[0], 3), round(stroke[1], 3), round(stroke[2], 3)],
                    "source": "vector",
                }
            })
    vector_polylines = walk_chains(vector_segments)

    # --- Annotations ---
    markup_segments = []
    annot_rects = []
    design_notes = []
    try:
        annots = list(page.annots() or [])
    except Exception:
        annots = []

    for a in annots:
        typ = a.type[1] if a.type else "?"
        info = a.info or {}
        content = (info.get("content") or "").strip()
        stroke = a.colors.get("stroke") if hasattr(a, "colors") and a.colors else None

        if typ == "FreeText":
            r = a.rect
            design_notes.append({
                "text": content,
                "pdf_x": (r.x0 + r.x1) / 2,
                "pdf_y": (r.y0 + r.y1) / 2,
                "rect": [r.x0, r.y0, r.x1, r.y1],
                "author": info.get("title", ""),
            })
            continue

        # Any annotation with a poly-path geometry counts as reviewer markup.
        # Covers Line (open poly), PolyLine, Polygon, Ink (freehand).
        if typ in ("Line", "PolyLine", "Polygon", "Ink"):
            verts = getattr(a, "vertices", None) or []
            if len(verts) < 2:
                r = a.rect
                verts = [(r.x0, r.y0), (r.x1, r.y1)]
            pts = []
            for v in verts:
                vx = v[0] if hasattr(v, "__getitem__") else v.x
                vy = v[1] if hasattr(v, "__getitem__") else v.y
                pts.append((vx, vy))
            if poly_length(pts) < MARKUP_MIN_LEN:
                continue
            rgb = tuple(stroke) if stroke else (1.0, 0.0, 0.0)
            source = {"Line": "annot_line", "PolyLine": "annot_polyline",
                      "Polygon": "annot_polygon", "Ink": "annot_ink"}[typ]
            style_key = (round(rgb[0], 2), round(rgb[1], 2), round(rgb[2], 2), source)
            # Emit each adjacent pair so walk_chains can merge collinear markup lines.
            for i in range(len(pts) - 1):
                if math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) < 0.5:
                    continue
                markup_segments.append({
                    "a": pts[i], "b": pts[i + 1], "key": style_key,
                    "data": {
                        "status": "MARKUP",
                        "construction": "UNKNOWN",
                        "stroke_color": [round(rgb[0], 3), round(rgb[1], 3), round(rgb[2], 3)],
                        "source": source,
                        "note": content or "reviewer markup",
                    }
                })
            continue

        if typ == "Circle":
            r = a.rect
            rgb = tuple(stroke) if stroke else (1.0, 0.0, 0.0)
            cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
            rx, ry = (r.x1 - r.x0) / 2, (r.y1 - r.y0) / 2
            ring = [(cx + rx * math.cos(t), cy + ry * math.sin(t))
                    for t in [math.pi * 2 * k / 24 for k in range(25)]]
            annot_rects.append({
                "coords": ring,
                "data": {
                    "status": "MARKUP",
                    "construction": "UNKNOWN",
                    "stroke_color": [round(rgb[0], 3), round(rgb[1], 3), round(rgb[2], 3)],
                    "source": "annot_circle",
                    "note": content or "reviewer circle",
                }
            })
            continue

        if typ == "Square":
            r = a.rect
            rgb = tuple(stroke) if stroke else (1.0, 0.0, 0.0)
            corners = [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1), (r.x0, r.y0)]
            annot_rects.append({
                "coords": corners,
                "data": {
                    "status": "MARKUP",
                    "construction": "UNKNOWN",
                    "stroke_color": [round(rgb[0], 3), round(rgb[1], 3), round(rgb[2], 3)],
                    "source": "annot_square",
                    "note": content or "reviewer box",
                }
            })
            continue

        if typ == "Stamp":
            r = a.rect
            design_notes.append({
                "text": f"[STAMP] {content}",
                "pdf_x": (r.x0 + r.x1) / 2,
                "pdf_y": (r.y0 + r.y1) / 2,
                "rect": [r.x0, r.y0, r.x1, r.y1],
                "author": info.get("title", ""),
            })

    markup_polylines = walk_chains(markup_segments)

    # --- Merge everything into one list, then attach labels + JB/INCWT ---
    all_polylines = []
    for pl in vector_polylines:
        coords = pl["coords"]
        if len(coords) < 2:
            continue
        status = pl["data"]["status"]
        if status == "EXISTING" and poly_length(coords) < 3.0:
            continue
        if status in ("NEW", "REPLACE") and poly_length(coords) < 8.0:
            continue
        all_polylines.append({"coords": [list(c) for c in coords], **pl["data"]})

    for pl in markup_polylines:
        coords = pl["coords"]
        if len(coords) < 2 or poly_length(coords) < MARKUP_MIN_LEN:
            continue
        all_polylines.append({"coords": [list(c) for c in coords], **pl["data"]})

    for r in annot_rects:
        all_polylines.append({"coords": [list(c) for c in r["coords"]], **r["data"]})

    for pl in all_polylines:
        coords = pl["coords"]
        cx = sum(c[0] for c in coords) / len(coords)
        cy = sum(c[1] for c in coords) / len(coords)
        pl["bbox_center"] = [cx, cy]

        counts, footages, near_txt = [], [], []
        for (lx, ly, txt_) in labels:
            if (lx - cx) ** 2 + (ly - cy) ** 2 <= LABEL_RADIUS ** 2:
                near_txt.append(txt_)
                for m in COUNT_RE.finditer(txt_):
                    try:
                        counts.append(int(m.group(1)))
                    except ValueError:
                        pass
                for m in FOOTAGE_RE.finditer(txt_):
                    try:
                        footages.append(float(m.group(1)))
                    except ValueError:
                        pass
        pl["cable_count"] = max(set(counts), key=counts.count) if counts else None
        pl["footage_ft"] = round(sum(footages), 1) if footages else None

        # Assign JB (real job) and INCWT (sub-area)
        pl["job"] = nearest_label(cx, cy, jb_points, JB_MAX_ASSIGN_DIST) or "UNASSIGNED"
        pl["sub_area"] = nearest_label(cx, cy, incwt_points, INCWT_MAX_ASSIGN_DIST)

        if pl.get("construction") in (None, "UNKNOWN") or pl["status"] == "MARKUP":
            kind, reason = _classify_construction_by_text(coords, labels)
            if kind:
                pl["construction"] = kind

    # --- Summary ---
    status_counts = Counter(p["status"] for p in all_polylines)
    job_counts = Counter(p["job"] for p in all_polylines if p["status"] in ("NEW", "REPLACE", "MARKUP"))
    sub_counts = Counter(p.get("sub_area") or "None"
                         for p in all_polylines if p["status"] in ("NEW", "REPLACE", "MARKUP"))
    constr_counts = Counter(p["construction"] for p in all_polylines if p["status"] in ("NEW", "MARKUP"))

    result = {
        "pdf_path": pdf_path,
        "page": page_num,
        "page_width": round(page_width, 2),
        "page_height": round(page_height, 2),
        "polylines": all_polylines,
        "design_notes": design_notes,
        "jobs_jb": sorted(jb_points.keys()),
        "sub_areas_incwt": sorted(incwt_points.keys()),
        "job_label_centroids": {j: [list(pt) for pt in pts] for j, pts in jb_points.items()},
        "summary": {
            "total_polylines": len(all_polylines),
            "by_status": dict(status_counts),
            "by_job": dict(job_counts),
            "by_sub_area": dict(sub_counts),
            "by_construction_new_markup": dict(constr_counts),
            "design_notes": len(design_notes),
        },
    }
    doc.close()
    return result


def main():
    ap = argparse.ArgumentParser(description="Extract JB-grouped polylines from a Sphere PDF")
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--output", default="extracted_routes.json")
    args = ap.parse_args()

    result = extract(args.pdf, args.page)
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    s = result["summary"]
    print(f"[OK] wrote {args.output}")
    print(f"     jobs (JB):      {result['jobs_jb']}")
    print(f"     sub-areas:      {result['sub_areas_incwt']}")
    print(f"     polylines:      {s['total_polylines']}")
    print(f"     by status:      {s['by_status']}")
    print(f"     by job:         {s['by_job']}")
    print(f"     by construction: {s['by_construction_new_markup']}")
    print(f"     design notes:   {s['design_notes']}")


if __name__ == "__main__":
    main()
