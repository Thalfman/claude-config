---
name: operators-ticket-pack
description: Use when an operator wants a paste-ready prompt to delegate one job to Claude Code, Codex, or a bash loop with a proof gate, boundary, budget, and fallback. Covers 8 verbatim templates - migration, bug hunt, coverage climb, refactor, invoice extraction, inbox triage, content repurpose, lead qualifier. Triggers on "write me a ticket", "delegate to Claude Code", "five-part ticket", "proof gate", "Ralph Wiggum Loop", or "DOO MADE".
source: The Operator's Ticket Pack - DOO MADE (May 2026). Companion to the Ralph Wiggum Loop video on DOO MADE.
---

# Operator's Ticket Pack

8 verbatim five-part tickets for delegating one job to an AI agent. The proof gate decides done, not the agent. Source: DOO MADE.

## When to fire

- Operator wants to delegate a task to Claude Code / Codex / a bash loop and asks for a "ticket" or "prompt".
- Task fits one of: migration, bug hunt, coverage, refactor, invoice extraction, inbox triage, content repurpose, lead qualifier.
- Operator references DOO MADE, the Ralph Wiggum Loop, the five-part ticket, the proof gate, or any of order / proof / boundary / budget / fallback.

**Do not fire when:** operator wants the work executed here. This skill emits text; the downstream agent runs it.

## The 8 tickets

| # | Ticket | One-line use |
|---|--------|--------------|
| 01 | Migration | Move from `[SOURCE LIB]` to `[TARGET LIB]`, behavior preserved |
| 02 | Bug Hunt | Get failing tests in a dir passing without touching prod logic |
| 03 | Coverage Climber | Raise coverage on a module to `[%]`, meaningful assertions |
| 04 | Refactor | Merge functions >=70% overlap; line count must drop |
| 05 | Invoice Extractor | PDF invoices -> CSV; line totals sum to document total |
| 06 | Inbox Triage | Emails -> urgent / this-week / archive with one-line reasons |
| 07 | Content Repurposer | Source asset -> tweet thread + LinkedIn + pull-quote (JSON) |
| 08 | Lead Qualifier | Score leads 1-10 vs rubric; output ranked CSV |

Full decision matrix: `reference/decision-matrix.md`.

## Workflow when triggered

1. **Pick the ticket.** Map the task to one of the 8. If two fit, show both and ask.
2. **Open the template.** Read `templates/0X-name.md` for the bracket list and verbatim wording.
3. **Collect brackets in one batch.** Ask all at once. Do not drip questions.
4. **Fill verbatim.** Replace each `[BRACKET]`. Do not rephrase the Order, Proof, Boundary, Budget, or Fallback wording. The exact words are load-bearing.
5. **Restate the proof gate** in one plain-English sentence: "Done = [proof condition in plain words]."
6. **Emit the filled ticket** as a single fenced code block, paste-ready for Claude Code / Codex `/goal` / a bash loop. Do not execute it.

## Quality check before returning

- Every bracket filled or annotated `[TBD: reason]`
- Proof gate restated in plain English
- Budget present (fail loud if absent)
- Fallback present and concrete

## Guardrails

- **Never weaken a proof gate or remove a boundary.** If the operator pushes to soften, surface the trade-off and let them decide. Do not soften by default.
- **Never invent new tickets in v1.** If nothing fits, show the two closest from the matrix and stop. Custom-ticket support may land in v2.
- **Never execute the filled ticket.** Skill produces text. Downstream agent runs it.
- **Verbatim means verbatim.** No paraphrase, no smoothing, no "improvement". Every line in PROOF / BOUNDARY / BUDGET / FALLBACK blocks a specific reward-hack documented in `reference/failure-modes.md`.

## Default budgets (from the PDF)

| Ticket | Budget |
|--------|--------|
| 01 Migration | 30 turns OR 60 min, whichever first |
| 02 Bug Hunt | 20 turns OR 30 min, whichever first |
| 03 Coverage Climber | 25 turns OR 45 min, whichever first |
| 04 Refactor | 20 turns OR 40 min, whichever first |
| 05 Invoice Extractor | N invoices (operator picks N) |
| 06 Inbox Triage | all emails OR 200, whichever first |
| 07 Content Repurposer | 10 turns |
| 08 Lead Qualifier | all leads OR 200, whichever first |

## Ambiguities the operator must resolve

Some templates carry intentional vagueness. Surface it as a question, do not silently default. See `reference/failure-modes.md` for the full list. The most common:

- **Refactor "70% structural overlap"** - quantitative or qualitative? Give examples, let the operator decide.
- **Coverage "meaningful assertion"** - operator defines the line. (`assert True` no; `assert x == 5` yes; assertion on a mock-return borderline.)
- **Inbox Triage "urgent in 24h"** - 24h from receipt or from now? Operator clarifies.
- **Inbox Triage email format** - MBOX / CSV / JSON / IMAP? Ask up front.
- **Refactor git assumptions** - `git restore` needs a clean working tree. Note this in the handoff.

## Assumed defaults when info is missing

- **Budget:** PDF default for that ticket.
- **Fallback artifact location:** current working directory (operator can override).
- **Protected directories:** none - but flag the gap so the operator can name them.

## Files in this skill

- `templates/01-08-*.md` - the 8 verbatim templates with bracket lists, plain-English proof gate, and one filled example each
- `reference/five-part-structure.md` - what Order / Proof / Boundary / Budget / Fallback mean
- `reference/glossary.md` - domain terms (proof gate, the cook, reward-hacking, etc.)
- `reference/decision-matrix.md` - task -> ticket mapping
- `reference/failure-modes.md` - the specific reward-hack each PROOF / BOUNDARY / FALLBACK blocks
- `examples/coding-tickets-filled.md` - extra worked examples for 01-04
- `examples/operator-tickets-filled.md` - extra worked examples for 05-08
- `README.md` - install + DOO MADE / Ralph Wiggum Loop credit
