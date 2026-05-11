---
name: plan-sheet-endpoints
description: "Extract start- and end-point metadata from every plan-profile sheet in a fiber/cable construction-drawing (CD) PDF. Works on any drafter's CD package — no template required. Outputs a CSV of per-sheet endpoints (sheet ID, start/end stations, structures, road names, span lengths, construction type, continuation references) and a KML containing pins ONLY for sheets where lat/lon was printed directly on that sheet. Vicinity / overview / cover-page coordinates are kept in a separate vicinity_reference.csv as reference data and are NEVER used to geolocate per-sheet endpoints. Trigger on requests like 'extract endpoints from this CD', 'pull the start/end points from each plan sheet', 'list every site plan's stations and coordinates', 'get the per-sheet metadata from this construction drawing'. For one-shot KMZ-of-the-whole-route output, use cd-route-stitcher instead."
---

# Plan-Sheet Endpoints

## What this skill does

Walks every page of a fiber/cable construction-drawing PDF and, for each plan-profile sheet, extracts:

- Sheet / site-plan identifier
- Start point: first station marker, leading structure label, or continuation reference from previous sheet
- End point: last station marker, trailing structure, or continuation reference to next sheet
- Lat/lon **printed directly on that sheet** (decimal degrees, DMS, or UTM — all converted to WGS84)
- Road / right-of-way names
- Pole / structure labels
- Span lengths (feet)
- Construction type (aerial, underground, overlash, direct bore, trench)
- Cable specs when present (e.g. `288F`, `144 COUNT`, `OPGW`)
- Match / continuation references to adjacent sheets

Outputs three files in `--output-dir`:

| File | Content |
|------|---------|
| `plan_endpoints.csv` | One row per plan-profile sheet, columns per spec |
| `vicinity_reference.csv` | Cover / vicinity / overview coords only — **never used to geolocate per-sheet endpoints** |
| `plan_endpoints.kml` | Pins ONLY for sheets with `has_native_gps=True` |

**Critical constraint:** Vicinity-page coords and per-sheet endpoints are treated as completely independent data. The KML and the per-sheet CSV are populated only from coordinates physically printed on the corresponding plan-profile page. If a vicinity map shows a different rough position than a plan sheet's stamped coords, the plan sheet wins (and the vicinity row stays in the reference CSV).

## When to use

Use whenever a user uploads a fiber/cable CD PDF and wants per-sheet endpoint metadata, including:

- "Extract the start and end points from each plan sheet"
- "List the stations, coordinates, and continuation references for every sheet"
- "Pull a CSV of per-page metadata from this construction drawing"
- "Tell me which sheets have GPS coordinates stamped on them"

Identifying signals in a PDF that mean this skill applies:

- Multi-page CD package (typically 5-60 pages)
- Sheet titles like `SITE PLAN - 1`, `SHEET 5 OF 25`, `SP-12`
- Station markers like `STA 0+00`, `B 21+37`
- Match-line callouts like `MATCH TO SHEET 6`, `SEE SHEET 11`
- Pole / structure labels like `POLE 32`, `P-15`, `STR #42`
- Variability across drafters — no fixed template required

For converting a CD into a single stitched route KMZ, use the separate `cd-route-stitcher` skill. For rendering each plan sheet as a raster overlay onto Google Earth, use `cd-ground-overlays`. This skill produces tabular metadata, not geographic geometry.

## Prerequisites

```bash
pip install -r ~/.claude/skills/plan-sheet-endpoints/requirements.txt --break-system-packages
```

Dependencies: `pymupdf`, `simplekml`, `pyproj`, `pandas`, `pytest`.

## Workflow

### Single PDF

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m scripts.extract /path/to/cd_package.pdf --output-dir /path/to/output
```

### Folder of PDFs (recursive)

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m scripts.extract /path/to/folder_of_cds --output-dir /path/to/output
```

The CLI prints a summary including PDF count, plan-sheet count, sheets-with-native-GPS count, vicinity rows, and raster pages flagged.

### Reading the output

`plan_endpoints.csv` columns (in order):

```
pdf_file, page_number, sheet_id,
start_label, start_station, start_lat, start_lon,
end_label, end_station, end_lat, end_lon,
road_names, structures, span_lengths_ft,
construction_type, continues_from_sheet, continues_to_sheet,
coords_source, has_native_gps
```

- `coords_source` is one of: `printed_on_this_sheet`, `none`. **Never** vicinity-derived.
- `has_native_gps` is `True` only when at least one valid lat/lon was found on that specific sheet.
- List-valued columns (`road_names`, `structures`, `span_lengths_ft`) are pipe-separated (`|`); empty lists render as `-` (so pandas keeps them as object dtype on read-back).

`vicinity_reference.csv` columns: `pdf_file, page_number, page_type, lat, lon, note`. Use this to manually cross-reference rough overview locations — but treat the per-sheet CSV as authoritative.

`plan_endpoints.kml`: open in Google Earth Pro. Each sheet with native GPS produces up to two pins (start + end) tagged with the sheet ID, page, construction type, and continuation reference.

## Architecture

```
scripts/
├── coord_parser.py     - decimal degrees, DMS, UTM → WGS84
├── station_parser.py   - station markers (B 21+37, STA 5+00, ...)
├── sheet_id_parser.py  - sheet IDs and continuation references
├── feature_parsers.py  - roads, structures, spans, construction type, cable specs
├── page_text.py        - PyMuPDF text extraction + raster-page detection
├── page_classifier.py  - score-based PageType classifier (PLAN_PROFILE vs COVER, etc.)
├── sheet_extractor.py  - orchestrates per-sheet extraction
├── pdf_processor.py    - walks PDF and folder; emits PdfResult records
├── output_writer.py    - main CSV, vicinity CSV, KML
└── extract.py          - CLI entry point
```

Each module is independently importable and tested. Add new coordinate formats, new page-type heuristics, or new feature extractors by editing one file.

## Known limitations

- **Coordinate detection is regex-only.** Drafters who print coordinates as graphic blocks (text-as-paths) will not be detected. Render the suspicious page to PNG; if you can read text but PyMuPDF cannot, the page is hybrid raster and needs OCR (out of scope).
- **Page classifier is heuristic.** A plan sheet that lacks station markers AND match references AND structure labels will fall through to `OTHER` and be skipped. Conversely, a "general notes" page that happens to mention several `STA 5+00`-style numbers in a table can mis-classify as plan-profile. Spot-check the row count vs. expected sheet count.
- **Start/end coord assignment is positional.** When two coords are stamped on a sheet, the first occurrence (in extracted text order) becomes start and the second becomes end. PyMuPDF text order roughly tracks reading order but not perfectly — verify in the KML before using endpoint coords for layout.
- **Raster-only pages are flagged but not OCR'd.** A scanned-image PDF will produce zero plan rows and a `raster_pages` count in the summary. To recover, OCR the PDF first (e.g. `ocrmypdf`) and re-run.
- **No coord ↔ station correlation.** This skill records what's printed; it does not validate that a printed coord matches the implied station value. Use the output for indexing and KMZ pinning, not for engineering layout.

## Quality bar by use case

- **Production engineering layout:** not the right tool. Use the source DWG / CAD file.
- **Per-sheet indexing for jobs / tickets / handoff:** acceptable as the primary deliverable.
- **KMZ corridor exhibit:** acceptable for sheets with `has_native_gps=True`. Sheets without native GPS are intentionally absent from the KML — supplement with `cd-route-stitcher` if a continuous route is needed.
- **Audit / QA against engineering drawings:** acceptable as a checklist input. Spot-check at least 10% of sheets for classifier and extractor accuracy.

State the quality bar in any deliverable note: "Generated from CD PDF for indexing and reference. Not certified for engineering layout — for that, use the source DWG in Civil 3D."

## Gotchas

- If a known plan-profile page does not appear in `plan_endpoints.csv`, run `page_classifier` on its text alone and check the score breakdown. Most failures are missing station-marker patterns; extending the regex in `station_parser.py` is usually a one-line fix.
- If `coords_source` is `none` on a sheet you know has stamped coordinates, the lat/lon is likely embedded in a graphic, not extractable text. Confirm by selecting the coord text in a PDF viewer — if it doesn't highlight, PyMuPDF can't read it.
- If the CLI flags many `raster_pages`, the input was scanned. Run `ocrmypdf input.pdf input_ocr.pdf` and re-run this skill on the OCR'd output.
- The vicinity CSV is intentionally never used by the KML or by the per-sheet CSV's coord columns. If a downstream user wants vicinity points on a map, they must add them by hand from `vicinity_reference.csv` after confirming each one is appropriate.

## Testing

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest -v
```

Synthetic test PDFs are generated programmatically in `tests/conftest.py` — no binary fixtures.
