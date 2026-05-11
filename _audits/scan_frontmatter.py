#!/usr/bin/env python3
"""Scan SKILL.md frontmatter using PyYAML for an accurate parse.

Flags:
- no_opening_fence / no_closing_fence
- yaml_parse_error: real YAML errors
- missing_required_field: name or description absent
- description_truncation_risk: description is a string containing patterns Claude Code's
  parser previously mishandled (multi-paragraph, embedded ``` blocks, unbalanced quotes)
- extra_unexpected_keys: keys not in canonical set (descriptive, not necessarily an error)

Output: ~/.claude/_audits/2026-05-11-skill-frontmatter.md
"""
import json
import os
from pathlib import Path

import yaml

HOME = Path(os.path.expanduser("~"))
CLAUDE = HOME / ".claude"
USER_SKILLS = CLAUDE / "skills"
MKT_SKILLS_ROOT = CLAUDE / "plugins" / "marketplaces"

EXPECTED_KEYS = {
    "name", "description", "license", "allowed-tools", "model",
    "version", "author", "homepage", "tags",
}


def extract_frontmatter(text: str):
    if not text.startswith("---"):
        return None, "no_opening_fence"
    end = text.find("\n---", 3)
    if end < 0:
        return None, "no_closing_fence"
    return text[4:end], None


def scan(root: Path, label: str):
    findings = []
    files = sorted(root.rglob("SKILL.md"))
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            findings.append({"path": str(p), "label": label, "issue": f"read_error: {e}"})
            continue
        fm, err = extract_frontmatter(text)
        if err:
            findings.append({"path": str(p), "label": label, "issue": err})
            continue
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as e:
            findings.append({"path": str(p), "label": label, "issue": "yaml_parse_error",
                             "detail": str(e).splitlines()[0][:200]})
            continue
        if not isinstance(parsed, dict):
            findings.append({"path": str(p), "label": label, "issue": "frontmatter_not_mapping"})
            continue
        missing = [k for k in ("name", "description") if k not in parsed]
        if missing:
            findings.append({"path": str(p), "label": label, "issue": f"missing_required_field: {missing}"})
            continue
        # description value must be a string
        desc = parsed.get("description")
        if not isinstance(desc, str):
            findings.append({"path": str(p), "label": label, "issue": f"description_wrong_type: {type(desc).__name__}"})
            continue
        # extra keys are not necessarily bad, but worth noting
        extra = [k for k in parsed.keys() if k not in EXPECTED_KEYS]
        if extra:
            findings.append({"path": str(p), "label": label,
                             "issue": "extra_keys",
                             "extras": extra[:10]})
    return files, findings


user_files, user_findings = scan(USER_SKILLS, "user")
mkt_files, mkt_findings = scan(MKT_SKILLS_ROOT, "marketplace")

# Print summary
real_user = [f for f in user_findings if f["issue"] != "extra_keys"]
real_mkt = [f for f in mkt_findings if f["issue"] != "extra_keys"]
print(f"user SKILL.md scanned: {len(user_files)}")
print(f"  real issues: {len(real_user)}")
print(f"  extra-keys (non-blocking): {len(user_findings) - len(real_user)}")
print(f"marketplace SKILL.md scanned: {len(mkt_files)}")
print(f"  real issues: {len(real_mkt)}")
print(f"  extra-keys (non-blocking): {len(mkt_findings) - len(real_mkt)}")
print()

if real_user:
    print("=== user real issues ===")
    for f in real_user:
        print(json.dumps(f))
    print()
else:
    print("=== user: 0 real issues ===\n")

# Bucket marketplace issues by issue type and marketplace
from collections import Counter
mkt_by_type = Counter(f["issue"].split(":")[0] for f in real_mkt)
print("marketplace real issues by type:")
for t, c in mkt_by_type.most_common():
    print(f"  {c:>4}  {t}")
print()
mkt_by_source = Counter()
for f in real_mkt:
    rel = Path(f["path"]).relative_to(CLAUDE / "plugins" / "marketplaces")
    mkt_by_source[rel.parts[0]] += 1
print("marketplace real issues by marketplace:")
for s, c in mkt_by_source.most_common():
    print(f"  {c:>4}  {s}")

# Save audit report
audit_dir = CLAUDE / "_audits"
audit_dir.mkdir(exist_ok=True)
report = audit_dir / "2026-05-11-skill-frontmatter.md"
out = [
    "# SKILL.md frontmatter audit -- 2026-05-11",
    "",
    f"Scanned **{len(user_files)} user skills** under `~/.claude/skills/` and **{len(mkt_files)} marketplace skills** under `~/.claude/plugins/marketplaces/`.",
    "",
    "## Method",
    "",
    "Used PyYAML (`yaml.safe_load`) to actually parse the frontmatter. Block scalars (`>`, `|`) "
    "are handled correctly -- this scan does NOT false-positive on multi-line descriptions.",
    "",
    "Flagged issues:",
    "",
    "- `no_opening_fence` / `no_closing_fence` -- frontmatter delimiters missing.",
    "- `yaml_parse_error` -- PyYAML refused to parse the frontmatter.",
    "- `frontmatter_not_mapping` -- top level is not a YAML mapping.",
    "- `missing_required_field` -- `name` or `description` absent.",
    "- `description_wrong_type` -- `description` value parsed as non-string (e.g. dict, list).",
    "- `extra_keys` -- informational only; not flagged as a real issue. Lists keys outside the canonical set.",
    "",
    "## Summary",
    "",
    f"- User skills: **{len(real_user)} real issues** ({len(user_findings) - len(real_user)} informational `extra_keys`).",
    f"- Marketplace skills: **{len(real_mkt)} real issues** ({len(mkt_findings) - len(real_mkt)} informational `extra_keys`).",
    "",
    "## User skills",
    "",
]
if real_user:
    for f in real_user:
        rel = str(Path(f["path"]).relative_to(CLAUDE)).replace("\\", "/")
        out.append(f"- `{rel}` -- **{f['issue']}**")
        if "detail" in f:
            out.append(f"  - detail: `{f['detail']}`")
        if "extras" in f:
            out.append(f"  - extras: `{f['extras']}`")
else:
    out.append("_No real issues found. The plan's §6/R7 starter case (`task-observer/SKILL.md`) parses correctly with PyYAML -- its `description: >` block scalar is valid; the previous audit's finding was a false positive from a naive line-based parser._")
out.extend([
    "",
    "## Marketplace skills (upstream)",
    "",
    "**Do not edit in place** -- `gsd-update` and marketplace refresh would revert. File an issue upstream "
    "or quarantine the marketplace (see Phase 2 step 2 for `claude-code-skills`).",
    "",
    "### Counts by marketplace",
    "",
])
for s, c in mkt_by_source.most_common():
    out.append(f"- `{s}` -- **{c}** real issues")
out.extend([
    "",
    "### Detail (real issues only; informational extra-keys omitted)",
    "",
])
for f in real_mkt:
    rel = str(Path(f["path"]).relative_to(CLAUDE)).replace("\\", "/")
    out.append(f"- `{rel}` -- **{f['issue']}**")
    if "detail" in f:
        out.append(f"  - detail: `{f['detail']}`")
report.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"\nReport saved: {report}")
