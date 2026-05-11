---
name: permit-package-builder
description: "Build submission-ready right-of-way permit packages for Comcast/MasTec fiber and coax construction. Use when the user has construction-drawing PDFs (CD packages with cover, vicinity, sheet index, site plans, typicals) and wants permit submission deliverables for every jurisdiction the route crosses. Trigger on 'build permits for this CD', 'I need permits for JB##########', 'create the permit submission set', 'permit packages for all entities'. Produces minimal, scannable deliverables per (JB, entity) pair: short cover letter, filled application, scrubbed CD, KML, fee calculation, single-page transmittal. Skill author runs QC; outputs ship clean."
---

# Permit Package Builder

## What this skill produces

Two submission types, same minimal-output discipline:

**ROW permit package** — for road authorities (state DOT, county/CRC, municipality):
```
output/JB##########/NN_Entity_Name/
  cover_letter.pdf            — 3-4 sentences on letterhead, signed
  application_form.pdf        — entity's form, filled
  fee_calculation.pdf         — line items + total
  transmittal.pdf             — single-page checklist + one-line COI/TCP notes
  construction_drawings.pdf   — scrubbed CD (state-correct 811, correct legal block)
  route.kml                   — copied from input KML when available
  job_aid.pdf        — specialist job aid (NOT bundled into SUBMISSION_PACKAGE.pdf)
```

**Pole-attachment package** — for pole owners (Consumers Energy, AT&T MI, DTE, other utilities):
```
output/JB##########/NN_PoleOwner_Name/
  cover_letter.pdf            — 3-4 sentence notification letter on letterhead
  notification_form.pdf       — pole-attachment notification (master agreement reference)
  pole_list.pdf               — surveyed poles with IDs, tags, lat/lon
  transmittal.pdf             — single-page checklist + one-line COI / agreement notes
  construction_drawings.pdf   — scrubbed CD
  route.kml                   — copied from input KML when available
  job_aid.pdf        — specialist job aid (NOT bundled into SUBMISSION_PACKAGE.pdf)
```

Per JB:
```
output/JB##########/
  open_items.pdf              — terse blocker list (only real action items)
  submission_order.pdf        — project-level checklist: which entity to submit first, what blocks construction
```

Both `job_aid.pdf` (per entity) and `submission_order.pdf` (per JB) are **specialist job aids** — printed checklists for the permit specialist to follow. They MUST be rendered to PDF. They MUST NOT be bundled into the per-entity `SUBMISSION_PACKAGE.pdf` (the reviewer never sees them; they're not part of the submission to the entity).

That's it. No `research.md`, no `coi.md`, no `route_map.md`, no `traffic_control_plan.md`, no `qc_report.md`, no project-level `open_items.md`. Specialists do not need a verification-call script in every package; reviewers do not need QC confirmation tables in every transmittal.

## Iron rule: PDFs are the only deliverable

Markdown is the source format used during generation; the PDF is what ships. After Phase 4 runs, the output tree contains **only** `.pdf` files plus `route.kml` and `construction_drawings_scrubbed.pdf`. No `.md` files remain. If a `.md` exists in the output tree at end of run, the run is incomplete — re-run the cleanup step.

## Iron rule: deliverables ship submission-ready

The skill author runs every quality check **during generation**. Outputs are clean. Specialists scan, sign, submit.

**Never write into a reviewer-facing deliverable file** (cover letter, application, fee calc, transmittal, notification form, pole list):
- "Status: Placeholder" / "Status: Estimate" / "Status: Prefill draft"
- QC tables (QC-001, QC-002...) showing what was checked
- "Verify before submission" / "Specialist must re-verify" notes inside the body
- Field-completeness scans, sum-checks, cross-artifact-agreement tables
- Verification call scripts, "Why this package is required" sections
- Cross-jurisdiction scope partition tables in every entity's fee calc (put ONCE in `open_items.md` if scope is contested; otherwise the per-entity LF in the fee calc speaks for itself)
- Narrative explanations of what's enclosed (the transmittal is the index; the cover letter does not re-list it)

**Specialist-facing files are different.** `job_aid.pdf` and `submission_order.pdf` and `open_items.pdf` are FOR the submitting contact, not the reviewer. They contain action steps, contact verification calls, OPE confirmation reminders, etc. — exactly the content that would be noise in a reviewer-facing deliverable. Keep specialist content in specialist files; keep reviewer content in reviewer files.

If a fact is uncertain, it goes in `open_items.md` as a checkable line. It does not contaminate the reviewer-facing deliverable.

## Contacts (skill defaults)

| Role | Name | Phone | Email |
|------|------|-------|-------|
| MasTec submitting contact | Thomas Halfman | 224-277-1041 | thomas.halfman@mastec.com |
| Comcast project contact | Don Carr | (317) 914-9071 | doncarr@cable.comcast.com |
| MasTec OPE contact | Jacob Poe | (765) 412-5831 | jacob.poe@mastec.com |

**MasTec office of record:** 1800 Johnson Street, Elkhart, IN 46514

Override precedence: `contacts.md` in the working folder > CD title-block contacts > defaults above. Substitutions are recorded as one line in `open_items.md`, not narrated in deliverables.

## When to use

Use whenever the user has Comcast/MasTec CD PDFs and wants permit or pole-attachment submission deliverables. Identifying signals:

- CD title block carries `MasTec Communications Group` and Comcast branding
- JB number `JB##########` (10 digits)
- Sheet structure: cover, vicinity + sheet index + scope, general notes, legend, N site plans, typicals
- For pole-attachment notifications: a per-JB KML with surveyed poles (iKE GPS, Katapult, Spatial Business Systems exports) is the typical input

When NOT to use:
- KMZ-of-the-route only → `cd-route-stitcher` (vector) or `cd-ground-overlays` (raster)
- One-page Sphere overview map → `pdf-to-kmz`
- Per-sheet endpoint metadata only → `plan-sheet-endpoints`

## Prerequisites

```bash
pip install pymupdf reportlab pillow simplekml shapely pyproj requests --break-system-packages
```

| Package | Used for |
|---------|----------|
| `pymupdf` | CD parsing, scrub, combined PDF |
| `reportlab` | Markdown → PDF for cover letter, application, fee calc, transmittal |
| `simplekml` / `shapely` / `pyproj` | KML inspection, polygon containment for entity confirmation |
| `pillow` | KML render fallback |
| `requests` | Pulling current application forms / fee schedules |

Run scripts as `python -m scripts.MODULE_NAME ...`.

## Entity registry

The skill ships a structured registry of permit entities at `references/mi_entity_registry.json`. It's the canonical machine-readable source for everything scripts need about a permit-issuing body: legal name, addressee, submission portal, application form name + URL + version, fee schedule URL + line-item math, COI verbatim wording, review window, and quirks.

The registry covers Michigan: all 7 MDOT regions (Grand Region fully verified; the other 6 stubbed with shared `inherits` references), top MI county road commissions (Kent CRC verified; Wayne, Oakland, Macomb, Washtenaw, Ingham, Genesee, Kalamazoo, Ottawa, Allegan stubbed), top MI municipalities (City of Grand Rapids verified; Detroit, Lansing, Ann Arbor, Kalamazoo, Flint, Walker, Wyoming, Kentwood, Grandville stubbed), the three MI pole owners that show up most (Consumers Energy, AT&T MI, DTE), the major MI rail operators, and the EGLE / USACE / Kent SESC environmental overlays. The full 83-county MDOT region lookup table is included.

**Verified vs. stub.** Each entity carries `verified_date` (ISO) and `stub: true|false`. Verified entries have real values for every reviewer-relevant field and were last confirmed on the listed date. Stubs exist so scripts don't crash when a JB hits an enumerated-but-not-yet-verified entity, but a package using a stub cannot ship until the missing fields are filled or the gaps are noted in `open_items.md`. The pre-flight render linter (forthcoming) will block any draft that draws from a stub entity.

**Inheritance.** A field on an entity can be `{"inherits": "<dotted-path>"}` — used heavily on MDOT regions, where every region inherits the same `submission`, `application_form`, `fee`, and `coi` blocks from the agency-level definitions under `mdot.permit_gateway`, `mdot.common_forms[0]`, etc. Scripts must resolve `inherits` references before using the data.

**Verification policy.** Verified entries become stale after 90 days. Stubs are always-stale. Five fields are flagged `always_verify_before_submission` regardless of staleness: `fee.schedule_url`, `fee.line_items[*].amount_usd`, `addressee.name`, `submission.portal_url`, `application_form.version`.

**Workflow.** Before running any script that consumes the registry, run `python -m scripts.validate_registry`. Exit 0 means the JSON is well-formed and internally consistent (all 83 counties present, all `inherits` references resolve, no contradictory verified/stub flags). Exit 1 means stop — fix the registry before proceeding. After every edit to the registry, append a one-line entry to `references/registry_changelog.md`.

**Schema reference.** Full schema, conventions, and how-to-add-an-entity walkthrough at `references/mi_entity_registry_schema.md`.

The pre-existing markdown reference docs (`entity_research_checklist.md`, `mdot_regions_by_county.md`, `state_811_systems.md`) remain as human-readable companions for prose context — research procedures, jurisdictional logic, escalation paths. When the registry and a markdown reference disagree on a fact, the registry wins.

## Project facts extraction (run before Phase 1)

For each JB, run `python -m scripts.extract_project_facts <JB_folder>` (or `--all <Deliverables_root>` for a batch). The script reads the CD PDF + KML and emits `output/JB##########/project_facts.json` — a single object containing JB number, project address/county/lat/lon, LF aerial / LF underground / pole count / UG-station count from the KML, MDOT region looked up from the registry, BP-001 / BP-002 boilerplate signals from the CD, and an `open_questions` array surfacing every gap that requires manual verification (e.g., "no KML — Mode C, transcribe scope from CD page 2").

Every reviewer-facing draft (cover letter, application, fee calculation, transmittal) reads from `project_facts.json` rather than re-extracting from the inputs. This is the source-of-truth pattern: extract once, render many times. When the script can't extract a value (the typical Mode C case, or a CD with non-standard title block), it sets the field to `null` and adds a line to `open_questions` — it does not invent data.

The script handles the per-JB output naming and directory creation automatically. Default output location is `<deliverables_parent>/output/JB##########/project_facts.json`; override with `--output-dir`.

## Workflow (4 phases)

### Phase 1: Inventory and entity derivation

1. Walk the working folder. Group inputs by JB number (`JB##########`).
2. Per JB, declare mode: **A** (CDs + scoping doc + master KMZ + per-JB KMLs), **B** (CDs + per-JB KMLs), **C** (CDs only).
3. Derive `(JB, entity)` pairs:
   - Mode A: scoping document JB-to-entity table verbatim, with polygon containment cross-check.
   - Mode B: per-JB KML overlay against published jurisdictional boundaries (state DOT, county, municipality, railroad).
   - Mode C: CD title block (address, county, lat/lon) + site plan road labels.
4. **Tell the user the mode and entity list. Wait for go-ahead before drafting.**

For the user response (Phase 1 output), use this format — short, no extra commentary:

```
JB0002479252 — Mode A
  Entities: 01_MDOT_Grand_Region, 02_City_of_Grand_Rapids
  (Kent CRC dropped — route entirely inside Grand Rapids city limits; KCRC has no jurisdiction over incorporated municipality streets)
  CD: JB0002479252.pdf  KML: KML_JB0002479252_2026-04-14.kml  Scoping: Fullerton Jobs JX.pdf

Proceed?
```

The agent does NOT add a Kent CRC package "to be safe" when the route does not enter unincorporated county. Drop the package and note the override in `open_items.md`. Authority over what to submit is the user's; the skill's job is to apply the obvious rule (KCRC = unincorporated only) and surface judgment calls explicitly.

### Phase 2: Scaffold

```
output/JB##########/NN_Entity_Name/
output/JB##########/open_items.md
```

Numbering: state DOT first, then county/CRC (only if real jurisdiction), then municipality. Adjust per job.

### Phase 3: Draft per (JB, entity)

For each pair, write these 4 markdown files:

#### `cover_letter.md`

3-4 sentences. No narrative of what's enclosed. No QC notes. Signature is Thomas Halfman.

```markdown
[Date, ISO 8601]

[Entity addressee block: name, title, address]

Re: Right-of-Way Permit Application — JB##########, [project address]

Dear [permit administrator name or title]:

On behalf of Comcast, MasTec Communications Group submits the attached package for a right-of-way permit covering [one-clause scope: e.g., "1,025 LF of aerial fiber overlash on existing pole plant"] within [entity] jurisdiction at the above location. Construction will be coordinated with permit issuance.

Please contact me with any questions.

Sincerely,

Thomas Halfman
MasTec Communications Group
1800 Johnson Street, Elkhart, IN 46514
224-277-1041
thomas.halfman@mastec.com
```

If the work is purely existing-plant access (no new fiber in this entity's ROW), the scope clause says so in one phrase: "access to one existing aerial tap and one existing UG vault for equipment replacement; no new plant proposed."

#### `application_form.md` (generated by `scripts/render_application_form.py`)

The actual form, filled. Generation: `python -m scripts.render_application_form --jb JB########## --entity <entity_id>`.

The renderer loads `assets/forms/<entity_id>.md` (per-entity slot-filled markdown template that mirrors the entity's published form), flattens `project_facts.json` + the entity registry record + the default-contacts block into a single keyspace, and substitutes every `{{slot}}` with its value. Slots that resolve to nothing are replaced with `(pending)` so the specialist knows what to fill manually.

**Available templates today:** `MDOT_2205-1.md` (covers all 7 MDOT regions via alias), `Kent_CRC.md`, `City_of_Grand_Rapids.md`. Add new templates by dropping a `<entity_id>.md` into `assets/forms/` using the same `{{slot}}` syntax.

**No status banners, no field-completeness scans, no QC tables.** When a value is unknown, the slot is replaced with `(pending)` per the iron-rule discipline. The reader sees a filled form. Structure mirrors the entity's published form: Permit type → Applicant → Project location → Scope → Schedule → Traffic control → Insurance → 811 → Signature.

Submitting contact line: `Thomas Halfman | 224-277-1041 | thomas.halfman@mastec.com` (sourced from registry's `default_contacts.mastec_submitting`).

#### `fee_calculation.md` (generated by `scripts/compute_fee.py`)

Line items, total, fee schedule citation. No partition tables. No "estimate" disclaimers in the body.

Generation: `python -m scripts.compute_fee --jb JB########## --entity <entity_id>`. Reads `project_facts.json` + the entity record from the registry; dispatches on `fee.calculation_method`:
- `line_items_lookup` (Kent CRC, etc.) — applies per-line-item rules from `scripts/compute_fee.py:RULES` against project facts (LF aerial, LF UG, pole counts) → real dollar totals.
- `engineering_computes_at_submission` (City of Grand Rapids, etc.) — produces a placeholder fee_calculation that explains the framework + cites the schedule URL; no synthetic dollar amount.
- `portal_calculator` (MDOT MPG, etc.) — same shape as engineering_computes; the entity's portal calculates the fee from submitted scope at application time.

Stub entities (verified_date=null) emit a `Verification required before submission` block warning the specialist. Do not ship the fee_calculation without confirming the dollar amounts against the entity's current schedule.

```markdown
# Fee Calculation — [Entity] (JB##########)

| Item | Quantity | Rate | Subtotal |
|------|----------|------|----------|
| [Line 1] | [Q] | [$ rate] | [$] |
| [Line 2] | [Q] | [$ rate] | [$] |
| ... | | | |

**Total: $XXX.XX**

Fee schedule: [URL] (retrieved YYYY-MM-DD)
Authority: [statute or ordinance reference if applicable]
Payment: [method — ACH / check / portal / etc.] payable to [payee], reference "JB########## — Comcast/MasTec"
```

#### `transmittal.md`

Single page. Six lines plus a contents table. No QC confirmations.

```markdown
# Permit Submission Transmittal — [Entity] (JB##########)

| Field | Value |
|-------|-------|
| Date | YYYY-MM-DD |
| JB | JB########## |
| Entity | [legal name] |
| Project | [address] |
| Submitting | Thomas Halfman, MasTec Communications Group, 224-277-1041, thomas.halfman@mastec.com |
| Submission method | [portal URL / email / mail / hand delivery] |

| # | Item | File | Notes |
|---|------|------|-------|
| 1 | Cover letter | cover_letter.pdf | |
| 2 | Application | application_form.pdf | [form name + version] |
| 3 | Construction drawings | construction_drawings.pdf | [N pages, scrubbed YYYY-MM-DD] |
| 4 | Route map / KML | route.kml | per-JB KML |
| 5 | Traffic control | (MUTCD typical [TA-#] applies; full plan on file with contractor) | only when applicable |
| 6 | Certificate of Insurance | (issued by MasTec broker; required additional-insured wording: [one-line quote]) | |
| 7 | Fee calculation | fee_calculation.pdf | $XXX total |
| 8 | [Entity-specific attachment, e.g., Form 2205-1] | reference_*.pdf | |
```

The COI line is one line: who issues, one-line additional-insured wording. **Not a separate file.** The TCP line is one line: which MUTCD typical applies, or "custom TCP required (separate)". **Not a separate file unless work needs custom design** (lane closure, detour). When custom TCP is required, generate a one-page `traffic_control_plan.md` matched to the work; otherwise omit the file entirely.

### Phase 4: Process inputs and render

1. **Scrub CD.** `python -m scripts.scrub_cd <input.pdf> <output.pdf> --state MI`. Produces `output/JB##########/construction_drawings_scrubbed.pdf`. Copy into each entity folder as `construction_drawings.pdf`.
2. **Copy KML** (Mode A/B). `cp <input>.kml output/JB##########/<NN_Entity>/route.kml`. Skip in Mode C.
3. **Write the job aids.** One `job_aid.md` per entity folder; one `submission_order.md` at the JB root. See "Submission job aids" below for required structure.
4. **Render markdown to PDF.** `python -m scripts.render_all output/`. Cover letters get the MasTec letterhead; every PDF gets a footer with JB | entity | filename | page. Job aids render alongside the rest.
5. **Combine.** `python -m scripts.build_combined_packages output/`. Produces `output/JB##########/<NN_Entity>/SUBMISSION_PACKAGE.pdf` in submission order: cover letter → application/notification → pole_list (pole owners) → transmittal → fee calculation (ROW only) → scrubbed CD → reference docs. Job aids (`job_aid.pdf`, `submission_order.pdf`) are **excluded** from the combined PDF by design — they're specialist-facing, not reviewer-facing.
6. **Clean up markdown intermediates.** `find output/ -name "*.md" -delete`. The user wants only PDFs (and the `route.kml` for the route exhibit) in the deliverable folder. The markdown was an intermediate; the PDF is the deliverable. **Do not leave any `.md` file in the output tree at end of run.**

KML stays beside the combined PDF as `route.kml` (KML is not bundled into the PDF). The scrubbed source CD stays at `output/JB##########/construction_drawings_scrubbed.pdf` as the audit-trail master.

## Route exhibit (`route_exhibit.pdf`)

Generated by `scripts/render_route_exhibit.py`. One-page vector-only PDF rendition of the per-JB KML, scaled to fit US Letter landscape with title block, route geometry (aerial spans dashed-red, UG spans solid-red, anchor leads yellow, surveyed poles green dots), legend, north arrow, and scale bar. No satellite imagery (no API dependency); for richer maps feed the same KML into `cd-ground-overlays`.

Generation: `python -m scripts.render_route_exhibit --jb JB########## --entity <entity_id>`. Output ships as page 4 of `SUBMISSION_PACKAGE.pdf` (after transmittal, before scrubbed CD) so reviewers always see a printed exhibit alongside the raw `route.kml`.

## Master submission tracker (`output/MASTER_TRACKER.md`)

Generated by `scripts/build_master_tracker.py`. Walks every `output/JB##########/project_facts.json`, derives a status verdict per JB, and writes a single dashboard with: per-JB scope (LF, type, county, MDOT region), per-JB BP-001/BP-002 signals, per-JB scrub state, per-JB open-question count, status verdict, and aggregate batch stats (e.g., "5 of 6 CDs already scrubbed").

**Status verdicts** (in priority order — first matching wins):
- `NEEDS_CD_TRANSCRIBE` — Mode C (no KML); scope must be hand-transcribed from CD page 2.
- `NEEDS_SCRUB` — BP-001 or BP-002 flagged AND no sibling `<jb>_scrubbed.pdf` present.
- `NEEDS_RESEARCH` — county or MDOT region didn't auto-resolve.
- `SCRUBBED` — boilerplate-flagged but `<jb>_scrubbed.pdf` exists; ready for fee/form/exhibit.
- `READY_TO_DRAFT` — clean scope, jurisdiction, and BP signals.

The tracker derives scrub state by probing the filesystem for `output/<jb>/<jb>_scrubbed.pdf`. To trigger the `SCRUBBED` transition, run `scripts/scrub_cd.py` and place the output at that exact path. Re-run after each `extract_project_facts` to refresh.

Generation: `python -m scripts.build_master_tracker --root output/`. Companion `MASTER_TRACKER.json` ships for downstream tooling and includes a `scrubbed_cd_pdf` field per row for pipelines that need the path.

## Pre-flight render lint (`scripts/preflight_lint.py`)

Last gate before any package ships. The renderer iron-rule is "no status banners, no QC tables, no scaffolding language" — the linter mechanically enforces it.

Run: `python -m scripts.preflight_lint --root output/` (whole batch) or `python -m scripts.preflight_lint --package-dir output/<JB>/<entity>/` (single package).

Scans every reviewer-facing markdown file (cover_letter, application_form, fee_calculation, transmittal*) and flags hard findings if it sees:
- internal QC tags (`QC-001`)
- internal status banners (`Status: Placeholder|Estimate|Prefill draft|...`)
- internal QC headings (`Field-completeness scan`, `Verify before submission`)
- universal markers (`TODO`, `FIXME`, `TBD`, `XXX`)
- boilerplate signal codes (`BP-001`)
- internal script/schema names (`scrub_cd`, `open_questions`)
- the word `stub` used as a status

Soft findings (warn-by-default, fail with `--strict`):
- narrative-of-enclosure phrases (`We are pleased to enclose`, `Please find enclosed`, `Pursuant to your request`, etc.) — bureaucratic filler the iron-rule strips.

The `(pending)` sentinel is whitelisted — that's the iron-rule placeholder for unknown slots and should NOT be removed.

Exit code 0 = clean and shippable; nonzero = block the ship and fix what surfaced. Run before `render_all` whenever a package is about to be submitted.

## Submission job aids

Two PDFs the specialist prints and works against. Both MUST exist for every JB.

### Per-JB `submission_order.md` → `submission_order.pdf`

Lives at `output/JB##########/`. Single page. Five sections:

1. **Step 0 — Resolve open items affecting all packages** (OPE start date, COIs, master joint-use agreement numbers, etc.)
2. **Step 1 onward — Per-entity submission**, in order of slowest-review-first (typically state DOT → county/CRC → municipality → pole-attachment notifications). Each entry: a one-line pointer to that entity's `job_aid.pdf`, a placeholder for the ticket/record number, and the typical review window.
3. **Final step — Construction may start when ALL of the following are true** (every issued permit, every pole-attachment authorization, Miss Dig 811 ticket, OPE start date confirmed).

No narrative. Checkboxes only.

### Per-entity `job_aid.md` → `job_aid.pdf` (the entity-specific runbook)

Lives in each `NN_Entity_Name/` folder. One page when rendered. Sections:

- **A. Before submission** — concrete pre-flight items: OPE start date, COI request with verbatim additional-insured wording, account registration, named-coordinator call, field verification, pole-attachment authorization (where applicable).
- **B. Submission via [portal name]** — log-in URL, application type/schedule, project fields to enter, files to upload, fee to pay, ticket/record number to capture.
- **C. After submission** — typical review window, RFI response time, issuance steps, on-site requirements (printed permit, inspector contact, Miss Dig).
- **D. Path 1 / Path 2 (pole attachments only)** — direct NJUNS submission vs routing through Comcast HQ.
- **E. Paper backup (pole attachments only)** — mail-to address and certified-tracking note.

Same discipline as the rest of the deliverables: every line is an action. No narrative justification. No "verify before submission" notes inside the action steps (the steps ARE the verification).

The job aid is for the user (Thomas Halfman or whoever the submitting contact is). It does not enter the SUBMISSION_PACKAGE.pdf. It does, however, render to PDF so it can be printed and physically checked off during submission.

## Per-JB `open_items.md`

Single per-JB file. Terse. Only real action items. No narrative.

```markdown
# Open Items — JB##########

| # | Item | Action | Owner |
|---|------|--------|-------|
| 1 | COI request — MDOT additional-insured wording: "State of Michigan, MTC, MDOT, and their officers/agents are named additional insured…" | Request from MasTec broker | Thomas Halfman |
| 2 | Construction start date | Hold for OPE confirmation | Jacob Poe (OPE) |
| 3 | Verify named permit administrator at MDOT Grand Region (placeholder used: "Region Permit Coordinator") | Call (616) 451-3091 | Thomas Halfman |
| 4 | [other real items] | | |
```

Categories that **do not** belong here:
- "Cover letter, application, transmittal agree" — verified during generation; not an action.
- "Form fields filled or flagged" — verified during generation.
- "Fee calculation cites schedule URL" — visible in fee_calculation.md.
- "CD scrub completed" — visible in the scrubbed PDF and the one-line scrub note (below).

Categories that **do** belong here:
- Real blockers (COI broker request, OPE start-date confirmation, account registration).
- Verification calls a specialist must make (named contact, fee verification at submission).
- Drop/keep decisions for entities with ambiguous jurisdiction.
- Pole-attachment authorization for non-Comcast poles.

When the CD has scrub-worthy issues, append one paragraph at the bottom of `open_items.md`:

> **CD scrub applied [YYYY-MM-DD]:** Replaced state-mismatched 811 callout (was: 1-800-424-5555 / 48HRS; now: Miss Dig 811, three working days, PA 174/2013). Replaced legacy "SEFNCO Communication, Inc." legal boilerplate (was: in General Notes Note 1 + page footer; now: MasTec Communications Group + Comcast Cable Communications, LLC). The scrubbed CD ships in every entity package; the original is retained in the input folder for audit.

That paragraph **replaces** the prior `cd_scrubs.md` and `qc_report.md` files. Keep one note in one place.

## Mode-specific entity derivation rules

### Mode A
- Scoping document JB-to-entity table is authoritative.
- Cross-check: route polygon containment against master KMZ. If the route doesn't enter the polygon claimed by the table, drop the entity and note in `open_items.md`. Don't ship a "just in case" package.
- "Sheridan ambiguity" / "Ingham vs Ingraham" / typo patterns → log in `open_items.md` as a verification line; pick the most likely entity by polygon containment.

### Mode B
- For each JB, overlay per-JB KML on:
  - State DOT region/district maps (MI: M-routes, BL/BR, US-, I- → MDOT; see `references/mdot_regions_by_county.md`)
  - County boundary layers → primary CRC; county-line crossings add both
  - Municipal boundary layers → cities/villages add their engineering/PW; **MI townships do NOT issue road permits** (CRC handles unincorporated)
  - Railroad corridors → operator (license, separate paperwork)
- Default for unincorporated MI is the County Road Commission. Do not add a township as a road permit entity in MI.

### Mode C
- Title block: address, county, lat/lon → resolve municipality and county.
- Site plan road labels: state-route patterns (`I-`, `US-`, `M-`, `BL/BR`) imply state DOT; non-state roads in incorporated areas imply municipality; non-state roads in unincorporated MI imply CRC.
- Lowest confidence; surface every entity choice in `open_items.md` for specialist override.

## Pole-attachment notifications (when aerial overlash is in scope)

When the CD's description-of-work includes any new aerial fiber overlash on existing pole plant, generate one pole-attachment package per pole owner in the corridor. This is a separate workflow from ROW permits — submissions go to the pole owner's joint-use department (typically via NJUNS in MI), not to a road authority.

### Identifying pole owners

Source data, in priority order:
1. **Per-JB KML pole-tag fields** (iKE GPS / Katapult exports). Common tag formats:
   - **Consumers Energy (MI):** 5-character alphanumeric (e.g., `054E6`, `05240`, `0526F`)
   - **AT&T Michigan / legacy Michigan Bell:** 6–7 digit numeric (e.g., `0898136`)
   - **DTE Energy:** varies; check current convention
   - **Comcast-owned poles:** rare in MI; usually overlash on existing electric/telco plant
2. **Comcast joint-use database / pole-attachment records** — authoritative; query Don Carr (Comcast project contact) for the master joint-use agreement numbers and current pole inventory.
3. **CD callouts on individual poles** — rarely state ownership; mostly identify equipment swaps. The "CE10 / CE12 / CS02" notations are Comcast tap-module part numbers, **not** Consumers Energy pole indicators.

### Default pole-owner mapping (MI)

Most MI urban joint-use corridors carry both Consumers Energy and AT&T Michigan poles. Default to two pole-attachment packages (CE + AT&T MI). Add DTE Energy when the corridor is in DTE service territory (southeast MI). Drop a pole-owner package when no surveyed tags or known records support that owner.

### Pole-attachment package contents

Same minimal discipline as ROW permits:
- `cover_letter.md` — 3-4 sentence notification, signed by Thomas Halfman, addressed to the joint-use department
- `notification_form.md` — pole-attachment notification with attaching party, owner, location, scope, master agreement reference, insurance, and signature
- `pole_list.md` — table of surveyed poles (Pole ID, tag, lat, lon, suspected owner)
- `transmittal.md` — single-page index; COI line is one line; master agreement reference is one line

The same scrubbed CD ships in each pole-owner package as `construction_drawings.pdf`. The same KML ships as `route.kml`.

### Submission route

Most MI joint-use submissions go through **NJUNS** (National Joint Utility Notification System). The skill ships a paper notification packet for the audit trail; the actual ticket submission is electronic. The `transmittal.md` notes "NJUNS ticket preferred; paper backup to [joint-use department address]". Confirm current route per pole owner in `open_items.md`.

## Quality bar

This skill produces **submission-ready first-pass packages**. The specialist scans, validates the entity-list and any open items, requests the COI from the broker, confirms the start date with OPE, and submits. No package contents requires line-by-line review.

If the user receives a package and finds review work — disclaimers in deliverable bodies, QC tables, narrative explanations of what's enclosed, partition tables in every fee calc, multiple Open Items files — that is a skill regression. Strip and ship clean.

## Gotchas

- **JB0002479252 sample carries a state-mismatched 811 callout (1-800-424-5555 / 48HRS) and "SEFNCO Communication, Inc." legal boilerplate.** Both are leftovers from an older drafter template. Auto-scrubbed by `scripts/scrub_cd.py`.
- **Construction start date:** Never commit a date in a cover letter or application without explicit MasTec OPE (Jacob Poe) confirmation. Use "to be coordinated with permit issuance" everywhere; the open-items entry tracks the OPE call.
- **Township jurisdiction in MI:** townships do NOT issue road ROW permits. CRC handles unincorporated MI. Do not add a township as a permit entity in MI unless the CD specifically calls out a township-owned road.
- **Multi-county JBs:** verify both CRCs and confirm the state DOT region on each side of any county line.
- **Railroad crossings are licenses, not permits.** Document encroachment package separately; do not file as a permit submission. Note in `open_items.md`.
- **KCRC = unincorporated only.** A route entirely within Grand Rapids city limits does not need a Kent CRC package even if a scoping doc lists it. Drop and note in `open_items.md`.

## Known limitations

- COI generation is broker-issued; the skill ships the additional-insured wording in the transmittal as a one-line note.
- Custom TCP design (lane closure, detour) requires a TCP designer; the skill notes "custom TCP required" in the transmittal and ships nothing else for that line. Generic shoulder/curbside work cites the appropriate MUTCD typical (TA-1 / TA-3) on the transmittal line.
- Application form retrieval is best-effort; some entities require an account or captcha. Surface as `open_items.md` line; don't guess form contents.
- Mode C confidence is lowest; surface every entity choice for specialist override.

## File map

```
permit-package-builder/
  SKILL.md                                — this file
  assets/
    contacts_default.md                   — Thomas Halfman + Don Carr + Jacob Poe
    cover_letter_template.md              — 3-4 sentence template
    transmittal_template.md               — single-page table template
    job_aid_template.md                   — per-entity job aid template
    submission_order_template.md          — per-JB order/checklist template
    forms/
      MDOT_2205-1.md                      — slot-filled application form template (covers all 7 MDOT regions)
      Kent_CRC.md                         — slot-filled KCRC application template
      City_of_Grand_Rapids.md             — slot-filled GR Accela portal field set
  references/
    mi_entity_registry.json               — CANONICAL entity data (machine-readable)
    mi_entity_registry_schema.md          — registry schema, conventions, how-to-add-an-entity
    registry_changelog.md                 — one line per registry refresh / addition
    canonical_cd_format.md                — CD title block / sheet structure
    entity_research_checklist.md          — research procedure + per-entity prose context
    known_boilerplate_errors.md           — BP-001 (811), BP-002 (SEFNCO), detection regexes
    mdot_regions_by_county.md             — MI county → MDOT region (companion; registry is canonical)
    state_811_systems.md                  — MI / IN / IL / etc. (registry has MI canonical)
    open_items_taxonomy.md                — categories of real items
    package_contents.md                   — one-line summary of the per-entity folder
    quality_checks.md                     — what the skill verifies during generation
  scripts/
    validate_registry.py                  — sanity-check the registry; run before any consuming script
    extract_project_facts.py              — read CD PDF + KML, emit project_facts.json (single source of truth for downstream renders)
    compute_fee.py                        — read project_facts.json + registry → write fee_calculation.md per (JB, entity) pair
    render_application_form.py            — read project_facts.json + registry + per-entity template → write application_form.md
    render_route_exhibit.py               — read KML + project_facts.json → write route_exhibit.pdf (1-page route map)
    build_master_tracker.py               — read all JBs' project_facts.json → write MASTER_TRACKER.md (cross-JB submission tracker)
    scrub_cd.py                           — BP-001 / BP-002 scrubs
    render_md_to_pdf.py                   — markdown → PDF (letterhead on cover letters)
    render_all.py                         — batch render every .md → .pdf
    preflight_lint.py                     — last gate before shipping; scans reviewer-facing .md for QC tags, status banners, internal scaffolding, narrative-of-enclosure phrases. Exits nonzero on hard findings.
    build_combined_packages.py            — concatenated SUBMISSION_PACKAGE.pdf
                                            (job aids and open_items are EXCLUDED)
    inventory_inputs.py                   — Mode A/B/C declaration
    derive_entities_modeA.py              — scoping → entity_pairs.json
    derive_entities_modeB.py              — KML overlay → entity_pairs.json
    derive_entities_modeC.py              — CD title block → entity_pairs.json (uses registry)
    scaffold_package_tree.py              — output folder layout
    extract_cd_titleblock.py              — title block fields
```

## Bottom line

Per ROW entity: 6 reviewer-facing files (cover letter, application, fee calc, transmittal, scrubbed CD, KML) + 1 specialist job aid (`job_aid.pdf`).

Per pole-owner: 6 reviewer-facing files (cover letter, notification form, pole list, transmittal, scrubbed CD, KML) + 1 specialist job aid (`job_aid.pdf`).

Per JB: 1 open-items file + 1 project-level submission-order job aid.

No project-level open-items duplicate, no QC report, no research file, no separate COI doc, no separate route map doc, no separate TCP doc unless custom design is required. Cover letter is 3-4 sentences. Application/notification is filled, not annotated. Transmittal is one page. Fee calc is a table with a total. Job aids are PDFs with action checkboxes; they live in entity folders but never enter SUBMISSION_PACKAGE.pdf. Specialist prints the job aid, requests broker COI, confirms OPE date, submits per the steps.
