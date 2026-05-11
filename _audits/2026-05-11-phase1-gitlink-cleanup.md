# Gitlink cleanup — 2026-05-11 (Phase 1 / scoped from Phase 2 step 4)

## Why this happened in Phase 1, not Phase 2

Phase 0's baseline commit (`099a8c4`) tracked three skills as **gitlinks** (mode 160000) because each contained an embedded `.git/` directory:

| Skill | Inner branch | Inner remote | Working tree at Phase 0 |
|---|---|---|---|
| `skills/dxf-to-kmz` | `master` | none | clean |
| `skills/kmz-level-up` | `main` | none | **15 modified files, 2 untracked (WIP from 2026-04-28)** |
| `skills/plan-sheet-endpoints` | `master` | none | clean |

Plan §6 Phase 2 step 4 was designated to handle this. But Phase 1 step 7 (bootstrap reproducibility test) requires the file contents to exist in the outer repo — gitlinks would have made the test fail before Phase 2. Lifted the cleanup forward.

## What was done

1. Moved each inner `.git/` directory to `_quarantine/2026-05-11/inner-git/<skill>/.git/` (gitignored, local-only, fully reversible). Preserves the inner repo's full commit history and any reflog/stash.
2. `git rm --cached` removed the gitlink index entries in the outer repo.
3. `git add -A` re-staged each skill's working tree (including `kmz-level-up`'s 15 modified files + 2 untracked feature files) as ordinary tracked content.
4. New outer commit captured the converted state.

## Inner-repo histories — preserved

The quarantined `.git/` directories under `_quarantine/2026-05-11/inner-git/<skill>/` retain:

- All inner commits (e.g. `kmz-level-up` had `5f52d14`, `71309d3`, `312bb0e`, ...).
- The inner reflog.
- Any stashes.

**Recovery:** to restore an inner repo as it was, `mv ~/.claude/_quarantine/2026-05-11/inner-git/<skill>/.git ~/.claude/skills/<skill>/.git`. Working tree files were not moved, so they'll line up with the WIP state recorded in the inner index.

## Impact on `kmz-level-up` WIP

The 15 modified files (`SKILL.md`, 6 transformer scripts, 5 pipeline scripts, 4 tests; +468/-152 LOC) and 2 untracked files (`scripts/transformers/polygon_merger.py`, `tests/test_polygon_handling.py`) are now part of the outer config repo's tracked tree as their on-disk state. If you intended that WIP to remain "in progress" and not be snapshotted, recover via the procedure above and decide separately.

## Open follow-ups (out of scope here)

- Phase 2 step 4 originally also called out `skills/cd-ground-overlays/cd-ground-overlays.zip` (a stale zip of the skill inside its own folder) and `*/__pycache__/` cleanup. Those still need handling in Phase 2.
- The `_quarantine/` tree is local-only by `.gitignore`. If the machine is lost, the inner-repo histories are lost. They have no remotes — they were local-only from the start — so this is a pre-existing condition, not a regression.
