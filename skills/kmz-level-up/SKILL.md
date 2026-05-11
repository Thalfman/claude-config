---
name: kmz-level-up
description: >
  Use when you have an existing KMZ with attributed geometry (route LineStrings or polygons) that needs to be upgraded to the family deliverable standard. Trigger on "level up this KMZ", "upgrade this Google Earth file", "apply the standard styling", "make this KMZ deliverable-ready", "fix the folder structure on this KMZ". Two pipelines: route-dominant inputs apply the family color language (red dashed aerial, red solid underground, orange replace, magenta markup) and the family folder hierarchy with derived poles / station ticks / permit-area polygons; polygon-dominant inputs (Sphere / ESRI / ArcGIS dashboard exports) collapse same-permit polygons into MultiGeometry placemarks under attribute-driven folders (e.g., JB → PRM). Handles attributes in <ExtendedData> or in HTML <table> blocks inside <description>. Two-stage workflow with editable attribute_mapping.json between inspect and build.
---

# KMZ Level Up

## What this skill does

Takes any KMZ with attributed geometry (route LineStrings, or polygons) and produces an upgraded KMZ that matches the family deliverable standard (`cd-route-stitcher`, `dxf-to-kmz`, `permit-to-kmz`). The output emphasizes:

- The **family color language**: red dashed aerial / red solid underground / orange replace / magenta markup / bright green boundary / gray existing
- The **family folder hierarchy** for route-dominant input: Permit Area / Proposed Route / Proposed Infrastructure / Stations & Labels / Existing Infrastructure (default-off)
- An **attribute-driven hierarchy** for polygon-dominant input (e.g., JB folder → PRM placemark, with same-permit polygons merged into a single MultiGeometry placemark)
- **Derived features** when the input lacks them: pole markers from vertex deflection on aerial routes, station ticks from chainage attributes, permit-area polygon from buffered route hull
- **HTML balloon templates** rendered from attributes (Null/empty fields suppressed)
- A **minimal document description** stamped with input filename + CRS only (no commentary, summaries, or disclaimers)

## Two input shapes

The skill auto-detects which path applies based on geometry type:

1. **Route-dominant** (LineStrings + attributes): the original family-folder pipeline. Inputs from Civil 3D / QGIS / ArcGIS / `cd-route-stitcher` / `dxf-to-kmz` / `permit-to-kmz` / hand-built Google Earth KMZs.
2. **Polygon-dominant** (polygons only, no LineStrings): an attribute-driven hierarchy pipeline. Inputs from Sphere / ESRI ArcGIS Online dashboard exports where each polygon is a permit area, and attributes live in HTML `<table>` blocks inside `<description>` rather than `<ExtendedData>`. The skill auto-emits a `polygon_handling` block in `attribute_mapping.json` that drives folder grouping, polygon merging, and styling.

## When to use

Use whenever you have an existing KMZ with attributed geometry and want any of:

- A KMZ that follows the family standard regardless of source authoring tool
- Re-pass on an old skill output now that conventions have evolved
- Conversion of a Civil 3D / QGIS / ArcGIS export to family format
- Cleanup of a contractor / drafter hand-built KMZ
- A Sphere / ESRI dashboard export turned into a deliverable-quality, JB-organized KMZ

If the input is a multi-page CD PDF, use `cd-route-stitcher` (vector) or `cd-ground-overlays` (raster). If the input is a Sphere/Comcast permit map PDF, use `permit-to-kmz`. If the input is a DXF, use `dxf-to-kmz`. **This skill is for KMZs that already have geometry + attributes** (in either `<ExtendedData>` or HTML-table `<description>`).

## Prerequisites

```bash
pip install -r requirements.txt
# or
pip install lxml simplekml shapely
```

## Workflow

**Run all scripts from the `kmz-level-up/` folder.** The `scripts/` package only resolves when the skill folder is your CWD.

The pipeline is **inspect -> edit `attribute_mapping.json` -> build**. Always run Step 1 first; never skip directly to `build_kmz.py` -- the mapping JSON is what tells the builder which attributes mean what.

### Step 1: Inspect the input KMZ

```bash
cd kmz-level-up
python -m scripts.inspect_kmz path/to/input.kmz --output attribute_mapping.json
```

This walks the input, classifies each detected attribute name to a role (construction_type, chainage, span_length, owner, sheet_id), classifies each LineString to a `style_role` (aerial / underground / replace / markup / existing / unmapped), and writes `attribute_mapping.json`.

**Stdout summary** lists detected attribute keys, classifications, and per-placemark auto-roles. Most jobs require zero edits to the JSON.

### Step 2 (optional): Edit `attribute_mapping.json`

If the inspect output flagged unmapped routes, missed an attribute mapping, or you want to disable a derivation knob:

- **Add or override an attribute role:** edit the `attribute_roles` block.
- **Pin a specific placemark's classification:** find it in the `placemarks` list, set `override_role` (e.g., `"override_role": "aerial"`).
- **Drop a placemark:** set `"publish": false` for it in `placemarks`.
- **Disable a derivation:** set `derive.permit_area` / `derive.poles` / `derive.station_ticks` to `false`.
- **Tune buffer / threshold:** edit `derive.permit_area_buffer_ft` (default 50) or `derive.pole_deflection_deg` (default 5).

#### Polygon-dominant input: editing `polygon_handling`

When the input is polygon-only, the inspector auto-emits a `polygon_handling` block. Defaults usually work; tune as needed:

```json
"polygon_handling": {
  "enabled": true,
  "top_folder_name": null,
  "group_by": ["JBNumber"],
  "merge_at": "Unique_ID",
  "folder_label_templates": {"JBNumber": "{value}"},
  "placemark_label_template": "{Unique_ID} - {Jurisdiction}",
  "style_by": "Build_Status",
  "default_style": {"line": "ff00ff00", "fill": "8000ff00", "line_width": 4},
  "status_styles": {}
}
```

- `enabled`: master switch. Set `false` to fall back to the route-style pipeline (all polygons land in `Permit Area`).
- `top_folder_name`: optional wrapper folder above the `group_by` levels. `null` = no wrapper (the JB folders sit directly under the document).
- `group_by`: ordered list of attribute keys -- one folder level per key.
- `merge_at`: attribute key that identifies a single logical entity. All polygons sharing this value within the same `group_by` group are merged into one MultiGeometry placemark. Set to `null` to keep each polygon as its own placemark.
- `folder_label_templates`: map of `attribute_key` -> template string for the folder name at that level. Tokens: `{value}` (the group key's own value) and `{AnyAttrKey}` (any other attribute from the first member). Null/empty values are suppressed and orphan separators (` - `, `[]`) cleaned up.
- `placemark_label_template`: template for the merged placemark's name. Same token rules.
- `style_by`: attribute key whose value selects an entry in `status_styles`. Polygons get a `style_override` with the matching dict (or `default_style` when unmatched).
- `status_styles`: map of `attribute_value` -> `{line, fill, line_width}`. KML colors are AABBGGRR.
- `default_style`: applied when `status_styles` doesn't contain the polygon's value (or when `style_by` is null).

### Step 3: Build the upgraded KMZ

```bash
python -m scripts.build_kmz path/to/input.kmz attribute_mapping.json --output upgraded.kmz
```

This loads the input + mapping, parses to the internal model, runs the 7-transformer pipeline, and writes the upgraded KMZ.

### Step 4: Validate in Google Earth Pro

Spot-check:
- Folder hierarchy matches the family standard
- Aerial routes dashed red, underground solid red
- Existing Infrastructure folder folded + visibility off
- Document description shows ONLY input filename + CRS (no skill commentary)

## KMZ output structure

### Route-dominant input

```
[Job name from input filename]
+- Permit Area                         (bright green translucent polygon, visible)
+- Proposed Route                      (visible)
|  +- Aerial   (dashed red)
|  +- Underground   (solid red)
|  +- Replace   (dashed orange)
|  +- Markup    (dashed magenta)
+- Proposed Infrastructure             (visible)
|  +- Poles
|  +- Vaults
+- Stations & Labels                   (visible, folded)
+- Unmapped Routes                     (visibility OFF, flagged)
+- Existing Infrastructure             (visibility OFF, folded)
```

### Polygon-dominant input

Hierarchy is driven by `polygon_handling.group_by` and `merge_at`. Default for Sphere/ESRI exports:

```
[Job name from input filename]
+- JB0002131476                        (bright green boundary placemarks for each PRM)
|  +- PRM0001321537 - MIAMI HIWAY      (1 placemark, possibly with MultiGeometry)
|  +- PRM0001379080 - INDOT
+- JB0002131506
|  +- PRM0001317463 - INDOT
|  +- ...
+- ...
```

Same-permit polygons collapse into one placemark with a MultiGeometry, so a 102-row export with 52 unique permits produces ~52 placemarks instead of 102. Each placemark gets the Build_Status-driven style (defaults to bright green `#00FF00` outline + 50% fill, the satellite-pop default).

The document description carries only input filename + CRS — no classification summaries, derivation logs, or disclaimers. Deliverables stay clean.

## Family color language

| `style_role` | Color | Pattern | Folder destination |
|---|---|---|---|
| `aerial` | red `ff0000ff` | dashed | `Proposed Route/Aerial` |
| `underground` | red `ff0000ff` | solid | `Proposed Route/Underground` |
| `replace` | orange `ff0080ff` | dashed | `Proposed Route/Replace` |
| `markup` | magenta `ffff00ff` | dashed | `Proposed Route/Markup` |
| `existing` | gray `ff808080` | preserve | `Existing Infrastructure` (visibility=0) |
| `boundary` | bright green `#00FF00` line + 50%-fill | n/a | `Permit Area` |
| `pole` | red dot | n/a | `Proposed Infrastructure/Poles` |
| `vault` | blue square | n/a | `Proposed Infrastructure/Vaults` |
| `station` | small text label | n/a | `Stations & Labels` (folded) |
| `unmapped` | gray | preserve | `Unmapped Routes` (visibility=0) |

Matches `dxf-to-kmz` / `cd-route-stitcher` exactly so downstream consumers see the same visual language.

## Attribute conventions

First-match-wins regex against attribute names. Order matters; existing check fires before route classification.

| Pattern | Role |
|---|---|
| `.*const.*type.*` / `.*method.*` / `.*type.*` | construction_type |
| `.*chain.*` / `.*\bsta\b.*` / `.*station.*` | chainage |
| `.*span.*` / `.*length.*` / `.*\bft\b.*` | span_length |
| `.*owner.*` / `.*\bprm\b.*` / `.*entity.*` | owner |
| `.*sheet.*` / `.*\bsht\b.*` | sheet_id |
| `.*existing.*` / `^ex$` | existing_flag |

Construction-type values: `AERIAL` / `OVH` / `OVERHEAD` / `OVERLASH` / `STRAND` -> aerial. `UNDERGROUND` / `UG` / `BORE` / `TRENCH` / `DIRECTIONAL` -> underground. `REPLACE` / `RPLC` -> replace. `MARKUP` / `REVISION` / `REDLINE` -> markup.

To add a new drafter convention, edit `scripts/attribute_conventions.py`:

```python
NAME_RULES.insert(0, NameRule(re.compile(r"my_new_pattern", re.I), "construction_type"))
```

## Deliverable cleanliness

The skill intentionally emits no commentary inside the KMZ:
- No quality-bar disclaimer in the document description
- No "(inferred -- verify before submittal)" suffix on the Permit Area folder name
- No classification summary, derivation log, or unmapped count

Document description = input filename + CRS only. Anything Claude or this skill wants to flag belongs in the chat reply, not in the artifact. If you need to attach a disclaimer for a specific job, hand-edit the description after the build.

## Known limitations

- **Single KMZ in / out for v1.** Multi-KMZ batch / merge is deferred to v2.
- **No coordinate reprojection.** Input must already be WGS84 (EPSG:4326). Projected sources fail fast with a clear error pointing at `dxf-to-kmz`.
- **Dashed polylines** in KML are not natively supported by Google Earth Pro -- width and color are honored; folder names disambiguate Aerial vs Underground when the line style alone doesn't.
- **HTML balloons** use a fixed template; per-feature customization beyond `display_attributes` requires editing `balloon_enricher.py`.
- **Existing-infrastructure detection** keys on placemark name (`EX_*`) and `existing` attribute. Drafters who use other conventions need a per-job override in the placemarks list.
- **Pole derivation** uses vertex deflection only; doesn't synthesize poles between two collinear points. For survey-grade pole locations, derive in the source authoring tool.

## Gotchas

- **`inspect_kmz.py` fails: "No attributes found and no polygons to organize"** -- input KMZ has only LineString geometry, no ExtendedData, no HTML-table descriptions. Use a builder skill (cd-route-stitcher / dxf-to-kmz / permit-to-kmz) instead.
- **`inspect_kmz.py` fails: "Non-WGS84 coords detected"** -- input has projected coordinates. Use `dxf-to-kmz` for projected sources.
- **Most LineStrings end up `unmapped`** -- construction-type values don't match any value rule. Edit `attribute_mapping.json` `value_classifications.construction_type` to map this drafter's values.
- **Permit Area inferred when one already exists in input** -- input polygon is named non-conventionally. Edit `attribute_mapping.json` `placemarks` list to set the polygon's `override_role: "boundary"`, set `derive.permit_area: false`.
- **Poles derived in wrong locations** -- aerial polylines have CAD-tessellation vertex noise. Increase `derive.pole_deflection_deg` (default 5) or set `derive.poles: false`.
- **Output is huge** -- input has dense polylines. Add a polyline simplification step in CAD before exporting.
- **`merge_at` picks the wrong attribute on a Sphere export** -- inspect uses regex priority to pick `Unique_ID` (stable PRM key) over `Permit_Number` (often "Null" or "BLANKET PERMIT"). If your drafter uses a different convention, edit `polygon_handling.merge_at` directly.
- **Polygons end up under "(unknown)" folder** -- `polygon_handling.group_by` attribute is missing or "Null" on those records. Either fix the source data or set `polygon_handling.enabled: false` to fall back to the single Permit Area folder.
- **HTML balloon attributes don't appear** -- the input description didn't use a standard `<tr><td>Field</td><td>Value</td>` two-column table. Inspect `parse_kml._parse_html_table_attrs` and extend the regex if your source uses a different table shape.

## Red flags (do not do these)

- **Do not skip `inspect_kmz.py`.** The builder requires `attribute_mapping.json` -- running `build_kmz.py` first will fail.
- **Do not run scripts from a parent directory** or with absolute paths. The `scripts/` package only resolves when `kmz-level-up/` is your CWD.
- **Do not skip Step 4** (Google Earth Pro spot check). Misclassifications are silent at the file level -- the upgraded KMZ opens fine but might style routes incorrectly.
- **Do not commit an upgraded KMZ with inferred Permit Area without verifying it.** The inferred hull is a buffered convex hull, not an authored boundary; reviewers must confirm before submittal.

## Files

- `SKILL.md` (this file)
- `scripts/inspect_kmz.py` -- pipeline stage 1: parse + classify + write `attribute_mapping.json` (auto-emits `polygon_handling` for polygon-dominant inputs)
- `scripts/build_kmz.py` -- pipeline stage 2: orchestrator, runs the 8-transformer pipeline
- `scripts/parse_kml.py` -- lxml-based KML/KMZ parser; falls back to HTML-table description parsing when ExtendedData is absent
- `scripts/emit_kml.py` -- simplekml writer (CDATA-wraps balloons, emits MultiGeometry for merged polygons)
- `scripts/kml_model.py` -- internal normalized representation (dataclasses + StyleRole enum + polygon `extra_parts` / `style_override`)
- `scripts/attribute_conventions.py` -- first-match-wins regex rules
- `scripts/transformers/` -- eight independently-testable transformer modules (now includes `polygon_merger`)
- `tests/` -- pytest suite covering all modules + end-to-end fixture-based tests (route-style and Sphere-style)
- `requirements.txt` -- pip install targets

## Testing

```bash
cd kmz-level-up
pytest tests/ -v
```

All tests use synthetic KMZs generated programmatically in `tests/conftest.py` -- no binary fixtures.
