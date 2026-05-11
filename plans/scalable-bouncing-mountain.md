# Plan — Geomap PDF Page 1 to KMZ (Putnam INCWT00900, cgrey markups)

## Context

User has a Putnam County, Indiana electric utility permit map PDF at `NEED_JB0001914985_PUTNAM_INCWT00900_permit map (003).pdf`. Reviewer "cgrey" (Chris Grey) placed **299 annotations on page 1 only** — 122 FreeText callouts, 138 lines (39 of them orange route segments), 39 squares (structure boxes). An existing `Putnam_INCWT00900_cgrey_markup.kmz` is approximate and was built from generic extraction — user wants a **rebuilt KMZ where every cgrey annotation on page 1 is placed at its true WGS84 lat/lon**, derived directly from the PDF (not from the `Drafter_Request.md` coordinate tables). Base-map context for viewing will be Google Earth's satellite + streets.

The PDF has **no GeoPDF metadata** (confirmed: no `/LGIDict`, no `/VP`/`/Measure`), so georeferencing must come from ground control points. Chris handily provided ~40 FreeText callouts whose `/Contents` contain explicit "Approx 39.xxx, -86.xxx" coordinates — these serve as GCPs (known PDF-space position + known WGS84 position).

Output: `C:\Users\thalf\OneDrive\Desktop\Need Revisions\Putnam_INCWT00900_cgrey_page1.kmz`

---

## Critical files

- **Input PDF:** `C:\Users\thalf\OneDrive\Desktop\Need Revisions\NEED_JB0001914985_PUTNAM_INCWT00900_permit map (003).pdf`
- **Reference only (do NOT feed into the fit — verification only):** `Drafter_Request.md`, `cgrey_Drafter_Directive.md`, `cgrey_markup_page1-01.png`
- **Existing KMZ (to be replaced, not reused):** `Putnam_INCWT00900_cgrey_markup.kmz`
- **Output:** `C:\Users\thalf\OneDrive\Desktop\Need Revisions\Putnam_INCWT00900_cgrey_page1.kmz`
- **Build script (new):** `C:\Users\thalf\OneDrive\Desktop\Need Revisions\build_cgrey_kmz.py`

Python: `C:\Users\thalf\AppData\Local\Programs\Python\Python312\python.exe`. Already installed: `pypdf`, `pdfplumber`. **Need to install:** `simplekml`, `numpy`.

---

## Implementation

### Step 0 — Install deps
Run `python -m pip install simplekml numpy` once. Abort if install fails.

### Step 1 — Parse cgrey annotations (use `pypdf`, not `pdfplumber`)
Open PDF with `pypdf.PdfReader`, take page 0. Iterate `/Annots`, resolve each indirect ref, and keep entries where `/T == "cgrey"` (fallback to `/NM` prefix if `/T` missing). Confirm `page.get("/Rotate", 0) == 0` first; abort with a clear error otherwise.

For every kept annotation capture `/Subtype`, `/NM`, `/Contents` (fall back to stripped `/RC` if blank — Bluebeam often uses rich text), `/Rect`, `/C` (stroke RGB 0–1). Then by subtype:
- **FreeText:** also capture `/CL` (callout polyline — tail is at indices `[0],[1]`; this is the point the bubble actually points to), `/IT`.
- **Line:** capture `/L` (`[x1 y1 x2 y2]`).
- **Square:** `/Rect` corners give the polygon.

Expected totals (sanity): 122 FreeText + 138 Lines + 39 Squares = 299. Stop if count is off by more than a handful.

### Step 2 — Harvest ground control points from FreeText
For each FreeText, regex `r"(-?\d{1,3}\.\d{3,7})\s*[,\s]\s*(-?\d{1,3}\.\d{3,7})"` against `/Contents`. Accept only pairs where lat ∈ [39.84, 39.86] and lon ∈ [-86.81, -86.77] (guards against dimensions like `36" × 48"` being misread as numbers).

PDF anchor for each GCP: **prefer `/CL[0], /CL[1]` (callout tail — touches the feature)**. If `/CL` missing, use `/Rect` centroid. Store tuples `(px, py, lon, lat, annotation_name)`.

Expect ~40 GCPs. If fewer than 15, stop and surface the issue — transform quality will be unreliable.

### Step 3 — Fit affine transform PDF → WGS84
Use 6-parameter affine (not similarity — longitude and latitude have different point-per-degree scales at 39.85° where cos(lat) ≈ 0.767). Two independent `numpy.linalg.lstsq` fits:
- `lon = a·px + b·py + c`
- `lat = d·px + e·py + f`

Sign sanity: `a > 0` (x → east), `e > 0` (y-up = north-up), `b, d` near zero on a north-up map.

**Residuals:** convert to feet via `dx_ft = (lon_pred − lon_true) · cos(lat) · 364000`, `dy_ft = (lat_pred − lat_true) · 364000`. Expect RMS ≤ 10 ft. Drop any point with residual > 3σ **or** > 30 ft and refit once (not more — iterating chases noise). Print the residual table for a human to eyeball.

Fit-range sanity: predicted longitudes must span both -86.776 (Set A cluster) and -86.795 (Set B cluster). If not, stop — fit is wrong.

### Step 4 — Apply transform, build KMZ
Helper `pdf_to_lonlat(px, py)` applies both linear forms. For every cgrey annotation:
- **Line** → `LineString` with both `/L` endpoints transformed.
- **Square** → `Polygon` with the four `/Rect` corners transformed (ring closed); also emit a centroid `Point` in a "Structure centroids" sub-folder for readable labels at low zoom.
- **FreeText** with `/CL` → `Point` at transformed `/CL` tail; without `/CL` → `Point` at transformed `/Rect` centroid. `name` = first 40 chars of contents, `description` = full contents in CDATA.

**KMZ folder structure:**
- `Orange route / Set A` (orange lines with lon > -86.785)
- `Orange route / Set B` (orange lines with lon ≤ -86.785)
- `Structure boxes` (39 squares; 1 red in a distinct sub-folder)
- `Leaders / other lines` (~99 non-orange lines, sub-grouped by color: pink / blue / green)
- `Callouts` (all 122 FreeTexts)
- `Coordinate pins` (subset that parsed as GCPs — duplicates fine, useful for QA)

**Styles:** one `LineStyle` per color bucket. Orange KML color `ff0080ff` (ABGR), width 4. Other per-annotation `/C` → ABGR hex. Match "orange" with ±0.15 per-channel tolerance around RGB(1.0, 0.408, 0.125); if fewer than 30 orange lines land in the bucket (expected 39), stop and re-examine tolerance.

Write via `simplekml.Kml().savekmz(<output_path>)`.

### Step 5 — Verify (required before declaring done)
Parse `Drafter_Request.md` programmatically for the endpoints of **A-01, A-05, B-07, B-20, B-31** (5 segments — 3 is too few to catch a longitude-axis sign flip). For each, find the nearest orange `LineString` in the built KMZ by midpoint distance and compare endpoints. Target: each endpoint within **15 ft**; any miss > 30 ft means re-examine `/CL` tail orientation (PDF spec is ambiguous — Bluebeam and Acrobat disagree on whether `/CL[0:2]` or `/CL[-2:]` is the tail). Print a small comparison table.

---

## Risks / open questions to verify mid-execution

- **`/CL` tail orientation** — spot-check on 2–3 GCPs by cross-referencing `cgrey_markup_page1-01.png` before trusting the whole batch. If reversed, swap to `/CL[-2], /CL[-1]`.
- **Set A/B longitude split** — Drafter_Request shows a clean gap between -86.7765 and -86.7948; split at -86.785. No orange segment should land within ±0.001° of the boundary.
- **Orange color tolerance** — start at ±0.15/channel; widen only if the orange-line count falls short of 39.
- **`/Contents` vs `/RC` encoding** — prefer `/Contents`; if blank, strip XHTML tags from `/RC` before regex.
- **Do NOT use `Drafter_Request.md` as fit input** — verification only. Using it for GCPs would make the verification tautological.

---

## Verification end-to-end

1. Run `python build_cgrey_kmz.py` and confirm it prints: GCP count, residual RMS in feet, 5-segment verification table with per-endpoint errors, and output file path.
2. Confirm `Putnam_INCWT00900_cgrey_page1.kmz` exists and opens in Google Earth (user-facing check).
3. In Google Earth, the orange route should sit in/near the N CR 425 E west ROW (Set A) and along the east-west corridor around 39.849–39.852 N (Set B). The pump station pin should read near 39.849892, -86.795756.
4. If residual RMS > 10 ft, or any of the 5 verification segments misses by > 30 ft, treat the run as failed and re-examine `/CL` orientation before shipping.
