# Failure modes blocked by each ticket

Every PROOF, BOUNDARY, and FALLBACK in the PDF blocks a specific reward-hack. This file documents which hack each block defends against, so the skill can explain "why this line is in the ticket" on request - and so an operator never softens a block by accident.

## 01 Migration

- **Reward-hack:** Cook declares "done" while old-library imports linger in the codebase.
  **Block:** The `grep -r "[SOURCE LIBRARY]" src/` proof - returns zero matches or it is not done.
- **Reward-hack:** Cook makes the suite green by editing tests.
  **Block:** "Do not modify any test files."
- **Reward-hack:** Drift into refactoring or behavior changes during the migration.
  **Block:** "Do not change behavior of any function. Migration only, not refactoring."
- **Reward-hack:** Loop forever on irreconcilable feature gaps.
  **Block:** `MIGRATION_GAPS.md` fallback - log it and continue.

## 02 Bug Hunt

- **Reward-hack:** Delete the failing test, suite goes green.
  **Block:** "Do not delete failing tests." + `git diff` proof shows changes only in fix-related files, no test deletions.
- **Reward-hack:** Mark the test as `.skip` or `pytest.mark.skip`.
  **Block:** "Do not skip failing tests with .skip or pytest marks."
- **Reward-hack:** Patch the symptom instead of the root cause.
  **Block:** "The root cause is identified, not just patched over."
- **Reward-hack:** Loop on a dead-end hypothesis forever.
  **Block:** `BUG_REPORT.md` fallback after 5 unsuccessful turns.

## 03 Coverage Climber

- **Reward-hack:** Add empty tests (`assert True`) to hit lines without testing behavior.
  **Block:** "Each new test contains at least one meaningful assertion." + "Do not write tests that only assert True or invoke functions without checking output."
- **Reward-hack:** Delete uncovered branches to make coverage % go up.
  **Block:** "Do not modify production code in [TARGET MODULE]."
- **Reward-hack:** Mutate existing tests to inflate coverage.
  **Block:** "Do not modify existing tests."
- **Reward-hack:** Loop forever chasing the last 5%.
  **Block:** `COVERAGE_GAPS.md` fallback - exit at whatever was achieved.

## 04 Refactor

- **Reward-hack:** Add helper functions that silently grow the file while declaring the merge "done".
  **Block:** "Line count in [TARGET MODULE] is lower than before."
- **Reward-hack:** Drift into behavior changes during the refactor.
  **Block:** "Do not change function behavior, only structure."
- **Reward-hack:** Refactor across modules and create a ripple.
  **Block:** "Do not refactor across module boundaries."
- **Reward-hack:** Bad merge corrupts the working tree.
  **Block:** `git restore` fallback + `REFACTOR_CANDIDATES.md` after 5 failed merges.

## 05 Invoice Extractor

- **Reward-hack:** Skip the hard invoices, declare the CSV done.
  **Block:** "Every invoice in [FOLDER PATH] has at least one row in the output." + "Do not skip invoices because they look hard. Mark them for review instead."
- **Reward-hack:** Get the line items wrong silently.
  **Block:** Checksum - "the sum of its line_total values matches the document_total on the invoice." Deterministic.
- **Reward-hack:** Loop forever on a malformed invoice.
  **Block:** `REVIEW_NEEDED.csv` + `PARSE_ERRORS.md` fallback. Splits "needs review" from "could not parse."

## 06 Inbox Triage

- **Reward-hack:** Plate "looks important" as the reason for every email.
  **Block:** "Every one_line_reason is at least 5 words long." Forces real thought per email.
- **Reward-hack:** Mark every automated noreply email "urgent".
  **Block:** "Do not categorize automated emails as urgent unless they explicitly require human response."
- **Reward-hack:** Reply to emails because it looked helpful.
  **Block:** "Do not reply to any email."
- **Reward-hack:** Stall on ambiguous emails.
  **Block:** Default-to-this-week fallback - keep moving with "unclear, needs human review".

## 07 Content Repurposer

- **Reward-hack:** Hallucinate statistics and quotes to make the post punchier.
  **Block:** "Do not invent statistics or quotes not present in the source." The most important boundary in this ticket - fabrication destroys trust faster than any other error.
- **Reward-hack:** Write in LinkedIn-influencer voice instead of operator voice.
  **Block:** "Do not write in lecturer voice. Talk to one person."
- **Reward-hack:** Skirt the length validators.
  **Block:** Hard counts on tweet thread (5-7, < 280 chars), LinkedIn (150-250 words), pull-quote (1-2 sentences). JSON parses cleanly.
- **Reward-hack:** Pad output with hashtags and em-dashes.
  **Block:** "Do not use hashtags." + "Do not use em-dashes anywhere."

## 08 Lead Qualifier

- **Reward-hack:** Default to a middle score (5 or 6) when uncertain.
  **Block:** "Do not default to a middle score (5 or 6) when uncertain. Pick a clear high or low and explain why."
- **Reward-hack:** Make up criteria not in the rubric.
  **Block:** "Do not add criteria not in [CRITERIA FILE]." + "Every reason references at least one criterion from [CRITERIA FILE]."
- **Reward-hack:** Try to contact the lead.
  **Block:** "Do not contact any lead."
- **Reward-hack:** Conflate "low fit" with "missing data".
  **Block:** Score 0 + "insufficient data: [FIELD]" reason in the fallback.

## Operator-resolved ambiguities

Some templates carry intentional vagueness. The skill should surface these as questions, not silently default.

- **Refactor "70% structural overlap"** - quantitative or qualitative?
  Examples: identical AST -> yes. Same variable names but different control flow -> borderline. Two completely different bodies that take the same args -> no. Operator decides.
- **Coverage "meaningful assertion"** - borderline cases.
  Examples: `assert True` -> no. `assert x == 5` -> yes. `assert len(result) > 0` -> borderline. Assertion on a mocked return value -> borderline. Operator decides per codebase.
- **Inbox Triage "urgent in 24h"** - 24h from receipt or from now?
  Operator picks. From-now is the simpler default for a batch triage.
- **Inbox Triage email format** - MBOX, CSV, JSON, IMAP dump?
  Unspecified in the PDF. Skill must ask up front before the ticket can be filled.
- **Refactor `git restore` assumption** - requires a clean working tree.
  Skill should note this dependency in the handoff so the operator can stash or commit first.

## The operator's standard (from page 07)

> Better proof gates beat better cooks every time.

If you remember nothing else:
1. Your ticket is more important than which AI you pick.
2. The proof gate decides whether you ship work or garbage.
3. One ticket = one job. Bake the budget into the ticket itself.
