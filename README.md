# Personal Claude Code config

This is `~/.claude/` — global Claude Code configuration for user `thalf`. Tracked
in git so the config is reproducible from a fresh machine.

## What lives here

- `CLAUDE.md` — global preferences loaded into every session.
- `settings.json` — Claude Code runtime config: enabled plugins, marketplace
  registry, hook wiring, statusLine, permissions, effort level.
- `settings.local.json` — per-machine permissions (PowerShell auto-allow rules).
  **Not gitignored**, but treat as machine-local: do not rely on values being
  identical across machines.
- `agents/` — 39 agent definitions (6 core + 33 GSD-namespaced).
- `skills/` — 74 user-owned skills (8 domain + 63 GSD-namespaced + 3 misc).
- `hooks/` — 18 hook scripts (5 Python v2, 10 GSD JS/sh, 2 GSD support, 1 plugin
  bridge). 15 wired in `settings.json`.
- `plans/` — accumulated `/plan-mode` artifacts. Plans older than 30 days move
  to `plans/_archive/`.
- `get-shit-done/` — the GSD planning framework's bin/contexts/templates/
  workflows. Reference target for many GSD agents (`@$HOME/.claude/get-shit-done/...`).
- `_archive/` — long-term-retention snapshots (v1 hooks, etc.). Each subdir
  carries its own README.md.
- `_audits/` — generated audit reports.
- `_quarantine/<date>/` — items pulled out of the active config pending review.
  Gitignored; local-only.
- `_pre_v2_backup/` is **historical**; was promoted to `_archive/2026-05-11-v1-hooks/`
  on 2026-05-11.

See `ARCHITECTURE.md` for the runtime model: hook lifecycle, plugin list with
purpose, context loading order.

## What does NOT live here (gitignored)

- `.credentials.json` — Claude Code's OAuth tokens. Created by `claude login`.
- `mcp-needs-auth-cache.json`, `stats-cache.json`, `.last-cleanup` — runtime caches.
- `sessions/`, `projects/`, `transcript-backups/`, `history.jsonl` — session
  artifacts and per-project memory.
- `file-history/`, `paste-cache/`, `shell-snapshots/`, `session-env/`, `ide/`,
  `todos/`, `tasks/`, `debug/`, `skill-observations/`, `backups/`,
  `context-mode/` — assorted runtime state and plugin caches.
- `cache/`, `plugins/cache/`, `plugins/data/`, `statsig/`, `telemetry/` — caches.
- `plugins/marketplaces/` — cloned marketplace contents (regenerable).
- `logs/`, `_quarantine/` — runtime/transient.
- `**/__pycache__/`, `**/*.pyc`, `**/.pytest_cache/`.

## Prerequisites for bootstrap

| Tool | Why | Where it shows up |
|---|---|---|
| Claude Code CLI | the harness | `claude` on PATH |
| Node.js (any LTS) | 10 JS hooks + statusLine + plugin runtime | settings.json hook commands |
| Python 3 (with `pyyaml`) | 5 v2 hooks + audit scripts | `python` on PATH |
| Git for Windows (or any `bash`) | 3 sh hooks | `bash` on PATH |
| `gh` CLI (optional) | repo management | `gh` on PATH |

On Windows: the `python3` executable is intercepted by the App Execution Alias;
hook scripts intentionally use `python` (not `python3`).

## Bootstrap from clean checkout

This is the procedure to recreate `~/.claude/` on a new machine.

```bash
# 1. Clone (the existing ~/.claude/ must not already be a git repo for this
#    path; rename or remove first if needed).
git clone https://github.com/Thalfman/claude-config.git ~/.claude

# 2. Install Claude Code CLI (https://docs.claude.com/claude-code) and
#    authenticate. This creates ~/.claude/.credentials.json (NOT committed).
claude login

# 3. Re-register the user-known marketplaces. settings.json's
#    extraKnownMarketplaces records them but the contents under
#    plugins/marketplaces/ are gitignored and must be re-fetched.
claude plugin marketplace add github://anthropics/skills           # document-skills
claude plugin marketplace add github://openai/codex-plugin-cc      # codex
claude plugin marketplace add github://mksglu/context-mode         # context-mode
claude plugin marketplace add github://thedotmack/claude-mem       # claude-mem
# claude-plugins-official is built into Claude Code; no add needed.
# claude-code-skills (alirezarezvani/claude-skills) is intentionally NOT
# re-added: its plugin is disabled and Phase 2 quarantines the marketplace.

# 4. Install the enabled plugins.
claude plugin install document-skills@anthropic-agent-skills
claude plugin install superpowers@claude-plugins-official
claude plugin install frontend-design@claude-plugins-official
claude plugin install context7@claude-plugins-official
claude plugin install skill-creator@claude-plugins-official
claude plugin install codex@openai-codex
claude plugin install context-mode@context-mode
claude plugin install claude-mem@thedotmack

# 5. Verify Python + PyYAML are usable (needed by _audits scripts).
python -c "import yaml; print(yaml.__version__)"

# 6. Start a session and confirm:
#    - SessionStart hooks run without error
#    - statusLine renders
#    - skills list includes the 8 domain skills and the 63 gsd-* skills
claude
```

## Where credentials live

**Not in this repo.** `.gitignore` excludes `.credentials.json`. Re-create on a
fresh machine via `claude login`. If you need application credentials (API
keys, etc.), use Claude Code's secret management — never inline.

## How to add things

### A new skill

1. `mkdir ~/.claude/skills/<skill-name>` and create `SKILL.md` with frontmatter:
   ```yaml
   ---
   name: <skill-name>
   description: >
     One paragraph. Use a `>` or `|` block scalar if the description contains
     `:`, `"`, or YAML-significant characters — see _audits/2026-05-11-skill-frontmatter.md.
   ---
   ```
2. Body is Markdown.
3. Commit. Skill becomes available on the next session start.

### A new agent

1. Create `~/.claude/agents/<name>.md` with frontmatter:
   ```yaml
   ---
   name: <name>
   description: <when to use this agent>
   tools: Read, Grep, Bash      # optional, narrows the toolset
   model: haiku                  # optional, for cheap agents
   ---
   ```
2. Body describes what the agent does. Keep tight — see `agents/explorer.md`
   (18 lines) for the exemplar.

### A new hook

1. Write the script under `~/.claude/hooks/`. Prefer Python (`_log_run.py`
   wrapper coming in Phase 3 will time it). Read stdin JSON, write to stdout,
   exit 0 (pass) or 2 (block).
2. Wire it in `settings.json` under the relevant lifecycle event
   (`SessionStart`, `PreToolUse`, `PostToolUse`, `PreCompact`).
3. Test with a fixture: `echo '{"tool_name":"Write"}' | python hooks/your_hook.py`.

## Bootstrap reproducibility test

After any change to this README or the bootstrap procedure:

```bash
# Use a throwaway location so the live ~/.claude/ is not touched.
git clone https://github.com/Thalfman/claude-config.git /tmp/claude-bootstrap-test
cd /tmp/claude-bootstrap-test
# Open a new Claude Code session in this dir and follow the README verbatim.
# Note any deviation between documented and actual steps; fix README, re-push.
# When clean, remove the test dir.
rm -rf /tmp/claude-bootstrap-test
```

On Windows the throwaway path is `C:\Users\thalf\tmp\claude-bootstrap-test\`.

## Plan tracking

Active migration: `plans/mission-you-are-replicated-canyon-v2.md`. See plan
§6 for phases and §7 for explicit pause points.
