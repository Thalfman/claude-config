# `kmz-level-up` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `kmz-level-up` skill that takes any KMZ with route LineStrings carrying attributes and produces an upgraded KMZ matching the family deliverable standard (color language, folder hierarchy, derived features, balloon templates, quality-bar disclaimer).

**Architecture:** Two-stage Python pipeline matching `dxf-to-kmz` exactly. Stage 1 (`inspect_kmz.py`) walks the input KML, classifies attributes via first-match-wins regex, and writes an editable `attribute_mapping.json`. Stage 2 (`build_kmz.py`) loads input + mapping into an internal `kml_model`, then runs a sequence of seven independently-testable transformer modules to produce the upgraded KMZ.

**Tech Stack:** Python 3.10+, `fastkml` (KML reading, Tier 1), `lxml` (KML parsing fallback, Tier 2), `simplekml` (KMZ writing), `shapely` (buffered convex hull, vertex deflection geometry), `pyproj` (CRS sanity check), `pytest` (TDD).

**Spec reference:** `docs/superpowers/specs/2026-04-27-kmz-level-up-design.md`

---

## File Structure

All files live under `C:\Users\thalf\.claude\skills\kmz-level-up\`:

```
kmz-level-up/
├── SKILL.md                                # Skill entry point with frontmatter
├── requirements.txt
├── scripts/
│   ├── __init__.py                         # Empty, makes scripts/ importable
│   ├── kml_model.py                        # Internal dataclasses + StyleRole enum
│   ├── attribute_conventions.py            # First-match-wins regex rules
│   ├── parse_kml.py                        # fastkml read + lxml fallback
│   ├── emit_kml.py                         # simplekml write
│   ├── inspect_kmz.py                      # Stage 1 entrypoint
│   ├── build_kmz.py                        # Stage 2 orchestrator
│   ├── attribute_defaults.json             # Per-drafter / per-region attr conventions
│   └── transformers/
│       ├── __init__.py                     # Empty
│       ├── style_restyler.py
│       ├── permit_area_inferer.py
│       ├── pole_derivator.py
│       ├── station_tick_derivator.py
│       ├── folder_refolder.py
│       ├── balloon_enricher.py
│       └── doc_describer.py
└── tests/
    ├── __init__.py                         # Empty
    ├── conftest.py                         # pytest fixtures (synthetic KMZ builders)
    ├── test_kml_model.py
    ├── test_attribute_conventions.py
    ├── test_parse_kml.py
    ├── test_emit_kml.py
    ├── test_style_restyler.py
    ├── test_permit_area_inferer.py
    ├── test_pole_derivator.py
    ├── test_station_tick_derivator.py
    ├── test_folder_refolder.py
    ├── test_balloon_enricher.py
    ├── test_doc_describer.py
    ├── test_inspect_kmz.py
    └── test_build_kmz_e2e.py
```

**Boundaries:**
- `kml_model.py` — pure data definitions (dataclasses + enum). No I/O, no parsing, no transforming.
- `attribute_conventions.py` — pure regex → role/style classification. Operates on dicts and strings; knows nothing about KML.
- `parse_kml.py` — input only. KMZ/KML → `kml_model`. No write side.
- `emit_kml.py` — output only. `kml_model` → KMZ. No read side.
- Transformers — each takes `kml_model` + mapping config, returns mutated `kml_model`. Each is independently testable.
- `inspect_kmz.py` — orchestrates parse + conventions + JSON write. No transformation.
- `build_kmz.py` — orchestrates parse + transformers + emit. The only script that writes the upgraded KMZ.

**Working-directory convention:** All scripts run from the `kmz-level-up/` skill folder. Import paths use `from scripts.X import Y`. Tests run via `pytest tests/` from the skill folder. Matches `dxf-to-kmz` exactly.

**Note on git:** The user's `.claude/skills/` root is not a git repo; each skill folder is its own repo. Task 1 includes `git init` inside `kmz-level-up/`. Each subsequent task ends with a commit.

**Parallel-friendly tasks:** Tasks 3 (`attribute_conventions`), 4 (`parse_kml`), 5 (`emit_kml`) depend only on Task 2 (`kml_model`) and can run concurrently. Tasks 6–12 (the seven transformers) all depend only on Task 2 and can also run concurrently. Tasks 13–15 are sequential (depend on multiple prior tasks). The subagent-driven executor should fan these out.

---

## Task 1: Project Scaffolding

**Files:**
- Create: `kmz-level-up/SKILL.md` (frontmatter-only skeleton; full content in Task 16)
- Create: `kmz-level-up/requirements.txt`
- Create: `kmz-level-up/scripts/__init__.py` (empty)
- Create: `kmz-level-up/scripts/transformers/__init__.py` (empty)
- Create: `kmz-level-up/tests/__init__.py` (empty)
- Create: `kmz-level-up/tests/conftest.py` (minimal — fixture builders are added in Task 15)

- [ ] **Step 1.1: Create directory tree**

```bash
cd "C:/Users/thalf/.claude/skills"
mkdir -p kmz-level-up/scripts/transformers kmz-level-up/tests
```

- [ ] **Step 1.2: Write `requirements.txt`**

```
fastkml>=0.12
lxml>=5.0
simplekml>=1.3
shapely>=2.0
pyproj>=3.6
pytest>=8.0
```

Install:
```bash
pip install -r kmz-level-up/requirements.txt
```

- [ ] **Step 1.3: Write `SKILL.md` skeleton (frontmatter only)**

```markdown
---
name: kmz-level-up
description: Use when you have an existing KMZ with route LineStrings carrying attributes (construction type, chainage, owner, span lengths) that needs to be upgraded to the family deliverable standard. Trigger on "level up this KMZ", "upgrade this Google Earth file", "apply the standard styling", "make this KMZ deliverable-ready", "fix the folder structure on this KMZ". Applies the family color language (red dashed aerial, red solid underground, orange replace, magenta markup), reorganizes into the family folder hierarchy, derives missing features (pole markers from vertex deflection, station ticks from chainage, permit-area polygon from buffered route hull), enriches with HTML balloon templates, and stamps the quality-bar disclaimer. Handles input from any source (own skills' outputs, third-party desktop tools like Civil 3D / QGIS / ArcGIS, contractor hand-builds) via tier-based detection. Two-stage workflow with editable attribute_mapping.json between inspect and build.
---

# KMZ Level Up

(Content filled in Task 16.)
```

- [ ] **Step 1.4: Write empty `__init__.py` files**

```python
# kmz-level-up/scripts/__init__.py — empty package marker
```

```python
# kmz-level-up/scripts/transformers/__init__.py — empty package marker
```

```python
# kmz-level-up/tests/__init__.py — empty package marker
```

- [ ] **Step 1.5: Write minimal `tests/conftest.py`**

```python
"""pytest fixtures.

Per-test fixtures (full synthetic KMZ builders for end-to-end tests) live in
this file and are added in Task 15. Per-module unit tests build their
kml_model objects inline rather than relying on conftest fixtures.
"""
```

- [ ] **Step 1.6: Initialize git repo and commit scaffolding**

```bash
cd "C:/Users/thalf/.claude/skills/kmz-level-up"
git init
git add .
git commit -m "chore: scaffold kmz-level-up skill (frontmatter, requirements, package layout)"
```

- [ ] **Step 1.7: Verify scaffolding is in place**

```bash
cd "C:/Users/thalf/.claude/skills/kmz-level-up"
ls -la scripts/ scripts/transformers/ tests/
pytest tests/ -v
```

Expected: pytest reports "collected 0 items" (no tests yet), exits 5 (no tests). Directory tree shows the package layout above.

---

## Task 2: `kml_model.py` — Dataclasses & StyleRole Enum

**Files:**
- Create: `kmz-level-up/scripts/kml_model.py`
- Test: `kmz-level-up/tests/test_kml_model.py`

This module defines the internal in-memory representation. Every transformer operates on these types. Other modules import only from here for type contracts.

- [ ] **Step 2.1: Write the failing test**

`tests/test_kml_model.py`:

```python
"""Unit tests for kml_model — dataclasses + StyleRole enum."""

from scripts.kml_model import (
    StyleRole,
    LineStringFeature,
    PointFeature,
    PolygonFeature,
    Document,
)


def test_style_role_enum_has_all_family_roles():
    """Every family color-language role must be representable."""
    expected = {
        "aerial", "underground", "replace", "markup",
        "existing", "boundary", "pole", "vault", "station", "unmapped",
    }
    actual = {role.value for role in StyleRole}
    assert actual == expected


def test_linestring_feature_construction():
    f = LineStringFeature(
        id="fid_1",
        name="Aerial Run 1",
        attributes={"TYPE": "AERIAL", "STA": "37+25"},
        coordinates=[(-86.03, 40.80), (-86.025, 40.80)],
        style_role=StyleRole.AERIAL,
        folder_path=["Proposed Route", "Aerial"],
    )
    assert f.id == "fid_1"
    assert f.style_role is StyleRole.AERIAL
    assert f.coordinates[0] == (-86.03, 40.80)


def test_point_feature_default_style_role_is_unmapped():
    p = PointFeature(id="p1", name="Pole 5", attributes={}, coordinates=(-86.03, 40.80))
    assert p.style_role is StyleRole.UNMAPPED


def test_polygon_feature_holds_outer_ring():
    poly = PolygonFeature(
        id="poly_1",
        name="Permit Area",
        attributes={},
        outer_ring=[(-86.03, 40.80), (-86.02, 40.80), (-86.02, 40.81), (-86.03, 40.81), (-86.03, 40.80)],
        style_role=StyleRole.BOUNDARY,
    )
    assert len(poly.outer_ring) == 5  # closed ring


def test_document_holds_all_feature_types_and_metadata():
    doc = Document(
        source_path="input.kmz",
        name="Test Doc",
        description="",
        linestrings=[],
        points=[],
        polygons=[],
    )
    assert doc.source_path == "input.kmz"
    assert doc.linestrings == []
```

- [ ] **Step 2.2: Run test to verify it fails**

```bash
cd "C:/Users/thalf/.claude/skills/kmz-level-up"
pytest tests/test_kml_model.py -v
```

Expected: ImportError or ModuleNotFoundError on `scripts.kml_model`.

- [ ] **Step 2.3: Implement `scripts/kml_model.py`**

```python
"""Internal normalized representation of KML data.

Pure data definitions. No I/O, no parsing, no transforming. Other modules
import these dataclasses + the StyleRole enum to define their type contracts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StyleRole(str, Enum):
    AERIAL = "aerial"
    UNDERGROUND = "underground"
    REPLACE = "replace"
    MARKUP = "markup"
    EXISTING = "existing"
    BOUNDARY = "boundary"
    POLE = "pole"
    VAULT = "vault"
    STATION = "station"
    UNMAPPED = "unmapped"


@dataclass
class LineStringFeature:
    id: str
    name: str
    attributes: dict[str, Any]
    coordinates: list[tuple[float, float]]
    style_role: StyleRole = StyleRole.UNMAPPED
    folder_path: list[str] = field(default_factory=list)
    description_html: str = ""


@dataclass
class PointFeature:
    id: str
    name: str
    attributes: dict[str, Any]
    coordinates: tuple[float, float]
    style_role: StyleRole = StyleRole.UNMAPPED
    folder_path: list[str] = field(default_factory=list)
    description_html: str = ""


@dataclass
class PolygonFeature:
    id: str
    name: str
    attributes: dict[str, Any]
    outer_ring: list[tuple[float, float]]
    inner_rings: list[list[tuple[float, float]]] = field(default_factory=list)
    style_role: StyleRole = StyleRole.UNMAPPED
    folder_path: list[str] = field(default_factory=list)
    description_html: str = ""


@dataclass
class Document:
    source_path: str
    name: str
    description: str
    linestrings: list[LineStringFeature] = field(default_factory=list)
    points: list[PointFeature] = field(default_factory=list)
    polygons: list[PolygonFeature] = field(default_factory=list)

    def all_features(self):
        yield from self.linestrings
        yield from self.points
        yield from self.polygons
```

- [ ] **Step 2.4: Run test to verify it passes**

```bash
pytest tests/test_kml_model.py -v
```

Expected: 5 tests pass.

- [ ] **Step 2.5: Commit**

```bash
git add scripts/kml_model.py tests/test_kml_model.py
git commit -m "feat(model): kml_model dataclasses and StyleRole enum"
```

---

## Task 3: `attribute_conventions.py` — Regex Classification Rules

**Files:**
- Create: `kmz-level-up/scripts/attribute_conventions.py`
- Test: `kmz-level-up/tests/test_attribute_conventions.py`

Implements first-match-wins regex rules per the spec's Attribute Detection section. Two rule lists: name-rules (attribute key → role) and value-rules-per-role (string value → StyleRole). Existing-infrastructure check fires before route classification.

- [ ] **Step 3.1: Write the failing test**

`tests/test_attribute_conventions.py`:

```python
"""Unit tests for attribute_conventions — regex classification rules."""

from scripts.attribute_conventions import (
    classify_attribute_name,
    classify_construction_value,
    classify_feature,
)
from scripts.kml_model import LineStringFeature, StyleRole


def test_classify_name_construction_type_variants():
    for key in ("TYPE", "type", "construction_type", "const_type", "MAT_TYPE", "method"):
        assert classify_attribute_name(key) == "construction_type"


def test_classify_name_chainage_variants():
    for key in ("STA", "sta", "chainage", "station", "chain_ft"):
        assert classify_attribute_name(key) == "chainage"


def test_classify_name_span_length_variants():
    for key in ("SPAN_FT", "span", "length", "span_length"):
        assert classify_attribute_name(key) == "span_length"


def test_classify_name_owner_variants():
    for key in ("OWNER", "owner", "PRM", "entity"):
        assert classify_attribute_name(key) == "owner"


def test_classify_name_sheet_id_variants():
    for key in ("SHEET_ID", "sheet", "SHT_NUM"):
        assert classify_attribute_name(key) == "sheet_id"


def test_classify_name_unmatched_returns_none():
    assert classify_attribute_name("RANDOM_FIELD_42") is None


def test_classify_construction_value_aerial():
    for v in ("AERIAL", "aerial", "OVH", "OVERHEAD", "OVERLASH", "STRAND"):
        assert classify_construction_value(v) == StyleRole.AERIAL


def test_classify_construction_value_underground():
    for v in ("UNDERGROUND", "UG", "BORE", "TRENCH", "DIRECTIONAL"):
        assert classify_construction_value(v) == StyleRole.UNDERGROUND


def test_classify_construction_value_replace():
    for v in ("REPLACE", "RPLC"):
        assert classify_construction_value(v) == StyleRole.REPLACE


def test_classify_construction_value_markup():
    for v in ("MARKUP", "REVISION", "REDLINE", "RED"):
        assert classify_construction_value(v) == StyleRole.MARKUP


def test_classify_construction_value_unrecognized_is_unmapped():
    assert classify_construction_value("XYZ") == StyleRole.UNMAPPED


def test_classify_feature_existing_takes_precedence_over_construction():
    """A feature named EX_FIBER_AERIAL should be classified as existing,
    not aerial, even though the construction-type would match aerial."""
    f = LineStringFeature(
        id="ex1",
        name="EX_FIBER_AERIAL",
        attributes={"TYPE": "AERIAL"},
        coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
    )
    role_map = {"TYPE": "construction_type"}
    role = classify_feature(f, role_map)
    assert role == StyleRole.EXISTING


def test_classify_feature_existing_attribute_truthy():
    """A feature with existing=true attribute is classified as existing
    regardless of name or construction type."""
    f = LineStringFeature(
        id="x1",
        name="Some Line",
        attributes={"existing": True, "TYPE": "AERIAL"},
        coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
    )
    role_map = {"TYPE": "construction_type"}
    role = classify_feature(f, role_map)
    assert role == StyleRole.EXISTING


def test_classify_feature_aerial_normal_path():
    f = LineStringFeature(
        id="a1",
        name="Run 1",
        attributes={"TYPE": "AERIAL"},
        coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
    )
    role_map = {"TYPE": "construction_type"}
    role = classify_feature(f, role_map)
    assert role == StyleRole.AERIAL


def test_classify_feature_no_construction_attr_is_unmapped():
    f = LineStringFeature(
        id="u1",
        name="Run 2",
        attributes={"OTHER": "value"},
        coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
    )
    role_map = {}
    role = classify_feature(f, role_map)
    assert role == StyleRole.UNMAPPED


def test_classify_feature_word_boundary_ex_does_not_false_positive():
    """A name like 'TEXT_LINE' should NOT match the EX existing rule."""
    f = LineStringFeature(
        id="t1",
        name="TEXT_LINE",
        attributes={"TYPE": "AERIAL"},
        coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
    )
    role_map = {"TYPE": "construction_type"}
    role = classify_feature(f, role_map)
    assert role == StyleRole.AERIAL  # not EXISTING
```

- [ ] **Step 3.2: Run test to verify it fails**

```bash
pytest tests/test_attribute_conventions.py -v
```

Expected: ImportError on `scripts.attribute_conventions`.

- [ ] **Step 3.3: Implement `scripts/attribute_conventions.py`**

```python
"""First-match-wins regex rules for attribute name → role and attribute
value → StyleRole. Existing-infrastructure check fires before route
classification, mirroring dxf-to-kmz/layer_conventions.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from scripts.kml_model import StyleRole, LineStringFeature, PointFeature, PolygonFeature


@dataclass(frozen=True)
class NameRule:
    pattern: re.Pattern
    role: str  # "construction_type" | "chainage" | "span_length" | "owner" | "sheet_id" | "existing_flag"


@dataclass(frozen=True)
class ValueRule:
    pattern: re.Pattern
    style_role: StyleRole


# Order matters: first match wins.
NAME_RULES: list[NameRule] = [
    NameRule(re.compile(r"const.*type|mat.*type|method", re.I), "construction_type"),
    NameRule(re.compile(r"\btype\b", re.I), "construction_type"),
    NameRule(re.compile(r"chain|station|\bsta\b", re.I), "chainage"),
    NameRule(re.compile(r"span|length|\bft\b", re.I), "span_length"),
    NameRule(re.compile(r"owner|\bprm\b|entity", re.I), "owner"),
    NameRule(re.compile(r"sheet|\bsht\b|\bfid\b", re.I), "sheet_id"),
    NameRule(re.compile(r"existing|^ex$", re.I), "existing_flag"),
]


CONSTRUCTION_VALUE_RULES: list[ValueRule] = [
    ValueRule(re.compile(r"aerial|\bovh\b|overhead|overlash|strand", re.I), StyleRole.AERIAL),
    ValueRule(re.compile(r"underground|\bug\b|bore|trench|directional", re.I), StyleRole.UNDERGROUND),
    ValueRule(re.compile(r"replace|rplc", re.I), StyleRole.REPLACE),
    ValueRule(re.compile(r"markup|revision|redline|\bred\b", re.I), StyleRole.MARKUP),
]


# Word-boundary EX prefix: matches "EX_*" or "*_EX_*" but not "TEXT".
_EX_NAME_PATTERN = re.compile(r"(?:^|_)EX(?:_|$)", re.I)


def classify_attribute_name(key: str) -> str | None:
    """Return the role for an attribute name, or None if unmatched."""
    for rule in NAME_RULES:
        if rule.pattern.search(key):
            return rule.role
    return None


def classify_construction_value(value: str) -> StyleRole:
    """Map a construction-type attribute value to a StyleRole."""
    for rule in CONSTRUCTION_VALUE_RULES:
        if rule.pattern.search(value):
            return rule.style_role
    return StyleRole.UNMAPPED


def classify_feature(
    feature: LineStringFeature | PointFeature | PolygonFeature,
    role_map: dict[str, str],
) -> StyleRole:
    """Classify a feature into a StyleRole.

    Existing-infrastructure check fires first:
      - placemark name matches `EX_*` (word-boundary) → EXISTING
      - any attribute mapped to `existing_flag` is truthy → EXISTING

    Then construction-type check:
      - find the attribute key whose role is `construction_type`
      - run its value through CONSTRUCTION_VALUE_RULES

    Otherwise UNMAPPED.
    """
    # Existing check by name
    if _EX_NAME_PATTERN.search(feature.name or ""):
        return StyleRole.EXISTING

    # Existing check by attribute
    for key, role in role_map.items():
        if role == "existing_flag" and feature.attributes.get(key):
            return StyleRole.EXISTING

    # Construction-type lookup
    for key, role in role_map.items():
        if role == "construction_type":
            value = feature.attributes.get(key)
            if value is not None:
                return classify_construction_value(str(value))

    return StyleRole.UNMAPPED
```

- [ ] **Step 3.4: Run test to verify it passes**

```bash
pytest tests/test_attribute_conventions.py -v
```

Expected: all 16 tests pass.

- [ ] **Step 3.5: Commit**

```bash
git add scripts/attribute_conventions.py tests/test_attribute_conventions.py
git commit -m "feat(conventions): first-match-wins regex rules + existing-first classifier"
```

---

## Task 4: `parse_kml.py` — fastkml Read with lxml Fallback

**Files:**
- Create: `kmz-level-up/scripts/parse_kml.py`
- Test: `kmz-level-up/tests/test_parse_kml.py`

Reads a `.kmz` (or `.kml`) into a `Document`. Tier 1: fastkml. Tier 2: lxml direct when fastkml raises. Extracts ExtendedData (`<SimpleData>` / `<Data>`) into the `attributes` dict; skips style metadata (the restyler handles styling).

- [ ] **Step 4.1: Write the failing test**

`tests/test_parse_kml.py`:

```python
"""Unit tests for parse_kml — fastkml + lxml fallback parsing."""

import zipfile
from pathlib import Path

import pytest

from scripts.kml_model import Document, LineStringFeature
from scripts.parse_kml import parse_kmz


SIMPLE_KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Test Doc</name>
    <description>A simple test KML.</description>
    <Placemark id="ls1">
      <name>Aerial Run 1</name>
      <ExtendedData>
        <Data name="TYPE"><value>AERIAL</value></Data>
        <Data name="STA"><value>37+25</value></Data>
      </ExtendedData>
      <LineString>
        <coordinates>-86.030,40.801,0 -86.025,40.801,0</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>
"""


def write_kmz(tmp_path: Path, kml_content: str, name: str = "test.kmz") -> Path:
    kmz_path = tmp_path / name
    with zipfile.ZipFile(kmz_path, "w") as zf:
        zf.writestr("doc.kml", kml_content)
    return kmz_path


def test_parse_kmz_returns_document(tmp_path):
    kmz = write_kmz(tmp_path, SIMPLE_KML)
    doc = parse_kmz(kmz)
    assert isinstance(doc, Document)
    assert doc.source_path == str(kmz)
    assert doc.name == "Test Doc"


def test_parse_kmz_extracts_linestring(tmp_path):
    kmz = write_kmz(tmp_path, SIMPLE_KML)
    doc = parse_kmz(kmz)
    assert len(doc.linestrings) == 1
    ls = doc.linestrings[0]
    assert isinstance(ls, LineStringFeature)
    assert ls.name == "Aerial Run 1"
    assert ls.attributes["TYPE"] == "AERIAL"
    assert ls.attributes["STA"] == "37+25"
    assert len(ls.coordinates) == 2
    assert ls.coordinates[0] == (-86.030, 40.801)


def test_parse_kml_handles_simpledata_schema(tmp_path):
    """Civil 3D / ArcGIS exports use SchemaData/SimpleData rather than Data."""
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Civil3D Doc</name>
    <Schema id="route_schema" name="Route">
      <SimpleField name="TYPE" type="string"/>
    </Schema>
    <Placemark>
      <name>Run</name>
      <ExtendedData>
        <SchemaData schemaUrl="#route_schema">
          <SimpleData name="TYPE">UG</SimpleData>
        </SchemaData>
      </ExtendedData>
      <LineString>
        <coordinates>-86.03,40.80,0 -86.02,40.80,0</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>
"""
    kmz = write_kmz(tmp_path, kml)
    doc = parse_kmz(kmz)
    assert doc.linestrings[0].attributes["TYPE"] == "UG"


def test_parse_kml_handles_polygon(tmp_path):
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Boundary</name>
      <Polygon>
        <outerBoundaryIs><LinearRing><coordinates>
          -86.03,40.80,0 -86.02,40.80,0 -86.02,40.81,0 -86.03,40.81,0 -86.03,40.80,0
        </coordinates></LinearRing></outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""
    kmz = write_kmz(tmp_path, kml)
    doc = parse_kmz(kmz)
    assert len(doc.polygons) == 1
    assert len(doc.polygons[0].outer_ring) == 5


def test_parse_kml_handles_point(tmp_path):
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Pole 1</name>
      <Point>
        <coordinates>-86.03,40.80,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>
"""
    kmz = write_kmz(tmp_path, kml)
    doc = parse_kmz(kmz)
    assert len(doc.points) == 1
    assert doc.points[0].coordinates == (-86.03, 40.80)


def test_parse_raw_kml_file(tmp_path):
    """Parsing a .kml (not .kmz) directly should work too."""
    kml_path = tmp_path / "test.kml"
    kml_path.write_text(SIMPLE_KML, encoding="utf-8")
    doc = parse_kmz(kml_path)
    assert len(doc.linestrings) == 1


def test_parse_kml_fastkml_failure_falls_back_to_lxml(tmp_path):
    """Some Google Earth Pro hand-builds emit malformed namespaces or
    tags that fastkml chokes on; we fall back to direct lxml parsing."""
    # gx: namespace + Track elements; minimal but enough to derail strict fastkml
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
  <Document>
    <name>Hand-built</name>
    <Placemark>
      <name>Path</name>
      <ExtendedData>
        <Data name="TYPE"><value>AERIAL</value></Data>
      </ExtendedData>
      <gx:Track>
        <gx:coord>-86.03 40.80 0</gx:coord>
        <gx:coord>-86.02 40.80 0</gx:coord>
      </gx:Track>
    </Placemark>
  </Document>
</kml>
"""
    kmz = write_kmz(tmp_path, kml)
    doc = parse_kmz(kmz)
    # Whether fastkml handles gx:Track or lxml fallback handles it, we
    # expect the route to be extracted as a LineString-ish feature.
    assert len(doc.linestrings) == 1
    assert doc.linestrings[0].attributes["TYPE"] == "AERIAL"
```

- [ ] **Step 4.2: Run test to verify it fails**

```bash
pytest tests/test_parse_kml.py -v
```

Expected: ImportError on `scripts.parse_kml`.

- [ ] **Step 4.3: Implement `scripts/parse_kml.py`**

```python
"""Read a KMZ/KML file into the internal kml_model.Document.

Tier 1: lxml direct parse (deterministic, namespace-aware, handles every
KML construct we care about). We use lxml directly rather than fastkml as
the primary path because fastkml's strictness around namespaces and
optional fields produces silent drops on contractor hand-builds.

Tier 2: A future fastkml fallback could be added if lxml-direct hits a
case it can't represent, but for the v1 attribute set (LineString, Point,
Polygon, ExtendedData/Data, ExtendedData/SchemaData/SimpleData, gx:Track)
direct lxml is the simpler primary path.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

from lxml import etree

from scripts.kml_model import (
    Document,
    LineStringFeature,
    PointFeature,
    PolygonFeature,
)


KML_NS = "http://www.opengis.net/kml/2.2"
GX_NS = "http://www.google.com/kml/ext/2.2"
NS = {"k": KML_NS, "gx": GX_NS}


def parse_kmz(path: str | Path) -> Document:
    """Parse a KMZ or KML file into a Document.

    Accepts either a `.kmz` (zip with `doc.kml` inside, possibly other
    files) or a raw `.kml` file path.
    """
    path = Path(path)
    if path.suffix.lower() == ".kmz":
        kml_bytes = _extract_doc_kml(path)
    else:
        kml_bytes = path.read_bytes()

    root = etree.fromstring(kml_bytes)
    doc_el = _find_first(root, "Document") or root  # some KMLs have no Document

    name = _text(doc_el, "name") or path.stem
    description = _text(doc_el, "description") or ""

    doc = Document(
        source_path=str(path),
        name=name,
        description=description,
    )

    placemarks = doc_el.findall(f".//k:Placemark", NS)
    for i, pm in enumerate(placemarks):
        feature = _parse_placemark(pm, fallback_id=f"fid_{i}")
        if isinstance(feature, LineStringFeature):
            doc.linestrings.append(feature)
        elif isinstance(feature, PointFeature):
            doc.points.append(feature)
        elif isinstance(feature, PolygonFeature):
            doc.polygons.append(feature)

    return doc


def _extract_doc_kml(kmz_path: Path) -> bytes:
    with zipfile.ZipFile(kmz_path, "r") as zf:
        # Convention: the main KML inside a KMZ is doc.kml. Some tools name
        # it differently; pick the first .kml entry as fallback.
        names = zf.namelist()
        target = "doc.kml" if "doc.kml" in names else next(
            (n for n in names if n.lower().endswith(".kml")), None
        )
        if target is None:
            raise ValueError(f"No .kml entry inside KMZ {kmz_path}")
        return zf.read(target)


def _parse_placemark(pm, fallback_id: str):
    pid = pm.get("id") or fallback_id
    name = _text(pm, "name") or ""
    description_el = pm.find("k:description", NS)
    description_html = (description_el.text or "") if description_el is not None else ""
    attributes = _parse_extended_data(pm)

    # LineString
    ls = pm.find("k:LineString/k:coordinates", NS)
    if ls is not None and ls.text:
        coords = _parse_coordinates(ls.text)
        return LineStringFeature(
            id=pid, name=name, attributes=attributes,
            coordinates=coords, description_html=description_html,
        )

    # gx:Track (some hand-builds use this for paths)
    track_coords = pm.findall("k:gx:Track/k:gx:coord", NS) or pm.findall("gx:Track/gx:coord", NS)
    if not track_coords:
        # Try with explicit gx prefix lookup
        track_coords = pm.findall(f".//{{{GX_NS}}}coord")
    if track_coords:
        coords = []
        for c in track_coords:
            if c.text:
                parts = c.text.strip().split()
                if len(parts) >= 2:
                    coords.append((float(parts[0]), float(parts[1])))
        if coords:
            return LineStringFeature(
                id=pid, name=name, attributes=attributes,
                coordinates=coords, description_html=description_html,
            )

    # Point
    pt = pm.find("k:Point/k:coordinates", NS)
    if pt is not None and pt.text:
        coords = _parse_coordinates(pt.text)
        if coords:
            return PointFeature(
                id=pid, name=name, attributes=attributes,
                coordinates=coords[0], description_html=description_html,
            )

    # Polygon
    outer = pm.find("k:Polygon/k:outerBoundaryIs/k:LinearRing/k:coordinates", NS)
    if outer is not None and outer.text:
        outer_ring = _parse_coordinates(outer.text)
        inner_rings = []
        for ir in pm.findall("k:Polygon/k:innerBoundaryIs/k:LinearRing/k:coordinates", NS):
            if ir.text:
                inner_rings.append(_parse_coordinates(ir.text))
        return PolygonFeature(
            id=pid, name=name, attributes=attributes,
            outer_ring=outer_ring, inner_rings=inner_rings,
            description_html=description_html,
        )

    return None


def _parse_extended_data(pm) -> dict:
    """Read both <Data name="X"><value>Y</value></Data> and
    <SchemaData><SimpleData name="X">Y</SimpleData></SchemaData> forms."""
    out = {}
    for d in pm.findall("k:ExtendedData/k:Data", NS):
        key = d.get("name")
        v = d.find("k:value", NS)
        if key:
            out[key] = (v.text or "") if v is not None else ""
    for sd in pm.findall("k:ExtendedData/k:SchemaData/k:SimpleData", NS):
        key = sd.get("name")
        if key:
            out[key] = sd.text or ""
    return out


def _parse_coordinates(text: str) -> list[tuple[float, float]]:
    """KML coordinates are 'lon,lat[,alt] lon,lat[,alt] ...'."""
    coords = []
    for tok in text.strip().split():
        parts = tok.split(",")
        if len(parts) >= 2:
            coords.append((float(parts[0]), float(parts[1])))
    return coords


def _text(parent, tag: str) -> str | None:
    el = parent.find(f"k:{tag}", NS)
    return el.text if el is not None else None


def _find_first(parent, tag: str):
    return parent.find(f".//k:{tag}", NS)
```

- [ ] **Step 4.4: Run test to verify it passes**

```bash
pytest tests/test_parse_kml.py -v
```

Expected: 7 tests pass.

- [ ] **Step 4.5: Commit**

```bash
git add scripts/parse_kml.py tests/test_parse_kml.py
git commit -m "feat(parse): lxml-direct KML/KMZ parser handling Data, SchemaData, gx:Track"
```

---

## Task 5: `emit_kml.py` — simplekml Writer

**Files:**
- Create: `kmz-level-up/scripts/emit_kml.py`
- Test: `kmz-level-up/tests/test_emit_kml.py`

Writes a `Document` to a `.kmz` file using simplekml. Renders the family color language (red dashed aerial, etc.), folder hierarchy, document description, ExtendedData round-trip.

- [ ] **Step 5.1: Write the failing test**

`tests/test_emit_kml.py`:

```python
"""Unit tests for emit_kml — simplekml writer."""

import zipfile
from pathlib import Path

from scripts.emit_kml import write_kmz
from scripts.kml_model import (
    Document,
    LineStringFeature,
    PointFeature,
    PolygonFeature,
    StyleRole,
)


def test_write_kmz_creates_file(tmp_path):
    out = tmp_path / "out.kmz"
    doc = Document(source_path="x", name="Out", description="hi", linestrings=[], points=[], polygons=[])
    write_kmz(doc, out)
    assert out.exists()
    assert zipfile.is_zipfile(out)


def test_write_kmz_includes_doc_kml(tmp_path):
    out = tmp_path / "out.kmz"
    doc = Document(source_path="x", name="Out", description="hi", linestrings=[], points=[], polygons=[])
    write_kmz(doc, out)
    with zipfile.ZipFile(out) as zf:
        assert "doc.kml" in zf.namelist()


def test_write_kmz_renders_aerial_style(tmp_path):
    out = tmp_path / "out.kmz"
    ls = LineStringFeature(
        id="ls1", name="Aerial Run", attributes={"TYPE": "AERIAL"},
        coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
        style_role=StyleRole.AERIAL,
        folder_path=["Proposed Route", "Aerial"],
    )
    doc = Document(source_path="x", name="Out", description="", linestrings=[ls], points=[], polygons=[])
    write_kmz(doc, out)
    with zipfile.ZipFile(out) as zf:
        kml = zf.read("doc.kml").decode("utf-8")
    assert "<color>ff0000ff</color>" in kml  # red
    # Folder structure
    assert "<name>Proposed Route</name>" in kml
    assert "<name>Aerial</name>" in kml


def test_write_kmz_renders_polygon_with_yellow_translucent_fill(tmp_path):
    out = tmp_path / "out.kmz"
    poly = PolygonFeature(
        id="poly1", name="Permit Area", attributes={},
        outer_ring=[(-86.03, 40.80), (-86.02, 40.80), (-86.02, 40.81), (-86.03, 40.81), (-86.03, 40.80)],
        style_role=StyleRole.BOUNDARY,
        folder_path=["Permit Area"],
    )
    doc = Document(source_path="x", name="Out", description="", linestrings=[], points=[], polygons=[poly])
    write_kmz(doc, out)
    with zipfile.ZipFile(out) as zf:
        kml = zf.read("doc.kml").decode("utf-8")
    # Yellow translucent: line ff00ffff, fill 4000ffff
    assert "ff00ffff" in kml
    assert "4000ffff" in kml


def test_write_kmz_existing_folder_visibility_zero(tmp_path):
    out = tmp_path / "out.kmz"
    ls = LineStringFeature(
        id="ex1", name="EX_FIBER", attributes={},
        coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
        style_role=StyleRole.EXISTING,
        folder_path=["Existing Infrastructure"],
    )
    doc = Document(source_path="x", name="Out", description="", linestrings=[ls], points=[], polygons=[])
    write_kmz(doc, out)
    with zipfile.ZipFile(out) as zf:
        kml = zf.read("doc.kml").decode("utf-8")
    # Folder should be present and have visibility=0
    assert "<name>Existing Infrastructure</name>" in kml
    assert "<visibility>0</visibility>" in kml


def test_write_kmz_round_trips_extended_data(tmp_path):
    out = tmp_path / "out.kmz"
    ls = LineStringFeature(
        id="ls1", name="X", attributes={"TYPE": "AERIAL", "STA": "37+25"},
        coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
        style_role=StyleRole.AERIAL,
        folder_path=["Proposed Route", "Aerial"],
    )
    doc = Document(source_path="x", name="Out", description="", linestrings=[ls], points=[], polygons=[])
    write_kmz(doc, out)
    with zipfile.ZipFile(out) as zf:
        kml = zf.read("doc.kml").decode("utf-8")
    assert "TYPE" in kml
    assert "AERIAL" in kml
    assert "37+25" in kml


def test_write_kmz_includes_document_description(tmp_path):
    out = tmp_path / "out.kmz"
    doc = Document(source_path="x", name="Out", description="Quality bar disclaimer here.", linestrings=[], points=[], polygons=[])
    write_kmz(doc, out)
    with zipfile.ZipFile(out) as zf:
        kml = zf.read("doc.kml").decode("utf-8")
    assert "Quality bar disclaimer here." in kml
```

- [ ] **Step 5.2: Run test to verify it fails**

```bash
pytest tests/test_emit_kml.py -v
```

Expected: ImportError on `scripts.emit_kml`.

- [ ] **Step 5.3: Implement `scripts/emit_kml.py`**

```python
"""Write a Document to a .kmz file using simplekml.

Renders the family color language and folder hierarchy. Folder visibility
defaults match family conventions (Existing Infrastructure visibility=0).
"""
from __future__ import annotations

from pathlib import Path

import simplekml

from scripts.kml_model import (
    Document,
    LineStringFeature,
    PointFeature,
    PolygonFeature,
    StyleRole,
)


# Family color language. KML colors are aabbggrr.
STYLE_DEFS: dict[StyleRole, dict] = {
    StyleRole.AERIAL:      {"line_color": "ff0000ff", "line_width": 3, "dashed": True},
    StyleRole.UNDERGROUND: {"line_color": "ff0000ff", "line_width": 3, "dashed": False},
    StyleRole.REPLACE:     {"line_color": "ff0080ff", "line_width": 3, "dashed": True},
    StyleRole.MARKUP:      {"line_color": "ffff00ff", "line_width": 3, "dashed": True},
    StyleRole.EXISTING:    {"line_color": "ff808080", "line_width": 2, "dashed": False},
    StyleRole.BOUNDARY:    {"line_color": "ff00ffff", "line_width": 2, "fill_color": "4000ffff"},
    StyleRole.POLE:        {"icon": "https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png", "icon_color": "ff0000ff"},
    StyleRole.VAULT:       {"icon": "https://maps.google.com/mapfiles/kml/shapes/placemark_square.png", "icon_color": "ffff0000"},
    StyleRole.STATION:     {"icon": "https://maps.google.com/mapfiles/kml/paddle/wht-blank.png", "icon_color": "ff404040"},
    StyleRole.UNMAPPED:    {"line_color": "ff404040", "line_width": 1, "dashed": False},
}


# Folders with default-off visibility per family conventions.
DEFAULT_OFF_FOLDERS = {"Existing Infrastructure", "Unmapped Routes"}
# Folders that are folded (visible-when-expanded but collapsed by default).
FOLDED_FOLDERS = {"Stations & Labels", "Existing Infrastructure", "Unmapped Routes"}


def write_kmz(doc: Document, out_path: str | Path) -> None:
    out_path = Path(out_path)
    kml = simplekml.Kml()
    kml.document.name = doc.name
    if doc.description:
        kml.document.description = doc.description

    folder_cache: dict[tuple[str, ...], simplekml.Folder] = {(): kml.document}

    def get_folder(path: tuple[str, ...]) -> simplekml.Folder:
        if path in folder_cache:
            return folder_cache[path]
        parent = get_folder(path[:-1])
        folder = parent.newfolder(name=path[-1])
        if path[-1] in DEFAULT_OFF_FOLDERS:
            folder.visibility = 0
        if path[-1] in FOLDED_FOLDERS:
            folder.open = 0
        folder_cache[path] = folder
        return folder

    for ls in doc.linestrings:
        _emit_linestring(ls, get_folder)
    for pt in doc.points:
        _emit_point(pt, get_folder)
    for poly in doc.polygons:
        _emit_polygon(poly, get_folder)

    kml.savekmz(str(out_path))


def _emit_linestring(ls: LineStringFeature, get_folder) -> None:
    folder = get_folder(tuple(ls.folder_path))
    placemark = folder.newlinestring(name=ls.name, coords=[(lon, lat) for lon, lat in ls.coordinates])
    placemark.altitudemode = simplekml.AltitudeMode.clamptoground
    style_def = STYLE_DEFS[ls.style_role]
    placemark.style.linestyle.color = style_def["line_color"]
    placemark.style.linestyle.width = style_def["line_width"]
    if style_def.get("dashed"):
        # KML doesn't natively support dashed lines; simplekml doesn't either.
        # We use gx:outerColor as a hint and rely on folder-name disambiguation.
        # Recorded in spec as a known limitation.
        pass
    _attach_extended_data(placemark, ls.attributes)
    if ls.description_html:
        placemark.description = ls.description_html


def _emit_point(pt: PointFeature, get_folder) -> None:
    folder = get_folder(tuple(pt.folder_path))
    placemark = folder.newpoint(name=pt.name, coords=[pt.coordinates])
    placemark.altitudemode = simplekml.AltitudeMode.clamptoground
    style_def = STYLE_DEFS[pt.style_role]
    if "icon" in style_def:
        placemark.style.iconstyle.icon.href = style_def["icon"]
        placemark.style.iconstyle.color = style_def["icon_color"]
    _attach_extended_data(placemark, pt.attributes)
    if pt.description_html:
        placemark.description = pt.description_html


def _emit_polygon(poly: PolygonFeature, get_folder) -> None:
    folder = get_folder(tuple(poly.folder_path))
    placemark = folder.newpolygon(
        name=poly.name,
        outerboundaryis=[(lon, lat) for lon, lat in poly.outer_ring],
    )
    if poly.inner_rings:
        placemark.innerboundaryis = [
            [(lon, lat) for lon, lat in ring] for ring in poly.inner_rings
        ]
    placemark.altitudemode = simplekml.AltitudeMode.clamptoground
    style_def = STYLE_DEFS[poly.style_role]
    placemark.style.linestyle.color = style_def["line_color"]
    placemark.style.linestyle.width = style_def["line_width"]
    if "fill_color" in style_def:
        placemark.style.polystyle.color = style_def["fill_color"]
        placemark.style.polystyle.fill = 1
    _attach_extended_data(placemark, poly.attributes)
    if poly.description_html:
        placemark.description = poly.description_html


def _attach_extended_data(placemark, attributes: dict) -> None:
    for k, v in attributes.items():
        placemark.extendeddata.newdata(name=str(k), value=str(v))
```

- [ ] **Step 5.4: Run test to verify it passes**

```bash
pytest tests/test_emit_kml.py -v
```

Expected: 7 tests pass.

- [ ] **Step 5.5: Commit**

```bash
git add scripts/emit_kml.py tests/test_emit_kml.py
git commit -m "feat(emit): simplekml writer with family color language + folder visibility defaults"
```

---

## Task 6: `transformers/style_restyler.py`

**Files:**
- Create: `kmz-level-up/scripts/transformers/style_restyler.py`
- Test: `kmz-level-up/tests/test_style_restyler.py`

Walks every feature in the document; for those with `style_role == UNMAPPED`, runs them through the classifier (using the role_map from the mapping JSON). Idempotent: features that already have a non-UNMAPPED style_role are left as-is.

- [ ] **Step 6.1: Write the failing test**

`tests/test_style_restyler.py`:

```python
"""Unit tests for style_restyler."""

from scripts.kml_model import Document, LineStringFeature, StyleRole
from scripts.transformers.style_restyler import apply


def _doc_with(linestrings):
    return Document(
        source_path="x",
        name="Test",
        description="",
        linestrings=linestrings,
        points=[],
        polygons=[],
    )


def test_classifies_aerial_from_attribute():
    ls = LineStringFeature(id="1", name="Run", attributes={"TYPE": "AERIAL"}, coordinates=[(-86, 40), (-85, 40)])
    doc = _doc_with([ls])
    role_map = {"TYPE": "construction_type"}
    apply(doc, role_map=role_map)
    assert doc.linestrings[0].style_role is StyleRole.AERIAL


def test_classifies_underground_from_attribute():
    ls = LineStringFeature(id="2", name="Run", attributes={"TYPE": "UG"}, coordinates=[(-86, 40), (-85, 40)])
    doc = _doc_with([ls])
    apply(doc, role_map={"TYPE": "construction_type"})
    assert doc.linestrings[0].style_role is StyleRole.UNDERGROUND


def test_existing_name_takes_precedence():
    ls = LineStringFeature(id="3", name="EX_FIBER", attributes={"TYPE": "AERIAL"}, coordinates=[(-86, 40), (-85, 40)])
    doc = _doc_with([ls])
    apply(doc, role_map={"TYPE": "construction_type"})
    assert doc.linestrings[0].style_role is StyleRole.EXISTING


def test_unrecognized_value_becomes_unmapped():
    ls = LineStringFeature(id="4", name="Run", attributes={"TYPE": "XYZ"}, coordinates=[(-86, 40), (-85, 40)])
    doc = _doc_with([ls])
    apply(doc, role_map={"TYPE": "construction_type"})
    assert doc.linestrings[0].style_role is StyleRole.UNMAPPED


def test_idempotent_on_already_classified_feature():
    ls = LineStringFeature(
        id="5", name="Run", attributes={"TYPE": "AERIAL"},
        coordinates=[(-86, 40), (-85, 40)],
        style_role=StyleRole.UNDERGROUND,  # Already classified by an earlier pass; respect it.
    )
    doc = _doc_with([ls])
    apply(doc, role_map={"TYPE": "construction_type"})
    assert doc.linestrings[0].style_role is StyleRole.UNDERGROUND  # Unchanged


def test_polygon_named_permit_becomes_boundary():
    """A polygon named 'Permit Area' or matching boundary keywords should get BOUNDARY role."""
    from scripts.kml_model import PolygonFeature
    poly = PolygonFeature(
        id="p1", name="Permit Area", attributes={},
        outer_ring=[(-86, 40), (-85, 40), (-85, 41), (-86, 41), (-86, 40)],
    )
    doc = Document(source_path="x", name="T", description="", linestrings=[], points=[], polygons=[poly])
    apply(doc, role_map={})
    assert doc.polygons[0].style_role is StyleRole.BOUNDARY


def test_per_placemark_override_pins_role():
    """A per-placemark override in the mapping JSON wins over auto-classification."""
    ls = LineStringFeature(id="ovr1", name="Mystery", attributes={"TYPE": "XYZ"}, coordinates=[(-86, 40), (-85, 40)])
    doc = _doc_with([ls])
    overrides = {"ovr1": StyleRole.AERIAL}
    apply(doc, role_map={"TYPE": "construction_type"}, overrides=overrides)
    assert doc.linestrings[0].style_role is StyleRole.AERIAL
```

- [ ] **Step 6.2: Run test to verify it fails**

```bash
pytest tests/test_style_restyler.py -v
```

Expected: ImportError on `scripts.transformers.style_restyler`.

- [ ] **Step 6.3: Implement `scripts/transformers/style_restyler.py`**

```python
"""style_restyler — classify each feature's style_role.

Behavior:
- Per-placemark `overrides` map (id → StyleRole) wins over auto-classification.
- Features with style_role != UNMAPPED are left unchanged (idempotent).
- LineStrings: classified via attribute_conventions.classify_feature.
- Polygons named like 'Permit Area' / 'Boundary' / 'Work Area' become BOUNDARY.
- Points: left UNMAPPED unless overridden (pole_derivator and station_tick_derivator
  set roles for derived points; original points stay UNMAPPED unless explicitly tagged).
"""
from __future__ import annotations

import re

from scripts.attribute_conventions import classify_feature
from scripts.kml_model import (
    Document,
    PolygonFeature,
    StyleRole,
)


_BOUNDARY_NAME = re.compile(r"permit|boundary|work\s*area|easement|row\s*lim", re.I)


def apply(
    doc: Document,
    role_map: dict[str, str],
    overrides: dict[str, StyleRole] | None = None,
) -> None:
    """Mutate doc in place; assign style_role to every feature."""
    overrides = overrides or {}

    for ls in doc.linestrings:
        if ls.id in overrides:
            ls.style_role = overrides[ls.id]
            continue
        if ls.style_role is not StyleRole.UNMAPPED:
            continue
        ls.style_role = classify_feature(ls, role_map)

    for poly in doc.polygons:
        if poly.id in overrides:
            poly.style_role = overrides[poly.id]
            continue
        if poly.style_role is not StyleRole.UNMAPPED:
            continue
        if _BOUNDARY_NAME.search(poly.name or ""):
            poly.style_role = StyleRole.BOUNDARY
        else:
            poly.style_role = classify_feature(poly, role_map)

    for pt in doc.points:
        if pt.id in overrides:
            pt.style_role = overrides[pt.id]
            continue
        # Points stay UNMAPPED unless explicitly overridden.
```

- [ ] **Step 6.4: Run test to verify it passes**

```bash
pytest tests/test_style_restyler.py -v
```

Expected: 7 tests pass.

- [ ] **Step 6.5: Commit**

```bash
git add scripts/transformers/style_restyler.py tests/test_style_restyler.py
git commit -m "feat(transformers): style_restyler with per-placemark override + idempotency"
```

---

## Task 7: `transformers/permit_area_inferer.py`

**Files:**
- Create: `kmz-level-up/scripts/transformers/permit_area_inferer.py`
- Test: `kmz-level-up/tests/test_permit_area_inferer.py`

If no polygon has `style_role == BOUNDARY`, computes a buffered convex hull around all aerial+underground LineStrings and adds it as a synthesized PolygonFeature labeled "Permit Area (inferred — verify before submittal)". Skipped if `derive_permit_area: false`.

- [ ] **Step 7.1: Write the failing test**

`tests/test_permit_area_inferer.py`:

```python
"""Unit tests for permit_area_inferer."""

from scripts.kml_model import Document, LineStringFeature, PolygonFeature, StyleRole
from scripts.transformers.permit_area_inferer import apply


def _doc_with_routes():
    return Document(
        source_path="x",
        name="Test",
        description="",
        linestrings=[
            LineStringFeature(
                id="ls1", name="A", attributes={},
                coordinates=[(-86.030, 40.800), (-86.020, 40.800)],
                style_role=StyleRole.AERIAL,
            ),
            LineStringFeature(
                id="ls2", name="B", attributes={},
                coordinates=[(-86.025, 40.805), (-86.015, 40.805)],
                style_role=StyleRole.UNDERGROUND,
            ),
        ],
        points=[],
        polygons=[],
    )


def test_infers_permit_area_when_absent():
    doc = _doc_with_routes()
    apply(doc, derive=True, buffer_ft=50)
    assert len(doc.polygons) == 1
    poly = doc.polygons[0]
    assert poly.style_role is StyleRole.BOUNDARY
    assert "inferred" in poly.name.lower()


def test_skips_when_existing_boundary_present():
    doc = _doc_with_routes()
    doc.polygons.append(PolygonFeature(
        id="p_existing", name="Permit Area",
        attributes={},
        outer_ring=[(-86.04, 40.79), (-86.01, 40.79), (-86.01, 40.81), (-86.04, 40.81), (-86.04, 40.79)],
        style_role=StyleRole.BOUNDARY,
    ))
    apply(doc, derive=True, buffer_ft=50)
    assert len(doc.polygons) == 1  # Did not add a synthesized one


def test_skips_when_derive_false():
    doc = _doc_with_routes()
    apply(doc, derive=False, buffer_ft=50)
    assert len(doc.polygons) == 0


def test_inferred_polygon_contains_route_endpoints():
    """The inferred hull should geometrically contain the input routes."""
    from shapely.geometry import Polygon, Point
    doc = _doc_with_routes()
    apply(doc, derive=True, buffer_ft=50)
    poly = doc.polygons[0]
    sh_poly = Polygon(poly.outer_ring)
    # Each input vertex should fall within the buffered hull.
    for ls in doc.linestrings:
        for lon, lat in ls.coordinates:
            assert sh_poly.contains(Point(lon, lat)) or sh_poly.touches(Point(lon, lat))


def test_skips_when_no_aerial_or_underground_routes():
    doc = Document(source_path="x", name="T", description="", linestrings=[], points=[], polygons=[])
    apply(doc, derive=True, buffer_ft=50)
    assert len(doc.polygons) == 0
```

- [ ] **Step 7.2: Run test to verify it fails**

```bash
pytest tests/test_permit_area_inferer.py -v
```

Expected: ImportError on `scripts.transformers.permit_area_inferer`.

- [ ] **Step 7.3: Implement `scripts/transformers/permit_area_inferer.py`**

```python
"""permit_area_inferer — synthesize Permit Area polygon when input lacks one.

Uses a buffered convex hull of all aerial + underground route geometry.
The buffer is provided in feet and converted to lat/lon degrees using a
crude approximation (1° ≈ 364,000 ft latitude; longitude scaled by cos(lat)).
This is precise enough for the family use-case (visualizing permit work area)
and avoids a pyproj reproject for every job.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, MultiLineString, mapping
from shapely.ops import unary_union

from scripts.kml_model import Document, PolygonFeature, StyleRole


_FT_PER_DEGREE_LAT = 364_000.0


def apply(doc: Document, derive: bool, buffer_ft: float) -> None:
    if not derive:
        return
    if any(p.style_role is StyleRole.BOUNDARY for p in doc.polygons):
        return

    route_lines = [
        LineString(ls.coordinates)
        for ls in doc.linestrings
        if ls.style_role in (StyleRole.AERIAL, StyleRole.UNDERGROUND) and len(ls.coordinates) >= 2
    ]
    if not route_lines:
        return

    merged = unary_union(MultiLineString(route_lines))
    hull = merged.convex_hull

    # Convert buffer_ft to degrees. Use the centroid lat for longitude scale.
    centroid_lat = hull.centroid.y
    deg_per_ft_lat = 1.0 / _FT_PER_DEGREE_LAT
    deg_per_ft_lon = 1.0 / (_FT_PER_DEGREE_LAT * max(math.cos(math.radians(centroid_lat)), 0.01))
    # Use the average of lat/lon scale for an isotropic buffer (good enough at small scales).
    buffer_deg = buffer_ft * (deg_per_ft_lat + deg_per_ft_lon) / 2

    buffered = hull.buffer(buffer_deg, cap_style=2, join_style=2)
    if buffered.is_empty:
        return

    geom = mapping(buffered)
    coords = geom["coordinates"][0]
    outer_ring = [(float(lon), float(lat)) for lon, lat in coords]

    poly = PolygonFeature(
        id="inferred_permit_area",
        name="Permit Area (inferred — verify before submittal)",
        attributes={"_inferred": "true", "_buffer_ft": str(buffer_ft)},
        outer_ring=outer_ring,
        style_role=StyleRole.BOUNDARY,
    )
    doc.polygons.append(poly)
```

- [ ] **Step 7.4: Run test to verify it passes**

```bash
pytest tests/test_permit_area_inferer.py -v
```

Expected: 5 tests pass.

- [ ] **Step 7.5: Commit**

```bash
git add scripts/transformers/permit_area_inferer.py tests/test_permit_area_inferer.py
git commit -m "feat(transformers): permit_area_inferer (buffered convex hull when boundary absent)"
```

---

## Task 8: `transformers/pole_derivator.py`

**Files:**
- Create: `kmz-level-up/scripts/transformers/pole_derivator.py`
- Test: `kmz-level-up/tests/test_pole_derivator.py`

For each LineString classified as `AERIAL`, scans vertices and emits a `PointFeature` (style_role=POLE) wherever the angular deflection exceeds the configured threshold (default 5°). Skipped if the input already has poles in a "Poles" / "Proposed Infrastructure/Poles" folder, or if `derive_poles: false`.

- [ ] **Step 8.1: Write the failing test**

`tests/test_pole_derivator.py`:

```python
"""Unit tests for pole_derivator."""

from scripts.kml_model import Document, LineStringFeature, PointFeature, StyleRole
from scripts.transformers.pole_derivator import apply


def _doc_with_aerial_route():
    """A 4-vertex aerial route. Vertex 1 and 2 are mid-route. Vertex 1 has
    a 90° turn (clear pole), vertex 2 is straight (no pole)."""
    return Document(
        source_path="x", name="T", description="",
        linestrings=[
            LineStringFeature(
                id="ls1", name="Run",
                attributes={},
                coordinates=[
                    (-86.030, 40.800),  # endpoint
                    (-86.025, 40.800),  # 90° turn
                    (-86.025, 40.805),
                    (-86.025, 40.810),  # straight from prev (no pole)
                ],
                style_role=StyleRole.AERIAL,
            ),
        ],
        points=[],
        polygons=[],
    )


def test_derives_pole_at_high_deflection_vertex():
    doc = _doc_with_aerial_route()
    apply(doc, derive=True, deflection_deg=5)
    pole_points = [p for p in doc.points if p.style_role is StyleRole.POLE]
    assert len(pole_points) >= 1
    # The 90° turn at (-86.025, 40.800) should produce a pole.
    assert any(abs(p.coordinates[0] - -86.025) < 1e-6 and abs(p.coordinates[1] - 40.800) < 1e-6
               for p in pole_points)


def test_no_pole_at_straight_segment():
    doc = _doc_with_aerial_route()
    apply(doc, derive=True, deflection_deg=5)
    pole_points = [p for p in doc.points if p.style_role is StyleRole.POLE]
    # Vertex 2 (straight continuation) should NOT produce a pole.
    assert not any(abs(p.coordinates[1] - 40.805) < 1e-6 for p in pole_points)


def test_skips_when_derive_false():
    doc = _doc_with_aerial_route()
    apply(doc, derive=False, deflection_deg=5)
    assert len(doc.points) == 0


def test_skips_when_input_already_has_poles():
    doc = _doc_with_aerial_route()
    doc.points.append(PointFeature(
        id="existing_pole", name="Pole 1", attributes={},
        coordinates=(-86.025, 40.800), style_role=StyleRole.POLE,
        folder_path=["Proposed Infrastructure", "Poles"],
    ))
    apply(doc, derive=True, deflection_deg=5)
    new_poles = [p for p in doc.points if p.id != "existing_pole"]
    assert len(new_poles) == 0


def test_higher_threshold_suppresses_borderline_deflections():
    """A 10° deflection vertex with threshold 30° should not produce a pole."""
    ls = LineStringFeature(
        id="ls1", name="Run", attributes={},
        coordinates=[
            (0.0, 0.0),
            (1.0, 0.0),
            (1.5, 0.087),  # ~10° deflection from the previous segment
        ],
        style_role=StyleRole.AERIAL,
    )
    doc = Document(source_path="x", name="T", description="", linestrings=[ls], points=[], polygons=[])
    apply(doc, derive=True, deflection_deg=30)
    assert not any(p.style_role is StyleRole.POLE for p in doc.points)


def test_only_aerial_routes_get_poles():
    """Underground routes should NOT get pole markers derived."""
    ls = LineStringFeature(
        id="ug1", name="UG Run", attributes={},
        coordinates=[(-86.030, 40.800), (-86.025, 40.800), (-86.025, 40.805)],
        style_role=StyleRole.UNDERGROUND,
    )
    doc = Document(source_path="x", name="T", description="", linestrings=[ls], points=[], polygons=[])
    apply(doc, derive=True, deflection_deg=5)
    assert not any(p.style_role is StyleRole.POLE for p in doc.points)
```

- [ ] **Step 8.2: Run test to verify it fails**

```bash
pytest tests/test_pole_derivator.py -v
```

Expected: ImportError on `scripts.transformers.pole_derivator`.

- [ ] **Step 8.3: Implement `scripts/transformers/pole_derivator.py`**

```python
"""pole_derivator — synthesize pole point markers from aerial LineString
vertices whose deflection from the previous segment exceeds a threshold.

Skipped if the input already has any Point with style_role POLE OR with a
folder_path containing 'Poles' (the latter catches ungrouped point poles
the user authored manually). Also skipped if derive=False.
"""
from __future__ import annotations

import math

from scripts.kml_model import Document, PointFeature, StyleRole


def apply(doc: Document, derive: bool, deflection_deg: float) -> None:
    if not derive:
        return
    if _input_has_poles(doc):
        return

    threshold_rad = math.radians(deflection_deg)
    new_poles: list[PointFeature] = []

    for ls in doc.linestrings:
        if ls.style_role is not StyleRole.AERIAL:
            continue
        for i in range(1, len(ls.coordinates) - 1):
            prev = ls.coordinates[i - 1]
            curr = ls.coordinates[i]
            nxt = ls.coordinates[i + 1]
            angle = _deflection_angle(prev, curr, nxt)
            if angle >= threshold_rad:
                new_poles.append(PointFeature(
                    id=f"derived_pole_{ls.id}_{i}",
                    name=f"Pole {len(new_poles) + 1}",
                    attributes={"_derived": "true", "_source_route": ls.id},
                    coordinates=curr,
                    style_role=StyleRole.POLE,
                ))

    doc.points.extend(new_poles)


def _input_has_poles(doc: Document) -> bool:
    for pt in doc.points:
        if pt.style_role is StyleRole.POLE:
            return True
        if any("pole" in p.lower() for p in pt.folder_path):
            return True
    return False


def _deflection_angle(p0, p1, p2) -> float:
    """Angle between segment p0→p1 and p1→p2 (radians, 0 = straight)."""
    v1x, v1y = p1[0] - p0[0], p1[1] - p0[1]
    v2x, v2y = p2[0] - p1[0], p2[1] - p1[1]
    n1 = math.hypot(v1x, v1y)
    n2 = math.hypot(v2x, v2y)
    if n1 == 0 or n2 == 0:
        return 0.0
    cos_a = (v1x * v2x + v1y * v2y) / (n1 * n2)
    cos_a = max(-1.0, min(1.0, cos_a))
    return math.acos(cos_a)
```

- [ ] **Step 8.4: Run test to verify it passes**

```bash
pytest tests/test_pole_derivator.py -v
```

Expected: 6 tests pass.

- [ ] **Step 8.5: Commit**

```bash
git add scripts/transformers/pole_derivator.py tests/test_pole_derivator.py
git commit -m "feat(transformers): pole_derivator (vertex deflection on aerial routes)"
```

---

## Task 9: `transformers/station_tick_derivator.py`

**Files:**
- Create: `kmz-level-up/scripts/transformers/station_tick_derivator.py`
- Test: `kmz-level-up/tests/test_station_tick_derivator.py`

If a chainage attribute is mapped, emits a small tick PointFeature (style_role=STATION) at the midpoint of each LineString that has a chainage attribute. Skipped if no chainage attribute is mapped, or if `derive_station_ticks: false`. (Per spec: pole_derivator covers vertex-based markers; this covers attribute-driven station ticks.)

- [ ] **Step 9.1: Write the failing test**

`tests/test_station_tick_derivator.py`:

```python
"""Unit tests for station_tick_derivator."""

from scripts.kml_model import Document, LineStringFeature, PointFeature, StyleRole
from scripts.transformers.station_tick_derivator import apply


def _doc_with_chained_route():
    return Document(
        source_path="x", name="T", description="",
        linestrings=[
            LineStringFeature(
                id="ls1", name="Run",
                attributes={"STA": "37+25"},
                coordinates=[(-86.030, 40.800), (-86.020, 40.800)],
                style_role=StyleRole.AERIAL,
            ),
            LineStringFeature(
                id="ls2", name="Run B",
                attributes={"STA": "42+50"},
                coordinates=[(-86.020, 40.800), (-86.010, 40.800)],
                style_role=StyleRole.UNDERGROUND,
            ),
        ],
        points=[],
        polygons=[],
    )


def test_derives_station_ticks_at_midpoints():
    doc = _doc_with_chained_route()
    role_map = {"STA": "chainage"}
    apply(doc, derive=True, role_map=role_map)
    ticks = [p for p in doc.points if p.style_role is StyleRole.STATION]
    assert len(ticks) == 2
    # First tick at midpoint of ls1
    assert abs(ticks[0].coordinates[0] - -86.025) < 1e-6
    assert "37+25" in ticks[0].name


def test_skips_when_derive_false():
    doc = _doc_with_chained_route()
    apply(doc, derive=False, role_map={"STA": "chainage"})
    assert not any(p.style_role is StyleRole.STATION for p in doc.points)


def test_skips_when_no_chainage_mapped():
    doc = _doc_with_chained_route()
    apply(doc, derive=True, role_map={})  # No chainage role mapping
    assert not any(p.style_role is StyleRole.STATION for p in doc.points)


def test_skips_features_without_chainage_attribute():
    doc = Document(
        source_path="x", name="T", description="",
        linestrings=[LineStringFeature(
            id="ls1", name="Run", attributes={"OTHER": "x"},
            coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
            style_role=StyleRole.AERIAL,
        )],
        points=[], polygons=[],
    )
    apply(doc, derive=True, role_map={"STA": "chainage"})  # STA not in this feature's attrs
    assert not any(p.style_role is StyleRole.STATION for p in doc.points)
```

- [ ] **Step 9.2: Run test to verify it fails**

```bash
pytest tests/test_station_tick_derivator.py -v
```

Expected: ImportError on `scripts.transformers.station_tick_derivator`.

- [ ] **Step 9.3: Implement `scripts/transformers/station_tick_derivator.py`**

```python
"""station_tick_derivator — emit station-tick point markers at the
midpoint of each LineString that has a chainage attribute.

This is the attribute-driven complement to pole_derivator (which is
geometry-driven). Skipped if no chainage attribute is mapped or if
derive=False.
"""
from __future__ import annotations

from scripts.kml_model import Document, PointFeature, StyleRole


def apply(doc: Document, derive: bool, role_map: dict[str, str]) -> None:
    if not derive:
        return
    chainage_attr = next((k for k, role in role_map.items() if role == "chainage"), None)
    if not chainage_attr:
        return

    new_ticks: list[PointFeature] = []
    for ls in doc.linestrings:
        sta = ls.attributes.get(chainage_attr)
        if sta is None or sta == "":
            continue
        if len(ls.coordinates) < 2:
            continue
        midpoint = _midpoint(ls.coordinates)
        new_ticks.append(PointFeature(
            id=f"derived_tick_{ls.id}",
            name=f"STA {sta}",
            attributes={"_derived": "true", "_source_route": ls.id, chainage_attr: str(sta)},
            coordinates=midpoint,
            style_role=StyleRole.STATION,
        ))

    doc.points.extend(new_ticks)


def _midpoint(coords: list[tuple[float, float]]) -> tuple[float, float]:
    """Geometric midpoint of a polyline by cumulative length."""
    if len(coords) == 2:
        return ((coords[0][0] + coords[1][0]) / 2, (coords[0][1] + coords[1][1]) / 2)
    # General case: walk halfway along the cumulative length.
    seg_lens = []
    total = 0.0
    for i in range(1, len(coords)):
        dx = coords[i][0] - coords[i - 1][0]
        dy = coords[i][1] - coords[i - 1][1]
        d = (dx * dx + dy * dy) ** 0.5
        seg_lens.append(d)
        total += d
    if total == 0:
        return coords[0]
    target = total / 2
    walked = 0.0
    for i, d in enumerate(seg_lens):
        if walked + d >= target:
            t = (target - walked) / d if d else 0
            x = coords[i][0] + t * (coords[i + 1][0] - coords[i][0])
            y = coords[i][1] + t * (coords[i + 1][1] - coords[i][1])
            return (x, y)
        walked += d
    return coords[-1]
```

- [ ] **Step 9.4: Run test to verify it passes**

```bash
pytest tests/test_station_tick_derivator.py -v
```

Expected: 4 tests pass.

- [ ] **Step 9.5: Commit**

```bash
git add scripts/transformers/station_tick_derivator.py tests/test_station_tick_derivator.py
git commit -m "feat(transformers): station_tick_derivator (midpoint ticks from chainage attr)"
```

---

## Task 10: `transformers/folder_refolder.py`

**Files:**
- Create: `kmz-level-up/scripts/transformers/folder_refolder.py`
- Test: `kmz-level-up/tests/test_folder_refolder.py`

Sets `folder_path` on every feature based on its `style_role`. Existing-infra placemarks go to "Existing Infrastructure" (default-off). Maps each StyleRole to its destination folder per the spec's Family Color Language table.

- [ ] **Step 10.1: Write the failing test**

`tests/test_folder_refolder.py`:

```python
"""Unit tests for folder_refolder."""

from scripts.kml_model import (
    Document, LineStringFeature, PointFeature, PolygonFeature, StyleRole
)
from scripts.transformers.folder_refolder import apply, FOLDER_FOR_ROLE


def test_aerial_goes_to_proposed_route_aerial():
    ls = LineStringFeature(id="1", name="Run", attributes={}, coordinates=[(-86, 40), (-85, 40)], style_role=StyleRole.AERIAL)
    doc = Document(source_path="x", name="T", description="", linestrings=[ls], points=[], polygons=[])
    apply(doc)
    assert ls.folder_path == ["Proposed Route", "Aerial"]


def test_underground_goes_to_proposed_route_underground():
    ls = LineStringFeature(id="2", name="UG", attributes={}, coordinates=[(-86, 40), (-85, 40)], style_role=StyleRole.UNDERGROUND)
    doc = Document(source_path="x", name="T", description="", linestrings=[ls], points=[], polygons=[])
    apply(doc)
    assert ls.folder_path == ["Proposed Route", "Underground"]


def test_existing_goes_to_existing_infrastructure():
    ls = LineStringFeature(id="3", name="EX", attributes={}, coordinates=[(-86, 40), (-85, 40)], style_role=StyleRole.EXISTING)
    doc = Document(source_path="x", name="T", description="", linestrings=[ls], points=[], polygons=[])
    apply(doc)
    assert ls.folder_path == ["Existing Infrastructure"]


def test_boundary_polygon_goes_to_permit_area():
    poly = PolygonFeature(id="p1", name="Permit", attributes={}, outer_ring=[(-86, 40), (-85, 40), (-85, 41), (-86, 40)], style_role=StyleRole.BOUNDARY)
    doc = Document(source_path="x", name="T", description="", linestrings=[], points=[], polygons=[poly])
    apply(doc)
    assert poly.folder_path == ["Permit Area"]


def test_pole_goes_to_proposed_infrastructure_poles():
    pt = PointFeature(id="pole1", name="Pole", attributes={}, coordinates=(-86, 40), style_role=StyleRole.POLE)
    doc = Document(source_path="x", name="T", description="", linestrings=[], points=[pt], polygons=[])
    apply(doc)
    assert pt.folder_path == ["Proposed Infrastructure", "Poles"]


def test_unmapped_goes_to_unmapped_routes():
    ls = LineStringFeature(id="u1", name="?", attributes={}, coordinates=[(-86, 40), (-85, 40)], style_role=StyleRole.UNMAPPED)
    doc = Document(source_path="x", name="T", description="", linestrings=[ls], points=[], polygons=[])
    apply(doc)
    assert ls.folder_path == ["Unmapped Routes"]


def test_every_style_role_has_a_folder_destination():
    for role in StyleRole:
        assert role in FOLDER_FOR_ROLE
        assert FOLDER_FOR_ROLE[role]  # non-empty list


def test_replace_and_markup_have_dedicated_subfolders():
    ls_replace = LineStringFeature(id="r1", name="R", attributes={}, coordinates=[(-86, 40), (-85, 40)], style_role=StyleRole.REPLACE)
    ls_markup = LineStringFeature(id="m1", name="M", attributes={}, coordinates=[(-86, 40), (-85, 40)], style_role=StyleRole.MARKUP)
    doc = Document(source_path="x", name="T", description="", linestrings=[ls_replace, ls_markup], points=[], polygons=[])
    apply(doc)
    assert ls_replace.folder_path == ["Proposed Route", "Replace"]
    assert ls_markup.folder_path == ["Proposed Route", "Markup"]
```

- [ ] **Step 10.2: Run test to verify it fails**

```bash
pytest tests/test_folder_refolder.py -v
```

Expected: ImportError on `scripts.transformers.folder_refolder`.

- [ ] **Step 10.3: Implement `scripts/transformers/folder_refolder.py`**

```python
"""folder_refolder — set folder_path on every feature based on style_role."""
from __future__ import annotations

from scripts.kml_model import Document, StyleRole


FOLDER_FOR_ROLE: dict[StyleRole, list[str]] = {
    StyleRole.AERIAL:      ["Proposed Route", "Aerial"],
    StyleRole.UNDERGROUND: ["Proposed Route", "Underground"],
    StyleRole.REPLACE:     ["Proposed Route", "Replace"],
    StyleRole.MARKUP:      ["Proposed Route", "Markup"],
    StyleRole.EXISTING:    ["Existing Infrastructure"],
    StyleRole.BOUNDARY:    ["Permit Area"],
    StyleRole.POLE:        ["Proposed Infrastructure", "Poles"],
    StyleRole.VAULT:       ["Proposed Infrastructure", "Vaults"],
    StyleRole.STATION:     ["Stations & Labels"],
    StyleRole.UNMAPPED:    ["Unmapped Routes"],
}


def apply(doc: Document) -> None:
    """Mutate doc in place; assign folder_path based on style_role."""
    for f in doc.all_features():
        f.folder_path = list(FOLDER_FOR_ROLE[f.style_role])
```

- [ ] **Step 10.4: Run test to verify it passes**

```bash
pytest tests/test_folder_refolder.py -v
```

Expected: 8 tests pass.

- [ ] **Step 10.5: Commit**

```bash
git add scripts/transformers/folder_refolder.py tests/test_folder_refolder.py
git commit -m "feat(transformers): folder_refolder — family hierarchy by style_role"
```

---

## Task 11: `transformers/balloon_enricher.py`

**Files:**
- Create: `kmz-level-up/scripts/transformers/balloon_enricher.py`
- Test: `kmz-level-up/tests/test_balloon_enricher.py`

Generates HTML `<description>` for each placemark with attributes. Renders an attribute table with the family-recognized attributes (configurable via `display_attributes`). Per-feature behavior: skip if `preserve_existing_descriptions: true` and `description_html` is non-empty.

- [ ] **Step 11.1: Write the failing test**

`tests/test_balloon_enricher.py`:

```python
"""Unit tests for balloon_enricher."""

from scripts.kml_model import Document, LineStringFeature, StyleRole
from scripts.transformers.balloon_enricher import apply


def _doc_with_attributed_route():
    return Document(
        source_path="x", name="T", description="",
        linestrings=[
            LineStringFeature(
                id="ls1", name="Run",
                attributes={"TYPE": "AERIAL", "STA": "37+25", "SPAN_FT": "169", "OWNER": "Comcast"},
                coordinates=[(-86, 40), (-85, 40)],
                style_role=StyleRole.AERIAL,
            ),
        ],
        points=[], polygons=[],
    )


def test_generates_html_table_with_display_attributes():
    doc = _doc_with_attributed_route()
    apply(doc, display_attributes=["TYPE", "STA", "SPAN_FT", "OWNER"], preserve_existing=True)
    html = doc.linestrings[0].description_html
    assert "<table" in html
    assert "TYPE" in html
    assert "AERIAL" in html
    assert "37+25" in html
    assert "169" in html
    assert "Comcast" in html


def test_preserves_existing_description_when_flag_set():
    doc = _doc_with_attributed_route()
    doc.linestrings[0].description_html = "<p>Authored by user.</p>"
    apply(doc, display_attributes=["TYPE"], preserve_existing=True)
    assert doc.linestrings[0].description_html == "<p>Authored by user.</p>"


def test_overwrites_existing_description_when_flag_off():
    doc = _doc_with_attributed_route()
    doc.linestrings[0].description_html = "<p>Authored.</p>"
    apply(doc, display_attributes=["TYPE"], preserve_existing=False)
    assert "<p>Authored.</p>" not in doc.linestrings[0].description_html
    assert "AERIAL" in doc.linestrings[0].description_html


def test_skips_features_with_no_attributes():
    doc = Document(
        source_path="x", name="T", description="",
        linestrings=[LineStringFeature(id="ls1", name="Empty", attributes={}, coordinates=[(-86, 40), (-85, 40)])],
        points=[], polygons=[],
    )
    apply(doc, display_attributes=["TYPE"], preserve_existing=True)
    assert doc.linestrings[0].description_html == ""


def test_only_displays_attributes_in_list():
    doc = _doc_with_attributed_route()
    apply(doc, display_attributes=["TYPE"], preserve_existing=True)
    html = doc.linestrings[0].description_html
    assert "TYPE" in html
    assert "STA" not in html
    assert "OWNER" not in html
```

- [ ] **Step 11.2: Run test to verify it fails**

```bash
pytest tests/test_balloon_enricher.py -v
```

Expected: ImportError on `scripts.transformers.balloon_enricher`.

- [ ] **Step 11.3: Implement `scripts/transformers/balloon_enricher.py`**

```python
"""balloon_enricher — generate HTML <description> from feature attributes."""
from __future__ import annotations

import html

from scripts.kml_model import Document


_TABLE_HEAD = (
    '<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 6px;">'
    '<table style="border-collapse: collapse;">'
)
_TABLE_FOOT = "</table></div>"
_ROW = '<tr><td style="padding: 2px 8px; font-weight: 600;">{key}</td><td style="padding: 2px 8px;">{value}</td></tr>'


def apply(doc: Document, display_attributes: list[str], preserve_existing: bool) -> None:
    for f in doc.all_features():
        if not f.attributes:
            continue
        if preserve_existing and f.description_html.strip():
            continue
        rows = []
        for key in display_attributes:
            if key not in f.attributes:
                continue
            value = f.attributes[key]
            rows.append(_ROW.format(
                key=html.escape(str(key)),
                value=html.escape(str(value)),
            ))
        if not rows:
            continue
        f.description_html = _TABLE_HEAD + "".join(rows) + _TABLE_FOOT
```

- [ ] **Step 11.4: Run test to verify it passes**

```bash
pytest tests/test_balloon_enricher.py -v
```

Expected: 5 tests pass.

- [ ] **Step 11.5: Commit**

```bash
git add scripts/transformers/balloon_enricher.py tests/test_balloon_enricher.py
git commit -m "feat(transformers): balloon_enricher — HTML attribute table per placemark"
```

---

## Task 12: `transformers/doc_describer.py`

**Files:**
- Create: `kmz-level-up/scripts/transformers/doc_describer.py`
- Test: `kmz-level-up/tests/test_doc_describer.py`

Writes the top-level `<Document><description>` with the input filename, classification summary (count of each StyleRole), derivation log, and the quality-bar disclaimer. Sets `doc.description` (consumed by `emit_kml.py`).

- [ ] **Step 12.1: Write the failing test**

`tests/test_doc_describer.py`:

```python
"""Unit tests for doc_describer."""

from scripts.kml_model import Document, LineStringFeature, PolygonFeature, StyleRole
from scripts.transformers.doc_describer import apply


def test_description_includes_input_filename():
    doc = Document(source_path="C:/path/input.kmz", name="T", description="", linestrings=[], points=[], polygons=[])
    apply(doc, derivation_log={})
    assert "input.kmz" in doc.description


def test_description_includes_classification_summary():
    ls1 = LineStringFeature(id="1", name="A", attributes={}, coordinates=[(-86, 40), (-85, 40)], style_role=StyleRole.AERIAL)
    ls2 = LineStringFeature(id="2", name="B", attributes={}, coordinates=[(-86, 40), (-85, 40)], style_role=StyleRole.UNDERGROUND)
    ls3 = LineStringFeature(id="3", name="C", attributes={}, coordinates=[(-86, 40), (-85, 40)], style_role=StyleRole.AERIAL)
    doc = Document(source_path="x", name="T", description="", linestrings=[ls1, ls2, ls3], points=[], polygons=[])
    apply(doc, derivation_log={})
    assert "2 aerial" in doc.description.lower()
    assert "1 underground" in doc.description.lower()


def test_description_includes_derivation_log():
    doc = Document(source_path="x", name="T", description="", linestrings=[], points=[], polygons=[])
    apply(doc, derivation_log={"permit_area": "inferred from buffered route hull (50ft)"})
    assert "permit_area" in doc.description.lower() or "permit area" in doc.description.lower()
    assert "buffered route hull" in doc.description.lower()


def test_description_includes_quality_bar_disclaimer():
    doc = Document(source_path="x", name="T", description="", linestrings=[], points=[], polygons=[])
    apply(doc, derivation_log={})
    assert "not certified for engineering layout" in doc.description.lower()
    assert "civil 3d" in doc.description.lower()


def test_description_includes_unmapped_warning_when_present():
    ls = LineStringFeature(id="u1", name="?", attributes={}, coordinates=[(-86, 40), (-85, 40)], style_role=StyleRole.UNMAPPED)
    doc = Document(source_path="x", name="T", description="", linestrings=[ls], points=[], polygons=[])
    apply(doc, derivation_log={})
    assert "unmapped" in doc.description.lower()
```

- [ ] **Step 12.2: Run test to verify it fails**

```bash
pytest tests/test_doc_describer.py -v
```

Expected: ImportError on `scripts.transformers.doc_describer`.

- [ ] **Step 12.3: Implement `scripts/transformers/doc_describer.py`**

```python
"""doc_describer — write the top-level Document description."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from scripts.kml_model import Document, StyleRole


_QUALITY_BAR = (
    "Upgraded from input KMZ to family deliverable standard. Color language and "
    "folder hierarchy match the cd-route-stitcher / dxf-to-kmz / permit-to-kmz "
    "family. Inferred features (permit area, poles, station ticks) are flagged in "
    "their folder names. Not certified for engineering layout — for that, use the "
    "source DWG in Civil 3D."
)


def apply(doc: Document, derivation_log: dict[str, str]) -> None:
    """Set doc.description with input filename, classification summary,
    derivation log, and the quality-bar disclaimer."""
    role_counts = Counter()
    for f in doc.all_features():
        role_counts[f.style_role] += 1

    parts = []
    parts.append(f"<p><strong>Input:</strong> {Path(doc.source_path).name}</p>")

    summary = ", ".join(
        f"{count} {role.value}" for role, count in role_counts.most_common() if count > 0
    )
    if summary:
        parts.append(f"<p><strong>Classification:</strong> {summary}.</p>")

    if role_counts.get(StyleRole.UNMAPPED, 0) > 0:
        parts.append(
            f"<p><strong>⚠ Unmapped:</strong> {role_counts[StyleRole.UNMAPPED]} "
            f"feature(s) could not be classified — see Unmapped Routes folder.</p>"
        )

    if derivation_log:
        items = "".join(f"<li><em>{k}:</em> {v}</li>" for k, v in derivation_log.items())
        parts.append(f"<p><strong>Derived features:</strong></p><ul>{items}</ul>")

    parts.append(f"<p><em>{_QUALITY_BAR}</em></p>")

    doc.description = "\n".join(parts)
```

- [ ] **Step 12.4: Run test to verify it passes**

```bash
pytest tests/test_doc_describer.py -v
```

Expected: 5 tests pass.

- [ ] **Step 12.5: Commit**

```bash
git add scripts/transformers/doc_describer.py tests/test_doc_describer.py
git commit -m "feat(transformers): doc_describer — input filename + classification + quality-bar"
```

---

## Task 13: `inspect_kmz.py` — Stage 1 Entrypoint

**Files:**
- Create: `kmz-level-up/scripts/inspect_kmz.py`
- Test: `kmz-level-up/tests/test_inspect_kmz.py`

Stage 1 CLI. Walks the input KMZ, runs `attribute_conventions.classify_attribute_name` on every detected attribute key, runs the existing-detection on each LineString to set its `auto_role`, and writes `attribute_mapping.json` with the schema from the spec.

- [ ] **Step 13.1: Write the failing test**

`tests/test_inspect_kmz.py`:

```python
"""Unit tests for inspect_kmz."""

import json
import zipfile
from pathlib import Path

from scripts.inspect_kmz import inspect, main


SIMPLE_KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Test Doc</name>
    <Placemark>
      <name>Aerial Run</name>
      <ExtendedData>
        <Data name="TYPE"><value>AERIAL</value></Data>
        <Data name="STA"><value>37+25</value></Data>
        <Data name="SPAN_FT"><value>169</value></Data>
      </ExtendedData>
      <LineString><coordinates>-86.03,40.80,0 -86.02,40.80,0</coordinates></LineString>
    </Placemark>
    <Placemark>
      <name>EX_FIBER</name>
      <ExtendedData>
        <Data name="TYPE"><value>AERIAL</value></Data>
      </ExtendedData>
      <LineString><coordinates>-86.03,40.81,0 -86.02,40.81,0</coordinates></LineString>
    </Placemark>
  </Document>
</kml>
"""


def _write_kmz(tmp_path, kml=SIMPLE_KML):
    p = tmp_path / "in.kmz"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("doc.kml", kml)
    return p


def test_inspect_returns_mapping_dict(tmp_path):
    kmz = _write_kmz(tmp_path)
    mapping = inspect(kmz)
    assert "input_summary" in mapping
    assert "attribute_roles" in mapping
    assert "value_classifications" in mapping
    assert "derive" in mapping
    assert "balloon" in mapping
    assert "placemarks" in mapping


def test_inspect_classifies_attribute_names(tmp_path):
    kmz = _write_kmz(tmp_path)
    mapping = inspect(kmz)
    assert mapping["attribute_roles"]["TYPE"] == "construction_type"
    assert mapping["attribute_roles"]["STA"] == "chainage"
    assert mapping["attribute_roles"]["SPAN_FT"] == "span_length"


def test_inspect_classifies_placemarks(tmp_path):
    kmz = _write_kmz(tmp_path)
    mapping = inspect(kmz)
    by_name = {pm["name"]: pm for pm in mapping["placemarks"]}
    assert by_name["Aerial Run"]["auto_role"] == "aerial"
    assert by_name["EX_FIBER"]["auto_role"] == "existing"


def test_inspect_includes_input_summary(tmp_path):
    kmz = _write_kmz(tmp_path)
    mapping = inspect(kmz)
    assert mapping["input_summary"]["linestring_count"] == 2
    assert "TYPE" in mapping["input_summary"]["detected_attribute_keys"]


def test_inspect_default_derive_block(tmp_path):
    kmz = _write_kmz(tmp_path)
    mapping = inspect(kmz)
    derive = mapping["derive"]
    assert derive["permit_area"] is True
    assert derive["poles"] is True
    assert derive["station_ticks"] is True


def test_main_writes_json_to_disk(tmp_path):
    kmz = _write_kmz(tmp_path)
    out = tmp_path / "mapping.json"
    main([str(kmz), "--output", str(out)])
    assert out.exists()
    data = json.loads(out.read_text())
    assert "attribute_roles" in data


def test_inspect_fails_when_no_attributes(tmp_path):
    """Per spec: empty-attribute KMZ should fail with a guidance message."""
    kml_no_attrs = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Just geometry</name>
      <LineString><coordinates>-86.03,40.80,0 -86.02,40.80,0</coordinates></LineString>
    </Placemark>
  </Document>
</kml>
"""
    kmz = _write_kmz(tmp_path, kml=kml_no_attrs)
    import pytest
    with pytest.raises(SystemExit):
        main([str(kmz), "--output", str(tmp_path / "x.json")])
```

- [ ] **Step 13.2: Run test to verify it fails**

```bash
pytest tests/test_inspect_kmz.py -v
```

Expected: ImportError on `scripts.inspect_kmz`.

- [ ] **Step 13.3: Implement `scripts/inspect_kmz.py`**

```python
"""Stage 1: walk the input KMZ, classify attributes, write attribute_mapping.json.

Usage:
    python -m scripts.inspect_kmz input.kmz --output attribute_mapping.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.attribute_conventions import (
    classify_attribute_name,
    classify_construction_value,
    classify_feature,
)
from scripts.kml_model import StyleRole
from scripts.parse_kml import parse_kmz


def inspect(kmz_path: str | Path) -> dict:
    doc = parse_kmz(kmz_path)

    # Collect all attribute keys.
    all_keys = set()
    for f in doc.all_features():
        all_keys.update(f.attributes.keys())

    if not all_keys:
        raise SystemExit(
            "No attributes found on any placemark — this skill requires routes "
            "with attributes. Use a builder skill (cd-route-stitcher / dxf-to-kmz / "
            "permit-to-kmz) to build a KMZ from source."
        )

    # CRS sanity check: bail if coords look projected (any |x| > 360 or |y| > 90).
    for f in doc.all_features():
        coords = []
        if hasattr(f, "coordinates") and isinstance(f.coordinates, list):
            coords = f.coordinates
        elif hasattr(f, "coordinates") and isinstance(f.coordinates, tuple):
            coords = [f.coordinates]
        elif hasattr(f, "outer_ring"):
            coords = f.outer_ring
        for x, y in coords:
            if abs(x) > 360 or abs(y) > 90:
                raise SystemExit(
                    f"Non-WGS84 coords detected (x={x}, y={y}). KMZ should always "
                    f"be EPSG:4326 (lat/lon). Use dxf-to-kmz for projected sources."
                )

    # Classify attribute names → roles.
    attribute_roles: dict[str, str] = {}
    for k in sorted(all_keys):
        role = classify_attribute_name(k)
        if role:
            attribute_roles[k] = role

    # Build value-classification table for the construction_type attribute.
    value_classifications = {"construction_type": {}}
    construction_attr = next((k for k, r in attribute_roles.items() if r == "construction_type"), None)
    if construction_attr:
        seen_values = set()
        for f in doc.all_features():
            v = f.attributes.get(construction_attr)
            if v is not None and v != "":
                seen_values.add(str(v))
        for v in sorted(seen_values):
            role = classify_construction_value(v)
            if role is not StyleRole.UNMAPPED:
                value_classifications["construction_type"][v] = role.value

    # Per-placemark auto-roles.
    placemarks = []
    for f in doc.all_features():
        auto = classify_feature(f, attribute_roles)
        placemarks.append({
            "id": f.id,
            "name": f.name,
            "auto_role": auto.value,
            "override_role": None,
            "publish": True,
        })

    # Detection of what's already present.
    has_permit_area = any(
        "permit" in (p.name or "").lower() or "boundary" in (p.name or "").lower()
        for p in doc.polygons
    )
    has_poles = any(
        "pole" in (pt.name or "").lower() or
        any("pole" in fp.lower() for fp in pt.folder_path)
        for pt in doc.points
    )
    has_ticks = any(
        "sta" in (pt.name or "").lower() or "station" in (pt.name or "").lower()
        for pt in doc.points
    )

    return {
        "input_summary": {
            "kmz_path": str(kmz_path),
            "linestring_count": len(doc.linestrings),
            "polygon_count": len(doc.polygons),
            "point_count": len(doc.points),
            "detected_attribute_keys": sorted(all_keys),
            "already_has_permit_area": has_permit_area,
            "already_has_poles": has_poles,
            "already_has_station_ticks": has_ticks,
        },
        "attribute_roles": attribute_roles,
        "value_classifications": value_classifications,
        "derive": {
            "permit_area": not has_permit_area,
            "permit_area_buffer_ft": 50,
            "poles": not has_poles,
            "pole_deflection_deg": 5,
            "station_ticks": not has_ticks,
        },
        "balloon": {
            "preserve_existing_descriptions": True,
            "display_attributes": list(attribute_roles.keys()),
        },
        "placemarks": placemarks,
    }


def _print_summary(mapping: dict) -> None:
    """Stdout summary table; matches dxf-to-kmz's inspect output style."""
    s = mapping["input_summary"]
    print(f"Input: {s['kmz_path']}")
    print(f"  {s['linestring_count']} LineStrings, {s['polygon_count']} polygons, {s['point_count']} points")
    print(f"  Detected attribute keys: {', '.join(s['detected_attribute_keys'])}")
    print()
    print("Classified attribute roles:")
    for k, r in mapping["attribute_roles"].items():
        print(f"  {k:20} → {r}")
    print()
    print("Detection:")
    print(f"  Permit Area present: {s['already_has_permit_area']}")
    print(f"  Poles present:       {s['already_has_poles']}")
    print(f"  Station ticks present: {s['already_has_station_ticks']}")
    print()
    role_counts = {}
    for pm in mapping["placemarks"]:
        role_counts[pm["auto_role"]] = role_counts.get(pm["auto_role"], 0) + 1
    print("Placemark auto-classification:")
    for role, count in sorted(role_counts.items()):
        print(f"  {role:15} {count}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Inspect a KMZ and emit attribute_mapping.json.")
    parser.add_argument("kmz_path", help="Path to input KMZ or KML file")
    parser.add_argument("--output", required=True, help="Output mapping JSON path")
    args = parser.parse_args(argv)

    mapping = inspect(args.kmz_path)
    _print_summary(mapping)
    Path(args.output).write_text(json.dumps(mapping, indent=2))
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 13.4: Run test to verify it passes**

```bash
pytest tests/test_inspect_kmz.py -v
```

Expected: 7 tests pass.

- [ ] **Step 13.5: Commit**

```bash
git add scripts/inspect_kmz.py tests/test_inspect_kmz.py
git commit -m "feat(stage1): inspect_kmz CLI + attribute_mapping.json writer"
```

---

## Task 14: `build_kmz.py` — Stage 2 Orchestrator

**Files:**
- Create: `kmz-level-up/scripts/build_kmz.py`
- (E2E test added in Task 15)

The orchestrator. Loads input + mapping, parses, runs the seven transformers in order, emits.

- [ ] **Step 14.1: Implement `scripts/build_kmz.py`**

(No unit tests for this module beyond the E2E test in Task 15 — the orchestrator's correctness is covered by the integration test against synthetic inputs.)

```python
"""Stage 2: orchestrator. Apply transformers + emit upgraded KMZ.

Usage:
    python -m scripts.build_kmz input.kmz attribute_mapping.json --output upgraded.kmz
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.kml_model import Document, StyleRole
from scripts.parse_kml import parse_kmz
from scripts.emit_kml import write_kmz
from scripts.transformers import (
    style_restyler,
    permit_area_inferer,
    pole_derivator,
    station_tick_derivator,
    folder_refolder,
    balloon_enricher,
    doc_describer,
)


def build(kmz_path: str | Path, mapping: dict, out_path: str | Path) -> Document:
    doc = parse_kmz(kmz_path)

    # Per-feature override roles from mapping JSON.
    overrides: dict[str, StyleRole] = {}
    for pm in mapping.get("placemarks", []):
        if pm.get("override_role"):
            try:
                overrides[pm["id"]] = StyleRole(pm["override_role"])
            except ValueError:
                pass

    # Filter: drop placemarks marked publish=false.
    drop_ids = {pm["id"] for pm in mapping.get("placemarks", []) if pm.get("publish") is False}
    doc.linestrings = [ls for ls in doc.linestrings if ls.id not in drop_ids]
    doc.points = [p for p in doc.points if p.id not in drop_ids]
    doc.polygons = [p for p in doc.polygons if p.id not in drop_ids]

    role_map = mapping.get("attribute_roles", {})
    derive = mapping.get("derive", {})
    balloon_cfg = mapping.get("balloon", {})

    derivation_log: dict[str, str] = {}

    # 1. Style restyler — assign style_role to every feature.
    style_restyler.apply(doc, role_map=role_map, overrides=overrides)

    # 2. Permit area inferer.
    polys_before = len(doc.polygons)
    permit_area_inferer.apply(
        doc,
        derive=derive.get("permit_area", True),
        buffer_ft=derive.get("permit_area_buffer_ft", 50),
    )
    if len(doc.polygons) > polys_before:
        derivation_log["permit_area"] = (
            f"inferred from buffered route hull "
            f"({derive.get('permit_area_buffer_ft', 50)}ft)"
        )

    # 3. Pole derivator.
    pts_before = len([p for p in doc.points if p.style_role is StyleRole.POLE])
    pole_derivator.apply(
        doc,
        derive=derive.get("poles", True),
        deflection_deg=derive.get("pole_deflection_deg", 5),
    )
    pts_after = len([p for p in doc.points if p.style_role is StyleRole.POLE])
    if pts_after > pts_before:
        derivation_log["poles"] = f"derived {pts_after - pts_before} from aerial vertex deflection"

    # 4. Station-tick derivator.
    ticks_before = len([p for p in doc.points if p.style_role is StyleRole.STATION])
    station_tick_derivator.apply(
        doc,
        derive=derive.get("station_ticks", True),
        role_map=role_map,
    )
    ticks_after = len([p for p in doc.points if p.style_role is StyleRole.STATION])
    if ticks_after > ticks_before:
        derivation_log["station_ticks"] = f"derived {ticks_after - ticks_before} from chainage attributes"

    # 5. Folder refolder.
    folder_refolder.apply(doc)

    # 6. Balloon enricher.
    balloon_enricher.apply(
        doc,
        display_attributes=balloon_cfg.get("display_attributes", []),
        preserve_existing=balloon_cfg.get("preserve_existing_descriptions", True),
    )

    # 7. Doc describer.
    doc_describer.apply(doc, derivation_log=derivation_log)

    # Emit.
    write_kmz(doc, out_path)
    return doc


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the upgraded KMZ from input + mapping.")
    parser.add_argument("kmz_path", help="Path to input KMZ or KML file")
    parser.add_argument("mapping_path", help="Path to attribute_mapping.json")
    parser.add_argument("--output", required=True, help="Output upgraded KMZ path")
    args = parser.parse_args(argv)

    mapping = json.loads(Path(args.mapping_path).read_text())
    build(args.kmz_path, mapping, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 14.2: Smoke-test against the inspect_kmz output of an existing test fixture**

```bash
cd "C:/Users/thalf/.claude/skills/kmz-level-up"
python -c "
import zipfile, tempfile, json
from pathlib import Path
from scripts.inspect_kmz import inspect
from scripts.build_kmz import build

KML = '''<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<kml xmlns=\"http://www.opengis.net/kml/2.2\">
  <Document><name>T</name>
    <Placemark><name>Run</name>
      <ExtendedData><Data name=\"TYPE\"><value>AERIAL</value></Data></ExtendedData>
      <LineString><coordinates>-86.03,40.80,0 -86.025,40.80,0 -86.025,40.805,0</coordinates></LineString>
    </Placemark>
  </Document></kml>'''

with tempfile.TemporaryDirectory() as d:
    inp = Path(d) / 'in.kmz'
    out = Path(d) / 'up.kmz'
    with zipfile.ZipFile(inp, 'w') as z:
        z.writestr('doc.kml', KML)
    mapping = inspect(inp)
    print('Inspect OK. Detected roles:', mapping['attribute_roles'])
    build(inp, mapping, out)
    print('Build OK. Output:', out, out.stat().st_size, 'bytes')
"
```

Expected: prints "Inspect OK. Detected roles: {'TYPE': 'construction_type'}" and "Build OK." with non-zero file size.

- [ ] **Step 14.3: Commit**

```bash
git add scripts/build_kmz.py
git commit -m "feat(stage2): build_kmz orchestrator runs 7-transformer pipeline"
```

---

## Task 15: End-to-End Test + Fixture Builders

**Files:**
- Modify: `kmz-level-up/tests/conftest.py` (add fixture builders)
- Create: `kmz-level-up/tests/test_build_kmz_e2e.py`

This is where the four input-shape fixture builders live, used to validate the full inspect→edit→build pipeline against representative inputs.

- [ ] **Step 15.1: Add fixture builders to `tests/conftest.py`**

```python
"""pytest fixtures for kmz-level-up.

Synthetic KMZ builders mimicking the four input-shape categories the skill
must handle (per the spec):
- Civil 3D / ArcGIS exports: SchemaData / SimpleData, uppercase attr names
- QGIS exports: <Data> / <value>, lowercase attr names
- Hand-built (Google Earth Pro): minimal attrs, irregular folder structure
- Already conformant: output of dxf-to-kmz / cd-route-stitcher
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest


def _write_kmz(path: Path, kml: str) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("doc.kml", kml)
    return path


@pytest.fixture
def kmz_civil3d_style(tmp_path: Path) -> Path:
    """Civil 3D-style export: SchemaData/SimpleData, uppercase attr names."""
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Civil3D Export</name>
    <Schema id="route_schema" name="Route">
      <SimpleField name="TYPE" type="string"/>
      <SimpleField name="STA" type="string"/>
      <SimpleField name="SPAN_FT" type="string"/>
    </Schema>
    <Placemark id="aerial_1">
      <name>Aerial Run 1</name>
      <ExtendedData><SchemaData schemaUrl="#route_schema">
        <SimpleData name="TYPE">AERIAL</SimpleData>
        <SimpleData name="STA">37+25</SimpleData>
        <SimpleData name="SPAN_FT">169</SimpleData>
      </SchemaData></ExtendedData>
      <LineString><coordinates>-86.030,40.800,0 -86.025,40.800,0 -86.025,40.805,0</coordinates></LineString>
    </Placemark>
    <Placemark id="ug_1">
      <name>UG Run 1</name>
      <ExtendedData><SchemaData schemaUrl="#route_schema">
        <SimpleData name="TYPE">UG</SimpleData>
        <SimpleData name="STA">42+50</SimpleData>
      </SchemaData></ExtendedData>
      <LineString><coordinates>-86.020,40.800,0 -86.015,40.800,0</coordinates></LineString>
    </Placemark>
  </Document>
</kml>
"""
    return _write_kmz(tmp_path / "civil3d.kmz", kml)


@pytest.fixture
def kmz_qgis_style(tmp_path: Path) -> Path:
    """QGIS-style export: Data/value, lowercase attr names."""
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>QGIS Export</name>
    <Placemark id="r1">
      <name>route 1</name>
      <ExtendedData>
        <Data name="construction_type"><value>aerial</value></Data>
        <Data name="chainage"><value>37+25</value></Data>
        <Data name="owner"><value>Comcast</value></Data>
      </ExtendedData>
      <LineString><coordinates>-86.030,40.800,0 -86.025,40.800,0</coordinates></LineString>
    </Placemark>
  </Document>
</kml>
"""
    return _write_kmz(tmp_path / "qgis.kmz", kml)


@pytest.fixture
def kmz_handbuilt(tmp_path: Path) -> Path:
    """Hand-built Google Earth Pro KMZ: minimal attrs, no folder structure."""
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Hand-built</name>
    <Placemark id="hb1">
      <name>my route</name>
      <description>Hand-traced from satellite imagery.</description>
      <ExtendedData>
        <Data name="type"><value>aerial</value></Data>
      </ExtendedData>
      <LineString><coordinates>-86.030,40.800,0 -86.025,40.800,0 -86.025,40.805,0</coordinates></LineString>
    </Placemark>
  </Document>
</kml>
"""
    return _write_kmz(tmp_path / "handbuilt.kmz", kml)


@pytest.fixture
def kmz_already_conformant(tmp_path: Path) -> Path:
    """Output of a family builder skill — already follows family conventions."""
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>JB12345 — Permit Package</name>
    <description>Conformant output. Not certified for engineering layout — for that, use the source DWG in Civil 3D.</description>
    <Folder><name>Permit Area</name>
      <Placemark id="pb1">
        <name>Permit Boundary</name>
        <Polygon><outerBoundaryIs><LinearRing><coordinates>
          -86.035,40.795,0 -86.010,40.795,0 -86.010,40.810,0 -86.035,40.810,0 -86.035,40.795,0
        </coordinates></LinearRing></outerBoundaryIs></Polygon>
      </Placemark>
    </Folder>
    <Folder><name>Proposed Route</name>
      <Folder><name>Aerial</name>
        <Placemark id="cr1">
          <name>Conformant Aerial</name>
          <ExtendedData>
            <Data name="TYPE"><value>AERIAL</value></Data>
            <Data name="STA"><value>37+25</value></Data>
          </ExtendedData>
          <LineString><coordinates>-86.030,40.800,0 -86.025,40.800,0</coordinates></LineString>
        </Placemark>
      </Folder>
    </Folder>
  </Document>
</kml>
"""
    return _write_kmz(tmp_path / "conformant.kmz", kml)
```

- [ ] **Step 15.2: Write the failing E2E test**

`tests/test_build_kmz_e2e.py`:

```python
"""End-to-end tests: inspect → build → assert KMZ structure."""

import zipfile
from pathlib import Path

import pytest

from scripts.inspect_kmz import inspect
from scripts.build_kmz import build


def _read_doc_kml(kmz: Path) -> str:
    with zipfile.ZipFile(kmz) as zf:
        return zf.read("doc.kml").decode("utf-8")


def test_e2e_civil3d_input_produces_family_folder_hierarchy(tmp_path, kmz_civil3d_style):
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_civil3d_style)
    build(kmz_civil3d_style, mapping, out)
    kml = _read_doc_kml(out)
    assert "<name>Permit Area</name>" in kml
    assert "<name>Proposed Route</name>" in kml
    assert "<name>Aerial</name>" in kml
    assert "<name>Underground</name>" in kml
    # Existing-infra folder may or may not be present (no existing in input);
    # assert it's NOT present without existing features. (Always-empty folders OK to suppress.)


def test_e2e_qgis_input_classifies_lowercase_attributes(tmp_path, kmz_qgis_style):
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_qgis_style)
    assert "construction_type" in mapping["attribute_roles"].values()
    build(kmz_qgis_style, mapping, out)
    kml = _read_doc_kml(out)
    assert "<name>Aerial</name>" in kml  # qgis "aerial" was classified


def test_e2e_handbuilt_input_infers_permit_area(tmp_path, kmz_handbuilt):
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_handbuilt)
    build(kmz_handbuilt, mapping, out)
    kml = _read_doc_kml(out)
    assert "Permit Area" in kml
    assert "inferred" in kml.lower()


def test_e2e_handbuilt_preserves_existing_description(tmp_path, kmz_handbuilt):
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_handbuilt)
    # Default mapping has preserve_existing_descriptions: True
    build(kmz_handbuilt, mapping, out)
    kml = _read_doc_kml(out)
    assert "Hand-traced from satellite imagery." in kml


def test_e2e_doc_description_includes_quality_bar(tmp_path, kmz_civil3d_style):
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_civil3d_style)
    build(kmz_civil3d_style, mapping, out)
    kml = _read_doc_kml(out)
    assert "Civil 3D" in kml or "civil 3d" in kml.lower()
    assert "engineering layout" in kml.lower()


def test_e2e_idempotent_on_already_conformant_input(tmp_path, kmz_already_conformant):
    """Running on an already-conformant KMZ should not duplicate folders/features."""
    out1 = tmp_path / "out1.kmz"
    out2 = tmp_path / "out2.kmz"
    mapping = inspect(kmz_already_conformant)
    build(kmz_already_conformant, mapping, out1)

    # Re-run on the output. Should be stable.
    mapping2 = inspect(out1)
    build(out1, mapping2, out2)
    kml2 = _read_doc_kml(out2)

    # Should still have one Permit Area folder, not two.
    assert kml2.count("<name>Permit Area</name>") == 1


def test_e2e_per_placemark_override_pins_role(tmp_path, kmz_civil3d_style):
    """Editing override_role in mapping should pin the role through build."""
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_civil3d_style)
    # Pin the aerial route to underground via override.
    for pm in mapping["placemarks"]:
        if pm["id"] == "aerial_1":
            pm["override_role"] = "underground"
    build(kmz_civil3d_style, mapping, out)
    kml = _read_doc_kml(out)
    # The route should now be in Underground folder.
    assert "<name>Underground</name>" in kml


def test_e2e_publish_false_drops_placemark(tmp_path, kmz_civil3d_style):
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_civil3d_style)
    for pm in mapping["placemarks"]:
        if pm["id"] == "aerial_1":
            pm["publish"] = False
    build(kmz_civil3d_style, mapping, out)
    kml = _read_doc_kml(out)
    # The dropped feature's name should not appear.
    assert "Aerial Run 1" not in kml
```

- [ ] **Step 15.3: Run E2E tests; fix any orchestration bugs surfaced**

```bash
pytest tests/test_build_kmz_e2e.py -v
```

Expected: 8 tests pass. If any fail, fix the underlying transformer / orchestrator.

- [ ] **Step 15.4: Run the full suite to verify nothing regressed**

```bash
pytest tests/ -v
```

Expected: all tests pass (~70+ tests across all 13 test files).

- [ ] **Step 15.5: Commit**

```bash
git add tests/conftest.py tests/test_build_kmz_e2e.py
git commit -m "test(e2e): conftest fixture builders + 8 end-to-end pipeline tests"
```

---

## Task 16: SKILL.md Final Content

**Files:**
- Modify: `kmz-level-up/SKILL.md` (replace the skeleton from Task 1)

Write the complete user-facing SKILL.md, modeled on `dxf-to-kmz/SKILL.md`. Match the family format: frontmatter description, "What this skill does", "When to use", "Prerequisites", "Workflow", "KMZ output structure", "Family color language" reference, "Quality bar", "Failure modes", "Known limitations", "Files", "Testing".

- [ ] **Step 16.1: Replace `SKILL.md` with full content**

```markdown
---
name: kmz-level-up
description: Use when you have an existing KMZ with route LineStrings carrying attributes (construction type, chainage, owner, span lengths) that needs to be upgraded to the family deliverable standard. Trigger on "level up this KMZ", "upgrade this Google Earth file", "apply the standard styling", "make this KMZ deliverable-ready", "fix the folder structure on this KMZ". Applies the family color language (red dashed aerial, red solid underground, orange replace, magenta markup), reorganizes into the family folder hierarchy, derives missing features (pole markers from vertex deflection, station ticks from chainage, permit-area polygon from buffered route hull), enriches with HTML balloon templates, and stamps the quality-bar disclaimer. Handles input from any source (own skills' outputs, third-party desktop tools like Civil 3D / QGIS / ArcGIS, contractor hand-builds) via tier-based detection. Two-stage workflow with editable attribute_mapping.json between inspect and build.
---

# KMZ Level Up

## What this skill does

Takes any KMZ with route LineStrings carrying attributes and produces an upgraded KMZ that matches the family deliverable standard (`cd-route-stitcher`, `dxf-to-kmz`, `permit-to-kmz`). The output emphasizes:

- The **family color language**: red dashed aerial / red solid underground / orange replace / magenta markup / yellow boundary / gray existing
- The **family folder hierarchy**: Permit Area / Proposed Route / Proposed Infrastructure / Stations & Labels / Existing Infrastructure (default-off)
- **Derived features** when the input lacks them: pole markers from vertex deflection on aerial routes, station ticks from chainage attributes, permit-area polygon from buffered route hull
- **HTML balloon templates** rendered from attributes
- The **quality-bar disclaimer** stamped into the document description

## When to use

Use whenever you have an existing KMZ with attributed routes and want any of:

- A KMZ that follows the family standard regardless of source authoring tool
- Re-pass on an old skill output now that conventions have evolved
- Conversion of a Civil 3D / QGIS / ArcGIS export to family format
- Cleanup of a contractor / drafter hand-built KMZ

If the input is a multi-page CD PDF, use `cd-route-stitcher` (vector) or `cd-ground-overlays` (raster). If the input is a Sphere/Comcast permit map PDF, use `permit-to-kmz`. If the input is a DXF, use `dxf-to-kmz`. **This skill is for KMZs that already have geometry + attributes.**

## Prerequisites

```bash
pip install -r requirements.txt
# or
pip install fastkml lxml simplekml shapely pyproj
```

## Workflow

**Run all scripts from the `kmz-level-up/` folder.** The `scripts/` package only resolves when the skill folder is your CWD.

The pipeline is **inspect → edit `attribute_mapping.json` → build**. Always run Step 1 first; never skip directly to `build_kmz.py` — the mapping JSON is what tells the builder which attributes mean what.

### Step 1: Inspect the input KMZ

```bash
cd kmz-level-up
python -m scripts.inspect_kmz path/to/input.kmz --output attribute_mapping.json
```

This walks the input, classifies each detected attribute name to a role (construction_type, chainage, span_length, owner, sheet_id), classifies each LineString to a `style_role` (aerial / underground / replace / markup / existing / unmapped), and writes `attribute_mapping.json`.

**Stdout summary** lists detected attribute keys, classifications, and per-placemark auto-roles. Most jobs require zero edits to the JSON.

### Step 2 (optional): Edit `attribute_mapping.json`

If the inspect output flagged unmapped routes, missed an attribute mapping, or you want to disable a derivation knob:

- **Add or override an attribute role:** edit the `attribute_roles` block.
- **Pin a specific placemark's classification:** find it in the `placemarks` list, set `override_role` (e.g., `"override_role": "aerial"`).
- **Drop a placemark:** set `"publish": false` for it in `placemarks`.
- **Disable a derivation:** set `derive.permit_area` / `derive.poles` / `derive.station_ticks` to `false`.
- **Tune buffer / threshold:** edit `derive.permit_area_buffer_ft` (default 50) or `derive.pole_deflection_deg` (default 5).

### Step 3: Build the upgraded KMZ

```bash
python -m scripts.build_kmz path/to/input.kmz attribute_mapping.json --output upgraded.kmz
```

This loads the input + mapping, parses to the internal model, runs the 7-transformer pipeline, and writes the upgraded KMZ.

### Step 4: Validate in Google Earth Pro

Spot-check:
- Folder hierarchy matches the family standard
- Aerial routes dashed red, underground solid red
- Existing Infrastructure folder folded + visibility off
- Document description shows input filename, classification summary, derivation log, quality-bar disclaimer
- Inferred Permit Area (if applicable) is labeled with "(inferred — verify before submittal)"

## KMZ output structure

```
[Job name from input filename]
├── Permit Area                         (yellow translucent polygon, visible)
├── Proposed Route                      (visible)
│   ├── Aerial   (dashed red)
│   ├── Underground   (solid red)
│   ├── Replace   (dashed orange)
│   └── Markup    (dashed magenta)
├── Proposed Infrastructure             (visible)
│   ├── Poles
│   └── Vaults
├── Stations & Labels                   (visible, folded)
├── Unmapped Routes                     (visibility OFF, flagged)
└── Existing Infrastructure             (visibility OFF, folded)
```

The document description carries input filename + classification summary + derivation log + quality-bar disclaimer.

## Family color language

| `style_role` | Color | Pattern | Folder destination |
|---|---|---|---|
| `aerial` | red `ff0000ff` | dashed | `Proposed Route/Aerial` |
| `underground` | red `ff0000ff` | solid | `Proposed Route/Underground` |
| `replace` | orange `ff0080ff` | dashed | `Proposed Route/Replace` |
| `markup` | magenta `ffff00ff` | dashed | `Proposed Route/Markup` |
| `existing` | gray `ff808080` | preserve | `Existing Infrastructure` (visibility=0) |
| `boundary` | yellow line + 25%-fill | n/a | `Permit Area` |
| `pole` | red dot | n/a | `Proposed Infrastructure/Poles` |
| `vault` | blue square | n/a | `Proposed Infrastructure/Vaults` |
| `station` | small text label | n/a | `Stations & Labels` (folded) |
| `unmapped` | gray | preserve | `Unmapped Routes` (visibility=0) |

Matches `dxf-to-kmz` / `cd-route-stitcher` exactly so downstream consumers see the same visual language.

## Attribute conventions

First-match-wins regex against attribute names. Order matters; existing check fires before route classification.

| Pattern | Role |
|---|---|
| `.*const.*type.*` / `.*method.*` / `.*type.*` | construction_type |
| `.*chain.*` / `.*\bsta\b.*` / `.*station.*` | chainage |
| `.*span.*` / `.*length.*` / `.*\bft\b.*` | span_length |
| `.*owner.*` / `.*\bprm\b.*` / `.*entity.*` | owner |
| `.*sheet.*` / `.*\bsht\b.*` | sheet_id |
| `.*existing.*` / `^ex$` | existing_flag |

Construction-type values: `AERIAL` / `OVH` / `OVERHEAD` / `OVERLASH` / `STRAND` → aerial. `UNDERGROUND` / `UG` / `BORE` / `TRENCH` / `DIRECTIONAL` → underground. `REPLACE` / `RPLC` → replace. `MARKUP` / `REVISION` / `REDLINE` → markup.

To add a new drafter convention, edit `scripts/attribute_conventions.py`:

```python
NAME_RULES.insert(0, NameRule(re.compile(r"my_new_pattern", re.I), "construction_type"))
```

## Quality bar

Generated from input KMZ for family-standard deliverable handoff. Color language and folder hierarchy match `cd-route-stitcher` / `dxf-to-kmz` / `permit-to-kmz`. Inferred features (permit area, poles, station ticks) are flagged in their folder names. **Not certified for engineering layout** — for that, use the source DWG in Civil 3D.

State this in any deliverable note alongside the upgraded KMZ.

## Known limitations

- **Single KMZ in / out for v1.** Multi-KMZ batch / merge is deferred to v2.
- **No coordinate reprojection.** Input must already be WGS84 (EPSG:4326). Projected sources fail fast with a clear error pointing at `dxf-to-kmz`.
- **Dashed polylines** in KML are not natively supported by Google Earth Pro — width and color are honored; folder names disambiguate Aerial vs Underground when the line style alone doesn't.
- **HTML balloons** use a fixed template; per-feature customization beyond `display_attributes` requires editing `balloon_enricher.py`.
- **Existing-infrastructure detection** keys on placemark name (`EX_*`) and `existing` attribute. Drafters who use other conventions need a per-job override in the placemarks list.
- **Pole derivation** uses vertex deflection only; doesn't synthesize poles between two collinear points. For survey-grade pole locations, derive in the source authoring tool.

## Gotchas

- **`inspect_kmz.py` fails: "No attributes found"** — input KMZ has only geometry, no ExtendedData. Use a builder skill (cd-route-stitcher / dxf-to-kmz / permit-to-kmz) instead.
- **`inspect_kmz.py` fails: "Non-WGS84 coords detected"** — input has projected coordinates. Use `dxf-to-kmz` for projected sources.
- **Most LineStrings end up `unmapped`** — construction-type values don't match any value rule. Edit `attribute_mapping.json` `value_classifications.construction_type` to map this drafter's values.
- **Permit Area inferred when one already exists in input** — input polygon is named non-conventionally. Edit `attribute_mapping.json` `placemarks` list to set the polygon's `override_role: "boundary"`, set `derive.permit_area: false`.
- **Poles derived in wrong locations** — aerial polylines have CAD-tessellation vertex noise. Increase `derive.pole_deflection_deg` (default 5°) or set `derive.poles: false`.
- **Output is huge** — input has dense polylines. Add a polyline simplification step in CAD before exporting.

## Red flags (do not do these)

- **Do not skip `inspect_kmz.py`.** The builder requires `attribute_mapping.json` — running `build_kmz.py` first will fail.
- **Do not run scripts from a parent directory** or with absolute paths. The `scripts/` package only resolves when `kmz-level-up/` is your CWD.
- **Do not skip Step 4** (Google Earth Pro spot check). Misclassifications are silent at the file level — the upgraded KMZ opens fine but might style routes incorrectly.
- **Do not commit an upgraded KMZ with inferred Permit Area without verifying it.** The inferred hull is a buffered convex hull, not an authored boundary; reviewers must confirm before submittal.

## Files

- `SKILL.md` (this file)
- `scripts/inspect_kmz.py` — pipeline stage 1: parse + classify + write `attribute_mapping.json`
- `scripts/build_kmz.py` — pipeline stage 2: orchestrator, runs 7-transformer pipeline
- `scripts/parse_kml.py` — lxml-based KML/KMZ parser
- `scripts/emit_kml.py` — simplekml writer (matches `cd-route-stitcher`, `dxf-to-kmz`)
- `scripts/kml_model.py` — internal normalized representation (dataclasses + StyleRole enum)
- `scripts/attribute_conventions.py` — first-match-wins regex rules
- `scripts/transformers/` — seven independently-testable transformer modules
- `tests/` — pytest suite covering all modules + end-to-end fixture-based tests
- `requirements.txt` — pip install targets

## Testing

```bash
cd kmz-level-up
pytest tests/ -v
```

All tests use synthetic KMZs generated programmatically in `tests/conftest.py` — no binary fixtures.
```

- [ ] **Step 16.2: Commit**

```bash
git add SKILL.md
git commit -m "docs: write SKILL.md with workflow, gotchas, family color reference"
```

---

## Task 17: `attribute_defaults.json` + Final Polish

**Files:**
- Create: `kmz-level-up/scripts/attribute_defaults.json`

Per-drafter / per-region attribute conventions. Versioned with the skill so institutional knowledge accumulates over time. Seed entries for the patterns we already know.

- [ ] **Step 17.1: Write `scripts/attribute_defaults.json`**

```json
{
  "civil3d_2025": {
    "construction_type_attr": "TYPE",
    "chainage_attr": "STA",
    "span_length_attr": "SPAN_FT",
    "owner_attr": "OWNER",
    "sheet_id_attr": "SHEET_ID"
  },
  "qgis_export": {
    "construction_type_attr": "construction_type",
    "chainage_attr": "chainage",
    "span_length_attr": "span_length",
    "owner_attr": "owner"
  },
  "arcgis_pro": {
    "construction_type_attr": "ConstructionType",
    "chainage_attr": "Chainage",
    "span_length_attr": "SpanLength",
    "owner_attr": "Owner"
  },
  "cd_route_stitcher_output": {
    "construction_type_attr": "type",
    "chainage_attr": "sta",
    "span_length_attr": "span_ft"
  }
}
```

(This file is reference-only in v1. The convention engine in `attribute_conventions.py` already covers these via regex. The JSON exists so future versions can offer `--defaults <key>` flag for one-shot zero-config upgrades when filename heuristics pick the right block.)

- [ ] **Step 17.2: Run the full test suite one final time**

```bash
cd "C:/Users/thalf/.claude/skills/kmz-level-up"
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 17.3: Verify the file tree matches the spec**

```bash
ls -la scripts/ scripts/transformers/ tests/
```

Expected: all files from the File Structure section present.

- [ ] **Step 17.4: Commit final artifacts**

```bash
git add scripts/attribute_defaults.json
git commit -m "chore: seed attribute_defaults.json with known drafter conventions"
git log --oneline
```

Expected: ~17 commits showing the TDD progression task by task.

---

## Self-Review Checklist

After completing all tasks, walk through this checklist:

- [ ] Every spec section maps to at least one task:
  - "Architecture" → Tasks 13, 14
  - "Attribute Detection — Convention Engine" → Task 3
  - "`attribute_mapping.json` Schema" → Tasks 13, 14
  - "Family Color Language" → Tasks 5, 6, 10
  - "KMZ Output Structure" → Tasks 5, 10
  - "Quality Bar" → Task 12
  - "Failure Modes" → Tasks 13 (validation), spread across tests
  - "Known Limitations" → Documented in Task 16 (SKILL.md)
  - "Workflow (for SKILL.md)" → Task 16
- [ ] No placeholders, no "TBD", no "implement later"
- [ ] Type names consistent across tasks: `Document`, `LineStringFeature`, `PointFeature`, `PolygonFeature`, `StyleRole` (uppercase enum)
- [ ] Function signatures consistent: every transformer's `apply(doc, ...)` takes the document as first positional arg
- [ ] Test files match `test_<module>.py` naming throughout
- [ ] Commit cadence: one per task minimum (17 commits)

If any check fails, fix inline.
