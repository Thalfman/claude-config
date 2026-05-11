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
