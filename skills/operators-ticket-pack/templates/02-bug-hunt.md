# Ticket 02 - The Bug Hunt Ticket

**Use case:** Find and fix failing tests in a target directory without touching production code logic.

## Bracket list

Collect these from the operator in one batch before filling:

- `[TARGET DIRECTORY]` - the directory whose tests must pass (e.g. `tests/integration/`)
- `[TEST COMMAND]` - the full test command to run (e.g. `pytest tests/integration/ -v`, `npm test -- tests/integration`)
- `[PROTECTED FILES]` - files the agent must not modify (e.g. `src/core/`, `db/schema.sql`)

## Template (verbatim from DOO MADE)

```
GOAL: Get all tests in [TARGET DIRECTORY] passing
without modifying core business logic.

1. THE ORDER
   - All tests in [TARGET DIRECTORY] pass when
     running [TEST COMMAND].
   - The root cause is identified, not just patched
     over.

2. THE PROOF
   - [TEST COMMAND] in [TARGET DIRECTORY] exits 0.
   - git diff shows changes only in fix-related
     files, no test deletions.

3. THE BOUNDARY
   - Do not delete failing tests.
   - Do not skip failing tests with .skip or pytest
     marks.
   - Do not modify [PROTECTED FILES].

4. THE BUDGET
   - Stop after 20 turns OR 30 minutes, whichever
     hits first.

5. THE FALLBACK
   - If the root cause is not found after 5 turns,
     write the current hypothesis and what was tried
     to BUG_REPORT.md and exit.
```

## Plain-English proof gate

Done = your test command exits 0, and `git diff` shows only fix-related changes - no test deletions, no skips.

## Why it works (from DOO MADE)

- The "no test deletions" boundary directly blocks the most common reward-hack: plating a simpler dish by removing the order.
- The `BUG_REPORT.md` fallback turns dead-end loops into useful documentation for you.
- The `git diff` proof catches unrelated changes from sneaking in.

## Filled example - failing integration tests

```
GOAL: Get all tests in tests/integration/ passing
without modifying core business logic.

1. THE ORDER
   - All tests in tests/integration/ pass when
     running pytest tests/integration/ -v.
   - The root cause is identified, not just patched
     over.

2. THE PROOF
   - pytest tests/integration/ -v in tests/integration/ exits 0.
   - git diff shows changes only in fix-related
     files, no test deletions.

3. THE BOUNDARY
   - Do not delete failing tests.
   - Do not skip failing tests with .skip or pytest
     marks.
   - Do not modify src/core/.

4. THE BUDGET
   - Stop after 20 turns OR 30 minutes, whichever
     hits first.

5. THE FALLBACK
   - If the root cause is not found after 5 turns,
     write the current hypothesis and what was tried
     to BUG_REPORT.md and exit.
```
