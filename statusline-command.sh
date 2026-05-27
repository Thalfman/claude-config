#!/bin/sh
# Claude Code statusLine wrapper.
# Delegates to the Node implementation (dependency-free, no jq required).
# settings.local.json invokes: sh "C:/Users/thalf/.claude/statusline-command.sh"
# (machine-specific path lives in gitignored local settings; this script is portable)
exec node "$(dirname "$0")/statusline-command.js"
