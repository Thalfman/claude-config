# State 811 Systems

The 811 callout on a CD must match the state where the work is being performed. Mismatched 811 callouts (e.g., Indiana 811 on Michigan work) are a common drafter-template leftover and must be scrubbed before submission. See `known_boilerplate_errors.md`.

## Lookup table

| State | 811 system name | Phone | URL | Notes |
|-------|-----------------|-------|-----|-------|
| MI | Miss Dig 811 | 811 (in MI) or (800) 482-7171 | https://missdig811.org | Statewide. Required for any excavation in MI. |
| IN | Indiana 811 | 811 (in IN) or (800) 382-5544 | https://indiana811.org | Statewide. Sometimes branded "Dig Alert" historically. |
| IL | JULIE | 811 (in IL) or (800) 892-0123 | https://illinois1call.com | Statewide except Chicago, which uses CHICAGO DIGGER (separate system inside city limits). |
| OH | OHIO811 | 811 (in OH) or (800) 362-2764 | https://www.oups.org | Statewide. Two-business-day notice. |
| WI | Diggers Hotline | 811 (in WI) or (800) 242-8511 | https://diggershotline.com | Statewide. Three-business-day notice. |
| KY | Kentucky 811 | 811 (in KY) or (800) 752-6007 | https://kentucky811.org | Statewide. Two-business-day notice. |
| TN | Tennessee 811 | 811 (in TN) or (800) 351-1111 | https://tn811.com | Statewide. |
| PA | PA One Call | 811 (in PA) or (800) 242-1776 | https://www.pa1call.org | Statewide. Three-business-day notice. |
| NY | Dig Safely New York | 811 (in NY) or (800) 962-7962 | https://www.digsafelynewyork.com | Statewide except NYC, Long Island, and parts of Westchester (separate systems). |
| OK | Oklahoma 811 | 811 (in OK) or (800) 522-6543 | https://callokie.com | Statewide. |
| TX | Texas811 | 811 (in TX) or (800) 344-8377 | https://www.texas811.org | Statewide. |
| FL | Sunshine 811 | 811 (in FL) or (800) 432-4770 | https://www.sunshine811.com | Statewide. Two-business-day notice. |

## Detection logic

The QC scrub looks for these patterns in the CD's general notes section and on the cover sheet:

- "Indiana 811", "Indiana One Call", "Dig Alert" → IN system in use
- "Miss Dig", "MISS DIG 811", "Miss Dig System" → MI system in use
- "JULIE" → IL system in use
- "OHIO811", "OUPS" → OH system in use

The state of work is determined from the title block (`State` field, or derived from the address). If the detected 811 system does not match the state of work, fire the scrub and flag for replacement.

## Replacement text patterns

When scrubbing the CD, replace ALL occurrences of the wrong-state 811 callout with the right-state one. The general notes section typically contains language like:

> Contractor shall contact [SYSTEM] a minimum of [N] working days prior to excavation.

Update both the system name and the notice period if they differ between states.

## Adding a new state

1. Add a row to the table above with system name, phone, URL, and notice period.
2. Add the detection patterns to `quality_checks.md`'s 811 scrub.
3. Add the replacement boilerplate text to `scripts/extract_cd_titleblock.py`'s patches dictionary.
4. Test against a CD known to be in the new state.
