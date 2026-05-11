#!/usr/bin/env python3
"""build_synthetic_off_route_anchor.py - Fixture for anchor-binding accuracy.

Generates a single-PDF JB folder where the lat/lon stamp text is intentionally
placed far from the route polyline. With the fix in place (Task 3), the
overlay's bounding box must still cover the route's geographic extent.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import fitz


JB_NAME = "JB_TEST_OFF_ROUTE"
PRM_NAME = "PRM0099000003"
PAGE_W = 792
PAGE_H = 1224

# Lat/lon stamp text placed far from the route but within the extractable
# region (not in the title-block exclusion zone x<=277 AND y>=918, and
# far enough from the right edge that the full "lat, lon" string renders).
# STAMP_X=550, STAMP_Y=1050 is ~150 pt from the route's x=400 line and
# safely fits on a 792-pt-wide page at fontsize 10.
STAMP_X = 550
STAMP_Y = 1050
STAMP_LAT = 40.801166
STAMP_LON = -86.030433

# Route polyline endpoints (entry at small y_unrotated = rendered LEFT,
# exit at large y_unrotated = rendered RIGHT). Route at unrotated x=400.
ROUTE_ENTRY = (400, 50)
ROUTE_EXIT = (400, 1170)


def _draw_non_site_page(doc: fitz.Document, kind: str) -> None:
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.set_rotation(270)
    page.insert_text(fitz.Point(50, 100), f"{kind.upper()} PAGE", fontsize=24)


def _draw_site_plan(doc: fitz.Document) -> None:
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.set_rotation(270)
    page.insert_text(fitz.Point(700, 1180), "SITE PLAN - 1", fontsize=14)
    page.insert_text(fitz.Point(50, 700), "100 N MAIN ST, ANYTOWN IN 46970", fontsize=10)
    # Stamp deliberately far from the route (x=550 vs route x=400)
    page.insert_text(fitz.Point(STAMP_X, STAMP_Y),
                     f"{STAMP_LAT:.6f}, {STAMP_LON:.6f}", fontsize=10)
    # Route polyline
    page.draw_line(
        fitz.Point(*ROUTE_ENTRY), fitz.Point(*ROUTE_EXIT),
        color=(1.0, 0.0, 0.0), width=0.7,
    )


def build_jb(out_dir: Path) -> Path:
    jb = out_dir / JB_NAME
    if jb.exists():
        import shutil
        shutil.rmtree(jb)
    prm = jb / PRM_NAME
    pdf_path = prm / "test.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    for kind in ("cover", "vicinity", "legend", "notes"):
        _draw_non_site_page(doc, kind)
    _draw_site_plan(doc)
    doc.save(str(pdf_path))
    doc.close()
    return jb


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir", type=Path)
    args = ap.parse_args()
    jb = build_jb(args.out_dir.resolve())
    print(f"Wrote synthetic JB folder: {jb}")
    print(f"  stamp text at PDF ({STAMP_X}, {STAMP_Y}) -> "
          f"({STAMP_LAT}, {STAMP_LON})")
    print(f"  route entry at PDF {ROUTE_ENTRY}, exit at PDF {ROUTE_EXIT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
