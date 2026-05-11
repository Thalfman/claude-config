# Canonical CD Format (JB0002479252 reference)

The `JB0002479252` deliverable is the canonical example of a Comcast/MasTec construction-drawing PDF for permit-package purposes. This walkthrough documents what a "complete" CD looks like and where each datum lives, so the skill knows what to expect and where to extract from.

## Reference identifiers

| Field | Value |
|-------|-------|
| JB number | JB0002479252 |
| Project address | 1860 Alpine Ave NW, Grand Rapids, MI 49504 |
| County | Kent |
| Township | (incorporated; City of Grand Rapids) |
| Range / Section | (printed on title block; both used to confirm jurisdiction) |
| Lat / Lon | (printed on cover sheet near the project address) |
| Drafter / template origin | MasTec Communications Group (Civil 3D 2025) |

## Sheet structure (20 pages typical)

| Page | Sheet type | Title-block label |
|------|-----------|-------------------|
| 1 | Cover sheet | Project name, JB#, address, lat/lon, drafter info, scale block |
| 2 | Vicinity map + contacts + sheet index + description-of-work table | "VICINITY MAP" |
| 3 | General notes | "GENERAL NOTES" — including the 811 callout and legal boilerplate |
| 4 | Legend | "LEGEND" — symbology key for the site plan sheets |
| 5 to N | Site plans | "SITE PLAN - 1", "SITE PLAN - 2", ... |
| N+1 to N+M | Typical details | "TYPICAL DETAILS" |
| Last | Traffic control plan | "TRAFFIC CONTROL PLAN" or "MAINTENANCE OF TRAFFIC" |

For JB0002479252, the count is approximately 4 pre-site pages, 7-10 site plan pages, and 4-6 post-site pages.

## Title block field positions

Title block sits in the lower-right of every page (PDF unrotated coords; the page is portrait `792 x 1224` with `270` rotation flag, so it displays landscape with the title block at the bottom-right of the rendered view).

Title-block fields (canonical order, top to bottom within the title block):

1. Drafter logo (MasTec Communications Group)
2. Client logo (Comcast)
3. Project name
4. JB number
5. Address
6. County
7. Township / municipality
8. Range / Section (sometimes)
9. Lat / Lon (when printed on this sheet; usually only on the cover sheet)
10. Sheet number / total
11. Sheet title (e.g., "SITE PLAN - 1")
12. Revision block (date, drafter initials, revision description)
13. Scale block (e.g., "SCALE: 1 INCH = 40 FEET")

Use `python -m scripts.extract_cd_titleblock <pdf>` to pull all 13 fields per page.

## Contacts block (page 2, on or near the vicinity map)

Block format observed in JB0002479252:

```
COMCAST CONTACT:           MASTEC CONTACT:
Don Carr                    Thomas Halfman
(317) 914-9071              224-277-1041
doncarr@cable.comcast.com   thomas.halfman@mastec.com
```

When the contacts block is present and names different individuals than the standing references, prefer the CD contacts and log the substitution in the per-JB Open Items file.

## Description-of-work table (page 2)

A tabulated breakdown of plant by sheet, used to derive scope quantities partitioned by jurisdiction. Typical columns:

| Sheet | LF Aerial | LF UG | Poles | Vaults | Bores | Notes |
|-------|-----------|-------|-------|--------|-------|-------|
| SITE PLAN - 1 | 425 | 0 | 6 | 0 | 0 | Overlash on existing GR strand |
| SITE PLAN - 2 | 0 | 320 | 0 | 1 | 1 | Bore + place 2" conduit |
| ... | | | | | | |

The skill reads this table to:

- Compute total scope (sum of columns)
- Compute per-sheet scope (used to partition by jurisdiction when sheets correspond to specific jurisdictions)
- Detect rail crossings (rows with rail callouts in the Notes column)
- Detect water/wetland crossings (rows with stream / culvert / wetland callouts)

## KML pairing

When a per-JB KML is in the input set, it is named with a date suffix matching the CD revision date. Example: `KML_JB0002479252_2026-04-14.kml`. The skill confirms the JB number in the KML filename matches the CD title block before pairing.

## Sheet-rotation conventions

Site plans are drawn north-up in the rendered (landscape) view. The PDF page is stored portrait `792 x 1224` with rotation flag `270`. When extracting coordinates from the PDF, the geographic-axis convention is:

| Geographic axis | Rendered direction | Direction in unrotated PDF coords |
|-----------------|--------------------|------------------------------------|
| North | up | +x_pdf |
| East | right | +y_pdf |

(This matches `cd-ground-overlays`'s rotation handling and is the OPPOSITE of `cd-route-stitcher`'s default.)

## Quality-check anchors in this CD

The QC list (`quality_checks.md`) specifically watches for these elements in JB0002479252-style CDs:

- 811 callout in general notes — must match state of work
- "SEFNCO Communication, Inc." or other non-MasTec/Comcast company names in legal boilerplate
- Lat/Lon on cover sheet — must resolve to the address printed beside it
- State-route labels on any site plan — adds an MDOT region as a permit entity
- Description-of-work table totals — must agree with cover letter scope summary
