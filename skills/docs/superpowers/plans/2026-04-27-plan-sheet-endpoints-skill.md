# Plan-Sheet Endpoints Skill — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill named `plan-sheet-endpoints` that ingests fiber/cable construction-drawing (CD) PDFs from any drafter, identifies the plan-profile sheets, and emits per-sheet start/end metadata as CSV plus a KML containing pins **only** for sheets whose coordinates are stamped directly on that sheet.

**Architecture:** A small Python pipeline of single-responsibility modules under `scripts/`, each callable independently and composed by a single CLI entry point. PyMuPDF reads PDFs, dedicated regex parsers extract coordinates / stations / sheet IDs / route features from text, a permissive scoring classifier separates plan-profile sheets from cover / vicinity / legend / notes / detail / traffic-control pages, an orchestrator produces `PdfResult` records, and writers render CSV + KML deliverables. No vicinity-page coordinates ever flow into per-sheet endpoints — they live in a separate `vicinity_reference.csv` only.

**Tech Stack:** Python 3.12, PyMuPDF (PDF parsing), simplekml (KML output), pyproj (UTM → WGS84 conversion), pandas (CSV writing), pytest with PyMuPDF-generated synthetic fixtures.

---

## File Structure

All files live under `~/.claude/skills/plan-sheet-endpoints/` (the skill is its own git repo, mirroring `dxf-to-kmz`).

| File | Responsibility |
|------|----------------|
| `SKILL.md` | Trigger phrases, prerequisites, workflow recipe — written last, after all behavior is locked in |
| `requirements.txt` | `pymupdf`, `simplekml`, `pyproj`, `pandas`, `pytest` |
| `.gitignore` | Ignore `__pycache__/`, `.pytest_cache/`, `*.pyc` |
| `scripts/__init__.py` | Empty marker file (makes `scripts/` an importable package) |
| `scripts/coord_parser.py` | `parse_decimal_degrees`, `parse_dms`, `parse_utm`, `parse_coords`, `find_all_coords` — text → `(lat, lon)` in WGS84 |
| `scripts/station_parser.py` | `Station` dataclass, `station_to_value`, `parse_stations` — text → numeric station values |
| `scripts/sheet_id_parser.py` | `parse_sheet_id`, `ContinuationRef` dataclass, `parse_continuation_refs` |
| `scripts/feature_parsers.py` | `parse_road_names`, `parse_structures`, `parse_span_lengths`, `parse_construction_type`, `parse_cable_specs` |
| `scripts/page_text.py` | `TextBlock` dataclass, `get_page_text`, `get_text_blocks`, `is_raster_page` (PyMuPDF wrapper) |
| `scripts/page_classifier.py` | `PageType` enum, `classify_page` — score-based page-type classifier |
| `scripts/sheet_extractor.py` | `SheetData`, `VicinityCoord` dataclasses, `extract_sheet`, `extract_vicinity_coords` |
| `scripts/pdf_processor.py` | `PdfResult` dataclass, `process_pdf`, `process_input` (folder or single PDF) |
| `scripts/output_writer.py` | `write_main_csv`, `write_vicinity_csv`, `write_kml` |
| `scripts/extract.py` | `main()` — CLI entry: argparse, orchestrate, write three outputs |
| `tests/__init__.py` | Empty marker file |
| `tests/conftest.py` | Synthetic-PDF fixture builders (programmatic, not binary) |
| `tests/test_*.py` | One file per `scripts/*.py` module |

Total: 9 production modules, 9 test modules, 4 metadata files.

**Why this split:** Each parser has one regex family it owns, making it cheap to add new formats without touching siblings. The page classifier lives apart from the sheet extractor because classification logic gets tuned independently of feature extraction. The orchestrator (`pdf_processor`) and writers (`output_writer`) are separated because the user might one day want JSON, GeoJSON, or PDF outputs alongside CSV/KML — adding a writer is then a one-file change.

---

## Conventions (from `project_skill_conventions.md`)

- **TDD throughout** — RED → GREEN → REFACTOR. Every task starts with a failing test.
- **Programmatic fixtures only** — synthetic PDFs are built at test time with `fitz.open()` + `page.insert_text()`. Never check binary fixtures into git.
- **Run modules with `python -m scripts.MODULE`** — package-style, not `python scripts/MODULE.py`.
- **First-match-wins regex rule lists**, case-insensitive.
- **Tier-based fallbacks** for coordinate parsing (decimal degrees → DMS → UTM).
- **Frequent commits** — one commit per task minimum.

The plan does **not** specify a `pyproject.toml` because `dxf-to-kmz` doesn't have one and the test discovery pattern works fine with pytest's default rootdir behavior (rootdir = skill folder, `scripts/__init__.py` makes the package importable from there).

---

## Task Index

1. Skill scaffolding (directories, `requirements.txt`, `.gitignore`, `__init__.py` files, skeletal `SKILL.md`)
2. `coord_parser` — decimal degrees
3. `coord_parser` — DMS
4. `coord_parser` — UTM
5. `coord_parser` — unified `parse_coords` and `find_all_coords`
6. `station_parser` — `Station`, `station_to_value`, `parse_stations`
7. `sheet_id_parser` — `parse_sheet_id` and `parse_continuation_refs`
8. `feature_parsers` — roads, structures, spans, construction type, cable specs
9. `page_text` — `TextBlock`, `get_page_text`, `get_text_blocks`, `is_raster_page`
10. `page_classifier` — `PageType` enum and scoring `classify_page`
11. `sheet_extractor` — `SheetData`, `VicinityCoord`, `extract_sheet`, `extract_vicinity_coords`
12. `pdf_processor` — `PdfResult`, `process_pdf`, `process_input`
13. `output_writer` — `write_main_csv` and `write_vicinity_csv`
14. `output_writer` — `write_kml`
15. `extract` — CLI entry `main()`
16. Final `SKILL.md` content (trigger phrases, recipe, output schema, gotchas, quality bar)

---

## Task 1: Skill scaffolding

**Files:**
- Create: `~/.claude/skills/plan-sheet-endpoints/requirements.txt`
- Create: `~/.claude/skills/plan-sheet-endpoints/.gitignore`
- Create: `~/.claude/skills/plan-sheet-endpoints/scripts/__init__.py`
- Create: `~/.claude/skills/plan-sheet-endpoints/tests/__init__.py`
- Create: `~/.claude/skills/plan-sheet-endpoints/SKILL.md` (skeletal — fills in Task 16)

- [ ] **Step 1: Create the directory tree**

```bash
mkdir -p ~/.claude/skills/plan-sheet-endpoints/scripts
mkdir -p ~/.claude/skills/plan-sheet-endpoints/tests
cd ~/.claude/skills/plan-sheet-endpoints
git init
```

- [ ] **Step 2: Write `requirements.txt`**

```text
pymupdf>=1.24
simplekml>=1.3
pyproj>=3.6
pandas>=2.0
pytest>=8.0
```

Save to `~/.claude/skills/plan-sheet-endpoints/requirements.txt`.

- [ ] **Step 3: Write `.gitignore`**

```text
__pycache__/
.pytest_cache/
*.pyc
*.kml
*.csv
output/
.venv/
```

Save to `~/.claude/skills/plan-sheet-endpoints/.gitignore`.

- [ ] **Step 4: Create empty `__init__.py` markers**

```bash
touch ~/.claude/skills/plan-sheet-endpoints/scripts/__init__.py
touch ~/.claude/skills/plan-sheet-endpoints/tests/__init__.py
```

- [ ] **Step 5: Write skeletal `SKILL.md`**

Content (the final version is written in Task 16):

```markdown
---
name: plan-sheet-endpoints
description: "Extract per-sheet start and end metadata from every plan-profile sheet in a fiber/cable construction-drawing PDF. Outputs CSV plus a KML containing pins only for sheets with coordinates printed directly on them. Vicinity/cover-page coordinates are kept separate and never used to geolocate per-sheet endpoints."
---

# Plan-Sheet Endpoints (skeleton — see Task 16 for final content)
```

Save to `~/.claude/skills/plan-sheet-endpoints/SKILL.md`.

- [ ] **Step 6: Install dependencies**

```bash
pip install -r ~/.claude/skills/plan-sheet-endpoints/requirements.txt --break-system-packages
```

Expected output: `Successfully installed pymupdf-... simplekml-... pyproj-... pandas-... pytest-...` (or "Requirement already satisfied" lines).

- [ ] **Step 7: Sanity-check pytest discovery**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest -v
```

Expected output: `no tests ran` (zero collected). This proves rootdir + import paths are wired before any module exists.

- [ ] **Step 8: Commit**

```bash
git add SKILL.md requirements.txt .gitignore scripts/__init__.py tests/__init__.py
git commit -m "chore: scaffold plan-sheet-endpoints skill"
```

---

## Task 2: `coord_parser` — decimal degrees

**Files:**
- Create: `~/.claude/skills/plan-sheet-endpoints/scripts/coord_parser.py`
- Create: `~/.claude/skills/plan-sheet-endpoints/tests/test_coord_parser.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_coord_parser.py
import pytest

from scripts.coord_parser import parse_decimal_degrees


def test_parse_dd_signed_pair():
    assert parse_decimal_degrees("34.123456, -118.123456") == pytest.approx((34.123456, -118.123456))


def test_parse_dd_hemisphere_suffix():
    assert parse_decimal_degrees("34.123456 N, 118.123456 W") == pytest.approx((34.123456, -118.123456))


def test_parse_dd_hemisphere_with_degree_symbol():
    assert parse_decimal_degrees("34.123456° N, 118.123456° W") == pytest.approx((34.123456, -118.123456))


def test_parse_dd_lat_lon_labels():
    assert parse_decimal_degrees("LAT: 34.123456 LON: -118.123456") == pytest.approx((34.123456, -118.123456))


def test_parse_dd_southern_hemisphere():
    assert parse_decimal_degrees("33.86 S, 151.20 E") == pytest.approx((-33.86, 151.20))


def test_parse_dd_returns_none_for_no_match():
    assert parse_decimal_degrees("just some text with no coords") is None


def test_parse_dd_rejects_out_of_range_latitude():
    assert parse_decimal_degrees("234.567890, -118.123456") is None
```

Save to `~/.claude/skills/plan-sheet-endpoints/tests/test_coord_parser.py`.

- [ ] **Step 2: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_coord_parser.py -v
```

Expected: ImportError (module `scripts.coord_parser` does not exist) — pytest fails collection with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `parse_decimal_degrees`**

```python
# scripts/coord_parser.py
"""Parse coordinate strings into WGS84 decimal degrees.

Three text formats are handled (in this priority order):
  1. Hemisphere-suffixed decimal degrees:  "34.123456° N, 118.123456° W"
  2. LAT/LON labeled decimals:             "LAT: 34.123456 LON: -118.123456"
  3. Bare signed decimal pair:             "34.123456, -118.123456"

A unified `parse_coords` (added in Task 5) tries decimal degrees, then DMS,
then UTM, and reports which format won.
"""
import re
from typing import Optional, Tuple


_DD_HEMI_RE = re.compile(
    r"(?P<lat>\d{1,2}\.\d{3,10})\s*°?\s*(?P<lat_h>[NS])"
    r"\s*[,;/]?\s*"
    r"(?P<lon>\d{1,3}\.\d{3,10})\s*°?\s*(?P<lon_h>[EW])",
    re.IGNORECASE,
)

_DD_LABELED_RE = re.compile(
    r"LAT(?:ITUDE)?\s*[:=]?\s*(?P<lat>[+-]?\d{1,2}\.\d{3,10})"
    r".{0,40}?"
    r"LON(?:GITUDE|G)?\s*[:=]?\s*(?P<lon>[+-]?\d{1,3}\.\d{3,10})",
    re.IGNORECASE | re.DOTALL,
)

_DD_SIGNED_RE = re.compile(
    r"(?<![A-Za-z\d.])"
    r"(?P<lat>[+-]?\d{1,2}\.\d{3,10})"
    r"\s*[,;]\s*"
    r"(?P<lon>[+-]?\d{1,3}\.\d{3,10})"
    r"(?![A-Za-z\d.])"
)


def parse_decimal_degrees(text: str) -> Optional[Tuple[float, float]]:
    """Return the first lat/lon pair found in decimal-degree form, else None."""
    for pattern in (_DD_HEMI_RE, _DD_LABELED_RE, _DD_SIGNED_RE):
        for m in pattern.finditer(text):
            lat = float(m.group("lat"))
            lon = float(m.group("lon"))
            groups = m.groupdict()
            if (groups.get("lat_h") or "").upper() == "S":
                lat = -abs(lat)
            if (groups.get("lon_h") or "").upper() == "W":
                lon = -abs(lon)
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                return (lat, lon)
    return None
```

Save to `~/.claude/skills/plan-sheet-endpoints/scripts/coord_parser.py`.

- [ ] **Step 4: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_coord_parser.py -v
```

Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/coord_parser.py tests/test_coord_parser.py
git commit -m "feat: parse decimal-degree coordinates"
```

---

## Task 3: `coord_parser` — DMS

**Files:**
- Modify: `~/.claude/skills/plan-sheet-endpoints/scripts/coord_parser.py`
- Modify: `~/.claude/skills/plan-sheet-endpoints/tests/test_coord_parser.py`

- [ ] **Step 1: Append failing DMS tests**

Add to `tests/test_coord_parser.py`:

```python
from scripts.coord_parser import parse_dms


def test_parse_dms_with_symbols():
    lat, lon = parse_dms("34° 07' 24.4\" N, 118° 07' 24.4\" W")
    assert lat == pytest.approx(34.12344, abs=1e-4)
    assert lon == pytest.approx(-118.12344, abs=1e-4)


def test_parse_dms_with_d_m_s_letters():
    lat, lon = parse_dms("34d 07m 24.4s N, 118d 07m 24.4s W")
    assert lat == pytest.approx(34.12344, abs=1e-4)
    assert lon == pytest.approx(-118.12344, abs=1e-4)


def test_parse_dms_dash_separated():
    lat, lon = parse_dms("34-07-24.4N 118-07-24.4W")
    assert lat == pytest.approx(34.12344, abs=1e-4)
    assert lon == pytest.approx(-118.12344, abs=1e-4)


def test_parse_dms_returns_none_for_no_match():
    assert parse_dms("plain text 34.5, -118.5") is None
```

- [ ] **Step 2: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_coord_parser.py -v -k dms
```

Expected: 4 failures with `ImportError` (`parse_dms` not defined).

- [ ] **Step 3: Implement `parse_dms`**

Append to `scripts/coord_parser.py`:

```python
_DMS_RE = re.compile(
    r"(?P<lat_d>\d{1,2})\s*[°d\-]\s*(?P<lat_m>\d{1,2})\s*[′'m\-]\s*(?P<lat_s>\d{1,2}(?:\.\d+)?)\s*[″\"s]?\s*(?P<lat_h>[NS])"
    r"\s*[,;/\s]+\s*"
    r"(?P<lon_d>\d{1,3})\s*[°d\-]\s*(?P<lon_m>\d{1,2})\s*[′'m\-]\s*(?P<lon_s>\d{1,2}(?:\.\d+)?)\s*[″\"s]?\s*(?P<lon_h>[EW])",
    re.IGNORECASE,
)


def _dms_to_decimal(d: str, m: str, s: str, hemi: str) -> float:
    decimal = float(d) + float(m) / 60.0 + float(s) / 3600.0
    if hemi.upper() in ("S", "W"):
        decimal = -decimal
    return decimal


def parse_dms(text: str) -> Optional[Tuple[float, float]]:
    """Return the first lat/lon pair found in DMS form, else None."""
    m = _DMS_RE.search(text)
    if not m:
        return None
    lat = _dms_to_decimal(m.group("lat_d"), m.group("lat_m"), m.group("lat_s"), m.group("lat_h"))
    lon = _dms_to_decimal(m.group("lon_d"), m.group("lon_m"), m.group("lon_s"), m.group("lon_h"))
    if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
        return (lat, lon)
    return None
```

- [ ] **Step 4: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_coord_parser.py -v
```

Expected: `11 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/coord_parser.py tests/test_coord_parser.py
git commit -m "feat: parse DMS coordinates"
```

---

## Task 4: `coord_parser` — UTM

**Files:**
- Modify: `~/.claude/skills/plan-sheet-endpoints/scripts/coord_parser.py`
- Modify: `~/.claude/skills/plan-sheet-endpoints/tests/test_coord_parser.py`

- [ ] **Step 1: Append failing UTM tests**

Add to `tests/test_coord_parser.py`:

```python
from scripts.coord_parser import parse_utm


def test_parse_utm_zone_letter_form():
    # Zone 11N near Los Angeles
    lat, lon = parse_utm("Zone 11N, 372345 E, 3776543 N")
    assert lat == pytest.approx(34.12, abs=0.05)
    assert lon == pytest.approx(-118.27, abs=0.05)


def test_parse_utm_compact_form():
    lat, lon = parse_utm("UTM 11N 372345E 3776543N")
    assert lat == pytest.approx(34.12, abs=0.05)
    assert lon == pytest.approx(-118.27, abs=0.05)


def test_parse_utm_southern_hemisphere():
    # Zone 56H (Sydney area)
    lat, lon = parse_utm("Zone 56H 334897 E 6252001 N")
    assert lat == pytest.approx(-33.86, abs=0.05)
    assert lon == pytest.approx(151.21, abs=0.05)


def test_parse_utm_returns_none_for_no_match():
    assert parse_utm("plain text no zones here") is None
```

- [ ] **Step 2: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_coord_parser.py -v -k utm
```

Expected: 4 failures with `ImportError` (`parse_utm` not defined).

- [ ] **Step 3: Implement `parse_utm`**

Append to `scripts/coord_parser.py`:

```python
from pyproj import Transformer

_UTM_RE = re.compile(
    r"(?:ZONE|UTM)\s*(?P<zone>\d{1,2})\s*(?P<band>[A-HJ-NP-Z])"
    r"[,\s]*"
    r"(?P<easting>\d{6,7})\s*E?"
    r"[,\s]+"
    r"(?P<northing>\d{6,7})\s*N?",
    re.IGNORECASE,
)


def parse_utm(text: str) -> Optional[Tuple[float, float]]:
    """Return the first lat/lon pair found in UTM form, else None.

    Band letters N..X are northern hemisphere, C..M are southern.
    """
    m = _UTM_RE.search(text)
    if not m:
        return None
    zone = int(m.group("zone"))
    band = m.group("band").upper()
    easting = float(m.group("easting"))
    northing = float(m.group("northing"))

    is_north = band >= "N"
    epsg = 32600 + zone if is_north else 32700 + zone
    transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(easting, northing)
    if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
        return (lat, lon)
    return None
```

- [ ] **Step 4: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_coord_parser.py -v
```

Expected: `15 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/coord_parser.py tests/test_coord_parser.py
git commit -m "feat: parse UTM coordinates via pyproj"
```

---

## Task 5: `coord_parser` — unified entry points

**Files:**
- Modify: `~/.claude/skills/plan-sheet-endpoints/scripts/coord_parser.py`
- Modify: `~/.claude/skills/plan-sheet-endpoints/tests/test_coord_parser.py`

- [ ] **Step 1: Append failing tests for `parse_coords` and `find_all_coords`**

Add to `tests/test_coord_parser.py`:

```python
from scripts.coord_parser import parse_coords, find_all_coords


def test_parse_coords_picks_decimal_first():
    result = parse_coords("LAT: 34.123456 LON: -118.123456 (also 34d 07m 24.4s N 118d 07m 24.4s W)")
    assert result is not None
    lat, lon, fmt = result
    assert fmt == "decimal_degrees"
    assert lat == pytest.approx(34.123456, abs=1e-4)


def test_parse_coords_falls_through_to_dms():
    result = parse_coords("Reference: 34° 07' 24.4\" N, 118° 07' 24.4\" W")
    assert result is not None
    lat, lon, fmt = result
    assert fmt == "dms"
    assert lat == pytest.approx(34.12344, abs=1e-4)


def test_parse_coords_falls_through_to_utm():
    result = parse_coords("Stamp: Zone 11N 372345 E 3776543 N")
    assert result is not None
    lat, lon, fmt = result
    assert fmt == "utm"
    assert lat == pytest.approx(34.12, abs=0.05)


def test_parse_coords_returns_none_for_no_match():
    assert parse_coords("no coords in this text") is None


def test_find_all_coords_returns_each_format_once():
    text = (
        "Start LAT: 34.123456 LON: -118.123456\n"
        "Mid 34° 07' 24.4\" N, 118° 07' 24.4\" W\n"
        "End Zone 11N 372500 E 3776600 N\n"
    )
    results = find_all_coords(text)
    formats = sorted(r[2] for r in results)
    assert formats == ["decimal_degrees", "dms", "utm"]
    assert len(results) == 3
```

- [ ] **Step 2: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_coord_parser.py -v -k "parse_coords or find_all"
```

Expected: 5 failures with `ImportError`.

- [ ] **Step 3: Implement `parse_coords` and `find_all_coords`**

Append to `scripts/coord_parser.py`:

```python
from typing import List


def parse_coords(text: str) -> Optional[Tuple[float, float, str]]:
    """Try decimal degrees, then DMS, then UTM. Return (lat, lon, format) or None.

    `format` is one of: "decimal_degrees", "dms", "utm".
    """
    dd = parse_decimal_degrees(text)
    if dd is not None:
        return (dd[0], dd[1], "decimal_degrees")
    dms = parse_dms(text)
    if dms is not None:
        return (dms[0], dms[1], "dms")
    utm = parse_utm(text)
    if utm is not None:
        return (utm[0], utm[1], "utm")
    return None


def find_all_coords(text: str) -> List[Tuple[float, float, str]]:
    """Find every coord-pair occurrence in text across all three formats.

    Used by sheet_extractor to detect 1+ stamps on a plan sheet so start/end
    coords can be assigned independently.
    """
    results: List[Tuple[float, float, str]] = []

    for pattern in (_DD_HEMI_RE, _DD_LABELED_RE, _DD_SIGNED_RE):
        for m in pattern.finditer(text):
            lat = float(m.group("lat"))
            lon = float(m.group("lon"))
            groups = m.groupdict()
            if (groups.get("lat_h") or "").upper() == "S":
                lat = -abs(lat)
            if (groups.get("lon_h") or "").upper() == "W":
                lon = -abs(lon)
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                results.append((lat, lon, "decimal_degrees"))

    for m in _DMS_RE.finditer(text):
        lat = _dms_to_decimal(m.group("lat_d"), m.group("lat_m"), m.group("lat_s"), m.group("lat_h"))
        lon = _dms_to_decimal(m.group("lon_d"), m.group("lon_m"), m.group("lon_s"), m.group("lon_h"))
        if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
            results.append((lat, lon, "dms"))

    for m in _UTM_RE.finditer(text):
        zone = int(m.group("zone"))
        band = m.group("band").upper()
        easting = float(m.group("easting"))
        northing = float(m.group("northing"))
        is_north = band >= "N"
        epsg = 32600 + zone if is_north else 32700 + zone
        transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(easting, northing)
        if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
            results.append((lat, lon, "utm"))

    return results
```

- [ ] **Step 4: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_coord_parser.py -v
```

Expected: `20 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/coord_parser.py tests/test_coord_parser.py
git commit -m "feat: unified parse_coords and find_all_coords"
```

---

## Task 6: `station_parser`

**Files:**
- Create: `~/.claude/skills/plan-sheet-endpoints/scripts/station_parser.py`
- Create: `~/.claude/skills/plan-sheet-endpoints/tests/test_station_parser.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_station_parser.py
from scripts.station_parser import Station, parse_stations, station_to_value


def test_station_to_value_basic():
    assert station_to_value("21+37") == 2137
    assert station_to_value("0+00") == 0
    assert station_to_value("100+50") == 10050


def test_station_to_value_with_decimal():
    assert station_to_value("21+37.5") == 2137  # truncate to int feet


def test_parse_stations_with_letter_prefix():
    stations = parse_stations("Route runs B 21+37 to B 24+50")
    assert len(stations) == 2
    assert stations[0] == Station(prefix="B", value=2137, original="B 21+37")
    assert stations[1] == Station(prefix="B", value=2450, original="B 24+50")


def test_parse_stations_with_sta_prefix():
    stations = parse_stations("Stations: STA 5+00 and STA 12+50")
    assert len(stations) == 2
    assert stations[0].prefix == "STA"
    assert stations[0].value == 500
    assert stations[1].value == 1250


def test_parse_stations_bare_form():
    stations = parse_stations("0+00 to 12+50 along the route")
    assert len(stations) == 2
    assert stations[0] == Station(prefix=None, value=0, original="0+00")
    assert stations[1] == Station(prefix=None, value=1250, original="12+50")


def test_parse_stations_returns_empty_for_no_match():
    assert parse_stations("just plain text with no stations") == []


def test_parse_stations_does_not_match_phone_numbers():
    # 555-1234 looks vaguely station-y but has no '+' separator
    assert parse_stations("Call 555-1234") == []
```

Save to `~/.claude/skills/plan-sheet-endpoints/tests/test_station_parser.py`.

- [ ] **Step 2: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_station_parser.py -v
```

Expected: ImportError on first test (`scripts.station_parser` does not exist).

- [ ] **Step 3: Implement `station_parser.py`**

```python
# scripts/station_parser.py
"""Parse construction-drawing station markers like 'B 21+37' or 'STA 5+00'."""
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Station:
    prefix: Optional[str]   # e.g. "B", "STA", or None for bare "21+37"
    value: int              # position along route in feet (21+37 → 2137)
    original: str           # the matched substring


_PREFIXED_RE = re.compile(
    r"\b(?P<prefix>STA(?:TION)?|[A-Z])\s+(?P<station>\d{1,4}\+\d{2}(?:\.\d+)?)",
    re.IGNORECASE,
)

_BARE_RE = re.compile(r"\b(?P<station>\d{1,4}\+\d{2}(?:\.\d+)?)\b")


def station_to_value(station_text: str) -> int:
    """Convert '21+37' or '21+37.5' to feet (2137). Truncates fractional feet."""
    plus_split = station_text.split("+", 1)
    hundreds = int(plus_split[0])
    feet = float(plus_split[1])
    return hundreds * 100 + int(feet)


def parse_stations(text: str) -> List[Station]:
    """Find all station markers in text. Prefixed forms take priority over bare."""
    found: List[Station] = []
    consumed_spans: List[tuple] = []

    for m in _PREFIXED_RE.finditer(text):
        prefix = m.group("prefix").upper()
        station = m.group("station")
        found.append(Station(prefix=prefix, value=station_to_value(station), original=m.group(0)))
        consumed_spans.append(m.span())

    for m in _BARE_RE.finditer(text):
        # Skip bare matches that overlap a prefixed match
        if any(start <= m.start() < end for start, end in consumed_spans):
            continue
        station = m.group("station")
        found.append(Station(prefix=None, value=station_to_value(station), original=m.group(0)))

    return found
```

Save to `~/.claude/skills/plan-sheet-endpoints/scripts/station_parser.py`.

- [ ] **Step 4: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_station_parser.py -v
```

Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/station_parser.py tests/test_station_parser.py
git commit -m "feat: parse station markers into numeric values"
```

---

## Task 7: `sheet_id_parser` — sheet IDs and continuation references

**Files:**
- Create: `~/.claude/skills/plan-sheet-endpoints/scripts/sheet_id_parser.py`
- Create: `~/.claude/skills/plan-sheet-endpoints/tests/test_sheet_id_parser.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_sheet_id_parser.py
from scripts.sheet_id_parser import (
    ContinuationRef,
    parse_continuation_refs,
    parse_sheet_id,
)


def test_parse_sheet_id_sheet_n_of_m():
    assert parse_sheet_id("SHEET 12 OF 25") == "12"


def test_parse_sheet_id_site_plan_dash_n():
    assert parse_sheet_id("SITE PLAN - 5") == "5"


def test_parse_sheet_id_sp_n():
    assert parse_sheet_id("SP-12") == "12"


def test_parse_sheet_id_s_dash_n():
    assert parse_sheet_id("S-3") == "3"


def test_parse_sheet_id_returns_none_for_no_match():
    assert parse_sheet_id("just some text with no sheet identifier") is None


def test_parse_continuation_refs_match_to_sheet():
    refs = parse_continuation_refs("MATCH TO SHEET 11")
    assert len(refs) == 1
    assert refs[0] == ContinuationRef(direction="to", target="11", original="MATCH TO SHEET 11")


def test_parse_continuation_refs_see_sheet():
    refs = parse_continuation_refs("SEE SHEET 5")
    assert refs[0].direction == "to"
    assert refs[0].target == "5"


def test_parse_continuation_refs_match_to_site_plan_dash_n():
    refs = parse_continuation_refs("MATCH TO SITE PLAN - 12")
    assert refs[0].target == "12"
    assert refs[0].direction == "to"


def test_parse_continuation_refs_continued_from():
    refs = parse_continuation_refs("CONTINUED FROM SHEET 7")
    assert refs[0].direction == "from"
    assert refs[0].target == "7"


def test_parse_continuation_refs_multiple_in_one_text():
    text = "MATCH TO SHEET 11. CONTINUED FROM SHEET 9."
    refs = parse_continuation_refs(text)
    assert len(refs) == 2
    targets = {r.target for r in refs}
    assert targets == {"11", "9"}


def test_parse_continuation_refs_returns_empty_for_no_match():
    assert parse_continuation_refs("plain text") == []
```

Save to `~/.claude/skills/plan-sheet-endpoints/tests/test_sheet_id_parser.py`.

- [ ] **Step 2: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_sheet_id_parser.py -v
```

Expected: ImportError on first test.

- [ ] **Step 3: Implement `sheet_id_parser.py`**

```python
# scripts/sheet_id_parser.py
"""Parse sheet identifiers and continuation references from CD-page text."""
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ContinuationRef:
    direction: str   # "from", "to", or "unknown"
    target: str
    original: str


_SHEET_ID_PATTERNS = [
    re.compile(r"SHEET\s*[#\-]?\s*(\w+)\s+OF\s+\w+", re.IGNORECASE),
    re.compile(r"SITE\s+PLAN\s*[#\-]?\s*(\w+)", re.IGNORECASE),
    re.compile(r"\bSP\s*[#\-]\s*(\w+)", re.IGNORECASE),
    re.compile(r"\bS\s*-\s*(\w+)\b", re.IGNORECASE),
    re.compile(r"SHEET\s*[#\-]?\s*(\w+)", re.IGNORECASE),
]


def parse_sheet_id(text: str) -> Optional[str]:
    """Return the first sheet identifier found, else None.

    Patterns are first-match-wins, ordered by specificity:
      "SHEET 12 OF 25" -> "12"
      "SITE PLAN - 5"  -> "5"
      "SP-12"          -> "12"
      "S-3"            -> "3"
      "SHEET 7"        -> "7"
    """
    for pattern in _SHEET_ID_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1)
    return None


_TO_RE = re.compile(
    r"(?:MATCH(?:LINE)?\s+TO|SEE|GO\s+TO|CONTINUED?\s+ON)\s+"
    r"(?:SHEET|SITE\s+PLAN|SP)\s*[#\-]?\s*(?P<target>\w+)",
    re.IGNORECASE,
)

_FROM_RE = re.compile(
    r"(?:CONTINUED?\s+FROM|FROM)\s+"
    r"(?:SHEET|SITE\s+PLAN|SP)\s*[#\-]?\s*(?P<target>\w+)",
    re.IGNORECASE,
)


def parse_continuation_refs(text: str) -> List[ContinuationRef]:
    """Find all match/continuation references. Returns list (possibly empty)."""
    refs: List[ContinuationRef] = []

    for m in _FROM_RE.finditer(text):
        refs.append(ContinuationRef(direction="from", target=m.group("target"), original=m.group(0)))

    for m in _TO_RE.finditer(text):
        # Skip if this match is contained in a from-match we already added
        if any(r.original == m.group(0) for r in refs):
            continue
        refs.append(ContinuationRef(direction="to", target=m.group("target"), original=m.group(0)))

    return refs
```

Save to `~/.claude/skills/plan-sheet-endpoints/scripts/sheet_id_parser.py`.

- [ ] **Step 4: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_sheet_id_parser.py -v
```

Expected: `11 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/sheet_id_parser.py tests/test_sheet_id_parser.py
git commit -m "feat: parse sheet IDs and continuation references"
```

---

## Task 8: `feature_parsers` — roads, structures, spans, construction type, cable specs

**Files:**
- Create: `~/.claude/skills/plan-sheet-endpoints/scripts/feature_parsers.py`
- Create: `~/.claude/skills/plan-sheet-endpoints/tests/test_feature_parsers.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_feature_parsers.py
from scripts.feature_parsers import (
    parse_cable_specs,
    parse_construction_type,
    parse_road_names,
    parse_span_lengths,
    parse_structures,
)


def test_parse_road_names_finds_common_suffixes():
    text = "Route along E 250 N RD, crossing MAIN ST and OAK AVE"
    roads = parse_road_names(text)
    assert "E 250 N RD" in roads
    assert "MAIN ST" in roads
    assert "OAK AVE" in roads


def test_parse_road_names_returns_empty_for_no_match():
    assert parse_road_names("no street suffixes here") == []


def test_parse_road_names_deduplicates():
    text = "MAIN ST runs into MAIN ST"
    assert parse_road_names(text) == ["MAIN ST"]


def test_parse_structures_pole_n():
    structures = parse_structures("POLE 32, POLE 33, P-15, STR #42")
    assert "POLE 32" in structures
    assert "POLE 33" in structures
    assert "P-15" in structures
    assert "STR #42" in structures


def test_parse_structures_returns_empty():
    assert parse_structures("no structures here") == []


def test_parse_span_lengths_apostrophe_form():
    spans = parse_span_lengths("260' span, then 316' to next pole")
    assert 260.0 in spans
    assert 316.0 in spans


def test_parse_span_lengths_ft_form():
    spans = parse_span_lengths("Span: 260 FT followed by 316 ft")
    assert 260.0 in spans
    assert 316.0 in spans


def test_parse_span_lengths_returns_empty():
    assert parse_span_lengths("no measurements") == []


def test_parse_construction_type_aerial():
    assert parse_construction_type("OVERLASH ON EXISTING STRAND, AERIAL ROUTE") == "aerial"


def test_parse_construction_type_underground():
    assert parse_construction_type("BORE AND PLACE 2\" CONDUIT, UNDERGROUND") == "underground"


def test_parse_construction_type_direct_bore():
    assert parse_construction_type("DIRECTIONAL BORE under highway") == "direct_bore"


def test_parse_construction_type_trench():
    assert parse_construction_type("OPEN TRENCH along right-of-way") == "trench"


def test_parse_construction_type_returns_none():
    assert parse_construction_type("plain descriptive text") is None


def test_parse_cable_specs_fiber_count():
    assert parse_cable_specs("288F SM FIBER") == "288F"


def test_parse_cable_specs_count_form():
    assert parse_cable_specs("Place 144 COUNT cable") == "144 COUNT"


def test_parse_cable_specs_returns_none():
    assert parse_cable_specs("nothing fiber-y") is None
```

Save to `~/.claude/skills/plan-sheet-endpoints/tests/test_feature_parsers.py`.

- [ ] **Step 2: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_feature_parsers.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `feature_parsers.py`**

```python
# scripts/feature_parsers.py
"""Per-sheet feature regex extractors: roads, structures, spans, construction type, cable specs."""
import re
from typing import List, Optional


_ROAD_SUFFIXES = (
    "RD", "ROAD", "ST", "STREET", "AVE", "AVENUE", "BLVD", "BOULEVARD",
    "CT", "COURT", "DR", "DRIVE", "LN", "LANE", "PKWY", "HWY", "HIGHWAY",
    "WAY", "TER", "TERRACE", "CIR", "CIRCLE", "PL", "PLACE",
)

_ROAD_RE = re.compile(
    r"\b(?P<name>[A-Z][A-Z0-9 \-]{1,40}?\s+(?:" + "|".join(_ROAD_SUFFIXES) + r"))\b"
)


def parse_road_names(text: str) -> List[str]:
    """Find all road/street names in text (deduplicated, original casing preserved)."""
    seen = []
    for m in _ROAD_RE.finditer(text):
        name = m.group("name").strip()
        if name not in seen:
            seen.append(name)
    return seen


_STRUCTURE_RE = re.compile(
    r"\b(?:POLE\s*\d+|P-\d+|STR\s*#?\s*\d+|STRUCTURE\s*\d+|MH\s*\d+|VLT\s*\d+|VAULT\s*\d+)\b",
    re.IGNORECASE,
)


def parse_structures(text: str) -> List[str]:
    """Find all structure/pole/vault labels (deduplicated, original casing preserved)."""
    seen = []
    for m in _STRUCTURE_RE.finditer(text):
        s = m.group(0).upper().replace("  ", " ").strip()
        if s not in seen:
            seen.append(s)
    return seen


_SPAN_RE = re.compile(r"\b(?P<feet>\d{2,4})\s*(?:'|FT|FEET)\b", re.IGNORECASE)


def parse_span_lengths(text: str) -> List[float]:
    """Find all span/length annotations as feet."""
    spans = []
    for m in _SPAN_RE.finditer(text):
        feet = float(m.group("feet"))
        if 10.0 <= feet <= 5000.0:  # reject obvious non-spans
            spans.append(feet)
    return spans


_CONSTRUCTION_KEYWORDS = [
    ("direct_bore", re.compile(r"\b(?:DIR(?:ECTIONAL)?\s+BORE|HDD)\b", re.IGNORECASE)),
    ("trench", re.compile(r"\bOPEN\s+TRENCH|\bTRENCH\b", re.IGNORECASE)),
    ("underground", re.compile(r"\b(?:UNDERGROUND|UG\b|BORE|CONDUIT|DUCT)\b", re.IGNORECASE)),
    ("overlash", re.compile(r"\bOVERLASH\b", re.IGNORECASE)),
    ("aerial", re.compile(r"\bAERIAL\b", re.IGNORECASE)),
]


def parse_construction_type(text: str) -> Optional[str]:
    """Pick the most specific construction-type keyword found.

    Priority order: direct_bore > trench > underground > overlash > aerial.
    Direct bore wins over generic underground; overlash and aerial both signal
    aerial construction but overlash is the more specific Comcast term so it wins.
    """
    for label, pattern in _CONSTRUCTION_KEYWORDS:
        if pattern.search(text):
            if label == "overlash":
                return "aerial"
            return label
    return None


_CABLE_RE_FIBER_F = re.compile(r"\b(?P<count>\d{2,4})F\b")
_CABLE_RE_FIBER_COUNT = re.compile(r"\b(?P<count>\d{2,4})\s+COUNT\b", re.IGNORECASE)
_CABLE_RE_OPGW = re.compile(r"\b(?:OPGW|ADSS)\b", re.IGNORECASE)


def parse_cable_specs(text: str) -> Optional[str]:
    """Best-effort cable spec string. Picks the first matching pattern."""
    m = _CABLE_RE_FIBER_F.search(text)
    if m:
        return f"{m.group('count')}F"
    m = _CABLE_RE_FIBER_COUNT.search(text)
    if m:
        return f"{m.group('count')} COUNT"
    m = _CABLE_RE_OPGW.search(text)
    if m:
        return m.group(0).upper()
    return None
```

Save to `~/.claude/skills/plan-sheet-endpoints/scripts/feature_parsers.py`.

- [ ] **Step 4: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_feature_parsers.py -v
```

Expected: `15 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/feature_parsers.py tests/test_feature_parsers.py
git commit -m "feat: per-sheet feature parsers (roads, structures, spans, type, cable)"
```

---

## Task 9: `page_text` — PyMuPDF wrapper and raster detection

**Files:**
- Create: `~/.claude/skills/plan-sheet-endpoints/scripts/page_text.py`
- Create: `~/.claude/skills/plan-sheet-endpoints/tests/conftest.py`
- Create: `~/.claude/skills/plan-sheet-endpoints/tests/test_page_text.py`

- [ ] **Step 1: Write the conftest fixtures**

```python
# tests/conftest.py
"""Pytest fixtures: synthetic PDFs generated programmatically with PyMuPDF.

We build small, deterministic PDFs at test time. Each fixture returns a path
to a temporary .pdf the test can read.
"""
from pathlib import Path
from typing import List, Tuple

import fitz
import pytest


def _make_pdf(tmp_path: Path, name: str, pages: List[List[Tuple[float, float, str]]]) -> Path:
    """Create a PDF where `pages[i]` is a list of (x, y, text) entries for page i+1."""
    doc = fitz.open()
    for entries in pages:
        page = doc.new_page(width=1224, height=792)  # 17"x11" landscape
        for x, y, text in entries:
            page.insert_text((x, y), text, fontsize=10)
    out = tmp_path / name
    doc.save(out)
    doc.close()
    return out


@pytest.fixture
def text_only_pdf(tmp_path: Path) -> Path:
    """Single page with a few text strings — no images."""
    return _make_pdf(tmp_path, "text_only.pdf", [[
        (50, 50, "Hello world"),
        (50, 80, "STA 5+00"),
        (50, 110, "Lat: 34.123456 Lon: -118.123456"),
    ]])


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    """Single blank page (no text, no images) — should look raster to detector."""
    return _make_pdf(tmp_path, "empty.pdf", [[]])


@pytest.fixture
def plan_sheet_pdf(tmp_path: Path) -> Path:
    """A page that should classify as PLAN_PROFILE: stations, structures, match line, road."""
    return _make_pdf(tmp_path, "plan_sheet.pdf", [[
        (50, 50, "SITE PLAN - 5"),
        (50, 80, "STA 0+00"),
        (200, 80, "STA 12+50"),
        (50, 110, "POLE 32"),
        (200, 110, "POLE 35"),
        (350, 80, "MATCH TO SHEET 6"),
        (50, 140, "MAIN ST"),
        (250, 140, "260' SPAN"),
        (450, 140, "OVERLASH ON EXISTING STRAND"),
        (50, 170, "LAT: 34.123456 LON: -118.123456"),
    ]])


@pytest.fixture
def cover_sheet_pdf(tmp_path: Path) -> Path:
    """A cover page — should classify as COVER, not PLAN_PROFILE."""
    return _make_pdf(tmp_path, "cover.pdf", [[
        (200, 50, "COVER SHEET"),
        (200, 80, "FIBER OPTIC CONSTRUCTION DRAWINGS"),
        (200, 110, "MASTEC COMMUNICATIONS GROUP"),
        (200, 140, "PROJECT: PERU UTILITIES JB123"),
    ]])


@pytest.fixture
def vicinity_pdf(tmp_path: Path) -> Path:
    """A vicinity/overview map page — should classify as VICINITY, not PLAN_PROFILE."""
    return _make_pdf(tmp_path, "vicinity.pdf", [[
        (200, 50, "VICINITY MAP"),
        (200, 80, "OVERVIEW"),
        (200, 110, "Project Site Reference"),
        (200, 140, "LAT: 34.123456 LON: -118.123456"),
    ]])


@pytest.fixture
def multi_page_pdf(tmp_path: Path) -> Path:
    """Cover + vicinity + 2 plan sheets + legend — typical CD package."""
    return _make_pdf(tmp_path, "multi.pdf", [
        # Page 1: Cover
        [(200, 50, "COVER SHEET"), (200, 80, "FIBER CONSTRUCTION")],
        # Page 2: Vicinity
        [(200, 50, "VICINITY MAP"), (200, 80, "Reference 34.10000, -118.10000")],
        # Page 3: Plan sheet 1
        [(50, 50, "SITE PLAN - 1"), (50, 80, "STA 0+00"), (200, 80, "STA 12+50"),
         (50, 110, "POLE 1"), (200, 110, "POLE 5"), (350, 80, "MATCH TO SHEET 4"),
         (50, 140, "MAIN ST"), (50, 170, "LAT: 34.20000 LON: -118.20000")],
        # Page 4: Plan sheet 2
        [(50, 50, "SITE PLAN - 2"), (50, 80, "STA 12+50"), (200, 80, "STA 25+00"),
         (50, 110, "POLE 6"), (200, 110, "POLE 10"), (350, 80, "MATCH TO SHEET 3"),
         (50, 140, "OAK AVE"), (50, 170, "BORE AND PLACE 2\" CONDUIT")],
        # Page 5: Legend
        [(200, 50, "LEGEND"), (200, 80, "SYMBOLS"), (200, 110, "AERIAL FIBER")],
    ])
```

Save to `~/.claude/skills/plan-sheet-endpoints/tests/conftest.py`.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_page_text.py
from pathlib import Path

import fitz

from scripts.page_text import TextBlock, get_page_text, get_text_blocks, is_raster_page


def test_get_page_text_returns_concatenated_text(text_only_pdf: Path):
    doc = fitz.open(text_only_pdf)
    text = get_page_text(doc[0])
    assert "Hello world" in text
    assert "STA 5+00" in text
    assert "34.123456" in text
    doc.close()


def test_get_text_blocks_returns_positioned_blocks(text_only_pdf: Path):
    doc = fitz.open(text_only_pdf)
    blocks = get_text_blocks(doc[0])
    assert len(blocks) >= 1
    assert all(isinstance(b, TextBlock) for b in blocks)
    # First block should contain "Hello world" and have sane coordinates
    hello = [b for b in blocks if "Hello world" in b.text]
    assert len(hello) == 1
    assert hello[0].x0 < hello[0].x1
    assert hello[0].y0 < hello[0].y1
    doc.close()


def test_is_raster_page_returns_false_for_text_pdf(text_only_pdf: Path):
    doc = fitz.open(text_only_pdf)
    assert is_raster_page(doc[0]) is False
    doc.close()


def test_is_raster_page_returns_true_for_empty_page(empty_pdf: Path):
    doc = fitz.open(empty_pdf)
    assert is_raster_page(doc[0]) is True
    doc.close()
```

Save to `~/.claude/skills/plan-sheet-endpoints/tests/test_page_text.py`.

- [ ] **Step 3: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_page_text.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement `page_text.py`**

```python
# scripts/page_text.py
"""PyMuPDF wrappers: page text, positioned blocks, raster-page detection."""
from dataclasses import dataclass
from typing import List

import fitz


@dataclass(frozen=True)
class TextBlock:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


def get_page_text(page: fitz.Page) -> str:
    """Return all extractable text on the page, joined with spaces."""
    return page.get_text("text")


def get_text_blocks(page: fitz.Page) -> List[TextBlock]:
    """Return one TextBlock per PyMuPDF block (text-bearing only)."""
    raw_blocks = page.get_text("blocks")
    out: List[TextBlock] = []
    for b in raw_blocks:
        # Tuple shape: (x0, y0, x1, y1, text, block_no, block_type)
        # block_type 0 == text, 1 == image
        if len(b) < 6:
            continue
        x0, y0, x1, y1, text, *_rest = b
        block_type = b[6] if len(b) >= 7 else 0
        if block_type != 0:
            continue
        text_str = (text or "").strip()
        if not text_str:
            continue
        out.append(TextBlock(text=text_str, x0=float(x0), y0=float(y0), x1=float(x1), y1=float(y1)))
    return out


_RASTER_TEXT_THRESHOLD = 30   # chars; below this and the page is functionally raster


def is_raster_page(page: fitz.Page) -> bool:
    """Return True if the page has effectively no extractable text.

    A scanned-image page reports near-zero text from PyMuPDF; that is the
    signal we use rather than inspecting embedded images directly, because
    a hybrid page (image background + sparse text overlay) is still useful.
    """
    text = get_page_text(page).strip()
    return len(text) < _RASTER_TEXT_THRESHOLD
```

Save to `~/.claude/skills/plan-sheet-endpoints/scripts/page_text.py`.

- [ ] **Step 5: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_page_text.py -v
```

Expected: `4 passed`.

- [ ] **Step 6: Commit**

```bash
git add scripts/page_text.py tests/conftest.py tests/test_page_text.py
git commit -m "feat: PyMuPDF text extraction and raster-page detection"
```

---

## Task 10: `page_classifier`

**Files:**
- Create: `~/.claude/skills/plan-sheet-endpoints/scripts/page_classifier.py`
- Create: `~/.claude/skills/plan-sheet-endpoints/tests/test_page_classifier.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_page_classifier.py
from pathlib import Path

import fitz

from scripts.page_classifier import PageType, classify_page
from scripts.page_text import get_page_text, get_text_blocks


def _classify(pdf_path: Path, page_index: int = 0) -> PageType:
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    text = get_page_text(page)
    blocks = get_text_blocks(page)
    result = classify_page(text, blocks)
    doc.close()
    return result


def test_classify_plan_sheet(plan_sheet_pdf: Path):
    assert _classify(plan_sheet_pdf) == PageType.PLAN_PROFILE


def test_classify_cover_sheet(cover_sheet_pdf: Path):
    assert _classify(cover_sheet_pdf) == PageType.COVER


def test_classify_vicinity_map(vicinity_pdf: Path):
    assert _classify(vicinity_pdf) == PageType.VICINITY


def test_classify_empty_page_is_raster(empty_pdf: Path):
    assert _classify(empty_pdf) == PageType.RASTER


def test_classify_multi_page_pdf(multi_page_pdf: Path):
    assert _classify(multi_page_pdf, 0) == PageType.COVER
    assert _classify(multi_page_pdf, 1) == PageType.VICINITY
    assert _classify(multi_page_pdf, 2) == PageType.PLAN_PROFILE
    assert _classify(multi_page_pdf, 3) == PageType.PLAN_PROFILE
    assert _classify(multi_page_pdf, 4) == PageType.LEGEND
```

Save to `~/.claude/skills/plan-sheet-endpoints/tests/test_page_classifier.py`.

- [ ] **Step 2: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_page_classifier.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `page_classifier.py`**

```python
# scripts/page_classifier.py
"""Score-based page classifier for CD pages.

Each page text is scored against keyword rules for each PageType. The
highest-scoring type with a score >= MIN_SCORE wins; otherwise OTHER.

The classifier is intentionally permissive: the goal is to keep clearly
non-plan-profile pages out of the per-sheet output, not to perfectly tag
every page.
"""
import re
from enum import Enum
from typing import List

from scripts.page_text import TextBlock
from scripts.sheet_id_parser import parse_continuation_refs
from scripts.station_parser import parse_stations


class PageType(str, Enum):
    PLAN_PROFILE = "plan_profile"
    COVER = "cover"
    VICINITY = "vicinity"
    LEGEND = "legend"
    NOTES = "notes"
    DETAIL = "detail"
    TRAFFIC_CONTROL = "traffic_control"
    RASTER = "raster"
    OTHER = "other"


_MIN_SCORE = 3


_KEYWORD_RULES = {
    PageType.COVER: [
        (re.compile(r"\bCOVER\s+SHEET\b", re.IGNORECASE), 5),
        (re.compile(r"\bTITLE\s+SHEET\b", re.IGNORECASE), 5),
        (re.compile(r"\bCONSTRUCTION\s+DRAWINGS?\b", re.IGNORECASE), 2),
    ],
    PageType.VICINITY: [
        (re.compile(r"\bVICINITY\b", re.IGNORECASE), 5),
        (re.compile(r"\bOVERVIEW(?:\s+MAP)?\b", re.IGNORECASE), 4),
        (re.compile(r"\bINDEX\s+OF\s+SHEETS\b", re.IGNORECASE), 3),
        (re.compile(r"\bKEY\s+MAP\b", re.IGNORECASE), 4),
    ],
    PageType.LEGEND: [
        (re.compile(r"\bLEGEND\b", re.IGNORECASE), 5),
        (re.compile(r"\bSYMBOLS?\b", re.IGNORECASE), 3),
        (re.compile(r"\bABBREVIATIONS?\b", re.IGNORECASE), 3),
    ],
    PageType.NOTES: [
        (re.compile(r"\bGENERAL\s+NOTES\b", re.IGNORECASE), 5),
        (re.compile(r"\bCONSTRUCTION\s+NOTES\b", re.IGNORECASE), 5),
        (re.compile(r"\bSPECIFICATIONS?\b", re.IGNORECASE), 2),
    ],
    PageType.DETAIL: [
        (re.compile(r"\bTYPICAL\s+DETAILS?\b", re.IGNORECASE), 5),
        (re.compile(r"\bDETAIL\s+SHEET\b", re.IGNORECASE), 5),
        (re.compile(r"\bSTANDARD\s+DETAILS?\b", re.IGNORECASE), 4),
    ],
    PageType.TRAFFIC_CONTROL: [
        (re.compile(r"\bTRAFFIC\s+CONTROL\b", re.IGNORECASE), 5),
        (re.compile(r"\bMAINTENANCE\s+OF\s+TRAFFIC\b", re.IGNORECASE), 5),
        (re.compile(r"\bMOT\b", re.IGNORECASE), 3),
        (re.compile(r"\bMUTCD\b", re.IGNORECASE), 3),
    ],
}


def _score_plan_profile(text: str, blocks: List[TextBlock]) -> int:
    """Plan-profile heuristic: stations + match refs + structures."""
    score = 0
    stations = parse_stations(text)
    score += min(len(stations), 4) * 2  # cap at 8 from stations alone

    refs = parse_continuation_refs(text)
    score += min(len(refs), 2) * 2

    # Structures (rough count)
    structure_re = re.compile(r"\b(?:POLE\s*\d+|P-\d+|STR\s*#?\s*\d+)\b", re.IGNORECASE)
    score += min(len(structure_re.findall(text)), 4)

    # Penalty for clear non-plan keywords
    for penalty_re, penalty in (
        (re.compile(r"\bCOVER\s+SHEET\b", re.IGNORECASE), -10),
        (re.compile(r"\bVICINITY\b", re.IGNORECASE), -10),
        (re.compile(r"\bOVERVIEW(?:\s+MAP)?\b", re.IGNORECASE), -10),
        (re.compile(r"\bGENERAL\s+NOTES\b", re.IGNORECASE), -10),
        (re.compile(r"\bTYPICAL\s+DETAILS?\b", re.IGNORECASE), -10),
        (re.compile(r"\bTRAFFIC\s+CONTROL\b", re.IGNORECASE), -10),
        (re.compile(r"\bLEGEND\b", re.IGNORECASE), -10),
    ):
        if penalty_re.search(text):
            score += penalty

    return score


def classify_page(text: str, blocks: List[TextBlock]) -> PageType:
    """Return the most likely PageType for this page."""
    if not text or len(text.strip()) < 30:
        return PageType.RASTER

    scores = {pt: 0 for pt in PageType if pt not in (PageType.OTHER, PageType.RASTER)}

    for pt, rules in _KEYWORD_RULES.items():
        for pattern, weight in rules:
            if pattern.search(text):
                scores[pt] += weight

    scores[PageType.PLAN_PROFILE] = _score_plan_profile(text, blocks)

    best = max(scores.items(), key=lambda kv: kv[1])
    if best[1] >= _MIN_SCORE:
        return best[0]
    return PageType.OTHER
```

Save to `~/.claude/skills/plan-sheet-endpoints/scripts/page_classifier.py`.

- [ ] **Step 4: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_page_classifier.py -v
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/page_classifier.py tests/test_page_classifier.py
git commit -m "feat: score-based page-type classifier"
```

---

## Task 11: `sheet_extractor` — orchestrate per-sheet extraction

**Files:**
- Create: `~/.claude/skills/plan-sheet-endpoints/scripts/sheet_extractor.py`
- Create: `~/.claude/skills/plan-sheet-endpoints/tests/test_sheet_extractor.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_sheet_extractor.py
from pathlib import Path

import fitz
import pytest

from scripts.page_text import get_page_text, get_text_blocks
from scripts.sheet_extractor import (
    SheetData,
    VicinityCoord,
    extract_sheet,
    extract_vicinity_coords,
)


def _open_first_page(pdf_path: Path):
    doc = fitz.open(pdf_path)
    page = doc[0]
    text = get_page_text(page)
    blocks = get_text_blocks(page)
    return doc, page, text, blocks


def test_extract_sheet_full_plan(plan_sheet_pdf: Path):
    doc, page, text, blocks = _open_first_page(plan_sheet_pdf)
    sheet = extract_sheet(page, page_number=1, text=text, blocks=blocks)
    doc.close()

    assert sheet.page_number == 1
    assert sheet.sheet_id == "5"
    assert sheet.start_station == "0+00" or sheet.start_station == "STA 0+00"
    assert sheet.end_station == "12+50" or sheet.end_station == "STA 12+50"
    assert "POLE 32" in sheet.structures
    assert "POLE 35" in sheet.structures
    assert "MAIN ST" in sheet.road_names
    assert 260.0 in sheet.span_lengths_ft
    assert sheet.construction_type == "aerial"
    assert sheet.continues_to_sheet == "6"
    assert sheet.has_native_gps is True
    assert sheet.coords_source == "printed_on_this_sheet"
    assert sheet.start_lat == pytest.approx(34.123456, abs=1e-4)
    assert sheet.start_lon == pytest.approx(-118.123456, abs=1e-4)


def test_extract_sheet_no_coords_marks_none(tmp_path: Path):
    """A sheet with stations but no coordinates: has_native_gps must be False."""
    doc = fitz.open()
    page = doc.new_page(width=1224, height=792)
    page.insert_text((50, 50), "SITE PLAN - 7", fontsize=10)
    page.insert_text((50, 80), "STA 0+00", fontsize=10)
    page.insert_text((200, 80), "STA 5+00", fontsize=10)
    page.insert_text((50, 110), "POLE 1", fontsize=10)
    out = tmp_path / "no_coords.pdf"
    doc.save(out)
    doc.close()

    doc = fitz.open(out)
    page = doc[0]
    text = get_page_text(page)
    blocks = get_text_blocks(page)
    sheet = extract_sheet(page, page_number=1, text=text, blocks=blocks)
    doc.close()

    assert sheet.has_native_gps is False
    assert sheet.coords_source == "none"
    assert sheet.start_lat is None
    assert sheet.start_lon is None
    assert sheet.end_lat is None
    assert sheet.end_lon is None


def test_extract_vicinity_coords(vicinity_pdf: Path):
    doc, page, text, blocks = _open_first_page(vicinity_pdf)
    coords = extract_vicinity_coords(page, page_number=1, page_type="vicinity", text=text)
    doc.close()

    assert len(coords) == 1
    assert isinstance(coords[0], VicinityCoord)
    assert coords[0].lat == pytest.approx(34.123456, abs=1e-4)
    assert coords[0].lon == pytest.approx(-118.123456, abs=1e-4)
    assert coords[0].page_type == "vicinity"
```

Save to `~/.claude/skills/plan-sheet-endpoints/tests/test_sheet_extractor.py`.

- [ ] **Step 2: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_sheet_extractor.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `sheet_extractor.py`**

```python
# scripts/sheet_extractor.py
"""Per-page extraction: combine all parsers into SheetData / VicinityCoord."""
from dataclasses import dataclass, field
from typing import List, Optional

import fitz

from scripts.coord_parser import find_all_coords
from scripts.feature_parsers import (
    parse_cable_specs,
    parse_construction_type,
    parse_road_names,
    parse_span_lengths,
    parse_structures,
)
from scripts.page_text import TextBlock
from scripts.sheet_id_parser import parse_continuation_refs, parse_sheet_id
from scripts.station_parser import parse_stations


@dataclass
class SheetData:
    page_number: int
    sheet_id: Optional[str] = None
    start_label: Optional[str] = None
    start_station: Optional[str] = None
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    end_label: Optional[str] = None
    end_station: Optional[str] = None
    end_lat: Optional[float] = None
    end_lon: Optional[float] = None
    road_names: List[str] = field(default_factory=list)
    structures: List[str] = field(default_factory=list)
    span_lengths_ft: List[float] = field(default_factory=list)
    construction_type: Optional[str] = None
    cable_specs: Optional[str] = None
    continues_from_sheet: Optional[str] = None
    continues_to_sheet: Optional[str] = None
    coords_source: str = "none"
    has_native_gps: bool = False


@dataclass
class VicinityCoord:
    page_number: int
    page_type: str
    lat: float
    lon: float
    note: str = ""


def extract_sheet(page: fitz.Page, page_number: int, text: str, blocks: List[TextBlock]) -> SheetData:
    """Build SheetData from a plan-profile page.

    The function is best-effort: any field that can't be extracted stays None
    (or empty list). It never raises on missing data.
    """
    sheet = SheetData(page_number=page_number)

    sheet.sheet_id = parse_sheet_id(text)

    stations = parse_stations(text)
    if stations:
        stations_sorted = sorted(stations, key=lambda s: s.value)
        sheet.start_station = stations_sorted[0].original
        sheet.end_station = stations_sorted[-1].original
        sheet.start_label = stations_sorted[0].original
        sheet.end_label = stations_sorted[-1].original

    coords = find_all_coords(text)
    if coords:
        sheet.has_native_gps = True
        sheet.coords_source = "printed_on_this_sheet"
        sheet.start_lat, sheet.start_lon = coords[0][0], coords[0][1]
        if len(coords) >= 2:
            sheet.end_lat, sheet.end_lon = coords[1][0], coords[1][1]

    sheet.road_names = parse_road_names(text)
    sheet.structures = parse_structures(text)
    if sheet.structures and not sheet.start_label:
        sheet.start_label = sheet.structures[0]
        sheet.end_label = sheet.structures[-1]

    sheet.span_lengths_ft = parse_span_lengths(text)
    sheet.construction_type = parse_construction_type(text)
    sheet.cable_specs = parse_cable_specs(text)

    refs = parse_continuation_refs(text)
    for r in refs:
        if r.direction == "from":
            sheet.continues_from_sheet = r.target
        elif r.direction == "to":
            sheet.continues_to_sheet = r.target

    return sheet


def extract_vicinity_coords(
    page: fitz.Page, page_number: int, page_type: str, text: str
) -> List[VicinityCoord]:
    """Pull every coord pair from a non-plan page, tagged for the vicinity_reference CSV."""
    coords = find_all_coords(text)
    return [
        VicinityCoord(
            page_number=page_number,
            page_type=page_type,
            lat=lat,
            lon=lon,
            note=fmt,
        )
        for lat, lon, fmt in coords
    ]
```

Save to `~/.claude/skills/plan-sheet-endpoints/scripts/sheet_extractor.py`.

- [ ] **Step 4: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_sheet_extractor.py -v
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/sheet_extractor.py tests/test_sheet_extractor.py
git commit -m "feat: per-sheet extraction orchestrator"
```

---

## Task 12: `pdf_processor` — single PDF and folder of PDFs

**Files:**
- Create: `~/.claude/skills/plan-sheet-endpoints/scripts/pdf_processor.py`
- Create: `~/.claude/skills/plan-sheet-endpoints/tests/test_pdf_processor.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pdf_processor.py
from pathlib import Path

import fitz

from scripts.pdf_processor import PdfResult, process_input, process_pdf


def test_process_pdf_classifies_each_page(multi_page_pdf: Path):
    result = process_pdf(multi_page_pdf)
    assert isinstance(result, PdfResult)
    assert result.pdf_file == multi_page_pdf.name

    # Two plan sheets (pages 3 and 4)
    assert len(result.sheets) == 2
    assert {s.page_number for s in result.sheets} == {3, 4}

    # One vicinity coord (page 2)
    assert len(result.vicinity_coords) == 1
    assert result.vicinity_coords[0].page_number == 2

    # No raster pages in this fixture
    assert result.raster_pages == []


def test_process_pdf_flags_raster_pages(tmp_path: Path):
    doc = fitz.open()
    doc.new_page(width=1224, height=792)  # blank page → raster
    out = tmp_path / "raster.pdf"
    doc.save(out)
    doc.close()

    result = process_pdf(out)
    assert result.raster_pages == [1]
    assert result.sheets == []


def test_process_input_single_pdf(multi_page_pdf: Path):
    results = process_input(multi_page_pdf)
    assert len(results) == 1
    assert results[0].pdf_file == multi_page_pdf.name


def test_process_input_folder(multi_page_pdf: Path, plan_sheet_pdf: Path, tmp_path: Path):
    folder = tmp_path / "pdfs"
    folder.mkdir()
    (folder / "a.pdf").write_bytes(multi_page_pdf.read_bytes())
    (folder / "b.pdf").write_bytes(plan_sheet_pdf.read_bytes())

    results = process_input(folder)
    assert len(results) == 2
    files = sorted(r.pdf_file for r in results)
    assert files == ["a.pdf", "b.pdf"]
```

Save to `~/.claude/skills/plan-sheet-endpoints/tests/test_pdf_processor.py`.

- [ ] **Step 2: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_pdf_processor.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `pdf_processor.py`**

```python
# scripts/pdf_processor.py
"""Walk a PDF or folder of PDFs and emit PdfResult records."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import fitz

from scripts.page_classifier import PageType, classify_page
from scripts.page_text import get_page_text, get_text_blocks
from scripts.sheet_extractor import SheetData, VicinityCoord, extract_sheet, extract_vicinity_coords


@dataclass
class PdfResult:
    pdf_file: str
    sheets: List[SheetData] = field(default_factory=list)
    vicinity_coords: List[VicinityCoord] = field(default_factory=list)
    raster_pages: List[int] = field(default_factory=list)


_VICINITY_COLLECTING_TYPES = {PageType.COVER, PageType.VICINITY}


def process_pdf(pdf_path: Path) -> PdfResult:
    """Walk every page of one PDF, classify, and extract."""
    pdf_path = Path(pdf_path)
    result = PdfResult(pdf_file=pdf_path.name)

    doc = fitz.open(pdf_path)
    try:
        for i, page in enumerate(doc, start=1):
            text = get_page_text(page)
            blocks = get_text_blocks(page)
            page_type = classify_page(text, blocks)

            if page_type == PageType.RASTER:
                result.raster_pages.append(i)
                continue

            if page_type == PageType.PLAN_PROFILE:
                result.sheets.append(extract_sheet(page, page_number=i, text=text, blocks=blocks))
            elif page_type in _VICINITY_COLLECTING_TYPES:
                result.vicinity_coords.extend(
                    extract_vicinity_coords(page, page_number=i, page_type=page_type.value, text=text)
                )
            # OTHER / LEGEND / NOTES / DETAIL / TRAFFIC_CONTROL: skip silently
    finally:
        doc.close()

    return result


def process_input(input_path: Path) -> List[PdfResult]:
    """Process a single PDF or every PDF under a folder (recursive)."""
    input_path = Path(input_path)
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        return [process_pdf(input_path)]
    if input_path.is_dir():
        results = []
        for pdf in sorted(input_path.rglob("*.pdf")):
            results.append(process_pdf(pdf))
        return results
    raise ValueError(f"Not a PDF or folder: {input_path}")
```

Save to `~/.claude/skills/plan-sheet-endpoints/scripts/pdf_processor.py`.

- [ ] **Step 4: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_pdf_processor.py -v
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/pdf_processor.py tests/test_pdf_processor.py
git commit -m "feat: PDF and folder processor with page classification"
```

---

## Task 13: `output_writer` — main CSV and vicinity reference CSV

**Files:**
- Create: `~/.claude/skills/plan-sheet-endpoints/scripts/output_writer.py`
- Create: `~/.claude/skills/plan-sheet-endpoints/tests/test_output_writer.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_output_writer.py
from pathlib import Path

import pandas as pd

from scripts.output_writer import write_main_csv, write_vicinity_csv
from scripts.pdf_processor import PdfResult
from scripts.sheet_extractor import SheetData, VicinityCoord


def _sample_results() -> list:
    return [PdfResult(
        pdf_file="example.pdf",
        sheets=[
            SheetData(
                page_number=3,
                sheet_id="5",
                start_label="POLE 32",
                start_station="STA 0+00",
                start_lat=34.123,
                start_lon=-118.123,
                end_label="POLE 35",
                end_station="STA 12+50",
                end_lat=34.124,
                end_lon=-118.124,
                road_names=["MAIN ST"],
                structures=["POLE 32", "POLE 35"],
                span_lengths_ft=[260.0],
                construction_type="aerial",
                continues_from_sheet=None,
                continues_to_sheet="6",
                coords_source="printed_on_this_sheet",
                has_native_gps=True,
            ),
            SheetData(
                page_number=4,
                sheet_id="6",
                coords_source="none",
                has_native_gps=False,
            ),
        ],
        vicinity_coords=[
            VicinityCoord(page_number=2, page_type="vicinity", lat=34.10, lon=-118.10, note="decimal_degrees"),
        ],
        raster_pages=[],
    )]


def test_write_main_csv_includes_every_required_column(tmp_path: Path):
    out = tmp_path / "main.csv"
    write_main_csv(_sample_results(), out)
    df = pd.read_csv(out)
    expected_columns = [
        "pdf_file", "page_number", "sheet_id",
        "start_label", "start_station", "start_lat", "start_lon",
        "end_label", "end_station", "end_lat", "end_lon",
        "road_names", "structures", "span_lengths_ft",
        "construction_type", "continues_from_sheet", "continues_to_sheet",
        "coords_source", "has_native_gps",
    ]
    for col in expected_columns:
        assert col in df.columns


def test_write_main_csv_two_rows(tmp_path: Path):
    out = tmp_path / "main.csv"
    write_main_csv(_sample_results(), out)
    df = pd.read_csv(out)
    assert len(df) == 2
    assert df.iloc[0]["pdf_file"] == "example.pdf"
    assert df.iloc[0]["page_number"] == 3
    assert df.iloc[0]["has_native_gps"] is True or df.iloc[0]["has_native_gps"] == "True"
    assert df.iloc[1]["coords_source"] == "none"


def test_write_main_csv_serializes_lists_as_pipe_separated(tmp_path: Path):
    out = tmp_path / "main.csv"
    write_main_csv(_sample_results(), out)
    df = pd.read_csv(out)
    assert df.iloc[0]["structures"] == "POLE 32|POLE 35"
    assert df.iloc[0]["span_lengths_ft"] == "260.0"


def test_write_vicinity_csv_columns(tmp_path: Path):
    out = tmp_path / "vicinity.csv"
    write_vicinity_csv(_sample_results(), out)
    df = pd.read_csv(out)
    expected = ["pdf_file", "page_number", "page_type", "lat", "lon", "note"]
    for col in expected:
        assert col in df.columns
    assert len(df) == 1
    assert df.iloc[0]["lat"] == 34.10


def test_write_vicinity_csv_handles_empty(tmp_path: Path):
    """Empty results still produce a file with headers — easier for downstream tools."""
    empty = [PdfResult(pdf_file="empty.pdf")]
    out = tmp_path / "vicinity.csv"
    write_vicinity_csv(empty, out)
    df = pd.read_csv(out)
    assert list(df.columns) == ["pdf_file", "page_number", "page_type", "lat", "lon", "note"]
    assert len(df) == 0
```

Save to `~/.claude/skills/plan-sheet-endpoints/tests/test_output_writer.py`.

- [ ] **Step 2: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_output_writer.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement CSV writers in `output_writer.py`**

```python
# scripts/output_writer.py
"""Render PdfResult records to CSV and KML deliverables."""
from pathlib import Path
from typing import List

import pandas as pd

from scripts.pdf_processor import PdfResult


_MAIN_COLUMNS = [
    "pdf_file", "page_number", "sheet_id",
    "start_label", "start_station", "start_lat", "start_lon",
    "end_label", "end_station", "end_lat", "end_lon",
    "road_names", "structures", "span_lengths_ft",
    "construction_type", "continues_from_sheet", "continues_to_sheet",
    "coords_source", "has_native_gps",
]

_VICINITY_COLUMNS = ["pdf_file", "page_number", "page_type", "lat", "lon", "note"]


def _join_list(values) -> str:
    if not values:
        return ""
    return "|".join(str(v) for v in values)


def write_main_csv(results: List[PdfResult], output_path: Path) -> None:
    """Write the per-sheet CSV with one row per plan-profile sheet across all PDFs."""
    rows = []
    for r in results:
        for s in r.sheets:
            rows.append({
                "pdf_file": r.pdf_file,
                "page_number": s.page_number,
                "sheet_id": s.sheet_id,
                "start_label": s.start_label,
                "start_station": s.start_station,
                "start_lat": s.start_lat,
                "start_lon": s.start_lon,
                "end_label": s.end_label,
                "end_station": s.end_station,
                "end_lat": s.end_lat,
                "end_lon": s.end_lon,
                "road_names": _join_list(s.road_names),
                "structures": _join_list(s.structures),
                "span_lengths_ft": _join_list(s.span_lengths_ft),
                "construction_type": s.construction_type,
                "continues_from_sheet": s.continues_from_sheet,
                "continues_to_sheet": s.continues_to_sheet,
                "coords_source": s.coords_source,
                "has_native_gps": s.has_native_gps,
            })
    df = pd.DataFrame(rows, columns=_MAIN_COLUMNS)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def write_vicinity_csv(results: List[PdfResult], output_path: Path) -> None:
    """Write the vicinity/cover-page reference CSV — never used to geolocate plan sheets."""
    rows = []
    for r in results:
        for v in r.vicinity_coords:
            rows.append({
                "pdf_file": r.pdf_file,
                "page_number": v.page_number,
                "page_type": v.page_type,
                "lat": v.lat,
                "lon": v.lon,
                "note": v.note,
            })
    df = pd.DataFrame(rows, columns=_VICINITY_COLUMNS)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
```

Save to `~/.claude/skills/plan-sheet-endpoints/scripts/output_writer.py`.

- [ ] **Step 4: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_output_writer.py -v
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/output_writer.py tests/test_output_writer.py
git commit -m "feat: main and vicinity CSV writers"
```

---

## Task 14: `output_writer` — KML

**Files:**
- Modify: `~/.claude/skills/plan-sheet-endpoints/scripts/output_writer.py`
- Modify: `~/.claude/skills/plan-sheet-endpoints/tests/test_output_writer.py`

- [ ] **Step 1: Append failing KML tests**

```python
# Append to tests/test_output_writer.py
import xml.etree.ElementTree as ET

from scripts.output_writer import write_kml


def test_write_kml_only_includes_native_gps_sheets(tmp_path: Path):
    out = tmp_path / "out.kml"
    write_kml(_sample_results(), out)
    tree = ET.parse(out)
    root = tree.getroot()
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    placemarks = root.findall(".//kml:Placemark", ns)
    # Sample data has 1 sheet with native GPS (start + end coords) and 1 sheet without.
    # The native-GPS sheet should produce 2 placemarks (start pin + end pin).
    assert len(placemarks) == 2


def test_write_kml_excludes_vicinity_coords(tmp_path: Path):
    """Vicinity coords must never appear in the KML — they live only in vicinity_reference.csv."""
    out = tmp_path / "out.kml"
    write_kml(_sample_results(), out)
    text = out.read_text(encoding="utf-8")
    # The vicinity-coord lat in our fixture is 34.10 (different from sheet coords 34.123/34.124).
    assert "34.1" not in text or "34.123" in text  # 34.10 must NOT appear standalone
    # Stronger check: parse and look at coordinates
    tree = ET.parse(out)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    coords_elements = tree.getroot().findall(".//kml:coordinates", ns)
    for c in coords_elements:
        lon, lat, *_ = c.text.strip().split(",")
        # Our vicinity coord was -118.10, 34.10 — assert that pair not present
        assert not (abs(float(lat) - 34.10) < 0.001 and abs(float(lon) - (-118.10)) < 0.001)


def test_write_kml_emits_no_placemarks_when_no_native_gps(tmp_path: Path):
    """Sheet with has_native_gps=False produces zero pins."""
    no_gps = [PdfResult(
        pdf_file="x.pdf",
        sheets=[SheetData(page_number=1, sheet_id="1", coords_source="none", has_native_gps=False)],
    )]
    out = tmp_path / "out.kml"
    write_kml(no_gps, out)
    tree = ET.parse(out)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    placemarks = tree.getroot().findall(".//kml:Placemark", ns)
    assert len(placemarks) == 0


def test_write_kml_pin_label_includes_sheet_id(tmp_path: Path):
    out = tmp_path / "out.kml"
    write_kml(_sample_results(), out)
    text = out.read_text(encoding="utf-8")
    # Sheet 5 had native GPS so its pins should reference the sheet id
    assert "Sheet 5" in text or "SHEET 5" in text or "sheet_id=5" in text
```

- [ ] **Step 2: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_output_writer.py -v -k kml
```

Expected: 4 failures with `ImportError` (`write_kml` not defined).

- [ ] **Step 3: Implement `write_kml`**

Append to `scripts/output_writer.py`:

```python
import simplekml


def write_kml(results: List[PdfResult], output_path: Path) -> None:
    """Render KML with start/end pins ONLY for sheets where has_native_gps is True.

    Vicinity-page coordinates are intentionally excluded from the KML —
    they live in vicinity_reference.csv as reference-only data.
    """
    kml = simplekml.Kml()
    folder = kml.newfolder(name="Plan-sheet endpoints (native GPS only)")

    for r in results:
        for s in r.sheets:
            if not s.has_native_gps:
                continue
            sheet_label = f"Sheet {s.sheet_id}" if s.sheet_id else f"Page {s.page_number}"
            if s.start_lat is not None and s.start_lon is not None:
                folder.newpoint(
                    name=f"{sheet_label} start ({s.start_label or s.start_station or ''})".strip(),
                    coords=[(s.start_lon, s.start_lat)],
                    description=(
                        f"PDF: {r.pdf_file}\n"
                        f"Page: {s.page_number}\n"
                        f"Construction: {s.construction_type or 'unknown'}\n"
                        f"Roads: {', '.join(s.road_names) if s.road_names else 'unknown'}"
                    ),
                )
            if s.end_lat is not None and s.end_lon is not None:
                folder.newpoint(
                    name=f"{sheet_label} end ({s.end_label or s.end_station or ''})".strip(),
                    coords=[(s.end_lon, s.end_lat)],
                    description=(
                        f"PDF: {r.pdf_file}\n"
                        f"Page: {s.page_number}\n"
                        f"Continues to: {s.continues_to_sheet or 'unknown'}"
                    ),
                )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    kml.save(str(output_path))
```

- [ ] **Step 4: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_output_writer.py -v
```

Expected: `9 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/output_writer.py tests/test_output_writer.py
git commit -m "feat: KML writer with native-GPS-only pin policy"
```

---

## Task 15: `extract` — CLI entry point

**Files:**
- Create: `~/.claude/skills/plan-sheet-endpoints/scripts/extract.py`
- Create: `~/.claude/skills/plan-sheet-endpoints/tests/test_extract_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_extract_cli.py
import subprocess
import sys
from pathlib import Path


def test_cli_writes_three_outputs(multi_page_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable, "-m", "scripts.extract",
            str(multi_page_pdf),
            "--output-dir", str(out_dir),
        ],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"stderr:\n{proc.stderr}\nstdout:\n{proc.stdout}"

    assert (out_dir / "plan_endpoints.csv").exists()
    assert (out_dir / "vicinity_reference.csv").exists()
    assert (out_dir / "plan_endpoints.kml").exists()


def test_cli_reports_summary_counts(multi_page_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable, "-m", "scripts.extract",
            str(multi_page_pdf),
            "--output-dir", str(out_dir),
        ],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    # Output should mention how many sheets and how many had native GPS
    assert "plan-profile sheet" in proc.stdout.lower() or "sheets" in proc.stdout.lower()
    assert "native gps" in proc.stdout.lower() or "gps" in proc.stdout.lower()


def test_cli_rejects_nonexistent_input(tmp_path: Path):
    proc = subprocess.run(
        [
            sys.executable, "-m", "scripts.extract",
            str(tmp_path / "does_not_exist.pdf"),
        ],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
```

Save to `~/.claude/skills/plan-sheet-endpoints/tests/test_extract_cli.py`.

- [ ] **Step 2: Run tests; verify failure**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_extract_cli.py -v
```

Expected: 3 failures (module `scripts.extract` does not exist).

- [ ] **Step 3: Implement `extract.py`**

```python
# scripts/extract.py
"""CLI entry point for plan-sheet-endpoints.

Usage:
    python -m scripts.extract <pdf_or_folder> [--output-dir <dir>]

Produces three deliverables in --output-dir:
    plan_endpoints.csv         - one row per plan-profile sheet
    vicinity_reference.csv     - cover/vicinity-page coords (reference only)
    plan_endpoints.kml         - pins for sheets with native GPS only
"""
import argparse
import sys
from pathlib import Path
from typing import List, Optional

from scripts.output_writer import write_kml, write_main_csv, write_vicinity_csv
from scripts.pdf_processor import process_input


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract per-sheet start/end metadata from fiber/cable construction-drawing PDFs.",
    )
    parser.add_argument("input", type=Path, help="Path to a PDF file or a folder of PDFs")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Output directory (default: ./output)",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"ERROR: input path does not exist: {args.input}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing {args.input} ...")
    results = process_input(args.input)

    main_csv = args.output_dir / "plan_endpoints.csv"
    vicinity_csv = args.output_dir / "vicinity_reference.csv"
    kml_path = args.output_dir / "plan_endpoints.kml"

    write_main_csv(results, main_csv)
    write_vicinity_csv(results, vicinity_csv)
    write_kml(results, kml_path)

    total_sheets = sum(len(r.sheets) for r in results)
    native_gps = sum(1 for r in results for s in r.sheets if s.has_native_gps)
    raster_pages = sum(len(r.raster_pages) for r in results)
    vicinity_count = sum(len(r.vicinity_coords) for r in results)

    print(f"  PDFs processed:        {len(results)}")
    print(f"  Plan-profile sheets:   {total_sheets}")
    print(f"  Sheets with native GPS:{native_gps}")
    print(f"  Vicinity coord rows:   {vicinity_count}")
    print(f"  Raster pages flagged:  {raster_pages}")
    print(f"  CSV: {main_csv}")
    print(f"  CSV: {vicinity_csv}")
    print(f"  KML: {kml_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Save to `~/.claude/skills/plan-sheet-endpoints/scripts/extract.py`.

- [ ] **Step 4: Run tests; verify pass**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest tests/test_extract_cli.py -v
```

Expected: `3 passed`.

- [ ] **Step 5: Run the full test suite**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest -v
```

Expected: All tests pass (~75 total across all modules).

- [ ] **Step 6: Commit**

```bash
git add scripts/extract.py tests/test_extract_cli.py
git commit -m "feat: CLI entry point with three-output deliverable"
```

---

## Task 16: Final `SKILL.md` content

**Files:**
- Modify: `~/.claude/skills/plan-sheet-endpoints/SKILL.md`

- [ ] **Step 1: Replace the skeletal `SKILL.md` with the final content**

Save the following to `~/.claude/skills/plan-sheet-endpoints/SKILL.md` (overwrites Task 1's skeleton):

```markdown
---
name: plan-sheet-endpoints
description: "Extract start- and end-point metadata from every plan-profile sheet in a fiber/cable construction-drawing (CD) PDF. Works on any drafter's CD package — no template required. Outputs a CSV of per-sheet endpoints (sheet ID, start/end stations, structures, road names, span lengths, construction type, continuation references) and a KML containing pins ONLY for sheets where lat/lon was printed directly on that sheet. Vicinity / overview / cover-page coordinates are kept in a separate vicinity_reference.csv as reference data and are NEVER used to geolocate per-sheet endpoints. Trigger on requests like 'extract endpoints from this CD', 'pull the start/end points from each plan sheet', 'list every site plan's stations and coordinates', 'get the per-sheet metadata from this construction drawing'. For one-shot KMZ-of-the-whole-route output, use cd-route-stitcher instead."
---

# Plan-Sheet Endpoints

## What this skill does

Walks every page of a fiber/cable construction-drawing PDF and, for each plan-profile sheet, extracts:

- Sheet / site-plan identifier
- Start point: first station marker, leading structure label, or continuation reference from previous sheet
- End point: last station marker, trailing structure, or continuation reference to next sheet
- Lat/lon **printed directly on that sheet** (decimal degrees, DMS, or UTM — all converted to WGS84)
- Road / right-of-way names
- Pole / structure labels
- Span lengths (feet)
- Construction type (aerial, underground, overlash, direct bore, trench)
- Cable specs when present (e.g. `288F`, `144 COUNT`, `OPGW`)
- Match / continuation references to adjacent sheets

Outputs three files in `--output-dir`:

| File | Content |
|------|---------|
| `plan_endpoints.csv` | One row per plan-profile sheet, columns per spec |
| `vicinity_reference.csv` | Cover / vicinity / overview coords only — **never used to geolocate per-sheet endpoints** |
| `plan_endpoints.kml` | Pins ONLY for sheets with `has_native_gps=True` |

**Critical constraint:** Vicinity-page coords and per-sheet endpoints are treated as completely independent data. The KML and the per-sheet CSV are populated only from coordinates physically printed on the corresponding plan-profile page. If a vicinity map shows a different rough position than a plan sheet's stamped coords, the plan sheet wins (and the vicinity row stays in the reference CSV).

## When to use

Use whenever a user uploads a fiber/cable CD PDF and wants per-sheet endpoint metadata, including:

- "Extract the start and end points from each plan sheet"
- "List the stations, coordinates, and continuation references for every sheet"
- "Pull a CSV of per-page metadata from this construction drawing"
- "Tell me which sheets have GPS coordinates stamped on them"

Identifying signals in a PDF that mean this skill applies:

- Multi-page CD package (typically 5-60 pages)
- Sheet titles like `SITE PLAN - 1`, `SHEET 5 OF 25`, `SP-12`
- Station markers like `STA 0+00`, `B 21+37`
- Match-line callouts like `MATCH TO SHEET 6`, `SEE SHEET 11`
- Pole / structure labels like `POLE 32`, `P-15`, `STR #42`
- Variability across drafters — no fixed template required

For converting a CD into a single stitched route KMZ, use the separate `cd-route-stitcher` skill. For rendering each plan sheet as a raster overlay onto Google Earth, use `cd-ground-overlays`. This skill produces tabular metadata, not geographic geometry.

## Prerequisites

```bash
pip install -r ~/.claude/skills/plan-sheet-endpoints/requirements.txt --break-system-packages
```

Dependencies: `pymupdf`, `simplekml`, `pyproj`, `pandas`, `pytest`.

## Workflow

### Single PDF

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m scripts.extract /path/to/cd_package.pdf --output-dir /path/to/output
```

### Folder of PDFs (recursive)

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m scripts.extract /path/to/folder_of_cds --output-dir /path/to/output
```

The CLI prints a summary including PDF count, plan-sheet count, sheets-with-native-GPS count, vicinity rows, and raster pages flagged.

### Reading the output

`plan_endpoints.csv` columns (in order):

```
pdf_file, page_number, sheet_id,
start_label, start_station, start_lat, start_lon,
end_label, end_station, end_lat, end_lon,
road_names, structures, span_lengths_ft,
construction_type, continues_from_sheet, continues_to_sheet,
coords_source, has_native_gps
```

- `coords_source` is one of: `printed_on_this_sheet`, `none`. **Never** vicinity-derived.
- `has_native_gps` is `True` only when at least one valid lat/lon was found on that specific sheet.
- List-valued columns (`road_names`, `structures`, `span_lengths_ft`) are pipe-separated (`|`).

`vicinity_reference.csv` columns: `pdf_file, page_number, page_type, lat, lon, note`. Use this to manually cross-reference rough overview locations — but treat the per-sheet CSV as authoritative.

`plan_endpoints.kml`: open in Google Earth Pro. Each sheet with native GPS produces up to two pins (start + end) tagged with the sheet ID, page, construction type, and continuation reference.

## Architecture

```
scripts/
├── coord_parser.py     - decimal degrees, DMS, UTM → WGS84
├── station_parser.py   - station markers (B 21+37, STA 5+00, ...)
├── sheet_id_parser.py  - sheet IDs and continuation references
├── feature_parsers.py  - roads, structures, spans, construction type, cable specs
├── page_text.py        - PyMuPDF text extraction + raster-page detection
├── page_classifier.py  - score-based PageType classifier (PLAN_PROFILE vs COVER, etc.)
├── sheet_extractor.py  - orchestrates per-sheet extraction
├── pdf_processor.py    - walks PDF and folder; emits PdfResult records
├── output_writer.py    - main CSV, vicinity CSV, KML
└── extract.py          - CLI entry point
```

Each module is independently importable and tested. Add new coordinate formats, new page-type heuristics, or new feature extractors by editing one file.

## Known limitations

- **Coordinate detection is regex-only.** Drafters who print coordinates as graphic blocks (text-as-paths) will not be detected. Render the suspicious page to PNG; if you can read text but PyMuPDF cannot, the page is hybrid raster and needs OCR (out of scope).
- **Page classifier is heuristic.** A plan sheet that lacks station markers AND match references AND structure labels will fall through to `OTHER` and be skipped. Conversely, a "general notes" page that happens to mention several `STA 5+00`-style numbers in a table can mis-classify as plan-profile. Spot-check the row count vs. expected sheet count.
- **Start/end coord assignment is positional.** When two coords are stamped on a sheet, the first occurrence (in extracted text order) becomes start and the second becomes end. PyMuPDF text order roughly tracks reading order but not perfectly — verify in the KML before using endpoint coords for layout.
- **Raster-only pages are flagged but not OCR'd.** A scanned-image PDF will produce zero plan rows and a `raster_pages` count in the summary. To recover, OCR the PDF first (e.g. `ocrmypdf` ) and re-run.
- **No coord ↔ station correlation.** This skill records what's printed; it does not validate that a printed coord matches the implied station value. Use the output for indexing and KMZ pinning, not for engineering layout.

## Quality bar by use case

- **Production engineering layout:** not the right tool. Use the source DWG / CAD file.
- **Per-sheet indexing for jobs / tickets / handoff:** acceptable as the primary deliverable.
- **KMZ corridor exhibit:** acceptable for sheets with `has_native_gps=True`. Sheets without native GPS are intentionally absent from the KML — supplement with `cd-route-stitcher` if a continuous route is needed.
- **Audit / QA against engineering drawings:** acceptable as a checklist input. Spot-check at least 10% of sheets for classifier and extractor accuracy.

State the quality bar in any deliverable note: "Generated from CD PDF for indexing and reference. Not certified for engineering layout — for that, use the source DWG in Civil 3D."

## Gotchas

- If a known plan-profile page does not appear in `plan_endpoints.csv`, run `page_classifier` on its text alone and check the score breakdown. Most failures are missing station-marker patterns; extending the regex in `station_parser.py` is usually a one-line fix.
- If `coords_source` is `none` on a sheet you know has stamped coordinates, the lat/lon is likely embedded in a graphic, not extractable text. Confirm by selecting the coord text in a PDF viewer — if it doesn't highlight, PyMuPDF can't read it.
- If the CLI flags many `raster_pages`, the input was scanned. Run `ocrmypdf input.pdf input_ocr.pdf` and re-run this skill on the OCR'd output.
- The vicinity CSV is intentionally never used by the KML or by the per-sheet CSV's coord columns. If a downstream user wants vicinity points on a map, they must add them by hand from `vicinity_reference.csv` after confirming each one is appropriate.

## Testing

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest -v
```

Synthetic test PDFs are generated programmatically in `tests/conftest.py` — no binary fixtures.
```

- [ ] **Step 2: Verify the SKILL.md saves and re-run the full suite**

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest -v
```

Expected: All tests still pass.

- [ ] **Step 3: Final commit**

```bash
git add SKILL.md
git commit -m "docs: final SKILL.md with trigger phrases, recipe, and quality bar"
```

---

## Final verification

After Task 16, the engineer runs:

```bash
cd ~/.claude/skills/plan-sheet-endpoints
python -m pytest -v
```

Expected: every test passes.

Then a smoke run against a real CD PDF (the user will provide one):

```bash
python -m scripts.extract /path/to/real_cd.pdf --output-dir /tmp/psep_smoke
ls /tmp/psep_smoke
# plan_endpoints.csv  vicinity_reference.csv  plan_endpoints.kml
head /tmp/psep_smoke/plan_endpoints.csv
```

The engineer should hand the smoke output back to the user for spot-check before the skill is declared done.
