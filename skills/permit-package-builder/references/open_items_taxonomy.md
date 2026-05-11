# Open Items Taxonomy

Open Items are surfaced as encountered, not batched at the end of a run. Two files capture them:

- `output/open_items.md` — project-wide rollup
- `output/<JB>/open_items.md` — per-JB, including entity-derivation override lines

Each row carries: category tag, JB number, entity (if applicable), a one-line description, and an action / escalation note. The seven categories below.

## OI-1: Missing input

A required input for a JB is absent.

| Subtype | Example |
|---------|---------|
| Missing CD | "JB0002479260 has no CD PDF in inputs" |
| Missing per-JB KML | "JB0002479252 KML pending; route map traced from CD vicinity for Mode A workflow" |
| Missing scoping doc | "Mode A inputs incomplete; running Mode B for all JBs" |
| Missing master KMZ | "Mode A inputs incomplete; falling back to per-JB boundary checks" |

**Action:** request the missing input from the project source (vendor for scoping/KMZ, drafter for CD/KML). Hold submission for any package whose missing input affects fidelity of the entity list or scope quantities.

## OI-2: Polygon implies entity not in scope (Mode A)

The master KMZ shows the route crossing an entity polygon that the scoping document's JB-to-entity table did not include.

| Example |
|---------|
| "JB0002479252 master KMZ shows route crossing Walker city polygon; scoping table lists only Grand Rapids and Kent CRC" |

**Action:** verify whether the polygon crossing is a real corridor traverse or a polygon-noise artifact (e.g., the master KMZ's polygon for Walker is inflated or the route briefly clips the boundary). If real, add the entity to the JB scope and produce its package. If polygon noise, document in research.md and ignore.

## OI-3: Scoping doc names entity whose polygon route does not intersect

Inverse of OI-2. The scoping document lists an entity, but the route does not actually cross that entity's polygon per the master KMZ.

| Example |
|---------|
| "JB0002479258 lists 'City of East Grand Rapids' but route does not enter EGR per master KMZ" |

**Action:** verify with the scoping source. If the entity is included for permitting reasons not derivable from polygon crossing (e.g., the route's staging area is in EGR even though the work is not), keep the package. If the entity is in error, drop the package and document.

## OI-4: Entity application form changed

The current application form retrieved at the start of the package differs in format or version from the form used in prior submissions to the same entity.

| Example |
|---------|
| "MDOT Grand Region permit application updated to v2026-03; field 7b ('Estimated Schedule') now requires sub-fields not in v2025-09" |

**Action:** review the new form. Update any standing template or prefill list. Document the version change in `open_items.md`. Notify the MasTec submitting contact (default: Thomas Halfman) so future jobs use the new form.

## OI-5: Jurisdiction requires beyond-canonical artifact

An entity requires something outside the canonical 10-item package.

| Example |
|---------|
| "City of Grand Rapids requires arborist letter for tree-removal in ROW; not in canonical package" |
| "Kent CRC requires soil-boring log for any bore deeper than 8 feet" |
| "MDOT Grand Region requires environmental review for crossings of EGLE-mapped waters" |

**Action:** add the artifact to the package. Update the entity's section in `entity_research_checklist.md` so future jobs default to including it.

## OI-6: Scope inside corridor needing separate environmental / encroachment permit

The CD shows scope inside a railroad corridor, water body, or wetland that may need separate paperwork beyond the ROW permit.

| Subtype | Action |
|---------|--------|
| Railroad corridor | License/encroachment notice to the rail operator; 60-120 day timeline |
| Water body crossing | USACE Section 404 if a water of the US; state water quality cert |
| Wetland crossing | EGLE Part 303 in MI; flag for state-specific wetland permit elsewhere |
| Floodplain | Coordinate with local FEMA-mapped floodplain administrator |

**Action:** open a separate package or paperwork track for the encroachment / environmental piece. The ROW permit submission is held until the separate paperwork is in flight (some entities require a copy of the rail license at submission; others require it before construction).

## OI-7: Stale contact info

Permit-administrator contact returns a bounceback, disconnected number, or "no longer at this office" auto-response.

| Example |
|---------|
| "Email to permit-admin@xyzcity.gov bounced; no replacement listed on entity website" |

**Action:** call the entity's main switchboard for the current contact. Update research.md and the entity-research checklist. Hold submission until verified contact is in place; misrouted submissions can lose weeks.

## Escalation guidance

| Severity | Trigger | Escalate to |
|----------|---------|-------------|
| Low | OI-4, OI-5 (informational) | Note in research.md; surface at next standup |
| Medium | OI-1 (missing input), OI-7 (stale contact) | Email to MasTec OPE contact (Jacob Poe); CC the submitting contact |
| High | OI-2, OI-3 (entity scope wrong), OI-6 (separate environmental/rail paperwork needed) | Same-day call to MasTec OPE; CC the submitting contact and Don Carr (Comcast) |

When escalating, include: JB number, entity, OI category, one-line description, the affected package's submission target date, and what the package is currently held for.

## Open Items table format

Both `output/open_items.md` and `output/<JB>/open_items.md` use a markdown table:

```
| Date | JB | Entity | Category | Description | Action / Escalation | Status |
|------|----|---------|----------|-------------|---------------------|--------|
| 2026-04-27 | JB0002479252 | MDOT Grand Region | OI-4 | Application form updated to v2026-03 | Reviewed; field 7b sub-fields filled per new format | Resolved |
```

Status values: `Open`, `In progress`, `Resolved`, `Escalated`. Sort by date descending. Per-JB file does not need the JB column.
