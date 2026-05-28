# Cloud session setup script

Paste-ready copy of the Claude Code "on the web" setup script. The canonical
executable is [`scripts/cloud-setup.sh`](./cloud-setup.sh); keep this block in
sync with it.

## What it does

Clones this public repo and reconstructs as much of the local desktop config as
a cloud session can actually read. A cloud session only ever reads the
checked-out project-level `.claude/` (never `~/.claude`), so everything personal
has to land there. It:

- **Mirrors** `skills/`, `commands/`, `agents/`, `hooks/`, `output-styles/` into
  the session's project-level `.claude/`. Additions and deletions both propagate;
  it only removes entries it previously added (tracked in a manifest), so a
  project's own `.claude` content is never clobbered.
- **Merges personal keys into `.claude/settings.json`** — `model`
  (`claude-opus-4-8[1m]`, i.e. Opus 4.8 with 1M context), `effortLevel`
  (`xhigh` = Extra High), output style, `enabledPlugins` +
  `extraKnownMarketplaces` (cloud auto-installs the plugins from their
  marketplaces at session start), and the hooks (paths rewritten to the cloud
  workspace, `python` → `python3`). The project's original settings are backed
  up once so re-runs stay idempotent and project hooks are preserved.
- **Installs the global `CLAUDE.md`** at the repo root only if none exists (cloud
  reads root `CLAUDE.md`, not `.claude/CLAUDE.md`); otherwise it leaves the
  project's file untouched and drops the prefs at `.claude/personal-prefs.md` for
  manual `@import`.

Deliberately omitted because a headless cloud VM does not honor them: the
`statusLine` command and any Windows-only paths/permissions.

## Model note

A model pinned in the cloud environment's own UI **overrides** `settings.json`.
Leave the environment model on **Default** (or pick Opus 4.8 there directly) so
the `settings.json` model written by this script actually applies.

## Setup

1. Open the desktop or web app → **environment settings → Setup script**.
2. Paste the block below. (Editing this field also busts the per-environment
   cache, so the next **new** session re-clones. Resumed sessions never re-run
   the setup script.)
3. Start a new cloud session.

Cloud refresh rides the setup-script cache (~7-day expiry, or re-paste/edit to
force it), not every session.

## Script

```bash
#!/usr/bin/env bash
# Stage 2 (cloud): setup script for Claude Code on the web.
#
# Paste this entire script into the desktop/web app:
#   claude.ai/code (or desktop app) > environment settings > Setup script
#
# It clones the public claude-config repo and reconstructs as much of the local
# desktop config as a cloud session can actually read. A cloud session only ever
# reads the checked-out project-level .claude/ (never ~/.claude), so everything
# personal has to land there. The script runs as root BEFORE Claude Code
# launches, so the files are present at discovery.
#
# What it brings over:
#   - skills / commands / agents / hooks / output-styles  -> mirrored into .claude/
#   - settings.json  -> personal keys merged in: model (Opus 4.8, 1M context),
#     effortLevel xhigh (Extra High), output style, plugins (auto-installed from
#     their marketplaces at session start), and the hooks (paths rewritten to the
#     cloud workspace, python -> python3).
#   - CLAUDE.md global prefs -> installed at repo root only if none exists
#     (cloud reads root CLAUDE.md, not .claude/CLAUDE.md), else left untouched.
#
# Deliberately NOT brought over (not honored / not meaningful in a headless
# cloud VM): the statusLine command (no status line in cloud) and Windows-only
# paths/permissions from the local machine.
#
# MODEL NOTE: a model pinned in the cloud environment's own UI overrides
# settings.json. Leave the environment model on Default (or pick Opus 4.8 there)
# so the settings.json model below actually applies.
#
# Mirror semantics for dirs: additions AND deletions propagate; only entries this
# script previously added are removed (tracked in a manifest), so a project's own
# .claude content is never clobbered. settings.json is merged, not overwritten:
# the project's original is backed up once so re-runs stay idempotent.
#
# Output is cached per environment (~7-day expiry, or re-runs when you edit this
# script or change allowed network hosts). To force a refresh sooner, edit this
# script.
set -uo pipefail

REPO_URL="https://github.com/Thalfman/claude-config.git"
SRC="/tmp/claude-config"

# Project root the session uses. CLAUDE_PROJECT_DIR is set in cloud sessions;
# fall back to the current directory.
ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
DEST="$ROOT/.claude"
MANIFEST="$DEST/.cloud-setup-manifest"
SETTINGS="$DEST/settings.json"
SETTINGS_ORIG="$DEST/.cloud-setup.settings.orig"

# Directories to mirror, all auto-discovered from project-level .claude/.
# (hooks are inert until declared in settings.json -- this script declares them.)
IMPORT=(skills commands agents hooks output-styles)

echo "cloud-setup: cloning $REPO_URL"
rm -rf "$SRC"
git clone --depth 1 "$REPO_URL" "$SRC"

mkdir -p "$DEST"

# Deletion pass: remove previously-imported entries now gone from the repo.
if [ -f "$MANIFEST" ]; then
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    if [ ! -e "$SRC/$rel" ] && [ -e "$DEST/$rel" ]; then
      rm -rf "$DEST/$rel"
      echo "cloud-setup: removed $rel (gone from repo)"
    fi
  done < "$MANIFEST"
fi

# Import pass: mirror current repo content and rebuild the manifest.
: > "$MANIFEST.tmp"
imported=0
for sub in "${IMPORT[@]}"; do
  [ -d "$SRC/$sub" ] || { echo "cloud-setup: skip $sub (absent in repo)" >&2; continue; }
  mkdir -p "$DEST/$sub"
  for entry in "$SRC/$sub"/*; do
    [ -e "$entry" ] || continue   # no matches -> literal glob, skip
    name="$(basename "$entry")"
    rm -rf "$DEST/$sub/$name"
    cp -r "$entry" "$DEST/$sub/$name"
    echo "$sub/$name" >> "$MANIFEST.tmp"
    imported=$((imported + 1))
  done
done
mv "$MANIFEST.tmp" "$MANIFEST"

if [ "$imported" -eq 0 ]; then
  echo "cloud-setup: ERROR nothing imported (checked $SRC)" >&2
  exit 1
fi
echo "cloud-setup: $imported item(s) mirrored into $DEST"

# ---- settings.json: merge personal config (model / effort / plugins / hooks) ----
# Capture the project's original settings once; re-runs always merge from it so
# the result is idempotent (hooks never accumulate duplicates across runs).
if [ ! -f "$SETTINGS_ORIG" ]; then
  if [ -f "$SETTINGS" ]; then cp "$SETTINGS" "$SETTINGS_ORIG"; else echo '{}' > "$SETTINGS_ORIG"; fi
fi

if command -v python3 >/dev/null 2>&1; then
  HOOKS_DIR="$DEST/hooks" python3 - "$SETTINGS_ORIG" "$SETTINGS" <<'PYEOF'
import json, os, sys

orig_path, out_path = sys.argv[1], sys.argv[2]
hooks_dir = os.environ["HOOKS_DIR"]

def cmd(script, timeout):
    return {"type": "command",
            "command": f'python3 "{hooks_dir}/{script}"',
            "timeout": timeout}

# Personal config that a cloud session can actually honor. statusLine and
# Windows-only permissions are intentionally omitted.
overlay = {
    "model": "claude-opus-4-8[1m]",   # Opus 4.8, 1M-context variant
    "effortLevel": "xhigh",            # Extra High
    "outputStyle": "proactive",
    "autoMemoryEnabled": True,
    "editorMode": "normal",
    "permissions": {"allow": ["Bash"], "defaultMode": "auto"},
    "enabledPlugins": {
        "document-skills@anthropic-agent-skills": True,
        "superpowers@claude-plugins-official": True,
        "context7@claude-plugins-official": True,
    },
    "extraKnownMarketplaces": {
        "claude-plugins-official": {"source": {"source": "github", "repo": "anthropics/claude-plugins-official"}},
        "anthropic-agent-skills": {"source": {"source": "github", "repo": "anthropics/skills"}},
        "openai-codex": {"source": {"source": "github", "repo": "openai/codex-plugin-cc"}},
        "karpathy-skills": {"source": {"source": "github", "repo": "forrestchang/andrej-karpathy-skills"}},
    },
    "hooks": {
        "SessionStart": [{"hooks": [cmd("session_context.py", 10)]}],
        "PostToolUse": [{"matcher": "Write|Edit|MultiEdit", "hooks": [cmd("format.py", 30)]}],
        "PreToolUse": [
            {"matcher": "Bash", "hooks": [cmd("block_dangerous.py", 5)]},
            {"matcher": "Write|Edit|MultiEdit", "hooks": [cmd("protect_main.py", 5)]},
        ],
        "PreCompact": [{"hooks": [cmd("backup_transcript.py", 10)]}],
        "SessionEnd": [{"hooks": [cmd("session_logger.py", 30)]}],
    },
}

try:
    with open(orig_path, encoding="utf-8") as fh:
        base = json.load(fh)
    if not isinstance(base, dict):
        base = {}
except (OSError, json.JSONDecodeError):
    base = {}

def merge(dst, src):
    """Deep-merge src into dst. Project hooks are preserved by appending ours
    per event; other dicts merge recursively; scalars/lists are overridden."""
    for key, val in src.items():
        if key == "hooks" and isinstance(dst.get(key), dict) and isinstance(val, dict):
            for event, groups in val.items():
                dst[key].setdefault(event, [])
                dst[key][event].extend(groups)
        elif isinstance(dst.get(key), dict) and isinstance(val, dict):
            merge(dst[key], val)
        else:
            dst[key] = val
    return dst

result = merge(base, overlay)
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(result, fh, indent=2)
    fh.write("\n")
print("cloud-setup: settings.json merged (model=claude-opus-4-8[1m], effort=xhigh)")
PYEOF
else
  echo "cloud-setup: WARNING python3 not found; settings.json left unmodified" >&2
fi

# ---- CLAUDE.md global prefs (cloud reads ROOT CLAUDE.md only) ----
if [ -f "$SRC/CLAUDE.md" ]; then
  cp "$SRC/CLAUDE.md" "$DEST/personal-prefs.md"
  if [ ! -f "$ROOT/CLAUDE.md" ]; then
    cp "$SRC/CLAUDE.md" "$ROOT/CLAUDE.md"
    echo "cloud-setup: installed personal CLAUDE.md at repo root (none existed)"
  else
    echo "cloud-setup: repo root CLAUDE.md exists; left it untouched."
    echo "cloud-setup: to load personal prefs too, add a line '@.claude/personal-prefs.md' to it."
  fi
fi

echo "cloud-setup: done"
```
