<!--
Template: Kent County Road Commission — Utility Permit Application
Mirror of the field structure on KCRC's online permit form.
Slot syntax: double-curly slot names. Renderer: scripts/render_application_form.py
KCRC permit landing: https://kentcountyroads.net/permits/
This template is a slot-filled markdown rendition for archival; the actual filing goes through KCRC's online form, by email PDF, or in-person.
-->

# Kent County Road Commission — Utility Permit Application

**Submitted via:** {{entity_portal_name}}
**Filing date:** {{date_today}}
**Reference:** {{jb}}

---

## 1. Applicant

| Field | Value |
|-------|-------|
| Applicant legal name | {{applicant_legal_name}} |
| Role | {{applicant_role}} (acting on behalf of {{franchise_utility}}) |
| Mailing address | {{applicant_address_line_1}} |
| | {{applicant_address_line_2}} |
| Submitting contact | {{submitting_contact_name}} |
| Phone | {{submitting_contact_phone}} |
| Email | {{submitting_contact_email}} |

## 2. Project location

| Field | Value |
|-------|-------|
| Project name | {{project_name}} |
| Project address | {{address}} |
| City / Township | {{city}} (verify if unincorporated — KCRC jurisdiction is unincorporated Kent County only) |
| County | {{county}} |
| Latitude | {{lat}} |
| Longitude | {{lon}} |
| Township / Range / Section | {{township}} {{range}} {{section}} (Qtr: {{qtr_section}}) |

## 3. Scope of work

| Field | Value |
|-------|-------|
| One-clause scope | {{scope_clause}} |
| Aerial fiber (LF, on existing poles) | {{lf_aerial}} |
| Underground fiber (LF) | {{lf_underground}} |
| Surveyed poles in corridor | {{poles_count}} |
| New poles / anchors | (pending — KMLs typically show only existing surveyed poles; transcribe new pole/anchor count from CD if any) |
| Open-cut crossings | (pending — transcribe from CD description-of-work table) |
| Bores | (pending — transcribe from CD description-of-work table) |
| Soil borings | (pending — transcribe from CD description-of-work table) |
| Construction type | {{primary_construction_type}} |

## 4. Per-project compliance

KCRC defines "per project" as: contained to a single Township; ≤2 lineal miles; continuous (no gap >0.5 mile). Confirmed for this submission.

## 5. Required attachments

- [x] Construction drawings (scrubbed CD)
- [x] Route exhibit / KML
- [ ] Traffic control plan (MUTCD typical TA-# or custom TCP)
- [ ] Certificate of Insurance (additional-insured: KCRC and its commissioners, officers, employees, and agents)
- [ ] SESC permit (separate filing — required when earth disturbance ≥1 acre OR within 500 ft of a lake/stream)

## 6. Insurance

| Field | Value |
|-------|-------|
| Minimum general liability | {{coi_min_gl}} |
| Additional-insured wording (verbatim) | {{coi_additional_insured}} |
| Certificate source | {{coi_source}} |

## 7. Miss Dig 811

Miss Dig 811 ticket will be obtained at least 3 working days prior to any excavation, per PA 174 of 2013.

## 8. Schedule

| Field | Value |
|-------|-------|
| Proposed start | To be coordinated with permit issuance (pending OPE confirmation — see open_items.md) |
| Review window | {{entity_review_window}} |

## 9. Fee

Fee per current KCRC fee schedule (effective {{entity_fee_schedule_effective}}). Computed line items in `fee_calculation.pdf`. Payment by online portal ({{entity_online_payment_url}}, up to ${{entity_online_payment_limit}}) or by check to "Kent County Road Commission" mailed to {{entity_addressee_address}}.

## 10. Signature

Submitted on behalf of {{franchise_utility}} as authorized agent.

| Field | Value |
|-------|-------|
| Signed | {{submitting_contact_name}} |
| Title | MasTec submitting contact |
| Date | {{date_today}} |

---

> **Penalty notice:** Fees doubled if construction begins without a permit. Maximum civil fine $5,000 per violation per PA 283 of 1909, sec. 224.19b par. 2.
