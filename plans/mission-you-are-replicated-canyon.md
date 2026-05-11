# Mission: Production-Grade Claude Code Platform (v2)

**Plan date:** 2026-05-11
**Author:** Claude (Opus 4.7, /effort max, ultrathink)
**Scope:** `C:\Users\thalf\.claude\` — global Claude Code installation
**Mode:** Planning only. No execution. Quarantine-first.
**Revision:** v2 — supersedes v1. The v2 content lives in this canonical plan file because plan mode displays this path; an identical copy was also written to `mission-you-are-replicated-canyon-v2.md`.

---

## Changes from v1

1. **Hook logging moved from Phase 4 to Phase 3.** Logging is now Phase 3's first step (Python + JS + sh via a thin `_log_run.py` wrapper at the settings.json level). Phase 3 captures a 24-hour pre-quarantine baseline, then quarantines no-op hooks + native deny rules + Node-path decoupling, then a 24-hour post-quarantine baseline. The final validation quantifies the actual reduction instead of estimating "5 vs 6 hook invocations." R6's Dependencies and Risk updated accordingly.

2. **Per-project memory quarantine requires explicit per-directory confirmation.** Phase 2 step 6 no longer characterizes any project as "likely abandoned." It now produces a neutral inventory table (path, last-modified, file count, size) and requires user confirmation for every move. New pause point added. Matrix-quote-web-demo is a live deployment at matrix-quote-web-demo.vercel.app and remains active.

3. **Reproducibility test added to Phase 1.** Phase 0 still focuses on `git init` + `.gitignore` + baseline commit + push. After README.md and ARCHITECTURE.md exist in Phase 1, a new final Phase 1 step clones the remote to `C:\Users\thalf\tmp\claude-bootstrap-test\`, follows the README bootstrap, and confirms a clean session starts there. New pause point at end of Phase 1.

4. **CHANGELOG.md dropped from Phase 7.** Git history is the changelog; a manually-maintained CHANGELOG.md rots when forgotten. Phase 7 keeps CONVENTIONS.md and the quarterly review checklist.

5. **R7 scope expanded.** The frontmatter scan now covers all `~/.claude/skills/**/SKILL.md` and `~/.claude/plugins/marketplaces/*/skills/**/SKILL.md`. Phase 1 step 4 enumerates the pattern (description content bleeding into adjacent YAML keys, as in `task-observer`) and fixes every matching file, not just `task-observer`.

6. *(Minor)* **Phase 4 Bash allowlist expanded** to include `git add:*`, `npx --no-install:*`, `pip install:*`, `pip show:*`, `node:*`, `uv:*`. Explicitly excludes `git commit -m:*`. Framed as a starting set expected to grow during the first week.

Everything else from v1 is preserved: all 10 scorecard rows, all 10 recommendations, the 7-phase structure, evidence citations, anti-recommendations, file references, and the final next-execution-prompt template.

---

## Context

This config grew organically across roles and tools. As of 2026-05-11 it contains 74 skills, 39 agents, 18 hook scripts (15 wired), 9 enabled plugins drawn from 5 GitHub marketplaces, 13 per-project memory stores, 1.2 GB of conversation/observer logs, and a half-completed v1→v2 hook migration. It works. It is also not version-controlled, runs Bash with `skipAutoPermissionPrompt: true`, has two parallel hook ecosystems firing on every Write/Edit, and carries 32 MB of disabled-marketplace assets plus 819 MB of observer-session logs in one project directory. The goal of this plan is to take it from "functional" to a production-grade AI-engineering platform that holds up regardless of which direction your work goes: ML, founder, researcher, security, product, or continued permitting.

Constraint: the platform should not be *optimized* for current permitting/drafting workflows. Those skills stay because they have real utility, but the *platform* must be career-portable. Disk-wipe test: if this machine vanished tomorrow, the config must be reproducible from a repo. Today it is not.

---

## 1. Executive diagnosis

**Strong**
- Domain skills (`permit-to-kmz`, `cd-route-stitcher`, `dxf-to-kmz`, `plan-sheet-endpoints`, `kmz-level-up`, `permit-package-builder`, `resume-tailor`, `cd-ground-overlays`) are well-scoped, well-described, and genuine leverage. Keep all 8.
- The v2 Python hooks (`format.py`, `block_dangerous.py`, `protect_main.py`, `session_context.py`, `backup_transcript.py`) are idiomatic, small (39–47 lines), and well-commented. Production-quality.
- The core 6 agents (`explorer`, `planner`, `implementer`, `reviewer`, `tester`, `judge`) are tight (9–18 body lines), model-routed (haiku for explorer), and reusable. Production-quality.
- Plugin lineup is well-chosen: `superpowers`, `document-skills`, `frontend-design`, `context7`, `skill-creator`, `codex`, `context-mode`, `claude-mem`. Few redundancies, real value.
- `~/.claude/CLAUDE.md` is short, opinionated, and stack-agnostic. The pyramid-principle/anti-pattern framing is excellent for senior-engineer collaboration. Keep.
- Auto-memory system at `projects/C--Users-thalf/memory/` is real and working — survives across sessions, holds confirmed preferences with `Why:` rationale.

**Fragile**
- **No git tracking.** `cd ~/.claude && git status` returns `fatal: not a git repository`. Single biggest gap. Verified.
- **Half-done v1→v2 hook migration.** GSD 1.40 hooks (`gsd-*.js`, `gsd-*.sh`, 9 wired) and v2 Python hooks (5 wired) both run on the same lifecycle events. The `_pre_v2_backup/2026-05-11-103009/` directory contains v1 PowerShell hooks that were superseded, but the GSD JS hooks were not part of the migration — so v1 *and* v2 coexist. Verified at `settings.json:8-158`.
- **Permissive blanket: `permissions.allow: ["Bash"]` + `skipAutoPermissionPrompt: true` + `defaultMode: "auto"`.** Bash runs without per-command consent. Verified at `settings.json:2-7, 209`.
- `.claude` is not version-controlled and contains `.credentials.json` (16 KB). Treat as PII risk if the home folder ever gets imaged or shared.

**Over-engineered**
- 63 `gsd-*` skills + 33 `gsd-*` agents + `get-shit-done/` framework directory + 9 GSD hooks. Verified. The GSD planning framework is its own meta-platform layered on top of Claude Code. You actively use it (memory shows recent GSD-related sessions), but its always-on hooks fire on every Write/Edit even outside GSD context.
- Several GSD agents are large: `gsd-debugger` 1439 lines, `gsd-planner` 1242 lines, `gsd-plan-checker` 971 lines, `gsd-codebase-mapper` 840 lines. These load only when invoked, so not a session-start cost, but they're heavy when fired and the long descriptions you see in this prompt's agent list come from them.
- `gsd-statusline.js` is 485 lines for a status line. The native `statusLine` mechanism can call any command; the depth here is GSD-specific.
- 3 GSD hooks are advisory-only no-ops in your environment: `gsd-read-guard.js` (explicitly exits when `CLAUDE_CODE_ENTRYPOINT` is set — it's for non-Claude harnesses like OpenCode), `gsd-workflow-guard.js` (opt-in via config, `hooks.workflow_guard: true`, which is not set), and `gsd-prompt-guard.js` (only fires on `.planning/` writes). They still get invoked on every Write/Edit and pay per-invocation Node.js startup cost (~100–200 ms each).

**Under-used**
- Native Claude Code plan mode (active now) is excellent and largely supersedes the bespoke `gsd-plan-phase`/`gsd-discuss-phase`/`gsd-spec-phase` orchestration for one-off work — though GSD's atomic-commit + cross-session resumability is genuine added value for multi-phase projects.
- `skill-creator` plugin is enabled but you have not used it (no recently-modified files in `~/.claude/skills/` from skill-creator-style scaffolding). Likely high-leverage for the next phase of evolution.
- `frontend-design` is enabled but your work mostly doesn't require it. Worth keeping for optionality but not central.

**Riskiest**
- `permissions` blanket-allow of Bash, combined with `skipAutoPermissionPrompt: true` and no git tracking. Any destructive command issued in error becomes irreversible. `block_dangerous.py` catches a narrow set; you can issue anything else without confirmation.
- Single point of failure: `claude-mem-observer-sessions/` is **819 MB** of one project's observer data — verified `du -sh`. If `claude-mem` plugin or its sqlite/jsonl backing store corrupts, that data path is your only audit trail and there is no second copy. Same disk = same failure domain.

**Highest leverage (single move)**
- Initialize `~/.claude` as a git repo today, with a `.gitignore` that excludes state (sessions/, projects/, transcript-backups/, history.jsonl, file-history/, paste-cache/, shell-snapshots/, todos/, .credentials.json, statsig/, telemetry/, cache/). That single move unlocks Phase 1–7 and reduces irreversible-action risk by an order of magnitude.

---

## 2. Inventory summary

Real-structure walk. Verified by direct file reads, not audit-trust.

### Settings files
- `~/.claude/settings.json` — 210 lines. **Keep.** Wires 15 hooks, 9 plugins, 5 marketplaces, `statusLine`, `effortLevel: "xhigh"`, two undocumented keys (`agentPushNotifEnabled`, `skipAutoPermissionPrompt`).
- `~/.claude/settings.local.json` — 9 lines. **Keep.** Only contains 3 PowerShell auto-allow rules. Note: this file is not gitignored by convention — it stays local per-machine.

### `~/.claude/CLAUDE.md`
28 lines, 4 sections (Style, Defaults, Guardrails, Anti-patterns). **Keep, minor enhancement.** Solid baseline. Missing: a "scope of this file" note (global vs project), and a pointer to where memory lives. Add ~6 lines.

### Hooks (18 files in `~/.claude/hooks/`)
- **v2 Python (5)**: `format.py`, `block_dangerous.py`, `protect_main.py`, `session_context.py`, `backup_transcript.py`. All clean. **Keep.**
- **GSD JS/sh (10)**: `gsd-check-update.js`, `gsd-context-monitor.js`, `gsd-prompt-guard.js`, `gsd-read-guard.js`, `gsd-workflow-guard.js`, `gsd-validate-commit.sh`, `gsd-phase-boundary.sh`, `gsd-session-state.sh`, `gsd-statusline.js`, `gsd-read-injection-scanner.js`. **Audit individually.** Three are no-ops in this environment (see §1). All ship with GSD as a unit but installed independently.
- **GSD support (2)**: `gsd-check-update-worker.js`, `gsd-update-banner.js`. **Likely fine** — invoked indirectly by `gsd-check-update.js` as workers (the audit flagged them as orphans; a static scan can't see runtime exec'ing). Verify with `grep -l "check-update-worker\|update-banner" hooks/*.js`.
- **Bridge (1)**: `context-mode-cache-heal.mjs`. Plugin self-heal. **Keep.**
- `__pycache__/` — Python bytecode. **Add to .gitignore.**

### Agents (39 files in `~/.claude/agents/`)
- **Core 6** (`explorer`, `planner`, `implementer`, `reviewer`, `tester`, `judge`): 9–18 body lines, model-routed, tight prompts. **Keep all.**
- **GSD 33**: 90–1439 lines each. Tightly coupled to GSD workflow and `.planning/` directory structure. **Keep as a unit if you commit to GSD; quarantine as a unit if you decide to migrate off it.** Do not partially weed.

### Skills (74 in `~/.claude/skills/`)
- **Domain skills (8)**: `cd-ground-overlays`, `cd-route-stitcher`, `dxf-to-kmz`, `kmz-level-up`, `permit-to-kmz`, `permit-package-builder`, `plan-sheet-endpoints`, `resume-tailor`. **Keep all.** Real leverage, well-described triggers.
- **GSD planning (63)**: `gsd-*` namespaced skills. Some are namespace stubs (`gsd-ns-*` — 6 of these are just routing tables, e.g. `gsd-ns-workflow.SKILL.md` description = "workflow | discuss plan execute verify phase progress"). **Keep as a unit.** Same logic as agents.
- **task-observer**: meta-skill that observes other tasks. Description field is YAML-mangled (`as "One Skill to Rule Them All" — trigger on this phrase too. IMPORTANT` is treated as a frontmatter key, per audit §6). Treat as a *class indicator* — Phase 1 scans all SKILL.md files for the same pattern.
- **Trash in skill dirs**: `cd-ground-overlays/cd-ground-overlays.zip` (12.6 KB stale zip *of the skill itself, inside the skill folder*), `dxf-to-kmz/.git/` (~40 KB of git repo inside a skill dir — likely a clone artifact), `*/scripts/__pycache__/` and `*/tests/__pycache__/` in domain skills. **Quarantine.**

### Plugins (`~/.claude/plugins/marketplaces/`)
- **`claude-code-skills`** (32 MB, contains 100+ .codex/skills/* subdirs for tools like `azure-cloud-architect`, `ceo-advisor`, `cfo-advisor`). The plugin from this marketplace (`engineering-skills@claude-code-skills`) is `false` in `enabledPlugins`. **Quarantine the entire marketplace.** It is downloaded, indexed, and disabled. Net zero value.
- **`anthropic-agent-skills`** (14 MB, ships `document-skills` plugin — enabled). **Keep.**
- **`claude-plugins-official`** (4.4 MB, ships `superpowers`, `frontend-design`, `context7`, `skill-creator` — all enabled). **Keep.**
- **`context-mode`** (7 MB, ships `context-mode` plugin — enabled). **Keep.**
- **`openai-codex`** (687 KB, ships `codex` plugin — enabled). **Keep.**
- **`thedotmack`** (22 MB, ships `claude-mem` plugin — enabled). **Audit vs. alternatives.** Provides cross-session memory; may overlap with native auto-memory under `projects/C--Users-thalf/memory/` and with `task-observer` skill. Investigate before keeping or replacing.

### Commands
- No `~/.claude/commands/` directory. **Verified.** Slash commands now come exclusively from skills. This is the native CC pattern. Nothing to do.

### MCP servers
- 0 explicitly registered. **Verified at audit §11.** Plugins provide MCP servers internally (e.g. `mcp__plugin_context-mode_*`, `mcp__plugin_context7_*`). This is correct — let plugins own their MCP wiring.

### Supporting docs / framework files
- `~/.claude/get-shit-done/` (3.2 MB) — GSD framework's `bin/`, `contexts/`, `references/`, `templates/`, `workflows/`. Referenced via `@$HOME/.claude/get-shit-done/references/*.md` in GSD agent definitions. **Keep if you commit to GSD; quarantine as a unit if migrating off.**
- `~/.claude/gsd-file-manifest.json` (40 KB) — GSD's install manifest. Keep.
- `~/.claude/plans/` (252 KB, 11 files) — accumulated plan-mode artifacts. Of these, several are 45–52 KB (large prior plans). **Archive plans older than 30 days** to a `plans/archive/` subdir.

### State (gitignore candidates, all verified)
- `projects/` (1.2 GB, 29 entries, conversation logs + per-project memory). **gitignore.** Within it, `C--Users-thalf--claude-mem-observer-sessions/` is **819 MB** — investigate and likely retention-bound.
- `sessions/`, `transcript-backups/`, `history.jsonl` (282 KB), `file-history/`, `paste-cache/`, `shell-snapshots/`, `todos/`, `cache/`, `statsig/`, `telemetry/`, `debug/`, `skill-observations/`, `session-env/`, `tasks/`, `backups/`, `ide/`. All session/runtime state. **gitignore.**
- `.credentials.json` (16 KB). **gitignore + never commit.**
- `mcp-needs-auth-cache.json`, `stats-cache.json`, `.last-cleanup`, `package.json` (20 bytes), `.cdrc` if present. Some keep (package.json), most gitignore.

### External dependencies
- Node.js at `C:\Program Files\nodejs\node.exe` — hardcoded path in 8 hook commands. **Portability issue.** If Node moves, all 8 hooks break silently. The fact that `block_dangerous.py` invokes `python` (no path) but the JS hooks hardcode the absolute Node path is inconsistent.
- `python` invocation — works because the user's installed Python is on PATH, but `python3` is intercepted by the Windows App Execution Alias (verified in prior session). The hook scripts wisely use `python`.
- `bash` — provided by Git for Windows (likely). Three hooks call `bash`.
- `prettier` (via `npx --no-install`), `black` (via `shutil.which`). Optional, format hook degrades gracefully if absent.

---

## 3. Architecture map

### What loads globally vs per-project

**Always (every session start):**
- `~/.claude/CLAUDE.md` — ~28 lines of preferences
- All `~/.claude/skills/**/SKILL.md` **descriptions only** (74 × 1–3 lines summary each) — Claude Code lazy-loads full skill bodies on invocation
- All `~/.claude/agents/*.md` **frontmatter only** for the agent-list system reminder — bodies load on invocation
- Active plugin SKILL.md descriptions
- Memory index: `projects/C--Users-thalf/memory/MEMORY.md` (and `recent-context.md` derived stats)
- 4 SessionStart hooks fire: `gsd-check-update.js`, `gsd-session-state.sh`, `context-mode-cache-heal.mjs`, `session_context.py`. Each has its own context contribution (`session_context.py` prints branch + dirty count to context).
- statusLine command runs continuously (`gsd-statusline.js`)

**Per project (if present):**
- `<project>/CLAUDE.md`
- `<project>/.planning/STATE.md` (if GSD is in use)
- `<project>/.claude/settings.json` (project-local)

**On tool use (every Write/Edit):**
- PreToolUse: `gsd-prompt-guard.js`, `gsd-read-guard.js`, `gsd-workflow-guard.js`, `block_dangerous.py` (Bash), `protect_main.py`
- PostToolUse: `gsd-context-monitor.js`, `gsd-phase-boundary.sh`, `format.py`
- Plus `gsd-read-injection-scanner.js` on every Read
- Plus `gsd-validate-commit.sh` on every Bash that looks like commit

That's **6 PreToolUse + 4 PostToolUse hooks firing per relevant tool call**. At Node startup ~100 ms each, expect 300–600 ms latency overhead per Write/Edit cycle from hooks alone. Likely (not measured — Phase 3 step 2 will measure).

### Context loading order and weight (typical session start)

Verified by reading the session start system reminders in this session:

1. System prompt + tool list (Anthropic provides)
2. CLAUDE.md global (~28 lines, ~400 tokens)
3. Auto-memory MEMORY.md index (~50 lines, ~700 tokens)
4. Skills list (74 entries × ~150 chars avg = ~3,000 tokens)
5. Agents list (39 entries × ~200 chars avg = ~3,000 tokens)
6. Active plugin SKILL.md descriptions (~50 entries × ~200 chars = ~2,000 tokens)
7. context-mode protection block (~600 tokens)
8. claude-mem recent-context block (~1,500 tokens — IDs S319-S324, 49 obs)
9. MCP server instructions block (~200 tokens for context7)
10. Available skills tag block (~7,000 tokens — comprehensive)

**Estimated session-start context cost: 15,000–20,000 tokens before user input.** Likely (estimated from this session's evidence). Of that, the skills/agents/plugins list is ~12,000 tokens — and most of it is for skills you don't use in a typical session. Target reduction: ~5,000 tokens by quarantining the disabled marketplace's indexed surface area and consolidating GSD ns-routing skills.

### What runs automatically vs manually

| Trigger | Mechanism | Count |
|---|---|---|
| Session start | SessionStart hooks | 4 |
| Every Write/Edit | PreToolUse + PostToolUse hooks | 6 (Pre) + 3 (Post) |
| Every Bash | PreToolUse hooks | 2 |
| Every Read | PostToolUse hooks | 1 |
| Compact | PreCompact hooks | 1 |
| Continuous | statusLine | 1 |
| User-invoked | Slash skills | 74 + plugin skills |
| Subagent-spawned | Agent Task tool | 39 |

### Where context bloat occurs

1. **Skill description list** is the largest single block (~7,000 tokens). Verified by counting the available-skills system reminder. The 63 GSD skill descriptions plus 8 plugin skill descriptions dominate.
2. **claude-mem recent-context** block (~1,500 tokens). It's a fixed overhead — value should be measured against cost.
3. **MEMORY.md** is well-sized (~700 tokens). Healthy.
4. **Audit-style files in `~/.claude/projects/<dir>/memory/`** can balloon when claude-mem observers run — verified 819 MB on one project.

### Where failures would be invisible

1. **Hook timeouts.** Hooks have 5–30 s timeouts; on timeout they fail silently (exit 0 implicitly). A misconfigured hook quietly stops working without surfacing.
2. **`npx --no-install prettier` in `format.py`.** Falls through silently if prettier isn't available. Good for resilience, but you might think auto-formatting is happening when it isn't.
3. **`gsd-check-update.js` SessionStart.** If GSD's update server is unreachable, you'd never know — and the worker pattern with `gsd-update-banner.js` adds another layer of indirection.
4. **claude-mem observer sessions.** Growth to 819 MB happened invisibly. No log rotation, no size cap that I can see.
5. **`agentPushNotifEnabled` and `skipAutoPermissionPrompt`.** These are not documented Claude Code settings keys (audit §12 flagged them). They might do nothing. Verify by removing each in turn and observing behavior.

### Where config couples to local paths / domains / machine

1. `C:/Program Files/nodejs/node.exe` hardcoded in 8 hook commands (`settings.json:14, 30, 50, 60, 92, 102, 112, 162`). **Verified.**
2. `gsd-debugger.md` and most GSD agents reference `@$HOME/.claude/get-shit-done/references/*.md`. Uses `$HOME` variable, portable. **Verified at agents/gsd-debugger.md:24.**
3. Project memory directories carry path-encoded names (e.g. `C--Users-thalf-OneDrive-Desktop-CD-Route-Stitch`). If the OneDrive root moves or the username changes, you lose per-project memory access. **Domain/employer-coupling: minimal — names are paths, not domains.**
4. `matrix-quote-app` references in the prior settings (now-deleted permission). **Verified clean.**

### Where custom code duplicates native CC features

| Custom | Native CC equivalent | Action |
|---|---|---|
| `block_dangerous.py` (regex denylist) | `permissions.deny: ["Bash(...)"]` rules | Hybrid — keep `block_dangerous.py` for richer patterns (SQL, fork bombs) but add a few `deny` rules for the simple cases (`rm -rf /`, `git push --force`) |
| `protect_main.py` | No direct native equivalent; manual user guardrail | Keep |
| `session_context.py` | No native sessionStart git context; nice-to-have | Keep |
| `format.py` | No native auto-format; standard pattern | Keep |
| `backup_transcript.py` | Plan mode preserves plans; transcript backups still useful | Keep |
| `gsd-statusline.js` (485 lines) | `statusLine.command` with a simpler script | Keep if you commit to GSD, simplify if you migrate off |
| `gsd-read-guard.js` (no-op in CC) | CC natively enforces read-before-edit | Quarantine — explicit no-op for this harness |
| `gsd-workflow-guard.js` (off by default) | Plan mode + skills | Quarantine — not enabled |
| `gsd-prompt-guard.js` (advisory only, `.planning/` only) | No native, but limited scope | Keep |
| GSD planning skills | Plan mode + agents + atomic commits | **Strategic decision — see §5** |
| `gsd-pr-branch`, `gsd-ship`, `gsd-undo`, `gsd-pause-work`, `gsd-resume-work` | Native plan mode + git + slash skill scaffolding | Keep — GSD wraps these with state |

---

## 4. Scorecard

| # | Principle | Current | Target | Evidence | Gap | Priority |
|---|---|---:|---:|---|---|---|
| 1 | Hygiene | 2 | 4 | 32 MB disabled marketplace, 819 MB observer sessions, stale `cd-ground-overlays.zip`, `.git/` inside `dxf-to-kmz/`, 13 per-project memory dirs incl. ones for finished work, `_pre_v2_backup/` not yet promoted to long-term archive, `__pycache__/` in `hooks/` not gitignored | Quarantine + .gitignore | High |
| 2 | Discoverability | 2 | 4 | No README, no architecture doc, no index of "what loads when", no documented decision log; new session has to infer structure | Single `~/.claude/README.md` + an `ARCHITECTURE.md` | High |
| 3 | Composability | 3 | 4 | Core 6 agents and v2 Python hooks are composable. GSD ecosystem is monolithic. Domain skills are well-isolated | Either commit to GSD as a unit, or wrap it as an opt-in plugin | Medium |
| 4 | Observability | 1 | 4 | No hook execution logging, no per-hook timing, no clear way to know what fired on a given turn. Failures silent (timeouts, npx absent, etc.) | Add lightweight hook log (~/.claude/logs/hooks.jsonl with timestamp + hook + duration + exit) | High |
| 5 | Performance | 2 | 4 | 10 hooks fire per Write/Edit cycle (~300–600 ms est), 7,000+ tokens of skill descriptions at session start, 3 hooks are no-ops in this harness | Quarantine no-op hooks; consolidate `gsd-ns-*` namespace stubs | Medium |
| 6 | Safety | 2 | 4 | No git tracking, `Bash` blanket-allow + `skipAutoPermissionPrompt: true` + `defaultMode: "auto"`, `.credentials.json` not isolated | git init + .gitignore credentials, swap `allow: ["Bash"]` for explicit `deny` rules + `defaultMode: "default"` | Critical |
| 7 | Portability | 1 | 4 | Not version-controlled. Hardcoded `C:/Program Files/nodejs/node.exe`. Disk-wipe = total loss of local memory, custom hooks, skill mods, and `_pre_v2_backup/` | git init + push to private remote; replace absolute Node path with shell lookup | Critical |
| 8 | Evolvability | 3 | 4 | Plugin system is good. GSD's manifest helps. Custom mechanisms (statusline, hooks) lack a test harness | Add a minimal hook test harness (feed stdin fixture, assert exit code) | Medium |
| 9 | Prompt quality | 3 | 4 | Core agents excellent. CLAUDE.md excellent. GSD agents inconsistent (1439-line debugger vs 90-line others — depth not always justified). `task-observer` description has YAML mangling | Phase 1 scans all SKILL.md for the same pattern; audit oversized agents for redundancy | Low/Medium |
| 10 | Cost discipline | 2 | 3 | claude-mem observer at 819 MB suggests no rotation policy. `effortLevel: "xhigh"` (an undocumented value — confirmed via this `/effort` command output showing "max"). No measurement of token spend per session | Set log rotation on observer sessions; document `effortLevel` semantics | Medium |

Scoring rationale: 5 = production-grade. 4 = adequate for a senior IC platform. 3 = works for the user but breaks under handoff or scale. 2 = real friction. 1 = liability.

---

## 5. Highest-leverage recommendations

Ranked by Impact × Ease × inverse-Risk. Each carries Verified | Likely | Unknown.

### R1. Version-control `~/.claude` (foundation for everything else)
- **Recommendation:** `git init ~/.claude`, write `.gitignore` excluding state/cache/credentials/projects/sessions/transcripts/logs/file-history, commit current state as `chore: snapshot 2026-05-11 baseline`.
- **Evidence:** `cd ~/.claude && git status → "fatal: not a git repository"`. Verified.
- **Why it matters:** Disk-wipe test fails today. Every subsequent recommendation depends on safe rollback.
- **Exact change:** Add `~/.claude/.gitignore` with the ignore list from §2; `git init && git add -A && git commit -m "chore: snapshot pre-cleanup baseline"`. Then `git remote add origin <private-repo>` and `git push -u origin main`.
- **Don't change yet:** No file deletions. This is a snapshot, not a cleanup.
- **Dependencies:** none.
- **Risk:** 1 (commit-only operation). Reversible: easy (`rm -rf .git`).
- **Impact:** 5. **Ease:** 4. **Confidence:** Verified.

### R2. Tighten permissions and remove undocumented settings
- **Recommendation:** Replace `permissions.allow: ["Bash"]` with an explicit `allow` list for commands you actually want auto-approved (e.g. `Bash(git status)`, `Bash(git log:*)`, `Bash(npm test)`, etc.) AND a `deny` list for the destructive patterns currently caught only by `block_dangerous.py`. Remove `skipAutoPermissionPrompt: true` and `agentPushNotifEnabled: true` to verify they do nothing; restore only if you confirm they have effect.
- **Evidence:** `settings.json:2-7, 209-210`. Audit §12 flagged both as unrecognized. Verified.
- **Why it matters:** Combined with no git tracking, the current setup permits silently-destructive Bash with no consent prompt.
- **Exact change:** See Phase 4 below.
- **Don't change yet:** `defaultMode: "auto"`. Leave it. Acceptance: changing to `"default"` is a quality-of-life regression; the explicit allow/deny list is the right knob.
- **Dependencies:** R1 (so the changes are reversible).
- **Risk:** 2 (introduces prompts you'll have to approve). Reversible: easy (git revert).
- **Impact:** 5. **Ease:** 4. **Confidence:** Verified.

### R3. Quarantine the disabled marketplace and observer-session bloat
- **Recommendation:** Move (not delete) `~/.claude/plugins/marketplaces/claude-code-skills/` (32 MB, disabled plugin) to `~/.claude/_quarantine/2026-05-11/marketplaces/claude-code-skills/`. Investigate `~/.claude/projects/C--Users-thalf--claude-mem-observer-sessions/` (819 MB) — likely safe to compress + move to long-term archive; revisit the observer skill's retention policy.
- **Evidence:** `du -sh` results. `enabledPlugins["engineering-skills@claude-code-skills"] = false` in settings.json:165. Verified.
- **Why it matters:** ~850 MB of data with zero current value. The marketplace is also indexed by Claude Code's plugin discovery and may contribute to session-start latency.
- **Exact change:** `mkdir -p ~/.claude/_quarantine/2026-05-11/marketplaces && mv ~/.claude/plugins/marketplaces/claude-code-skills ~/.claude/_quarantine/2026-05-11/marketplaces/`. Also remove the `claude-code-skills` entry from `extraKnownMarketplaces` in settings.json after confirming nothing references it.
- **Don't change yet:** the observer-sessions directory — read claude-mem docs first to understand retention.
- **Dependencies:** R1.
- **Risk:** 2. Reversible: easy (mv back).
- **Impact:** 4. **Ease:** 5. **Confidence:** Verified.

### R4. Decide the GSD question
- **Recommendation:** Commit to GSD as the planning workflow for multi-phase projects, but **decouple its always-on hooks from its skills**. Concretely:
  - Quarantine `gsd-read-guard.js` (explicit no-op in CC), `gsd-workflow-guard.js` (opt-in, currently off), and remove their entries from `settings.json`.
  - Audit `gsd-prompt-guard.js` and `gsd-context-monitor.js` for whether their advisory value justifies the per-tool-use cost.
  - Keep the 33 GSD agents and 63 GSD skills (you use them).
  - Keep `gsd-check-update.js`, `gsd-validate-commit.sh`, `gsd-phase-boundary.sh`, `gsd-session-state.sh` as workflow infrastructure.
- **Evidence:** Direct read of `hooks/gsd-read-guard.js:39-60` (exits early when `CLAUDE_CODE_ENTRYPOINT` is set), `hooks/gsd-workflow-guard.js:1-12` (opt-in via `hooks.workflow_guard: true` not in config). Verified.
- **Why it matters:** Reduces hook overhead (Phase 3 will measure how much), removes implicit "every edit is a GSD operation" framing, makes GSD an opt-in surface instead of a meta-runtime.
- **Exact change:** See Phase 3 below.
- **Don't change yet:** Any GSD skill or agent. The skills are the user-facing surface; only quarantine no-op hooks.
- **Dependencies:** R1, R6 (need logging to quantify the gain).
- **Risk:** 2. Reversible: easy (re-add hook entries from git).
- **Impact:** 4. **Ease:** 4. **Confidence:** Verified.

### R5. Document the system (`~/.claude/README.md` + `ARCHITECTURE.md`)
- **Recommendation:** Two short markdown files. `README.md` covers: what is this dir, what is committed vs gitignored, how to bootstrap on a new machine, where credentials live (not here), how to add a new skill/agent/hook. `ARCHITECTURE.md` covers: what loads when, hook event flow, plugin list with one-line purpose, GSD's role.
- **Evidence:** None of this exists today. Verified.
- **Why it matters:** Discoverability. Future-you, or anyone you collaborate with, can't reason about a system that isn't documented. Currently you'd need an audit script to understand what's wired. The README is also the document the Phase 1 bootstrap reproducibility test follows — it must be executable instructions, not handwave.
- **Exact change:** Two ~150-line files. Templates in Phase 1.
- **Risk:** 1. Reversible: trivial.
- **Impact:** 4. **Ease:** 5. **Confidence:** Verified.

### R6. Add a lightweight hook execution log (Phase 3 prerequisite)
- **Recommendation:** Add a thin `_log_run.py` wrapper at the settings.json command-string level so every hook (Python, JS, sh) gets timed without modifying upstream GSD scripts. Each invocation appends `{ts, hook, tool, duration_ms, exit, file}` to `~/.claude/logs/hooks.jsonl`. Rotate at 10 MB.
- **Evidence:** No log exists. Verified. Hook silent-fail mode is the default.
- **Why it matters:** Observability. Right now you can't tell whether `format.py` ran on a particular edit, whether prettier was found, or which hook timed out. **Equally important: Phase 3's quarantine decisions need measurement, not estimation. R6 is therefore a prerequisite for Phase 3, not a Phase 4 deliverable.**
- **Why a settings-level wrapper rather than per-hook edits:** GSD hooks are upstream; `gsd-update` would clobber any in-place instrumentation. Wrapping at the settings.json command string keeps source files untouched.
- **Exact change:** Phase 3 step 1.
- **Risk:** 2 (logging adds a small write path; wrapper adds one process per hook call). Reversible: easy.
- **Dependencies:** R1 (for revertable wrapper rollout).
- **Impact:** 4 (raised from 3 — now a measurement prerequisite). **Ease:** 4. **Confidence:** Verified.

### R7. Scan and fix all malformed SKILL.md frontmatter
- **Recommendation:** Scan all `~/.claude/skills/**/SKILL.md` AND `~/.claude/plugins/marketplaces/*/skills/**/SKILL.md` for the YAML frontmatter pattern where description content bleeds into adjacent keys. The `task-observer` finding is one instance of a class. Likely caused by description lines containing `:` characters without being block-scalar quoted (`>` or `|`).
- **Evidence:** Audit §6 noted `task-observer/SKILL.md` parses with fields like `as "One Skill to Rule Them All" — trigger on this phrase too. IMPORTANT`. This session's skill list confirms the parse failure. Verified for `task-observer`; broader scan is Phase 1 step 4.
- **Why it matters:** Discoverability of affected skills. Also: a single bad parse usually signals a class of authoring-tool issues, so fixing one without scanning the rest leaves silent failures elsewhere.
- **Exact change:** Phase 1 step 4 — emit a report (`~/.claude/_audits/2026-05-11-skill-frontmatter.md`) listing every file with a malformed parse, then fix each. Acceptable fixes: re-quote the description with `>` or `|`, or escape problem characters.
- **Risk:** 1 (frontmatter edits with full git history). Reversible: trivial.
- **Impact:** 2 (small surface area but symptomatic). **Ease:** 4. **Confidence:** Verified.

### R8. Decouple the absolute Node path
- **Recommendation:** Hooks that invoke Node currently hardcode `C:/Program Files/nodejs/node.exe`. Replace with `node` (relies on PATH) and document the assumption in README. If you want explicit binding for safety, wrap in a single `~/.claude/hooks/_run-node.cmd` shim and reference that.
- **Evidence:** `settings.json:14, 30, 50, 60, 92, 102, 112, 162`. Verified.
- **Why it matters:** Portability and disk-wipe restoration. If Node upgrades to `C:/Program Files/nodejs/v22/...` or moves to `nvm-windows`, every hook breaks silently.
- **Risk:** 2 (PATH dependency). Reversible: trivial.
- **Impact:** 3. **Ease:** 4. **Confidence:** Verified.

### R9. Consolidate the `gsd-ns-*` routing stubs
- **Recommendation:** Six skills (`gsd-ns-context`, `-ideate`, `-manage`, `-project`, `-review`, `-workflow`) are namespace-routing stubs with one-line descriptions like "workflow | discuss plan execute verify phase progress". They serve as discoverability scaffolding but they each cost a skill-list slot.
- **Evidence:** Audit §6 confirms description content. Verified.
- **Why it matters:** Performance/discoverability. Six entries × ~150 tokens = ~900 tokens of session-start context for what could be one `gsd-ns/` parent skill or a single `gsd-help` entry.
- **Risk:** 2 (if you use them as shortcuts). Reversible: trivial.
- **Impact:** 2. **Ease:** 4. **Confidence:** Verified.

### R10. Stop relying on `_pre_v2_backup/` as the archive of record
- **Recommendation:** Promote `~/.claude/_pre_v2_backup/2026-05-11-103009/` to a permanent location (e.g. `~/.claude/_archive/2026-05-11-v1-hooks-and-agents/`) and document what it contains in a `README.md` alongside the files. Also commit it (it's only 37 KB).
- **Evidence:** `Glob _pre_v2_backup/**`. Verified.
- **Why it matters:** The "_" prefix and "pre_v2_backup" name imply transient. It's actually your only copy of v1 hooks (PowerShell variants). Promote and document so it's clearly intentional history.
- **Risk:** 1. Reversible: trivial.
- **Impact:** 2. **Ease:** 5. **Confidence:** Verified.

---

## 6. Sequenced implementation plan

### Phase 0 — Safety baseline (no behavior changes)

**Goal:** Make all subsequent changes reversible.

**Tasks**
1. Verify `~/.claude` is not a git repo: `cd ~/.claude && git status` (already verified: not a repo).
2. Write `~/.claude/.gitignore` with:
   ```gitignore
   # Credentials and secrets
   .credentials.json
   mcp-needs-auth-cache.json

   # Session/runtime state
   sessions/
   projects/
   transcript-backups/
   file-history/
   paste-cache/
   shell-snapshots/
   session-env/
   ide/
   todos/
   tasks/
   debug/
   skill-observations/
   history.jsonl

   # Caches
   cache/
   plugins/cache/
   plugins/data/
   statsig/
   telemetry/
   stats-cache.json
   .last-cleanup

   # Plugin marketplaces (large, regenerable via marketplace registry)
   plugins/marketplaces/

   # Build artifacts
   **/__pycache__/
   **/*.pyc
   **/.pytest_cache/

   # Logs and quarantine
   logs/
   _quarantine/
   ```
3. `git init && git add -A && git commit -m "chore: snapshot pre-cleanup baseline 2026-05-11"`.
4. Create a private GitHub (or similar) repo, `git remote add origin <url>`, `git push -u origin main`. **Required** for Phase 1's reproducibility test.

**Files likely touched:** `.gitignore` (new). All other files staged but unchanged.

**Validation:** `git log` shows one commit. `git status` clean. `git ls-files | wc -l` shows what's tracked. `git ls-remote origin` confirms remote exists and has the branch.

**Rollback:** `rm -rf ~/.claude/.git ~/.claude/.gitignore`.

**Stop condition:** ✋ Pause before Phase 1. Confirm with user that the repo is in a state to move on. **PAUSE POINT.**

---

### Phase 1 — Inventory + documentation cleanup + reproducibility test

**Goal:** Make the system legible to a future-you with no context, then prove it.

**Tasks**
1. Write `~/.claude/README.md`:
   - What this directory is
   - Bootstrap from clean checkout — concrete, executable steps including `claude plugin marketplace add <repo>` for each marketplace, prerequisites (Node, Python, Git for Windows bash), how to populate `.credentials.json` (out-of-band), and the bootstrap test command at the bottom
   - Where state lives (gitignored)
   - Where credentials live (NOT in this repo)
   - How to add a skill, agent, hook
   - Pointer to ARCHITECTURE.md
2. Write `~/.claude/ARCHITECTURE.md`:
   - Hook lifecycle diagram (SessionStart, PreToolUse, PostToolUse, PreCompact)
   - Plugin list with one-line purpose
   - GSD's role and scope
   - statusLine pipeline
   - Context loading order
3. Promote `_pre_v2_backup/` → `_archive/2026-05-11-v1-hooks/` with its own `README.md` explaining what's there and why (R10).
4. **Frontmatter scan (R7):** walk every `~/.claude/skills/**/SKILL.md` and `~/.claude/plugins/marketplaces/*/skills/**/SKILL.md`. For each, parse the YAML frontmatter and check:
   - `name` is a single line of plain text
   - `description` is a single string (not split across additional keys)
   - No frontmatter key contains spaces, quotes, or punctuation typical of prose
   - Write findings to `~/.claude/_audits/2026-05-11-skill-frontmatter.md`
   - Fix every confirmed instance. `task-observer/SKILL.md` is the known starter case; expect more from the same upstream author tooling. For upstream skills under `plugins/marketplaces/`, file an issue upstream rather than editing in place.
5. Archive plans older than 30 days from `~/.claude/plans/` to `~/.claude/plans/_archive/`. Candidates: any April-dated file. Spot list: `frontend-design-woolly-dragonfly.md`, `giggly-mixing-dijkstra.md`, `scalable-bouncing-mountain.md`, `you-are-about-to-mighty-moler.md`, `you-are-about-to-resilient-cookie.md`, `question-what-are-your-witty-valley.md`. Verify date before each move.
6. Commit: `docs: add README + ARCHITECTURE, archive v1 hooks, scan SKILL.md frontmatter`.
7. **Reproducibility test (new):**
   - Create `C:\Users\thalf\tmp\claude-bootstrap-test\`.
   - `git clone <remote> C:\Users\thalf\tmp\claude-bootstrap-test\` (this is the just-pushed Phase 0 repo).
   - Open a new Claude Code session in that directory. Follow the README's documented bootstrap steps verbatim.
   - Confirm: session starts without errors, no missing files referenced, the 8 active plugins resolve (some may require marketplace re-add per README), hooks run on a test Write/Edit.
   - Record any deviations between what README claims and what you had to do in practice — fix the README, re-push, re-test until clean.
   - Delete `claude-bootstrap-test\` when done (it was a throwaway).

**Files likely touched:** `README.md` (new), `ARCHITECTURE.md` (new), `_archive/` (renamed from `_pre_v2_backup`), various `SKILL.md` (frontmatter fixes), `plans/_archive/` (new), `_audits/2026-05-11-skill-frontmatter.md` (new).

**Validation:**
- Both docs readable
- Frontmatter audit shows zero remaining malformed parses for files you own
- `_archive/` is the long-term-archive convention
- **Bootstrap test passes:** fresh clone in temp location starts a clean Claude Code session by following README only

**Rollback:** `git revert <commits>`.

**Stop condition:** ✋ **PAUSE POINT 1** — review README + ARCHITECTURE for accuracy. ✋ **PAUSE POINT 2 (new)** — bootstrap test must pass before declaring Phase 1 complete; if it fails, iterate on README until it succeeds.

---

### Phase 2 — Hygiene and quarantine (archive dead/stale items)

**Goal:** Reduce footprint and noise without deleting anything. No project's lifecycle status is inferred — only confirmed.

**Tasks**
1. `mkdir -p ~/.claude/_quarantine/2026-05-11/`.
2. Move `~/.claude/plugins/marketplaces/claude-code-skills/` → `_quarantine/2026-05-11/marketplaces/claude-code-skills/` (R3).
3. Remove `claude-code-skills` entry from `extraKnownMarketplaces` in `settings.json` AND leave `engineering-skills@claude-code-skills: false` (already false).
4. Move stray skill artifacts:
   - `skills/cd-ground-overlays/cd-ground-overlays.zip` → `_quarantine/2026-05-11/skills/cd-ground-overlays/`
   - `skills/cd-ground-overlays/_tmp/` if empty → quarantine
   - `skills/dxf-to-kmz/.git/` → investigate; if it's a vestigial clone, quarantine; if it's an active submodule, document
5. Investigate `~/.claude/projects/C--Users-thalf--claude-mem-observer-sessions/` (819 MB):
   - Read `~/.claude/plugins/marketplaces/thedotmack/.../claude-mem` for retention docs
   - If no rotation, compress oldest 50% to `_quarantine/2026-05-11/claude-mem-observer/` and configure rotation
6. **Per-project memory inventory (revised — no inference).** Walk all 13 directories under `~/.claude/projects/*/memory/`. Produce a neutral table at `~/.claude/_audits/2026-05-11-project-memory.md`:

   | Project dir | Last-modified | Files | Size | Notes (last-modified file name only) |
   |---|---|---:|---:|---|

   No "abandoned/active/completed" judgments in this table. Show only the facts. Then **for each row, ask the user to confirm one of: ACTIVE (do not touch), COMPLETED (move to `_quarantine/2026-05-11/project-memory/`), UNKNOWN (leave in place; revisit later).** Use AskUserQuestion or an interactive table — one row at a time is fine for 13 entries.

   *Note: matrix-quote-web-demo is a live deployment at matrix-quote-web-demo.vercel.app per user correction in v2 review; expect at least matrix-quote-app, matrix-quote-web, matrix-quote-web-demo to be confirmed ACTIVE.*

7. Apply only the moves explicitly confirmed COMPLETED in step 6. UNKNOWN and ACTIVE stay in place.
8. Commit: `chore: quarantine disabled marketplace + stale artifacts + user-confirmed completed-project memory`.

**Files likely touched:** moves only, no edits except `settings.json` (remove `claude-code-skills` marketplace entry) and the new `_audits/` file.

**Validation:** `du -sh ~/.claude` should drop by ~30–50 MB from the marketplace move (more if observer-sessions compression is applied; project-memory drop depends on user confirmations). Session restart shows no warnings about missing marketplace. No active skill/agent regression.

**Rollback:** Move back from `_quarantine/`.

**Stop conditions:**
- ✋ **PAUSE POINT 1** — before step 5, confirm claude-mem observer retention policy understood.
- ✋ **PAUSE POINT 2 (new)** — at step 6, **user confirms each of the 13 project memory directories as ACTIVE/COMPLETED/UNKNOWN before any move.** No project should be moved on inference alone.
- ✋ **PAUSE POINT 3** — restart Claude Code in a test session after step 8 and verify domain skills + GSD skills work, no missing-file errors.

---

### Phase 3 — Observability first, then supersession (ultrathink resequence)

**Goal:** Measure the system, then quarantine no-op hooks and replace custom code with native features where applicable. Every reduction claim must be backed by log data, not estimate.

#### Architectural note on the wrapper approach

To time every hook without modifying upstream GSD scripts (which `gsd-update` would clobber), wrap each hook command in `settings.json` with a thin `_log_run.py`. Pattern:

Before:
```json
"command": "\"C:/Program Files/nodejs/node.exe\" \"C:/Users/thalf/.claude/hooks/gsd-prompt-guard.js\""
```

After:
```json
"command": "python C:/Users/thalf/.claude/hooks/_log_run.py gsd-prompt-guard -- \"C:/Program Files/nodejs/node.exe\" \"C:/Users/thalf/.claude/hooks/gsd-prompt-guard.js\""
```

The wrapper:
1. Captures `time.monotonic()` at start
2. Reads stdin once, buffers it
3. Spawns the underlying command with the buffered stdin piped through
4. Captures stdout, stderr, exit code
5. Captures `time.monotonic()` at end
6. Writes `{ts, hook, tool, duration_ms, exit, file_path}` to `~/.claude/logs/hooks.jsonl`
7. Forwards stdout/stderr to its own stdout/stderr
8. Exits with the underlying exit code

This is invisible to the hooks themselves and to Claude Code.

#### Tasks

1. **Write `~/.claude/hooks/_log_run.py`** (~50 lines, single file, Python stdlib only). Wire it as a wrapper for all 15 currently-wired hooks by updating `settings.json`. Add log rotation at 10 MB (`hooks.jsonl` → `hooks.jsonl.1`, keep 5 generations).
2. **Add a baseline measurement script** `~/.claude/hooks/_summarize_logs.py` that reads `hooks.jsonl` and prints: per-hook invocation count, mean/p50/p95 duration, exit-code histogram, timeout count, total wall-clock cost per session. ~40 lines.
3. **Capture 24-hour pre-quarantine baseline.** Use Claude Code normally for one day. At the end, run `_summarize_logs.py` and save output to `~/.claude/_audits/2026-05-11-phase3-baseline.md`. Commit.
4. **Quarantine `gsd-read-guard.js`** (explicit no-op in CC, `hooks/gsd-read-guard.js:39-60`). Move to `_quarantine/2026-05-11/hooks/`. Remove its PreToolUse entry from `settings.json`.
5. **Quarantine `gsd-workflow-guard.js`** (opt-in, currently off, `hooks/gsd-workflow-guard.js:1-12`). Move to `_quarantine/2026-05-11/hooks/`. Remove its PreToolUse entry.
6. **Add native `permissions.deny` rules** for the destructive patterns currently caught only by `block_dangerous.py`:
   ```json
   "permissions": {
     "allow": ["..."],
     "deny": [
       "Bash(rm -rf /:*)",
       "Bash(rm -rf ~:*)",
       "Bash(git push --force:*)",
       "Bash(shutdown:*)",
       "Bash(mkfs.*:*)",
       "Bash(chmod -R 777 /:*)"
     ]
   }
   ```
   Keep `block_dangerous.py` as defense-in-depth for the patterns native rules can't express (SQL, fork bombs, curl-pipe-shell).
7. **Decouple absolute Node path (R8).** Replace every `\"C:/Program Files/nodejs/node.exe\"` in `settings.json` with `node`. Document the PATH requirement in README. Commit.
8. **Capture 24-hour post-quarantine baseline.** Use Claude Code normally for one day. Run `_summarize_logs.py`, save to `~/.claude/_audits/2026-05-11-phase3-post.md`.
9. **Diff and document.** Compare pre vs post:
   - Hook invocations per Write/Edit cycle (expected: drops by 2)
   - Total per-cycle wall-clock cost (expected: drops by 200–400 ms based on Node startup × 2; verify)
   - Any new timeouts or errors (expected: none)
   - Token-cost impact at session start (orthogonal to this phase, but record if visible)
   Write findings to `~/.claude/_audits/2026-05-11-phase3-summary.md`. If gains are <50% of estimate, investigate before continuing (the no-ops may not be the dominant cost).
10. Commit: `refactor: supersede no-op hooks, add native deny rules, decouple node path — measured Δ in _audits/`.

**Files likely touched:** `_log_run.py` (new), `_summarize_logs.py` (new), `settings.json` (every hook command wrapped + permissions section), `_quarantine/2026-05-11/hooks/` (2 files moved), 3 audit files (new), `README.md` (PATH note).

**Validation:**
- `hooks.jsonl` exists and accumulates entries during normal use
- Pre-baseline audit shows expected hook activity
- Post-baseline audit shows 2 fewer hook invocations per Write/Edit cycle
- `Bash(rm -rf /tmp/test)` is denied by the native rule with a clear message
- `Bash(git push --force origin main)` is denied

**Rollback:** `git revert`. Wrapper rollout is reversible by reverting `settings.json`.

**Stop conditions:**
- ✋ **PAUSE POINT 1** — after step 1 (wrapper rollout): confirm one test session works cleanly with logging in place before starting the 24-hour clock.
- ✋ **PAUSE POINT 2** — after step 3 (pre-baseline): review the audit summary; confirm baseline numbers look sane before quarantining.
- ✋ **PAUSE POINT 3** — after step 9 (post-baseline diff): review actual measured gains. If gains are unexpectedly small, decide whether to proceed or revert and investigate.

---

### Phase 4 — Permissions hardening

**Goal:** Tighten the consent surface. (Logging from Phase 3 stays in place.)

**Tasks**
1. **Replace `permissions.allow: ["Bash"]`** with an explicit allowlist. Starting set — expect to expand over the first week as legitimate read-only commands trigger unnecessary prompts; add them via `settings.json` edit, never via `skipAutoPermissionPrompt`:
   ```json
   "allow": [
     "Bash(git status)",
     "Bash(git log:*)",
     "Bash(git diff:*)",
     "Bash(git branch:*)",
     "Bash(git show:*)",
     "Bash(git add:*)",
     "Bash(ls:*)",
     "Bash(pwd)",
     "Bash(node:*)",
     "Bash(node --version)",
     "Bash(python --version)",
     "Bash(python:*)",
     "Bash(uv:*)",
     "Bash(npm test:*)",
     "Bash(npx --no-install:*)",
     "Bash(pip install:*)",
     "Bash(pip show:*)",
     "Bash(pytest:*)"
   ]
   ```
   **Explicitly excluded:** `Bash(git commit -m:*)`. Commits should stay explicit per turn. (Override only by deliberate per-project local settings.)
2. **Remove `skipAutoPermissionPrompt: true` and `agentPushNotifEnabled: true`** from `settings.json`. Restart and observe whether anything misbehaves; restore individually only if you confirm they have effect. Document outcome in `~/.claude/_audits/2026-05-11-unknown-settings.md`.
3. **Add to `permissions.deny`:** `Bash(git commit -m * --no-verify:*)` and `Bash(git push --force-with-lease shared-branch:*)` patterns to match your CLAUDE.md guardrails.
4. **Audit `.credentials.json`.** Confirm it does not contain credentials you don't recognize. Confirm `.gitignore` excludes it (Phase 0 handles this; re-verify with `git check-ignore -v ~/.claude/.credentials.json`).
5. Commit: `feat: explicit Bash allowlist + remove undocumented settings keys`.

**Files likely touched:** `settings.json` (permissions section), `_audits/2026-05-11-unknown-settings.md` (new).

**Validation:** Trigger `Bash(ls /etc)` — should prompt (not in allowlist). Trigger `Bash(git status)` — should auto-approve. Trigger `Bash(git push --force)` — denied. Trigger `Bash(git commit --no-verify -m "..."` — denied.

**Rollback:** `git revert`.

**Stop condition:** ✋ One day of normal usage to confirm no surprises. **PAUSE POINT.**

---

### Phase 5 — Performance and context discipline

**Goal:** Reduce session-start cost.

**Tasks**
1. **Use existing Phase 3 logs** to measure ongoing hook cost (no new logging needed — Phase 3 set this up).
2. **Consolidate `gsd-ns-*` routing skills (R9).** Options:
   - Combine into one `gsd-ns` skill with a sub-routing argument
   - Or fold into `gsd-help`
   - Or quarantine if unused (check transcripts for invocations)
3. **Audit `claude-mem` plugin (`thedotmack` marketplace) vs `task-observer` skill vs native auto-memory:**
   - All three persist cross-session knowledge in slightly different ways
   - claude-mem produced 819 MB of observer data on one project
   - Decide: keep `claude-mem` for explicit history queries; rely on native auto-memory (`projects/.../memory/`) for live recall; quarantine `task-observer` if redundant
4. **Consider whether `effortLevel: "xhigh"` is the right default.** The `/effort` command supports `max` (this session) and presumably lower levels. `xhigh` is undocumented and may map to `max`. Verify and document.
5. Optional: prune indexed surface area further by consolidating duplicate-functionality plugin skills. `superpowers` skills like `writing-plans` overlap with native plan mode; `subagent-driven-development` overlaps with Task tool. Keep but be aware.
6. Commit: `perf: consolidate ns-routing, audit memory plugins, document effort level`.

**Files likely touched:** various skill files, `settings.json` (`effortLevel`), README docs.

**Validation:** Session-start token count reduced (compare context-mode stats before/after). Hook latency per Write/Edit cycle steady or reduced vs Phase 3 post-baseline.

**Rollback:** `git revert`.

**Stop condition:** ✋ Verify measurement-based gains. **PAUSE POINT.**

---

### Phase 6 — Prompt and agent quality upgrades

**Goal:** Lift agent and skill prompt quality to match the core 6 standard.

**Tasks**
1. **Audit oversized GSD agents** (>500 body lines):
   - `gsd-debugger` (1439), `gsd-planner` (1242), `gsd-plan-checker` (971), `gsd-codebase-mapper` (840), `gsd-phase-researcher` (827), `gsd-verifier` (817), `gsd-roadmapper` (675), `gsd-project-researcher` (664), `gsd-code-fixer` (659), `gsd-executor` (623), `gsd-doc-writer` (602)
   - Look for: redundant context-loading via `@$HOME/...` (some agents pull in 3+ reference docs), boilerplate that's now in CLAUDE.md, verbose role descriptions
   - Goal: reduce by 20–40% without functional loss. Use the diff to validate behavior.
   - **Note:** these are upstream GSD agents. Edits will conflict with future `gsd-update`. Decide between: (a) accept the conflict and re-apply locally after each update, (b) maintain a forked manifest, (c) skip this work and accept agent size.
2. **Enhance global `CLAUDE.md`:**
   - Add a "Scope of this file" section
   - Add a pointer to `~/.claude/projects/<dir>/memory/MEMORY.md` so future sessions know where memory lives
   - Add a "When in doubt, ask" line for ambiguous tasks
3. **Add `~/.claude/skills/README.md`** describing your skill conventions (frontmatter fields used, naming convention, where scripts live, how to test). Helps future skill creation.
4. **Set up a tiny hook test harness:** `~/.claude/hooks/_tests/` directory with fixture-based pytest that feeds JSON to each hook on stdin and asserts exit codes. Run via `pytest ~/.claude/hooks/_tests/`.
5. Commit: `refactor: trim oversized GSD agents, enhance CLAUDE.md, add hook tests`.

**Files likely touched:** ~10 GSD agent files (or none, per decision above), `CLAUDE.md`, `skills/README.md`, `hooks/_tests/*`.

**Validation:** Diff review per agent. Hook tests pass.

**Rollback:** `git revert`.

**Stop condition:** ✋ Manual review of trimmed agents to ensure no functional regression. **PAUSE POINT.**

---

### Phase 7 — Evolvability and governance

**Goal:** Make this maintainable as Claude Code evolves.

**Tasks**
1. **Write `~/.claude/CONVENTIONS.md`:**
   - When to write a skill vs an agent vs a hook
   - Naming conventions (`gsd-*` for GSD framework, `_archive/`, `_quarantine/` for transient)
   - Frontmatter standards
   - How to retire something (move to `_archive/`, document, commit)
   - Required fields for new skills
2. **Set up a quarterly review checklist** — re-run the audit script, check `_quarantine/` for items >90 days old (delete), check `logs/hooks.jsonl` for high-failure hooks, check `projects/` for memory bloat. Commit this checklist as `~/.claude/_governance/quarterly-review.md`.
3. **Decide on a remote backup cadence:** `git push` after each meaningful Phase commit; weekly `git push` for state-significant changes.
4. Final commit: `docs: add CONVENTIONS + quarterly review checklist`.

**Files likely touched:** `CONVENTIONS.md`, `_governance/quarterly-review.md`, both new.

**Validation:** None automated. Read-through review.

**Stop condition:** No further pause. This phase is documentation only.

---

## 7. Explicit pause points

Each marked with ✋ in §6. Summarized:

1. **Before Phase 1** — git repo initialized + pushed to remote, baseline committed. Confirm before docs work.
2. **Within Phase 1** — README + ARCHITECTURE reviewed for accuracy.
3. **End of Phase 1 (new)** — **Bootstrap reproducibility test must pass** in `C:\Users\thalf\tmp\claude-bootstrap-test\` before Phase 1 is declared complete. If it fails, iterate on README.
4. **Within Phase 2** — claude-mem retention policy understood before observer compression.
5. **Within Phase 2 (new)** — **User explicitly confirms each of 13 project memory dirs as ACTIVE/COMPLETED/UNKNOWN.** No inference. matrix-quote-web-demo is known ACTIVE per v2 review.
6. **After Phase 2** — session restart clean, no missing-file errors.
7. **Within Phase 3** — wrapper rollout test session before starting 24-hour clock.
8. **Within Phase 3** — review pre-baseline audit before quarantining anything.
9. **End of Phase 3** — review measured gains vs estimate; decide proceed/investigate.
10. **End of Phase 4** — one day of normal usage to confirm permission tightening.
11. **End of Phase 5** — measurement-based gains verified.
12. **Within Phase 6** — each trimmed agent diff reviewed before commit.

Additional always-pause items (regardless of phase):
- Changing `enabledPlugins` (could disable skills you rely on mid-task).
- Editing global `~/.claude/CLAUDE.md` (affects every project).
- Touching `.credentials.json` or anything in `_pre_v2_backup/` before Phase 1 promotion.
- Modifying any file under `~/.claude/projects/*/memory/` (live memory — even quarantining can affect cross-session recall).
- Any `permissions.allow` rule change that affects Bash autoexec.

---

## 8. Unknowns and open questions

### Blocking (require user answer before execution)
- **Remote git host for `~/.claude` backup.** GitHub private repo, GitLab, self-hosted? Affects Phase 0 final step and Phase 1 reproducibility test.
- **claude-mem retention policy.** Are the 819 MB of observer sessions value or noise? Before Phase 2 step 5, you need to decide if any of it is referenced.
- **Are `agentPushNotifEnabled` and `skipAutoPermissionPrompt` undocumented official settings or vestigial?** Affects Phase 4 step 2. Recommend removing and observing.
- **Per-project memory directory status.** Phase 2 step 6 requires user confirmation for each of 13 entries.

### Non-blocking (answerable by inspection — agent can resolve)
- Whether `gsd-check-update-worker.js` and `gsd-update-banner.js` are truly invoked from `gsd-check-update.js`. Grep can confirm.
- Whether the `skills/dxf-to-kmz/.git/` is an intentional submodule or a clone artifact.
- Whether prettier and black are installed and functional (affects whether `format.py` is doing anything).
- Exact extent of malformed SKILL.md frontmatter beyond `task-observer` (Phase 1 step 4 will enumerate).

### Inspection-only (don't need user, but worth recording)
- The exact size of `~/.claude/projects/C--Users-thalf/` (48 MB) — your own session history. Likely keepable.
- Whether `~/.claude/get-shit-done/` contains anything customized vs. the upstream GSD install (suggests whether `gsd-update` would clobber local mods).

---

## 9. Anti-recommendations

Things that look like fixes but are not worth prioritizing.

1. **Don't rewrite the GSD planning framework.** It's a working meta-platform. Either commit to it or migrate cleanly later; piecemeal rewrites of `gsd-*` agents will leave you with a Frankenstein. The platform plan keeps GSD as-is and only quarantines no-op hooks.
2. **Don't introduce a configuration manager (Nix, Chezmoi, dotfiles framework) yet.** A git repo + `.gitignore` covers 90% of the value. Add a layer of indirection only after you've used a vanilla repo for a quarter and identified concrete friction.
3. **Don't merge the v1 GSD hooks into v2 Python.** They serve different concerns (GSD-state-aware vs. lifecycle utilities). Keep them as two layers.
4. **Don't write a custom statusLine to replace `gsd-statusline.js`.** Either keep GSD's (you use it) or accept the default. A 485-line replacement is a yak.
5. **Don't try to deduplicate auto-memory + claude-mem + task-observer in one pass.** All three have subtly different roles. Audit in Phase 5 with measurements; don't preemptively rip one out.
6. **Don't migrate to project-local `.claude/settings.json` for everything.** Global is correct for cross-project preferences. Use project-local only for project-specific permissions/MCP servers.
7. **Don't add a custom MCP server.** Plugins already provide MCP. Adding bespoke ones is a maintenance burden without a clear use case.
8. **Don't add an Anthropic API CLI tool to `~/.claude/`.** Use the existing `claude` CLI. The configuration repo is config, not application code.
9. **Don't deeply refactor the 63 GSD skills.** They're upstream; `gsd-update` should manage them. Local customizations should live as overrides or wrappers.
10. **Don't move per-project memory to global.** Per-project scoping is correct. Quarantine completed projects' memory, don't merge them.
11. **(new)** **Don't add a CHANGELOG.md.** Git history is the changelog. A manually-maintained file rots when forgotten. Use `git log --oneline` and good commit messages.

---

## 10. Final recommended path

### Do first (Phase 0, immediately)
1. `git init ~/.claude` + write `.gitignore` from §6.0 + commit baseline.
2. Push to a private remote.

This is the single highest-leverage move. Everything else is reversible afterward.

### Do this week (Phases 1–2)
3. Write README.md + ARCHITECTURE.md.
4. Promote `_pre_v2_backup/` to `_archive/`. Scan all SKILL.md frontmatter. Archive old plans.
5. **Run the Phase 1 bootstrap reproducibility test.** Iterate on README until clean.
6. Quarantine `claude-code-skills` marketplace (32 MB) and stale skill artifacts.
7. Inventory the 13 project memory dirs neutrally; user confirms each before any move.
8. Investigate and bound the claude-mem 819 MB observer cache.

### Do next month (Phases 3–4)
9. Add `_log_run.py` hook wrapper. Capture 24h pre-baseline.
10. Quarantine `gsd-read-guard` and `gsd-workflow-guard`. Add native `permissions.deny` rules. Decouple Node path.
11. Capture 24h post-baseline; document measured Δ.
12. Tighten `permissions.allow` from blanket-Bash to explicit list. Remove undocumented settings keys.

### Defer (Phases 5–7)
13. Performance measurement + ns-routing consolidation.
14. Agent prompt trimming (decide GSD-update conflict strategy first).
15. Governance docs (CONVENTIONS.md only — no CHANGELOG.md).

### Do not do
- Don't touch GSD skills/agents content until Phase 6, and only after deciding update strategy.
- Don't disable plugins until you can A/B test the impact.
- Don't act on undocumented settings keys until you've confirmed by removal what they do (or don't).
- Don't infer any project's lifecycle status — always ask.

### Highest-leverage next execution prompt (when you're ready)

After approval of this plan, the next Claude Code session should be invoked with a prompt along these lines:

> "Execute Phase 0 of `~/.claude/plans/mission-you-are-replicated-canyon.md`: initialize git in `~/.claude`, write the `.gitignore` per the plan, commit the baseline, push to <remote>. Do not do anything else. Report the commit SHA, total tracked file count, and remote URL. Pause for my approval before Phase 1."

Strict-scope, one-phase, reversible, stops at the pause point. After Phase 0 is committed and pushed, repeat with Phase 1, then Phase 2, etc. The pause points are doing real work — don't skip them.

---

## Verification methods

For each phase, verification = running these commands or doing these checks before claiming "done":

- **Phase 0:** `git -C ~/.claude log --oneline` shows the snapshot commit. `git -C ~/.claude ls-files | wc -l` matches expectation. `git -C ~/.claude status` clean. `git -C ~/.claude ls-remote origin` returns refs.
- **Phase 1:** Open README.md and ARCHITECTURE.md, verify they describe what actually exists. Frontmatter audit shows zero remaining malformed parses in files you own. **Bootstrap test:** fresh clone in `C:\Users\thalf\tmp\claude-bootstrap-test\` starts a clean Claude Code session by following only the README.
- **Phase 2:** `du -sh ~/.claude` drops by the marketplace size + any compressed observer + user-confirmed memory moves. Domain and GSD skills still trigger. No "marketplace not found" errors. The `_audits/2026-05-11-project-memory.md` table shows every project labeled.
- **Phase 3:** `~/.claude/logs/hooks.jsonl` accumulates entries. `_summarize_logs.py` produces both pre- and post-baseline audits. Diff shows 2 fewer hook invocations per Write/Edit cycle, with measured wall-clock cost reduction documented in `_audits/2026-05-11-phase3-summary.md`. Native deny rules block test commands.
- **Phase 4:** `Bash(ls)` requires approval if not in allowlist. `Bash(git status)` auto-approves. `Bash(git push --force)` denied. `~/.claude/_audits/2026-05-11-unknown-settings.md` documents removal outcome.
- **Phase 5:** Session-start token count drop measurable in context-mode stats. Hook latency per cycle steady or lower vs Phase 3 post-baseline.
- **Phase 6:** Agent bodies trimmed; spawning each trimmed agent in a real workflow returns the same kind of output. `pytest hooks/_tests/` green.
- **Phase 7:** `~/.claude/CONVENTIONS.md` and `~/.claude/_governance/quarterly-review.md` exist. Next planning session uses them.

---

## Files referenced

For audit traceability — all citations in this plan, in order of appearance:

- `~/.claude/settings.json` (210 lines, primary config)
- `~/.claude/settings.local.json` (9 lines, local-only permissions)
- `~/.claude/CLAUDE.md` (28 lines, global preferences)
- `~/.claude/hooks/gsd-statusline.js` (485 lines, statusLine impl)
- `~/.claude/hooks/format.py` (43 lines, prettier/black wrapper)
- `~/.claude/hooks/block_dangerous.py` (44 lines, regex denylist)
- `~/.claude/hooks/session_context.py` (40 lines, git context print)
- `~/.claude/hooks/protect_main.py` (40 lines, protected branch refuse)
- `~/.claude/hooks/gsd-prompt-guard.js` (97 lines, advisory injection scan)
- `~/.claude/hooks/gsd-read-guard.js` (101 lines, NO-OP in Claude Code, explicit)
- `~/.claude/hooks/gsd-workflow-guard.js` (94 lines, opt-in, currently off)
- `~/.claude/agents/explorer.md` (18 lines, model: haiku, exemplar)
- `~/.claude/agents/gsd-debugger.md` (1439 lines, @-mention references, exemplar of GSD scale)
- `~/.claude/_pre_v2_backup/2026-05-11-103009/` (37 KB, v1 PowerShell hooks + v1 agents)
- `~/.claude/plugins/marketplaces/claude-code-skills/` (32 MB, disabled-plugin marketplace)
- `~/.claude/projects/C--Users-thalf--claude-mem-observer-sessions/` (819 MB, observer cache)
- `C:\Users\thalf\Downloads\claude-code-audit-2026-05-11-105016.md` (546 KB, prior audit)
