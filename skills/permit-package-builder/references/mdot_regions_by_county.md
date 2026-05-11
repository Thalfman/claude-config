# MDOT Regions by County (Michigan)

> **Canonical source for scripts:** `references/mi_entity_registry.json` → `mdot.county_to_region` (full 83-county table) and `mdot.regions` (per-region entities). This markdown is the human-readable companion; when the two ever disagree, the JSON wins.
>
> **Verify against MDOT's current published boundaries before relying on either source for a submission.**
> MDOT source: https://www.michigan.gov/mdot
> Snapshot date for this companion: 2026-04-27. Registry was synchronized 2026-05-04. MDOT periodically reorganizes region boundaries; both sources are reference only — confirm before submission.

MDOT operates seven regions. Each region has its own permit office and its own utility permit application form. State-route work (any I-, US-, M-, BL, or BR designated road) requires an MDOT permit from the region office covering the project county.

## Region table

| Region | Counties (snapshot) | Region office |
|--------|---------------------|---------------|
| Superior | Alger, Baraga, Chippewa, Delta, Dickinson, Gogebic, Houghton, Iron, Keweenaw, Luce, Mackinac, Marquette, Menominee, Ontonagon, Schoolcraft | Ishpeming |
| North | Alcona, Alpena, Antrim, Benzie, Charlevoix, Cheboygan, Crawford, Emmet, Grand Traverse, Iosco, Kalkaska, Leelanau, Manistee, Missaukee, Montmorency, Ogemaw, Oscoda, Otsego, Presque Isle, Roscommon, Wexford | Cadillac |
| Bay | Arenac, Bay, Clare, Genesee, Gladwin, Gratiot, Huron, Isabella, Lapeer, Midland, Saginaw, Sanilac, Shiawassee, Tuscola | Saginaw |
| Grand | Ionia, Kent, Lake, Mason, Mecosta, Montcalm, Muskegon, Newaygo, Oceana, Osceola, Ottawa | Grand Rapids |
| Southwest | Allegan, Barry, Berrien, Branch, Calhoun, Cass, Kalamazoo, St. Joseph, Van Buren | Kalamazoo |
| University | Clinton, Eaton, Hillsdale, Ingham, Jackson, Lenawee, Livingston, Monroe, Washtenaw | Lansing or Brighton |
| Metro | Macomb, Oakland, St. Clair, Wayne | Southfield |

## Reference deliverable

`JB0002479252` is in Kent County → MDOT Grand Region (region office: Grand Rapids). When the JB0002479252 CD's site plans show a state-route label such as M-37 or US-131, the MDOT Grand Region permit application is required in addition to the Kent CRC and City of Grand Rapids applications.

## Lookup logic (used by `derive_entities_modeC.py`)

The lookup table now lives in the registry, not in this file. Loading pattern:

```python
import json
from pathlib import Path

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "references" / "mi_entity_registry.json"

def _registry():
    return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))

def mdot_region_for_county(county_name_mi: str) -> str:
    """
    Returns the MDOT region name for a Michigan county
    (e.g., "Kent" → "Grand", "Wayne" → "Metro").
    Raises KeyError if the county is not in the registry — which
    should never happen for a valid MI county; if it does, the
    registry is incomplete or the input is mis-spelled.
    """
    return _registry()["mdot"]["county_to_region"][county_name_mi]
```

The registry's table covers all 83 MI counties and is validated by `scripts/validate_registry.py`. If `derive_entities_modeC.py` raises a `KeyError`, the input county name is wrong (check spelling: `St. Clair` not `St Clair`; `Grand Traverse` with a space).

## How to verify

1. Open https://www.michigan.gov/mdot and navigate to "Doing Business" → "Permits" → "Region office contact map" (the path may change; search for "MDOT region map" if the navigation has been reorganized).
2. Confirm the region for the project county against the published map.
3. If the table here is wrong for any county, edit this file and update `derive_entities_modeC.py`'s lookup. Add a note in the per-JB Open Items file recording the verification.

## State-route patterns to detect on site plans

| Pattern | Meaning | Adds entity |
|---------|---------|-------------|
| `I-##` | Interstate | MDOT region for that county |
| `US-##` | US highway | MDOT region for that county |
| `M-##` | State trunkline | MDOT region for that county |
| `BL ##` | Business loop | MDOT region for that county |
| `BR ##` | Business route | MDOT region for that county |

These regex patterns appear on site plan road labels and in the description-of-work table. Match case-insensitively, allow space or hyphen between the prefix and the number.

## Notes

- MDOT permits are separate from city/township/county permits and are filed with the region office, not with the central MDOT office in Lansing.
- Some MDOT routes inside incorporated municipalities have shared jurisdiction; both MDOT and the municipality may require permits. When in doubt, file both and note the duplication in research.md.
- MDOT's online permit portal is the **MDOT Permit Gateway (MPG)** — https://www.michigan.gov/mdot/business/permit-gateway. (The older name "MERMAID" is out of date.) Tech support: MDOT-MPG@Michigan.gov, (844) 806-0002 option 1. Some regions still accept paper submissions; MPG is preferred and accepted across all regions.
- Construction Permit Application is filed via MPG's Construction Permit System (CPS). The General Conditions document (Form 2205-1, rev 08/21) is bundled with every issued permit; download at https://mdotjboss.state.mi.us/webforms/GetDocument.htm?fileName=2205-1.pdf for COI / additional-insured wording reference.
