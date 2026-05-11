---
name: permit-to-kmz
description: Convert a Sphere/Comcast fiber permit map PDF into a drafter-ready KMZ and per-JB summary PDF. Use when the user wants to process a permit PDF, create a drafting package, convert a permit map to KMZ, or produce a job summary for drafters. Works with or without embedded coordinates and with or without reviewer markup (originals and revisions).
---

# Sphere Permit PDF to Drafter-Ready KMZ + Per-JB PDF

Convert any Sphere/Comcast fiber permit map PDF into two deliverables:

1. **KMZ** — per-JB folder layout with polyline routes (NEW / REPLACE / MARKUP) and a collapsible Design Notes folder
2. **Per-JB PDF** — cover page + one page per job showing routes on a gray basemap with a spec table

This skill works identically for originals (no markup) and revisions (with reviewer markup). Originals produce zero MARKUP polylines and an empty Design Notes folder — this is expected, not an error.

## Prerequisites

Before running the pipeline, verify these dependencies:

```bash
python -c "import fitz; import simplekml; import numpy; import matplotlib; print('OK')"
```

If any import fails, install:
```bash
pip install pymupdf simplekml numpy matplotlib
```

### Pipeline Scripts

Four Python scripts must exist in the working directory:
- `extract_routes.py`
- `generate_routes_kmz.py`
- `generate_routes_pdf.py`
- `scan_coordinates.py`

If any are missing, copy them from this skill's `scripts/` directory (the skill's base directory contains a `scripts/` subfolder with all four).

## Workflow

Execute these steps in order. Do not skip steps.

### Step 1: Find the PDF

Glob for `*.pdf` in the working directory. If multiple PDFs are found, ask the user which one to process.

Extract job info from the filename if possible:
- JB number: pattern `JB\d{10}`
- County: often appears as a plain name (e.g., PUTNAM, HAMILTON)
- Sub-area: pattern `INCWT\d{5}` or `INCW\d{5}\w+`

### Step 2: Extract Routes

```bash
python extract_routes.py "<pdf_filename>" --page 0 --output extracted_routes.json
```

**Verify the output** — read `extracted_routes.json` and check:

| Check | Good | Investigate |
|---|---|---|
| `jobs_jb` | 1+ JB codes found | Empty — JBs may be only in title block |
| `summary.by_status.NEW` | > 0 | 0 — possible stroke color mismatch |
| `summary.by_status.MARKUP` | > 0 for revisions, 0 for originals | 0 on a known revision — annotation type issue |
| `summary.by_job` | All routes assigned to JBs | Many UNASSIGNED — assignment radius too tight |

If all polylines are UNASSIGNED and the filename contains a JB code, this is likely a single-JB sheet where JB labels only appear in the title block. Note this to the user but continue — the KMZ will use "UNASSIGNED" as the folder name, which the user can rename.

### Step 3: Geocode Control Points

Use the 3-tier fallback to build `control_points.json`:

#### Tier 1: Embedded Coordinates (Automatic)

```bash
python scan_coordinates.py "<pdf_filename>" --page 0 --output control_points.json
```

- **Exit code 0** (TIER1_OK): 4+ coordinate pairs found, best 6 selected. Proceed to Step 4.
- **Exit code 1** (TIER1_FAIL): fewer than 4 pairs. Fall through to Tier 2.

#### Tier 2: Street Name Geocoding (Semi-Automatic)

If Tier 1 fails, geocode from street names found in the PDF:

1. **Extract street names and positions** from the PDF:

```python
import fitz, re
doc = fitz.open("<pdf_filename>")
page = doc[0]
blocks = page.get_text("dict")["blocks"]
road_re = re.compile(
    r"(State Road|County Road|US[-\s]?\d|SR[-\s]?\d|CR[-\s]?\d|"
    r"\b\w+\s(?:St|Ave|Blvd|Dr|Rd|Hwy|Ln|Ct|Way|Pike|Trail))\b", re.I
)
streets = []
for b in blocks:
    for line in b.get("lines", []):
        for s in line["spans"]:
            if road_re.search(s["text"]):
                x = (s["bbox"][0] + s["bbox"][2]) / 2
                y = (s["bbox"][1] + s["bbox"][3]) / 2
                streets.append({"text": s["text"].strip(), "pdf_x": x, "pdf_y": y})
doc.close()
```

2. **Identify intersection pairs**: two different street names within ~150 PDF points of each other.

3. **Determine city/state** from the PDF text or filename. Sphere permits always include a county name.

4. **Web search** for GPS coordinates of each intersection:
   - Query: `intersection "<Street A>" "<Street B>" <city> <state> GPS coordinates`
   - Need 5-6 well-spread intersections

5. **Match PDF positions**: use polyline junction endpoints in `extracted_routes.json` near those street labels as the PDF coordinates.

6. **Write `control_points.json`**:

```json
{
  "control_points": [
    {"name": "Main St at State Road 236", "pdf_x": 1667.0, "pdf_y": 1811.0, "lat": 39.8501, "lon": -86.7959}
  ]
}
```

Verify at least 4 points with good geometric spread (not all collinear).

#### Tier 3: Manual Fallback

If Tiers 1 and 2 fail to produce 4+ control points:

1. Tell the user: "I couldn't auto-detect enough control points from the PDF. I need your help identifying 4-6 road intersections on this map."
2. Show the street names found and their approximate PDF positions.
3. Ask the user to confirm intersection names and provide GPS coordinates (they can look these up on Google Maps).
4. Build `control_points.json` from their input.

### Step 4: Generate KMZ

```bash
python generate_routes_kmz.py extracted_routes.json control_points.json --output permit_routes.kmz
```

**Check the residuals** printed to console:

| Residual | Status | Action |
|---|---|---|
| All < 50m | Good | Proceed |
| Any 50-100m | Acceptable | Note in handoff |
| Any > 100m | Bad | Drop that control point, add a replacement, re-run |

If max residual > 100m, try removing the worst control point from `control_points.json` and re-running. If still bad, the control point coordinates may be wrong — verify them.

### Step 5: Generate Per-JB PDF

```bash
python generate_routes_pdf.py extracted_routes.json control_points.json --output permit_by_job.pdf
```

Expected: cover page listing all JBs, then one page per JB with:
- Map on left (existing infrastructure as gray basemap, NEW/REPLACE/MARKUP in color)
- Spec table on right (counts, cable distribution, footage, legend)

### Step 6: Hand Off

Present to the user:

```
## Drafting Package Complete

**Deliverables:**
- permit_routes.kmz — drafter-ready KMZ with per-JB folders
- permit_by_job.pdf — per-JB summary with maps and spec tables

**Extraction Summary:**
- JBs found: [list]
- Routes per JB: [NEW / REPLACE / MARKUP counts]
- Sub-areas: [list]
- Design notes: [count]
- Cable types: [distribution]

**Geocoding:**
- Tier used: [1/2/3]
- Max control point residual: [X]m
- [Any warnings about specific points]

**Before sending to drafters:**
- Spot-check 1-2 known segments in Google Earth
- Verify JB folder structure has correct routes per job
- Check markup lines appear alongside the NEW routes they reference
```

## Error Reference

| Problem | Likely Cause | Fix |
|---|---|---|
| All polylines UNASSIGNED | JB labels only in title block | Rename UNASSIGNED folder to JB code |
| Zero NEW routes | Stroke colors differ from palette | Inspect `stroke_color` values, add to extract_routes.py |
| Zero MARKUP on revision | Annotations have unexpected type | Check annotation types with fitz |
| Large residuals (> 100m) | Control point misidentified or collinear | Drop worst point, add off-axis point |
| PDF is raster (no vectors) | Scanned/image-based PDF | Cannot extract routes — manual tracing needed |
| Cable count/footage missing | Label radius too tight | Increase LABEL_RADIUS in extract_routes.py |
