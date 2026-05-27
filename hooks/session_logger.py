#!/usr/bin/env python3
"""SessionEnd: append one structured line per session to a global, greppable index.

Layer 1 of the native passive-memory setup. Pure transcript parsing, no model
call, finishes in well under a second so it completes before the hook is killed.
Layer 2 (distilled, auto-loading per-project notes) is handled by Claude Code's
built-in auto-memory, not this hook.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

LOG_PATH = Path.home() / ".claude" / "memory" / "session-log.jsonl"
MAX_FILES = 50
MAX_COMMITS = 20
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
COMMIT_RE = re.compile(r"""git\s+commit\b[^\n]*?-m\s+(['"])(.+?)\1""", re.DOTALL)


def already_logged(session_id: str) -> bool:
    if not session_id or not LOG_PATH.exists():
        return False
    needle = f'"session_id": "{session_id}"'
    try:
        with LOG_PATH.open(encoding="utf-8") as fh:
            return any(needle in line for line in fh)
    except OSError:
        return False


def parse_transcript(path: Path, cwd: str) -> dict:
    prompts = 0
    tools = 0
    files: list[str] = []
    seen_files: set[str] = set()
    commits: list[str] = []
    branch = ""
    last_ts = ""

    try:
        fh = path.open(encoding="utf-8")
    except OSError:
        return {"prompts": 0, "tools": 0, "files": [], "commits": [], "branch": "", "ts": ""}

    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("gitBranch"):
                branch = event["gitBranch"]
            if event.get("timestamp"):
                last_ts = event["timestamp"]

            msg = event.get("message") or {}
            role = msg.get("role")
            content = msg.get("content")

            if event.get("type") == "user" and role == "user":
                if isinstance(content, str):
                    prompts += 1
                elif isinstance(content, list):
                    kinds = {b.get("type") for b in content if isinstance(b, dict)}
                    if "tool_result" not in kinds:
                        prompts += 1

            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    tools += 1
                    name = block.get("name")
                    inp = block.get("input") or {}
                    if name in WRITE_TOOLS:
                        fp = inp.get("file_path") or inp.get("notebook_path")
                        if fp:
                            rel = _relativize(fp, cwd)
                            if rel not in seen_files and len(files) < MAX_FILES:
                                seen_files.add(rel)
                                files.append(rel)
                    elif name == "Bash":
                        for _, message in COMMIT_RE.findall(inp.get("command", "")):
                            msg_text = message.strip()
                            if msg_text and msg_text not in commits and len(commits) < MAX_COMMITS:
                                commits.append(msg_text)

    return {"prompts": prompts, "tools": tools, "files": files,
            "commits": commits, "branch": branch, "ts": last_ts}


def _relativize(path: str, cwd: str) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(cwd).resolve())).replace("\\", "/")
    except (ValueError, OSError):
        return path.replace("\\", "/")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    session_id = data.get("session_id", "")
    if already_logged(session_id):
        return 0

    transcript_path = data.get("transcript_path", "")
    cwd = data.get("cwd", "")
    parsed = {"prompts": 0, "tools": 0, "files": [], "commits": [], "branch": "", "ts": ""}
    if transcript_path and Path(transcript_path).exists():
        parsed = parse_transcript(Path(transcript_path), cwd)

    project = ""
    if transcript_path:
        project = Path(transcript_path).parent.name

    record = {
        "ts": parsed["ts"] or datetime.now().isoformat(timespec="seconds"),
        "session_id": session_id,
        "project": project,
        "cwd": cwd,
        "branch": parsed["branch"],
        "reason": data.get("reason", ""),
        "prompts": parsed["prompts"],
        "tools": parsed["tools"],
        "files": parsed["files"],
        "commits": parsed["commits"],
    }

    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"session_logger: write failed: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
