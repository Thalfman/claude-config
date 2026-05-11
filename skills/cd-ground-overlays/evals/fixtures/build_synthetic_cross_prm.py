#!/usr/bin/env python3
"""build_synthetic_cross_prm.py - Generate a minimal 2-PRM JB folder for testing.

Produces:
    <out_dir>/JB_TEST_XPRM/PRM0000000001/test.pdf   (1 site plan page, embedded coord)
    <out_dir>/JB_TEST_XPRM/PRM0000000002/test.pdf   (2 site plan pages, no coord)

The first PRM's site plan carries an embedded "40.801166, -86.030433"
stamp (US-range coord). Subsequent site plans rely on cross-PRM ordinal
chaining to be anchored.

PDF geometry is portrait 792x1224 with rotation 270 (the standard CD
layout: rendered as 1224x792 landscape). Each site plan draws:
    - title text "SITE PLAN - N" inside the title-block region of the
      unrotated page (high x, high y)
    - "MATCH TO SITE PLAN - (N-1)" callout at low y
    - "MATCH TO SITE PLAN - (N+1)" callout at high y (when N has a
      successor)
    - red route line from (396, 0) to (396, 1224) — runs horizontally
      in rendered space, with entry endpoint at rendered LEFT and exit
      endpoint at rendered RIGHT
    - address text "100 N MAIN ST, ANYTOWN IN 46970" to satisfy the
      site-plan classifier
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import fitz


JB_NAME = "JB_TEST_XPRM"
PAGE_W = 792
PAGE_H = 1224
ROUTE_X = 396  # unrotated x of the red route line (vertical line in unrotated coords)


def _draw_non_site_page(doc: fitz.Document, kind: str) -> None:
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.set_rotation(270)
    page.insert_text(fitz.Point(50, 100), f"{kind.upper()} PAGE", fontsize=24)


def _draw_site_plan(
    doc: fitz.Document,
    ordinal: int,
    has_predecessor: bool,
    has_successor: bool,
    embedded_coord: tuple[float, float] | None,
) -> None:
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.set_rotation(270)

    # Title block: "SITE PLAN - N" in the bottom-right of the unrotated page.
    page.insert_text(fitz.Point(700, 1180), f"SITE PLAN - {ordinal}", fontsize=14)

    # Address line so the site-plan classifier picks the page up even if
    # the MATCH callouts are missing.
    page.insert_text(fitz.Point(50, 700), "100 N MAIN ST, ANYTOWN IN 46970", fontsize=10)

    # Embedded lat/lon stamp (only on the seed page).
    if embedded_coord:
        lat, lon = embedded_coord
        page.insert_text(fitz.Point(50, 600), f"{lat:.6f}, {lon:.6f}", fontsize=10)

    # MATCH callouts. Place at low/high y so they're outside the title block.
    if has_predecessor:
        page.insert_text(fitz.Point(50, 50), f"MATCH TO SITE PLAN - {ordinal - 1}", fontsize=8)
    if has_successor:
        page.insert_text(fitz.Point(50, 1200), f"MATCH TO SITE PLAN - {ordinal + 1}", fontsize=8)

    # Red route line from (ROUTE_X, 0) to (ROUTE_X, 1224). Width 0.7 to fall
    # within the route-stroke palette (0.40..1.10). Color (1, 0, 0) gives
    # pure red at the upper bound of the R channel.
    page.draw_line(
        fitz.Point(ROUTE_X, 0),
        fitz.Point(ROUTE_X, PAGE_H),
        color=(1.0, 0.0, 0.0),
        width=0.7,
    )


def build_prm_pdf(
    pdf_path: Path,
    site_plan_specs: list[tuple[int, bool, bool, tuple[float, float] | None]],
) -> None:
    doc = fitz.open()
    # 4 non-site preamble pages so is_site_plan's `page_idx < 3` filter passes.
    for kind in ("cover", "vicinity", "legend", "notes"):
        _draw_non_site_page(doc, kind)
    for ordinal, has_pred, has_succ, embedded in site_plan_specs:
        _draw_site_plan(doc, ordinal, has_pred, has_succ, embedded)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(pdf_path))
    doc.close()


def build_jb(out_dir: Path) -> Path:
    jb_dir = out_dir / JB_NAME
    if jb_dir.exists():
        # Wipe prior fixture so the build is deterministic.
        import shutil
        shutil.rmtree(jb_dir)
    prm1 = jb_dir / "PRM0000000001"
    prm2 = jb_dir / "PRM0000000002"

    # PRM1: ordinal 1, has successor, embedded coord
    build_prm_pdf(prm1 / "test.pdf", [
        (1, False, True, (40.801166, -86.030433)),
    ])

    # PRM2: ordinals 2 and 3, neither carries an embedded coord
    build_prm_pdf(prm2 / "test.pdf", [
        (2, True, True, None),
        (3, True, False, None),
    ])

    return jb_dir


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir", type=Path,
                    help="Parent directory; the JB folder is created inside it")
    args = ap.parse_args()
    jb = build_jb(args.out_dir.resolve())
    print(f"Wrote synthetic JB folder: {jb}")
    print(f"  {jb}/PRM0000000001/test.pdf  (1 site plan, embedded 40.801166,-86.030433)")
    print(f"  {jb}/PRM0000000002/test.pdf  (2 site plans, no embedded coord)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
