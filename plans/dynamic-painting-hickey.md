# Demo Plan — Current Status Review

## Context

User asked to review the demo plan and assess where we stand. This file captures the current state of the RFQ/SOW demo showcase work, what's shipped, what's open, and the decision points before next action.

---

## Where We Stand: Headline

**The demo-showcase work is complete and merged to `main`.** PR #3 closed as MERGED (commit `0709fad`). Local `demo-showcase` branch is fully merged — it contains nothing `main` doesn't have except the merge commit itself.

Vercel production deployment confirmed previously (memory 1413: "RFQ/SOW Vercel App Shipped to Production").

---

## Demo PR #3 — What Shipped

Four commits, all merged to `main`:

| Commit | Purpose |
|---|---|
| `867f59a` | Demo upgrade: DisclaimerBox, badges, README rewrite, .env.example as integration roadmap, demo script, OpenAI/KB architecture docs (deferred to future phase) |
| `228f96e` | Reframe spec to permanent deployment-mode (Option 3: separate Vercel deployments for demo vs AI modes) |
| `0a38a33` | Reconcile spec ↔ implementation contradictions on PDF/DOCX server-side extraction (Codex P2) |
| `88f25ac` | Gate `scenarioId` on Load Sample state to prevent contamination of custom RFQs (Codex P2) |

### Codex Review Trail
- Pass 1 on `228f96e`: COMMENTED (reframing review)
- Pass 2 on `0a38a33`: COMMENTED (spec reconciliation review)
- Pass 3 on `88f25ac`: triggered, no findings recorded that block merge
- Result: merged without unresolved blockers

---

## Demo Architecture Locked In

Per memory and committed spec/docs:

- **Permanent dual-mode strategy**: demo deployment (mock-only, no API key) coexists with future AI deployment (full OpenAI integration)
- **Demo deployment**: zero-cost, sales/stakeholder-facing, hardcoded scenarios + custom RFQ paste-through to mock generator
- **Companion-document governance**: demo plan + UltraPlan spec are co-authoritative, with demo plan describing the showcase deployment mode
- **Server-side extraction shipped**: PDF/DOCX/TXT/MD text extraction works in production (reconciled in `0a38a33`)

---

## Open Items (Not Demo-Blocking)

### 1. Pre-existing Unstaged Spec Rewrite — UNRELATED TO DEMO

`rfq_sow_vercel_app_ultraplan_spec.md` has **1,197 insertions / 607 deletions** unstaged. This is a comprehensive expansion that converts the older terse MVP spec into a numbered 32-section UltraPlan covering:
- Detailed environment variables and runbooks
- Knowledge base templates (sections 22–23)
- Claude Code implementation prompts (section 26)
- Deployment runbook + handoff (section 27)
- Testing requirements (section 28)
- Final acceptance criteria + future enhancements

**Origin**: This predates the demo-showcase branch (memory observation 1436 flagged it as pre-existing and outside the demo PR scope). It was never resolved.

**Decision needed**: keep, discard, or commit separately. It does not conflict with the merged demo work — it is additive content in the same file.

### 2. Branch Hygiene

`demo-showcase` is fully merged. Standard cleanup options:
- Delete local + remote branch
- Or keep as the working branch for the demo deployment-mode (per Option 3 strategy, demo and AI deployments will diverge eventually)

### 3. Codex Pass 4 (theoretical)

Memory noted "if codex pass 4 returns post-merge with flags, address via follow-up branch/PR." No new flags surfaced in fetched PR data — this risk is effectively closed.

### 4. Future AI Integration Phase

Per locked architecture, the next major workstream is wiring real OpenAI generation in a separate deployment branch. This is a future milestone, not part of demo-plan completion.

---

## Critical Files (For Reference, Not Modification)

- `rfq_sow_vercel_app_ultraplan_spec.md` — UltraPlan source of truth (committed) + unstaged expansion (open)
- `rfq-sow-app/` — Next.js demo app (shipped to Vercel)
- `rfq-sow-app/components/DisclaimerBox.tsx` — variant-prop disclaimer component (added in `867f59a`)
- `rfq-sow-app/.env.example` — demo-mode + integration roadmap doc
- `rfq-sow-app/README.md` — demo-only positioning + workflow
- `rfq-sow-app/app/api/upload/route.ts` — server-side text extraction (shipped)
- `rfq-sow-app/components/IntakeForm.tsx` — scenarioId gating fix (`88f25ac`)

---

## Verification Status

| Check | Status |
|---|---|
| PR #3 merged to main | ✅ MERGED |
| Demo deployed to Vercel production | ✅ (memory 1413) |
| Spec ↔ implementation contradictions | ✅ Reconciled |
| ScenarioId leak | ✅ Fixed |
| Codex review loop | ✅ No outstanding findings |
| Unstaged spec rewrite | ⚠️ Open decision |

---

## Next Actions (User-Selected)

### 1. Review unstaged spec diff section-by-section
Walk the diff in logical chunks (header reframe, sections 1–10, 11–20, 21–32) and report what each change does. User decides keep/drop per chunk before any commit.

- Source: `rfq_sow_vercel_app_ultraplan_spec.md` working copy vs `HEAD`
- Method: `git diff HEAD -- rfq_sow_vercel_app_ultraplan_spec.md` (chunked via offset/range)
- Deliverable: structured summary table → user picks per-section action → final commit on a new branch (e.g. `spec-ultraplan-expansion`) + PR

### 2. Verify Vercel demo URL is live
- Locate deployment URL (check `rfq-sow-app/.vercel/`, Vercel CLI, or `gh` for deployment annotations)
- Confirm app loads, mock generation works, downloads work
- Report any regressions

### 3. Clean up `demo-showcase` branch
- Confirm fully merged: `git log origin/main..demo-showcase` returns empty (already verified ✅)
- Delete local: `git branch -d demo-showcase` (after switching to main)
- Delete remote: `git push origin --delete demo-showcase`
- Switch local to `main` and pull merge commit

### Order of operations
1. First: switch to main + pull, then clean up demo-showcase branch (foundational)
2. Then: verify Vercel demo (smoke test)
3. Then: review unstaged spec diff with user (collaborative decision loop)

### Critical files
- `rfq_sow_vercel_app_ultraplan_spec.md` — diff to review
- `rfq-sow-app/.vercel/project.json` — deployment metadata if present
- `.git/refs/heads/demo-showcase` — branch to delete after main pull
