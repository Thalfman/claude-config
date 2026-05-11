# MI Entity Registry — Schema Reference

The registry at `references/mi_entity_registry.json` is the canonical machine-readable source for permit entity data used by the skill. Scripts read it; humans edit it.

This document explains the schema, the verified-vs-stub distinction, the `inherits` mechanic, the verification policy, and how to add or refresh entries.

When the registry and a markdown reference disagree on a fact, **the JSON wins.** Markdown references (`entity_research_checklist.md`, `state_811_systems.md`, `mdot_regions_by_county.md`) are companions for prose context (research procedure, jurisdictional logic, escalation paths) — not duplicate sources of truth.

---

## File location

```
permit-package-builder/
  references/
    mi_entity_registry.json          ← canonical data
    mi_entity_registry_schema.md     ← this file
    registry_changelog.md            ← append a line on every refresh
  scripts/
    validate_registry.py             ← run after every edit
```

Run validation with:

```bash
python -m scripts.validate_registry
```

Exit 0 = registry is internally consistent. Exit 1 = something is broken; do not let downstream scripts run until it's fixed.

---

## Top-level structure

```
{
  "schema_version": "1.0.0",
  "registry": { metadata + verification_policy },
  "default_contacts": { MasTec / Comcast contacts },
  "state_811": { per-state 811 system },
  "mdot": {
    permit_gateway, common_forms, default_coi, fee_framework,
    county_to_region: { 83 counties → region name },
    regions: { 7 region entities },
    state_route_patterns: [ regex → entity rules ]
  },
  "county_road_commissions": { CRC entities },
  "municipalities": { city/village entities },
  "pole_owners": { joint-use pole owner entities },
  "railroad_operators_mi": { railroad operator entities },
  "environmental_overlays_mi": { EGLE / USACE / SESC etc. }
}
```

Every field with a leading underscore (`_note`, `_doc`, `_generic_template`, `_known_wrong_address`) is documentation or a template — scripts ignore them, humans read them. Use leading underscore for any field that should not be treated as data.

---

## Entity record shape

Every entity (regardless of category) carries the same skeleton. Optional fields may be `null` when not yet known.

```jsonc
"<entity_id>": {
  "category": "state_dot" | "county_road_commission" | "municipality"
            | "pole_owner" | "railroad" | "environmental",
  "state": "MI",                         // ISO 2-letter
  "legal_name": "...",                   // exact wording for forms and COI
  "verified_date": "YYYY-MM-DD" | null,  // ISO; null means stub
  "stub": true | false,                   // true = unverified placeholder

  "addressee": {
    "name_placeholder": "Region Permit Coordinator",
    "office": "...",
    "address": ["line1", "line2"]        // null if unknown
  },
  "phone": "(NNN) NNN-NNNN" | null,
  "email": "..." | null,
  "hours": "..." | null,

  "permit_landing_url": "https://..." | null,
  "submission": {
    "primary_method": "portal" | "email" | "paper" | "in_person" | "online_form" | "NJUNS",
    "portal_name": "...",
    "portal_url": "https://...",
    "secondary_methods": [...]
  },
  "application_form": { name, version, url, template_md },
  "fee": {
    "schedule_url": "...",
    "schedule_retrieved": "YYYY-MM-DD",
    "calculation_method": "line_items_lookup"
                         | "engineering_computes_at_submission"
                         | "portal_calculator",
    "line_items": [
      { "id": "...", "description": "...",
        "amount_usd": <number> | null, "unit": "...", "conditions": "..." }
    ]
  },
  "coi": {
    "minimum_general_liability_usd": <number>,
    "additional_insured_verbatim": ["..."],
    "additional_insured_source": "...",
    "notice_of_cancellation_days": <number>
  },
  "review_window_days": "14-21",
  "review_window": "1-2 business days for receipt; ...",  // free-form when needed
  "jurisdiction_notes": [...],
  "quirks": [...],
  "related_permits": [...]
}
```

Pole owners diverge slightly — they add `pole_tag_format` (a regex + examples for KML matching) and `joint_use` (Comcast master agreement reference, joint-use office). The shape is otherwise the same.

---

## Verified vs. stub

Every entity is **either** verified **or** a stub.

**Verified** (`stub: false` and `verified_date: <ISO date>`):
- Every field that scripts consume has a real value (URL, fee number, COI wording, addressee).
- The `verified_date` is the date a human last confirmed the data against authoritative sources.
- After `registry.verification_policy.stale_after_days` (default 90) the entry should be re-verified.

**Stub** (`stub: true` AND/OR `verified_date: null`):
- Entity is enumerated so scripts know it exists, but the data is incomplete or unconfirmed.
- A package using this entity cannot ship until the stub is upgraded to verified or the missing fields are filled in `open_items.md`.
- Stubs exist for two reasons: (1) the entity is in the lookup table (e.g. one of the 7 MDOT regions, even if only Grand is fully populated) so scripts don't fail on `KeyError`; (2) the user has anticipated that the entity will be hit soon and wants the schema slot ready.

The validator (`scripts.validate_registry`) flags any entity whose `stub` and `verified_date` disagree, e.g. `stub: false` with `verified_date: null`. Both states must be consistent.

---

## The `inherits` mechanic

MDOT regions and pole owners share most of their fields with their parent agency. To avoid duplication, an entity field can be a single-key object `{ "inherits": "<dotted-path>" }` instead of inline data. The dotted path resolves against the registry root.

Example:

```json
"MDOT_Bay_Region": {
  "category": "state_dot",
  "submission": {"inherits": "mdot.permit_gateway"},
  "application_form": {"inherits": "mdot.common_forms[0]"},
  "fee": {"inherits": "mdot.fee_framework"},
  "coi": {"inherits": "mdot.default_coi"},
  ...
}
```

When a script consumes the registry, it must resolve `inherits` references before using the data. Reference implementation:

```python
import re
def resolve_path(root, dotted):
    cur = root
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", dotted):
        cur = cur[int(part[1:-1])] if part.startswith("[") else cur[part]
    return cur

def deref(value, registry_root):
    if isinstance(value, dict) and set(value.keys()) == {"inherits"}:
        return resolve_path(registry_root, value["inherits"])
    return value
```

The validator checks every `inherits` reference resolves; broken references fail the run.

---

## Verification policy

The `registry.verification_policy` block declares two rules:

1. **Verified entries become stale after `stale_after_days` days** (default 90). When stale, re-verify before relying on the data — phone, address, portal URL, fee schedule, application form version, COI wording.

2. **Stub entries must be verified before any package ships** that uses them. The pre-flight render linter (forthcoming) will fail any draft that draws from a stub entity, forcing the user to either upgrade the stub or note the gap in `open_items.md`.

The policy also names the fields that `always_verify_before_submission`, regardless of staleness:

- `fee.schedule_url`
- `fee.line_items[*].amount_usd`
- `addressee.name`
- `submission.portal_url`
- `application_form.version`

These are the fields with the highest churn rates and the highest cost of being wrong (rejected applications, refused payment, wrong recipient).

---

## How to add a new entity

1. Pick the right top-level bucket: `county_road_commissions`, `municipalities`, `pole_owners`, `railroad_operators_mi`, or `environmental_overlays_mi`. (For state DOTs other than MDOT, add a new top-level key like `odot` parallel to `mdot`; the pattern is parallel.)

2. Pick an entity ID. Convention: `<TitleCase>_<TitleCase>` matching how the folder will be named. Examples: `City_of_Detroit`, `Wayne_County_DPS`, `Genesee_CRC`, `DTE_Energy`. Do not include the `NN_` numeric prefix — that's per-job priority and gets prepended at scaffolding time.

3. If you only know the legal name and county, write a stub:

   ```json
   "City_of_Lansing": {
     "category": "municipality",
     "state": "MI",
     "county": "Ingham",
     "legal_name": "City of Lansing",
     "verified_date": null,
     "stub": true
   }
   ```

   The validator will accept this. Subsequent submissions to this entity will surface the gap.

4. When you're ready to verify, fill the rest of the fields. Anchor every value to a source URL retrieved on a known date. When verification is complete:

   ```json
   {
     ...full data...,
     "verified_date": "2026-05-04",
     "stub": false
   }
   ```

5. Run `python -m scripts.validate_registry`. Fix any failures.

6. Append a line to `references/registry_changelog.md`:

   ```
   2026-05-04  Added City_of_Lansing (verified). Sources: [list of URLs].
   ```

---

## How to refresh a stale entity

1. Open the entity's record in the JSON.

2. For each `always_verify_before_submission` field, re-fetch the canonical source and update the value.

3. Set `verified_date` to today.

4. Run the validator.

5. Append a line to `registry_changelog.md`:

   ```
   2026-05-04  Refreshed Kent_CRC. Fee schedule updated from 2025-04-01 → 2026-04-01 schedule.
   ```

6. If anything material changed (fee math, COI wording, portal URL), also note it in the per-JB `open_items.md` for any in-flight package using that entity.

---

## Conventions

- **All URLs are full strings**, never relative.
- **Phone numbers** as `(NNN) NNN-NNNN` format. International phones include the `+1`.
- **Dollar amounts** as numbers (`100.00`), never strings (`"$100"`).
- **Addresses** as arrays of strings, one per line. Last line includes city, state, ZIP.
- **Dates** as ISO 8601 (`YYYY-MM-DD`).
- **Empty unknown** as `null`, not empty string `""`.
- **COI wording** stored verbatim including punctuation as it appears on the entity's form. Use a single string with explicit `\n` if line breaks matter, or a single-element array.
- **County names** spelled exactly as MDOT publishes them (`St. Clair` not `St Clair`; `Grand Traverse` with a space).
- **Leading underscore** marks documentation, schema templates, and notes that scripts must ignore.

---

## Why JSON, not YAML or TOML

JSON is:
- Stdlib in Python (zero dependencies)
- Stdlib in JavaScript (so a future web viewer needs nothing)
- Strictly schema-able (the validator uses plain dict walks, no parser quirks)
- Universal across the toolchain

The cost is comments — JSON has none — which is why we use leading-underscore fields (`_note`, `_doc`) as documentation carriers. Future tooling that produces JSON from a more-authorable source (YAML, JSON5) is welcome but the canonical form on disk stays JSON.
