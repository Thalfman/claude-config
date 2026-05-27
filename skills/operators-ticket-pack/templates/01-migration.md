# Ticket 01 - The Migration Ticket

**Use case:** Move your codebase from one framework or library to another while keeping behavior identical.

## Bracket list

Collect these from the operator in one batch before filling:

- `[SOURCE LIBRARY]` - the library being migrated away from (e.g. `requests`, `Vue 2`)
- `[TARGET LIBRARY]` - the library being migrated to (e.g. `httpx`, `Vue 3`)
- `[YOUR TEST COMMAND]` - the full test command (e.g. `pytest -q`, `npm test`)
- `[PROTECTED DIRECTORY]` - any directory the agent must not touch (e.g. `migrations/`, `infra/`)

## Template (verbatim from DOO MADE)

```
GOAL: Migrate [SOURCE LIBRARY] to [TARGET LIBRARY] across
the entire codebase. The job is done when every
condition below is met.

1. THE ORDER
   - Every import of [SOURCE LIBRARY] is replaced with
     the equivalent [TARGET LIBRARY] import.
   - All existing functionality continues to work
     without behavior changes.

2. THE PROOF
   - [YOUR TEST COMMAND] exits 0.
   - grep -r "[SOURCE LIBRARY]" src/ returns zero matches.
   - The build completes without errors.

3. THE BOUNDARY
   - Do not modify any test files.
   - Do not change behavior of any function.
     Migration only, not refactoring.
   - Do not touch [PROTECTED DIRECTORY].

4. THE BUDGET
   - Stop after 30 turns OR 60 minutes, whichever
     hits first.

5. THE FALLBACK
   - If blocked on the same error 3 times in a row,
     write the error to ERROR.md and exit.
   - If a [SOURCE LIBRARY] feature has no equivalent,
     log it to MIGRATION_GAPS.md and continue.
```

## Plain-English proof gate

Done = your test command exits 0, no `[SOURCE LIBRARY]` references remain in `src/`, and the build is green.

## Why it works (from DOO MADE)

- The `grep` proof stops the cook from declaring "done" while stragglers remain in the codebase.
- The boundary against test edits prevents reward-hacking the suite.
- The `MIGRATION_GAPS.md` fallback handles irreconcilable differences without locking the loop forever.

## Filled example - `requests` to `httpx`

```
GOAL: Migrate requests to httpx across
the entire codebase. The job is done when every
condition below is met.

1. THE ORDER
   - Every import of requests is replaced with
     the equivalent httpx import.
   - All existing functionality continues to work
     without behavior changes.

2. THE PROOF
   - pytest -q exits 0.
   - grep -r "requests" src/ returns zero matches.
   - The build completes without errors.

3. THE BOUNDARY
   - Do not modify any test files.
   - Do not change behavior of any function.
     Migration only, not refactoring.
   - Do not touch migrations/.

4. THE BUDGET
   - Stop after 30 turns OR 60 minutes, whichever
     hits first.

5. THE FALLBACK
   - If blocked on the same error 3 times in a row,
     write the error to ERROR.md and exit.
   - If a requests feature has no equivalent,
     log it to MIGRATION_GAPS.md and continue.
```

Heads-up: if the codebase imports `requests` from outside `src/` (e.g. `scripts/`, `notebooks/`), the operator may want to broaden the grep path, or add additional protected directories.
