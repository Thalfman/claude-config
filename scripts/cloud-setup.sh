#!/usr/bin/env bash
# Stage 2 (cloud): setup script for Claude Code on the web.
#
# Paste this entire script into the desktop/web app:
#   claude.ai/code (or desktop app) > environment settings > Setup script
#
# It clones the public claude-config repo and MIRRORS personal skills/commands/
# agents into the cloud session's project-level .claude/, the only place a cloud
# session discovers them (it never reads ~/.claude). The setup script runs as
# root BEFORE Claude Code launches, so the files are present at discovery.
#
# Mirror semantics: additions AND deletions propagate. Items removed from the
# repo are removed here too. To avoid clobbering skills a project ships itself,
# it only removes entries IT previously added (tracked in a manifest).
#
# Output is cached per environment (~7-day expiry, or re-runs when you edit this
# script or change allowed network hosts), so the mirror refreshes on that
# cadence rather than every session. To force a refresh sooner, edit this script.
set -uo pipefail

REPO_URL="https://github.com/Thalfman/claude-config.git"
SRC="/tmp/claude-config"

# Project root the session uses. CLAUDE_PROJECT_DIR is set in cloud sessions;
# fall back to the current directory.
DEST="${CLAUDE_PROJECT_DIR:-$PWD}/.claude"
MANIFEST="$DEST/.cloud-setup-manifest"

# Directories to mirror. skills/commands/agents are auto-discovered from
# project-level .claude/. (Hooks are intentionally excluded: they only fire when
# declared in .claude/settings.json, so copying files alone does nothing.)
IMPORT=(skills commands agents)

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

echo "cloud-setup: done -- $imported item(s) mirrored into $DEST"
