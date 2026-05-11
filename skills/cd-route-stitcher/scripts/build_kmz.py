#!/usr/bin/env python3
"""
build_kmz.py - Apply per-page affine transforms and produce a styled KMZ.

Usage:
    python build_kmz.py cd_data.json control_points.json --output route.kmz \
        [--prm-label "PERU UTILITIES"] [--job-label "JB0002131511"]

Output KMZ structure:
    <Document>
      <Folder>By Sheet</Folder>
        <Folder>Sheet 5</Folder>
          <Placemark>aerial route segment</Placemark> (dashed)
          <Placemark>underground route segment</Placemark> (solid)
          <Placemark>pole 1</Placemark>
          ...
        <Folder>Sheet 6</Folder>
        ...
      <Folder>All Routes Combined</Folder>
        <Placemark>full route as one merged polyline</Placemark>
      <Folder>QC: Anchors</Folder>
        <Placemark>page 5 anchor</Placemark>
        ...
"""

import argparse
import json
import math
import sys
from pathlib import Path

import simplekml

# Reuse transform from auto_georef
sys.path.insert(0, str(Path(__file__).parent))
from auto_georef import pdf_to_latlon  # noqa: E402

# Annotation classifier proximity (PDF points) - polylines look up nearest annotation within this
ANNOTATION_LOOKUP_RADIUS = 120.0

# Default classification when no annotation is within range
DEFAULT_CLASSIFICATION = 'aerial'

# Style constants
AERIAL_COLOR = simplekml.Color.red       # aabbggrr - red
AERIAL_WIDTH = 3
UG_COLOR = simplekml.Color.blue
UG_WIDTH = 3
POLE_ICON = 'http://maps.google.com/mapfiles/kml/shapes/donut.png'
ANCHOR_ICON = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'


def midpoint(polyline):
    """Return the geometric midpoint of a polyline in PDF coords."""
    if not polyline:
        return None
    n = len(polyline)
    return (
        sum(p[0] for p in polyline) / n,
        sum(p[1] for p in polyline) / n,
    )


def classify_polyline(polyline, annotations):
    """Classify a polyline as aerial or ug based on the nearest annotation within radius."""
    mp = midpoint(polyline)
    if mp is None or not annotations:
        return DEFAULT_CLASSIFICATION
    best = None
    best_dist = float('inf')
    for ann in annotations:
        d = math.hypot(ann['x'] - mp[0], ann['y'] - mp[1])
        if d < best_dist:
            best_dist = d
            best = ann
    if best is None or best_dist > ANNOTATION_LOOKUP_RADIUS:
        return DEFAULT_CLASSIFICATION
    return best['kind']  # 'aerial' or 'ug'


def style_linestring(ls, kind):
    """Apply aerial-dashed or ug-solid styling to a KML linestring."""
    if kind == 'ug':
        ls.style.linestyle.color = UG_COLOR
        ls.style.linestyle.width = UG_WIDTH
    else:
        ls.style.linestyle.color = AERIAL_COLOR
        ls.style.linestyle.width = AERIAL_WIDTH
        # Dashed via gx:outerColor is not in core KML; we use a dotted icon style fallback.
        # Most clients render width+color reliably; dashing in Google Earth requires
        # a LineStyle gx:outerWidth extension which simplekml doesn't expose cleanly.
        # We document this in SKILL.md and rely on color (red=aerial) for visual distinction.


def transform_polyline(polyline, anchor):
    """Convert a list of PDF (x,y) points to (lon, lat) tuples using the page anchor."""
    out = []
    for x, y in polyline:
        lat, lon = pdf_to_latlon(x, y, anchor)
        out.append((lon, lat))
    return out


def add_polyline_to(folder, polyline, anchor, kind, name, description=''):
    coords = transform_polyline(polyline, anchor)
    if len(coords) < 2:
        return None
    ls = folder.newlinestring(name=name, coords=coords, description=description)
    style_linestring(ls, kind)
    return ls


def add_pole_to(folder, pole_pdf, anchor, label_prefix, idx):
    lat, lon = pdf_to_latlon(pole_pdf['x'], pole_pdf['y'], anchor)
    name = f"{label_prefix} pole {idx}"
    pm = folder.newpoint(name=name, coords=[(lon, lat)])
    pm.style.iconstyle.icon.href = POLE_ICON
    pm.style.iconstyle.scale = 0.7
    pm.style.labelstyle.scale = 0.0  # hide pole text labels by default
    return pm


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('cd_data', help='Path to cd_data.json')
    ap.add_argument('control_points', help='Path to control_points.json')
    ap.add_argument('--output', required=True, help='Output KMZ path')
    ap.add_argument('--prm-label', default=None, help='PRM display name (default: inferred)')
    ap.add_argument('--job-label', default=None, help='JB display name (default: inferred)')
    ap.add_argument('--show-pole-labels', action='store_true',
                    help='Show pole numbers as visible labels (default: hidden)')
    ap.add_argument('--debug', action='store_true')
    args = ap.parse_args()

    cd = json.loads(Path(args.cd_data).read_text())
    cp = json.loads(Path(args.control_points).read_text())

    prm_label = args.prm_label or cd.get('inferred_prm') or 'PRM'
    job_label = args.job_label or cd.get('inferred_jb') or 'JB'

    kml = simplekml.Kml(name=f"{job_label} - {prm_label}")
    doc = kml.document

    by_sheet = doc.newfolder(name='By Sheet')
    combined = doc.newfolder(name='All Routes Combined')
    qc = doc.newfolder(name='QC: Anchors & Notes')

    page_anchors = cp['pages']
    site_pages = [p for p in cd['pages'] if p['is_site_plan']]

    # Track totals for the combined merged route
    total_polylines = 0
    total_poles = 0
    aerial_count = 0
    ug_count = 0
    pages_rendered = 0
    pages_skipped = 0

    # Combined route accumulator: list of (lon, lat) chains, one per polyline across all pages
    combined_chains = []

    for page in site_pages:
        pnum = page['page_number']
        anchor = page_anchors.get(str(pnum))
        if anchor is None:
            print(f"  page {pnum}: skipped (no anchor)", file=sys.stderr)
            pages_skipped += 1
            continue

        sheet_folder = by_sheet.newfolder(name=f"Sheet {pnum}")
        sheet_folder.description = f"Source: page {pnum} of {cd['source_pdf']}\n" \
                                    f"Anchor source: {anchor.get('source')}\n" \
                                    f"Note: {anchor.get('note', '')}"

        # Polylines
        for i, pl in enumerate(page['polylines']):
            kind = classify_polyline(pl, page['annotations'])
            if kind == 'aerial':
                aerial_count += 1
            elif kind == 'ug':
                ug_count += 1
            name = f"{prm_label} Sh{pnum}-{i + 1} ({kind})"
            ls = add_polyline_to(sheet_folder, pl, anchor, kind, name)
            if ls is not None:
                total_polylines += 1
                combined_chains.append((kind, transform_polyline(pl, anchor), name))

        # Poles
        pole_subfolder = sheet_folder.newfolder(name='Poles')
        for i, pole in enumerate(page['poles']):
            pm = add_pole_to(pole_subfolder, pole, anchor, f"Sh{pnum}", i + 1)
            if args.show_pole_labels:
                pm.style.labelstyle.scale = 0.8
            total_poles += 1

        # QC anchor placemark
        qc_pm = qc.newpoint(
            name=f"Sheet {pnum} anchor ({anchor.get('source')})",
            coords=[(anchor['anchor_lon'], anchor['anchor_lat'])],
            description=anchor.get('note', ''),
        )
        qc_pm.style.iconstyle.icon.href = ANCHOR_ICON
        qc_pm.style.iconstyle.scale = 0.8

        pages_rendered += 1
        if args.debug:
            print(f"  page {pnum}: {len(page['polylines'])} polylines, "
                  f"{len(page['poles'])} poles", file=sys.stderr)

    # Combined merged route folder: one placemark per polyline, all PRM-prefixed
    for kind, coords, name in combined_chains:
        if len(coords) < 2:
            continue
        ls = combined.newlinestring(name=name, coords=coords)
        style_linestring(ls, kind)

    summary = (
        f"Job: {job_label}\n"
        f"PRM: {prm_label}\n"
        f"Source PDF: {cd['source_pdf']}\n"
        f"Pages rendered: {pages_rendered} / {len(site_pages)} site plans "
        f"({pages_skipped} skipped)\n"
        f"Polylines: {total_polylines} (aerial {aerial_count}, ug {ug_count}, "
        f"default {total_polylines - aerial_count - ug_count})\n"
        f"Poles: {total_poles}\n"
        f"Quality bar: visualization / corridor planning, NOT engineering layout."
    )
    doc.description = summary
    print(summary, file=sys.stderr)

    # Save as KMZ
    out_path = Path(args.output)
    if out_path.suffix.lower() != '.kmz':
        print(f"WARNING: output path does not end in .kmz; saving as KMZ anyway",
              file=sys.stderr)
    kml.savekmz(str(out_path))
    print(f"Wrote {out_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
