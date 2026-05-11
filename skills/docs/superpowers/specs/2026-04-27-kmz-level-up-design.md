# Design Spec — `kmz-level-up` Skill

**Date:** 2026-04-27
**Status:** Approved by user, ready for implementation planning
**Audience:** Future Claude executing the implementation plan, plus the human user (Thalf) reviewing the family-of-skills upgrade workflow

---

## Problem

The user produces fiber/utility permit deliverables and currently has four builder skills that convert source artifacts into KMZ files: `cd-route-stitcher` (multi-page CD PDF → vector KMZ), `cd-ground-overlays` (multi-page CD PDF → raster KMZ), `permit-to-kmz` (Sphere/Comcast permit map PDF → drafter KMZ), and `dxf-to-kmz` (DXF → contractor KMZ). They share a deliberate set of conventions: a five-folder hierarchy (Permit Area / Proposed Route / Proposed Infrastructure / Stations & Labels / Existing Infrastructure default-off), a strict color language (red dashed aerial / red solid underground / orange replace / magenta markup / yellow boundary / gray existing), HTML balloon templates, a quality-bar disclaimer, and the `python -m scripts.MODULE` pipeline shape.

What's missing: **the user regularly receives KMZs that already have route geometry and per-route attributes, but don't follow the family conventions.** Sources include third-party desktop tools (Civil 3D, QGIS, ArcGIS Pro exports), contractor / drafter / surveyor hand-builds in Google Earth Pro, and even older outputs of the user's own skills produced before the conventions evolved. Restyling and re-foldering these by hand for every deliverable is tedious and error-prone.

The `kmz-level-up` skill takes any such KMZ in and produces an upgraded KMZ that conforms to the family standard — restyled, re-foldered, enriched with derived features (poles, station ticks, permit-area polygon) when the input doesn't have them, with HTML balloon descriptions and the quality-bar disclaimer stamped into the document description.

## Goals

- **One KMZ in → one upgraded KMZ out** that matches the family deliverable standard — same color language, same folder hierarchy, same balloon templates, same quality-bar disclaimer.
- **Tier-based detection** of input shape: handle outputs from the user's own skills (already mostly conformant), third-party desktop tools (varied attribute schemas, varied styling), and contractor hand-builds (loose folder structure, attributes buried in HTML descriptions).
- **Two-stage workflow** (`inspect_kmz.py` → editable `attribute_mapping.json` → `build_kmz.py`) matching `dxf-to-kmz` exactly. The mapping JSON is the user's override surface for the messy 20% of jobs.
- **Convention-with-override** — first-match-wins regex on attribute names + values handles 80% of jobs zero-touch; the per-job mapping JSON catches the rest.
- **Per-feature derivation knobs** — when the input lacks something the family hierarchy expects (no permit-area polygon, no pole markers, no station ticks), synthesize it by default and let the user disable specific synthesizers via the mapping JSON.
- **Modular transformer pipeline** — each family concern is its own importable, independently-testable module. Adding a new transformer (e.g., for splice case markers, future) is a one-file addition.
- **TDD throughout**, fixtures generated programmatically (no binary fixtures), matching family conventions.

## Non-Goals (v1)

- **Multi-KMZ batch / merge support.** v1 is one KMZ in, one KMZ out. Multi-PRM merge (analog of `cd-route-stitcher/merge_kmz.py`) is a clean future addition.
- **Coordinate reprojection.** KMZ is by definition WGS84 (EPSG:4326). If the input has projected coordinates, the skill fails fast and refers the user to `dxf-to-kmz`.
- **Raster GroundOverlay handling.** Routes-with-attributes is the scope. For raster overlays, use `cd-ground-overlays`.
- **Engineering-grade geometry edits.** Same quality-bar disclaimer the family carries: "Not certified for engineering layout — for that, use the source DWG in Civil 3D."
- **Schema-aware validation against the source authoring tool.** This is a stylistic upgrade, not a data-quality audit.

---

## Architecture

Two-stage pipeline matching `dxf-to-kmz`. Stage 1 inspects the input and produces an editable mapping JSON; stage 2 consumes the input + mapping and runs a sequence of independently-testable transformer modules to produce the upgraded KMZ.

```
input.kmz
   │
   ▼
┌─────────────────────────┐  attribute_mapping.json   ┌─────────────────┐
│   inspect_kmz.py        │─────────────────────────▶ │   (you edit)    │
│  • parse KML            │                            │   if needed     │
│  • walk placemarks      │                            └────────┬────────┘
│  • collect attribute    │                                     │
│    key set              │                                     │
│  • regex name → roles   │                                     │
│  • regex value → styles │                                     │
│  • detect what's        │                                     │
│    already present      │                                     │
└─────────────────────────┘                                     │
                                                                ▼
                                              ┌─────────────────────────────────┐
                                              │       build_kmz.py              │
                                              │  • parse → kml_model            │
                                              │  • apply mapping (overrides)    │
                                              │  • run transformer pipeline:    │
                                              │      1. style_restyler          │
                                              │      2. permit_area_inferer     │
                                              │      3. pole_derivator          │
                                              │      4. station_tick_derivator  │
                                              │      5. folder_refolder         │
                                              │      6. balloon_enricher        │
                                              │      7. doc_describer           │
                                              │  • emit_kml writes output       │
                                              └────────────────┬────────────────┘
                                                               │
                                                               ▼
                                                         upgraded.kmz
```

### Files

- `SKILL.md` — overview, prerequisites, workflow, family color language reference, quality bar, gotchas. Frontmatter follows the family naming/description format.
- `requirements.txt` — `fastkml`, `lxml`, `simplekml`, `shapely`, `pyproj`.
- `scripts/inspect_kmz.py` — stage 1 entrypoint. Walks input KML, calls `parse_kml.py` and `attribute_conventions.py`, emits `attribute_mapping.json` + a stdout summary table.
- `scripts/build_kmz.py` — stage 2 orchestrator. Loads input + mapping, normalizes to `kml_model`, runs the transformer sequence, writes output via `emit_kml.py`.
- `scripts/parse_kml.py` — Tier 1: fastkml read. Tier 2: lxml direct fallback when fastkml chokes (custom namespaces, malformed XML, embedded HTML attribute storage).
- `scripts/emit_kml.py` — simplekml write (matches `cd-route-stitcher`).
- `scripts/kml_model.py` — internal normalized representation. Dataclasses: `Placemark`, `LineStringFeature`, `PointFeature`, `PolygonFeature`, each with `id`, `name`, `attributes` (dict), `geometry`, `style_role` (enum), `folder_path` (list[str]).
- `scripts/attribute_conventions.py` — first-match-wins regex rules for attribute name → role and attribute value → style_role. Existing-infrastructure check fires before route classification (analog of `dxf-to-kmz/layer_conventions.py`).
- `scripts/attribute_defaults.json` — institutional knowledge accumulator: per-drafter / per-region attribute name conventions. Versioned with the skill.
- `scripts/transformers/__init__.py`
- `scripts/transformers/style_restyler.py` — assigns family `<Style>` to every LineString based on `style_role`. Idempotent.
- `scripts/transformers/permit_area_inferer.py` — buffered convex hull around routes when no boundary polygon exists in input. Skipped if input has one or `derive_permit_area: false`.
- `scripts/transformers/pole_derivator.py` — extracts pole point markers from polyline vertices (deflection threshold) on aerial-classified segments. Skipped if input has poles or `derive_poles: false`.
- `scripts/transformers/station_tick_derivator.py` — emits tick points at every chainage value when chainage attribute is mapped. Skipped if no chainage mapping or `derive_station_ticks: false`.
- `scripts/transformers/folder_refolder.py` — moves placemarks into the family hierarchy based on `style_role` and origin (existing/proposed). Existing folder gets `<visibility>0</visibility>` and folded.
- `scripts/transformers/balloon_enricher.py` — generates HTML `<description>` from attributes for each placemark. Skipped per-placemark if input has a non-empty description and `preserve_existing_descriptions: true`.
- `scripts/transformers/doc_describer.py` — writes top-level `<Document><description>` with input source filename, classification summary, derivation log, CRS provenance line, and the quality-bar disclaimer.
- `tests/conftest.py` — synthetic KMZ fixture builders: `make_kmz_civil3d_style()`, `make_kmz_qgis_style()`, `make_kmz_handbuilt()`, `make_kmz_already_conformant()`. No binary fixtures.
- `tests/test_*.py` — per-module unit tests + end-to-end test. (See Testing section.)

### Prerequisites

```bash
pip install fastkml lxml simplekml shapely pyproj
```

- `fastkml` — KML/KMZ reader (Tier 1).
- `lxml` — direct XML fallback parsing (Tier 2) and namespace-aware attribute extraction.
- `simplekml` — KMZ writer (matches `cd-route-stitcher`, `dxf-to-kmz`).
- `shapely` — geometry operations (buffered convex hull for permit-area inference, vertex deflection for pole derivation, simplification).
- `pyproj` — CRS sanity check (verify input is WGS84-ish; bail with clear error if projected).

---

## Attribute Detection — Convention Engine

### Strategy

Standard names with regex fallback (option B from brainstorming). First-match-wins regex against attribute names → roles. Within each role, first-match-wins regex against attribute values → `style_role`. Existing-infrastructure check fires before route classification.

### Built-in name rules (`scripts/attribute_conventions.py`)

| Rule pattern (case-insensitive regex) | Role |
|---|---|
| `.*type.*` / `.*method.*` / `.*const.*type.*` / `.*mat.*type.*` | `construction_type` |
| `.*chain.*` / `.*\bsta\b.*` / `.*station.*` | `chainage` |
| `.*span.*` / `.*length.*` / `.*\bft\b.*` | `span_length` |
| `.*owner.*` / `.*\bprm\b.*` / `.*entity.*` | `owner` |
| `.*sheet.*` / `.*\bsht\b.*` / `.*\bfid\b.*` | `sheet_id` |
| `.*existing.*` / `.*\bex\b.*` (boolean values) | `existing_flag` |

### Built-in value rules (within `construction_type`)

| Rule pattern | `style_role` |
|---|---|
| `AERIAL` / `OVH` / `OVERHEAD` / `OVERLASH` / `STRAND` | `aerial` |
| `UNDERGROUND` / `\bUG\b` / `BORE` / `TRENCH` / `DIRECTIONAL` | `underground` |
| `REPLACE` / `RPLC` | `replace` |
| `MARKUP` / `REVISION` / `REDLINE` / `\bRED\b` | `markup` |

### Existing-first ordering

A LineString with name matching `EX_*` or attribute `existing: true` (any-truthy) is classified as `style_role: existing` regardless of any construction-type match. This mirrors the family pattern (`dxf-to-kmz/layer_conventions.py`) and prevents `EX_FIBER_AERIAL` from being styled as a fresh aerial route.

### Adding a new drafter convention

A one-line addition to `attribute_conventions.py`:

```python
NAME_RULES.insert(0, NameRule(r".*MY_NEW_PATTERN.*", "construction_type"))
```

`attribute_defaults.json` accumulates institutional knowledge per region/drafter:

```json
{
  "civil3d_2025": {"type_attr": "TYPE", "chain_attr": "STA"},
  "qgis_export":  {"type_attr": "type", "chain_attr": "station_m"}
}
```

Substring match against KMZ filename selects the default block; loaded via `--defaults <key>` flag if filename heuristic fails.

---

## `attribute_mapping.json` — Schema

```json
{
  "input_summary": {
    "kmz_path": "input.kmz",
    "linestring_count": 12,
    "polygon_count": 1,
    "point_count": 0,
    "detected_attribute_keys": ["TYPE", "STA", "SPAN_FT", "OWNER", "SHEET_ID"],
    "already_has_permit_area": true,
    "already_has_poles": false,
    "already_has_station_ticks": false
  },
  "attribute_roles": {
    "TYPE": "construction_type",
    "STA": "chainage",
    "SPAN_FT": "span_length",
    "OWNER": "owner",
    "SHEET_ID": "sheet_id"
  },
  "value_classifications": {
    "construction_type": {
      "AERIAL": "aerial",
      "OVERLASH": "aerial",
      "UG": "underground",
      "BORE": "underground",
      "TRENCH": "underground",
      "REPLACE": "replace"
    }
  },
  "derive": {
    "permit_area": true,
    "permit_area_buffer_ft": 50,
    "poles": true,
    "pole_deflection_deg": 5,
    "station_ticks": true
  },
  "balloon": {
    "preserve_existing_descriptions": true,
    "display_attributes": ["TYPE", "STA", "SPAN_FT", "OWNER", "SHEET_ID"]
  },
  "placemarks": [
    {
      "id": "fid_1",
      "name": "Aerial Run 1",
      "auto_role": "aerial",
      "override_role": null,
      "publish": true
    },
    {
      "id": "fid_2",
      "name": "Mystery Line",
      "auto_role": "unmapped",
      "override_role": null,
      "publish": false,
      "_note": "Unmapped — TYPE attribute value 'XYZ' didn't match any rule. Set override_role + publish:true to include."
    }
  ]
}
```

The `placemarks` list is the per-feature override surface; the user can pin any individual placemark's role. The `derive` block toggles each transformer's synthesizer behavior.

---

## Family Color Language (`style_restyler` output)

Matches `dxf-to-kmz` exactly so downstream consumers see the same visual language across deliverables.

| `style_role` | Color (KML aabbggrr) | Pattern | Folder destination |
|---|---|---|---|
| `aerial` | red `ff0000ff` | dashed | `Proposed Route/Aerial` |
| `underground` | red `ff0000ff` | solid | `Proposed Route/Underground` |
| `replace` | orange `ff0080ff` | dashed | `Proposed Route/Replace` |
| `markup` | magenta `ffff00ff` | dashed | `Proposed Route/Markup` |
| `existing` | gray `ff808080` | (preserve from input) | `Existing Infrastructure` (visibility=0, folded) |
| `boundary` | line `ff00ffff`, fill `4000ffff` | (polygon) | `Permit Area` (yellow translucent) |
| `pole` | red dot icon | (point) | `Proposed Infrastructure/Poles` |
| `vault` | blue square icon | (point) | `Proposed Infrastructure/Vaults` |
| `station` | small text label | (point) | `Stations & Labels` (folded) |
| `unmapped` | gray `ff404040` | (preserve) | `Unmapped Routes` (visibility=0, flagged in doc description) |

Idempotency: `style_restyler` replaces inline styles with shared family `<Style>` references, so re-running on a previously-upgraded KMZ produces a byte-equivalent output (same `<Style>` ids, same references).

---

## KMZ Output Structure

```
[Job name from input filename]                ← document name
│
├── ⬛ Permit Area                              ← yellow polygon (visible)
│   └── (input polygon OR inferred buffered hull, labeled accordingly)
│
├── 📐 Proposed Route                           ← visible folder
│   ├── Aerial    (dashed red)
│   ├── Underground   (solid red)
│   ├── Replace   (dashed orange)
│   └── Markup    (dashed magenta)
│
├── 🔵 Proposed Infrastructure                  ← visible folder
│   ├── Poles    (red dot icons)
│   └── Vaults   (blue square icons)
│
├── 📍 Stations & Labels                        ← visible, folded
│
├── ❓ Unmapped Routes                          ← visibility OFF, flagged
│   └── (any LineString that didn't match a style_role)
│
└── 🌫️ Existing Infrastructure                  ← visibility OFF, folded
    └── (any placemark named EX_* or with existing: true)
```

### Style choices, justified

- **Yellow translucent fill** for permit area: matches USACE/DOT permit-exhibit convention; visible but doesn't obscure the route inside.
- **Red dashed = aerial, red solid = underground:** matches `cd-route-stitcher` and `dxf-to-kmz`.
- **Default visibility:** Permit Area + Proposed Route + Proposed Infrastructure ON. Existing OFF + folded. Stations folded but visible-when-expanded. Unmapped OFF + flagged in doc description.
- **Inferred Permit Area** is labeled `Permit Area (inferred — verify before submittal)` so the reviewer can never confuse a buffered-hull synthesis for an authored boundary.
- **Document `<description>`** carries the input filename, classification summary, derivation log, CRS provenance line, and quality-bar disclaimer.
- **Geometry uses `<altitudeMode>clampToGround</altitudeMode>`** unless input explicitly set otherwise; preserve user intent if `relativeToGround` or `absolute` was authored.

---

## Quality Bar

Printed in `SKILL.md` and embedded in every upgraded KMZ's document description:

> *"Upgraded from input KMZ (`<input filename>`) to family deliverable standard. Color language and folder hierarchy match the cd-route-stitcher / dxf-to-kmz / permit-to-kmz family. Inferred features (permit area, poles, station ticks) are flagged in their folder names. Not certified for engineering layout — for that, use the source DWG in Civil 3D."*

---

## Failure Modes (documented in SKILL.md "Gotchas")

| Symptom | Likely cause | Fix |
|---|---|---|
| `inspect_kmz.py` fails: "No attributes found" | Input KMZ has only geometry, no ExtendedData | Use a builder skill (cd-route-stitcher / dxf-to-kmz / permit-to-kmz) instead — this skill is for KMZs that already have route attributes |
| `inspect_kmz.py` fails: "Non-WGS84 coords detected" | Input has projected coords (e.g., State Plane feet); KMZ should always be EPSG:4326 | Use `dxf-to-kmz` for projected sources; this skill is for KMZs already in lat/lon |
| Most LineStrings end up `unmapped` | Construction-type values don't match the value rules | Edit `attribute_mapping.json` `value_classifications` block to map this drafter's specific values |
| Permit Area inferred when one already exists in input | Existing polygon is on an unrecognized layer/folder | Edit `attribute_mapping.json` `placemarks` list to override the polygon's `auto_role` to `boundary`, set `derive.permit_area: false` |
| Poles derived in wrong locations | Aerial polylines have spurious vertex deflections (CAD tessellation artifacts) | Increase `derive.pole_deflection_deg` (default 5°) or set `derive.poles: false` and add poles manually in the source KMZ |
| HTML balloon templates obscure user-authored descriptions | `preserve_existing_descriptions: true` failed because input descriptions were empty strings (not absent) | Edit transformer logic to also skip empty-string descriptions, or set `balloon.preserve_existing_descriptions: false` if templates are wanted everywhere |
| Output is huge | Input has dense polylines from CAD tessellation | Add `--simplify <degrees>` flag (Douglas–Peucker tolerance in lat/lon degrees; ~0.000001 = ~10cm) |

## Known Limitations (v1)

- **Single KMZ in / single KMZ out.** Multi-KMZ batch / merge support deferred to v2 (analog of `cd-route-stitcher/merge_kmz.py`).
- **No coordinate reprojection.** Input must already be WGS84 lat/lon. For projected sources, use `dxf-to-kmz`.
- **Dashed polylines** in KML are not natively supported by Google Earth Pro — width and color honored, dashed/solid differentiation falls back to folder-name disambiguation (`Aerial` vs `Underground` folder labels).
- **HTML balloons** use a fixed template; per-feature customization beyond `display_attributes` requires editing `balloon_enricher.py`.
- **Existing-infrastructure detection** keys on placemark name (`EX_*`) and `existing` attribute. Drafters who use other conventions need a per-job override.
- **Pole derivation** uses vertex deflection only; doesn't account for spans (i.e., it can't synthesize poles between two collinear points). For fiber jobs this is acceptable; for survey-grade pole locations, derive poles in the source authoring tool.

---

## Workflow (for SKILL.md)

```bash
# Step 1: inspect the input KMZ, propose attribute mapping
cd kmz-level-up
python -m scripts.inspect_kmz path/to/input.kmz --output attribute_mapping.json

# Step 2: edit attribute_mapping.json IF inspect output flagged unmapped routes,
#         missed an attribute mapping, or you want to disable a derivation knob.
#         Most jobs require zero edits.

# Step 3: build the upgraded KMZ
python -m scripts.build_kmz path/to/input.kmz attribute_mapping.json --output upgraded.kmz

# Step 4: validate in Google Earth Pro
# - Folder hierarchy matches the family standard (Permit Area / Proposed Route / etc.)
# - Aerial routes dashed red, underground solid red
# - Existing Infrastructure folder folded + off by default
# - Document description shows input source, classification summary, quality-bar disclaimer
# - Inferred Permit Area (if applicable) is labeled with "(inferred — verify before submittal)"
```

## Validation (for the implementation phase)

A representative input KMZ (when available) should produce:

- KMZ that opens in Google Earth Pro without errors
- Folder hierarchy matches the family standard exactly
- Every LineString styled per its `style_role` (verified by spot-checking aerial=dashed, underground=solid, replace=orange, markup=magenta)
- Existing Infrastructure folder is folded + visibility=0
- Document description shows input filename, attribute mapping summary, derivation log, quality-bar disclaimer
- Re-running `build_kmz.py` on its own output is byte-equivalent (idempotency check)
- For inputs with no Permit Area polygon: a yellow translucent buffered hull appears, labeled with "(inferred — verify before submittal)"
- For inputs with no poles but with aerial-classified routes: pole point markers appear at vertex-deflection points (>5° default)
- For inputs with chainage-mapped attributes: station tick points appear at every chainage value

## Open Questions for Implementation

- **Sample inputs.** The user did not supply representative input KMZs during brainstorming. The implementation phase should request 1-2 representative samples from each of the three input categories (own-skills output, third-party tool export, contractor hand-build) to validate the regex rules in `attribute_conventions.py` and the buffered-hull buffer default (50 ft).
- **HTML balloon template style.** Should match the visual style of any existing family balloon templates (or establish a new one if none exist yet). Implementation should check `cd-route-stitcher` / `dxf-to-kmz` / `permit-to-kmz` for any pre-existing template before authoring a new one.
- **fastkml vs lxml split point.** When does fastkml fail and lxml take over? Implementation should test against malformed-but-loadable KMZs from Google Earth Pro hand-builds and codify the fallback trigger.
- **Pole-deflection threshold.** Default 5° is a guess; implementation should validate against a representative aerial route and tune if false-positives or false-negatives are common.
- **Idempotency contract.** Output of `build_kmz.py` fed back through `inspect_kmz.py` + `build_kmz.py` should produce identical output. Implementation should include a round-trip test asserting this.

---

## Decision Log

| Decision | Rationale |
|---|---|
| Two-stage workflow with editable mapping JSON | Matches `dxf-to-kmz` exactly; user picked B in brainstorming Q3 |
| Standard attribute names with regex fallback | Matches `dxf-to-kmz/layer_conventions.py` analog; user picked B in Q4 |
| Per-feature derivation knobs in mapping JSON | User picked D in Q5 (hybrid, controllable) |
| Pipeline of named transformers (Approach 3) | User picked Approach 3; modular, TDD-friendly, per-feature knobs map 1:1 to which transformer runs |
| fastkml read + lxml fallback | fastkml handles 95% of well-formed KML; lxml direct catches the messy 5% (Google Earth Pro hand-builds, custom namespaces) |
| simplekml for write | Matches `cd-route-stitcher` and `dxf-to-kmz`; consistent emit pattern across the family |
| Buffered convex hull (50 ft default) for permit-area inference | Simple, deterministic, easily auditable; user can override buffer in mapping JSON |
| Pole derivation by vertex deflection (5° default) | Captures real angle changes (where actual poles would be); avoids false positives from straight-run tessellation noise |
| Per-job override at the placemark level | User can pin any individual feature's role without editing global rules; matches the "convention with override" pattern |
| Single KMZ in / out for v1 | Matches user's stated common case; multi-KMZ merge deferred to v2 |
| `attribute_defaults.json` lives in skill folder, versioned | Per-drafter / per-region attribute conventions accumulate as institutional knowledge over time, same as `dxf_crs_defaults.json` |
| Existing infrastructure default-off | Matches family pattern; reviewer focus is the proposed work, not existing context |
| Inferred features explicitly labeled | "Permit Area (inferred — verify before submittal)" prevents reviewers from mistaking a synthesized hull for an authored boundary |
| Idempotency required | Re-running on already-upgraded output should produce byte-equivalent results — necessary for stable diffs and re-pass workflows |
