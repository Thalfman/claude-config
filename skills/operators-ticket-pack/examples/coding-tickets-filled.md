# Worked examples - coding tickets (01-04)

A second filled example per coding ticket. The first example for each ticket lives inline in `templates/0X-name.md`; this file adds another scenario for reference.

---

## 01 Migration - Vue 2 to Vue 3 on a Nuxt frontend

```
GOAL: Migrate Vue 2 to Vue 3 across
the entire codebase. The job is done when every
condition below is met.

1. THE ORDER
   - Every import of Vue 2 is replaced with
     the equivalent Vue 3 import.
   - All existing functionality continues to work
     without behavior changes.

2. THE PROOF
   - npm test exits 0.
   - grep -r "Vue 2" src/ returns zero matches.
   - The build completes without errors.

3. THE BOUNDARY
   - Do not modify any test files.
   - Do not change behavior of any function.
     Migration only, not refactoring.
   - Do not touch infra/.

4. THE BUDGET
   - Stop after 30 turns OR 60 minutes, whichever
     hits first.

5. THE FALLBACK
   - If blocked on the same error 3 times in a row,
     write the error to ERROR.md and exit.
   - If a Vue 2 feature has no equivalent,
     log it to MIGRATION_GAPS.md and continue.
```

**Plain-English proof gate:** Done = `npm test` exits 0, no remaining `Vue 2` references in `src/`, and the build is green.

**Note on ambiguity:** Vue 2 -> Vue 3 has well-known no-equivalent areas (filters, event bus, `Vue.set`). Expect `MIGRATION_GAPS.md` to be non-empty after this run - that is by design, not a failure. The grep target may need to be broader than `"Vue 2"` (e.g. import paths and option-API patterns). Confirm with the operator.

---

## 02 Bug Hunt - failing E2E tests in `tests/e2e/`

```
GOAL: Get all tests in tests/e2e/ passing
without modifying core business logic.

1. THE ORDER
   - All tests in tests/e2e/ pass when
     running npx playwright test tests/e2e/.
   - The root cause is identified, not just patched
     over.

2. THE PROOF
   - npx playwright test tests/e2e/ in tests/e2e/ exits 0.
   - git diff shows changes only in fix-related
     files, no test deletions.

3. THE BOUNDARY
   - Do not delete failing tests.
   - Do not skip failing tests with .skip or pytest
     marks.
   - Do not modify src/api/.

4. THE BUDGET
   - Stop after 20 turns OR 30 minutes, whichever
     hits first.

5. THE FALLBACK
   - If the root cause is not found after 5 turns,
     write the current hypothesis and what was tried
     to BUG_REPORT.md and exit.
```

**Plain-English proof gate:** Done = `npx playwright test tests/e2e/` exits 0, and `git diff` shows only fix-related changes - no test deletions, no skips.

**Note:** Playwright suites can flake on timing. If the agent reaches the 5-turn limit and the cause is environmental flakiness, that belongs in `BUG_REPORT.md` so the operator can decide whether to retry with a wider retry window or fix the underlying flake.

---

## 03 Coverage Climber - lib/auth/ to 90% with vitest

```
GOAL: Raise test coverage on lib/auth/ to
90%.

1. THE ORDER
   - Add tests until coverage on lib/auth/
     is at or above 90%.
   - New tests must test real behavior, not just
     hit lines.

2. THE PROOF
   - vitest run --coverage --coverage.include="lib/auth/**" reports coverage at or
     above 90% on lib/auth/.
   - All existing tests still pass.
   - Each new test contains at least one meaningful
     assertion.

3. THE BOUNDARY
   - Do not modify production code in lib/auth/.
   - Do not modify existing tests.
   - Do not write tests that only assert True or
     invoke functions without checking output.

4. THE BUDGET
   - Stop after 25 turns OR 45 minutes, whichever
     hits first.

5. THE FALLBACK
   - If 90% is unreachable without
     changing production code, write the gap analysis
     to COVERAGE_GAPS.md and exit at whatever coverage
     was achieved.
```

**Plain-English proof gate:** Done = coverage on `lib/auth/` is at or above 90%, all existing tests pass, and every new test has at least one assertion that actually checks output.

**Operator's call:** Token-issuance code paths often interact with crypto libraries. Assertions on mocked JWT signatures are borderline - decide whether they count as "meaningful" in this codebase before the ticket runs.

---

## 04 Refactor - merge duplicates in `app/services/payment.py`

```
GOAL: Reduce code duplication in app/services/payment.py
by merging functions with high structural overlap.

1. THE ORDER
   - Identify functions in app/services/payment.py that
     share at least 70% of their structure.
   - Merge them into a single function with
     appropriate parameters.
   - Update all call sites to use the new merged
     function.

2. THE PROOF
   - All existing tests still pass when running
     pytest tests/services/test_payment.py.
   - Line count in app/services/payment.py is lower than
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

**Plain-English proof gate:** Done = `pytest tests/services/test_payment.py` passes, line count in `app/services/payment.py` is lower than the starting count, and no function pair with >70% overlap remains.

**Pre-flight:** `git restore` needs a clean working tree. Operator should `git stash` or commit before pasting this ticket.
