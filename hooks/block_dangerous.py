#!/usr/bin/env python3
"""PreToolUse: block clearly destructive shell commands."""
import json
import re
import sys

PATTERNS = [
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/(?:\s|$|\*)",
     "rm -rf on root filesystem"),
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+~(?:\s|$|/)",
     "rm -rf on home directory"),
    (r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", "destructive SQL"),
    (r"\bTRUNCATE\s+TABLE\b", "TRUNCATE TABLE"),
    (r"\bDELETE\s+FROM\s+\w+\s*;", "DELETE without WHERE"),
    (r"\bgit\s+push\s+(?:[^|;&]*\s)?--force(?!-with-lease)\b",
     "git push --force"),
    (r"\bgit\s+push\s+(?:[^|;&]*\s)?-f\b", "git push -f"),
    (r"\bshutdown\b", "shutdown"),
    (r"\bmkfs\.", "filesystem format"),
    (r":\(\)\s*\{.*:\|:&\s*\};:", "fork bomb"),
    (r"\bdd\s+.*of=/dev/(sd|hd|nvme)", "raw disk write"),
    (r"\bchmod\s+-R\s+777\s+/", "chmod 777 on root"),
    (r"\b(curl|wget)\s+[^|]*\|\s*(sudo\s+)?(bash|sh|zsh)\b",
     "curl pipe shell"),
    (r"\bsudo\b", "sudo invocation"),
    (r"\bnpm\s+(install|i)\s+(-g|--global)\b", "global npm install"),
    (r"\bpip\s+install\s+.*--break-system-packages\b", "pip break-system-packages"),
    (r"\bgit\s+reset\s+--hard\s+(origin/|upstream/)", "destructive remote reset"),
    (r"\bgit\s+clean\s+-[a-zA-Z]*f[a-zA-Z]*d", "git clean -fd"),
    (r"\bchmod\s+-R\s+777\b", "chmod 777 recursive"),
    (r"\beval\s+\$\(", "eval of command substitution"),
    (r"\bbase64\s+-d.*\|\s*(bash|sh|zsh|python)\b", "base64 decode piped to shell"),
]


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    command = data.get("tool_input", {}).get("command", "")
    for pattern, label in PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            print(f"BLOCKED: {label} detected in command", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
