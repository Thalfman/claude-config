---
name: cd-ground-overlays
description: "Convert multi-page Sphere/Comcast/MasTec construction-drawing (CD) PDFs into a KMZ of named GroundOverlay tiles for Google Earth Pro. One overlay per SITE PLAN sheet, positioned at the correct lat/lon bounding box. Use whenever a user wants to turn CD pages into Google Earth raster overlays, georeference site plan sheets as PNG tiles, render each construction drawing page onto satellite imagery, or stitch a multi-PRM job folder into a combined ground-overlay KMZ. Triggers on 'convert these CDs to ground overlays', 'render each site plan as a KMZ', 'georeference each page of this construction PDF', 'turn the site plans into Google Earth overlays', or any request mentioning a CD/permit PDF and ground overlays / raster tiles. Handles single PDFs and JB[id]/PRM[id]/drawing.pdf folder structures. RASTER overlays of rendered pages; for VECTOR route lines use cd-route-stitcher; for one-page Sphere overview maps use pdf-to-kmz."
---

# CD Ground Overlays

## What this skill does

Takes a multi-page Sphere/Comcast/MasTec construction-drawing PDF (typically 18 to 60 pages: cover, vicinity, notes, legend, multiple SITE PLAN tile pages, typical details, traffic control plans) and produces a KMZ where each site plan sheet is a separate, named GroundOverlay positioned at the correct geographic bounding box on satellite imagery in Google Earth Pro.

Output KMZ contains:
- One `<GroundOverlay>` per qualifying site plan sheet, named "SITE PLAN - N (PDF page M)"
- High-resolution PNG of each page (default 600 DPI, ~10200x6600 pixels for 17"x11" landscape pages, sharpened with UnsharpMask + a 1.10x contrast boost; saved as lossless PNG with `optimize=True, compress_level=9`)
- `LatLonBox` with `north`/`south`/`east`/`west` and `rotation` (zero when the rendered image is north-up)
- Per-overlay description recording the anchor source, confidence (HIGH / MEDIUM / LOW), and any manual-adjustment notes

For multi-PRM job folders (`JB[id]/PRM[id]/drawing.pdf`), the skill processes each PRM independently and also emits a combined JB-level KMZ.

## When to use

Use whenever the user wants any of:
- A Google Earth file showing the construction drawing pages laid over satellite imagery
- One ground overlay per site plan sheet (raster, not vector)
- A KMZ that lets reviewers toggle individual sheets on/off
- Batch processing of every PRM PDF in a JB folder

Identifying signals in the source:
- Multi-page PDF with sheet titles like `SITE PLAN - 1`, `SITE PLAN - 2`
- `MATCH TO SITE PLAN - N` callouts on left/right page edges
- Red dashed/solid route over an aerial photograph
- One page typically embeds an explicit lat/lon next to the start address (e.g., `2237 E 250 N, PERU IN 46970   40.801166, -86.030433`); when present, this is the gold anchor

If the user wants the ROUTE drawn as polylines (vector) instead of the rendered pages as raster tiles, use `cd-route-stitcher` instead. The two skills are complementary; nothing prevents running both on the same PDF.

## Prerequisites

```bash
pip install pymupdf pillow numpy scipy --break-system-packages
```

`pymupdf` and `pillow` cover the core overlay pipeline (`build_overlays.py`).
`numpy` and `scipy` are required for the optional `enhance_features.py`
post-processor; install them up-front so the full pipeline runs without
re-prompting.

No external geocoder is required. The skill anchors from embedded lat/lon stamps when available and chains route-endpoint match-line continuity for the remaining sheets.

## Workflow

The pipeline is one script. Pass a PDF or a JB folder path.

### Single-PDF mode

```bash
python scripts/build_overlays.py /path/to/drawing.pdf --output /path/to/output.kmz
```

The script:
1. Walks every page, classifies it as site plan or non-site (cover, vicinity, notes, legend, typical details, traffic control)
2. Renders each site plan page at 600 DPI with PDF rotation applied (so north points up in the image when the drawing is north-up, which is the common case), then runs an UnsharpMask + contrast-boost pass to keep street labels legible for downstream LLM-vision triangulation
3. Extracts the embedded `lat, lon` stamp on whichever page carries it (typically Sheet 1)
4. Extracts route polyline endpoints and `MATCH TO SITE PLAN - N` labels for chaining
5. Builds a per-page affine transform from PDF unrotated coords to (lat, lon)
6. Computes the four-corner lat/lon bounding box of each rendered PNG
7. Emits a KMZ with one named GroundOverlay per sheet

### Multi-PRM mode

When run against a folder, the skill auto-detects the `JB[id]/PRM[id]/*.pdf` layout:

```bash
python scripts/build_overlays.py /path/to/JB123 --multi-prm --combined
```

Per-PRM KMZs are written into each PRM folder, and a `JB[id]_combined_overlays.kmz` is written to the JB folder containing every overlay across every PRM.

### Anchor precedence ladder

For each site plan page the script walks this ladder; first hit wins:

1. Manual single anchor (`page_N: {x_pdf, y_pdf, lat, lon}`) — HIGH confidence
2. Manual two-corner anchor (`page_N: {two_corner: [..., ...]}`) — HIGH confidence, supports rotation
3. Embedded lat/lon stamp on the page bound to the nearest route polyline endpoint — HIGH confidence (the default since 2026-04)
4. Embedded lat/lon stamp at the text bbox centroid — MEDIUM confidence (fallback when no route polyline is detected; opt-in with `--legacy-text-anchor` to force)
5. Forward chain from the prior anchored page's route exit endpoint — MEDIUM, errors compound
6. Backward chain from the next anchored page's route entry endpoint — MEDIUM
7. Cover-page lat/lon (harvested from non-site pages) bound to this page's route entry endpoint — MEDIUM
8. Cover-page lat/lon at this page's center — LOW (no route polyline detected)
9. None — overlay placed at a fallback position; manual placement required in Google Earth Pro

Use `--debug-coords` to print, per page, which rung won and which (x_pdf, y_pdf, lat, lon) it used.

### Manual anchors (optional, sub-2m accuracy)

Manual anchors override every other anchor source. Two schemas are accepted in `manual_anchors.json`:

**Single-anchor schema** (1-point translation; rotation defaults to 0 unless `rotation_deg` is supplied):

```json
{
  "page_5": {"x_pdf": 81.3, "y_pdf": 200.3, "lat": 40.801166, "lon": -86.030433}
}
```

**Two-corner schema** (2-point translation + rotation; easiest to fill in by hand from Google Earth + the rendered PNG):

```json
{
  "page_5": {
    "two_corner": [
      {"x_pdf": 100, "y_pdf": 200, "lat": 40.801166, "lon": -86.030433},
      {"x_pdf": 700, "y_pdf": 1100, "lat": 40.802500, "lon": -86.025000}
    ]
  }
}
```

For multi-PRM jobs the schema may be flat (`{"page_5": ...}`) or nested per-PRM (`{"PRM0001388160": {"page_5": ...}}`); the script auto-detects nested mode when any top-level key starts with `PRM`.

Pass `--manual-anchors anchors.json` on the command line. Manual anchors win over every other anchor source on the matched page.

### Optional post-processing

After the combined KMZ is produced, two optional scripts add presentation polish without modifying the GroundOverlays:

- `scripts/build_hud.py` adds three ScreenOverlay HUD elements (title card, legend, north arrow) so the KMZ feels like a finished deliverable.
- `scripts/enhance_features.py` post-processes the embedded SITE PLAN PNGs to make four feature classes (aerial fiber, underground fiber, vaults, anchors) far more visible against satellite imagery via HSV masking plus PDF-text-driven classification. Streets, labels, and other CD content stay untouched.

Both scripts are idempotent. Both default to writing alongside the input KMZ without overwriting it.

Typical chained usage:

```bash
python scripts/build_overlays.py /path/to/JBID --multi-prm --combined
python scripts/build_hud.py /path/to/JBID/JBID_combined_overlays.kmz
python scripts/enhance_features.py /path/to/JBID/JBID_combined_overlays_hud.kmz
```

Final output: `JBID_combined_overlays_hud_enhanced.kmz`.

## Render quality and DPI

The default render is 600 DPI with an UnsharpMask + 1.10x contrast pass on every site plan. **600 DPI is the recommended floor for downstream LLM-vision triangulation**: at 300 DPI, street labels and small callouts dissolve into 2-to-3-pixel-tall blurs that even strong vision models cannot read; at 600 DPI those same labels render at 4-to-6 pixels of stroke width with crisp edges, which is enough for a vision pass to pick out cross-streets and triangulate location. For the most demanding cases — rural jobs with narrow road labels, dense urban grids with overlapping callouts, anything that has to feed an unattended vision pipeline — bump to `--dpi 800`.

Size/quality tradeoff: a 17"x11" landscape sheet at 600 DPI is roughly 10200x6600 px and runs about 4-6 MB per PNG (lossless, `optimize=True`, `compress_level=9`). At 300 DPI the same sheet is ~2 MB. A 7-sheet job KMZ (with embedded source PDF) lands around 35-40 MB at 600 DPI vs ~22 MB at 300 DPI; denser routes with more aerial detail trend higher. The script does **not** transcode to JPEG: line work compresses badly and any JPEG artifact directly attacks readability of the labels we're trying to preserve.

Sharpening knobs are tunable per-run:

```bash
# Default (recommended): 600 DPI + sharpening
python scripts/build_overlays.py drawing.pdf --output out.kmz

# Higher DPI for the hardest jobs
python scripts/build_overlays.py drawing.pdf --dpi 800 --output out.kmz

# Skip sharpening (rare; only when sharpening over-emphasizes paper texture)
python scripts/build_overlays.py drawing.pdf --no-sharpen --output out.kmz

# Custom UnsharpMask
python scripts/build_overlays.py drawing.pdf \
    --unsharp-radius 1.5 --unsharp-percent 200 --unsharp-threshold 3 \
    --contrast-boost 1.15 \
    --output out.kmz
```

The module also exposes a `SUPERSAMPLE_FACTOR` constant (default `1`, off). When set to 2 the script renders at `dpi * 2` and Lanczos-downsamples to `dpi`, which softens aliasing on diagonals at the cost of ~4x render time and memory. Leave at 1 unless you have a specific aliasing complaint; the UnsharpMask pass already covers most of the gap.

Backwards compatibility: existing JB folders that were built at 300 DPI keep working — the change only affects new builds. The KMZ format and overlay metadata are unchanged; only the rendered PNGs are denser.

## Coordinate conventions (why the rotation math matters)

These CD PDFs are stored as portrait `792 x 1224` pages with a `270` rotation flag (i.e., displayed landscape). When the drawing's north arrow points UP in the rendered (landscape) view:

| Geographic axis | Rendered direction | Direction in unrotated PDF coords |
|---|---|---|
| North | up | +x_pdf |
| East  | right | +y_pdf |
| South | down  | -x_pdf |
| West  | left  | -y_pdf |

So the per-page transform is:

```
north_offset_feet = (x_pdf - x_anchor) * (scale_ft_per_inch / 72)
east_offset_feet  = (y_pdf - y_anchor) * (scale_ft_per_inch / 72)
```

This is the opposite of the convention used by `cd-route-stitcher`'s `auto_georef.py`, which assumes north-up in unrotated PDF coords. Don't borrow that module's transform; use this skill's bundled `build_overlays.py` instead. If you see all the overlays clustered into a tiny patch instead of stretching along the road, the rotation handling is wrong.

For pages drawn with a different north orientation, override per-page with a `rotation_deg` in the manual anchors JSON and the script will rotate the GroundOverlay's `LatLonBox` accordingly.

## Tile chaining (when only one page has an embedded coord)

Site plans tile west-to-east along the route. Each page's right-edge route exit is geographically the same point as the next page's left-edge route entry. The script:

1. Finds the polyline endpoint with maximum `y_pdf` on page N (rendered-RIGHT edge route exit)
2. Finds the polyline endpoint with minimum `y_pdf` on page N+1 (rendered-LEFT edge route entry)
3. Sets the page N+1 anchor lat/lon to the geographic location of page N's exit endpoint
4. Marks page N+1 confidence as MEDIUM (errors compound through long chains)

If the chain produces visible drift on satellite imagery, supply a manual anchor for any drifted page and the chain re-locks from that anchor onward.

## Cross-PRM ordinal chaining (multi-PRM mode only)

In a multi-PRM JB folder, a long fiber route is split across multiple PRMs by jurisdiction or pole-owner. Each PRM contains a contiguous slice of the same continuous route, so SITE PLAN ordinals are global to the route, not local to the PRM. The first sheet of the second PRM might be `SITE PLAN - 7`, not `SITE PLAN - 1`.

When run with `--multi-prm`, the script flattens every site plan across every PRM into a single sequence keyed by the parsed `SITE PLAN - N` title-block ordinal, then runs the same forward + backward chain math used within a PRM, but across PRM boundaries. A PRM with no embedded lat/lon now anchors off the prior PRM's exit endpoint instead of falling back to whatever local seed it could find.

### Parsed signals
- `SITE PLAN - N` in the title block of each site plan page (the page's own ordinal).
- `MATCH TO SITE PLAN - (N-1)` and `MATCH TO SITE PLAN - (N+1)` callouts at the left/right route entry/exit edges (used to recognize neighboring sheets, not for the page's own ordinal).

### Failure mode this fixes
Before this change: the first sheet of the second PRM would be re-anchored from whatever local seed was available (cover-page coord, page-1 fallback), and that PRM would land *on top of* the first PRM in Google Earth Pro instead of continuing the route east-to-west. The visible signature is two PRMs stacked at the same neighborhood instead of stretched along the road.

### Edge-case rules
- **Overlap** (two PRMs share an ordinal): Both overlays are kept. Tie-break is the PRM iteration order returned by `find_prm_pdfs` (alphabetical PRM directory name); the lower-index PRM is processed first, and the higher-index PRM's same-ordinal sheet anchors off the first PRM's exit-endpoint geometry.
- **Gap** (the ordinal sequence has a hole): The chain does **not** bridge by interpolation. Chain state resets at the gap. The post-gap PRM anchors from any embedded coord it has; if none, it falls back to the per-PRM behavior used before this change. A per-gap warning is logged naming the missing ordinal range.
- **No `SITE PLAN - N` parseable on a page**: a per-page warning is logged and that page falls back to per-PRM behavior in an isolated leftover pass; cross-PRM chaining is skipped for it.
- **Multiple embedded coords across the global sequence**: each embedded-coord page wins for itself (no averaging). After anchoring, the script walks pairs of adjacent embedded anchors and computes what the chain would predict at the meet point. If the chain prediction differs from the second embedded coord by more than `--reconciliation-threshold-m` meters (default 50 m), a warning is logged. The embedded anchor still wins; the threshold controls only the diagnostic.
- **Single PRM in JB folder**: the cross-PRM logic is a no-op. Output is functionally identical to the pre-change behavior.
- **Single-PDF mode** (no PRM folder structure): unchanged.

The per-overlay `<description>` records chain provenance, including any cross-PRM hop, formatted as `Chained from <prior_PRM>/SITE PLAN - <N> route exit endpoint ...`.

## Output structure

A typical output for a 7-sheet job:

```
output.kmz
├── doc.kml         (named overlays, descriptions with confidence + adjust notes)
└── images/
    ├── sheet_05.png
    ├── sheet_06.png
    ...
    └── sheet_11.png
```

In Google Earth Pro the user sees:

```
[Document name]
└── Site Plan Sheets (7)
    ├── SITE PLAN - 1 (PDF page 5)   [HIGH confidence]
    ├── SITE PLAN - 2 (PDF page 6)   [MEDIUM, chained]
    ...
    └── SITE PLAN - 7 (PDF page 11)  [MEDIUM, chained]
```

Each overlay's description carries:
- Anchor source (embedded / chained / manual)
- Confidence level
- Specific instructions for nudging if satellite imagery does not line up: "right-click the overlay -> Properties -> Location, and adjust corners"

## Diagnostics

When overlays don't land where you expect, run with `--debug-coords` and inspect the per-page table:

```bash
python scripts/build_overlays.py /path/to/JBID --multi-prm --combined --debug-coords 2>debug.txt
```

Each row shows: page number, sheet label, anchor PDF coords, anchor lat/lon, final LatLonBox bounds, and the anchor source. Common diagnoses:

- **Anchor source is `text centroid` and overlays are translated**: the embedded stamp text sits in a margin away from the route. Either the page has no detected red polyline (which is what falls back to the text centroid) or you ran with `--legacy-text-anchor`. Supply a manual two-corner anchor for the page to override.
- **Anchor source is `Cover-page` for every page**: no per-page embedded stamps were detected. Check whether the lat/lon stamp on each site plan is text (PyMuPDF can read it) or rasterized (PyMuPDF can't); if rasterized, supply manual anchors.
- **Anchor x/y are weirdly small or weirdly large**: probably a rotation problem. Check the WARN messages for `rotation=` lines — if any page has rotation other than 270 you need manual anchors for it.
- **Adjacent overlays don't align EW**: the route endpoint extraction picked a callout instead of the main polyline. Look at the rendered PNG; if you see a red callout near the page edge, the longest-polyline filter (added 2026-04) should already handle it — if it still wins, file a bug with the source PDF.

## Quality bar by use case

- **Production engineering layout:** not the right tool. Get the source `.dwg` from the drafter and export from Civil 3D directly.
- **Permit submittal exhibit:** acceptable when paired with manual anchors per page and span-length validation.
- **Visualization, corridor planning, reviewer markup, legacy job cleanup:** acceptable with default single-anchor + chain workflow.

State this in any deliverable note: "Georeferenced from drawing for visualization; not for engineering layout."

## Adjacent-tile overlap

Adjacent overlays intentionally overlap by ~50 to 100 feet east-west because each page extends past its match line by the title-block strip on the right and a small margin on the left. The chained anchor aligns the route exit and entry points, so the title block of sheet N geographically sits over the empty left-margin of sheet N+1. This is correct and matches reviewer intuition; do not "fix" it by cropping the page or trimming the bounding box.

## Validated reference

Validated against `JB0002131511/PRM0001388160/jb0002131511 A(1) PERU UTILITIES ONLY 21 POLES (2).pdf`:

- 18 pages total, 7 site plans (pages 5 to 11), 11 non-site (1 to 4 and 12 to 18) correctly skipped
- Sheet 1 anchored from embedded `2237 E 250 N PERU IN 46970   40.801166, -86.030433`
- Resulting overlays span longitude `-86.0308` to `-86.0156` at latitude `~40.801` (about 1.3 km east-west along E 250 N), matching the actual job extent
- Each tile measures `~680 ft EW x ~440 ft NS` at 1" = 40' scale
- Sheets 3 and 7 show ~85 ft north-south drift relative to neighbors, traced to route-endpoint shift between pages; documented in their overlay descriptions for manual nudging

## Known limitations

- **Drawing scale assumption** defaults to `1" = 40'` (the MasTec/Comcast standard for these jobs). Override with `--scale-feet-per-inch` when the title block prints a different scale.
- **North-up assumption** holds for all common Sphere/MasTec drawings. Drawings with a rotated north arrow need a per-page `rotation_deg` in the manual anchors file.
- **Chain accuracy** degrades after 5+ hops without a re-anchor. For long jobs, supply at least one embedded or manual anchor every ~5 sheets.
- **PDF rotation flag** must be honored when rendering. The bundled script handles the common `270` rotation; pages with `0` or `180` rotation render correctly because PyMuPDF's `get_pixmap` applies rotation by default.
- **Title-block exclusion** for embedded coords assumes the title block is in the bottom-right ~25% of the rotated page. Drafters with title blocks elsewhere will not be detected; supply a manual anchor.
- **`enhance_features.py` palette assumption.** The HSV constants in `scripts/enhance_features.py` assume the drafter uses red (~#FF0000) for proposed fiber, vaults, and anchors (the MasTec/Comcast standard). CD palettes from other drafters may differ; the wedge constants must be retuned for non-Comcast/MasTec palettes. The script prints zero-classification warnings when this happens.
- **Aerial vs underground separation depends on inline labels.** When aerial and UG fiber share the same color (the common MasTec case), separation relies on inline TEXT labels (`DB`, `TRENCH`, `VAC-T`, `BORE`, etc. for UG; `LASHED`, `STRAND`, `AERIAL` for aerial). Pages with no inline classification text default the route to aerial.

## Gotchas

- If overlays cluster into a tiny patch instead of spreading along the road, the geographic-axis rotation is off by 90 degrees. Verify the +x_pdf-is-north / +y_pdf-is-east convention above and that you are using this skill's `build_overlays.py`, not `cd-route-stitcher`'s `auto_georef.py`.
- **All overlays placed off-route by a similar offset**: the embedded lat/lon stamp on the seed sheet is being anchored at the text bounding-box centroid, not at the route endpoint nearest it. This is the `--legacy-text-anchor` codepath; the default since 2026-04 binds stamps to the closest route endpoint. If you see this with the default settings the page probably has no detectable red polyline (e.g. CAD'd at a non-route color, or the route stroke width is outside ROUTE_W_MIN..ROUTE_W_MAX). Supply a manual two-corner anchor.
- **WARN: page N: rotation=0 (or 90, 180)**: the geographic transform assumes the standard 270° rotation. For other rotations, supply a manual two-corner anchor for the affected pages or rotate the source PDF to 270 before re-running.
- If overlays land in the wrong neighborhood, the embedded anchor was misread or the manual anchor lat/lon has the wrong sign. Spot-check the seed coord on Google Maps before running the chain.
- If a sheet shows up rotated 90 degrees on satellite imagery, the page rotation flag was not applied at render time; force re-render with explicit rotation override.
- "Match line crosses page diagonally" jobs (rare) need manual anchors per sheet because the chain logic assumes left-edge entry / right-edge exit.
- **PRMs land stacked on top of each other in Google Earth Pro** instead of stretched along the route. The cross-PRM ordinal chain is missing. Verify the title block of the second PRM's first sheet reads `SITE PLAN - N` with `N > 1`; if it does and the chain is still failing, run with `--debug` and look for `WARN: ... no parseable SITE PLAN ordinal` lines or `WARN: ordinal gap detected ...` lines.
- **`enhance_features.py` classifies almost nothing on a page.** Run a probe: open the source PDF page in PyMuPDF, dump `page.get_text("dict")`, and check whether the expected red text spans exist with `R>180/G<100/B<100`. If the drafter uses a non-red palette, the script's HSV constants need retuning. If the PDF is raster-only (no text layer), no text spans will be present and the classifier defaults all routes to aerial; OCR is out of scope.

## Files

- `scripts/build_overlays.py` - main script; runs the entire pipeline. Self-contained: includes PDF parsing, page rendering, georeferencing, KMZ assembly, and multi-PRM orchestration with cross-PRM ordinal chaining.
- `scripts/build_hud.py` - optional post-processor; brands a combined KMZ with title-card / legend / north-arrow ScreenOverlay HUD. Reads the input KMZ, writes `<input>_hud.kmz`. Idempotent.
- `scripts/enhance_features.py` - optional post-processor; recolors aerial fiber, underground fiber, vaults, and anchors inside the embedded SITE PLAN PNGs via HSV masking + PDF-text classification. Reads a combined KMZ (preferably the `*_hud.kmz` from `build_hud.py`), writes `<input>_enhanced.kmz`. Idempotent.
