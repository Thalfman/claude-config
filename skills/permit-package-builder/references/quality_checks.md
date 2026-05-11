# Quality Checks (Mode-Conditional)

Every `(JB, entity)` package runs through this list before it is declared complete. Checks are mode-conditional: some only apply when route geometry is available (Modes A and B), others only apply when input lacks the scoping document (Modes B and C), and a core set applies to all modes.

A check that fires writes a row to `output/<JB>/open_items.md` and to `output/open_items.md`. Packages with unresolved Open Items affecting them must not be submitted; hold and escalate.

## Core checks (all modes)

### QC-001: 811 callout matches state of work

- **Where:** CD general notes section (typically page 3)
- **Test:** detected 811 system name from the CD ↔ state of work from the title block (or the `state` field of the application form)
- **Pass:** match per `state_811_systems.md`
- **Fail:** mismatch (e.g., Indiana 811 on Michigan work)
- **Action:** scrub the CD to insert the correct 811 callout; document in research.md
- **Known leftover:** JB0002479252 reference set ships with Indiana 811. See `known_boilerplate_errors.md`.

### QC-002: Legal boilerplate names MasTec or Comcast

- **Where:** CD general notes section, cover sheet legal block
- **Test:** company-name regex against `["MasTec", "Comcast"]`
- **Pass:** legal boilerplate names MasTec or Comcast
- **Fail:** legal boilerplate names a different company (e.g., "SEFNCO Communication, Inc.")
- **Action:** scrub the CD to replace; document in research.md
- **Known leftover:** JB0002479252 reference set ships with SEFNCO boilerplate. See `known_boilerplate_errors.md`.

### QC-003: Cover letter, application, and transmittal index agree

- **Where:** the three drafted artifacts in the package
- **Test:** JB number, scope quantities (LF aerial, LF UG, poles, vaults, bores), entity contact match across all three
- **Pass:** all three agree
- **Fail:** any drift between them
- **Action:** correct the source of the drift and regenerate

### QC-004: Every form field filled or flagged

- **Where:** application form
- **Test:** scan every form field; any blank field that is not explicitly flagged (with "TBD" or a placeholder) fails
- **Pass:** no blank fields
- **Fail:** at least one blank, unflagged field
- **Action:** fill the field or flag it explicitly; document in research.md if blocked on external data

### QC-005: Fee calculation cites schedule URL and date

- **Where:** fee_calculation.md
- **Test:** every line item references the fee schedule URL and the retrieval date
- **Pass:** every line cited
- **Fail:** any line missing citation
- **Action:** add the citation; if the schedule URL has changed, retrieve fresh and update

### QC-006: Multi-entity scope partition sums to CD total

- **Where:** fee_calculation.md across all entities for the JB
- **Test:** sum of per-entity scope quantities ↔ CD total per the description-of-work table
- **Pass:** partition sums to total within rounding
- **Fail:** mismatch
- **Action:** verify the partition; common cause is misattributing a sheet's scope to the wrong jurisdiction

### QC-007: Construction start date not committed without OPE confirmation

- **Where:** cover letter, application form
- **Test:** any specific date in the start-date field, vs. presence of "MasTec OPE confirmed" note in research.md
- **Pass:** placeholder ("to be coordinated with permit issuance") OR OPE confirmation in research.md
- **Fail:** specific date with no OPE confirmation
- **Action:** revert to placeholder; do not commit a date without OPE confirmation

### QC-008: Contact info freshness

- **Where:** entity contacts in research.md
- **Test:** verification timestamp on contact info is within 90 days OR freshness check confirmed
- **Pass:** verified within 90 days OR freshness check succeeded
- **Fail:** older than 90 days with no verification
- **Action:** verify the contact (call/email); if no response, flag as Open Item

## Mode A specific checks (full vendor package)

### QC-101: KML opens cleanly in Google Earth

- **Where:** per-JB KML file
- **Test:** the KML parses without errors and renders with at least one visible polyline
- **Pass:** opens cleanly
- **Fail:** parse error, no polyline, or rendering issues
- **Action:** request a corrected KML from the vendor; flag as Open Item

### QC-102: Route sits inside claimed entity polygon (master KMZ)

- **Where:** per-JB KML route ↔ entity polygon from the master jurisdictional KMZ
- **Test:** every claimed entity for the JB has a polygon in the master KMZ AND the route's bounding box (or a sample of polyline vertices) is contained
- **Pass:** all claimed entities contain the route
- **Fail:** route exits at least one claimed entity's polygon
- **Action:** verify the route geometry vs. the master KMZ; if the route does cross an entity polygon not in the JB-to-entity scope, flag as Open Item (extra entity may be required); if the route does not cross a claimed entity, flag as Open Item (entity may be erroneous)

### QC-103: Scoping document JB-to-entity table not contradicted by polygon overlay

- **Where:** scoping document table ↔ master KMZ polygon overlay
- **Test:** for each JB row in the table, verify the route's polygon containment against every named entity
- **Pass:** table matches overlay
- **Fail:** polygon overlay implies a different entity set than the table
- **Action:** flag in Open Items; treat the table as authoritative but record the discrepancy

## Mode B specific checks (CDs + KMLs, no scoping)

### QC-201: KML opens cleanly in Google Earth (same as QC-101)

### QC-202: Route sits inside published jurisdictional boundaries

- **Where:** per-JB KML route ↔ published entity boundaries (county GIS, MDOT region maps, municipal boundary layers)
- **Test:** every claimed entity has a published boundary AND the route is contained
- **Pass:** all claimed entities contain the route
- **Fail:** route exits a claimed entity's boundary, OR an entity claimed by the derivation logic does not match a published boundary
- **Action:** correct the entity list; flag as Open Item

## Mode C specific checks (CDs only)

### QC-301: Project address resolves into the claimed jurisdictions

- **Where:** project address from CD title block, lat/lon if printed
- **Test:** address lookup (or lat/lon) resolves to a municipality and county that match the entity derivation
- **Pass:** address ↔ derived jurisdictions are consistent
- **Fail:** address resolves to a different municipality or county
- **Action:** correct the entity list; if the CD title block is wrong (drafter typo), flag as Open Item

### QC-302: Site plan road labels include at least one road owned by each claimed entity

- **Where:** site plan road labels ↔ entity-owned road list
- **Test:** for each claimed entity, the site plans show at least one road segment that the entity is the road authority for
- **Pass:** every claimed entity has visible roads on site plans
- **Fail:** an entity is claimed but no roads owned by them appear on site plans
- **Action:** demote that entity to Open Items pending verification; common cause is that the route exits the visible site-plan tiles into an unlabeled adjacent jurisdiction

## Test logic summary

The QC scrub is implemented as a list of (id, name, applies_to_modes, test_function) tuples. The script `python -m scripts.run_quality_checks <JB> <entity>` runs every applicable check and writes a per-package `qc_report.md` plus appends rows to `open_items.md`.

Adding a new check:

1. Define the check (id, name, applies_to_modes, test_function) in `scripts/run_quality_checks.py`.
2. Add a documentation entry to this file under the appropriate section.
3. Test against the JB0002479252 reference set; verify it fires correctly on known issues and does not fire on correct data.
