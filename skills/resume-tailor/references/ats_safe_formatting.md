# ATS-Safe Formatting

ATS = Applicant Tracking System. Most large employers use one (Workday, Greenhouse, Lever, Taleo, iCIMS, SuccessFactors, Bullhorn, etc.). They parse your resume into structured fields. Bad formatting breaks parsing, which means a human may never see the resume.

These rules are conservative — they work across the major systems. You give up some visual polish; you gain reliability.

## Layout

| Rule | Why |
|---|---|
| Single column | Multi-column layouts confuse parsers; text from the right column gets interleaved with the left |
| No tables in Experience or Skills | Some parsers ignore table cells or read them in column order, scrambling content |
| No text boxes | Often dropped entirely by parsers |
| No headers/footers for contact info | Many ATS skip header/footer regions |
| Reading order top-to-bottom, left-to-right | What you see is what the parser sees only if reading order is linear |
| Margins ≥ 0.5" on all sides | Some parsers crop edges |

## Typography

| Rule | Why |
|---|---|
| Standard fonts only | Calibri, Arial, Helvetica, Times New Roman, Georgia. Custom fonts may render as boxes or get substituted |
| 10–12pt body, 14–16pt name | Smaller fails OCR (some ATS OCR PDFs); larger wastes space |
| Bold for emphasis, not all-caps | All-caps reads as a heading to some parsers, breaking sections |
| One bullet character throughout | Use • or - consistently. Avoid Wingdings glyphs |
| No italics for content (titles okay) | Some OCR confuses italic body text |
| Black text only (or near-black like #1a1a1a) | Color is fine for headings/links but not body |

## Sections

| Rule | Why |
|---|---|
| Standard heading names | "Experience" / "Work Experience" / "Professional Experience"; "Education"; "Skills"; "Certifications"; "Projects". ATS look for these tokens to segment the document |
| Avoid creative headings | "What I've Done", "My Toolkit", "Adventures" → parser doesn't recognize; content goes into "Other" or gets lost |
| Section heading on its own line | Inline headings ("Experience: …") break parsing |
| Consistent section ordering | Reverse-chrono Experience first (after header/summary), then Education, then Skills/Certs |

## Dates

| Rule | Why |
|---|---|
| `MMM YYYY – MMM YYYY` or `MMM YYYY – Present` | Most ATS parse this format reliably |
| Consistent format throughout | Mixing "2021-2023" and "Mar 2021 – Apr 2023" causes some parsers to fail one or both |
| En-dash or hyphen, not "to" | Word converts " to " inconsistently; dash is parsed as a range |
| No "current" — use "Present" | "Current" is also fine but "Present" is more universal |

## Contact

| Rule | Why |
|---|---|
| In the body, not in the header/footer | See above — header/footer regions get skipped |
| Email and phone on separate lines or separated by `|` | Comma-separated is fine; tab-separated breaks some parsers |
| URLs as plain text (linkedin.com/in/firstlast) | Some parsers strip hyperlinks but keep the visible text — make sure the visible text is the URL |
| No icons next to email/phone | Icons get dropped; if the parser was relying on them as separators, fields collide |

## Bullets

| Rule | Why |
|---|---|
| One bullet per achievement | Multi-sentence bullets get truncated by some parsers |
| One line preferred, two lines max | Three+ lines reduce keyword density visually |
| No nested bullets | Indented sub-bullets are unreliable across parsers |
| Plain bullet character | • or - or *. Avoid → ✦ ✪ etc |

## Skills section

| Rule | Why |
|---|---|
| Comma-separated or pipe-separated, not table | Tables in Skills are a top reason for parse failure |
| Group by category (Languages / Frameworks / Tools / Domains) | Helps both ATS keyword matching and human scanning |
| Only skills demonstrated in experience | Skills not backed by experience get the resume rejected by humans even if ATS accepts it |
| No proficiency bars / star ratings | Pure visual — ATS drops them and you lose information |

## File format

| Rule | Why |
|---|---|
| Submit `.docx` if the system accepts it | Most reliable parser format |
| Submit `.pdf` only if the system asks for PDF | Modern ATS handle PDF, but text-as-image PDFs (printed-then-scanned) fail |
| Never submit a Pages or Google Docs export without checking format | Format conversion sometimes scrambles dates |
| File name: `<First>_<Last>_Resume_<Role>_<Company>.<ext>` | Helps the recruiter find it in a sea of "resume.pdf" |

## What to skip

- Photos / headshots (illegal to consider in many jurisdictions; many ATS strip them)
- Charts / graphs / skill-level visualizations
- Background colors or shading
- Page borders
- Watermarks
- "References available upon request" (assumed)
- Address (street; city/state is fine, increasingly optional)
- Date of birth, marital status, gender (illegal in many jurisdictions; never include in US/UK/CA/AU)

## Smoke test

Open the .docx in a plain text editor (or copy-paste into Notepad). The text should read as a clean, linear document with no jumbled order. If you see column 1 row 1 / column 2 row 1 / column 1 row 2 — your layout is broken for ATS. If sections appear out of order — your section headings aren't being recognized.

## When to break these rules

For roles where the resume is reviewed primarily by humans (small companies, internal referrals, designer roles), visual polish matters more and these rules can flex. But the default is ATS-safe.

If a job posting explicitly says "We use [ATS Name]" — Google that ATS's parsing quirks before submitting.
