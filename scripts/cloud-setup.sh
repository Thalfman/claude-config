#!/usr/bin/env bash
# Cloud environment setup script for Claude Code on the web.
#
# Paste this entire script into the desktop/web app:
#   claude.ai/code (or desktop app) > environment settings > Setup script
#
# It clones the public claude-config repo and copies personal skills/commands
# into the cloud session's project-level .claude/, which is the only place a
# cloud session discovers them (it never reads ~/.claude). The setup script runs
# as root BEFORE Claude Code launches, so the files are present at discovery.
#
# Output is cached per environment (~7-day expiry, or re-runs when you edit this
# script or change allowed network hosts), so skills refresh on that cadence
# rather than every session. To force a refresh sooner, edit this script.
set -uo pipefail

REPO_URL="https://github.com/Thalfman/claude-config.git"
SRC="/tmp/claude-config"

# Project root the session uses. CLAUDE_PROJECT_DIR is set in cloud sessions;
# fall back to the current directory.
DEST="${CLAUDE_PROJECT_DIR:-$PWD}/.claude"

# Directories to import. skills and commands are auto-discovered from
# project-level .claude/. Add hooks/agents/output-styles if wanted (hooks also
# need declaring in .claude/settings.json to fire).
IMPORT=(skills commands)

echo "cloud-setup: cloning $REPO_URL"
rm -rf "$SRC"
git clone --depth 1 "$REPO_URL" "$SRC"

echo "cloud-setup: project dest = $DEST"
imported=0
for sub in "${IMPORT[@]}"; do
  if [ ! -d "$SRC/$sub" ]; then
    echo "cloud-setup: skip $sub (absent in repo)" >&2
    continue
  fi
  mkdir -p "$DEST/$sub"
  # Merge into any existing project-level dir; same-named entries are overwritten.
  if cp -r "$SRC/$sub/." "$DEST/$sub/"; then
    count=$(find "$DEST/$sub" -mindepth 1 -maxdepth 1 | wc -l)
    echo "cloud-setup: imported $sub ($count entries)"
    imported=$((imported + 1))
  else
    echo "cloud-setup: WARN copy failed for $sub" >&2
  fi
done

if [ "$imported" -eq 0 ]; then
  echo "cloud-setup: ERROR nothing imported (checked $SRC)" >&2
  exit 1
fi

echo "cloud-setup: done -- $imported group(s) into $DEST"
