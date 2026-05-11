# Design Spec — `dxf-to-kmz` Skill

**Date:** 2026-04-27
**Status:** Approved by user, ready for implementation planning
**Audience:** Future Claude executing the implementation plan, plus the human user (Thalf) reviewing the contractor handoff workflow

---

## Problem

The user produces fiber/utility permit packages and currently has three skills that convert source artifacts (PDFs of construction drawings, permit maps) into KMZ deliverables: `cd-route-stitcher`, `cd-ground-overlays`, and `permit-to-kmz`. Drafters and surveyors regularly hand over **DXF files** as well, and there is no skill to take those into a clean KMZ that contractors can open in Google Earth to understand:

1. The proposed route alignment (aerial vs underground)
2. **Where they are permitted to work** (the permit boundary / work area / ROW limits)
3. Proposed infrastructure (poles, vaults) they will be installing
4. Optionally, existing infrastructure for context (off by default to keep the file readable)

The deliverable must "look clean" — defaults visible, defaults toggleable, default-off for noise.

## Goals

- **One DXF in → one contractor-ready KMZ out** for the common case.
- Graceful degradation when CRS or layer info is incomplete (tier-based fallback patterns matching the user's existing skills).
- Conventions the user can extend (per-region CRS defaults, per-drafter layer rules) without editing Python.
- Output structure consistent with `cd-route-stitcher` and `permit-to-kmz` — same color language, same folder hierarchy intuition.

## Non-Goals (v1)

- **Multi-DXF JB-level merge** (`merge_kmz.py`). User confirmed one DXF per deliverable "most of the time"; documented as a clean future addition.
- **Engineering-grade layout fidelity.** Same quality-bar disclaimer the other skills carry: "Not certified for engineering layout — for that, use the source DWG in Civil 3D."
- **Curve precision** beyond polyline tessellation; **hatch fills**; **XREF resolution**; **3D/Z-coord** preservation.

---

## Architecture

Five Python scripts in `scripts/`, plus `SKILL.md`. Pipeline mirrors `cd-route-stitcher` and `permit-to-kmz` — distinct stages with clear inputs/outputs so individual stages can be re-run or replaced.

```
DXF in
  │
  ▼
┌─────────────────┐   layer_mapping.json   ┌─────────────────┐
│ inspect_dxf.py  │──────────────────────▶ │   (you edit)    │
│  • lists layers │                        │   if needed     │
│  • entity counts│                        └────────┬────────┘
│  • CRS guess    │                                 │
│  • regex-based  │                                 │
│    default map  │                                 │
└────────┬────────┘                                 │
         │                                          │
         ▼ (CRS Tier 3 only)                        │
┌─────────────────┐    anchors.json                 │
│build_anchors.py │────────────┐                    │
│  • 2+ DXF↔latlon│            │                    │
│    control pts  │            │                    │
└─────────────────┘            ▼                    ▼
                       ┌──────────────────────────────────┐
                       │          build_kmz.py            │
                       │  • applies CRS or anchors        │
                       │  • applies layer mapping         │
                       │  • applies conventions/styles    │
                       │  • emits clean folder structure  │
                       └────────────────┬─────────────────┘
                                        │
                                        ▼
                                  contractor.kmz
```

### Files

- `SKILL.md` — overview, prerequisites, workflow, quality bar, gotchas. Frontmatter follows the established naming/description format used by `permit-to-kmz`.
- `scripts/inspect_dxf.py` — reads DXF with `ezdxf`, prints layer summary with entity counts, runs CRS detection (Tier 1) and convention engine, writes `layer_mapping.json`.
- `scripts/detect_crs.py` — standalone CRS detector (callable from `inspect_dxf.py` or directly). Looks for `.prj` sidecar → `GEODATA` xrecord → header hints → `dxf_crs_defaults.json` → prompts.
- `scripts/build_anchors.py` — interactive anchor-builder for Tier 3 (local-coordinate jobs). Prompts user for 2+ DXF↔lat/lon pairs, computes Helmert (2 anchors) or affine (3+ anchors) transform, writes `anchors.json`.
- `scripts/layer_conventions.py` — module of regex rules + default styles, importable from `inspect_dxf.py`. One-line edits to add a new drafter convention.
- `scripts/build_kmz.py` — consumes DXF + `layer_mapping.json` + (CRS-from-mapping OR `anchors.json`), reprojects with `pyproj`, emits styled KMZ via `simplekml`.
- `scripts/dxf_crs_defaults.json` — region → EPSG mapping, edited by user. Versioned with the skill so institutional knowledge accumulates.

### Prerequisites

```bash
pip install ezdxf pyproj simplekml shapely
```

- `ezdxf` — DXF reader (covers AC1009 through AC1032).
- `pyproj` — CRS reprojection.
- `simplekml` — KMZ writer (already in user's stack).
- `shapely` — geometry cleanup (polyline merging, simplification).

---

## CRS Detection — Tier System

Three tiers, fall through automatically:

### Tier 1 — Embedded / sidecar (automatic)

In order, first hit wins:

1. **`.prj` sidecar** — same basename as DXF. `pyproj.CRS.from_wkt(open(prj).read())`.
2. **AutoCAD `GEODATA` xrecord** — `doc.rootdict["AcDbVariableDictionary"]` via `ezdxf`. Modern Civil 3D writes EPSG into this block.
3. **Header `$PROJECTNAME` / hint TEXT entities** — low-confidence; only used to *suggest* a CRS for user confirmation, never auto-applied.

If Tier 1 succeeds, write EPSG into `layer_mapping.json` with `confidence: "HIGH"`.

### Tier 2 — Known regional default (one-shot user supply)

Lookup in `scripts/dxf_crs_defaults.json`:

```json
{
  "Indiana": "EPSG:2965",
  "IN": "EPSG:2965",
  "Florida-North": "EPSG:2238",
  "Ohio-North": "EPSG:3734"
}
```

Match heuristic: case-insensitive substring search of DXF filename and any TEXT entity content against keys. First match wins. If multiple matches, list candidates and prompt for selection. Confidence: `MEDIUM`.

### Tier 3 — Manual anchors (local/job coordinates)

When Tier 1 + 2 both fail, `build_anchors.py`:

1. Lists candidate anchor points: `INSERT` blocks named `MON`/`BENCHMARK`/`CTRL_PT`, line endpoints near TEXT-tagged points, polyline vertices at intersections.
2. For each anchor, prompts: *"DXF point `(123456.78, 987654.32)` — what's the lat/lon?"*
3. Computes transform:
   - **2 anchors → 4-parameter Helmert** (translation + rotation + uniform scale).
   - **3+ anchors → 6-parameter affine** (handles non-uniform scale; common when CAD uses a stretched plot scale).
4. Writes `anchors.json`. Confidence: `MEDIUM` if 3+, `LOW` if 2.

### Confidence reporting

KMZ document description embeds the source line:

> *"Coordinates derived via Tier 1 (embedded GEODATA, EPSG:2965, NAD83 Indiana East). Confidence: HIGH."*

So contractors and future-self can see the provenance without re-running the workflow.

---

## Layer Mapping — Schema & Convention Engine

### `layer_mapping.json` shape

```json
{
  "source_dxf": "JB12345_NEW_FIBER.dxf",
  "crs": {
    "tier": 1,
    "epsg": "EPSG:2965",
    "label": "NAD83 / Indiana East (ftUS)",
    "source": "embedded GEODATA",
    "confidence": "HIGH"
  },
  "kmz_meta": {
    "title": "JB12345 — Anytown Permit Package",
    "description": "Generated from DXF for contractor work-area handoff. Not for engineering layout."
  },
  "layers": [
    {
      "name": "E_FIBER_AERIAL_NEW",
      "entity_counts": {"LWPOLYLINE": 14, "LINE": 0},
      "publish": true,
      "feature": "route",
      "subtype": "aerial",
      "folder": "Proposed Route/Aerial",
      "style": {"color": "ff0000ff", "width": 3, "dashed": true},
      "matched_rule": "*FIBER*AER*"
    },
    {
      "name": "PERMIT_BOUNDARY",
      "entity_counts": {"LWPOLYLINE": 1},
      "publish": true,
      "feature": "polygon",
      "folder": "Permit Area",
      "style": {"line_color": "ff00ffff", "fill_color": "4000ffff", "width": 2},
      "matched_rule": "*PERMIT*BOUND*"
    },
    {
      "name": "EX_POLE",
      "entity_counts": {"INSERT": 47},
      "publish": false,
      "feature": "point",
      "folder": "Existing Infrastructure",
      "style": {"icon": "shaded_dot", "color": "ff888888"},
      "matched_rule": "*EX*POLE*",
      "_note": "Existing → default off; flip publish:true to include for context"
    },
    {
      "name": "RANDOM_TEXT_LAYER_42",
      "entity_counts": {"TEXT": 12},
      "publish": false,
      "feature": null,
      "matched_rule": null,
      "_note": "Unmapped — no convention matched. Set feature + style to publish."
    }
  ]
}
```

### Built-in convention rules (`scripts/layer_conventions.py`)

Order matters; first match wins. Case-insensitive regex against the DXF layer name.

| Rule pattern | Feature | Subtype | Default style | Publish |
|---|---|---|---|---|
| `.*PERMIT.*BOUND.*` / `.*WORK.*AREA.*` / `.*ROW.*LIM.*` | polygon | boundary | yellow line + 25%-alpha yellow fill | yes |
| `.*FIBER.*AER.*` / `.*OVH.*` / `.*AERIAL.*` | route | aerial | red, width 3, **dashed** | yes |
| `.*FIBER.*UG.*` / `.*UNDERGRD.*` / `.*BORE.*` / `.*TRENCH.*` | route | underground | red, width 3, **solid** | yes |
| `.*REPLACE.*` (route layer) | route | replace | orange, width 3, dashed | yes |
| `.*MARKUP.*` / `.*REVISION.*` / `.*REDLINE.*` | route | markup | magenta, width 3, dashed | yes |
| `.*PROPOSED.*POLE.*` / `.*NEW.*POLE.*` | point | pole-new | red dot icon | yes |
| `.*VAULT.*` / `.*HANDHOLE.*` / `.*HH\b` | point | vault | blue square icon | yes |
| `(?:^\|_)EX(?:_\|$)` / `.*EXIST.*` | (whatever else matches) | existing | gray | **no** (default off) |
| `.*STA.*` / `.*STATION.*` (TEXT entities) | label | station | small text | no |
| Anything unmatched | null | null | null | no |

Adding a rule for a new drafter is a one-line addition to `layer_conventions.py`. The matched rule is recorded in `layer_mapping.json` so the user can see *why* a layer was classified.

### Why default existing OFF

Contractor handoff = "where you are permitted to work." Existing poles/cable add visual noise and aren't part of scope. They live in the KMZ (toggleable for context), but ship folded closed and visibility off.

---

## KMZ Output Structure

```
JB12345 — Anytown Permit Package          ← document name
│
├── ⬛ Permit Area                          ← yellow polygon (visible)
│
├── 📐 Proposed Route                       ← visible folder
│   ├── Aerial   (dashed red)
│   └── Underground   (solid red)
│
├── 🔵 Proposed Infrastructure              ← visible folder
│   ├── Poles (red dot icons)
│   └── Vaults (blue square icons)
│
├── 📍 Stations & Labels                    ← collapsed by default
│
└── 🌫️ Existing Infrastructure              ← visibility OFF, folded
    ├── Existing Poles
    ├── Existing Fiber
    └── (anything else matching `*EX*`)
```

### Style choices, justified

- **Yellow translucent fill** for permit area: matches USACE/DOT permit-exhibit convention; visible but doesn't obscure the route inside.
- **Red dashed = aerial, red solid = underground:** matches `cd-route-stitcher`, so a contractor seeing both deliverables reads them the same way.
- **Default visibility:** Permit Area + Proposed Route + Proposed Infrastructure ON. Existing OFF + folded. Stations folded but visible-when-expanded.
- **Document `<description>`** carries the CRS provenance line + the quality-bar disclaimer.
- **All geometry uses `<altitudeMode>clampToGround</altitudeMode>`.** Z-coords from DXF are discarded.

### v1 explicitly excludes

- HUD/legend ScreenOverlay (the `cd-ground-overlays` `build_hud.py` pattern). Folder names + per-folder colors are self-documenting.

---

## Quality Bar

Printed in `SKILL.md` and embedded in every KMZ document description:

> *"Generated from drafter DXF for contractor work-area handoff and field navigation. Coordinates derived via [tier]. Not certified for engineering layout — for that, use the source DWG in Civil 3D."*

---

## Failure Modes (documented in SKILL.md "Gotchas")

| Symptom | Likely cause | Fix |
|---|---|---|
| KMZ lands in the ocean / wrong continent | CRS misdetected; reprojected garbage | `inspect_dxf.py --crs-prompt` to override; verify EPSG matches survey datum on title block |
| Routes scaled too small/large but in right neighborhood | Wrong State Plane zone (right state, wrong half) | Common — Indiana East vs West, Florida North vs East. Override EPSG. |
| All polylines tagged as one feature | DXF uses single layer (`0` or `Default`) for everything | Pre-step in CAD: split entities to layered structure. (Color/linetype as fallback discriminator deferred to Tier 4 / future.) |
| Permit boundary missing | Drafter put it on a non-conventional layer | Find the layer in inspect output, set `publish: true, feature: polygon` |
| Block references not appearing as points | Block insertion-point is the feature anchor | `build_kmz.py` uses `INSERT` insertion-point by default; works for poles/vaults if drafter places blocks at actual feature locations |
| KMZ huge | DXF has thousands of arc-tessellation segments per polyline | `build_kmz.py --simplify <ft>` applies Douglas–Peucker; default 0.5 ft (invisible at contractor zoom) |

## Known Limitations (v1)

- Curve fidelity: arcs/splines tessellated at fixed segment count.
- Hatch patterns: not rendered. Permit boundary fills are flat translucent.
- 3D Z-coords: discarded.
- External references (XREFs): not auto-resolved. Bind in CAD before exporting DXF.
- Multi-DXF JB-level merge: deferred. Seam documented for clean future addition.

---

## Workflow (for SKILL.md)

The user-facing workflow when this skill is invoked:

```bash
# Step 1: inspect DXF, propose mapping + CRS
python scripts/inspect_dxf.py drawing.dxf --output layer_mapping.json

# Step 2 (only if Tier 3 / local coordinates): build manual anchors
python scripts/build_anchors.py drawing.dxf --output anchors.json

# Step 3: build the KMZ
python scripts/build_kmz.py drawing.dxf layer_mapping.json --output contractor.kmz
# OR with anchors:
python scripts/build_kmz.py drawing.dxf layer_mapping.json --anchors anchors.json --output contractor.kmz

# Step 4: validate in Google Earth Pro
# - Permit area lines up with parcel/road geometry on satellite imagery
# - Route follows roads, not yards
# - Existing folder toggleable for context
```

## Validation (for the implementation phase)

A representative DXF (when available) should produce:

- KMZ that opens in Google Earth Pro without errors
- Permit boundary visible as yellow translucent polygon at correct geographic location
- Aerial route dashed, underground solid
- All proposed infrastructure visible by default
- Existing infrastructure folded + off by default
- Document description shows CRS provenance and quality-bar disclaimer
- For Tier 1 jobs: no manual intervention required
- For Tier 2 jobs: one entry added to `dxf_crs_defaults.json` makes the next job in that region zero-touch
- For Tier 3 jobs: 2+ anchors produce sub-10m horizontal residual on a known landmark

## Open Questions for Implementation

- **Sample DXF:** The user did not supply a sample during brainstorming. The implementation phase should prompt for one before finalizing the regex rules in `layer_conventions.py` — the listed patterns are based on common Comcast/MasTec drafter conventions but should be validated against the user's actual files.
- **Block-extraction edge cases:** Whether to explode `INSERT` blocks into their constituent geometry, or always use the insertion-point as the feature location. Default is insertion-point; revisit if a real DXF shows pole symbols whose insertion-point is not at the pole.
- **Multi-line text (MTEXT) vs TEXT:** Both should be handled by the station/label rule. Implementation should test both entity types.

---

## Decision Log

| Decision | Rationale |
|---|---|
| Multi-stage pipeline (Option A) over single-script | Matches `cd-route-stitcher`/`permit-to-kmz` shape; easier to debug; clean fallback when a stage needs replacement |
| Hybrid layer-mapping (Tier-D / convention-with-override) | User picked D thrice; matches `permit-to-kmz` 3-tier geocoding pattern |
| `dxf_crs_defaults.json` lives in skill folder, not working dir | CRS conventions are per-region, not per-job; should accumulate as institutional knowledge versioned with the skill |
| Existing infrastructure default-off | Contractor handoff focus = "where to work," not "what's already there." Toggleable, not invisible. |
| `merge_kmz.py` deferred to v2 | User confirmed one DXF per deliverable "most of the time" |
| No HUD/legend in v1 | Folder names + colors are self-documenting; can be added later as `cd-ground-overlays` did |
| `pyproj` over hand-rolled CRS math | State Plane zones are too varied to encode by hand; `pyproj` is the standard |
| `shapely` for polyline merging/simplification | Avoids reinventing Douglas–Peucker and chain-merging |
