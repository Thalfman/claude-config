# Decision matrix

Use to map an operator's natural-language task to one of the 8 tickets.

## Mapping table

| Operator says... | Ticket | Notes |
|------------------|--------|-------|
| "Migrate from X to Y" | 01 Migration | Replaces imports and call sites; preserves behavior. |
| "Replace library X with Y" | 01 Migration | Same. |
| "Move from `requests` to `httpx`" | 01 Migration | Concrete migration example. |
| "Switch from `unittest` to `pytest`" | 01 Migration | Migration applies even to test frameworks. |
| "Upgrade Vue 2 to Vue 3" | 01 Migration | Major-version upgrades are migrations. |
| "Get the failing tests passing" | 02 Bug Hunt | Targeted at a directory; does not change prod logic. |
| "Fix the test failures in `tests/integration/`" | 02 Bug Hunt | Same. |
| "Make the build green" | 02 Bug Hunt | If "make it green" means fix the failing tests. |
| "Raise coverage to 80% on `src/billing/`" | 03 Coverage Climber | Adds tests only; production code untouched. |
| "Get coverage up on `module X`" | 03 Coverage Climber | Same. |
| "Add tests until coverage hits the target" | 03 Coverage Climber | Same. |
| "Refactor duplicate code in `src/billing/`" | 04 Refactor | Function merging with line-count proof. |
| "Merge similar functions" | 04 Refactor | Same. |
| "Reduce duplication in module X" | 04 Refactor | Same. |
| "Pull line items from these invoice PDFs" | 05 Invoice Extractor | Checksum proof (line totals -> document total). |
| "Extract invoices into a CSV" | 05 Invoice Extractor | Same. |
| "Sort these emails into urgent / this-week / archive" | 06 Inbox Triage | One-line reason per email; 5-word minimum. |
| "Triage my inbox" | 06 Inbox Triage | Operator must specify the email export format. |
| "Turn this article into a tweet thread + LinkedIn post + pull-quote" | 07 Content Repurposer | JSON output with hard length validators. |
| "Repurpose this blog post" | 07 Content Repurposer | Same. |
| "Score these inbound leads against our ICP" | 08 Lead Qualifier | Ranked CSV; every reason must cite a criterion. |
| "Rank our pipeline leads" | 08 Lead Qualifier | Same. |

## When two tickets fit

One ticket = one job. If the request spans two outcomes, that is two tickets.

- "Move from `unittest` to `pytest` AND fix the tests it breaks." -> **01 Migration** first, then **02 Bug Hunt** on what remains.
- "Refactor duplicated code AND bump coverage." -> **04 Refactor** first (proves behavior unchanged), then **03 Coverage Climber**.
- "Triage these emails AND reply to the urgent ones." -> **06 Inbox Triage** does not reply. Replying is a separate (out-of-pack) job.

## When nothing fits

v1 stays faithful to the 8. If the operator's task does not fit any ticket, surface the two closest and stop. Do not invent a ninth ticket. Custom-ticket support may land in v2.

## Triggering phrases for the skill (CSO)

The skill should fire on any of:

- "Write me a ticket for X" / "Give me a prompt for X"
- "Delegate X to Claude Code / Codex / the bash loop"
- "I need a five-part ticket"
- "What is a proof gate?" / "What is the boundary on X?"
- Mentions of: DOO MADE, Ralph Wiggum Loop, The Operator's Ticket Pack
- Mentions of any part name: "the order", "the proof", "the boundary", "the budget", "the fallback"

When the skill fires from a vague phrase ("write me a prompt"), confirm the ticket category by listing the 8 and asking which fits.
