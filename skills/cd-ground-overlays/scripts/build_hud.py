#!/usr/bin/env python3
"""build_hud.py - Brand a combined CD ground-overlay KMZ with a HUD.

USAGE
    python build_hud.py /path/to/<JBID>_combined_overlays.kmz [--out PATH]

WHAT IT DOES
    Reads an existing combined KMZ (from build_overlays.py --combined) and
    writes a new KMZ that adds three <ScreenOverlay> HUD elements directly
    inside <Document>, before the first <Folder>:
      - title card (top-left): JB id, sheet/PRM counts, latest revision date
      - legend (bottom-left): standard MasTec/Comcast CD legend
      - north arrow (bottom-right)

    GroundOverlays are not modified. All non-doc.kml archive members are
    streamed through unchanged. Three new PNGs are added at
    files/hud/{title_card,legend,north_arrow}.png. Output bytes are
    deterministic: identical input + same script produce identical output.

REVISION-DATE PRIORITY
    1. PDF cover-sheet text matched against REV[ISION]?[: -]\\d+/\\d+/\\d{2,4}
    2. Date pattern in reviewer-revision filename (\\d/\\d/20\\d\\d)
    3. Most recent mtime of PRM PDFs
    For a bare KMZ with no JB folder context, falls back directly to (3)
    using mtimes inside the KMZ's own ZipInfo entries.
"""
from __future__ import annotations

import argparse
import io
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

# ----- Constants -----
KML_NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", KML_NS)

# Panel chrome
PANEL_FILL = (20, 20, 20, 200)
PANEL_RADIUS = 8

# Text colors
TEXT_PRIMARY = (255, 255, 255, 255)
TEXT_SECONDARY = (210, 210, 210, 255)
TEXT_MUTED = (170, 170, 170, 255)

# Legend symbol colors
ROUTE_RED = (220, 30, 30, 255)
EXISTING_BLACK = (235, 235, 235, 255)

# Fixed ZipInfo date for byte-identical idempotent output. Identical inputs
# produce identical output bytes regardless of when the script is rerun.
ZIP_DATE = (1980, 1, 1, 0, 0, 0)

# HUD asset filenames inside the KMZ
HUD_PNG_PATHS = (
    "files/hud/title_card.png",
    "files/hud/legend.png",
    "files/hud/north_arrow.png",
)


# ----- Font loading (portable) -----
def _load_font(bold: bool, size: int) -> ImageFont.ImageFont:
    """Best-effort cross-platform font loader.

    Tries common bold/regular fonts on Windows / macOS / Linux in order, then
    falls back to PIL's tiny bitmap default (which renders at fixed size; the
    HUD will look small in that case but the script still produces output).
    """
    if bold:
        candidates = ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf",
                      "LiberationSans-Bold.ttf", "FreeSansBold.ttf"]
    else:
        candidates = ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf",
                      "LiberationSans-Regular.ttf", "FreeSans.ttf"]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# ----- HUD PNG rendering -----
def _draw_panel(size: tuple[int, int]) -> Image.Image:
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (0, 0, size[0] - 1, size[1] - 1),
        radius=PANEL_RADIUS,
        fill=PANEL_FILL,
    )
    return img


def build_title_card(title: str, sheets: int, prms: int, rev: str) -> Image.Image:
    img = _draw_panel((480, 140))
    draw = ImageDraw.Draw(img)
    draw.text((20, 16), title, font=_load_font(True, 36), fill=TEXT_PRIMARY)
    if prms:
        subtitle = f"{sheets} sheets · {prms} PRMs"
    else:
        subtitle = f"{sheets} sheets"
    draw.text((20, 72), subtitle, font=_load_font(False, 16), fill=TEXT_SECONDARY)
    draw.text((20, 100), f"Rev: {rev}", font=_load_font(False, 14), fill=TEXT_MUTED)
    return img


def build_legend() -> Image.Image:
    img = _draw_panel((320, 200))
    draw = ImageDraw.Draw(img)
    draw.text((16, 12), "LEGEND", font=_load_font(True, 14), fill=TEXT_PRIMARY)

    line_font = _load_font(False, 12)
    rows = [
        ("line_solid", ROUTE_RED, "Proposed underground"),
        ("line_dashed", ROUTE_RED, "Proposed aerial"),
        ("line_solid", EXISTING_BLACK, "Existing utility"),
    ]
    y = 38
    for kind, color, label in rows:
        if kind == "line_solid":
            draw.line([(20, y + 6), (60, y + 6)], fill=color, width=3)
        else:
            for x in range(20, 60, 8):
                draw.line([(x, y + 6), (x + 5, y + 6)], fill=color, width=3)
        draw.text((72, y), label, font=line_font, fill=TEXT_SECONDARY)
        y += 22

    y += 4
    sym_rows = [
        ("dot_filled", "Existing pole"),
        ("dot_open", "New pole"),
        ("square", "Pedestal / vault"),
        ("triangle", "Anchor"),
    ]
    for kind, label in sym_rows:
        cx, cy = 40, y + 6
        if kind == "dot_filled":
            draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=TEXT_PRIMARY)
        elif kind == "dot_open":
            draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), outline=TEXT_PRIMARY, width=2)
        elif kind == "square":
            draw.rectangle((cx - 6, cy - 6, cx + 6, cy + 6), fill=TEXT_PRIMARY)
        elif kind == "triangle":
            draw.polygon([(cx, cy - 7), (cx - 7, cy + 6), (cx + 7, cy + 6)], fill=TEXT_PRIMARY)
        draw.text((72, y), label, font=line_font, fill=TEXT_SECONDARY)
        y += 20

    return img


def build_north_arrow() -> Image.Image:
    img = _draw_panel((80, 80))
    draw = ImageDraw.Draw(img)
    cx = 40
    draw.polygon([(cx, 22), (cx - 14, 50), (cx, 42), (cx + 14, 50)], fill=TEXT_PRIMARY)
    n_font = _load_font(True, 16)
    bbox = draw.textbbox((0, 0), "N", font=n_font)
    draw.text((cx - (bbox[2] - bbox[0]) / 2, 56), "N", font=n_font, fill=TEXT_PRIMARY)
    return img


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ----- KML manipulation -----
SCREEN_OVERLAY_BLOCK = """<ScreenOverlay>
  <name>Title</name>
  <Icon><href>files/hud/title_card.png</href></Icon>
  <overlayXY x="0" y="1" xunits="fraction" yunits="fraction"/>
  <screenXY x="0.01" y="0.99" xunits="fraction" yunits="fraction"/>
  <rotationXY x="0" y="0" xunits="fraction" yunits="fraction"/>
  <size x="0" y="0" xunits="pixels" yunits="pixels"/>
</ScreenOverlay>
<ScreenOverlay>
  <name>Legend</name>
  <Icon><href>files/hud/legend.png</href></Icon>
  <overlayXY x="0" y="0" xunits="fraction" yunits="fraction"/>
  <screenXY x="0.01" y="0.01" xunits="fraction" yunits="fraction"/>
  <rotationXY x="0" y="0" xunits="fraction" yunits="fraction"/>
  <size x="0" y="0" xunits="pixels" yunits="pixels"/>
</ScreenOverlay>
<!-- North arrow is only accurate when the Google Earth view is north-up. -->
<ScreenOverlay>
  <name>North</name>
  <Icon><href>files/hud/north_arrow.png</href></Icon>
  <overlayXY x="1" y="0" xunits="fraction" yunits="fraction"/>
  <screenXY x="0.99" y="0.01" xunits="fraction" yunits="fraction"/>
  <rotationXY x="0" y="0" xunits="fraction" yunits="fraction"/>
  <size x="0" y="0" xunits="pixels" yunits="pixels"/>
</ScreenOverlay>
"""


def parse_kml_counts(kml_bytes: bytes) -> tuple[int, int]:
    """Return (ground_overlay_count, folder_count) from doc.kml."""
    root = ET.fromstring(kml_bytes)
    overlays = root.findall(f".//{{{KML_NS}}}GroundOverlay")
    folders = root.findall(f".//{{{KML_NS}}}Folder")
    return len(overlays), len(folders)


def inject_screen_overlays(kml_text: str) -> str:
    """Insert the HUD ScreenOverlay block before the first <Folder>.

    If no <Folder> is present, fall back to inserting before the first
    <GroundOverlay>. If neither is present, raise.
    """
    idx = kml_text.find("<Folder>")
    if idx == -1:
        idx = kml_text.find("<GroundOverlay>")
    if idx == -1:
        raise RuntimeError("doc.kml has neither <Folder> nor <GroundOverlay> — cannot place HUD")
    return kml_text[:idx] + SCREEN_OVERLAY_BLOCK + kml_text[idx:]


# ----- Revision detection -----
_DATE_PATTERNS = [
    re.compile(r"REV(?:ISION)?\s*(?:DATE)?\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-](?:20)?\d{2})", re.I),
    re.compile(r"(?:^|[\s_\-])(\d{1,2})[ _\-/](\d{1,2})[ _\-/](20\d\d)(?:[\s_\-)]|$)"),
]


def _coerce_date(parts: tuple[str, str, str]) -> datetime | None:
    m, d, y = parts
    try:
        year = int(y)
        if year < 100:
            year += 2000
        return datetime(year, int(m), int(d))
    except ValueError:
        return None


def _scan_text_for_dates(text: str) -> list[datetime]:
    found: list[datetime] = []
    for line in text.splitlines():
        m = _DATE_PATTERNS[0].search(line)
        if m:
            raw = m.group(1).replace("-", "/")
            parts = raw.split("/")
            if len(parts) == 3:
                dt = _coerce_date((parts[0], parts[1], parts[2]))
                if dt:
                    found.append(dt)
    return found


def _scan_filename_for_dates(name: str) -> list[datetime]:
    found: list[datetime] = []
    for m in _DATE_PATTERNS[1].finditer(name):
        dt = _coerce_date(m.group(1, 2, 3))
        if dt:
            found.append(dt)
    return found


def _find_revision_from_jb(jb_dir: Path) -> tuple[str, str]:
    import fitz

    candidates: list[datetime] = []
    sources: list[str] = []
    pdf_mtimes: list[tuple[datetime, Path]] = []

    for prm_dir in sorted(jb_dir.glob("PRM*")):
        if not prm_dir.is_dir():
            continue
        for pdf in prm_dir.glob("*.pdf"):
            pdf_mtimes.append((datetime.fromtimestamp(pdf.stat().st_mtime), pdf))
            for dt in _scan_filename_for_dates(pdf.name):
                candidates.append(dt)
                sources.append(f"filename:{pdf.name}")
        cover = prm_dir / f"{prm_dir.name}.pdf"
        if cover.exists():
            try:
                with fitz.open(cover) as doc:
                    text = doc[0].get_text("text") if len(doc) else ""
                    for dt in _scan_text_for_dates(text):
                        candidates.append(dt)
                        sources.append(f"pdf:{cover.name}")
            except Exception:
                pass

    if candidates:
        idx = max(range(len(candidates)), key=lambda i: candidates[i])
        return candidates[idx].strftime("%m/%d/%Y"), sources[idx]
    if pdf_mtimes:
        latest = max(pdf_mtimes, key=lambda t: t[0])
        return latest[0].strftime("%m/%d/%Y"), f"mtime:{latest[1].name}"
    return "unknown", "none"


def _find_revision_from_kmz_only(kmz_path: Path) -> tuple[str, str]:
    """Bare-KMZ fallback: take the most-recent date_time across ZipInfo entries."""
    with zipfile.ZipFile(kmz_path, "r") as zf:
        entries = zf.infolist()
    best = None
    for info in entries:
        try:
            dt = datetime(*info.date_time)
        except ValueError:
            continue
        if best is None or dt > best:
            best = dt
    if best is None:
        return "unknown", "none"
    return best.strftime("%m/%d/%Y"), "based on KMZ entry mtime"


def find_latest_revision(kmz_path: Path) -> tuple[str, str]:
    jb_dir = kmz_path.parent
    has_prm = False
    if jb_dir.exists():
        for p in jb_dir.iterdir():
            if p.is_dir() and re.match(r"(?i)^PRM", p.name):
                has_prm = True
                break
    if has_prm:
        return _find_revision_from_jb(jb_dir)
    return _find_revision_from_kmz_only(kmz_path)


# ----- Title derivation -----
_COMBINED_KMZ_RE = re.compile(r"^(?P<title>.+?)_combined_overlays(?:_hud)?\.kmz$", re.IGNORECASE)


def derive_title(kmz_path: Path) -> str:
    m = _COMBINED_KMZ_RE.match(kmz_path.name)
    if m:
        return m.group("title")
    return kmz_path.stem


# ----- Validation -----
def _validate_output(kmz_path: Path) -> None:
    """Re-open the new KMZ; assert HUD entries present; sanity-check XML."""
    with zipfile.ZipFile(kmz_path, "r") as zf:
        names = set(zf.namelist())
        for required in HUD_PNG_PATHS:
            if required not in names:
                raise RuntimeError(f"validation failed: {required} missing from output KMZ")
        if "doc.kml" not in names:
            raise RuntimeError("validation failed: doc.kml missing from output KMZ")
        kml_bytes = zf.read("doc.kml")

    # XML validation: try xmllint if on PATH, else fall back to ET.fromstring
    xmllint_ok = False
    try:
        proc = subprocess.run(
            ["xmllint", "--noout", "-"],
            input=kml_bytes,
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0:
            xmllint_ok = True
        else:
            print(f"WARN: xmllint reported errors:\n{proc.stderr.decode('utf-8', errors='replace')}",
                  file=sys.stderr)
    except FileNotFoundError:
        pass

    if not xmllint_ok:
        try:
            ET.fromstring(kml_bytes)
        except ET.ParseError as e:
            raise RuntimeError(f"validation failed: doc.kml does not parse as XML: {e}")


# ----- Main -----
def build_hud(kmz_path: Path, out_path: Path, hud_dir: Path) -> None:
    if kmz_path.resolve() == out_path.resolve():
        raise SystemExit(f"refusing to overwrite input: --out path matches input KMZ ({kmz_path})")

    if not kmz_path.exists():
        raise SystemExit(f"source KMZ not found: {kmz_path}")

    hud_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(kmz_path, "r") as zin:
        kml_bytes = zin.read("doc.kml")
        member_names = zin.namelist()

    sheets, folders = parse_kml_counts(kml_bytes)
    rev_date, rev_source = find_latest_revision(kmz_path)
    title = derive_title(kmz_path)
    print(f"title='{title}' sheets={sheets} prms={folders} rev={rev_date} ({rev_source})")

    title_img = build_title_card(title, sheets, folders, rev_date)
    legend_img = build_legend()
    north_img = build_north_arrow()

    title_img.save(hud_dir / "title_card.png", "PNG", optimize=True)
    legend_img.save(hud_dir / "legend.png", "PNG", optimize=True)
    north_img.save(hud_dir / "north_arrow.png", "PNG", optimize=True)
    print(f"wrote 3 HUD pngs to {hud_dir}")

    new_kml = inject_screen_overlays(kml_bytes.decode("utf-8")).encode("utf-8")

    tmp_out = out_path.with_suffix(out_path.suffix + ".tmp")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if tmp_out.exists():
        tmp_out.unlink()
    with zipfile.ZipFile(kmz_path, "r") as zin, zipfile.ZipFile(
        tmp_out, "w", zipfile.ZIP_DEFLATED, allowZip64=True
    ) as zout:
        for name in member_names:
            if name == "doc.kml":
                continue
            data = zin.read(name)
            info = zipfile.ZipInfo(filename=name, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zout.writestr(info, data)
        kml_info = zipfile.ZipInfo(filename="doc.kml", date_time=ZIP_DATE)
        kml_info.compress_type = zipfile.ZIP_DEFLATED
        kml_info.external_attr = 0o644 << 16
        zout.writestr(kml_info, new_kml)
        for arc, png in (
            ("files/hud/title_card.png", _png_bytes(title_img)),
            ("files/hud/legend.png", _png_bytes(legend_img)),
            ("files/hud/north_arrow.png", _png_bytes(north_img)),
        ):
            info = zipfile.ZipInfo(filename=arc, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zout.writestr(info, png)

    if out_path.exists():
        out_path.unlink()
    shutil.move(str(tmp_out), str(out_path))

    _validate_output(out_path)
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"wrote {out_path.name} ({size_mb:.1f} MB), validated")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Brand a combined CD ground-overlay KMZ with title / legend / north-arrow HUD.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("kmz_path", type=Path,
                    help="Input combined KMZ produced by build_overlays.py --combined")
    ap.add_argument("--out", type=Path, default=None,
                    help="Output path. Default: <input_stem>_hud.kmz next to input.")
    args = ap.parse_args(argv)

    kmz_path: Path = args.kmz_path.resolve()
    if args.out is not None:
        out_path: Path = args.out.resolve()
    else:
        out_path = kmz_path.with_name(kmz_path.stem + "_hud.kmz")

    # hud_assets directory written next to where build_hud.py is invoked from
    hud_dir = Path.cwd() / "hud_assets"

    build_hud(kmz_path, out_path, hud_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
