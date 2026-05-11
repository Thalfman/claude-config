# Per-Entity Research Checklist

For every `(JB, entity)` pair, the skill produces `output/<JB>/<NN_Entity>/research.md` populated against this checklist. Source URLs and retrieval dates are mandatory; without them, downstream review cannot verify whether the data is current.

## Required fields

| Field | Notes |
|-------|-------|
| Entity legal name | Exact wording for forms, COIs, and additional-insured language |
| Permit administrator name | Person who reviews and issues the permit |
| Permit administrator title | (e.g., "ROW Permit Coordinator") |
| Permit administrator phone | Direct line preferred over main switchboard |
| Permit administrator email | Verify email lands in the inbox (no bouncebacks) |
| Permit administrator office mailing address | For paper / hand-delivery submissions |
| Submission method | Online portal URL / email / paper / hand delivery / portal + paper |
| Application form URL | Direct download link to the current PDF/DOCX form |
| Application form version or date | Stamped on the form; if absent, use download date |
| Required attachments list | Entity-specific items beyond the canonical 10 |
| Fee schedule URL | Direct link to the fee table |
| Fee schedule retrieval date | Date the URL was last accessed |
| Fee calculation rules | Per-foot rate, flat fees, deposits, minimums |
| COI requirements | Limits, additional-insured wording, certificate-holder format |
| Bond / surety requirements | Amount, surety company restrictions, delivery method |
| Review timeline | Target days from complete submission to permit issuance |
| Pre-submission meeting | Required / Recommended / Not offered |
| Active moratoria | Paving moratorium dates, special-event exclusions, weather windows |
| Special districts | Historic district overlays, environmental overlays, business improvement districts |
| Verification: contact freshness | "Verified by [method] on [date] — replied / no response / bounced" |

## Research procedure

1. **Find the entity's current ROW permit landing page.** Web-search `"[entity legal name]" "right of way" permit`; preferred starting points: the entity's official `.gov`/`.org` site, then the state's local-government directory (in MI: https://www.michigan.gov/sos/elections).
2. **Confirm the permit administrator contact.** Cross-reference the landing page's contact listing against the entity's main directory. If they differ, prefer the landing page (more specific) but flag in research.md.
3. **Pull the current application form.** Download fresh; do not reuse a prior submission's form. Save as `application_form_<entity>_<date>.pdf` for archival.
4. **Pull the current fee schedule.** Save as `fee_schedule_<entity>_<date>.pdf` for archival.
5. **Compute the fee.** Line-by-line, partitioned by jurisdiction when the JB crosses multiple entities. Cite the schedule URL and retrieval date.
6. **Verify COI / bond requirements.** Pull the entity's current insurance requirements document if separate from the application form.
7. **Check for active moratoria.** Most entities post seasonal restrictions on a public works calendar; check for the proposed work window.
8. **Verify contact freshness.** When time permits, send a brief verification email to the permit administrator confirming the package will be submitted under the current process. A reply confirms the contact is current; no reply within a week is an Open Item.

## Per-entity templates (extend as the skill is exercised)

### Michigan Department of Transportation (MDOT) — region offices

> Verified 2026-04-28 against current MDOT publications.

- **Permit portal: MDOT Permit Gateway (MPG)** — https://www.michigan.gov/mdot/business/permit-gateway. (NOT "MERMAID" — that name is out of date.)
- MPG tech support: MDOT-MPG@Michigan.gov, (844) 806-0002 option 1.
- Submission: online via MPG (Construction Permit System / CPS); paper accepted by some regions but MPG is preferred.
- General Conditions document: **Form 2205-1** (rev 08/21), https://mdotjboss.state.mi.us/webforms/GetDocument.htm?fileName=2205-1.pdf
- Other utility forms (as applicable):
  - Form 2254 — Special Conditions for Private Utility-Type Facilities Transverse Crossings (rev 06/01/99)
  - Form PA-01 — Utility Cuts, Trenches and Pavement Replacement Permit Attachment (rev 04/30/01)
  - Form 3717 — Flowable Fill Special Provision for Utility Permits (rev 12/18/06)
- **Grand Region office (covers Kent County):** 1420 Front Avenue NW, Grand Rapids, MI 49504, (616) 451-3091.
- Fee framework: per Public Act 51 of 1951 (MCL 247.183) and the MPG application calculator. The MPG portal computes the fee from submitted scope at application time.
- **Additional-insured wording (verbatim from Form 2205-1 page 2):**
  > The State of Michigan, Michigan Transportation Commission, Department of Transportation, and governmental bodies performing permit activities under a maintenance contract, and all officers, agents, and employees of all the above, are named as additional insured for claims arising out of, under, or by reason of operations covered by the permits issued to the permittee.
- COI minimum: $1M general liability (recommended; verify per region at submission).
- Notice of cancellation: 30 days written notice required (Form 2205-1 §10).
- Review timeline: 30 to 45 days.
- Pre-submission meeting: recommended for complex corridor work; not required for utility access on existing aerial / UG plant.

### Kent County Road Commission (Michigan, verified 2026-04-28)

- **Office address:** 1900 4 Mile Road NW, Walker, MI 49544 (NOT 1500 Scribner Avenue NW; that address is wrong).
- **Phone:** (616) 242-6920
- **Email:** permits@kentcountyroads.net
- **Hours:** Monday–Friday, 7:30 AM – 3:30 PM
- Permit landing page: https://kentcountyroads.net/permits/
- Submission method: online (KCRC's permit form), email PDF, or in-person delivery.
- Online payment portal (up to $5,000): https://pay.payitgov.com/kent-roads
- Mail payments: KCRC, Permit Department, 1900 4 Mile Road NW, Walker, MI 49544
- **Fee schedule (effective 2025-04-01):** https://cms3.revize.com/revize/kentcounty/Documents/Permits/2025%20Permit%20Documents_fees.pdf
  - Aerial cable to existing poles: $100.00 (flat per project)
  - Underground mainline ≤1,000 LF: $300.00; >1,000 LF: $600.00 (per project)
  - Pole/anchor (>3 new): $150.00
  - Annual blanket utility maintenance: $200.00
  - Service tap/tie-in (not crossing road): $50.00
  - Open-cut roadway crossing: $350 (≤2 lanes) / $500 (multiple lanes)
  - Bore/jack ≤4" pipe: $100; >4" pipe: $200
  - Soil borings: $50/job min; $100 if >25 bores
- "Per project" definition: contained to a single Township; ≤2 lineal miles; continuous (no gap >0.5 mile). Waivers possible.
- Penalties: fees doubled if construction begins without a permit. Maximum civil fine $5,000 per violation per PA 283 of 1909, sec. 224.19b par. 2.
- COI: $1M GL standard (verify with KCRC); KCRC and its commissioners, officers, employees, and agents named additional insured.
- Soil Erosion and Sedimentation Control (SESC): KCRC is the Kent County SESC enforcing agency for Part 91 of PA 451. SESC permit is separate and required for any earth disturbance ≥1 acre or within 500 ft of a lake/stream.
- Review timeline: 14 to 21 days for standard utility ROW.
- **Jurisdiction note:** KCRC has road authority only over **unincorporated** Kent County. Roads inside an incorporated municipality (City of Grand Rapids, City of Walker, etc.) are the municipality's jurisdiction, not KCRC's.

### City of Grand Rapids (Michigan, verified 2026-04-28)

- **Engineering Department:** 300 Monroe Avenue NW, 5th Floor, Grand Rapids, MI 49503 (NOT 1120 Monroe; that address is wrong).
- **Phone:** (616) 456-3000 or dial 311
- **Email:** engineering@grcity.us
- Permit landing page: https://www.grandrapidsmi.gov/departments/engineering/apply-for-a-utility-permit/
- **Submission portal: Citizen Access (Accela)** — https://aca-prod.accela.com/GRANDRAPIDS/. The portal is the only way to submit standard utility permits.
- Eligibility: applicant must be an authorized agent of a City-registered Metro Act or Franchise Utility. MasTec acts as Comcast's agent; Comcast is the franchise utility on file.
- Application duration: ~20 minutes once data is gathered; saveable and resumable.
- Required attachments: site plan (the CD), traffic control plan (MUTCD-compliant), COI, plus parking-meter reservation if work zone affects metered curbside, plus pole-attachment letters for non-Comcast-owned poles.
- **FY26 Fee Schedule:** https://www.grandrapidsmi.gov/media/fnqdjzue/fy26-fee-schedule.pdf
  - **Utility Construction Permit (line 263):** "Varies — review, inspection, admin. of permit, each." Engineering computes fee from submitted scope at application.
  - Encroachment Permit (line 499; for permanent features in ROW, separate from utility): $330.00
  - Small Cell Wireless on Authority-owned pole rental: $22/yr; on post-2019 Authority-erected pole: $138/yr; on municipally-owned electric utility pole: $220/yr ($330 if engineering report required); new pole addition: $110.
- **COI requirement (verbatim from Encroachment Permit page):**
  > A certificate of insurance with a minimum of $500,000 liability that names the City of Grand Rapids as additionally insured and has the project location called out. The City must be notified in writing a minimum of 30 days prior to cancellation.
- City's published minimum is $500K GL; MasTec broker typically issues $1M+. Use $1M GL for the issued certificate.
- Restoration deposit: per-engineer determination at issuance; refundable on final inspection.
- Review timeline: 1–2 business days for receipt confirmation; substantive review depends on scope.
- Pre-submission meeting: not required for standard utility work.

### County Road Commissions (Michigan, generic)

- Submission method: typically paper or email; portals are rare
- Application form: per CRC website
- Required attachments: route exhibit, traffic control plan, COI; bond varies by CRC
- Fee schedule: published per CRC; verify
- COI: $1M general liability standard
- Review timeline: 14 to 30 days

### Townships (Michigan)

- MI townships do NOT issue road ROW permits in MI. Roads in unincorporated MI fall to the County Road Commission.
- The exception is some township-owned non-road facilities (parks, township-managed easements). Verify case-by-case.
- For OH and PA townships: townships DO issue road permits. Use the same checklist.

### Railroad operators (encroachment, not permit)

- Submission method: per the operator's licensing department (Norfolk Southern, CSX, Canadian National, etc.)
- "Application form" is an encroachment notice / license agreement, not a permit
- Required attachments: route exhibit at the crossing point, structural details for any aerial crossing, soil conditions for any bore, license fee
- COI: per operator's standard (often higher limits than ROW permits)
- Review timeline: 60 to 120 days; longer for new licenses
- Pre-submission meeting: often required for first-time licenses with that operator
