#!/usr/bin/env python3
"""
scan_coordinates.py -- Scan a Sphere permit PDF for embedded lat/lon labels.

Outputs control_points.json with the best-spread subset of 5-6 points.
Exit code 0 if >= 4 points found, exit code 1 otherwise (signals Tier 2 needed).

Usage:
    python scan_coordinates.py <pdf_path> [--page 0] [--output control_points.json]
"""
import argparse
import json
import math
import re
import sys

try:
    import fitz
except ImportError:
    print("ERROR: pymupdf not installed. Run: pip install pymupdf", file=sys.stderr)
    sys.exit(2)

import numpy as np

# CONUS decimal-degree ranges
COMBINED_RE = re.compile(
    r"((?:2[4-9]|[34]\d|50)\.\d{4,})\s*,\s*(-(?:6[6-9]|[789]\d|1[01]\d|12[0-5])\.\d{4,})"
)
LAT_RE = re.compile(r"^(2[4-9]|[34]\d|50)\.\d{4,},?$")
LON_RE = re.compile(r"^-(6[6-9]|[789]\d|1[01]\d|12[0-5])\.\d{4,}$")


def extract_coord_pairs(page, max_pair_dist=80):
    """Return list of {pdf_x, pdf_y, lat, lon} from page text."""
    blocks = page.get_text("dict")["blocks"]
    spans = []
    for b in blocks:
        for line in b.get("lines", []):
            for s in line["spans"]:
                x = (s["bbox"][0] + s["bbox"][2]) / 2
                y = (s["bbox"][1] + s["bbox"][3]) / 2
                spans.append((x, y, s["text"].strip()))

    pairs = []
    seen = set()

    # Pass 1: combined format "lat, lon" in one span
    for x, y, t in spans:
        m = COMBINED_RE.search(t)
        if m:
            lat, lon = float(m.group(1)), float(m.group(2))
            key = (round(x, 0), round(y, 0))
            if key not in seen:
                seen.add(key)
                pairs.append({"pdf_x": round(x, 2), "pdf_y": round(y, 2),
                              "lat": lat, "lon": lon})

    # Pass 2: separate lat / lon spans near each other
    lat_spans = []
    lon_spans = []
    for x, y, t in spans:
        clean = t.replace(",", "").strip()
        if LAT_RE.match(clean):
            lat_spans.append((x, y, float(clean)))
        if LON_RE.match(t.strip()):
            lon_spans.append((x, y, float(t.strip())))

    used_lons = set()
    for lx, ly, lat in lat_spans:
        best_i, best_d = None, max_pair_dist
        for i, (nx, ny, lon) in enumerate(lon_spans):
            if i in used_lons:
                continue
            d = math.hypot(lx - nx, ly - ny)
            if d < best_d:
                best_i, best_d = i, d
        if best_i is not None:
            used_lons.add(best_i)
            nx, ny, lon = lon_spans[best_i]
            key = (round((lx + nx) / 2, 0), round((ly + ny) / 2, 0))
            if key not in seen:
                seen.add(key)
                pairs.append({"pdf_x": round((lx + nx) / 2, 2),
                              "pdf_y": round((ly + ny) / 2, 2),
                              "lat": lat, "lon": lon})
    return pairs


def pick_spread(pairs, n=6):
    """Greedy farthest-point sampling to maximize geometric spread."""
    if len(pairs) <= n:
        return pairs
    pts = np.array([[p["pdf_x"], p["pdf_y"]] for p in pairs])
    selected = [0]
    for _ in range(n - 1):
        dists = np.full(len(pts), np.inf)
        for si in selected:
            d = np.linalg.norm(pts - pts[si], axis=1)
            dists = np.minimum(dists, d)
        for si in selected:
            dists[si] = -1
        selected.append(int(np.argmax(dists)))
    return [pairs[i] for i in selected]


def main():
    ap = argparse.ArgumentParser(description="Scan permit PDF for embedded coordinates")
    ap.add_argument("pdf_path")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--output", default="control_points.json")
    args = ap.parse_args()

    doc = fitz.open(args.pdf_path)
    if args.page >= len(doc):
        print(f"ERROR: page {args.page} out of range (PDF has {len(doc)} pages)",
              file=sys.stderr)
        sys.exit(2)
    page = doc[args.page]

    pairs = extract_coord_pairs(page)
    doc.close()

    if len(pairs) < 4:
        print(f"TIER1_FAIL: found only {len(pairs)} coordinate pairs (need >= 4)")
        with open(args.output, "w") as f:
            json.dump({"control_points": [{"name": f"embedded_{i}", **p}
                       for i, p in enumerate(pairs)]}, f, indent=2)
        sys.exit(1)

    best = pick_spread(pairs, n=min(6, len(pairs)))
    cp = {"control_points": [{"name": f"auto_embed_{i+1}", **p}
          for i, p in enumerate(best)]}

    with open(args.output, "w") as f:
        json.dump(cp, f, indent=2)

    print(f"TIER1_OK: {len(pairs)} coordinate pairs found, selected {len(best)} with best spread")
    for p in best:
        print(f"  ({p['pdf_x']:.1f}, {p['pdf_y']:.1f}) -> {p['lat']:.6f}, {p['lon']:.6f}")
    sys.exit(0)


if __name__ == "__main__":
    main()
