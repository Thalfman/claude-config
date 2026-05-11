# Known Boilerplate Errors

Drafter templates carry leftover content from prior jobs. The QC scrubs in `quality_checks.md` watch for these patterns and fire when they appear on the wrong job. The list below grows as the skill is exercised; append new entries when a new pattern is found.

## BP-001: Wrong-state 811 callout on Michigan work

**Reference:** `JB0002479252` (Grand Rapids, MI)
**Where:** CD General Notes Note 17 (page 3 typical)
**Pattern observed (verified verbatim 2026-04-28):**

> CALL THE "CALL BEFORE YOU DIG" NUMBER 48HRS IN ADVANCE AT 1-800-424-5555 PRIOR TO DIGGING.

The leftover does NOT contain the literal string "Indiana 811" in this drafter's
template. The fingerprint is the unbranded **wrong-state phone number**
(`1-800-424-5555` is not the current Miss Dig number) plus the **wrong notice
period** (`48HRS IN ADVANCE`; Michigan PA 174 of 2013 requires three working days).

**Should be (for MI work):**

> CALL MISS DIG 811 A MINIMUM OF THREE (3) WORKING DAYS PRIOR TO ANY EXCAVATION. DIAL 811 IN MICHIGAN OR (800) 482-7171. (PUBLIC ACT 174 OF 2013.)

**Detection regex (case-insensitive, MI work):**

```
(800.?424.?5555      # generic out-of-state placeholder seen in canonical ref
 |800.?382.?5544     # Indiana 811 number
 |800.?892.?0123     # JULIE (IL)
 |indiana\s*811
 |dig\s*alert
 |indiana\s*one\s*call
 |julie\b
 |48\s*HRS\s+IN\s+ADVANCE
 |48\s+HOURS\s+BEFORE\s+YOU\s+DIG
)
```

**Replacement reference:** `state_811_systems.md`

**Root cause:** Drafter forked the template from a different-state job. The
specific phone number and notice period in the boilerplate did not get
updated when the template was reused. The detection regex must NOT rely on
the literal "Indiana 811" string because the leftover may use only the
phone number, the notice-period phrase, or both.

**Implementation:** `scripts/scrub_cd.py` redacts these patterns and stamps a
yellow REVISION NOTE banner on every affected page with the corrected
wording. See `cd_scrubs.md` in any per-JB output folder for the full
change log.

## BP-002: SEFNCO Communication, Inc. legal boilerplate

**Reference:** `JB0002479252`
**Where:** CD general notes section, cover sheet legal block
**Pattern observed:** "SEFNCO Communication, Inc." appears in the legal boilerplate (work-for-hire language, indemnification, etc.) instead of MasTec or Comcast.

**Should be:** MasTec Communications Group OR Comcast (depending on which entity the boilerplate concerns; client-facing boilerplate names Comcast, contractor-facing names MasTec).

**Detection regex (case-insensitive):** `sefnco`
**Root cause:** Older drafter template, predates the MasTec branding consolidation. Several MasTec drafters' base templates carry SEFNCO boilerplate that did not get updated.

## How to scrub

The skill ships a working scrub at `scripts/scrub_cd.py`:

```bash
python -m scripts.scrub_cd <input.pdf> <output.pdf> --state MI
```

It does the following:

1. Opens the source PDF in PyMuPDF.
2. Searches every page for the BP-001 / BP-002 detection patterns and applies a
   white-fill redact annotation on each match.
3. Adds a yellow-bordered REVISION NOTE banner on every affected page that
   names the corrections (Miss Dig 811 phone, three-working-day notice,
   MasTec/Comcast company replacement).
4. Adds a larger REVISION NOTE on the cover sheet quoting the corrected
   General Notes Note 1 and Note 17 wording in full.
5. Re-opens the output PDF and confirms that none of the redacted target
   strings remain. Returns non-zero exit code on QC failure.

Save the output as a new PDF (do not overwrite the original; keep the
original for audit). Document the scrub in `cd_scrubs.md` (per-JB) and
research.md (per-entity) with the BP-id and the date of the scrub.

For final-final submission where pristine in-line replacement matters
(no visible gaps in Note 1 / Note 17), have the drafter regenerate the
General Notes sheet from the source `.dwg` and re-export the CD PDF.

## Adding a new entry

When a new boilerplate error is found:

1. Assign the next BP-id (BP-003, BP-004, ...).
2. Document the reference job, location in the CD, the exact pattern observed, the correct content, the detection regex, and the root cause if known.
3. Add the detection regex to `quality_checks.md`'s appropriate QC entry.
4. Add the replacement to the `scrub_boilerplate` function.
5. Test against the reference job and against a known-correct job; the scrub should fire on the former and not on the latter.

## Boilerplate categories worth watching

| Category | What to watch for |
|----------|-------------------|
| 811 callout | Wrong-state 811 system named (BP-001) |
| Company name | Old or third-party company name in legal text (BP-002) |
| Notice period | Wrong notice period (e.g., "two business days" when the state requires three) |
| Permit reference | A permit number from a prior job left in the title block or notes |
| Scale block | Wrong scale block (e.g., "1 INCH = 50 FEET" when the drawing is plotted at 1" = 40') |
| Drafter contact | Old drafter's email address still in the contacts block |
| Pole-owner reference | Wrong pole owner named in the description-of-work table |
| Address | Old project address from a forked template (rare; usually caught at title-block extraction time) |
