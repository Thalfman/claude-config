---
name: codex-auto-address
description: On ATLAS PM/Ops OS, always address Codex review bot comments and commit/push without asking permission; standing rule.
metadata:
  type: feedback
---

On the ATLAS PM/Ops OS repo (`C:\Users\thalf\OneDrive\Documents\ATLAS-PM-Ops-OS`), whenever a pull request has unresolved review threads from the Codex review bot, address them, commit on the PR's branch using a Conventional Commits message scoped to the phase (for example `docs(phase-XX): address codex review on PR #N`), push, and resolve the threads. Do not ask permission first. Log any decisions that resulted from the review in `10_DECISION_LOG/DECISION_LOG.md` in the same session.

**Why:** Tom explicitly requested "always" behavior after Phase 1 went through two rounds of Codex review where each round needed a separate Tom prompt to trigger the fix-commit-push loop. Removing that friction is the durable preference. The repo enforces "no edits to `main`" and "feature branch + PR for every phase," so this rule applies on the existing PR's branch, never on `main`.

**How to apply:** Whenever working in the ATLAS repo and the current branch has an open PR, proactively run `gh pr view --json reviewThreads` (or the equivalent GraphQL call) at session start and after any push. For each unresolved Codex thread either apply the requested change in the named file and line, or reply on the thread explaining why not (for example: the change would violate the ATLAS safety boundary in `MASTER_CONTEXT.md`, conflict with an Active decision in `DECISION_LOG.md`, or break a global guardrail). Commit each round atomically, push, and resolve threads. Update `09_HANDOFFS/SESSION_HANDOFF.md` if the round changes phase state or the next best prompt. The repo-level rule is captured in `CLAUDE.md` at the repo root; see [[atlas-repo-claudemd]] for the file's purpose.

Hard limits the rule never overrides: never edit `main` directly, never `git push --force` on a shared branch (use `--force-with-lease` on the PR's own branch only when a rebase requires it), never skip hooks, never apply a change that would commit employer-sensitive material into a personal tool, never apply a change that violates the global guardrails in `C:\Users\thalf\.claude\CLAUDE.md`.
