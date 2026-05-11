#!/usr/bin/env python3
"""
extract_pdf.py - Extract route geometry, anchors, and annotations from a multi-page CD PDF.

Usage:
    python extract_pdf.py <pdf_path> --output cd_data.json [--debug]

Outputs a JSON file with one entry per page containing:
    - is_site_plan: bool
    - polylines: list of [(x, y), ...] in rendered PDF coords
    - embedded_latlon: list of (lat, lon) found outside title block
    - addresses: list of {text, x, y} entries
    - match_lines: list of {sheet_ref, x, y, side}
    - poles: list of (x, y) circle-X marker centers
    - annotations: list of {text, x, y, kind} where kind is 'aerial'|'ug'|'other'
    - page_size: (width, height) in PDF points
    - page_rotation: int (0/90/180/270)
"""

import argparse
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

# ---- Tunable constants ----

# Route stroke color: pure red (1.0, 0.0, 0.0) and dark red (0.867, 0.0, 0.0)
ROUTE_COLOR_R_MIN = 0.80
ROUTE_COLOR_GB_MAX = 0.20

# Route stroke width band (in PDF points)
ROUTE_WIDTH_MIN = 0.40
ROUTE_WIDTH_MAX = 1.10

# Tolerance for chaining segment endpoints into polylines (PDF points)
SEGMENT_JOIN_TOLERANCE = 1.5

# Title block exclusion zone: bottom-right corner of page; lat/lon found here is ignored
# Expressed as fraction of page (x_min_frac, y_min_frac) - everything at or above/right is excluded
TITLE_BLOCK_X_FRAC = 0.65
TITLE_BLOCK_Y_FRAC = 0.75

# Pole detection: small closed paths with bounding box diameter in this range
POLE_MIN_DIAM = 4.0
POLE_MAX_DIAM = 20.0

# Annotation classification keywords
AERIAL_KEYWORDS = ['OVERLASH', 'TO EXISTING STRAND', 'LASH', 'AERIAL', 'EXISTING POLE',
                   'PROPOSED AERIAL', 'STRAND']
UG_KEYWORDS = ['BORE', 'HDD', 'TRENCH', 'UNDERGROUND', 'CONDUIT', 'OPEN CUT',
               'DIRECTIONAL BORE', 'PLACE CONDUIT', 'BURIED']

# Regex patterns
LATLON_RE = re.compile(r'(-?\d{1,2}\.\d{4,8})\s*,\s*(-?\d{1,3}\.\d{4,8})')
ADDRESS_RE = re.compile(
    r'\b(\d{1,6})\s+([NSEW]\s+)?([A-Z0-9][A-Z0-9 .]+?)\s*,\s*([A-Z][A-Z ]+?)\s*,\s*([A-Z]{2})\s+(\d{5})',
    re.IGNORECASE
)
MATCH_LINE_RE = re.compile(r'MATCH(?:\s+(?:TO|LINE))?\s*[:\-]?\s*SITE\s*PLAN\s*[-#]?\s*(\d+)',
                           re.IGNORECASE)
SHEET_NUM_RE = re.compile(r'(?:SHEET|SITE\s*PLAN)\s*[-#:]?\s*(\d+)\s*(?:OF\s*\d+)?', re.IGNORECASE)


def is_route_color(color):
    """Return True if a stroke color matches the route red palette."""
    if color is None:
        return False
    if len(color) < 3:
        return False
    r, g, b = color[0], color[1], color[2]
    return r >= ROUTE_COLOR_R_MIN and g <= ROUTE_COLOR_GB_MAX and b <= ROUTE_COLOR_GB_MAX


def is_route_width(width):
    """Return True if stroke width matches the route line weight."""
    if width is None:
        return False
    return ROUTE_WIDTH_MIN <= width <= ROUTE_WIDTH_MAX


def extract_segments(page):
    """Walk page drawings and return a list of red route line segments [(p1, p2), ...]."""
    segments = []
    drawings = page.get_drawings()
    for d in drawings:
        if d.get('type') not in ('s', 'sf', 'fs'):
            continue
        color = d.get('color')
        width = d.get('width')
        if not is_route_color(color) or not is_route_width(width):
            continue
        last_pt = None
        for item in d.get('items', []):
            op = item[0]
            if op == 'l':  # line: ('l', p1, p2)
                p1, p2 = item[1], item[2]
                segments.append(((p1.x, p1.y), (p2.x, p2.y)))
                last_pt = p2
            elif op == 'c':  # bezier: ('c', p1, p2, p3, p4)
                # Approximate by chord between endpoints
                p1, p4 = item[1], item[4]
                segments.append(((p1.x, p1.y), (p4.x, p4.y)))
                last_pt = p4
            elif op == 're':  # rectangle - skip, not a route
                continue
    return segments


def chain_segments(segments, tol=SEGMENT_JOIN_TOLERANCE):
    """Chain connected segments into polylines.

    Builds an endpoint adjacency graph where two segments are joined if an endpoint of one
    is within `tol` of an endpoint of the other. Walks each connected chain to produce
    ordered point lists.
    """
    if not segments:
        return []

    # Dedupe segments
    uniq = []
    seen = set()
    for (a, b) in segments:
        key = (round(a[0], 1), round(a[1], 1), round(b[0], 1), round(b[1], 1))
        rkey = (round(b[0], 1), round(b[1], 1), round(a[0], 1), round(a[1], 1))
        if key in seen or rkey in seen:
            continue
        seen.add(key)
        uniq.append((a, b))
    segments = uniq

    n = len(segments)
    used = [False] * n

    def near(p, q):
        return abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol

    polylines = []
    for i in range(n):
        if used[i]:
            continue
        used[i] = True
        a, b = segments[i]
        chain = [a, b]

        # Extend forward from b
        extended = True
        while extended:
            extended = False
            for j in range(n):
                if used[j]:
                    continue
                c, d = segments[j]
                if near(chain[-1], c):
                    chain.append(d)
                    used[j] = True
                    extended = True
                    break
                if near(chain[-1], d):
                    chain.append(c)
                    used[j] = True
                    extended = True
                    break

        # Extend backward from a
        extended = True
        while extended:
            extended = False
            for j in range(n):
                if used[j]:
                    continue
                c, d = segments[j]
                if near(chain[0], c):
                    chain.insert(0, d)
                    used[j] = True
                    extended = True
                    break
                if near(chain[0], d):
                    chain.insert(0, c)
                    used[j] = True
                    extended = True
                    break

        if len(chain) >= 2:
            polylines.append(chain)

    return polylines


def extract_text_blocks(page):
    """Return a flat list of {text, x, y, w, h} entries for all text on the page."""
    blocks = []
    text_dict = page.get_text("dict")
    for block in text_dict.get('blocks', []):
        if block.get('type') != 0:  # type 0 = text
            continue
        for line in block.get('lines', []):
            line_text = ''
            line_bbox = None
            for span in line.get('spans', []):
                line_text += span.get('text', '')
                bbox = span.get('bbox')
                if bbox:
                    if line_bbox is None:
                        line_bbox = list(bbox)
                    else:
                        line_bbox[0] = min(line_bbox[0], bbox[0])
                        line_bbox[1] = min(line_bbox[1], bbox[1])
                        line_bbox[2] = max(line_bbox[2], bbox[2])
                        line_bbox[3] = max(line_bbox[3], bbox[3])
            if line_text.strip() and line_bbox:
                blocks.append({
                    'text': line_text.strip(),
                    'x': (line_bbox[0] + line_bbox[2]) / 2,
                    'y': (line_bbox[1] + line_bbox[3]) / 2,
                    'w': line_bbox[2] - line_bbox[0],
                    'h': line_bbox[3] - line_bbox[1],
                })
    return blocks


def in_title_block(x, y, page_w, page_h):
    """Return True if (x, y) is inside the bottom-right title block exclusion zone."""
    return x >= page_w * TITLE_BLOCK_X_FRAC and y >= page_h * TITLE_BLOCK_Y_FRAC


def extract_embedded_latlon(text_blocks, page_w, page_h):
    """Find lat/lon stamps that appear outside the title block."""
    found = []
    for blk in text_blocks:
        if in_title_block(blk['x'], blk['y'], page_w, page_h):
            continue
        for m in LATLON_RE.finditer(blk['text']):
            lat = float(m.group(1))
            lon = float(m.group(2))
            # Sanity check: continental US-ish range. Reject false positives like "1.234, 5.678"
            if 24.0 <= lat <= 50.0 and -130.0 <= lon <= -65.0:
                found.append({
                    'lat': lat, 'lon': lon,
                    'x': blk['x'], 'y': blk['y'],
                    'context': blk['text'][:200],
                })
    return found


def extract_addresses(text_blocks):
    """Find street addresses with city/state/zip."""
    found = []
    for blk in text_blocks:
        m = ADDRESS_RE.search(blk['text'])
        if m:
            full = m.group(0)
            found.append({
                'text': full,
                'x': blk['x'], 'y': blk['y'],
            })
    return found


def extract_match_lines(text_blocks, page_w):
    """Find MATCH TO SITE PLAN labels and infer which side of the page they sit on."""
    found = []
    for blk in text_blocks:
        m = MATCH_LINE_RE.search(blk['text'])
        if m:
            sheet_ref = int(m.group(1))
            side = 'left' if blk['x'] < page_w / 2 else 'right'
            found.append({
                'sheet_ref': sheet_ref,
                'x': blk['x'], 'y': blk['y'],
                'side': side,
                'text': blk['text'],
            })
    return found


def detect_poles(page):
    """Detect circle/circle-X pole markers as small closed paths.

    Heuristic: filled or stroked closed paths whose bounding box is roughly square and
    falls within POLE_MIN_DIAM..POLE_MAX_DIAM. This is approximate; a follow-up pass
    that snaps poles to nearest route-vertex would tighten accuracy.
    """
    poles = []
    drawings = page.get_drawings()
    for d in drawings:
        rect = d.get('rect')
        if rect is None:
            continue
        w = rect.width
        h = rect.height
        if w < POLE_MIN_DIAM or h < POLE_MIN_DIAM:
            continue
        if w > POLE_MAX_DIAM or h > POLE_MAX_DIAM:
            continue
        # Roughly square
        if abs(w - h) > max(w, h) * 0.4:
            continue
        cx = (rect.x0 + rect.x1) / 2
        cy = (rect.y0 + rect.y1) / 2
        poles.append({'x': cx, 'y': cy, 'diameter': (w + h) / 2})
    return poles


def classify_annotation(text):
    """Return 'aerial', 'ug', or 'other' based on keyword match."""
    upper = text.upper()
    for kw in AERIAL_KEYWORDS:
        if kw in upper:
            return 'aerial'
    for kw in UG_KEYWORDS:
        if kw in upper:
            return 'ug'
    return 'other'


def extract_annotations(text_blocks):
    """Return all text blocks tagged with construction-method classification."""
    annotations = []
    for blk in text_blocks:
        kind = classify_annotation(blk['text'])
        if kind != 'other':
            annotations.append({
                'text': blk['text'],
                'x': blk['x'], 'y': blk['y'],
                'kind': kind,
            })
    return annotations


def is_site_plan_page(text_blocks, page_idx):
    """Decide if a page is a site plan vs cover/details/traffic/etc."""
    has_match_line = any(MATCH_LINE_RE.search(b['text']) for b in text_blocks)
    has_sheet_label = any(SHEET_NUM_RE.search(b['text']) for b in text_blocks)
    # First few pages are typically cover/notes/legend, not site plans
    if page_idx < 3:
        return has_match_line  # rare but possible
    # Site plans almost always have a match line on at least one side
    if has_match_line:
        return True
    # Fallback: pages that have addresses AND a sheet label
    has_address = any(ADDRESS_RE.search(b['text']) for b in text_blocks)
    return has_address and has_sheet_label


def process_page(page, page_idx, debug=False):
    """Run all extractors on one page, return the per-page dict."""
    page_w = page.rect.width
    page_h = page.rect.height
    rotation = page.rotation

    text_blocks = extract_text_blocks(page)
    is_site = is_site_plan_page(text_blocks, page_idx)

    out = {
        'page_index': page_idx,
        'page_number': page_idx + 1,
        'page_size': [page_w, page_h],
        'page_rotation': rotation,
        'is_site_plan': is_site,
        'polylines': [],
        'embedded_latlon': [],
        'addresses': [],
        'match_lines': [],
        'poles': [],
        'annotations': [],
    }

    # Always extract anchors and annotations even on non-site pages, since the cover
    # sheet often carries the seed lat/lon for the whole job
    out['embedded_latlon'] = extract_embedded_latlon(text_blocks, page_w, page_h)
    out['addresses'] = extract_addresses(text_blocks)

    if not is_site:
        if debug:
            print(f"  page {page_idx + 1}: not a site plan, skipping geometry extraction",
                  file=sys.stderr)
        return out

    segments = extract_segments(page)
    polylines = chain_segments(segments)
    out['polylines'] = polylines
    out['match_lines'] = extract_match_lines(text_blocks, page_w)
    out['poles'] = detect_poles(page)
    out['annotations'] = extract_annotations(text_blocks)

    if debug:
        print(f"  page {page_idx + 1}: {len(segments)} segs -> {len(polylines)} polylines, "
              f"{len(out['poles'])} poles, {len(out['annotations'])} annotations, "
              f"{len(out['match_lines'])} match lines, "
              f"{len(out['addresses'])} addresses, "
              f"{len(out['embedded_latlon'])} latlon",
              file=sys.stderr)

    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('pdf_path', help='Path to multi-page CD PDF')
    ap.add_argument('--output', required=True, help='Output JSON path')
    ap.add_argument('--debug', action='store_true', help='Verbose per-page logging')
    args = ap.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(str(pdf_path))
    print(f"Opened {pdf_path.name}: {len(doc)} pages", file=sys.stderr)

    pages = []
    for i in range(len(doc)):
        page = doc[i]
        pages.append(process_page(page, i, debug=args.debug))

    # PRM/JB inference from path
    parent = pdf_path.parent.name
    grandparent = pdf_path.parent.parent.name if pdf_path.parent.parent.name != '/' else None

    out = {
        'source_pdf': str(pdf_path.name),
        'source_pdf_path': str(pdf_path),
        'inferred_prm': parent,
        'inferred_jb': grandparent,
        'page_count': len(doc),
        'site_plan_count': sum(1 for p in pages if p['is_site_plan']),
        'pages': pages,
    }

    Path(args.output).write_text(json.dumps(out, indent=2))
    print(f"Wrote {args.output}: {out['site_plan_count']} site plans of {out['page_count']} pages",
          file=sys.stderr)
    doc.close()


if __name__ == '__main__':
    main()
