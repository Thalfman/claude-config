# Personal Claude Code config

This is `~/.claude/` — global Claude Code configuration for user `thalf`, tracked
in git so it is reproducible.

**Primary purpose:** imported into Claude Code **cloud sessions**
(claude.ai/code) by the environment's own setup step, which clones this repo
and overlays it onto the env's existing `~/.claude/`. The same repo also
bootstraps a fresh local machine (see below).

## What lives here

- `CLAUDE.md` — global preferences loaded into every session.
- `settings.json` — runtime config: enabled plugins, marketplace registry,
  statusLine, permissions, effort level. Note: it does **not** currently wire any
  `hooks` (see `hooks/` below).
- `statusline.js` — the status-line HUD (branch, context-window usage, model
  effort). Wired via `settings.json` → `statusLine.command`.
- `skills/` — 42 user-owned skills (writing, planning, code-quality, OpenSpec,
  issue/PRD, design, teaching, meta). One dir per skill, each with `SKILL.md`.
- `agents/` — 6 subagent definitions: `explorer`, `implementer`, `judge`,
  `planner`, `reviewer`, `tester`.
- `commands/` — 8 slash commands: `opsx/{apply,archive,explore,propose}`,
  `resume`, `ship-check`, `status`, `sweep`.
- `hooks/` — 6 Python hook scripts (`backup_transcript`, `block_dangerous`,
  `format`, `protect_main`, `session_context`, `session_logger`). **Present but
  not wired** in `settings.json`; they are inert until referenced under a
  `hooks.<event>` key.
- `output-styles/` — `concise.md` (custom output style; `settings.json` currently
  selects the built-in `proactive` style).
- `memory/` — tracked memory index (`MEMORY.md`) and individual memory files.
- `plugins/installed_plugins.json`, `plugins/known_marketplaces.json` — captured
  plugin/marketplace registry. Replayed to install plugins in a fresh
  environment (the plugin *payloads* under `plugins/cache/` and
  `plugins/marketplaces/` are gitignored and re-fetched).
- `_archive/`, `_audits/`, `plans/` — historical snapshots, audit reports, and
  planning artifacts. Already-tracked; `.gitignore` blocks new additions.

See `ARCHITECTURE.md` for the import model, settings contents, and plugin list.

## Plugins (9 enabled, 6 marketplaces)

| Plugin | Marketplace | Source |
|---|---|---|
| `superpowers` | claude-plugins-official | built-in |
| `context7` | claude-plugins-official | built-in |
| `skill-creator` | claude-plugins-official | built-in |
| `document-skills` | anthropic-agent-skills | `github:anthropics/skills` |
| `codex` | openai-codex | `github:openai/codex-plugin-cc` |
| `andrej-karpathy-skills` | karpathy-skills | `github:forrestchang/andrej-karpathy-skills` |
| `understand-anything` | understand-anything | `git:Lum1104/Understand-Anything` |
| `bmad-pro-skills` | bmad-method | `github:bmad-code-org/bmad-method` |
| `bmad-method-lifecycle` | bmad-method | `github:bmad-code-org/bmad-method` |

## Cloud import (primary use)

The cloud environment's own setup step is responsible for cloning this repo and
overlaying it onto `~/.claude/`. Provide a fine-grained, read-only GitHub PAT
scoped to this repo as an environment secret so the env can authenticate the
clone. The import script itself lives in the environment, not in this repo.

### Resetting a cloud environment

Cloud environments **persist their filesystem** across sessions, and there is no
UI "reset" button. The env's overlay step runs onto whatever is already there.
For a fully clean slate, recreate the environment (Managed Agents API: delete
the environment when no session references it, then create a new one) so the
overlay runs against a fresh `~/.claude/`.

## Bootstrap a fresh local machine

To recreate `~/.claude/` directly (the "clone AS `~/.claude`" path, distinct from
the cloud overlay):

```bash
# 1. Clone (the existing ~/.claude/ must not already be a git repo at this path).
git clone https://github.com/Thalfman/claude-config.git ~/.claude

# 2. Install the Claude Code CLI and authenticate (creates ~/.claude/.credentials.json,
#    which is NOT committed).
claude login

# 3. Register the non-built-in marketplaces (contents under plugins/marketplaces/
#    are gitignored and must be re-fetched). claude-plugins-official is built in.
claude plugin marketplace add github://anthropics/skills
claude plugin marketplace add github://openai/codex-plugin-cc
claude plugin marketplace add github://forrestchang/andrej-karpathy-skills
claude plugin marketplace add https://github.com/Lum1104/Understand-Anything.git
claude plugin marketplace add github://bmad-code-org/bmad-method

# 4. Install the enabled plugins.
claude plugin install document-skills@anthropic-agent-skills
claude plugin install superpowers@claude-plugins-official
claude plugin install context7@claude-plugins-official
claude plugin install skill-creator@claude-plugins-official
claude plugin install codex@openai-codex
claude plugin install andrej-karpathy-skills@karpathy-skills
claude plugin install understand-anything@understand-anything
claude plugin install bmad-pro-skills@bmad-method
claude plugin install bmad-method-lifecycle@bmad-method

# 5. Start a session; confirm the skills list and statusLine render.
claude
```

## Prerequisites

| Tool | Why |
|---|---|
| Claude Code CLI | the harness (`claude` on PATH) |
| Node.js (any LTS) | `statusline.js` + plugin runtime |
| Python 3 | the `hooks/` scripts, if wired |
| `git` | clone/update |

## What does NOT live here (gitignored)

- `.credentials.json` — OAuth tokens. Re-created by `claude login`.
- `settings.local.json` — per-machine settings (machine-specific paths).
- `sessions/`, `projects/`, `transcript-backups/`, `history.jsonl`, `todos/`,
  `tasks/`, `debug/`, `skill-observations/`, `backups/` — session/runtime state.
- `daemon.*`, `daemon/`, `jobs/` — background daemon runtime state (locks, logs,
  PIDs, pipe key, live job state).
- `cache/`, `plugins/cache/`, `plugins/data/`, `plugins/marketplaces/`, `statsig/`,
  `telemetry/` — caches and regenerable plugin payloads.
- `memory/session-log.jsonl` — machine-local cross-project session index.
- `**/__pycache__/`, `**/*.pyc`.

## How to add things

### A skill
1. `mkdir ~/.claude/skills/<name>` and create `SKILL.md` with `name:` +
   `description:` frontmatter (use a `>`/`|` block scalar if the description holds
   `:` or quotes).
2. Body is Markdown. Commit. Available on the next session start.

### An agent
Create `~/.claude/agents/<name>.md` with `name:`, `description:`, optional
`tools:` and `model:` frontmatter. Keep it tight — see `agents/explorer.md`.

### A hook
Write the script under `~/.claude/hooks/` (read stdin JSON, exit `0` to pass / `2`
to block), then wire it in `settings.json` under the lifecycle event
(`SessionStart`, `PreToolUse`, `PostToolUse`, `PreCompact`). Hooks are inert until
wired.

## Credentials

**Never in this repo.** `.gitignore` excludes `.credentials.json`; re-create via
`claude login`. For application secrets use the environment's secret management —
never inline.
