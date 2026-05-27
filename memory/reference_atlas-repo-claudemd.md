---
name: atlas-repo-claudemd
description: ATLAS repo has a repo-level CLAUDE.md at the root that codifies repo-scoped Claude Code behavior (source-of-truth files, branch policy, Codex auto-handling rule).
metadata:
  type: reference
---

`C:\Users\thalf\OneDrive\Documents\ATLAS-PM-Ops-OS\CLAUDE.md` is the repo-level Claude Code instruction file. It is auto-loaded into Claude's context whenever a session runs in this working directory. It captures:

- Source-of-truth files in their read order (`README.md`, `MASTER_CONTEXT.md`, `SESSION_HANDOFF.md`, the relevant phase prompt, `ROADMAP.md`, `ARTIFACT_BACKLOG.md`, `DECISION_LOG.md`).
- The standing Codex review loop: address unresolved Codex threads, commit on the PR's branch, push, resolve threads, without asking permission. See [[codex-auto-address]].
- Commit and branch policy: feature branch per phase (`feat/phase-NN-<slug>`), chore branch for cross-cutting operating changes (`chore/<slug>`), never edit `main` directly.
- The "what not to add" list inherited from `MASTER_CONTEXT.md` (no apps, packages, APIs, databases, deployment files, code scaffolding).

When changing repo-scoped operating behavior, edit `CLAUDE.md` and log the change in `10_DECISION_LOG/DECISION_LOG.md`.
