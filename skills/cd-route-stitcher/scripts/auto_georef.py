#!/usr/bin/env python3
"""
auto_georef.py - Synthesize per-page affine transforms (PDF coords -> lat/lon).

Usage:
    python auto_georef.py cd_data.json --output control_points.json \
        [--manual-anchors manual_anchors.json] \
        [--scale-feet-per-inch 40] \
        [--no-chain]

Input:
    cd_data.json from extract_pdf.py

Optional manual_anchors.json format:
    {
      "page_5": [
        {"address": "2237 E 250 N, PERU, IN 46970", "lat": 40.801166, "lon": -86.030433,
         "x_pdf": 350.5, "y_pdf": 480.2}
      ],
      "page_7": [...]
    }
    If x_pdf/y_pdf are omitted, the anchor is matched to the nearest extracted address
    on that page by string similarity.

Output:
    control_points.json with one entry per site-plan page describing the affine transform:
    {
      "pages": {
        "5": {
          "anchor_lat": 40.801166, "anchor_lon": -86.030433,
          "anchor_pdf_x": 350.5, "anchor_pdf_y": 480.2,
          "feet_per_pdf_point": 0.5556,
          "rotation_deg": 0,
          "source": "embedded" | "manual" | "chained",
          "note": "..."
        }
      }
    }
"""

import argparse
import json
import math
import sys
from pathlib import Path

# 1 inch on the page = SCALE feet on the ground. Default is the MasTec/Comcast standard.
DEFAULT_SCALE_FEET_PER_INCH = 40.0

# 1 foot of latitude is approximately 1/364320 degree (varies by latitude, but trivially)
FEET_PER_DEG_LAT = 364320.0

# 1 foot of longitude varies with latitude: 1 ft = 1 / (FEET_PER_DEG_LAT * cos(lat)) deg
def feet_per_deg_lon(lat_deg):
    return FEET_PER_DEG_LAT * math.cos(math.radians(lat_deg))


def feet_per_pdf_point(scale_feet_per_inch):
    """A PDF point is 1/72 inch. Return ground feet per PDF point."""
    return scale_feet_per_inch / 72.0


def pdf_to_latlon(x_pdf, y_pdf, anchor):
    """Apply the per-page affine transform to convert PDF coords to lat/lon.

    Assumes north-up: increasing PDF y is southward (PDF origin top-left).
    """
    fpp = anchor['feet_per_pdf_point']
    lat0 = anchor['anchor_lat']
    lon0 = anchor['anchor_lon']
    x0 = anchor['anchor_pdf_x']
    y0 = anchor['anchor_pdf_y']

    dx_feet = (x_pdf - x0) * fpp  # east-positive
    dy_feet = (y0 - y_pdf) * fpp  # north-positive (flip y)

    # Optional rotation correction in degrees (positive = clockwise)
    rot_deg = anchor.get('rotation_deg', 0)
    if rot_deg:
        rad = math.radians(rot_deg)
        rx = dx_feet * math.cos(rad) + dy_feet * math.sin(rad)
        ry = -dx_feet * math.sin(rad) + dy_feet * math.cos(rad)
        dx_feet, dy_feet = rx, ry

    dlat = dy_feet / FEET_PER_DEG_LAT
    dlon = dx_feet / feet_per_deg_lon(lat0)
    return lat0 + dlat, lon0 + dlon


def latlon_to_pdf(lat, lon, anchor):
    """Inverse of pdf_to_latlon. Used for chaining anchors across match lines."""
    fpp = anchor['feet_per_pdf_point']
    lat0 = anchor['anchor_lat']
    lon0 = anchor['anchor_lon']
    x0 = anchor['anchor_pdf_x']
    y0 = anchor['anchor_pdf_y']

    dlat = lat - lat0
    dlon = lon - lon0
    dy_feet = dlat * FEET_PER_DEG_LAT
    dx_feet = dlon * feet_per_deg_lon(lat0)

    rot_deg = anchor.get('rotation_deg', 0)
    if rot_deg:
        rad = math.radians(-rot_deg)
        rx = dx_feet * math.cos(rad) + dy_feet * math.sin(rad)
        ry = -dx_feet * math.sin(rad) + dy_feet * math.cos(rad)
        dx_feet, dy_feet = rx, ry

    x_pdf = x0 + dx_feet / fpp
    y_pdf = y0 - dy_feet / fpp
    return x_pdf, y_pdf


def find_address_pdf_pos(page, address_substring):
    """Locate the (x, y) position of an address on a page by substring match."""
    addr_low = address_substring.lower().strip()
    for a in page['addresses']:
        if addr_low in a['text'].lower() or a['text'].lower() in addr_low:
            return a['x'], a['y']
    return None, None


def get_polyline_endpoints(page):
    """Return all polyline endpoints on the page as a flat list."""
    pts = []
    for pl in page['polylines']:
        if len(pl) >= 2:
            pts.append(tuple(pl[0]))
            pts.append(tuple(pl[-1]))
    return pts


def find_route_exit_point(page, side='right'):
    """Find the polyline endpoint nearest to the given page edge.

    Used for match-line chaining: the route exit on page N is the route entry on page N+1.
    """
    if not page['polylines']:
        return None
    page_w, page_h = page['page_size']
    candidates = []
    for pl in page['polylines']:
        if len(pl) < 2:
            continue
        for endpoint in (pl[0], pl[-1]):
            x, y = endpoint
            if side == 'right':
                dist_to_edge = page_w - x
            elif side == 'left':
                dist_to_edge = x
            elif side == 'top':
                dist_to_edge = y
            elif side == 'bottom':
                dist_to_edge = page_h - y
            else:
                dist_to_edge = float('inf')
            candidates.append((dist_to_edge, endpoint))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0])
    return candidates[0][1]


def find_route_entry_point(page, side='left'):
    """Mirror of find_route_exit_point."""
    return find_route_exit_point(page, side=side)


def build_anchor_for_page(page, manual_anchors_for_page, fpp, prev_anchor=None,
                          allow_chain=True, debug=False):
    """Build the affine transform anchor for a single page.

    Priority order:
        1. Manual anchor with explicit pdf coords
        2. Manual anchor matched to an address on the page
        3. Embedded lat/lon stamp on the page
        4. Chained from the previous page's route exit (if allow_chain and prev_anchor)
        5. None
    """
    page_num = page['page_number']

    # 1+2: Manual anchor
    if manual_anchors_for_page:
        for ma in manual_anchors_for_page:
            if 'x_pdf' in ma and 'y_pdf' in ma:
                return {
                    'anchor_lat': ma['lat'],
                    'anchor_lon': ma['lon'],
                    'anchor_pdf_x': ma['x_pdf'],
                    'anchor_pdf_y': ma['y_pdf'],
                    'feet_per_pdf_point': fpp,
                    'rotation_deg': ma.get('rotation_deg', 0),
                    'source': 'manual_explicit',
                    'note': f"Manual anchor: {ma.get('address', 'no address provided')}",
                }
            if 'address' in ma:
                x, y = find_address_pdf_pos(page, ma['address'])
                if x is not None:
                    return {
                        'anchor_lat': ma['lat'],
                        'anchor_lon': ma['lon'],
                        'anchor_pdf_x': x,
                        'anchor_pdf_y': y,
                        'feet_per_pdf_point': fpp,
                        'rotation_deg': ma.get('rotation_deg', 0),
                        'source': 'manual_address',
                        'note': f"Manual anchor matched to address: {ma['address']}",
                    }

    # 3: Embedded lat/lon
    if page['embedded_latlon']:
        ell = page['embedded_latlon'][0]
        return {
            'anchor_lat': ell['lat'],
            'anchor_lon': ell['lon'],
            'anchor_pdf_x': ell['x'],
            'anchor_pdf_y': ell['y'],
            'feet_per_pdf_point': fpp,
            'rotation_deg': 0,
            'source': 'embedded',
            'note': f"Embedded lat/lon stamp at ({ell['x']:.1f}, {ell['y']:.1f})",
        }

    # 4: Chain from previous
    if allow_chain and prev_anchor is not None:
        # Compute previous page's route exit in lat/lon, then use as this page's
        # entry anchor mapped to this page's left-edge route entry pdf point
        prev_exit_pdf = prev_anchor.get('_route_exit_pdf')
        if prev_exit_pdf is not None:
            exit_lat, exit_lon = pdf_to_latlon(prev_exit_pdf[0], prev_exit_pdf[1], prev_anchor)
            entry_pdf = find_route_entry_point(page, side='left')
            if entry_pdf is None:
                # Try other sides as fallback
                for side in ('right', 'top', 'bottom'):
                    entry_pdf = find_route_entry_point(page, side=side)
                    if entry_pdf:
                        break
            if entry_pdf is not None:
                return {
                    'anchor_lat': exit_lat,
                    'anchor_lon': exit_lon,
                    'anchor_pdf_x': entry_pdf[0],
                    'anchor_pdf_y': entry_pdf[1],
                    'feet_per_pdf_point': fpp,
                    'rotation_deg': prev_anchor.get('rotation_deg', 0),
                    'source': 'chained',
                    'note': f"Chained from page {prev_anchor.get('_page_number', '?')} "
                            f"route exit at ({prev_exit_pdf[0]:.1f}, {prev_exit_pdf[1]:.1f})",
                }

    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('cd_data', help='Path to cd_data.json from extract_pdf.py')
    ap.add_argument('--output', required=True, help='Output control_points.json path')
    ap.add_argument('--manual-anchors', default=None,
                    help='Optional manual_anchors.json path')
    ap.add_argument('--scale-feet-per-inch', type=float,
                    default=DEFAULT_SCALE_FEET_PER_INCH,
                    help=f'Drawing scale (default {DEFAULT_SCALE_FEET_PER_INCH} ft/in)')
    ap.add_argument('--no-chain', action='store_true',
                    help='Disable chained anchors; pages without their own anchor are dropped')
    ap.add_argument('--debug', action='store_true')
    args = ap.parse_args()

    cd = json.loads(Path(args.cd_data).read_text())

    manual = {}
    if args.manual_anchors:
        manual = json.loads(Path(args.manual_anchors).read_text())

    fpp = feet_per_pdf_point(args.scale_feet_per_inch)
    print(f"Scale: 1 in = {args.scale_feet_per_inch} ft, "
          f"1 PDF point = {fpp:.4f} ft on ground", file=sys.stderr)

    site_pages = [p for p in cd['pages'] if p['is_site_plan']]
    print(f"Processing {len(site_pages)} site-plan pages", file=sys.stderr)

    anchors = {}
    prev_anchor = None
    for page in site_pages:
        pnum = page['page_number']
        manual_for_page = manual.get(f"page_{pnum}") or manual.get(str(pnum)) or []
        anchor = build_anchor_for_page(
            page, manual_for_page, fpp,
            prev_anchor=prev_anchor,
            allow_chain=not args.no_chain,
            debug=args.debug,
        )
        if anchor is None:
            print(f"  page {pnum}: NO ANCHOR (will be omitted from KMZ)", file=sys.stderr)
            continue

        # Compute and stash the route exit point for chaining the next page
        exit_pt = find_route_exit_point(page, side='right')
        if exit_pt:
            anchor['_route_exit_pdf'] = list(exit_pt)
        anchor['_page_number'] = pnum

        anchors[str(pnum)] = anchor
        prev_anchor = anchor

        print(f"  page {pnum}: anchor source={anchor['source']} "
              f"at ({anchor['anchor_pdf_x']:.1f}, {anchor['anchor_pdf_y']:.1f}) -> "
              f"({anchor['anchor_lat']:.6f}, {anchor['anchor_lon']:.6f})",
              file=sys.stderr)

    out = {
        'scale_feet_per_inch': args.scale_feet_per_inch,
        'feet_per_pdf_point': fpp,
        'pages': anchors,
    }
    Path(args.output).write_text(json.dumps(out, indent=2))
    print(f"Wrote {args.output} with {len(anchors)} anchored pages", file=sys.stderr)


if __name__ == '__main__':
    main()
