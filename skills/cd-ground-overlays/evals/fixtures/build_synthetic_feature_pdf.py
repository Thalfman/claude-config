#!/usr/bin/env python3
"""build_synthetic_feature_pdf.py - Generate a synthetic feature PDF + KMZ for enhance_features.py testing.

Produces a single-page PDF with red drawings + red text labels covering
all four feature classes, plus a combined-style KMZ that points at it.
The KMZ structure mimics build_overlays.py --combined output:

    <out_dir>/PRM0099000002/PRM0099000002.pdf
    <out_dir>/JB_FIXTURE_FEATURES_combined_overlays.kmz
        ├── doc.kml
        ├── images/PRM0099000002__sheet_05.png
        └── pdfs/PRM0099000002.pdf

The page contains:
    - Red horizontal aerial line at upper third with "LASHED AERIAL" label
    - Red horizontal UG line at middle with "DB UG TRENCH" label
    - Red filled square (vault) near "VAULT" label
    - Red filled triangle (anchor) near "ANCHOR" label

Lines are drawn long enough to clear LINE_LONG_SIDE_MIN_PX_300 at the
auto-detected DPI; symbols are sized to land in the vault/anchor
threshold ranges.
"""
from __future__ import annotations

import argparse
import io
import sys
import zipfile
from pathlib import Path

import fitz
from PIL import Image


JB_NAME = "JB_FIXTURE_FEATURES"
PRM_NAME = "PRM0099000002"
ZIP_DATE = (1980, 1, 1, 0, 0, 0)

# Page geometry: portrait 792x1224 with rotation 270 (standard CD).
PAGE_W = 792
PAGE_H = 1224
PNG_DPI = 300


def _build_pdf(pdf_path: Path) -> None:
    doc = fitz.open()
    # 4 non-site preamble pages so the site_plan classifier accepts page 5.
    for kind in ("cover", "vicinity", "legend", "notes"):
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        page.set_rotation(270)
        page.insert_text(fitz.Point(50, 100), f"{kind.upper()} PAGE", fontsize=24)

    # Site plan page (page index 4, page number 5).
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.set_rotation(270)

    # Title text + address so site-plan classifier accepts the page.
    page.insert_text(fitz.Point(700, 1180), "SITE PLAN - 1", fontsize=14)
    page.insert_text(fitz.Point(50, 700), "100 N MAIN ST, ANYTOWN IN 46970", fontsize=10)
    page.insert_text(fitz.Point(50, 600), "40.801166, -86.030433", fontsize=10)

    # ----- Aerial line (rendered horizontal, upper third)
    # In unrotated coords: vertical line at x=550 (which is upper-third in
    # rendered space because +x_pdf -> rendered up / NORTH).
    page.draw_line(
        fitz.Point(550, 200), fitz.Point(550, 1024),
        color=(1.0, 0.0, 0.0), width=0.8,
    )
    # "LASHED" label near the aerial line
    page.insert_text(
        fitz.Point(540, 612), "LASHED AERIAL",
        fontsize=10, color=(1.0, 0.0, 0.0),
    )

    # ----- UG line (rendered horizontal, middle)
    page.draw_line(
        fitz.Point(396, 200), fitz.Point(396, 1024),
        color=(1.0, 0.0, 0.0), width=0.8,
    )
    page.insert_text(
        fitz.Point(386, 612), "DB UG TRENCH",
        fontsize=10, color=(1.0, 0.0, 0.0),
    )

    # ----- Vault: small filled red square sized for the classifier.
    # 12pt square -> ~50 px at 300 DPI -> ~2500 px² area, well within
    # MIN_COMPONENT_AREA..SYMBOL_AREA_MAX (60..6000). Aspect 1.0, fill 1.0
    # both pass VAULT_ASPECT_MIN (0.4) and VAULT_FILL_MIN (0.4).
    page.draw_rect(
        fitz.Rect(244, 404, 256, 416),
        color=(1.0, 0.0, 0.0), fill=(1.0, 0.0, 0.0), width=0.5,
    )
    page.insert_text(
        fitz.Point(260, 410), "VAULT",
        fontsize=10, color=(1.0, 0.0, 0.0),
    )

    # ----- Anchor: small filled red circle sized for the classifier.
    # ANCHOR thresholds expect ~200..1500 px², aspect 0.7..1.4, fill
    # 0.55..0.95. A filled circle has fill ≈ 0.785. Radius 5pt -> ~21 px
    # at 300 DPI -> area ≈ 1380 px².
    page.draw_circle(
        fitz.Point(240, 810), 5,
        color=(1.0, 0.0, 0.0), fill=(1.0, 0.0, 0.0), width=0.3,
    )
    page.insert_text(
        fitz.Point(250, 815), "ANCHOR",
        fontsize=10, color=(1.0, 0.0, 0.0),
    )

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(pdf_path))
    doc.close()


def _render_page_png(pdf_path: Path) -> bytes:
    """Render page 5 of the synthetic PDF at PNG_DPI for embedding in the KMZ."""
    doc = fitz.open(str(pdf_path))
    page = doc[4]  # page index 4 = page number 5 (the site plan)
    matrix = fitz.Matrix(PNG_DPI / 72.0, PNG_DPI / 72.0)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True, compress_level=9)
    doc.close()
    return buf.getvalue()


def _build_kmz(kmz_path: Path, pdf_path: Path, png_data: bytes) -> None:
    doc_kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>{JB_NAME} - Combined Site Plan Overlays</name>
<description><![CDATA[Synthetic fixture for enhance_features.py eval]]></description>
<open>1</open>
<Folder>
<name>{PRM_NAME} (1 sheets)</name>
<description><![CDATA[]]></description>
<GroundOverlay>
  <name>{PRM_NAME} - SITE PLAN - 1 (PDF page 5)</name>
  <Icon>
    <href>images/{PRM_NAME}__sheet_05.png</href>
    <viewBoundScale>0.75</viewBoundScale>
  </Icon>
  <LatLonBox>
    <north>40.80200000</north>
    <south>40.80100000</south>
    <east>-86.03000000</east>
    <west>-86.03150000</west>
    <rotation>0.0000</rotation>
  </LatLonBox>
</GroundOverlay>
</Folder>
</Document>
</kml>
"""
    pdf_bytes = pdf_path.read_bytes()
    entries = [
        ("doc.kml", doc_kml.encode("utf-8")),
        (f"images/{PRM_NAME}__sheet_05.png", png_data),
        (f"pdfs/{PRM_NAME}.pdf", pdf_bytes),
    ]
    kmz_path.parent.mkdir(parents=True, exist_ok=True)
    if kmz_path.exists():
        kmz_path.unlink()
    with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for arc, data in entries:
            info = zipfile.ZipInfo(filename=arc, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir", type=Path,
                    help="Parent directory for the synthetic PDF and KMZ")
    args = ap.parse_args()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = out_dir / PRM_NAME / f"{PRM_NAME}.pdf"
    _build_pdf(pdf_path)
    png_data = _render_page_png(pdf_path)
    kmz_path = out_dir / f"{JB_NAME}_combined_overlays.kmz"
    _build_kmz(kmz_path, pdf_path, png_data)

    print(f"Wrote synthetic feature PDF: {pdf_path}")
    print(f"Wrote synthetic combined KMZ: {kmz_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
