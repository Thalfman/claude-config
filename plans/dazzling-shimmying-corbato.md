# Plan: Permit Resubmittal Floor Plans — 1595 Prospect Circle

## Context

Permit 26PINE-0182 for converting the 2nd-floor sitting room into an office was NOT APPROVED (SAFEbuilt Review #1, 5/1/2026). Eight deficiencies cited. **The only construction change is adding the partition wall and door.** No new electrical, HVAC, or lighting is proposed — the existing MEP elements are documented on the plan to satisfy the reviewer.

## Scope of Work

**Adding only:** One L-shaped partition wall (~8'2" main + ~2'8" return) with a pre-hung interior door (4' x 6'8") to enclose the 2nd-floor Sitting room (15'10" x 10'3") as an office.

**Not changing:** Electrical, HVAC, lighting, plumbing — all existing elements remain as-is.

## Room

- **Level**: Second floor
- **Current label**: Sitting (15'10" x 10'3")
- **New label**: Office
- **Position**: Right side of 2nd floor, between two bedrooms. Exterior wall (east) has window. West side has opening to stair/hallway area — this is where the new wall goes.

## Deliverable

Single HTML file (`floor_plan.html`) with inline SVG → two print-ready 8.5" x 11" sheets.

---

### Sheet A1 — Master Floor Plan

All three levels (Main, Second, Lower) drawn at 1/8" = 1'-0". Second floor shows the new wall on the Sitting room. Room relabeled "OFFICE". Stairs labeled. Revision cloud around the office area.

Addresses: **Building #1** (IRC R106.1.1)

### Sheet A2 — Detailed Room Plan

Zoomed view of the 15'10" x 10'3" office at 1/4" = 1'-0".

**New Construction (revision-clouded):**
- New L-wall with door, dimensioned
- Door swing arc (opens inward)

**Existing Elements Documented (labeled "EXISTING"):**
- Window on east exterior wall → EERO callout: "Emergency Escape and Rescue Opening (EERO): Min 5.7 sq ft net clear opening, min 24" height, min 20" width (IRC R310.2)"
- Existing supply air register location (standard symbol, labeled "EXISTING SUPPLY AIR")
- Existing return air grille location (standard symbol, labeled "EXISTING RETURN AIR")
- Existing receptacle locations on walls (standard symbol)
- Existing switch location (standard symbol)
- Existing ceiling light/fan (standard symbol)

**Code Compliance Legend** (exact text per user):
1. "All new receptacles shall be Arc-Fault Circuit-Interrupter (AFCI) protected (2020 NEC 210.12)."
2. "All new receptacles shall be Tamper-Resistant (TR) (2020 NEC 406.12)."
3. "All new permanently installed lighting shall be high efficacy (LED) (2021 IECC R404.1)."
4. "Permanently installed lighting in the new space shall be controlled by a dimmer, occupant sensor, or timer (2021 IECC R404.2)."

**Symbol Legend** and **Dimensions** on all walls.

---

## Formatting
- New wall/door: revision-clouded and dated 05/03/2026
- Plan annotations new to this resubmittal: also clouded (EERO callout, MEP symbols, legend)
- No personal name anywhere
- Title block: address, permit #, date, scale, revision block

## Technical Approach
- HTML + inline SVG, print CSS with page breaks
- viewBox 816 x 1056 per sheet
- Architectural symbols in `<defs>`, placed via `<use>`
- Revision clouds as SVG arc paths

## SAFEbuilt Cross-Check

| # | Comment | Response |
|---|---------|----------|
| B-1 | Floor plan in context (R106.1.1) | Sheet A1: all levels, office on 2nd floor |
| B-2 | EERO dimensions (R310.2) | Sheet A2: window callout with code mins |
| M-1 | Supply/return locations (R303.10) | Sheet A2: existing SA + RA shown |
| E-1 | Switches/lights/receptacles (R106.1.1) | Sheet A2: existing electrical shown |
| E-2 | AFCI note (NEC 210.12) | Legend note #1 |
| E-3 | TR note (NEC 406.12) | Legend note #2 |
| EN-1 | High efficacy (IECC R404.1) | Legend note #3 |
| EN-2 | Lighting controls (IECC R404.2) | Legend note #4 |

## Verification
1. Open in Chrome, Ctrl+P → two clean pages
2. All 8 SAFEbuilt comments addressed
3. Revision clouds on new work + new annotations
4. No name on sheets
5. Print to PDF
