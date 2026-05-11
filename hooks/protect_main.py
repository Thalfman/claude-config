#!/usr/bin/env python3
"""PreToolUse: refuse edits when on a protected branch."""
import json
import subprocess
import sys

PROTECTED = {"main", "master", "release", "prod", "production"}


def main() -> int:
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=3,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0

    if result.returncode != 0:
        return 0

    branch = result.stdout.strip().lower()
    if branch in PROTECTED:
        print(
            f"BLOCKED: refusing to edit files on protected branch '{branch}'. "
            f"Create a feature branch first: git switch -c feat/<name>",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
