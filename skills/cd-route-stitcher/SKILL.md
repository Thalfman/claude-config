---
name: cd-route-stitcher
description: "Convert multi-page Sphere/Comcast construction-drawing (CD) PDFs into a single georeferenced KMZ for Google Earth. Use this skill whenever the user uploads a multi-page CD package (cover sheet, vicinity map, multiple SITE-PLAN pages, typical details, traffic control plans) and wants every site-plan page's fiber route stitched onto a single KMZ. Trigger on requests to 'turn this CD into a KMZ', 'georeference all the site plans', 'stitch the construction drawing pages onto Google Earth', 'plot the entire route from this CD package', or any mention of multi-page CD/permit drawings that need to become geographic data. Output differentiates aerial routes (dashed lines) from underground routes (solid lines), with pole markers (no labels) at every station. This skill is for MULTI-PAGE CD packages; for one-page Sphere overview maps, use pdf-to-kmz instead."
---

# CD Route Stitcher

## What this skill does

Takes a multi-page Sphere/Comcast construction-drawing PDF (typically 20 to 60 pages: cover, vicinity, notes, legend, many SITE-PLAN tile pages, typical details, traffic control plans) and produces one georeferenced KMZ containing the complete fiber route stitched across every site-plan page.

Output KMZ contains:
- Route polylines for every site-plan page, styled by construction method (dashed for aerial, solid for underground)
- Pole markers at every station (no text labels by default to keep the map readable)
- One folder per source sheet plus a merged "Full Route" folder

## When to use

Use whenever the user has a multi-page MasTec/Comcast construction drawing PDF and wants any of:
- Google Earth file showing the fiber route across all site plans
- KMZ or KML output stitched from a multi-sheet CD package
- Geographic coordinates of the route for visualization or corridor planning
- Visual verification of the route on satellite imagery

Identifying signals in a PDF:
- Multi-page (typically 30 to 60 pages)
- Sheet titles like `SITE PLAN - 1`, `SITE PLAN - 2`, ...
- `MATCH TO SITE PLAN - N` labels on left/right page edges
- Red dashed route over an aerial photograph
- Pole tables with `Sequence`, `Pole #`, `Proposed Height`
- Station callouts like `STA: A 37+25 59' L`
- `MasTec Communications Group` and Comcast logos in the title block
- One page may embed an explicit lat/lon next to the start address (e.g., `2237 E 250 N, PERU, IN 46970, USA  40.801166, -86.030433`); when present, this is the preferred seed anchor

For single-page Sphere overview maps without site-plan tiles, use the separate `pdf-to-kmz` skill instead.

## Prerequisites

```bash
pip install pymupdf pillow simplekml --break-system-packages
```

## Workflow

The pipeline is three scripts run in sequence, with optional manual anchor input between steps 1 and 2.

### Step 1: Extract per-page features

```bash
python scripts/extract_pdf.py <pdf_path> --output cd_data.json
```

Walks every page and emits, per site-plan page:
- `polylines`: red route segments stitched into chains, in rendered (post-rotation) PDF coords
- `embedded_latlon`: any `lat, lon` text appearing outside the title-block area (the gold anchor when present)
- `addresses`: street addresses with city/state/zip and PDF positions
- `match_lines`: `MATCH TO SITE PLAN - N` labels with positions
- `endpoints`: start/end vertices of every polyline (used as match-line connection candidates)
- `poles`: circle-X pole symbol locations
- `annotations`: nearby text like `OVERLASH ... TO EXISTING STRAND` (aerial signal) or `BORE AND PLACE 2" CONDUIT` (underground signal)

Route filter: stroked-only paths, color near pure red `(1.0, 0.0, 0.0)` or dark red `(0.867, 0.0, 0.0)`, stroke width approximately 0.72 pt. This isolates route geometry from callout boxes (width 1.0), arrowheads (filled triangles), and basemap decorations.

### Step 2 (optional): Build manual anchors

If the PDF has no embedded `lat, lon` stamp, or you want sub-2-meter accuracy on critical pages, supply geocoded address anchors via a JSON file. Format:

```json
{
  "page_5": [
    {"address": "2237 E 250 N, PERU, IN 46970", "lat": 40.801166, "lon": -86.030433}
  ],
  "page_6": [
    {"address": "...", "lat": ..., "lon": ...}
  ]
}
```

Geocode each address via `web_search` or any external geocoder before writing the file.

### Step 3: Auto-georeference

```bash
python scripts/auto_georef.py cd_data.json \
  --manual-anchors manual_anchors.json \
  --output control_points.json
```

Synthesizes per-page control points from embedded coords, manual anchors, the printed scale (typically 1 inch = 40 feet), and a north-up assumption. Outputs an affine transform per page.

### Step 4: Build KMZ

```bash
python scripts/build_kmz.py cd_data.json control_points.json --output route.kmz
```

Applies the per-page affine transform, classifies each polyline as aerial or underground based on the nearest annotation within 120 pt of the polyline midpoint, merges polylines into chains across match lines, and renders dashed vs solid styling accordingly.

### Step 5: Validate

Open `route.kmz` in Google Earth. Spot-check:
- Does the route start at the address stamped on the first site-plan page?
- Does it follow the road shown in the drawing, not cut across yards or buildings?
- Pole count and rough sequence approximately right?
- Aerial vs underground styling matches the OVERLASH/BORE annotations on the drawing?

For quantitative validation, measure a few KMZ segments against the printed span callouts (e.g., 169', 157', 287'). Within 1 to 2 percent is good. More than 5 percent off indicates a transform problem.

## Multi-PRM workflow

When a job has multiple pole-owning entities (PRMs), each is processed independently against its own PDF, then merged. The folder convention:

```
JB[number]/
├── PRM[number]/
│   └── drawing.pdf
```

Both `JB` and `PRM` names are dynamic per job. The skill keys off path: grandparent of the PDF is the JB name, parent is the PRM name.

Process each PRM:

```bash
python scripts/extract_pdf.py JB123/PRM456/drawing.pdf --output PRM456_data.json
python scripts/auto_georef.py PRM456_data.json --output PRM456_cp.json
python scripts/build_kmz.py PRM456_data.json PRM456_cp.json --output JB123/PRM456/PRM456.kmz
```

Validate each PRM in Google Earth before moving to the next. Once all are accepted, merge:

```bash
python scripts/merge_kmz.py JB123/PRM*/PRM*.kmz \
  --job-name "JB123" \
  --output JB123/JB123_combined.kmz
```

Merged tree in Google Earth:

```
JB[number]
├── PRM[number]
│   ├── Route
│   └── Poles
└── Combined Route (all PRMs merged, with PRM-prefixed linestring names)
```

Each linestring is named with its PRM prefix (e.g., `PRM456 Sh3-2`) so segment provenance is identifiable from the placemark label.

## Validated reference data (Peru Utilities sample)

The following was validated against `jb0002131511_A_1__PERU_UTILITIES_ONLY_21_POLES.pdf`:

- **Page 5 ground-truth anchor:** `2237 E 250 N, PERU, IN 46970` at `40.801166, -86.030433`
- **Site plans:** pages 5 through 11
- **Non-site pages:** pages 12 through 18 (typical details, traffic control)
- **Continuation marker:** page 11 carries `CONTINUATION TO JB0002131511 - B`; remainder of route is in companion PDF
- **Output coordinate range:** longitude -86.030 to -86.015, latitude approximately 40.801 (about 1.5 km east-west along E 250 N, matching the actual job)

## Known limitations

- **Aerial vs underground classification** defaults to "aerial" when no annotation is found within 120 pt of a polyline midpoint. Safer for Comcast overlash work, but mostly-UG jobs will be misclassified if annotations are sparse.
- **Single-anchor accuracy:** single embedded anchor plus scale plus north-up gives 5 to 15 meter horizontal accuracy. For sub-2 meter, supply 3+ hand-geocoded manual anchors per page.
- **Match-line continuity** between pages works for horizontal exits (left/right edge). Vertical exits (top/bottom edge) are not yet automated.
- **Address geocoding fallback** is not built into the scripts. When a PDF lacks an embedded `lat, lon` stamp, you currently supply a `manual_anchors.json` by hand. Claude can geocode the addresses via `web_search` when running the workflow interactively.
- **Drafter-specific assumptions:** the color filter and stroke width were calibrated against MasTec drawings generated by Civil 3D 2025. Drawings from other drafters may use different colors or stroke widths and produce empty extraction.
- **Pole placemark accuracy** derives from drawing geometry, not real GPS. Placemarks will sit near but not exactly on the poles in the aerial imagery.

## Gotchas

- If `extract_pdf.py` returns zero polylines, the most likely cause is a different stroke color or width than the calibrated filter. Render page 5 (or any clear site plan) to PNG, sample the route stroke color and width, and update the filter constants in `extract_pdf.py`.
- If a page appears rotated 90 degrees in the KMZ, the page rotation flag was misread. Re-run with explicit rotation override.
- If routes land in the wrong neighborhood, the geocoded anchor is wrong. Verify the address callout you used actually exists at the lat/lon you supplied; common failure mode is geocoding to a similar address in a different state.
- Pages 12+ in most CD packages are typical details and traffic control plans, not site plans. Extraction correctly skips them. Do not be alarmed by missing geometry on those pages.

## Quality bar by use case

- **Production engineering layout:** not the right tool. Get the source `.dwg` from the drafter and export KMZ from Civil 3D directly.
- **Permit submittal corridor exhibit:** acceptable with manual anchors per page and span-length validation.
- **Visualization, corridor planning, legacy job cleanup:** acceptable with default single-anchor workflow and spot-check validation in Google Earth.

State the quality bar in any deliverable note: "Georeferenced from drawing for visualization and corridor planning, not for engineering layout."
