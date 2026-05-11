---
name: dxf-to-kmz
description: Use when converting DXF construction drawings into contractor-ready KMZ files for fiber/utility permit handoff. Trigger on requests to "turn this DXF into a KMZ", "convert the surveyor's CAD file for the contractor", "make a Google Earth file from this DXF", or any request involving DXF/CAD input that needs to become a clean Google Earth deliverable showing permit boundaries and the proposed route. Handles three CRS tiers (embedded .prj/GEODATA, regional defaults, manual anchors) and convention-based layer-to-feature mapping with per-job override.
---

# DXF to KMZ

## What this skill does

Takes a DXF construction drawing and produces a clean, contractor-ready KMZ for Google Earth. The output emphasizes:

- The **permit boundary / work area** (what the contractor is allowed to touch)
- The **proposed route**, with aerial (dashed) and underground (solid) differentiation matching `cd-route-stitcher`
- **Proposed infrastructure** (poles, vaults) the contractor will install
- **Existing infrastructure** for context (folder default-off, toggleable)

Coordinate handling is tier-based and graceful:

1. **Tier 1 — embedded:** `.prj` sidecar or AutoCAD `GEODATA` xrecord (zero-touch)
2. **Tier 2 — regional default:** filename matches a region in `dxf_crs_defaults.json` (zero-touch after the first job in that region)
3. **Tier 3 — manual anchors:** local-coord DXFs need 2+ DXF↔lat/lon control points

Layer-to-feature mapping uses regex conventions; the `inspect_dxf.py` step writes a `layer_mapping.json` that you can edit before producing the KMZ.

## When to use

Use whenever the user has a DXF and wants any of:

- A Google Earth deliverable for contractors showing the permit area and proposed route
- Conversion of a surveyor's or drafter's CAD output to KMZ
- Visualization of the permitted work area on satellite imagery

If the input is a multi-page CD PDF, use `cd-route-stitcher` (vector) or `cd-ground-overlays` (raster) instead. If the input is a Sphere/Comcast permit map PDF, use `permit-to-kmz`.

## Prerequisites

```bash
pip install -r requirements.txt
# or
pip install ezdxf pyproj simplekml shapely
```

## Workflow

**Run all scripts from the `dxf-to-kmz/` folder.** The `scripts/` package only resolves when the skill folder is your CWD. Running from a parent directory or absolute paths to the `.py` files will fail with import errors.

The pipeline is **inspect → edit `layer_mapping.json` → build**. Always run Step 1 first; never skip directly to `build_kmz.py` even on a "quick" job — the layer-mapping JSON is what tells the builder which layers to publish.

### Step 1: Inspect the DXF (always run first)

```bash
cd dxf-to-kmz
python -m scripts.inspect_dxf path/to/drawing.dxf --output layer_mapping.json
```

This prints a layer summary, attempts CRS detection (Tiers 1 + 2), and writes `layer_mapping.json` with default classifications.

**Verify the output:**

| Field | Good | Investigate |
|---|---|---|
| `crs.tier` | 1 (embedded) or 2 (regional match) | 3 → run `build_anchors.py` next |
| `crs.epsg` | matches the survey datum on title block | wrong zone → fix `dxf_crs_defaults.json` and re-run |
| `layers` with `publish: true` | route, boundary, proposed infrastructure | unmapped layer that should be published → set `feature` + `folder` + `style` manually |

**Branch on `crs.tier`:**
- `tier == 1` or `tier == 2` → skip to Step 3.
- `tier == 3` → continue to Step 2 (the DXF is in local coordinates; you must build anchors before the builder can reproject).

If a layer has the wrong feature classification (e.g., a permit boundary on a non-conventional layer name), edit `layer_mapping.json` *before* running Step 3:

```json
{
  "name": "EASEMENT_AREA",
  "publish": true,
  "feature": "polygon",
  "subtype": "boundary",
  "folder": "Permit Area",
  "style": {"line_color": "ff00ffff", "fill_color": "4000ffff", "width": 2}
}
```

### Step 2 (Tier 3 only): Build manual anchors

If `crs.tier == 3`, the DXF is in local coordinates. Run:

```bash
python -m scripts.build_anchors drawing.dxf --output anchors.json
```

The script lists candidate anchor points (POINTs/INSERTs on `MON`/`BENCHMARK`/`CTRL_PT`-named layers) and prompts you for the lat/lon of each. Look up coordinates on Google Maps. Need 2+ for Helmert, 3+ for affine.

### Step 3: Build the KMZ

```bash
# Tier 1 / 2 (CRS in layer_mapping.json):
python -m scripts.build_kmz drawing.dxf layer_mapping.json --output contractor.kmz

# Tier 3 (anchors):
python -m scripts.build_kmz drawing.dxf layer_mapping.json --anchors anchors.json --output contractor.kmz
```

Optional flags:
- `--simplify <ft>` — Douglas–Peucker tolerance for polylines (default 0.5 ft)

### Step 4: Validate in Google Earth Pro

Spot-check:
- Does the permit boundary line up with parcel/road geometry on satellite imagery?
- Does the proposed route follow the road, not cut across yards?
- Is "Existing Infrastructure" folded and toggleable?
- Does the document description show the CRS provenance line?

For Tier 3 jobs, measure the residual error: pick a known landmark visible on satellite imagery and compare to its DXF→KMZ position. Sub-10 m is typical for 2-anchor Helmert; sub-2 m for 3+ affine.

## KMZ output structure

```
[Job name]
├── Permit Area                          (yellow translucent polygon, visible)
├── Proposed Route                       (visible)
│   ├── Aerial   (dashed red — see styling note below)
│   └── Underground   (solid red)
├── Proposed Infrastructure              (visible)
│   ├── Poles
│   └── Vaults
├── Stations & Labels                    (visible, folded)
└── Existing Infrastructure              (visibility OFF, folded)
```

The document description carries the CRS provenance and the quality-bar disclaimer.

## Quality bar

Generated from drafter DXF for contractor work-area handoff and field navigation. Coordinates derived via the detected/configured tier. **Not certified for engineering layout** — for that, use the source DWG in Civil 3D.

State this in any deliverable note alongside the KMZ.

## Layer convention rules (built-in)

| Pattern (case-insensitive regex) | Feature | Subtype | Default | Publish |
|---|---|---|---|---|
| `.*PERMIT.*BOUND.*` / `.*WORK.*AREA.*` / `.*ROW.*LIM.*` | polygon | boundary | yellow polygon | yes |
| `(?:^\|_)EX(?:_\|$)` / `.*EXIST.*` | (resolved) | existing | gray | **no** (default off) |
| `.*FIBER.*AER.*` / `.*AERIAL.*` / `.*OVH.*` | route | aerial | red, dashed | yes |
| `.*FIBER.*UG.*` / `.*UNDERGRD.*` / `.*BORE.*` / `.*TRENCH.*` | route | underground | red, solid | yes |
| `.*REPLACE.*` | route | replace | orange, dashed | yes |
| `.*MARKUP.*` / `.*REVISION.*` / `.*REDLINE.*` | route | markup | magenta, dashed | yes |
| `.*PROPOSED.*POLE.*` / `.*NEW.*POLE.*` | point | pole-new | red dot | yes |
| `.*VAULT.*` / `.*HANDHOLE.*` / `.*\bHH\b.*` | point | vault | blue square | yes |
| `.*STATION.*` / `.*\bSTA\b.*` | label | station | small text | no |

Order matters; first match wins. Existing-infrastructure check runs *before* the route/point rules so `EX_FIBER` doesn't get classified as a fresh aerial route.

To add a rule for a new drafter, edit `scripts/layer_conventions.py`:

```python
RULES.insert(0, Rule(r".*MY_NEW_PATTERN.*", "route", "aerial", True))
```

## Adding a new region to defaults

`scripts/dxf_crs_defaults.json` accumulates institutional knowledge. When a new region first appears, add the EPSG once and every subsequent job in that region is zero-touch:

```json
{
  "Indiana": "EPSG:2965",
  "Texas-North-Central": "EPSG:2276"
}
```

Match heuristic is case-insensitive substring of the DXF filename. Use whatever phrase you reliably put in your filenames.

## Known limitations

- **Dashed polylines** in KML are not natively supported by Google Earth Pro — width is honored, but solid/dashed differentiation falls back to `<gx:outerColor>`. For maximum clarity, the aerial folder is named "Aerial" and the underground folder "Underground"; folder names disambiguate when the line style does not.
- **Curve fidelity:** Arcs and splines are tessellated to polylines; CAD-grade curve precision is not preserved.
- **Hatch patterns:** Not rendered. Permit boundary fills are flat translucent yellow.
- **3D Z-coordinates:** Discarded. KMZ is 2D-on-ground (`clampToGround`).
- **External references (XREFs):** Not auto-resolved. Bind XREFs in CAD before exporting DXF.
- **Multi-DXF JB-level merge:** Not supported in v1. If you need to combine multiple DXFs, build each KMZ separately.

## Gotchas

- **KMZ lands in the wrong continent** — CRS misdetected. Re-run `inspect_dxf.py` and inspect the `crs` block. If `tier=2`, the regional default may be wrong; verify the EPSG matches the survey datum on the title block.
- **Routes are scaled too small/large but in the right neighborhood** — wrong State Plane zone (right state, wrong half). Common: Indiana East (`EPSG:2965`) vs West (`EPSG:2966`); Florida North vs East vs West. Override the EPSG in `layer_mapping.json` and re-run `build_kmz.py`.
- **All polylines tagged as one feature** — DXF uses a single layer (`0` or `Default`) for everything. Pre-step in CAD: split entities to a layered structure, or supply a hand-written `layer_mapping.json` that does the discrimination by other means (color, linetype — not yet implemented as a Tier 4 fallback).
- **Permit boundary missing** — drafter put it on a non-conventional layer name. Find the layer in the inspect output, set `publish: true, feature: polygon, folder: "Permit Area"`.
- **KMZ is huge** — DXF has thousands of arc-tessellation segments per polyline. Run `build_kmz.py --simplify 1.0` for more aggressive simplification (1 ft is invisible at contractor zoom).
- **`build_anchors.py` finds no candidates** — your DXF doesn't have INSERT/POINT entities on `MON`/`BENCHMARK`/`CTRL_PT`-named layers. Either add them in CAD, or hand-write `anchors.json` with two known DXF↔lat/lon pairs (the script is just a convenience wrapper around the underlying transforms).

## Red flags (do not do these)

- **Do not skip `inspect_dxf.py`** even on a "trivial" job. The builder requires `layer_mapping.json`; running `build_kmz.py` first will fail and any classification you cobble by hand will miss the regex conventions and CRS tier detection.
- **Do not run the scripts from a parent directory** or with absolute paths to the `.py` files. The `scripts/` package only resolves when `dxf-to-kmz/` is your CWD. Use `python -m scripts.<name>` from inside the skill folder.
- **Do not edit `crs.epsg` to "fix" a misplaced KMZ without checking the survey datum on the title block.** Misdetected zones (e.g., Indiana East vs. West) look correct at small scale and are wrong at large scale; verify against the title block before overriding.
- **Do not hand-edit `feature` without also setting `folder` and `style`.** The KMZ builder uses all three fields; setting only `feature: polygon` on a layer that the convention engine classified as a route will produce an unstyled, mis-foldered output.
- **Do not skip Step 4** (Google Earth Pro spot check). CRS misdetection is the most common failure and it's silent at the file level — the KMZ opens fine but lands in the wrong place. Always open the output before handing it to the contractor.
- **Do not commit a Tier 3 KMZ without recording the residual error** in your handoff note. The disclaimer below is mandatory for Tier 3 anchors-based output.

## Files

- `SKILL.md` (this file)
- `scripts/inspect_dxf.py` — pipeline stage 1: DXF walk + classification + CRS detection
- `scripts/detect_crs.py` — Tier 1 (`.prj`/`GEODATA`) and Tier 2 (regional defaults) CRS detection
- `scripts/build_anchors.py` — Tier 3 manual-anchor builder + Helmert/affine transforms
- `scripts/layer_conventions.py` — regex → feature/style classification rules
- `scripts/build_kmz.py` — pipeline stage 2: geometry extraction + reprojection + KMZ writer
- `scripts/dxf_crs_defaults.json` — region → EPSG mapping (extend as new regions appear)
- `tests/` — pytest suite covering all modules end-to-end
- `requirements.txt` — pip install targets

## Testing

```bash
cd dxf-to-kmz
pytest tests/ -v
```

All tests use synthetic DXFs generated with `ezdxf` in `tests/conftest.py` — no binary fixtures.
