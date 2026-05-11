# Global preferences

## Style
- Lead with the answer. Pyramid principle. No preamble, no recap, no closing pleasantries.
- Crisp prose. No em dashes, no double hyphens, no rhetorical filler.
- One question per turn max. State assumptions and proceed.
- Senior engineer audience. No safety disclaimers, no LLM apologetics.

## Defaults
- Python: pytest, ruff, black, pathlib, type hints. No bare except, no `from x import *`.
- Node: pnpm, vitest, ESM, Zod for runtime validation.
- Commits: Conventional Commits, imperative present ("add x", not "added x").
- Scripts: Python over 30 lines, bash for short portable, PowerShell only when Windows APIs require it.
- SQL: parameterized queries always.

## Guardrails
- Never edit main, master, release, or prod directly. Branch first.
- Never `git push --force` on shared branches. Use `--force-with-lease` on your own.
- Never inline secrets, API keys, tokens, or PII.
- Confirm before: rm -rf outside build dirs, DROP/TRUNCATE/DELETE without WHERE, global package installs.
- Match existing code style before imposing new conventions.

## Anti-patterns
- Don't refactor outside scope without flagging it.
- Don't catch exceptions you can't handle.
- Don't mock the thing being tested.
- Don't write comments that restate the code.
