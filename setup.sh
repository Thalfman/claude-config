#!/usr/bin/env bash
#
# Install this repo as the global Claude Code config (~/.claude) inside a
# remote / Claude-Code-on-the-web environment.
#
# Unlike the README's "clone AS ~/.claude" bootstrap, a remote environment
# already ships a populated ~/.claude (built-in skills, hooks, settings). So
# this script *overlays* the repo onto the existing ~/.claude instead of
# replacing it: per-entry symlinks (no clobber, no nesting) plus a settings
# merge that preserves the environment's own hooks.
#
# Token: NEVER inline a PAT. Provide a fine-grained, read-only PAT scoped to
# this repo via the environment secret CLAUDE_CONFIG_TOKEN.
#
# Tunables (env vars):
#   CLAUDE_CONFIG_TOKEN   GitHub token used only to clone this private repo
#   CLAUDE_CONFIG_DIR     where to place the checkout (default: $HOME/claude-config)
#   INSTALL_PLUGINS       1 (default) to register marketplaces + install plugins; 0 to skip

set -euo pipefail

REPO_SLUG="Thalfman/claude-config"
DEST="${CLAUDE_CONFIG_DIR:-$HOME/claude-config}"
TARGET="$HOME/.claude"
INSTALL_PLUGINS="${INSTALL_PLUGINS:-1}"

# 1. Fetch the config repo. In a generic project's environment this repo is not
#    the checked-out project, so it must be cloned. Token comes from a secret.
if [ ! -d "$DEST/.git" ]; then
  : "${CLAUDE_CONFIG_TOKEN:?set CLAUDE_CONFIG_TOKEN as an environment secret (fine-grained, read-only, scoped to ${REPO_SLUG})}"
  git clone --depth 1 \
    "https://x-access-token:${CLAUDE_CONFIG_TOKEN}@github.com/${REPO_SLUG}.git" "$DEST"
else
  git -C "$DEST" fetch --depth 1 origin && git -C "$DEST" reset --hard '@{u}' || true
fi

mkdir -p "$TARGET"

# 2. Link file-based config one entry at a time. This is the key fix: linking
#    the *parent* dir nests under any pre-existing target dir (~/.claude/skills
#    already exists), burying every skill one level too deep so none load.
link_children() {
  local sub="$1" entry
  [ -d "$DEST/$sub" ] || return 0
  mkdir -p "$TARGET/$sub"
  # Drop a stale nested link left by the old (broken) parent-symlink approach.
  [ -L "$TARGET/$sub/$sub" ] && rm -f "$TARGET/$sub/$sub"
  for entry in "$DEST/$sub"/*; do
    [ -e "$entry" ] || continue
    ln -sfn "$entry" "$TARGET/$sub/$(basename "$entry")"
  done
}
for sub in skills agents commands; do link_children "$sub"; done

# Whole-dir references resolved by GSD agents/skills (@$HOME/.claude/get-shit-done/...).
for dir in hooks output-styles get-shit-done memory; do
  [ -d "$DEST/$dir" ] && ln -sfn "$DEST/$dir" "$TARGET/$dir"
done

ln -sfn "$DEST/CLAUDE.md" "$TARGET/CLAUDE.md"

# 3. Merge settings.json: repo values win on scalars, the environment's own
#    hooks are preserved, and permissions.allow is unioned rather than replaced.
[ -f "$TARGET/settings.json" ] || echo '{}' > "$TARGET/settings.json"
tmp="$(mktemp)"
jq -s '
  .[0] as $env | .[1] as $cfg
  | ($env * $cfg)
  | .permissions.allow = ((($env.permissions.allow // []) + ($cfg.permissions.allow // [])) | unique)
' "$TARGET/settings.json" "$DEST/settings.json" > "$tmp" && mv "$tmp" "$TARGET/settings.json"

# 4. Plugins are not just files: register the marketplaces and install the
#    enabled plugins, both driven from settings.json so they stay in sync.
#    Needs network + the `claude` CLI; failures are non-fatal.
if [ "$INSTALL_PLUGINS" = "1" ] && command -v claude >/dev/null 2>&1; then
  jq -r '.extraKnownMarketplaces // {} | to_entries[] | .value.source.repo' "$DEST/settings.json" \
    | while read -r repo; do
        [ -n "$repo" ] && { claude plugin marketplace add "github://$repo" || true; }
      done
  jq -r '.enabledPlugins // {} | to_entries[] | select(.value == true) | .key' "$DEST/settings.json" \
    | while read -r plugin; do
        [ -n "$plugin" ] && { claude plugin install "$plugin" || true; }
      done
fi

echo "claude-config installed into $TARGET"
