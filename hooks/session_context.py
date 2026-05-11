#!/usr/bin/env python3
"""SessionStart: print branch, dirty count, last commit to context."""
import subprocess
import sys


def run(cmd: list[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def main() -> int:
    branch = run(["git", "branch", "--show-current"])
    if not branch:
        return 0

    dirty = run(["git", "status", "--porcelain"])
    dirty_count = len([ln for ln in dirty.splitlines() if ln.strip()])
    last_commit = run(["git", "log", "-1", "--oneline"])
    ahead_behind = run(["git", "rev-list", "--left-right", "--count", "@{u}...HEAD"])

    print("--- Session Context ---")
    print(f"Branch: {branch}")
    print(f"Dirty files: {dirty_count}")
    if last_commit:
        print(f"Last commit: {last_commit}")
    if ahead_behind and "\t" in ahead_behind:
        behind, ahead = ahead_behind.split("\t")
        if behind != "0" or ahead != "0":
            print(f"Tracking: {ahead} ahead, {behind} behind upstream")
    print("-----------------------")
    return 0


if __name__ == "__main__":
    sys.exit(main())
