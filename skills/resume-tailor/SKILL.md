---
name: resume-tailor
description: Use when the user provides a job description (text, URL, PDF, or .docx) and wants a tailored resume, asks for help applying to a specific role, requests resume customization for a posting, or wants their resume ATS-optimized for a target job. Handles single-job tailoring and multi-version generation against one master resume.
---

# Resume Tailor

Tailor a resume to a specific job description through **reframing, never fabrication**. Every claim in the tailored resume traces back to evidence in the user's master resume (or to information the user explicitly confirms during the workflow).

## Core Principle

**Tailoring is reframing, never invention.**

Allowed:
- Reordering experience (most relevant first)
- Synonym/terminology swap that preserves meaning
- Quantifying with numbers from the master or that the user confirms
- Contextualizing scope when the master supports it
- Dropping bullets that don't serve the JD

Forbidden:
- Inventing projects, employers, technologies, or scope
- Inflating numbers (team size, % impact, $, scale)
- Fabricating metrics that aren't in the master and weren't user-confirmed
- Listing skills the user has not demonstrated
- Changing dates, titles, or institutions

If the master doesn't support a JD requirement, mark it a GAP — ask the user, omit it, or address a transferable skill truthfully. **Never close a gap by inventing.**

## When to Use

Use when:
- User pastes a JD and asks "tailor my resume to this"
- User links to a job posting and wants help applying
- User wants ATS optimization for a specific role
- User wants multiple resume versions for similar postings

Do NOT use for:
- Building a master resume from scratch (use the Stage 1 interview path or a separate intake)
- Cover letters as the only deliverable (you can layer one on, but the workflow is resume-focused)
- General career coaching

## Inputs (Tier-Based)

Master resume input — use the highest tier available:

| Tier | Form | How to ingest |
|---|---|---|
| 1 | `master_inventory.json` matching `templates/resume_master_starter.json` | Use as-is |
| 2 | `.md` resume | Read with the Read tool, normalize into the inventory schema |
| 3 | `.docx` / `.pdf` resume | Read with the Read tool (Claude Code reads PDFs natively; for .docx use `python -m scripts.parse_master <path>`), normalize into the inventory schema |
| 4 | No resume — only conversation history | Interview the user (see "Interview path" below) before proceeding |

JD input forms:

| Form | Ingest |
|---|---|
| Pasted text | Use directly |
| `.pdf` / `.docx` | Read with the Read tool |
| URL | WebFetch (with the user's permission) |

## Workflow

Execute these stages in order. **Stop at Stage 4 and present the mapping to the user before drafting** — that gate is the fabrication firewall.

### Stage 1: Inventory the master resume

Read the master and normalize into the schema in `templates/resume_master_starter.json`. Save to `master_inventory.json` in the working directory.

For each bullet in the master, capture:
- `text` — verbatim
- `verbs` — action verbs used
- `scope` — `team_size`, `scale` ($, users, RPS, etc.), `duration` (only what's in the master; nulls are fine)
- `metrics` — numbers/percentages that already appear in the master
- `skills` — technologies/methodologies actually used in this work

**Do not invent fields.** If the master says "improved performance" with no number, leave `metrics: []`. Don't guess "20%".

#### Interview path (Tier 4)

If the user has no master, run a structured intake:
- One job at a time, oldest to newest (less recall pressure than newest-first)
- For each role, ask: company, title, dates, what the team did, what *you* did, scope (team size, scale), outcomes (numbers if any), technologies
- Save to `master_inventory.json` as you go
- Stop when the user signals "that's everything"

### Stage 2: Parse the JD

```bash
python -m scripts.parse_jd <jd_path_or_inline_text> --output jd_analysis.json
```

Extracts:
- Role title and inferred level (junior / mid / senior / staff / principal / director)
- REQUIRED qualifications (heuristic: "required", "must have", "minimum X years")
- PREFERRED qualifications ("preferred", "plus", "bonus", "nice to have")
- Responsibilities ("What you'll do", "Responsibilities")
- Hard skills (technologies, languages, frameworks)
- Soft skills (collaboration, communication, leadership signals)
- Cultural/values signals
- Dealbreakers (clearance, visa, on-site, travel %)
- Target keyword set with rough density targets

**Verify the extraction.** The script uses heuristics — it will miss things and over-extract things. Read `jd_analysis.json` and adjust before Stage 3.

### Stage 3: Score relevance

```bash
python -m scripts.score_relevance master_inventory.json jd_analysis.json --output relevance.json
```

For each JD requirement, the script ranks inventory bullets by:
- Direct skill match (skill in `bullet.skills` matches JD keyword)
- Synonym match via `references/synonyms.json` (PostgreSQL ↔ Postgres, etc.)
- Verb + domain co-occurrence
- Recency boost (recent roles weighted slightly higher)

Output `relevance.json` lists each JD requirement with:
- Top 0–N matching bullets (ranked by score)
- Coverage label: STRONG | PARTIAL | GAP
- Suggested reframing if the source uses different terminology

### Stage 4: Mapping review — STOP here

Print a clean mapping table to the user:

```
JD Requirement                              | Coverage | Source bullet (abridged)
--------------------------------------------+----------+--------------------------
5+ years backend Python                     | STRONG   | "Built Python services at Acme (2019–2024)…"
GraphQL experience                          | PARTIAL  | "Designed REST APIs at Acme…" (REST, not GraphQL)
Kafka or similar stream processing          | GAP      | (no match)
Lead a team of 5+ engineers                 | PARTIAL  | "Mentored 3 engineers…" (3, not 5)
…
```

Ask the user to:
- Confirm STRONG/PARTIAL classifications
- Provide info to upgrade GAPs (or accept they'll be omitted)
- Add scope/numbers where the inventory has nulls but the user remembers them
- Note any bullets they want kept regardless of JD fit (credibility/personality bullets)

**Do not draft the resume until the user has reviewed.** This is the fabrication firewall.

### Stage 5: Draft the tailored resume

After user sign-off, produce a markdown resume.

**Default template:** `templates/resume_chronological.md` (reverse-chronological).
Switch to `templates/resume_hybrid.md` if the user is a career changer or has gaps — leads with a Skills/Highlights block.

**Section order (chronological):** Header → Summary (optional) → Experience → Skills → Education → Certifications → Projects.

**Bullet rules:**
- Strong action verb first (see `references/action_verbs.md`)
- Quantify where data exists (numbers, %, $, scale, time)
- Use JD terminology where it preserves meaning (synonym swap, not meaning swap)
- One line preferred, two lines max
- Past tense for past roles, present tense for current
- Canonical casing for technologies (PostgreSQL, JavaScript, GraphQL)

**Allowed transformations (reframing):**
- "Improved system performance" + master metric `35%` → "Improved system performance by 35%"
- "Built REST API" + JD asks "API design" → "Designed and built REST API"
- "Worked with team" + master scope `team_size: 7` → "Collaborated with 7-engineer team"

**Forbidden transformations (fabrication):**
- "Built REST API" → "Built GraphQL API" (changes technology)
- "Improved performance" → "Improved performance by 50%" without source metric
- "Worked with team" → "Led team" (changes role)
- "Mentored 3 engineers" → "Led team of 5+" (inflates scope)

**Length guideline:**
- 0–7 years: 1 page
- 7–15 years: 2 pages
- 15+ or executive: 2–3 pages

**Skills section:** only skills demonstrated in experience or in `inventory.skills`. No "exposed to" entries.

**Calibrate language to role level** using `references/role_levels.md`.

### Stage 6: Audit the draft

```bash
python -m scripts.audit_claims tailored_resume.md master_inventory.json --output audit_report.md
```

The audit flags:
- Numbers in the tailored resume not in the inventory
- Skills in the resume not in the inventory's skills lists
- Companies / titles / dates not matching the inventory
- Bullets with no clear inventory source

Read `audit_report.md`. Every FLAGGED item must be:
- Removed from the resume, OR
- Corrected to match the inventory, OR
- Confirmed by the user (and added to the inventory before re-running the audit)

**Do not move to outputs until the audit is clean.**

### Stage 7: Build outputs

```bash
python -m scripts.build_outputs tailored_resume.md jd_analysis.json relevance.json \
    --formats md,docx --output-dir outputs/
```

Produces:
- `outputs/<First>_<Last>_Resume_<Role>_<Company>.md` — markdown source-of-truth
- `outputs/<First>_<Last>_Resume_<Role>_<Company>.docx` — ATS-safe Word doc (if `docx` requested)
- `outputs/<First>_<Last>_Resume_<Role>_<Company>.pdf` — PDF (if `pdf` requested and `docx2pdf` available; otherwise the script prints a "open in Word and Save As PDF" instruction)
- `outputs/mapping_report.md` — JD requirement → tailored bullet trace
- `outputs/coverage_scorecard.md` — % of requirements addressed, gaps, ATS-keyword density

For Word features beyond the ATS-safe template (custom letterhead, tracked changes, comments), layer the `document-skills:docx` skill on top after this skill produces the markdown source.

## ATS-Safe Formatting (non-negotiable)

For the .docx/.pdf outputs:

- Single-column layout
- No tables in Experience or Skills
- Standard section headings: "Experience", "Education", "Skills", "Certifications", "Projects"
- Standard fonts: Calibri, Arial, Helvetica, Times New Roman, Georgia
- 10–12pt body, 14–16pt name
- Dates in `MMM YYYY – MMM YYYY` or `MMM YYYY – Present`, consistent throughout
- No headers/footers for contact info (some ATS skip those regions)
- No images, icons, charts, graphics, or text boxes
- Plain bullet character (•) or hyphen, not Wingdings glyphs
- File name: `<First>_<Last>_Resume_<Role>_<Company>.docx`

Full rule set with reasoning: `references/ats_safe_formatting.md`.

## Quality Bar

> Generated through structured tailoring against a specific JD. Every claim traces to the candidate's master resume — but the user owns final accuracy review. AI-generated phrasing should be read aloud and adjusted to match the user's natural voice before submission.

Include this disclaimer (or a paraphrase) in any cover letter generated alongside, and remind the user before they submit.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Drafting before user review of the mapping (Stage 4) | STOP at Stage 4. Always. The mapping IS the fabrication firewall. |
| Adding skills to "Skills" section because the JD lists them | Only list skills demonstrated in experience or in the master's skills block. JD asks the user can't demonstrate are gaps. |
| Quantifying with placeholder numbers ("Improved performance by ~50%") | Use a real number from the master, or don't quantify. No placeholders. |
| Synonym swap that changes meaning | "Designed and built" ≠ "Architected from scratch". Preserve meaning. |
| Dropping every bullet that doesn't match the JD | Some bullets are credibility/personality carriers. Discuss with the user. |
| Producing .docx without running the audit | Audit gate is mandatory. Drift compounds across versions. |
| "Worked on", "Responsible for", "Helped with" | Replace with action verbs. See `references/action_verbs.md`. |
| Stuffing JD keywords without context | Density target is 1–2% per critical keyword, contextually placed in real bullets. |

## Red Flags — STOP

- A claim in the tailored resume you can't trace to a specific inventory bullet
- A number in the resume that wasn't in the inventory
- A skill listed that the user has not demonstrated
- A reframing that changes the technology, scope, or role
- The thought "I'll just add this since the JD asks for it"
- Tailoring before the user has signed off on the mapping table

Each of these means: stop, return to the relevant stage, fix.

## Files in this Skill

- `SKILL.md` — this document
- `scripts/parse_jd.py` — JD analyzer (regex + light section detection)
- `scripts/parse_master.py` — master resume normalizer (handles .md / .docx; .pdf via Read tool by Claude)
- `scripts/score_relevance.py` — JD requirement → inventory evidence matcher
- `scripts/audit_claims.py` — fabrication audit
- `scripts/build_outputs.py` — markdown / docx / pdf output builder
- `templates/resume_master_starter.json` — empty inventory schema
- `templates/resume_chronological.md` — default template
- `templates/resume_hybrid.md` — skills-first template (for career changers / gappers)
- `references/action_verbs.md` — categorized strong action verbs
- `references/ats_safe_formatting.md` — full ATS rules with reasoning
- `references/quantification_patterns.md` — CAR/STAR + metric patterns
- `references/role_levels.md` — language calibration by level
- `references/synonyms.json` — terminology equivalence map
- `requirements.txt` — Python dependencies
- `tests/` — pytest tests with programmatically generated fixtures
