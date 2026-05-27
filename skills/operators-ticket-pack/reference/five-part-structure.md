# The five-part structure

Every ticket has five parts. Each part has a job. Skip a part and the agent will find a way to cheat.

## 1. The Order

**Job:** State the goal and the acceptance criteria as concrete bullets the agent can verify.

- Use direct, scannable bullets.
- "All existing functionality continues to work without behavior changes" is acceptance criteria. "Make it better" is not.
- An order without proof is a wish.

## 2. The Proof

**Job:** Define the test that decides done - deterministic, mechanical, no human judgment required.

Common proof shapes:
- Exit code (`pytest` exits 0, `make` exits 0)
- Grep result (`grep -r "foo" src/` returns zero matches)
- Format check (the CSV parses cleanly; the JSON parses cleanly)
- Checksum (sum of line_total matches document_total)
- Word / character / structural count

The proof gate decides ship vs. garbage. If you cannot write the proof, you do not yet have the ticket.

**Never paraphrase the proof gate when filling a template.** The exact wording is load-bearing.

## 3. The Boundary

**Job:** Say what the agent must NOT do. Block the specific reward-hacks for this task.

Boundaries usually take the form:
- "Do not modify [test files / production code / source data]."
- "Do not skip failing tests."
- "Do not invent statistics not in the source."

Each boundary in the PDF tickets blocks a *specific* observed reward-hack. Do not remove a boundary when filling a template, even if it looks obvious. It is there for a reason. See `reference/failure-modes.md` for the exact hack each line defends against.

## 4. The Budget

**Job:** Hard stop in turns AND minutes - whichever hits first.

- "Stop after 30 turns OR 60 minutes, whichever hits first."
- For data-shaped tickets (invoices, emails, leads), the budget is a count: "Stop after N invoices" / "Stop after 200 emails".

If a budget is missing, the loop can run forever. The skill must fail loud if the operator does not provide one (or accept the PDF default).

## 5. The Fallback

**Job:** Define a graceful exit when blocked. Write a diagnostic artifact; do not loop forever.

Conventions from the PDF:

| Ticket | Fallback artifact |
|--------|-------------------|
| 01 Migration | `ERROR.md`, `MIGRATION_GAPS.md` |
| 02 Bug Hunt | `BUG_REPORT.md` |
| 03 Coverage Climber | `COVERAGE_GAPS.md` |
| 04 Refactor | `REFACTOR_CANDIDATES.md` (after `git restore` retries) |
| 05 Invoice Extractor | `REVIEW_NEEDED.csv`, `PARSE_ERRORS.md` |
| 06 Inbox Triage | row in `triage.csv` with "unclear, needs human review" |
| 07 Content Repurposer | `REPURPOSE_NOTES.md` |
| 08 Lead Qualifier | score 0 + "insufficient data: [FIELD]" reason |

A fallback is the loop's escape hatch. Without one, the agent will either silently fail or burn the budget chasing dead-ends. The fallback file is also a useful artifact for the operator - it documents what was tried and what was left.

## Assumed defaults when info is missing

- **Fallback artifact location:** current working directory unless the operator specifies otherwise.
- **Budget:** PDF default unless the operator overrides.
- **Protected directories:** none by default - but the skill should flag the gap so the operator can name them.

## Source

Definitions are paraphrased from DOO MADE - The Operator's Ticket Pack (May 2026), page 02 ("Orientation"). The verbatim template wording for each part is preserved in the `templates/` folder.
