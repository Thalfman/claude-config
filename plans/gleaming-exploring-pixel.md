# Permit Resubmittal Floor Plan — 1595 Prospect Circle, Pingree Grove, IL

## Context

SAFEbuilt plan review (5/1/2026, Permit #26PINE-0182) returned **NOT APPROVED** with 8 deficiencies across Building, Mechanical, Electrical, and Energy categories. The remodel converts the **second-floor sitting room (15'10" x 10'3")** into an enclosed room by adding a 2x4 partition wall with a 48"x80" pre-hung door. A previous script (`codex_work/generate_permit_plan.py`) exists but incorrectly placed the work on the lower level — starting fresh.

## SAFEbuilt Deficiencies → Plan Response

| # | Category | Requirement | Code | Addressed By |
|---|----------|-------------|------|-------------|
| B-1 | Building | Floor plan showing work location relative to other rooms, stairs | IRC R106.1.1 | Sheet A-1 (master plan) |
| B-2 | Building | EERO net clear opening for window | IRC R310.2 | Sheet A-2 (EERO callout) |
| M-1 | Mechanical | Return and supply duct locations | IRC R303.10 | Sheet A-2 (HVAC symbols) |
| E-1 | Electrical | All switches, lights, receptacles | IRC R106.1.1 | Sheet A-2 (electrical plan) |
| E-2 | Electrical | AFCI protection note | NEC 210.12 | Sheet A-2 (code legend) |
| E-3 | Electrical | Tamper-resistant note | NEC 406.12 | Sheet A-2 (code legend) |
| EN-1 | Energy | High efficacy lighting | IECC R404.1 | Sheet A-2 (code legend) |
| EN-2 | Energy | Dimmer/sensor/timer control | IECC R404.2 | Sheet A-2 (code legend) |

## Deliverable

A single Python script generating a **2-sheet 11"x17" landscape PDF** plus PNG previews.

---

## Sheet A-1: Master Floor Plan

**Purpose:** Show location of proposed work relative to existing rooms and stairs (IRC R106.1.1).

1. Embed `IMG_7119.JPG` as background (all three levels visible)
2. Locate the **second-floor SITTING room** (lower-right area of the second floor section)
3. Draw blue overlay showing new partition wall position within the sitting room
4. Revision cloud (red scalloped border) around the work area, dated
5. Leader arrow + label: "PROPOSED REMODEL ROOM"
6. Label adjacent rooms: "EXISTING STAIRS", nearby bedrooms, bath for context
7. Notes box explaining the plan and referencing Sheet A-2 for details
8. Title block (no personal names)

**Key pixel mapping:** The second-floor section of IMG_7119.JPG is in the upper-right quadrant. The SITTING room label is visible in the lower-right portion of that section. I'll map image pixel coordinates to canvas coordinates to place the overlay accurately.

## Sheet A-2: Detailed Room Plan

**Purpose:** Zoomed-in 2D floor plan of the remodeled room with all required elements.

### Room Layout (drawn to scale, ~1/2" = 1')
- Room: 15'10" x 10'3" (the sitting room)
- 3 existing walls drawn in black (8pt line weight)
- 1 new partition wall drawn in **blue** with:
  - 8' 1 15/16" main wall segment
  - 2'8" return wall
  - 48"x80" pre-hung door with swing arc
- Window symbol on exterior wall (double-line architectural convention)
- Dimension lines for room width, depth, door width, return wall length

### EERO Window Callout (addresses B-2)
- Leader line (red) from text box to window
- Exact text: *"Emergency Escape and Rescue Opening (EERO): Min 5.7 sq ft net clear opening, min 24" height, min 20" width (IRC R310.2)"*

### HVAC Symbols — Red (addresses M-1)
- Supply air register: red rectangle with diagonal hatching, labeled "SUPPLY AIR REGISTER"
- Return air duct: red rectangle with horizontal lines, labeled "RETURN AIR DUCT"
- Placed on walls based on typical HVAC layout for second-floor rooms

### Electrical Symbols (addresses E-1)
- **Receptacles (yellow circles, "R")**: 6 receptacles on walls per NEC spacing (within 6' of door, every 12' along walls, flanking window)
- **Switch (orange square, "S")**: 1 switch adjacent to door on partition wall
- **Ceiling light (circle with X, "LED")**: 1 center ceiling fixture (existing ceiling fan/light)

### Code Compliance Legend (addresses E-2, E-3, EN-1, EN-2)
Text box with exact notes:
1. "All new receptacles shall be Arc-Fault Circuit-Interrupter (AFCI) protected (2020 NEC 210.12)."
2. "All new receptacles shall be Tamper-Resistant (TR) (2020 NEC 406.12)."
3. "All new permanently installed lighting shall be high efficacy (LED) (2021 IECC R404.1)."
4. "Permanently installed lighting in the new space shall be controlled by a dimmer, occupant sensor, or timer (2021 IECC R404.2)."

### Symbol Legend
Color-coded key per user spec:
- Red = Vent (HVAC supply/return)
- Yellow = Outlet (receptacle)
- Orange = Switch

### Revision Clouds (addresses G-1 formatting requirement)
- Red scalloped borders around: room plan, EERO callout, symbol legend, code legend
- Each cloud labeled with date

---

## Title Block (both sheets)
- "SFR REMODEL PERMIT RESUBMITTAL"
- "1595 PROSPECT CIRCLE, PINGREE GROVE, IL"
- Sheet number and title
- Revision date (05/04/2026)
- "Changes clouded in red"
- **No personal names anywhere**

## Source Files

| File | Role |
|------|------|
| `IMG_7119.JPG` | Full house floor plan background (Sheet A-1) |
| `Top Down.png` | SketchUp top-down — reference for framing overlay |
| `Front View.png` | SketchUp front — wall dims: 8' 1 15/16" wide, 4' door, ~8' ceiling |
| `Angled Side View.png` | SketchUp angled — 2'8" return dimension |
| `0A3C1FAF-...pdf` | SAFEbuilt review comments (reference) |

## Dependencies

```
pip install reportlab Pillow PyMuPDF
```

## Output Files

- `SFR_Remodel_1595_Prospect_Circle_Permit_Plan.pdf` (2-sheet PDF)
- `SFR_Remodel_1595_Prospect_Circle_Permit_Plan_sheet1.png` (preview)
- `SFR_Remodel_1595_Prospect_Circle_Permit_Plan_sheet2.png` (preview)

## Verification

1. Open PDF — both sheets render cleanly at 11x17
2. Sheet A-1: sitting room highlighted on the **second floor** (not lower level)
3. Sheet A-2: all 8 SAFEbuilt deficiencies addressed (walk through the table above)
4. Revision clouds with dates on all changed elements
5. No personal names anywhere in the document
6. Symbol colors match spec: red=vent, yellow=outlet, orange=switch
