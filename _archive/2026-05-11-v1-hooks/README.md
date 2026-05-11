# Archive: v1 hooks + agents + CLAUDE.md (snapshot 2026-05-11 10:30:09)

## What this is

The pre-migration snapshot of `~/.claude/` taken just before the v1 (PowerShell hooks) → v2 (Python hooks) migration on 2026-05-11. Originally lived at `~/.claude/_pre_v2_backup/2026-05-11-103009/`. Promoted to `_archive/` per plan §6 Phase 1 step 3 (R10) so its retention is intentional rather than accidental.

## Contents

| Path | Origin | Why kept |
|---|---|---|
| `CLAUDE.md` | Pre-2026-05-11 global preferences | Reference for any preference that didn't survive the migration. |
| `agents/` | Pre-migration agent definitions | Some may differ from current; check before assuming current is "the same". |
| `hooks/` | Pre-migration PowerShell hooks | The PowerShell variants that were superseded by the v2 Python hooks under `~/.claude/hooks/*.py`. |
| `settings.json.bak` | Pre-migration `settings.json` | The exact wiring before the v2 hook migration — useful for forensics if a v2 hook behaves differently. |

## When to consult this

- A v2 hook regresses behavior that worked under v1 → diff against the PowerShell variant in `hooks/`.
- A pre-existing preference seems to have vanished from `CLAUDE.md` → diff against this copy.
- Settings keys behave differently than expected → compare to `settings.json.bak`.

## When to delete

Not soon. This is a 37 KB on-disk cost. Keep at least until v2 hooks have run cleanly for 90+ days (suggested review: 2026-08-11).

## Recovery

Files are plain text. Either `cat` them in place or copy back into `~/.claude/` directly if needed. There is no automated recovery script — by design, this is a passive archive, not a feature.
