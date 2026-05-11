#!/usr/bin/env python3
"""PreCompact: copy transcript to backup folder, keep last 20."""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path.home() / ".claude" / "transcript-backups"
KEEP = 20


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    src = data.get("transcript_path")
    if not src or not Path(src).exists():
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    dst = BACKUP_DIR / f"transcript-{stamp}.jsonl"

    try:
        shutil.copy2(src, dst)
    except OSError as e:
        print(f"backup failed: {e}", file=sys.stderr)
        return 0

    backups = sorted(
        BACKUP_DIR.glob("transcript-*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in backups[KEEP:]:
        try:
            old.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
