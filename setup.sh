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
  # Force the checkout to the latest default branch. Non-fatal, but warn loudly:
  # silently keeping a stale checkout is what makes new skills/plugins "not show up".
  git -C "$DEST" fetch --depth 1 origin main \
    && git -C "$DEST" reset --hard origin/main \
    || echo "WARN: could not update $DEST; using existing (possibly stale) checkout" >&2
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

# Whole-dir config references.
for dir in hooks output-styles memory; do
  [ -d "$DEST/$dir" ] && ln -sfn "$DEST/$dir" "$TARGET/$dir"
done

# GSD is no longer part of this config. Cloud filesystems persist, so a prior
# install (or base image) can leave GSD behind every session. Purge it outright,
# scoped strictly to GSD-named paths so env built-ins are untouched.
rm -rf "$TARGET/get-shit-done" "$TARGET/gsd-file-manifest.json"
for d in skills agents hooks; do
  for stale in "$TARGET/$d"/gsd-*; do
    [ -e "$stale" ] && rm -rf "$stale"
  done
done

ln -sfn "$DEST/CLAUDE.md" "$TARGET/CLAUDE.md"
ln -sfn "$DEST/statusline.js" "$TARGET/statusline.js"

# 3. Merge settings.json: repo values win on scalars, the environment's own
#    hooks are preserved, and permissions.allow is unioned rather than replaced.
[ -f "$TARGET/settings.json" ] || echo '{}' > "$TARGET/settings.json"
tmp="$(mktemp)"
jq -s '
  .[0] as $env | .[1] as $cfg
  | ($env * $cfg)
  | .permissions.allow = ((($env.permissions.allow // []) + ($cfg.permissions.allow // [])) | unique)
' "$TARGET/settings.json" "$DEST/settings.json" > "$tmp" && mv "$tmp" "$TARGET/settings.json"

# settings.json captures statusLine.command from the author's Windows machine
# (an absolute C:\ path). Repoint it at the linked statusline.js in this
# environment so the HUD renders here too.
if [ -f "$TARGET/statusline.js" ]; then
  tmp="$(mktemp)"
  jq --arg cmd "node \"$TARGET/statusline.js\"" \
     'if .statusLine then .statusLine.command = $cmd else . end' \
     "$TARGET/settings.json" > "$tmp" && mv "$tmp" "$TARGET/settings.json"
fi

# 4. Plugins are not just files: register every marketplace and install every
#    plugin captured from the Windows machine. Marketplace sources are unioned
#    from settings.json (extraKnownMarketplaces) AND the captured snapshot
#    (plugins/known_marketplaces.json). The snapshot is what makes this robust:
#    it carries the repo for built-in marketplaces like claude-plugins-official,
#    so we register them explicitly instead of assuming the environment already
#    has them (it doesn't, in a fresh web container -- which silently dropped the
#    4 plugins sourced from claude-plugins-official). The plugin list is likewise
#    the union of settings.json's enabledPlugins and the snapshot's installed set.
#    Needs network + the `claude` CLI; failures are non-fatal.
if [ "$INSTALL_PLUGINS" = "1" ] && command -v claude >/dev/null 2>&1; then
  snap_mkts="$DEST/plugins/known_marketplaces.json"
  snap_plugs="$DEST/plugins/installed_plugins.json"

  # Marketplaces come in two source shapes: GitHub (source.repo = "owner/name") and
  # plain git (source.url = "https://.../x.git"). Earlier this only read .repo, which
  # silently dropped git-sourced marketplaces like understand-anything, so their
  # plugins never installed. Prefer .repo, fall back to .url, then add by shape.
  { jq -r '.extraKnownMarketplaces // {} | to_entries[] | .value.source.repo // .value.source.url // empty' "$DEST/settings.json"
    if [ -f "$snap_mkts" ]; then jq -r 'to_entries[] | .value.source.repo // .value.source.url // empty' "$snap_mkts"; fi
  } | sort -u | while read -r src; do
        [ -n "$src" ] || continue
        case "$src" in
          *://*|*.git) claude plugin marketplace add "$src" || true ;;        # git/https URL
          */*)         claude plugin marketplace add "github://$src" || true ;; # owner/name
        esac
      done

  { jq -r '.enabledPlugins // {} | to_entries[] | select(.value == true) | .key' "$DEST/settings.json"
    if [ -f "$snap_plugs" ]; then jq -r '.plugins // {} | keys[]' "$snap_plugs"; fi
  } | sort -u | while read -r plugin; do
        [ -n "$plugin" ] && { claude plugin install "$plugin" || true; }
      done
fi

echo "claude-config installed into $TARGET"
