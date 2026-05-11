#!/usr/bin/env python3
"""build_synthetic_combined_kmz.py - Generate a minimal combined KMZ for HUD testing.

Produces a tiny KMZ that mimics the structure produced by
build_overlays.py --combined: one Document, one Folder, two
GroundOverlays, two solid-color stand-in PNGs. No PDFs embedded —
build_hud.py's revision detection should fall back to ZipInfo mtime.
"""
from __future__ import annotations

import argparse
import io
import sys
import zipfile
from pathlib import Path

from PIL import Image


# Fixed ZipInfo date so the fixture is byte-identical across runs.
ZIP_DATE = (1980, 1, 1, 0, 0, 0)


DOC_KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>JB_FIXTURE_HUD - Combined Site Plan Overlays</name>
<description><![CDATA[Synthetic fixture for build_hud.py eval]]></description>
<open>1</open>
<Folder>
<name>PRM0099000001 (2 sheets)</name>
<description><![CDATA[]]></description>
<GroundOverlay>
  <name>PRM0099000001 - SITE PLAN - 1 (PDF page 5)</name>
  <Icon>
    <href>images/PRM0099000001__sheet_05.png</href>
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
<GroundOverlay>
  <name>PRM0099000001 - SITE PLAN - 2 (PDF page 6)</name>
  <Icon>
    <href>images/PRM0099000001__sheet_06.png</href>
    <viewBoundScale>0.75</viewBoundScale>
  </Icon>
  <LatLonBox>
    <north>40.80200000</north>
    <south>40.80100000</south>
    <east>-86.02850000</east>
    <west>-86.03000000</west>
    <rotation>0.0000</rotation>
  </LatLonBox>
</GroundOverlay>
</Folder>
</Document>
</kml>
"""


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (100, 100), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def build_kmz(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    entries = [
        ("doc.kml", DOC_KML.encode("utf-8")),
        ("images/PRM0099000001__sheet_05.png", _png_bytes((230, 230, 250))),
        ("images/PRM0099000001__sheet_06.png", _png_bytes((250, 230, 230))),
    ]
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for arc, data in entries:
            info = zipfile.ZipInfo(filename=arc, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_path", type=Path,
                    help="Output KMZ path (e.g. /tmp/eval/fixture_hud.kmz)")
    args = ap.parse_args()
    build_kmz(args.out_path.resolve())
    print(f"Wrote synthetic combined KMZ: {args.out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
