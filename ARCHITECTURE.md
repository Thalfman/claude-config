# Architecture of `~/.claude/`

The runtime model for this config: hook lifecycle, plugins, GSD's scope, the
statusLine, and what loads when. Intended for the question "what is going to
fire when I start a session or invoke a tool?"

## Hook lifecycle

Hooks are wired in `settings.json`. Each `hooks.<event>` array is a list of
matchers + commands. The harness runs them in order; non-zero exit (typically
`2`) blocks the tool call.

```
SessionStart
  ├─ gsd-check-update.js          (Node)  — checks GSD for upstream updates
  ├─ gsd-session-state.sh         (bash)  — restores per-project GSD state
  ├─ context-mode-cache-heal.mjs  (Node)  — plugin cache integrity bridge
  └─ session_context.py           (py)    — prints git branch + dirty count

PreToolUse [Write|Edit]
  ├─ gsd-prompt-guard.js          (Node)  — advisory injection scan on .planning/ writes
  ├─ gsd-read-guard.js            (Node)  — NO-OP in Claude Code (exits when CLAUDE_CODE_ENTRYPOINT set)
  ├─ gsd-workflow-guard.js        (Node)  — opt-in (config hooks.workflow_guard); off by default
  └─ protect_main.py              (py)    — refuses Write/Edit on protected branches (main/master/release/prod/production)

PreToolUse [Bash]
  ├─ gsd-validate-commit.sh       (bash)  — validates commit-style Bash invocations
  └─ block_dangerous.py           (py)    — regex denylist for destructive shell patterns (rm -rf /, fork bombs, etc.)

PostToolUse [Bash|Edit|Write|MultiEdit|Agent|Task]
  └─ gsd-context-monitor.js       (Node)  — tracks context-window pressure

PostToolUse [Read]
  └─ gsd-read-injection-scanner.js (Node) — scans Read output for prompt-injection markers

PostToolUse [Write|Edit]
  └─ gsd-phase-boundary.sh        (bash)  — detects GSD phase transitions on file writes

PostToolUse [Write|Edit|MultiEdit]
  └─ format.py                    (py)    — runs prettier/black on the touched file (silent if absent)

PreCompact
  └─ backup_transcript.py         (py)    — snapshots transcript before compaction

statusLine (continuous)
  └─ gsd-statusline.js            (Node)  — renders branch + phase + token cost in the status bar
```

**Per-Write/Edit cycle hook count:** PreToolUse 4 (gsd-prompt-guard, gsd-read-guard,
gsd-workflow-guard, protect_main) + PostToolUse 3 (gsd-context-monitor, gsd-phase-boundary,
format). Phase 3 of the migration plan instruments this with a `_log_run.py` wrapper to
measure actual cost, then quarantines the two no-op GSD hooks (`gsd-read-guard`,
`gsd-workflow-guard`).

## Plugins

| Plugin | Marketplace | Purpose | Status |
|---|---|---|---|
| `superpowers` | `claude-plugins-official` (built-in) | Brainstorm/plan/execute skills, finishing-a-branch, TDD, debugging | enabled |
| `document-skills` | `anthropic-agent-skills` (`anthropics/skills`) | Office docs, PDF, slides, web artifacts, brand guidelines | enabled |
| `frontend-design` | `claude-plugins-official` (built-in) | Distinctive frontend code | enabled |
| `context7` | `claude-plugins-official` (built-in) | Live library docs via MCP | enabled |
| `skill-creator` | `claude-plugins-official` (built-in) | Tools for authoring and evaluating skills | enabled |
| `codex` | `openai-codex` (`openai/codex-plugin-cc`) | Codex rescue/setup, GPT-5.4 prompting helpers | enabled |
| `context-mode` | `context-mode` (`mksglu/context-mode`) | Sandbox-execute large outputs; FTS5 cross-session index | enabled |
| `claude-mem` | `thedotmack` (`thedotmack/claude-mem`) | Persistent cross-session observation memory | enabled |
| `engineering-skills` | `claude-code-skills` (`alirezarezvani/claude-skills`) | 100+ AI skills targeting Gemini and Claude Code | **disabled** — Phase 2 quarantines the marketplace |

## Get Shit Done (GSD)

GSD is a multi-phase planning framework layered on top of Claude Code. It is
not a plugin — it is installed as a unit of agents, skills, hooks, and
reference docs under `~/.claude/`.

| Surface | Count | Where |
|---|---|---|
| Skills | 63 (incl. 6 `gsd-ns-*` routing stubs) | `skills/gsd-*` |
| Agents | 33 | `agents/gsd-*.md` |
| Hooks | 9 | `hooks/gsd-*.{js,sh,mjs}` |
| Framework | `bin/`, `contexts/`, `references/`, `templates/`, `workflows/` | `get-shit-done/` |
| Manifest | install record | `gsd-file-manifest.json` |

GSD agents reference `@$HOME/.claude/get-shit-done/references/*.md`. Updates
ship via `gsd-update`. Local edits to GSD files will conflict on update;
prefer override-wrappers over in-place edits.

Of the 9 GSD hooks, three are no-ops in this harness:
`gsd-read-guard.js` (exits when `CLAUDE_CODE_ENTRYPOINT` is set — targeted at
non-Claude harnesses), `gsd-workflow-guard.js` (opt-in via
`hooks.workflow_guard: true`, currently off), and arguably
`gsd-prompt-guard.js` (only fires on `.planning/` writes).

## statusLine

Driven by `gsd-statusline.js` (485 lines), wired via `settings.json` →
`statusLine.command`. Renders branch, GSD phase, and token-cost indicator. A
hand-rolled bash one-liner would also work; the current depth is GSD-specific.

## Context loading order (typical session start)

1. Anthropic system prompt + tool list.
2. `CLAUDE.md` (global preferences).
3. Auto-memory `projects/C--Users-thalf/memory/MEMORY.md` index.
4. Skills list — descriptions of all 74 user + active-plugin skills (~7,000
   tokens). Largest single context block.
5. Agents list — frontmatter of all 39 agents.
6. Active plugin SKILL.md descriptions.
7. `context-mode` protection block (~600 tokens).
8. `claude-mem` recent-context block (~1,500 tokens).
9. MCP server instructions for active plugins.
10. The 4 SessionStart hooks fire — `session_context.py` adds git context.

**Estimated session-start context cost: 15,000–20,000 tokens** before user
input. The `gsd-*` skills (63 entries) dominate; Phase 5 considers
consolidating the 6 `gsd-ns-*` routing stubs.

## Custom code vs native Claude Code features

| Custom | Native equivalent | Decision |
|---|---|---|
| `block_dangerous.py` | `permissions.deny: ["Bash(...)"]` rules | Hybrid: keep for rich patterns (SQL, fork bombs); Phase 3 adds native rules for simple cases. |
| `protect_main.py` | none | Keep — narrow purpose, no native alternative. |
| `session_context.py` | none | Keep — adds branch + dirty count to SessionStart context. |
| `format.py` | none | Keep — wraps prettier + black. |
| `backup_transcript.py` | plan mode preserves plans | Keep — transcript backups remain useful. |
| `gsd-statusline.js` | `statusLine.command` | Keep while GSD is in use. |
| `gsd-read-guard.js` | CC natively enforces read-before-edit | Phase 3 quarantines (no-op in CC). |
| `gsd-workflow-guard.js` | plan mode + skills | Phase 3 quarantines (off by default). |
| `gsd-prompt-guard.js` | none | Keep — narrow `.planning/` scope. |

## Failure modes worth knowing

1. **Hook timeouts.** Hooks have 5–30s timeouts; on timeout they fail silently
   (implicit exit 0). A misconfigured hook can quietly stop working. Phase 3's
   logging makes this visible.
2. **`format.py` graceful fallthrough.** If prettier or black is not on PATH,
   `format.py` skips silently. You might think auto-formatting is happening when
   it is not.
3. **`gsd-check-update.js` SessionStart.** If GSD's update server is unreachable,
   you would not know — fails silently.
4. **`claude-mem` observer growth.** No log rotation; one project grew to
   819 MB before being noticed. Phase 2 step 5 caps this.
5. **`agentPushNotifEnabled` and `skipAutoPermissionPrompt` keys in settings.json.**
   Not in Claude Code's documented schema; may be vestigial. Phase 4 removes
   them and observes behavior.
6. **Hardcoded Node path.** 8 hook commands hardcode
   `"C:/Program Files/nodejs/node.exe"`. Phase 3 replaces with `node` (PATH).

## Pointers

- `README.md` — bootstrap + day-to-day mechanics.
- `plans/mission-you-are-replicated-canyon-v2.md` — active migration plan.
- `_audits/2026-05-11-skill-frontmatter.md` — SKILL.md frontmatter audit.
- `_audits/2026-05-11-phase1-gitlink-cleanup.md` — gitlink → tree conversion notes.
- `_archive/2026-05-11-v1-hooks/README.md` — what's in the v1 backup.
