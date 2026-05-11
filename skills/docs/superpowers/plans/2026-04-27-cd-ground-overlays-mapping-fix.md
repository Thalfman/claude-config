# CD Ground Overlays — Mapping Accuracy Fix

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `cd-ground-overlays/scripts/build_overlays.py` so each `<GroundOverlay>`'s `<LatLonBox>` lands at the correct geographic location instead of being translated away from the route. Today bounding boxes are correctly *sized* (~680 ft EW × ~440 ft NS at 1″=40′) but get offset because the embedded-stamp anchor binds at the text bounding box centroid, which on real CDs sits in an address strip or notes block far from where the (lat, lon) actually falls on the rendered map.

**Architecture:** Replace the single text-position anchor with a tier-based ladder, mirroring the user's "tier-based fallbacks, convention-with-override" preference. New precedence:

1. **Manual JSON anchor** (highest, unchanged)
2. **Two-corner geographic anchor** (NEW — JSON specifies two pixel→lat/lon pairs and the script fits a 2-D affine transform)
3. **Embedded stamp bound to nearest route endpoint** (NEW — text supplies (lat, lon), the closest red-polyline endpoint supplies (x_pdf, y_pdf))
4. **Embedded stamp at text bbox centroid** (LEGACY fallback when no route polyline on page; opt-in via `--legacy-text-anchor` for backwards compatibility)
5. Forward chain (unchanged)
6. Backward chain (unchanged)
7. Cover-page lat/lon (unchanged)

Also fix four contributing bugs found during diagnosis:

- `in_title_block` is called with rotated dimensions (`page.rect.width=1224, page.rect.height=792`) but text/drawing coords come back in the unrotated MediaBox space (max x=792). The check `x >= 1224 * 0.65 = 795.6` therefore *never* matches, so title-block stamps aren't excluded.
- `extract_route_endpoints` finds global min/max y across **all** red strokes — red callouts, red text underlines, or red title-block accents shift entry/exit endpoints away from the actual route.
- No diagnostic mode — when placement is wrong the user has no way to see which subsystem chose what; add `--debug-coords` that dumps anchor source, route endpoints, and final LatLonBox per page.
- The `+x_pdf=NORTH, +y_pdf=EAST` convention only holds for `page.rotation == 270` (the standard MasTec/Comcast portrait-stored layout). Pages with rotation 0/90/180 silently produce 90°-misoriented overlays. Add an explicit rotation check that bails with a clear error rather than guessing.

**Tech Stack:** Python 3.12, PyMuPDF (`fitz`), Pillow. Same dependencies as today.

**Validation strategy:** Two new evals (off-route-stamp anchor accuracy + two-corner mode) plus re-running the existing three evals. Existing eval #1 (PERU job) may shift slightly — its expected output is permissive ("roughly at lat 40.801, lon -86.030 to -86.015") and should still pass; a small shift on the eastern boundary is acceptable because the new behavior is *more* accurate, binding the seed lat/lon to the actual route start endpoint instead of the address-text centroid.

---

## File Structure

All paths are relative to `C:\Users\thalf\.claude\skills\cd-ground-overlays\`.

```
cd-ground-overlays/
├── SKILL.md                                            # MODIFY — document new ladder, --debug-coords, --two-corner-anchors, --legacy-text-anchor
├── scripts/
│   └── build_overlays.py                               # MODIFY — bug fixes + new anchor ladder + diagnostic flag
├── evals/
│   ├── evals.json                                      # MODIFY — add evals 6 (off-route stamp) and 7 (two-corner)
│   └── fixtures/
│       ├── build_synthetic_off_route_anchor.py         # CREATE
│       └── build_synthetic_two_corner.py               # CREATE
```

**Boundaries:**

- All logic stays in `build_overlays.py` — the script is the single entry point per the skill's existing convention. Don't introduce new modules; this is a focused fix, not a refactor.
- New helpers (`closest_route_endpoint`, `apply_two_corner_anchor`, `_dump_debug_coords`) are private (underscore-prefixed if non-public) and live alongside existing helpers.
- The two new fixtures follow the existing fixture pattern: a single `main()` that takes an output directory, builds a synthetic PDF, returns a path. They reuse `ZIP_DATE`, `JB_NAME`, `PAGE_W`, `PAGE_H` constants.
- **Working directory for tasks:** `cd-ground-overlays/`. Python imports stay flat (the script is run as a file, not as a module).

**Note on git:** `~/.claude/skills/` is not currently a git repository. Commit steps below are written assuming the engineer either runs `git init` in `cd-ground-overlays/` before Task 1 or skips the commit lines — both are acceptable.

---

## Task 1: Add `--debug-coords` diagnostic mode

**Files:**

- Modify: `scripts/build_overlays.py` — add `_dump_debug_coords` helper and new CLI flag, wire it into both single-PDF and multi-PRM orchestrators.

**Why first:** Without diagnostics, the next tasks can't be validated. The user runs the script today and sees "the placement is wrong" — they need a printout of *which anchor source won, which (x_pdf, y_pdf) was used, which lat/lon, and what bounds came out* to verify each fix.

- [ ] **Step 1: Add the helper**

Insert after `_build_overlays` (around line 583), before `# ----- Single-PDF orchestrator -----`:

```python
def _dump_debug_coords(label, overlays, anchors, notes, anchor_key_fn=None):
    """Print a one-line-per-page diagnostic of anchor source, PDF coords, and bounds.

    label: e.g. "single PDF" or a PRM name. anchor_key_fn maps a meta dict
    to the key used in the anchors dict (defaults to page_number).
    """
    if anchor_key_fn is None:
        anchor_key_fn = lambda ov: ov["page"]
    print(f"== DEBUG COORDS: {label} ==", file=sys.stderr)
    print(f"  {'page':>4}  {'sheet':>5}  {'anchor_x':>9}  {'anchor_y':>9}  "
          f"{'anchor_lat':>11}  {'anchor_lon':>12}  {'N':>9}  {'S':>9}  "
          f"{'E':>10}  {'W':>10}  source", file=sys.stderr)
    for ov in overlays:
        a = anchors.get(anchor_key_fn(ov))
        if a is None:
            print(f"  {ov['page']:>4}  {ov['sheet_label']:>5}  "
                  f"{'(none)':>9}  {'(none)':>9}  {'-':>11}  {'-':>12}  "
                  f"{ov['north']:>9.6f}  {ov['south']:>9.6f}  "
                  f"{ov['east']:>10.6f}  {ov['west']:>10.6f}  NO ANCHOR",
                  file=sys.stderr)
            continue
        note = notes.get(anchor_key_fn(ov), "")
        # First few words of the note encode the source
        source = note.split(".", 1)[0][:48] if note else "?"
        print(f"  {ov['page']:>4}  {ov['sheet_label']:>5}  "
              f"{a['x0']:>9.1f}  {a['y0']:>9.1f}  "
              f"{a['lat0']:>11.6f}  {a['lon0']:>12.6f}  "
              f"{ov['north']:>9.6f}  {ov['south']:>9.6f}  "
              f"{ov['east']:>10.6f}  {ov['west']:>10.6f}  {source}",
              file=sys.stderr)
```

- [ ] **Step 2: Add the CLI flag**

In `main()` after the existing `--debug` line (around line 1076):

```python
    ap.add_argument("--debug-coords", action="store_true",
                    help="After building overlays, print a per-page table of anchor "
                         "source, PDF coords, lat/lon, and final LatLonBox to stderr. "
                         "Use this to diagnose 'placements look wrong in Google Earth' "
                         "without re-rendering — the table tells you which anchor source "
                         "won and which (x_pdf, y_pdf) it bound to.")
```

- [ ] **Step 3: Wire it into single-PDF mode**

In `process_pdf` (around line 587), change the function signature to also return the `anchors` and `notes` dicts so the orchestrator can pass them to the dumper. Replace the final `return overlays` (around line 646) with `return overlays, anchors, notes`. Then in `main()` (around line 1126), update the single-PDF call site:

```python
        ovs, anchors, notes = process_pdf(inp, args.dpi, args.scale_feet_per_inch, manual, img_dir,
                                          args.debug, **render_kwargs)
        write_kmz(ovs, out,
                  doc_name=f"{inp.stem} - Site Plan Overlays",
                  doc_description=f"Ground overlays for {inp.name}.",
                  source_pdf=inp)
        print(f"Wrote {out} ({len(ovs)} overlays, embedded {inp.name})", file=sys.stderr)
        if args.debug_coords:
            _dump_debug_coords(inp.stem, ovs, anchors, notes)
```

- [ ] **Step 4: Wire it into multi-PRM mode**

`process_multi_prm` already builds `anchors` and `notes` keyed by `(prm_name, page_number)`. Change its return type from `[(prm_name, pdf, overlays), ...]` to `[(prm_name, pdf, overlays, prm_anchors, prm_notes), ...]` where `prm_anchors`/`prm_notes` are the per-PRM dicts already built in Phase 8 (around line 865). Concretely, replace the final loop:

```python
    out = []
    for res in prm_results:
        prm_name = res["prm_name"]
        site_pages = [m for m in res["pages_meta"] if m["is_site"]]
        site_pages.sort(key=lambda x: x["page_number"])
        prm_anchors = {m["page_number"]: anchors.get((prm_name, m["page_number"])) for m in site_pages}
        prm_notes = {m["page_number"]: notes.get((prm_name, m["page_number"]), "") for m in site_pages}
        overlays = _build_overlays(site_pages, prm_anchors, prm_notes, scale_ft_per_inch)
        res["doc"].close()
        out.append((prm_name, res["pdf_path"], overlays, prm_anchors, prm_notes))
    return out
```

Then update the `main()` call site in the multi-prm branch (around line 1098):

```python
        prm_results = process_multi_prm(
            inp, args.dpi, args.scale_feet_per_inch, manual, nested_manual,
            debug=args.debug,
            reconciliation_threshold_m=args.reconciliation_threshold_m,
            **render_kwargs,
        )
        jb_overlays = []
        for prm_name, pdf, ovs, prm_anchors, prm_notes in prm_results:
            print(f"== Wrote overlays for {prm_name}: {pdf.name} ({len(ovs)} sheets) ==", file=sys.stderr)
            renamed_pdf = pdf.parent / f"{prm_name}.pdf"
            if renamed_pdf.resolve() != pdf.resolve():
                shutil.copy2(pdf, renamed_pdf)
            kmz_out = pdf.parent / f"{prm_name}_overlays.kmz"
            write_kmz(ovs, kmz_out,
                      doc_name=f"{inp.name} / {prm_name} - Site Plan Overlays",
                      doc_description=f"Ground overlays for {pdf.name}.",
                      source_pdf=renamed_pdf)
            print(f"  -> {kmz_out} ({len(ovs)} overlays, embedded {renamed_pdf.name})", file=sys.stderr)
            if args.debug_coords:
                _dump_debug_coords(prm_name, ovs, prm_anchors, prm_notes)
            jb_overlays.append((prm_name, ovs, renamed_pdf))
```

- [ ] **Step 5: Run the existing eval-3 fixture and confirm the dump appears**

```bash
python evals/fixtures/build_synthetic_cross_prm.py /tmp/eval-data/cross_prm
python scripts/build_overlays.py /tmp/eval-data/cross_prm/JB_TEST_XPRM --multi-prm --combined --debug-coords 2>/tmp/debug.txt
cat /tmp/debug.txt
```

Expected: `/tmp/debug.txt` contains a `== DEBUG COORDS: PRM0000000001 ==` header followed by exactly one row for the SITE PLAN - 1 sheet, then a `== DEBUG COORDS: PRM0000000002 ==` header followed by two rows (SITE PLAN - 2 and SITE PLAN - 3). Source column for PRM1/SP1 should read `Embedded lat/lon stamp at PDF` (or whatever the embedded note begins with); for PRM2 the source column reads `Chained from`.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_overlays.py
git commit -m "feat(cd-ground-overlays): add --debug-coords diagnostic mode

Prints per-page anchor source, PDF coords, lat/lon, and final LatLonBox
to stderr after build. Foundation for diagnosing placement bugs."
```

---

## Task 2: Fix `in_title_block` to use unrotated MediaBox dimensions

**Files:**

- Modify: `scripts/build_overlays.py:147` — `in_title_block` and call sites.

**Why this matters:** Today the function gets `page_w=page.rect.width=1224, page_h=page.rect.height=792`, but text/drawing coords come back in the unrotated MediaBox (max x=792, max y=1224). So `x >= 795.6` is never true and the title-block guard always returns False. On a multi-stamp page, the wrong stamp can win and the whole sheet anchors wrong.

The title block in the rendered image lives at *display BR*. Mapped back through the 270°-CW rotation, that corresponds to *unrotated bottom-left* in PyMuPDF's y-down MediaBox: small `x_orig`, large `y_orig`.

- [ ] **Step 1: Write the failing test**

Add to a new test file `tests/test_in_title_block.py` (create the `tests/` folder if missing — keep it tiny, no `__init__.py` needed because we run with `pytest` from the skill folder):

```python
"""Tests for the title-block exclusion fix."""
import sys
from pathlib import Path

# Allow the test to import build_overlays without packaging the script.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from build_overlays import in_title_block


def test_text_in_unrotated_bottom_left_is_in_title_block():
    """Title block displays at rendered BR -> unrotated BL (small x, large y).

    For a 270-rotated 792x1224 portrait page, the title block region in
    UNROTATED coords is x_orig small AND y_orig large.
    """
    # MediaBox dimensions for a portrait page stored 792x1224
    page_w_unrotated, page_h_unrotated = 792, 1224
    # A point well inside the title-block region (small x, large y)
    assert in_title_block(50, 1100, page_w_unrotated, page_h_unrotated) is True


def test_text_in_unrotated_top_right_is_not_in_title_block():
    """The opposite corner — large x, small y — is NOT the title block."""
    page_w_unrotated, page_h_unrotated = 792, 1224
    assert in_title_block(700, 100, page_w_unrotated, page_h_unrotated) is False


def test_text_at_unrotated_top_left_is_not_in_title_block():
    """Top-left of unrotated == display TL (or near it after rotation): not the title block."""
    page_w_unrotated, page_h_unrotated = 792, 1224
    assert in_title_block(50, 100, page_w_unrotated, page_h_unrotated) is False
```

- [ ] **Step 2: Run the test and confirm it fails**

```bash
pytest tests/test_in_title_block.py -v
```

Expected: All three tests FAIL with the current implementation. The first fails because `50 >= 792 * 0.65 = 514.8` is False (current logic returns False). The second/third coincidentally pass-in-meaning today only because *every* call returns False.

- [ ] **Step 3: Rewrite `in_title_block`**

Replace the current definition (around line 146) with:

```python
def in_title_block(x, y, page_w_unrotated, page_h_unrotated):
    """True when (x, y) sits in the title-block region of an unrotated MediaBox.

    For the standard MasTec/Comcast layout the title block prints at the
    *display* bottom-right of the rendered landscape page. Under the 270-deg
    PDF rotation that corresponds to *unrotated bottom-left* in PyMuPDF's
    y-down MediaBox space — small x_orig, large y_orig.

    Pass page.mediabox dimensions (NOT page.rect.width/height — those are
    rotated and don't match the coord system that get_text/get_drawings
    returns).
    """
    return (x <= page_w_unrotated * (1.0 - TITLE_BLOCK_X_FRAC)
            and y >= page_h_unrotated * TITLE_BLOCK_Y_FRAC)
```

The fractions stay the same (0.65, 0.75) but the geometric meaning shifts: `TITLE_BLOCK_X_FRAC` now bounds the "right ~35% in display = left ~25% in unrotated" zone, and `TITLE_BLOCK_Y_FRAC` bounds the "bottom 25% in display = bottom 25% in unrotated y-down".

- [ ] **Step 4: Update every call site to pass MediaBox dimensions, not rect dimensions**

Search for `page_w, page_h = ` and `is_site_plan(blocks, i, page.rect.width, page.rect.height)` style usages. There are three call paths to `in_title_block`:

`extract_embedded_latlon`, `extract_split_latlon`, `parse_site_plan_ordinal` — all receive `page_w, page_h` from their caller, which is `_extract_pdf_pages_metadata` and `is_site_plan`. Change the metadata extractor (around line 376):

```python
def _extract_pdf_pages_metadata(pdf_path):
    doc = fitz.open(str(pdf_path))
    pages_meta = []
    cover_anchors = []
    for i, page in enumerate(doc):
        blocks = text_blocks(page)
        # MediaBox = unrotated; matches the coord system get_text returns.
        mb = page.mediabox
        page_w_un, page_h_un = mb.width, mb.height
        site = is_site_plan(blocks, i, page_w_un, page_h_un)
        meta = {
            "page_number": i + 1,
            "is_site": site,
            "page_size_unrotated": [page_w_un, page_h_un],
            "page_size": [page.rect.width, page.rect.height],  # rotated; kept for page_corner_bounds
            "rotation": page.rotation,
        }
        if site:
            meta["embedded"] = extract_any_latlon(blocks, page_w_un, page_h_un)
            meta["entry_pdf"], meta["exit_pdf"] = extract_route_endpoints(page)
            meta["site_plan_ordinal"] = parse_site_plan_ordinal(blocks, page_w_un, page_h_un)
        else:
            cov = extract_any_latlon(blocks, page_w_un, page_h_un)
            if cov:
                x, y, lat, lon = cov
                cover_anchors.append((i + 1, x, y, lat, lon))
        pages_meta.append(meta)
    return pages_meta, cover_anchors, doc
```

Note: existing code reads `m["page_size"]` in `_anchor_one_site_page` (around line 477 — the cover-page fallback uses page-center as anchor) and in `_build_overlays`. Keep `m["page_size"]` as the rotated dims for `page_corner_bounds` (which expects rotated width/height as inputs and uses them as upper bounds for unrotated corner coordinates — that math is consistent and unchanged). The new `m["page_size_unrotated"]` is only consumed by anchor-extraction paths.

For the page-center fallback in `_anchor_one_site_page` (around line 477):

```python
            cx_pdf = m["page_size_unrotated"][0] / 2  # was m["page_size"][1] / 2
            cy_pdf = m["page_size_unrotated"][1] / 2  # was m["page_size"][0] / 2
```

This is also a latent bug — the old code used rotated `page_size` indices that *happened* to give center-ish values for the standard 270° case but would be wrong for any other rotation. Use the unrotated dims explicitly.

- [ ] **Step 5: Run the test and confirm it passes**

```bash
pytest tests/test_in_title_block.py -v
```

Expected: All three tests PASS.

- [ ] **Step 6: Re-run eval-3 with `--debug-coords` and confirm the existing fixture still chains correctly**

```bash
python evals/fixtures/build_synthetic_cross_prm.py /tmp/eval-data/cross_prm
python scripts/build_overlays.py /tmp/eval-data/cross_prm/JB_TEST_XPRM --multi-prm --combined --debug-coords 2>/tmp/debug.txt
grep "PRM0000000001" /tmp/debug.txt
```

Expected: PRM1/SP1's source column still reads `Embedded lat/lon stamp at PDF` and its anchor_x/anchor_y are still `(50.0, 600.0)` — the synthetic fixture's lat/lon stamp is at unrotated (50, 600), well outside any title-block region, so the fix shouldn't change selection here.

- [ ] **Step 7: Commit**

```bash
git add scripts/build_overlays.py tests/test_in_title_block.py
git commit -m "fix(cd-ground-overlays): in_title_block was always False

The check was called with page.rect.width=1224 (rotated) but text coords
come back in the unrotated MediaBox (max x=792). x >= 1224*0.65 = 795.6
never matched. Pass page.mediabox dims and flip the x predicate so the
title block — display-BR -> unrotated-BL — actually gets excluded."
```

---

## Task 3: Bind embedded stamps to the nearest route polyline endpoint

**Files:**

- Modify: `scripts/build_overlays.py` — add `closest_route_endpoint` helper, rewrite the embedded-stamp branch in `_anchor_one_site_page`, add `--legacy-text-anchor` flag.

**Why this is the main fix:** On real CDs the `LAT, LON` text sits in an address strip, callout box, or notes section. The skill currently uses the text bbox centroid as the anchor's (x_pdf, y_pdf) and assumes that pixel = that geographic point. It rarely does. The cover-page fallback already does the right thing (binds (lat, lon) to the route entry endpoint of the first site plan); apply the same logic to the embedded-stamp branch.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_in_title_block.py` (or create `tests/test_anchor_binding.py`):

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from build_overlays import closest_route_endpoint


def test_returns_none_when_no_endpoints():
    assert closest_route_endpoint((100, 100), None, None) is None


def test_returns_the_only_endpoint_when_one_present():
    assert closest_route_endpoint((100, 100), (200, 200), None) == (200, 200)
    assert closest_route_endpoint((100, 100), None, (300, 300)) == (300, 300)


def test_returns_the_closer_endpoint():
    # text near (50, 600), entry at (396, 0), exit at (396, 1224)
    # |entry - text| = sqrt(346^2 + 600^2) ~= 692.6
    # |exit  - text| = sqrt(346^2 + 624^2) ~= 713.5
    assert closest_route_endpoint((50, 600), (396, 0), (396, 1224)) == (396, 0)


def test_returns_the_closer_endpoint_when_text_is_near_exit():
    assert closest_route_endpoint((1100, 600), (396, 0), (396, 1224)) == (396, 1224)
```

- [ ] **Step 2: Run the test and confirm it fails**

```bash
pytest tests/ -v -k closest_route_endpoint
```

Expected: All four tests FAIL with `ImportError: cannot import name 'closest_route_endpoint'`.

- [ ] **Step 3: Implement `closest_route_endpoint`**

Insert just after `extract_route_endpoints` in `build_overlays.py` (around line 254):

```python
def closest_route_endpoint(text_pdf, entry_pdf, exit_pdf):
    """Return the route polyline endpoint closer to the text bbox centroid, or None.

    text_pdf: (x, y) in unrotated PDF coords (the bbox centroid of the lat/lon stamp).
    entry_pdf, exit_pdf: route endpoints from extract_route_endpoints (either may be None).
    """
    candidates = [p for p in (entry_pdf, exit_pdf) if p is not None]
    if not candidates:
        return None
    tx, ty = text_pdf
    return min(candidates, key=lambda p: (p[0] - tx) ** 2 + (p[1] - ty) ** 2)
```

- [ ] **Step 4: Run the test and confirm it passes**

```bash
pytest tests/ -v -k closest_route_endpoint
```

Expected: All four tests PASS.

- [ ] **Step 5: Add `--legacy-text-anchor` CLI flag**

In `main()` (around line 1076, alongside other anchor-related flags):

```python
    ap.add_argument("--legacy-text-anchor", action="store_true",
                    help="Restore pre-fix behavior: anchor embedded lat/lon stamps at "
                         "the text bbox centroid instead of binding them to the nearest "
                         "route polyline endpoint. The default (off) is more accurate "
                         "for real CDs where the stamp text sits in a margin away from "
                         "the route. Use this only to reproduce older outputs.")
```

Plumb the flag through `process_pdf` and `process_multi_prm` as `legacy_text_anchor=args.legacy_text_anchor`, and forward it to `_anchor_one_site_page`. The function signature for `_anchor_one_site_page` becomes:

```python
def _anchor_one_site_page(m, manual_anchors, cover_pool, scale_ft_per_inch,
                          state, current_label, legacy_text_anchor=False):
```

- [ ] **Step 6: Rewrite the embedded-stamp branch**

In `_anchor_one_site_page` replace the current `elif m.get("embedded"):` block (around line 442):

```python
    # 2. Embedded latlon on this page (inline or split LAT/LONG)
    elif m.get("embedded"):
        x, y, lat, lon = m["embedded"]
        rep = closest_route_endpoint((x, y), m.get("entry_pdf"), m.get("exit_pdf"))
        if rep is not None and not legacy_text_anchor:
            anchor = {"x0": rep[0], "y0": rep[1],
                      "lat0": lat, "lon0": lon, "rotation_deg": 0.0}
            note = (f"Embedded lat/lon stamp at PDF ({x:.1f}, {y:.1f}) bound to "
                    f"nearest route endpoint PDF ({rep[0]:.1f}, {rep[1]:.1f}) -> "
                    f"({lat:.6f}, {lon:.6f}). Confidence: HIGH. (Use "
                    f"--legacy-text-anchor to restore pre-2026-04 behavior that "
                    f"anchored at the text bbox centroid.)")
        else:
            anchor = {"x0": x, "y0": y, "lat0": lat, "lon0": lon, "rotation_deg": 0.0}
            reason = ("legacy mode" if legacy_text_anchor
                      else "no route polyline endpoint detected on this page")
            note = (f"Embedded lat/lon stamp at PDF ({x:.1f}, {y:.1f}) -> "
                    f"({lat:.6f}, {lon:.6f}); anchored at text centroid "
                    f"({reason}). Confidence: MEDIUM.")
```

- [ ] **Step 7: Re-run eval-3 with `--debug-coords` and confirm the synthetic chain still passes**

The synthetic cross-PRM fixture draws a vertical red line at unrotated x=396 from y=0 to y=1224, and the lat/lon stamp at (50, 600). With the new logic, PRM1/SP1's anchor moves from (50, 600) to (396, 0) — the entry endpoint, which is the closer of the two route endpoints. The chain still works because both the anchor and the chained pages use consistent geometry.

```bash
python evals/fixtures/build_synthetic_cross_prm.py /tmp/eval-data/cross_prm
python scripts/build_overlays.py /tmp/eval-data/cross_prm/JB_TEST_XPRM --multi-prm --combined --debug-coords 2>/tmp/debug.txt
grep "SITE PLAN - 1\|SITE PLAN - 2\|SITE PLAN - 3" /tmp/debug.txt
```

Expected: PRM1/SP1 anchor_x=396.0, anchor_y=0.0, source begins with `Embedded lat/lon stamp at PDF (50.0, 600.0) bound to nearest route endpoint`. PRM2/SP2 source begins with `Chained from`. The cross-PRM assertion (PRM2/SP2 west ≈ PRM1/SP1 east) must still hold within 1e-5° because both PRMs share the same reference geometry; verify with:

```bash
python -c "
import zipfile, re
z = zipfile.ZipFile('/tmp/eval-data/cross_prm/JB_TEST_XPRM/JB_TEST_XPRM_combined_overlays.kmz')
kml = z.read('doc.kml').decode()
def grab(name, tag):
    blk = re.search(re.escape(name) + r'.*?<' + tag + r'>([^<]+)</' + tag + r'>', kml, re.S)
    return float(blk.group(1)) if blk else None
sp1_east = grab('SITE PLAN - 1', 'east')
sp2_west = grab('SITE PLAN - 2', 'west')
print(f'PRM1/SP1 east: {sp1_east:.7f}')
print(f'PRM2/SP2 west: {sp2_west:.7f}')
print(f'delta: {abs(sp1_east - sp2_west):.2e}')
assert abs(sp1_east - sp2_west) < 1e-5, 'cross-PRM continuity broken'
print('OK: cross-PRM continuity holds')
"
```

- [ ] **Step 8: Commit**

```bash
git add scripts/build_overlays.py tests/
git commit -m "fix(cd-ground-overlays): bind embedded stamps to nearest route endpoint

On real CDs the lat/lon stamp text sits in an address strip or notes
block far from the actual map point. Today the anchor uses the text
bbox centroid as (x_pdf, y_pdf) and assumes that pixel == that
geographic point — so overlays end up translated. Switch to binding
(lat, lon) to the route polyline endpoint nearest the text. Add
--legacy-text-anchor for users who need to reproduce older outputs."
```

---

## Task 4: Add two-corner geographic anchor mode

**Files:**

- Modify: `scripts/build_overlays.py` — add `apply_two_corner_anchor` helper, accept `two_corner` JSON shape in the manual-anchors loader, new `--two-corner-anchors` flag is **not** required (reuse `--manual-anchors` with a new schema variant).

**Why:** Even with Task 3, some pages have no embedded coord and no usable route polyline. The fastest manual override for the user is: open the rendered PNG in Google Earth, identify two recognizable points (an intersection, a building corner), find their lat/lon on the satellite imagery, note the corresponding pixel positions in the rendered PNG, and feed both pairs in. The script fits a 2-point translation+rotation transform.

A 2-point fit is enough for these CDs because scale is fixed by the title block (`--scale-feet-per-inch`). With scale fixed, two points constrain a translation + rotation — exactly what `pdf_to_latlon`'s `rotation_deg` parameter already supports.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_anchor_binding.py`:

```python
from build_overlays import apply_two_corner_anchor


def test_two_corner_pure_translation():
    """Two corners aligned with the +x_pdf=NORTH, +y_pdf=EAST convention.

    Corner A at PDF (100, 200), lat/lon (40.0, -86.0).
    Corner B at PDF (500, 800), lat/lon (40.001, -85.99).
    The transform should anchor at A and produce 0 rotation.
    """
    a = apply_two_corner_anchor(
        corner_a=(100, 200, 40.0, -86.0),
        corner_b=(500, 800, 40.001, -85.99),
        scale_ft_per_inch=40.0,
    )
    assert a is not None
    assert abs(a["x0"] - 100) < 1e-6
    assert abs(a["y0"] - 200) < 1e-6
    assert abs(a["lat0"] - 40.0) < 1e-9
    assert abs(a["lon0"] - (-86.0)) < 1e-9
    # rotation_deg should be small (within 5 deg) when the two points are
    # roughly aligned with the assumed convention; the scale of "small"
    # depends on which test points you pick.
    assert abs(a["rotation_deg"]) < 5.0


def test_two_corner_returns_none_for_coincident_points():
    a = apply_two_corner_anchor(
        corner_a=(100, 200, 40.0, -86.0),
        corner_b=(100, 200, 40.0, -86.0),
        scale_ft_per_inch=40.0,
    )
    assert a is None
```

- [ ] **Step 2: Run the test and confirm it fails**

```bash
pytest tests/test_anchor_binding.py -v -k two_corner
```

Expected: ImportError on `apply_two_corner_anchor`.

- [ ] **Step 3: Implement `apply_two_corner_anchor`**

Insert just before `# ----- Page rendering -----` in `build_overlays.py` (around line 325):

```python
def apply_two_corner_anchor(corner_a, corner_b, scale_ft_per_inch):
    """Build an anchor dict from two (x_pdf, y_pdf, lat, lon) reference points.

    Anchors at corner_a and computes the rotation that makes corner_b's
    geographic position consistent with the +x_pdf=NORTH/+y_pdf=EAST
    convention at the given scale.

    Returns None if the two corners are too close to fit (<10 PDF points).
    """
    xa, ya, lat_a, lon_a = corner_a
    xb, yb, lat_b, lon_b = corner_b
    dx_pdf = xb - xa
    dy_pdf = yb - ya
    if math.hypot(dx_pdf, dy_pdf) < 10.0:
        return None
    fpp = scale_ft_per_inch / PT_PER_INCH

    # Predicted (north_ft, east_ft) under zero rotation
    pred_north = dx_pdf * fpp
    pred_east = dy_pdf * fpp

    # Observed (north_ft, east_ft) from geographic delta
    obs_north = (lat_b - lat_a) * FEET_PER_DEG_LAT
    obs_east = (lon_b - lon_a) * feet_per_deg_lon(lat_a)

    # Rotation that takes predicted -> observed (in feet-space)
    pred_angle = math.atan2(pred_east, pred_north)
    obs_angle = math.atan2(obs_east, obs_north)
    rot_deg = math.degrees(obs_angle - pred_angle)

    return {
        "x0": xa, "y0": ya,
        "lat0": lat_a, "lon0": lon_a,
        "rotation_deg": rot_deg,
    }
```

- [ ] **Step 4: Run the test and confirm it passes**

```bash
pytest tests/test_anchor_binding.py -v -k two_corner
```

Expected: Both two-corner tests PASS.

- [ ] **Step 5: Wire the new schema into the manual-anchors loader**

The current `manual_anchors.json` shape is `{"page_5": {"x_pdf": ..., "y_pdf": ..., "lat": ..., "lon": ...}}`. Extend it to also accept `{"page_5": {"two_corner": [{x_pdf, y_pdf, lat, lon}, {x_pdf, y_pdf, lat, lon}]}}`. In `_anchor_one_site_page` step 1 (around line 429), replace the current manual block:

```python
    # 1. Manual anchor (highest priority)
    ma = manual_anchors.get(f"page_{n}") or manual_anchors.get(str(n))
    if ma:
        if "two_corner" in ma and len(ma["two_corner"]) == 2:
            ca = ma["two_corner"][0]; cb = ma["two_corner"][1]
            anchor = apply_two_corner_anchor(
                (ca["x_pdf"], ca["y_pdf"], ca["lat"], ca["lon"]),
                (cb["x_pdf"], cb["y_pdf"], cb["lat"], cb["lon"]),
                scale_ft_per_inch,
            )
            if anchor is not None:
                note = (f"Two-corner manual anchor: A=PDF ({ca['x_pdf']:.1f},{ca['y_pdf']:.1f})->"
                        f"({ca['lat']:.6f},{ca['lon']:.6f}); B=PDF ({cb['x_pdf']:.1f},"
                        f"{cb['y_pdf']:.1f})->({cb['lat']:.6f},{cb['lon']:.6f}); "
                        f"rotation_deg={anchor['rotation_deg']:.3f}. Confidence: HIGH.")
        elif "lat" in ma and "lon" in ma:
            anchor = {
                "x0": ma.get("x_pdf", 0),
                "y0": ma.get("y_pdf", 0),
                "lat0": ma["lat"],
                "lon0": ma["lon"],
                "rotation_deg": ma.get("rotation_deg", 0.0),
            }
            note = (f"Manual anchor PDF ({anchor['x0']:.1f}, {anchor['y0']:.1f}) "
                    f"-> ({anchor['lat0']:.6f}, {anchor['lon0']:.6f}). Confidence: HIGH.")
```

(The `if anchor is None` from `apply_two_corner_anchor` falls through to the next ladder rung.)

- [ ] **Step 6: Smoke-test against an existing fixture**

Build a tiny manual-anchors JSON for the synthetic cross-PRM fixture that uses the two-corner schema for PRM1's only sheet, then re-run and verify with `--debug-coords` that source reads `Two-corner manual anchor`.

```bash
python evals/fixtures/build_synthetic_cross_prm.py /tmp/eval-data/cross_prm
cat > /tmp/anchors.json <<'EOF'
{
  "PRM0000000001": {
    "page_5": {
      "two_corner": [
        {"x_pdf": 396, "y_pdf":    0, "lat": 40.801166, "lon": -86.030433},
        {"x_pdf": 396, "y_pdf": 1224, "lat": 40.801166, "lon": -86.029500}
      ]
    }
  }
}
EOF
python scripts/build_overlays.py /tmp/eval-data/cross_prm/JB_TEST_XPRM \
    --multi-prm --combined --debug-coords \
    --manual-anchors /tmp/anchors.json 2>/tmp/debug.txt
grep "SITE PLAN - 1" /tmp/debug.txt
```

Expected: source column begins with `Two-corner manual anchor`, anchor_x=396.0, anchor_y=0.0.

- [ ] **Step 7: Commit**

```bash
git add scripts/build_overlays.py tests/test_anchor_binding.py
git commit -m "feat(cd-ground-overlays): two-corner manual anchor mode

Adds a two_corner schema to manual_anchors.json: the user supplies
two (x_pdf, y_pdf, lat, lon) reference pairs and the script fits a
translation+rotation anchor at fixed scale. Easier than figuring out
PDF coords for one anchor + a separate rotation_deg."
```

---

## Task 5: Harden `extract_route_endpoints`

**Files:**

- Modify: `scripts/build_overlays.py:228` — `extract_route_endpoints`.

**Why:** The current function takes the global min-y / max-y across *every* red stroke on the page. Red callout arrows, red text underlines, and red title-block accents pollute the candidate set and shift entry/exit endpoints away from the real route. Restrict the candidate set to the longest connected red polyline.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_anchor_binding.py`:

```python
import fitz

from build_overlays import extract_route_endpoints


def test_endpoints_picks_longest_polyline():
    """A 1224pt red main route plus a 50pt red callout segment.

    Without the fix, the callout's endpoints can win the global y min/max
    if the callout sits at extreme y. With the fix, the longest connected
    polyline (the main route) wins.
    """
    doc = fitz.open()
    page = doc.new_page(width=792, height=1224)
    page.set_rotation(270)
    # Main route: vertical line at x=396 from y=100 to y=1100 (length 1000)
    page.draw_line(fitz.Point(396, 100), fitz.Point(396, 1100),
                   color=(1.0, 0.0, 0.0), width=0.7)
    # Distractor callout: short red line at extreme y=10
    page.draw_line(fitz.Point(700, 10), fitz.Point(720, 30),
                   color=(1.0, 0.0, 0.0), width=0.7)
    entry, exit_ = extract_route_endpoints(page)
    # Without the fix, entry would be (700, 10) -> wrong.
    assert entry == (396, 100), f"expected (396, 100), got {entry}"
    assert exit_ == (396, 1100), f"expected (396, 1100), got {exit_}"
```

- [ ] **Step 2: Run the test and confirm it fails**

```bash
pytest tests/test_anchor_binding.py -v -k endpoints_picks
```

Expected: FAIL with the wrong entry/exit picked from the callout.

- [ ] **Step 3: Rewrite `extract_route_endpoints`**

Replace the current implementation (around line 228) with the polyline-collecting version below:

```python
def extract_route_endpoints(page):
    """Return (entry_pdf, exit_pdf) for the longest connected red polyline.

    entry = endpoint with smallest y_pdf (rendered LEFT under standard
    270-rotation), exit = endpoint with largest y_pdf (rendered RIGHT).
    Restricting to the longest polyline keeps callouts, underlines, and
    title-block accents from polluting the global y-range.
    """
    polylines = []
    for d in page.get_drawings():
        if d.get("type") not in ("s", "sf", "fs"):
            continue
        if not is_route_color(d.get("color")) or not is_route_width(d.get("width")):
            continue
        current = []
        for item in d.get("items", []):
            op = item[0]
            if op == "l":
                p1 = (item[1].x, item[1].y); p2 = (item[2].x, item[2].y)
            elif op == "c":
                # Cubic bezier: take only the endpoints (item[1] start, item[4] end)
                p1 = (item[1].x, item[1].y); p2 = (item[4].x, item[4].y)
            else:
                if current:
                    polylines.append(current); current = []
                continue
            if not current or current[-1] != p1:
                if current:
                    polylines.append(current)
                current = [p1, p2]
            else:
                current.append(p2)
        if current:
            polylines.append(current)
    if not polylines:
        return None, None
    best = max(polylines, key=_polyline_length)
    ymin = min(p[1] for p in best); ymax = max(p[1] for p in best)
    entry = next(p for p in best if p[1] == ymin)
    exit_ = next(p for p in best if p[1] == ymax)
    return entry, exit_


def _polyline_length(points):
    return sum(math.hypot(points[i + 1][0] - points[i][0],
                          points[i + 1][1] - points[i][1])
               for i in range(len(points) - 1))
```

- [ ] **Step 4: Run the test and confirm it passes**

```bash
pytest tests/test_anchor_binding.py -v -k endpoints_picks
```

Expected: PASS.

- [ ] **Step 5: Re-run eval-3 to confirm the synthetic fixture still works**

```bash
python evals/fixtures/build_synthetic_cross_prm.py /tmp/eval-data/cross_prm
python scripts/build_overlays.py /tmp/eval-data/cross_prm/JB_TEST_XPRM --multi-prm --combined --debug-coords 2>/tmp/debug.txt
grep "SITE PLAN" /tmp/debug.txt
```

Expected: anchor_x and anchor_y for PRM1/SP1 are still `(396.0, 0.0)`. The cross-PRM continuity assertion still holds.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_overlays.py tests/test_anchor_binding.py
git commit -m "fix(cd-ground-overlays): pick longest red polyline for endpoints

extract_route_endpoints used global min/max y across all red strokes.
Red callouts, underlines, and title-block accents could shift entry/
exit endpoints. Restrict to the longest connected red polyline."
```

---

## Task 6: Bail clearly on non-270 page rotations

**Files:**

- Modify: `scripts/build_overlays.py` — early-warning in `_extract_pdf_pages_metadata`.

**Why:** The `+x_pdf=NORTH, +y_pdf=EAST` geographic transform only holds for `page.rotation == 270` (270° CW = 90° CCW: +x_orig maps to display-up, +y_orig maps to display-right). For rotation 0 (landscape native), 90, or 180, the same transform produces a 90°/180° misorientation. Today the script silently produces wrong overlays. Detect and warn.

- [ ] **Step 1: Add the rotation guard**

In `_extract_pdf_pages_metadata`, inside the per-page loop after `meta = {...}` (around line 384):

```python
        if site and page.rotation != 270:
            print(f"WARN: page {i + 1}: rotation={page.rotation} (expected 270 for "
                  f"the standard MasTec/Comcast portrait-stored layout). The "
                  f"+x_pdf=NORTH/+y_pdf=EAST geographic transform is only valid "
                  f"for rotation=270; this page's overlay will be misoriented. "
                  f"Supply a manual two-corner anchor for this page or convert "
                  f"the source PDF to rotation=270 before re-running.",
                  file=sys.stderr)
```

- [ ] **Step 2: Re-run any single-PDF eval and confirm no spurious warnings**

```bash
python evals/fixtures/build_synthetic_cross_prm.py /tmp/eval-data/cross_prm
python scripts/build_overlays.py /tmp/eval-data/cross_prm/JB_TEST_XPRM --multi-prm --combined 2>/tmp/log.txt
grep -c "WARN: page.*rotation=" /tmp/log.txt
```

Expected: 0 (the synthetic fixture explicitly sets rotation=270).

- [ ] **Step 3: Commit**

```bash
git add scripts/build_overlays.py
git commit -m "feat(cd-ground-overlays): warn on unsupported page rotation

Geographic transform assumes rotation=270 (portrait-stored, displayed
landscape). Other rotations silently produce 90/180-misoriented
overlays. Print a clear WARN with remediation pointer."
```

---

## Task 7: Add eval — anchor accuracy when stamp is far from route

**Files:**

- Create: `evals/fixtures/build_synthetic_off_route_anchor.py`
- Modify: `evals/evals.json` — add eval id 6.

**Why:** None of the three existing evals catch the original bug (text-position anchor placing overlays away from the route) because they use synthetic PDFs where text and route happen to coincide closely enough or where math consistency alone suffices. This eval forces the stamp text into the title-block region while the route runs through the page center, then asserts the overlay's bounding box covers the route — which it can only do if the anchor binds to the route endpoint.

- [ ] **Step 1: Write the fixture**

Create `evals/fixtures/build_synthetic_off_route_anchor.py`:

```python
#!/usr/bin/env python3
"""build_synthetic_off_route_anchor.py - Fixture for anchor-binding accuracy.

Generates a single-PDF JB folder where the lat/lon stamp text is intentionally
placed far from the route polyline. With the fix in place (Task 3), the
overlay's bounding box must still cover the route's geographic extent.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import fitz


JB_NAME = "JB_TEST_OFF_ROUTE"
PRM_NAME = "PRM0099000003"
PAGE_W = 792
PAGE_H = 1224

# Lat/lon stamp text placed near unrotated bottom-right (display top-right of
# the title-block strip — far from the route polyline)
STAMP_X = 750
STAMP_Y = 1180
STAMP_LAT = 40.801166
STAMP_LON = -86.030433

# Route polyline endpoints (entry at small y_unrotated = rendered LEFT,
# exit at large y_unrotated = rendered RIGHT). Route at unrotated x=400.
ROUTE_ENTRY = (400, 50)
ROUTE_EXIT = (400, 1170)


def _draw_non_site_page(doc: fitz.Document, kind: str) -> None:
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.set_rotation(270)
    page.insert_text(fitz.Point(50, 100), f"{kind.upper()} PAGE", fontsize=24)


def _draw_site_plan(doc: fitz.Document) -> None:
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.set_rotation(270)
    page.insert_text(fitz.Point(700, 1180), "SITE PLAN - 1", fontsize=14)
    page.insert_text(fitz.Point(50, 700), "100 N MAIN ST, ANYTOWN IN 46970", fontsize=10)
    # Stamp deliberately far from the route
    page.insert_text(fitz.Point(STAMP_X, STAMP_Y),
                     f"{STAMP_LAT:.6f}, {STAMP_LON:.6f}", fontsize=10)
    # Route polyline
    page.draw_line(
        fitz.Point(*ROUTE_ENTRY), fitz.Point(*ROUTE_EXIT),
        color=(1.0, 0.0, 0.0), width=0.7,
    )


def build_jb(out_dir: Path) -> Path:
    jb = out_dir / JB_NAME
    if jb.exists():
        import shutil
        shutil.rmtree(jb)
    prm = jb / PRM_NAME
    pdf_path = prm / "test.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    for kind in ("cover", "vicinity", "legend", "notes"):
        _draw_non_site_page(doc, kind)
    _draw_site_plan(doc)
    doc.save(str(pdf_path))
    doc.close()
    return jb


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir", type=Path)
    args = ap.parse_args()
    jb = build_jb(args.out_dir.resolve())
    print(f"Wrote synthetic JB folder: {jb}")
    print(f"  stamp text at PDF ({STAMP_X}, {STAMP_Y}) -> "
          f"({STAMP_LAT}, {STAMP_LON})")
    print(f"  route entry at PDF {ROUTE_ENTRY}, exit at PDF {ROUTE_EXIT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Add the eval entry**

Append to `evals/evals.json` `evals` array (use id 6, mind the trailing comma syntax):

```json
{
  "id": 6,
  "name": "anchor-accuracy-stamp-off-route",
  "prompt": "I'm validating that an embedded lat/lon stamp gets bound to the route polyline rather than its text bounding box. First run `python evals/fixtures/build_synthetic_off_route_anchor.py /tmp/eval-data/off_route` to generate a single-PRM JB folder where the stamp text sits at unrotated PDF (750, 1180) but the route runs through (400, 50)..(400, 1170). Then run `python scripts/build_overlays.py /tmp/eval-data/off_route/JB_TEST_OFF_ROUTE --multi-prm --combined --debug-coords 2>/tmp/off_route.log`. Verify three properties: (a) the debug-coords table shows the SITE PLAN - 1 anchor_x ~ 400 (not 750) and anchor_y in {50, 1170} (not 1180), confirming the anchor moved off the text and onto a route endpoint; (b) the SITE PLAN - 1 overlay's LatLonBox geographically contains BOTH route endpoints — i.e., the route entry's geographic position (40.801166, -86.030433 if anchor==entry, or chained from anchor==exit) lies within [south,north]x[west,east] AND the route exit's geographic position likewise lies within those bounds; (c) the source string in the debug-coords output begins with 'Embedded lat/lon stamp at PDF (750.0, 1180.0) bound to nearest route endpoint'. Report pass/fail per assertion plus the actual values.",
  "expected_output": "All three assertions pass. anchor_x reported ~ 400.0, anchor_y reported as 50.0 or 1170.0. Both route endpoints' geographic positions fall inside the overlay's LatLonBox. Source string begins with 'Embedded lat/lon stamp at PDF (750.0, 1180.0) bound to nearest route endpoint'.",
  "files": []
}
```

- [ ] **Step 3: Run the eval and confirm it passes**

```bash
python evals/fixtures/build_synthetic_off_route_anchor.py /tmp/eval-data/off_route
python scripts/build_overlays.py /tmp/eval-data/off_route/JB_TEST_OFF_ROUTE --multi-prm --combined --debug-coords 2>/tmp/off_route.log
grep "SITE PLAN - 1" /tmp/off_route.log
```

Expected: anchor_x ≈ 400.0, anchor_y ∈ {50.0, 1170.0}, source string includes `bound to nearest route endpoint`.

- [ ] **Step 4: Commit**

```bash
git add evals/fixtures/build_synthetic_off_route_anchor.py evals/evals.json
git commit -m "test(cd-ground-overlays): eval for off-route stamp anchor binding

Stamp text sits at unrotated (750, 1180); route runs through (400, 50..1170).
Asserts the anchor binds to the route endpoint, not the text centroid."
```

---

## Task 8: Update SKILL.md to document the new ladder and flags

**Files:**

- Modify: `SKILL.md` — sections "Workflow", "Manual anchors", "Coordinate conventions", "Gotchas".

**Why:** The skill's docstring is what future Claude sessions read to decide how to use it. Document the new ladder, the `--debug-coords` flag, the two-corner schema, the `--legacy-text-anchor` escape hatch, and the rotation guard.

- [ ] **Step 1: Replace the "Manual anchors (optional, sub-2m accuracy)" section**

Find the current section (around SKILL.md:79) and replace with:

```markdown
### Manual anchors (optional, sub-2m accuracy)

Manual anchors override every other anchor source. Two schemas are accepted in `manual_anchors.json`:

**Single-anchor schema** (1-point translation; rotation defaults to 0 unless `rotation_deg` is supplied):

​```json
{
  "page_5": {"x_pdf": 81.3, "y_pdf": 200.3, "lat": 40.801166, "lon": -86.030433}
}
​```

**Two-corner schema** (2-point translation + rotation; easiest to fill in by hand from Google Earth + the rendered PNG):

​```json
{
  "page_5": {
    "two_corner": [
      {"x_pdf": 100, "y_pdf": 200, "lat": 40.801166, "lon": -86.030433},
      {"x_pdf": 700, "y_pdf": 1100, "lat": 40.802500, "lon": -86.025000}
    ]
  }
}
​```

For multi-PRM jobs the schema may be flat (`{"page_5": ...}`) or nested per-PRM (`{"PRM0001388160": {"page_5": ...}}`); the script auto-detects nested mode when any top-level key starts with `PRM`.

Pass `--manual-anchors anchors.json` on the command line. Manual anchors win over every other anchor source on the matched page.
```

- [ ] **Step 2: Replace the "Workflow" section's bullet list with the new ladder**

Find the section starting "The pipeline is one script" (around SKILL.md:51) and append a new sub-section just after the "Single-PDF mode" code block:

```markdown
### Anchor precedence ladder

For each site plan page the script walks this ladder; first hit wins:

1. Manual single anchor (`page_N: {x_pdf, y_pdf, lat, lon}`) — HIGH confidence
2. Manual two-corner anchor (`page_N: {two_corner: [..., ...]}`) — HIGH confidence, supports rotation
3. Embedded lat/lon stamp on the page bound to the nearest route polyline endpoint — HIGH confidence (the default since 2026-04)
4. Embedded lat/lon stamp at the text bbox centroid — MEDIUM confidence (fallback when no route polyline is detected; opt-in with `--legacy-text-anchor` to force)
5. Forward chain from the prior anchored page's route exit endpoint — MEDIUM, errors compound
6. Backward chain from the next anchored page's route entry endpoint — MEDIUM
7. Cover-page lat/lon (harvested from non-site pages) bound to this page's route entry endpoint — MEDIUM
8. Cover-page lat/lon at this page's center — LOW (no route polyline detected)
9. None — overlay placed at a fallback position; manual placement required in Google Earth Pro

Use `--debug-coords` to print, per page, which rung won and which (x_pdf, y_pdf, lat, lon) it used.
```

- [ ] **Step 3: Add a "Diagnostics" section just before "Quality bar by use case"**

```markdown
## Diagnostics

When overlays don't land where you expect, run with `--debug-coords` and inspect the per-page table:

​```bash
python scripts/build_overlays.py /path/to/JBID --multi-prm --combined --debug-coords 2>debug.txt
​```

Each row shows: page number, sheet label, anchor PDF coords, anchor lat/lon, final LatLonBox bounds, and the anchor source. Common diagnoses:

- **Anchor source is `text centroid` and overlays are translated**: the embedded stamp text sits in a margin away from the route. Either the page has no detected red polyline (which is what falls back to the text centroid) or you ran with `--legacy-text-anchor`. Supply a manual two-corner anchor for the page to override.
- **Anchor source is `Cover-page` for every page**: no per-page embedded stamps were detected. Check whether the lat/lon stamp on each site plan is text (PyMuPDF can read it) or rasterized (PyMuPDF can't); if rasterized, supply manual anchors.
- **Anchor x/y are weirdly small or weirdly large**: probably a rotation problem. Check the WARN messages for `rotation=` lines — if any page has rotation other than 270 you need manual anchors for it.
- **Adjacent overlays don't align EW**: the route endpoint extraction picked a callout instead of the main polyline. Look at the rendered PNG; if you see a red callout near the page edge, the longest-polyline filter (added 2026-04) should already handle it — if it still wins, file a bug with the source PDF.
```

- [ ] **Step 4: Update the "Gotchas" section**

Find the existing line about overlays clustering into a tiny patch and add two new bullets after it:

```markdown
- **All overlays placed off-route by a similar offset**: the embedded lat/lon stamp on the seed sheet is being anchored at the text bounding-box centroid, not at the route endpoint nearest it. This is the `--legacy-text-anchor` codepath; the default since 2026-04 binds stamps to the closest route endpoint. If you see this with the default settings the page probably has no detectable red polyline (e.g. CAD'd at a non-route color, or the route stroke width is outside ROUTE_W_MIN..ROUTE_W_MAX). Supply a manual two-corner anchor.
- **WARN: page N: rotation=0 (or 90, 180)**: the geographic transform assumes the standard 270° rotation. For other rotations, supply a manual two-corner anchor for the affected pages or rotate the source PDF to 270 before re-running.
```

- [ ] **Step 5: Commit**

```bash
git add SKILL.md
git commit -m "docs(cd-ground-overlays): document new anchor ladder + diagnostics"
```

---

## Self-Review Checklist

After all eight tasks land:

- [ ] **Spec coverage:** Every issue called out in the Architecture section has a task: title-block bug → Task 2; embedded-stamp anchor bug → Task 3; two-corner override → Task 4; route endpoint robustness → Task 5; rotation guard → Task 6; diagnostics → Task 1; eval coverage → Task 7; docs → Task 8.
- [ ] **Placeholder scan:** No "TBD", "fill in", "implement later", or "similar to Task N" markers anywhere above. Every code step shows the actual code; every test step shows the actual assertions.
- [ ] **Type/name consistency:** Helper names used the same way across tasks — `closest_route_endpoint` (Task 3), `apply_two_corner_anchor` (Task 4), `_polyline_length` and the cleaner `extract_route_endpoints` rewrite (Task 5), `_dump_debug_coords` (Task 1). No mid-plan rename.
- [ ] **Backwards compatibility:** `--legacy-text-anchor` reproduces pre-2026-04 behavior; the existing 5 evals continue to pass (eval-3's cross-PRM continuity assertion is the strongest check; verified in Task 3 step 7).
- [ ] **Validated reference impact:** The PERU job (`JB0002131511/PRM0001388160`) anchored from `40.801166,-86.030433` will shift slightly because the new logic binds that lat/lon to the route start endpoint instead of the address-text centroid. The shift is *toward* correctness — the lat/lon really IS at the route start address. Eval-1's expected output ("roughly at lat 40.801, lon -86.030 to -86.015") is permissive and should still pass; if a tighter check is desired add an assertion in a future eval.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-27-cd-ground-overlays-mapping-fix.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
