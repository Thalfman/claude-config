#!/usr/bin/env python3
"""enhance_features.py - Highlight fiber, vaults, and anchors inside CD overlay PNGs.

USAGE
    python enhance_features.py /path/to/<JBID>_combined_overlays_hud.kmz \\
        [--out PATH] [--source-folder /path/to/JBID]

WHAT IT DOES
    Post-processes a combined CD ground-overlay KMZ (from build_overlays.py
    --combined, optionally also passed through build_hud.py) so that four
    feature classes pop out of the rasterized SITE PLAN sheets:

      - aerial fiber  -> orange     (#FF6A00)
      - underground   -> electric   (#00A6FF)
      - vaults        -> magenta    (#FF00C8) + white 1px outline ring
      - anchors       -> lime       (#9DFF00) + white 1px outline ring

    Streets, parcels, labels, match lines, and other CD content stay
    untouched. The pipeline is HSV red-mask + connected components +
    PDF-text-driven classification (no OCR). Output is byte-identical
    on rerun: identical inputs produce identical output bytes regardless
    of when the script is run.

PERFORMANCE
    Each 5100x3300 PNG takes 5-10 seconds end-to-end (HSV mask + label +
    classify + recolor + PNG re-encode). A 60-sheet job runs roughly
    8-9 minutes. PyMuPDF text extraction is reused across pages from the
    same PRM via an in-process Document cache.

PALETTE ASSUMPTION
    The HSV constants below assume the drafter uses red (~#FF0000) for
    proposed fiber, vaults, and anchors (the MasTec/Comcast standard).
    For non-red palettes, retune the wedges in the CONSTANTS block; the
    script will print a per-page warning ("no red pixels detected") on
    pages where the assumption breaks.
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from scipy import ndimage


# ============================================================================
# CONSTANTS (tune here)
# ============================================================================
# Default render DPI used as a fallback when auto-detection fails. Auto-detect
# from the PNG dimensions vs page.rect * page.rotation_matrix is the primary
# path; this default only applies when both PDF rect dims are zero (degenerate
# input).
RENDER_DPI_DEFAULT = 300

# HSV red wedges (red wraps hue space). Each tuple is (Hmin, Smin, Vmin) /
# (Hmax, Smax, Vmax). PIL uses 8-bit HSV (0..255) for all channels.
RED_HSV_WEDGE_LO_1 = (0,   120, 80)
RED_HSV_WEDGE_HI_1 = (12,  255, 255)
RED_HSV_WEDGE_LO_2 = (170, 120, 80)
RED_HSV_WEDGE_HI_2 = (180, 255, 255)

# Dilation radii (pixels at the auto-detected DPI). Line dilation must NOT
# exceed half the dash-gap at typical 300 DPI rendering or dashed lines will
# read as solid; 5 px is the validated MasTec/Comcast value.
DILATE_LINE_PX     = 5
DILATE_VAULT_PX    = 3
DILATE_ANCHOR_PX   = 3
OUTLINE_RING_PX    = 2  # second-level dilation difference -> 1-2 px white ring

# Target colors per class (RGB).
COLOR_AERIAL   = (255, 106,   0)
COLOR_UG       = (  0, 166, 255)
COLOR_VAULT    = (255,   0, 200)
COLOR_ANCHOR   = (157, 255,   0)
COLOR_OUTLINE  = (255, 255, 255)

# Component-shape thresholds. Defined at a 300 DPI baseline; rescaled per
# image by dpi_scale = actual_dpi / 300. Areas scale by dpi_scale^2,
# distances and lengths by dpi_scale.
MIN_COMPONENT_AREA_PX_300 = 60
LINE_ASPECT_MIN           = 4.0
LINE_LONG_SIDE_MIN_PX_300 = 120
SYMBOL_AREA_MAX_PX_300    = 6000

VAULT_ASPECT_MIN          = 0.4   # min(w,h) / max(w,h) lower bound
VAULT_FILL_MIN            = 0.4   # area / bbox_area
VAULT_LABEL_RADIUS_PX_300 = 200

ANCHOR_AREA_MIN_PX_300    = 200
ANCHOR_AREA_MAX_PX_300    = 1500
ANCHOR_ASPECT_RANGE       = (0.7, 1.4)
ANCHOR_FILL_RANGE         = (0.55, 0.95)
ANCHOR_LABEL_RADIUS_PX_300 = 250

# Distance to the nearest UG/aerial classification label; default is aerial
# when no labels are within range.
LINE_LABEL_RADIUS_PX_300  = 900

# Toggle: skip components whose centroid falls inside a known red-text bbox.
# Filters out red text glyphs (vault/aerial/ug labels) from being recolored.
TEXT_GLYPH_FILTER         = True

# Label regexes per category. VAULT must be checked before UG because
# "PL. (N) UG VAULT" contains the UG token but the segment is a vault.
UG_LABEL_RE     = re.compile(r"\b(DB|TRENCH|VAC-T|BORE|BORED|CONDUIT|UG|UNDERGROUND|HDD|DRILL)\b")
AERIAL_LABEL_RE = re.compile(r"\b(LASHED|STRAND|AERIAL|OVERLASH|OVL)\b")
VAULT_LABEL_RE  = re.compile(r"\b(VAULT|HANDHOLE)\b")
ANCHOR_LABEL_RE = re.compile(r"\b(ANCHOR|GUY)\b")

# Fixed ZipInfo date for byte-identical idempotent output.
ZIP_DATE = (1980, 1, 1, 0, 0, 0)
# ============================================================================


# Combined-KMZ image entry pattern (PRM*__sheet_NN.png inside images/).
_IMAGE_ENTRY_RE = re.compile(r"^images/(?P<prm>PRM\d+)__sheet_(?P<page>\d+)\.png$")
_PDF_ENTRY_RE = re.compile(r"^pdfs/(?P<prm>PRM\d+)\.pdf$", re.IGNORECASE)


@dataclass
class Label:
    category: str
    text: str
    cx: float
    cy: float
    bbox: tuple[float, float, float, float]


# ----- Mask construction -----
def hsv_red_mask(rgb: np.ndarray) -> np.ndarray:
    hsv = np.asarray(Image.fromarray(rgb, "RGB").convert("HSV"))
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m1 = (h <= RED_HSV_WEDGE_HI_1[0]) & (s >= RED_HSV_WEDGE_LO_1[1]) & (v >= RED_HSV_WEDGE_LO_1[2])
    m2 = (h >= RED_HSV_WEDGE_LO_2[0]) & (s >= RED_HSV_WEDGE_LO_2[1]) & (v >= RED_HSV_WEDGE_LO_2[2])
    return m1 | m2


def disk(radius: int) -> np.ndarray:
    if radius < 1:
        return np.array([[True]])
    yy, xx = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    return (xx * xx + yy * yy) <= radius * radius


# ----- PDF text-layer extraction -----
def extract_labels(page: fitz.Page, dpi: int) -> tuple[list[Label], list[tuple[float,float,float,float]]]:
    """Return (classification_labels, red_text_bboxes_in_image_coords).

    Span bboxes are first multiplied by page.rotation_matrix (so the rect
    matches the rendered orientation) and then scaled by dpi/72 to land in
    PNG pixel coordinates.
    """
    labels: list[Label] = []
    red_text_bboxes: list[tuple[float, float, float, float]] = []
    z = dpi / 72.0
    rotmat = page.rotation_matrix
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                t = (span.get("text") or "").strip()
                if not t:
                    continue
                color = span.get("color", 0)
                r_byte = (color >> 16) & 0xFF
                g_byte = (color >> 8) & 0xFF
                b_byte = color & 0xFF
                is_red = r_byte > 180 and g_byte < 100 and b_byte < 100
                rect = fitz.Rect(span["bbox"]) * rotmat
                bbox = (rect.x0 * z, rect.y0 * z, rect.x1 * z, rect.y1 * z)
                if is_red:
                    red_text_bboxes.append(bbox)
                # VAULT-before-UG is critical: "PL. UG VAULT" hits both tokens.
                if VAULT_LABEL_RE.search(t):
                    cat = "vault"
                elif UG_LABEL_RE.search(t):
                    cat = "ug"
                elif ANCHOR_LABEL_RE.search(t):
                    cat = "anchor_label"
                elif AERIAL_LABEL_RE.search(t):
                    cat = "aerial"
                else:
                    continue
                labels.append(Label(
                    category=cat,
                    text=t,
                    cx=(bbox[0] + bbox[2]) / 2,
                    cy=(bbox[1] + bbox[3]) / 2,
                    bbox=bbox,
                ))
    return labels, red_text_bboxes


def nearest_line_class(cx: float, cy: float, labels: list[Label], radius_px: float) -> str:
    """Classify a line component by the nearest UG/aerial label, defaulting to aerial."""
    best_cat = "aerial"
    best_d2 = radius_px * radius_px
    for lab in labels:
        if lab.category not in ("ug", "aerial"):
            continue
        d2 = (lab.cx - cx) ** 2 + (lab.cy - cy) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best_cat = lab.category
    return best_cat


def in_any_bbox(cx: float, cy: float, bboxes: list[tuple[float, float, float, float]]) -> bool:
    for x0, y0, x1, y1 in bboxes:
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            return True
    return False


# ----- Component classification -----
def classify_components(
    mask: np.ndarray,
    labels: list[Label],
    text_bboxes: list[tuple[float, float, float, float]],
    dpi_scale: float,
) -> tuple[np.ndarray, dict[int, str]]:
    """dpi_scale = actual_dpi / 300; thresholds defined at 300 DPI scale."""
    lbl, n = ndimage.label(mask)
    if n == 0:
        return lbl, {}

    objects = ndimage.find_objects(lbl)
    vault_label_centers = [(L.cx, L.cy) for L in labels if L.category == "vault"]
    classifications: dict[int, str] = {}

    s = dpi_scale
    s2 = s * s
    min_area    = MIN_COMPONENT_AREA_PX_300 * s2
    line_min_px = LINE_LONG_SIDE_MIN_PX_300 * s
    sym_max     = SYMBOL_AREA_MAX_PX_300 * s2
    vault_r     = VAULT_LABEL_RADIUS_PX_300 * s
    anchor_amin = ANCHOR_AREA_MIN_PX_300 * s2
    anchor_amax = ANCHOR_AREA_MAX_PX_300 * s2
    line_r      = LINE_LABEL_RADIUS_PX_300 * s

    for cid in range(1, n + 1):
        sl = objects[cid - 1]
        if sl is None:
            continue
        ys, xs = sl
        comp = lbl[sl] == cid
        area = int(comp.sum())
        if area < min_area:
            classifications[cid] = "skip"
            continue

        h_ = ys.stop - ys.start
        w_ = xs.stop - xs.start
        bbox_area = h_ * w_
        long_side = max(h_, w_)
        short_side = max(min(h_, w_), 1)
        aspect = long_side / short_side
        fill = area / bbox_area if bbox_area else 0.0

        ys_idx, xs_idx = np.where(comp)
        cy = ys.start + ys_idx.mean()
        cx = xs.start + xs_idx.mean()

        if TEXT_GLYPH_FILTER and in_any_bbox(cx, cy, text_bboxes):
            classifications[cid] = "skip"
            continue

        cat = "skip"

        # 1. Vault: blob whose centroid is near a "VAULT" label, with a
        # square-ish + filled + bounded shape.
        for vlx, vly in vault_label_centers:
            if (vlx - cx) ** 2 + (vly - cy) ** 2 <= vault_r * vault_r:
                if (
                    VAULT_ASPECT_MIN <= w_ / max(h_, 1) <= 1 / VAULT_ASPECT_MIN
                    and area <= sym_max
                    and fill >= VAULT_FILL_MIN
                ):
                    cat = "vault"
                    break

        # 2. Fiber line: long thin component; classify by nearest UG/aerial label.
        if cat == "skip" and aspect >= LINE_ASPECT_MIN and long_side >= line_min_px:
            cat = nearest_line_class(cx, cy, labels, line_r)

        # 3. Anchor: small + roughly circular; text-glyph filter above already
        # eliminated red text false-positives.
        if cat == "skip" and anchor_amin <= area <= anchor_amax:
            ar = h_ / max(w_, 1)
            if ANCHOR_ASPECT_RANGE[0] <= ar <= ANCHOR_ASPECT_RANGE[1]:
                if ANCHOR_FILL_RANGE[0] <= fill <= ANCHOR_FILL_RANGE[1]:
                    cat = "anchor"

        classifications[cid] = cat

    return lbl, classifications


def recolor(rgb: np.ndarray, lbl: np.ndarray, classifications: dict[int, str]) -> np.ndarray:
    out = rgb.copy()

    def cat_mask(cat: str) -> np.ndarray:
        ids = [cid for cid, c in classifications.items() if c == cat]
        if not ids:
            return np.zeros(lbl.shape, dtype=bool)
        return np.isin(lbl, ids)

    aerial_m = cat_mask("aerial")
    ug_m     = cat_mask("ug")
    vault_m  = cat_mask("vault")
    anchor_m = cat_mask("anchor")

    if aerial_m.any():
        m = ndimage.binary_dilation(aerial_m, structure=disk(DILATE_LINE_PX))
        out[m] = COLOR_AERIAL
    if ug_m.any():
        m = ndimage.binary_dilation(ug_m, structure=disk(DILATE_LINE_PX))
        out[m] = COLOR_UG

    if vault_m.any():
        core = ndimage.binary_dilation(vault_m, structure=disk(DILATE_VAULT_PX))
        ring = ndimage.binary_dilation(core, structure=disk(OUTLINE_RING_PX)) & ~core
        out[ring] = COLOR_OUTLINE
        out[core] = COLOR_VAULT

    if anchor_m.any():
        core = ndimage.binary_dilation(anchor_m, structure=disk(DILATE_ANCHOR_PX))
        ring = ndimage.binary_dilation(core, structure=disk(OUTLINE_RING_PX)) & ~core
        out[ring] = COLOR_OUTLINE
        out[core] = COLOR_ANCHOR

    return out


# ----- DPI auto-detect -----
def detect_dpi(rgb: np.ndarray, page: fitz.Page) -> int:
    pw, ph = rgb.shape[1], rgb.shape[0]
    rect = page.rect * page.rotation_matrix
    pdf_w, pdf_h = abs(rect.x1 - rect.x0), abs(rect.y1 - rect.y0)
    dpi_x = pw / (pdf_w / 72.0) if pdf_w else RENDER_DPI_DEFAULT
    dpi_y = ph / (pdf_h / 72.0) if pdf_h else RENDER_DPI_DEFAULT
    return int(round((dpi_x + dpi_y) / 2))


# ----- Per-page enhancement -----
def enhance_one(rgb: np.ndarray, page: fitz.Page) -> tuple[np.ndarray, dict[str, int], bool]:
    """Returns (enhanced_rgb, counts, palette_ok).

    palette_ok is False when the red HSV mask captured zero pixels — a strong
    signal that the drafter is using a non-red palette. The caller should
    print a warning and skip enhancement on such pages.
    """
    dpi = detect_dpi(rgb, page)
    mask = hsv_red_mask(rgb)
    if not mask.any():
        return rgb, {"aerial": 0, "ug": 0, "vault": 0, "anchor": 0, "skip": 0}, False
    labels, text_bboxes = extract_labels(page, dpi)
    lbl, classes = classify_components(mask, labels, text_bboxes, dpi / 300.0)
    out = recolor(rgb, lbl, classes)
    counts = {cat: sum(1 for c in classes.values() if c == cat)
              for cat in ("aerial", "ug", "vault", "anchor", "skip")}
    return out, counts, True


# ----- PDF lookup -----
def find_pdf_for_prm(prm_id: str, source_folder: Path,
                     in_kmz_pdf_bytes: dict[str, bytes]) -> tuple[bytes, str] | None:
    """Locate the source PDF for a PRM in priority order.

    Priority:
      1. pdfs/<prm_id>.pdf entry inside the input KMZ
      2. <source_folder>/<prm_id>/<prm_id>.pdf
      3. <source_folder>/<prm_id>/*.pdf (first match)

    Returns (pdf_bytes, descriptive_source_path_str) or None if not found.
    """
    if prm_id in in_kmz_pdf_bytes:
        return in_kmz_pdf_bytes[prm_id], f"kmz:pdfs/{prm_id}.pdf"
    candidate = source_folder / prm_id / f"{prm_id}.pdf"
    if candidate.exists():
        return candidate.read_bytes(), str(candidate)
    candidates = sorted((source_folder / prm_id).glob("*.pdf")) if (source_folder / prm_id).is_dir() else []
    if candidates:
        return candidates[0].read_bytes(), str(candidates[0])
    return None


def png_bytes(rgb: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(buf, "PNG", optimize=True)
    return buf.getvalue()


# ----- Main pipeline -----
def enhance_kmz(kmz_path: Path, out_path: Path, source_folder: Path) -> int:
    if kmz_path.resolve() == out_path.resolve():
        raise SystemExit(f"refusing to overwrite input: --out path matches input KMZ ({kmz_path})")
    if not kmz_path.exists():
        raise SystemExit(f"source KMZ not found: {kmz_path}")

    # Pre-pass: collect any in-KMZ pdfs/ entries so PDF lookup can prefer them.
    in_kmz_pdf_bytes: dict[str, bytes] = {}
    image_entries: list[tuple[str, re.Match]] = []
    with zipfile.ZipFile(kmz_path, "r") as zin:
        for name in zin.namelist():
            pm = _PDF_ENTRY_RE.match(name)
            if pm:
                in_kmz_pdf_bytes[pm.group("prm").upper()] = zin.read(name)
            im = _IMAGE_ENTRY_RE.match(name)
            if im:
                image_entries.append((name, im))

    if not image_entries:
        print(f"WARN: input KMZ has no images/PRM*__sheet_NN.png entries — "
              f"this script targets multi-PRM combined KMZs only. "
              f"No changes will be made.", file=sys.stderr)

    pdf_doc_cache: dict[str, fitz.Document] = {}
    pdf_path_cache: dict[str, str] = {}
    summary: dict[str, dict[str, int]] = {}

    tmp_out = out_path.with_suffix(out_path.suffix + ".tmp")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if tmp_out.exists():
        tmp_out.unlink()

    with zipfile.ZipFile(kmz_path, "r") as zin, zipfile.ZipFile(
        tmp_out, "w", zipfile.ZIP_DEFLATED, allowZip64=True
    ) as zout:
        for name in zin.namelist():
            data = zin.read(name)
            m = _IMAGE_ENTRY_RE.match(name)
            if m:
                prm_id = m.group("prm")
                page_num = int(m.group("page"))
                if prm_id not in pdf_doc_cache:
                    found = find_pdf_for_prm(prm_id, source_folder, in_kmz_pdf_bytes)
                    if found is None:
                        print(f"  WARN: no PDF found for {prm_id}; copying {name} unchanged "
                              f"(checked: kmz pdfs/, {source_folder}/{prm_id}/{prm_id}.pdf, "
                              f"{source_folder}/{prm_id}/*.pdf)", file=sys.stderr)
                        pdf_doc_cache[prm_id] = None
                    else:
                        pdf_bytes, src = found
                        pdf_doc_cache[prm_id] = fitz.open(stream=pdf_bytes, filetype="pdf")
                        pdf_path_cache[prm_id] = src
                doc = pdf_doc_cache[prm_id]
                if doc is not None:
                    if page_num - 1 < len(doc):
                        page = doc[page_num - 1]
                        rgb = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
                        rgb_out, counts, palette_ok = enhance_one(rgb, page)
                        if not palette_ok:
                            print(f"  WARN: {prm_id}/sheet_{page_num:02d}: no red pixels detected; "
                                  f"drafter palette may differ from MasTec/Comcast standard, "
                                  f"skipping enhancement on this page", file=sys.stderr)
                        else:
                            data = png_bytes(rgb_out)
                        s = summary.setdefault(prm_id, {"sheets": 0, "aerial": 0, "ug": 0, "vault": 0, "anchor": 0})
                        s["sheets"] += 1
                        for k in ("aerial", "ug", "vault", "anchor"):
                            s[k] += counts.get(k, 0)
                    else:
                        print(f"  WARN: {pdf_path_cache.get(prm_id, prm_id)} has {len(doc)} pages, "
                              f"sheet_{page_num:02d} out of range; copying unchanged", file=sys.stderr)

            zinfo = zipfile.ZipInfo(filename=name, date_time=ZIP_DATE)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zinfo.external_attr = 0o644 << 16
            zout.writestr(zinfo, data)

    for doc in pdf_doc_cache.values():
        if doc is not None:
            doc.close()

    if out_path.exists():
        out_path.unlink()
    tmp_out.rename(out_path)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"\nWrote {out_path.name} ({size_mb:.1f} MB)")
    if summary:
        print("Per-PRM component classification counts:")
        for prm in sorted(summary):
            s = summary[prm]
            print(f"  {prm}: {s['sheets']:3d} sheets  "
                  f"aerial={s['aerial']:5d}  ug={s['ug']:4d}  "
                  f"vault={s['vault']:3d}  anchor={s['anchor']:4d}")
            if s["aerial"] == 0 and s["ug"] == 0 and s["vault"] == 0 and s["anchor"] == 0:
                print(f"    ^ zero classifications — this PRM's drafter may use different "
                      f"conventions or a non-red palette; retune CONSTANTS or check "
                      f"page text-layer presence.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Highlight CD feature classes inside a combined ground-overlay KMZ.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("kmz_path", type=Path, help="Input combined KMZ (preferably *_hud.kmz)")
    ap.add_argument("--out", type=Path, default=None,
                    help="Output path. Default: <input_stem>_enhanced.kmz next to input.")
    ap.add_argument("--source-folder", type=Path, default=None,
                    help="JB folder containing PRM*/<PRM>.pdf source PDFs. Default: kmz_path.parent.")
    args = ap.parse_args(argv)

    kmz_path: Path = args.kmz_path.resolve()
    if args.out is not None:
        out_path: Path = args.out.resolve()
    else:
        out_path = kmz_path.with_name(kmz_path.stem + "_enhanced.kmz")
    source_folder: Path = (args.source_folder.resolve() if args.source_folder
                           else kmz_path.parent)

    return enhance_kmz(kmz_path, out_path, source_folder)


if __name__ == "__main__":
    raise SystemExit(main())
