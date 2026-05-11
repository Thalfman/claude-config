#!/usr/bin/env python3
"""PostToolUse: format files Claude just wrote or edited."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

PRETTIER_EXTS = {".js", ".ts", ".jsx", ".tsx", ".css", ".scss",
                 ".html", ".json", ".yaml", ".yml", ".md"}
BLACK_EXTS = {".py"}


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    file_path = data.get("tool_input", {}).get("file_path")
    if not file_path or not Path(file_path).exists():
        return 0

    ext = Path(file_path).suffix.lower()
    try:
        if ext in PRETTIER_EXTS and shutil.which("npx"):
            subprocess.run(
                ["npx", "--no-install", "prettier", "--write", file_path],
                capture_output=True, timeout=20,
            )
        elif ext in BLACK_EXTS and shutil.which("black"):
            subprocess.run(
                ["black", "--quiet", file_path],
                capture_output=True, timeout=20,
            )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
