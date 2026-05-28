# Architecture of `~/.claude/`

How this repo becomes a live Claude Code config — the import model, what
`settings.json` actually contains, and what loads at session start.

## Import model

This repo is the source of truth for a personal Claude Code config. It reaches a
running environment two ways:

1. **Cloud overlay (primary).** A cloud environment's own setup step clones this
   repo and overlays it onto the env's existing `~/.claude/` (built-in skills,
   hooks, settings remain in place; this repo's entries sit alongside them).
   The overlay script lives in the cloud env, not in this repo. Cloud
   filesystems persist between sessions, so the overlay is expected to be
   idempotent.

2. **Fresh-machine clone.** Clone the repo directly as `~/.claude/` and re-install
   plugins. See `README.md`.

## settings.json

The committed `settings.json` carries:

- `statusLine` → `node "<path>/statusline.js"`. The committed path is the
  author's Windows machine; the cloud env's overlay step is expected to
  rewrite it to point at the linked `statusline.js`.
- `enabledPlugins` — 9 plugins (see table below).
- `extraKnownMarketplaces` — the non-built-in marketplaces, by source. Two source
  shapes appear: GitHub (`source.repo`) and plain git (`source.url`).
- `permissions` (`allow: ["Bash"]`, `defaultMode: "auto"`), `outputStyle:
  "proactive"`, `effortLevel: "xhigh"`, plus assorted toggles
  (`autoMemoryEnabled`, `remoteControlAtStartup`, `inputNeededNotifEnabled`,
  `agentPushNotifEnabled`, `skipAutoPermissionPrompt`).
- **No `hooks` key.** The repo wires no hooks; the scripts under `hooks/` are
  inert until a `hooks.<event>` entry references them.

## Hooks

Six Python scripts ship under `hooks/`, none currently wired in `settings.json`:

| Script | Intended event | Purpose |
|---|---|---|
| `session_context.py` | SessionStart | print git branch + dirty count |
| `session_logger.py` | SessionStart | append a cross-project session-log entry |
| `protect_main.py` | PreToolUse [Write\|Edit] | refuse edits on protected branches |
| `block_dangerous.py` | PreToolUse [Bash] | regex denylist for destructive shell |
| `format.py` | PostToolUse [Write\|Edit] | run prettier/black on the touched file |
| `backup_transcript.py` | PreCompact | snapshot the transcript before compaction |

To activate any of them, add a `hooks` block to `settings.json` (read stdin JSON;
exit `0` to pass, `2` to block).

## statusLine

`statusline.js` renders the HUD: git branch, context-window usage, and model
effort level. Wired via `settings.json` → `statusLine.command`. The committed
command holds a Windows absolute path; the cloud env's overlay rewrites it for
Linux.

## Plugins

| Plugin | Marketplace | Purpose |
|---|---|---|
| `superpowers` | claude-plugins-official (built-in) | brainstorm/plan/execute, TDD, debugging, finishing-a-branch |
| `context7` | claude-plugins-official (built-in) | live library docs via MCP |
| `skill-creator` | claude-plugins-official (built-in) | author/evaluate skills |
| `document-skills` | anthropic-agent-skills | office docs, PDF, slides, web artifacts |
| `codex` | openai-codex | Codex rescue/setup, GPT-5.4 prompting helpers |
| `andrej-karpathy-skills` | karpathy-skills | Karpathy coding guidelines |
| `understand-anything` | understand-anything (git URL) | codebase knowledge graph + dashboard |
| `bmad-pro-skills` | bmad-method | BMAD standalone utilities (spec, reviews, brainstorming) |
| `bmad-method-lifecycle` | bmad-method | BMAD SDLC agent suite (PM, architect, dev, etc.) |

Marketplace contents live under the gitignored `plugins/marketplaces/`; only the
registry pointers (`plugins/known_marketplaces.json`,
`plugins/installed_plugins.json`) and `settings.json` are tracked, so a fresh
environment re-fetches each plugin.

## Session-start load order (typical)

1. Anthropic system prompt + tool list.
2. `CLAUDE.md` (global preferences).
3. Auto-memory `MEMORY.md` index.
4. Skills list — descriptions of all user + active-plugin skills (the largest
   single context block; 42 user skills here plus each enabled plugin's).
5. Agents list — frontmatter of the 6 agents.
6. Active-plugin SKILL.md descriptions + MCP server instructions.
7. Any wired hooks fire. (None from this repo by default; the cloud env's own
   hooks still run.)

## Failure modes worth knowing

1. **Stale cloud filesystem.** Environments persist; a session keeps prior files.
   The overlay can hard-reset its own checkout, but base-image cruft outside
   those paths survives until the environment is recreated.
2. **`format.py` silent skip.** If prettier/black is absent from PATH it does
   nothing — you may believe formatting is happening when it is not. (Moot until
   the hook is wired.)
3. **statusLine path.** The committed command is Windows-absolute; without the
   overlay's rewrite it points at a nonexistent file on Linux.
4. **Plugin install needs network + `claude` CLI.** Marketplace/plugin steps in
   the overlay are skipped without the CLI; new plugins then will not appear.

## Pointers

- `README.md` — purpose, cloud-import usage, fresh-machine bootstrap.
