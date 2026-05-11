# Plan: Sphere Permit PDF to Drafter-Ready KMZ + Per-JB Summary PDF

## Context

Convert `NEED_JB0001914985_PUTNAM_INCWT00900_permit map (003).pdf` (10.5 MB, 42 pages, revision with 331 annotations) into two drafter deliverables:
1. **KMZ** — per-JB folder layout with polyline routes (NEW/REPLACE/MARKUP) and Design Notes
2. **Per-JB PDF** — cover page + one page per job with routes on basemap + spec table

The PDF covers **Greencastle, Indiana** (Putnam County) along US-231. It's a revision with 138 Line annotations and 39 Square annotations (reviewer markup). The user wants this done now AND set up as a repeatable workflow.

## Approach

Use the **pdf-to-kmz skill's route-based pipeline** (3 scripts, 3 stages). This is the recommended approach over the legacy point-feature extraction because it produces polyline geometry (what drafters need) and captures reviewer markup as real routes.

## Implementation Steps

### Stage 1: Environment Setup

1. **Install PyMuPDF** — the only missing dependency (simplekml, numpy, matplotlib are already on Python 3.12)
   ```bash
   python -m pip install pymupdf
   ```
   Verify: `python -c "import fitz; print(fitz.__version__)"`

2. **Copy skill scripts to working directory** for repeatability (skills-plugin path contains session UUIDs that change):
   - `extract_routes.py`
   - `generate_routes_kmz.py`
   - `generate_routes_pdf.py`
   
   Source: `C:\Users\thalf\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\6499e0b1-7ab6-440d-9940-e233c1b692ac\b8cc6a09-f62e-45b9-8d75-859b09fa1655\skills\pdf-to-kmz\scripts\`

### Stage 2: Extract Routes

3. **Run extract_routes.py** on page 0:
   ```bash
   python extract_routes.py "NEED_JB0001914985_PUTNAM_INCWT00900_permit map (003).pdf" --page 0 --output extracted_routes.json
   ```

4. **Verify extraction** — check `extracted_routes.json` for:
   - `jobs_jb` contains JB0001914985
   - `sub_areas_incwt` contains INCWT00900 (plus INCWT009B1, C1, H1, INCWT0209A1)
   - MARKUP count > 0 (138 Line + 39 Square annotations should produce ~177 markup polylines)
   - NEW and REPLACE routes detected with correct status/construction
   - ~150 design notes from FreeText/Stamp annotations
   - If all UNASSIGNED: JB labels only in title block — assign all to JB0001914985 (single-JB sheet per filename)

### Stage 3: Geocode Control Points

5. **Identify 5-6 intersections** spread across the map. Candidates based on PDF text extraction:

   | Intersection | Approx PDF position | Purpose |
   |---|---|---|
   | US-231 at SR-240 | x~140, y~1770 | West anchor |
   | Indiana St at SR-240 | x~1613, y~1770 | Center |
   | Walnut St at SR-240 | x~1656, y~1755 | Center-east |
   | County Road (north) | x~2000, y~1650 | Northeast anchor |
   | US-231 (south end) | x~140, y~2200 | South anchor |

6. **Get precise PDF coords** from polyline junction endpoints in `extracted_routes.json`

7. **Look up real-world lat/lon** via web search for each intersection (Greencastle is ~39.644, -86.862)

8. **Save `control_points.json`** with 5-6 entries

### Stage 4: Generate KMZ

9. **Run generate_routes_kmz.py**:
   ```bash
   python generate_routes_kmz.py extracted_routes.json control_points.json --output permit_routes.kmz
   ```

10. **Check residuals** in `permit_routes_report.json`:
    - All < 50m: good
    - 50-100m: acceptable with note
    - > 100m: recheck that control point

### Stage 5: Generate Per-JB PDF

11. **Run generate_routes_pdf.py**:
    ```bash
    python generate_routes_pdf.py extracted_routes.json control_points.json --output permit_by_job.pdf
    ```

12. **Verify PDF** — cover page lists JBs, per-JB pages have colored routes on gray basemap + spec table

### Stage 6: Hand Off

13. **Present summary**: JBs found, route counts (NEW/REPLACE/MARKUP), footage totals, design-note count, max residual, any UNASSIGNED items

## Output Files

| File | Type | Description |
|---|---|---|
| `permit_routes.kmz` | Deliverable | Drafter-ready KMZ with per-JB folders |
| `permit_by_job.pdf` | Deliverable | Per-JB summary with maps + spec tables |
| `extracted_routes.json` | Intermediate | Extracted route data (keep for audit) |
| `control_points.json` | Intermediate | Georeferencing anchors (keep for re-runs) |
| `permit_routes_report.json` | Intermediate | KMZ generation report with residuals |

## Reusable Scripts (local copies)

| Script | Purpose |
|---|---|
| `extract_routes.py` | PyMuPDF-based route extraction, JB grouping, markup capture |
| `generate_routes_kmz.py` | Per-JB KMZ generation with affine transform |
| `generate_routes_pdf.py` | Per-JB summary PDF with basemap + spec table |

## Repeatability

For future permits, re-run the same 3 commands with:
- A new PDF
- New control points (different location = different intersections)

The only manual step per permit is geocoding 4-6 control points (step 5-8).

## Verification

- Check `extracted_routes.json` summary for reasonable route counts and JB assignment
- Check `permit_routes_report.json` for control point residuals < 50m
- Open KMZ in Google Earth — routes should align with roads/poles in satellite imagery
- Open per-JB PDF — cover page lists correct JBs, per-JB pages show correctly colored routes with spec table

## Troubleshooting Reference

- **All UNASSIGNED**: JB only in title block — hardcode assignment to JB0001914985
- **MARKUP = 0**: Annotations have unexpected structure — debug annotation types
- **All UNKNOWN status**: Stroke colors differ from hardcoded palettes — inspect and add colors
- **Large residuals**: Control point misidentified or points too collinear — drop worst, add off-axis point
