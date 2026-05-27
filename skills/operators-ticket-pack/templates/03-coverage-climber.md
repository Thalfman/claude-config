# Ticket 03 - The Coverage Climber

**Use case:** Raise test coverage to a target percentage without modifying production code.

## Bracket list

Collect these from the operator in one batch before filling:

- `[TARGET MODULE]` - the module to cover (e.g. `src/billing/`, `lib/auth/`)
- `[TARGET PERCENTAGE]` - the coverage target as a whole number (e.g. `80`, `90`)
- `[COVERAGE COMMAND]` - the full coverage command (e.g. `pytest --cov=src/billing --cov-report=term`, `vitest run --coverage`)

## Template (verbatim from DOO MADE)

```
GOAL: Raise test coverage on [TARGET MODULE] to
[TARGET PERCENTAGE]%.

1. THE ORDER
   - Add tests until coverage on [TARGET MODULE]
     is at or above [TARGET PERCENTAGE]%.
   - New tests must test real behavior, not just
     hit lines.

2. THE PROOF
   - [COVERAGE COMMAND] reports coverage at or
     above [TARGET PERCENTAGE]% on [TARGET MODULE].
   - All existing tests still pass.
   - Each new test contains at least one meaningful
     assertion.

3. THE BOUNDARY
   - Do not modify production code in [TARGET MODULE].
   - Do not modify existing tests.
   - Do not write tests that only assert True or
     invoke functions without checking output.

4. THE BUDGET
   - Stop after 25 turns OR 45 minutes, whichever
     hits first.

5. THE FALLBACK
   - If [TARGET PERCENTAGE]% is unreachable without
     changing production code, write the gap analysis
     to COVERAGE_GAPS.md and exit at whatever coverage
     was achieved.
```

## Plain-English proof gate

Done = coverage on `[TARGET MODULE]` is at or above `[TARGET PERCENTAGE]%`, all existing tests pass, and every new test has at least one assertion that actually checks output.

## Why it works (from DOO MADE)

- The "meaningful assertion" rule blocks coverage gaming with empty test bodies.
- The boundary against modifying production code prevents the cook from "fixing" coverage by deleting branches.
- The `COVERAGE_GAPS.md` fallback reports partial success honestly instead of looping forever.

## Operator's call

What counts as a "meaningful assertion"? Examples:

- `assert x == 5` -> yes
- `assert True` -> no
- `assert len(result) > 0` -> borderline
- Assertion on a mocked return value -> borderline

Have the operator decide where the line sits for this codebase. Add a clarifying note alongside the ticket if borderline cases will come up.

## Filled example - raise `src/billing/` to 80%

```
GOAL: Raise test coverage on src/billing/ to
80%.

1. THE ORDER
   - Add tests until coverage on src/billing/
     is at or above 80%.
   - New tests must test real behavior, not just
     hit lines.

2. THE PROOF
   - pytest --cov=src/billing --cov-report=term reports coverage at or
     above 80% on src/billing/.
   - All existing tests still pass.
   - Each new test contains at least one meaningful
     assertion.

3. THE BOUNDARY
   - Do not modify production code in src/billing/.
   - Do not modify existing tests.
   - Do not write tests that only assert True or
     invoke functions without checking output.

4. THE BUDGET
   - Stop after 25 turns OR 45 minutes, whichever
     hits first.

5. THE FALLBACK
   - If 80% is unreachable without
     changing production code, write the gap analysis
     to COVERAGE_GAPS.md and exit at whatever coverage
     was achieved.
```
