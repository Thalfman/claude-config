#!/usr/bin/env bash
# Stage 1 (local): mirror personal skills from ~/.agents/skills into this repo's
# skills/ so the repo is the portable source of truth that cloud sessions clone.
#
# - Captures every skill EXCEPT ones whose SKILL.md frontmatter targets Codex.
# - Deletions propagate: a skill removed from the source is removed from the repo.
# - Skills are copied as real trees (not symlinks); content identical to the
#   tracked tree produces no git diff, so only real changes show up.
#
# Run manually, or automatically via .githooks/pre-commit (see scripts/README
# note in the PR). Override the source with AGENTS_SKILLS_DIR.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"
DEST="$REPO_ROOT/skills"

# Always-exclude list (names), in addition to Codex auto-detection.
EXCLUDE=()

is_codex() {
  # True if the SKILL.md frontmatter mentions codex (case-insensitive).
  local md="$1/SKILL.md"
  [ -f "$md" ] || return 1
  awk 'BEGIN{n=0} /^---[[:space:]]*$/{n++; if(n==2) exit; next} n==1{print}' "$md" \
    | grep -qi 'codex'
}

is_excluded() {
  local name="$1" e
  for e in "${EXCLUDE[@]:-}"; do [ "$e" = "$name" ] && return 0; done
  return 1
}

[ -d "$SRC" ] || { echo "vendor-skills: source $SRC not found" >&2; exit 1; }
mkdir -p "$DEST"

declare -A keep=()
for dir in "$SRC"/*/; do
  [ -d "$dir" ] || continue
  name="$(basename "$dir")"
  if [ ! -f "$dir/SKILL.md" ]; then echo "vendor-skills: skip $name (no SKILL.md)" >&2; continue; fi
  if is_excluded "$name"; then echo "vendor-skills: exclude $name (listed)"; continue; fi
  if is_codex "$dir"; then echo "vendor-skills: exclude $name (codex)"; continue; fi
  keep["$name"]=1
  rm -rf "$DEST/$name"
  cp -r "$dir" "$DEST/$name"
done

# Deletion propagation: drop repo skills no longer in the kept source set.
for dir in "$DEST"/*/; do
  [ -d "$dir" ] || continue
  name="$(basename "$dir")"
  if [ -z "${keep[$name]:-}" ]; then
    rm -rf "$DEST/$name"
    echo "vendor-skills: removed $name (gone from source)"
  fi
done

echo "vendor-skills: ${#keep[@]} skill(s) mirrored into $DEST"
