# Ticket 04 - The Refactor Ticket

**Use case:** Reduce duplication in a target module by merging similar functions, with tests as the proof gate.

## Bracket list

Collect these from the operator in one batch before filling:

- `[TARGET MODULE]` - the module to refactor (e.g. `src/billing/`, `app/services/payment.py`)
- `[TEST COMMAND]` - the full test command that covers the module (e.g. `pytest src/billing/`, `npm test -- billing`)

## Pre-flight check

`git restore` requires a clean working tree. Before the operator pastes this ticket, they should `git stash` or commit any pending changes. Flag this in the handoff.

## Template (verbatim from DOO MADE)

```
GOAL: Reduce code duplication in [TARGET MODULE]
by merging functions with high structural overlap.

1. THE ORDER
   - Identify functions in [TARGET MODULE] that
     share at least 70% of their structure.
   - Merge them into a single function with
     appropriate parameters.
   - Update all call sites to use the new merged
     function.

2. THE PROOF
   - All existing tests still pass when running
     [TEST COMMAND].
   - Line count in [TARGET MODULE] is lower than
     before.
   - No function with >70% overlap remains.

3. THE BOUNDARY
   - Do not change function behavior, only structure.
   - Do not modify any test files.
   - Do not refactor across module boundaries.

4. THE BUDGET
   - Stop after 20 turns OR 40 minutes, whichever
     hits first.

5. THE FALLBACK
   - If a merge breaks tests, revert with git restore
     and try a different candidate.
   - If 5 attempted merges all fail, write a list of
     duplicate candidates to REFACTOR_CANDIDATES.md
     and exit.
```

## Plain-English proof gate

Done = the test command exits 0, the line count in `[TARGET MODULE]` is lower than at the start, and no pair of functions remains with >70% structural overlap.

## Why it works (from DOO MADE)

- The "line count must be lower" proof blocks declaring a refactor done while helper functions silently grow the file.
- The `git restore` fallback lets the cook recover from a bad merge without escalating the mess.
- The boundary against behavior changes keeps the refactor surgical instead of accidental rewriting.

## Operator's call

What does "70% structural overlap" mean here? Examples:

- Identical AST -> yes, merge.
- Same variable names but different control flow -> borderline.
- Two completely different bodies that take the same args -> no.

Have the operator confirm the bar before pasting.

## Filled example - reduce duplication in `src/billing/`

```
GOAL: Reduce code duplication in src/billing/
by merging functions with high structural overlap.

1. THE ORDER
   - Identify functions in src/billing/ that
     share at least 70% of their structure.
   - Merge them into a single function with
     appropriate parameters.
   - Update all call sites to use the new merged
     function.

2. THE PROOF
   - All existing tests still pass when running
     pytest src/billing/.
   - Line count in src/billing/ is lower than
     before.
   - No function with >70% overlap remains.

3. THE BOUNDARY
   - Do not change function behavior, only structure.
   - Do not modify any test files.
   - Do not refactor across module boundaries.

4. THE BUDGET
   - Stop after 20 turns OR 40 minutes, whichever
     hits first.

5. THE FALLBACK
   - If a merge breaks tests, revert with git restore
     and try a different candidate.
   - If 5 attempted merges all fail, write a list of
     duplicate candidates to REFACTOR_CANDIDATES.md
     and exit.
```
