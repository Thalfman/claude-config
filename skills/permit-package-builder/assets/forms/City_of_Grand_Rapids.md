<!--
Template: City of Grand Rapids — Utility Construction Permit
The City of Grand Rapids uses the Citizen Access (Accela) portal as the
exclusive submission method for standard utility permits. There is no
PDF form; the portal collects fields, accepts attachments, and computes
the fee. This markdown template documents the field set the portal
expects so the data is captured ahead of the portal session.

Slot syntax: double-curly slot names. Renderer: scripts/render_application_form.py
GR permit landing: https://www.grandrapidsmi.gov/departments/engineering/apply-for-a-utility-permit/
GR portal: https://aca-prod.accela.com/GRANDRAPIDS/
-->

# City of Grand Rapids — Utility Construction Permit Application

**Submitted via:** Citizen Access (Accela) portal — https://aca-prod.accela.com/GRANDRAPIDS/
**Filing date:** {{date_today}}
**Reference:** {{jb}}

---

## 1. Eligibility (portal-gated)

By portal account, applicant is an authorized agent of a City-registered Metro Act or Franchise Utility.

| Field | Value |
|-------|-------|
| Authorized agent | {{applicant_legal_name}} |
| Franchise utility on file | {{franchise_utility}} |

## 2. Applicant

| Field | Value |
|-------|-------|
| Submitting contact | {{submitting_contact_name}} |
| Phone | {{submitting_contact_phone}} |
| Email | {{submitting_contact_email}} |
| Mailing address | {{applicant_address_line_1}}, {{applicant_address_line_2}} |

## 3. Project location

| Field | Value |
|-------|-------|
| Project name | {{project_name}} |
| Project address | {{address}} |
| Latitude | {{lat}} |
| Longitude | {{lon}} |

## 4. Scope of work

| Field | Value |
|-------|-------|
| One-clause scope | {{scope_clause}} |
| Aerial fiber (LF, on existing poles) | {{lf_aerial}} |
| Underground fiber (LF) | {{lf_underground}} |
| Surveyed poles | {{poles_count}} |
| Pole-attachment letters required | {{poles_count}} (one per non-Comcast-owned pole) |
| Construction type | {{primary_construction_type}} |
| Lane closure / parking-meter reservation | (pending — required if work zone affects metered curbside) |

## 5. Required attachments (uploaded via portal)

- [x] Site plan (the scrubbed CD, PDF)
- [ ] Traffic control plan (MUTCD-compliant)
- [ ] Certificate of Insurance (additional-insured: City of Grand Rapids; project location called out)
- [ ] Pole-attachment letters (one per non-Comcast-owned pole, when applicable)
- [ ] Parking-meter reservation (when applicable)

## 6. Insurance

| Field | Value |
|-------|-------|
| City published minimum | {{coi_min_gl}} |
| MasTec broker typical issuance | $1,000,000 GL |
| Additional-insured wording (verbatim, from Encroachment Permit) | {{coi_additional_insured}} |
| Notice of cancellation | {{coi_cancel_days}} days written, prior to cancellation |
| Project location callout | Required on certificate |

## 7. Fee

Engineering Department computes the Utility Construction Permit fee from submitted scope at application time per the FY26 Fee Schedule (line 263, "Varies — review, inspection, admin. of permit, each"). Fee finalized at portal submission.

Reference URL: {{entity_fee_schedule_url}} (retrieved {{entity_fee_schedule_retrieved}}).

## 8. Restoration deposit

Per-engineer determination at issuance; refundable on final inspection.

## 9. Miss Dig 811

Miss Dig 811 ticket will be obtained at least 3 working days prior to any excavation, per PA 174 of 2013.

## 10. Schedule

| Field | Value |
|-------|-------|
| Proposed start | To be coordinated with permit issuance (pending OPE confirmation — see open_items.md) |
| Receipt confirmation | 1–2 business days (per GR Engineering) |
| Substantive review | Depends on scope |

## 11. Signature (portal-acknowledged)

Submitted on behalf of {{franchise_utility}} as authorized agent. Account-level signature applies.

| Field | Value |
|-------|-------|
| Signed | {{submitting_contact_name}} |
| Title | MasTec submitting contact |
| Date | {{date_today}} |
