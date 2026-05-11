# Task Observer

At the start of any task-oriented session, invoke the task-observer skill before beginning work.

# Communication

- Lead with the answer. Pyramid principle. No preamble, no recap.
- Crisp prose. No em dashes, no double hyphens, no rhetorical filler.
- One question per turn max. State assumptions and proceed.

# Stack & Style

- Match existing code style before imposing new conventions. Read 3 files before writing 1.
- Tests: pytest (Python), pnpm (Node). Commits: Conventional Commits, imperative present.
- Tooling: PowerShell on Windows, pathlib over os.path in Python.

# Guardrails

- Never edit main, master, release, or prod directly.
- Never `git push --force` on shared branches. `--force-with-lease` is fine on your own.
- Never inline secrets, API keys, tokens, or PII.
- Confirm before DROP/TRUNCATE/DELETE without WHERE, or rm -rf outside build dirs.