"""Unit tests for polygon-dominant input flow:

- HTML-table description fallback in parse_kml
- polygon_handling block emission in inspect_kmz
- polygon_merger transformer
- folder_refolder polygon_handling routing
- style_restyler polygon_handling style_override
- emit_kml MultiGeometry path
- end-to-end Sphere-style fixture build
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pytest

from scripts.build_kmz import build
from scripts.emit_kml import write_kmz
from scripts.inspect_kmz import inspect
from scripts.kml_model import Document, PolygonFeature, StyleRole
from scripts.parse_kml import parse_kmz, _parse_html_table_attrs
from scripts.transformers import folder_refolder, polygon_merger, style_restyler


SPHERE_KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document id="Permits_v2_Sphere">
    <name>Permits_v2_Sphere</name>
    <Folder>
      <Placemark id="ID_00000">
        <name>SEG-A1</name>
        <description><![CDATA[<html><body><table border="1">
          <tr><th>Field Name</th><th>Field Value</th></tr>
          <tr><td>Segment_Name</td><td>SEG-A1</td></tr>
          <tr><td>JBNumber</td><td>JB001</td></tr>
          <tr><td>Unique_ID</td><td>PRM100</td></tr>
          <tr><td>Build_Status</td><td>Received</td></tr>
          <tr><td>Jurisdiction</td><td>INDOT</td></tr>
          <tr><td>Notes</td><td>Null</td></tr>
        </table></body></html>]]></description>
        <Polygon><outerBoundaryIs><LinearRing>
          <coordinates>-86.04,40.79,0 -86.03,40.79,0 -86.03,40.80,0 -86.04,40.80,0 -86.04,40.79,0</coordinates>
        </LinearRing></outerBoundaryIs></Polygon>
      </Placemark>
      <Placemark id="ID_00001">
        <name>SEG-A2</name>
        <description><![CDATA[<html><body><table border="1">
          <tr><th>Field Name</th><th>Field Value</th></tr>
          <tr><td>Segment_Name</td><td>SEG-A2</td></tr>
          <tr><td>JBNumber</td><td>JB001</td></tr>
          <tr><td>Unique_ID</td><td>PRM100</td></tr>
          <tr><td>Build_Status</td><td>Received</td></tr>
          <tr><td>Jurisdiction</td><td>INDOT</td></tr>
        </table></body></html>]]></description>
        <Polygon><outerBoundaryIs><LinearRing>
          <coordinates>-86.05,40.79,0 -86.045,40.79,0 -86.045,40.80,0 -86.05,40.80,0 -86.05,40.79,0</coordinates>
        </LinearRing></outerBoundaryIs></Polygon>
      </Placemark>
      <Placemark id="ID_00002">
        <name>SEG-B1</name>
        <description><![CDATA[<html><body><table border="1">
          <tr><th>Field Name</th><th>Field Value</th></tr>
          <tr><td>Segment_Name</td><td>SEG-B1</td></tr>
          <tr><td>JBNumber</td><td>JB002</td></tr>
          <tr><td>Unique_ID</td><td>PRM200</td></tr>
          <tr><td>Build_Status</td><td>Received</td></tr>
          <tr><td>Jurisdiction</td><td>PERU UTILITIES</td></tr>
        </table></body></html>]]></description>
        <Polygon><outerBoundaryIs><LinearRing>
          <coordinates>-86.06,40.78,0 -86.055,40.78,0 -86.055,40.79,0 -86.06,40.79,0 -86.06,40.78,0</coordinates>
        </LinearRing></outerBoundaryIs></Polygon>
      </Placemark>
    </Folder>
  </Document>
</kml>
"""


@pytest.fixture
def sphere_kmz(tmp_path: Path) -> Path:
    """Sphere-style export: polygons + HTML-table attributes in <description>."""
    p = tmp_path / "sphere.kmz"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("doc.kml", SPHERE_KML)
    return p


# ------- parse_kml HTML-table fallback -------

def test_parse_html_table_attrs_pulls_two_cell_rows():
    html = """<table>
        <tr><th>Field Name</th><th>Field Value</th></tr>
        <tr><td>JBNumber</td><td>JB001</td></tr>
        <tr><td>Unique_ID</td><td>PRM100</td></tr>
    </table>"""
    out = _parse_html_table_attrs(html)
    assert out == {"JBNumber": "JB001", "Unique_ID": "PRM100"}


def test_parse_html_table_strips_inline_tags_and_decodes_entities():
    html = "<tr><td><b>Notes</b></td><td>R&amp;D &lt;flagged&gt;</td></tr>"
    out = _parse_html_table_attrs(html)
    assert out == {"Notes": "R&D <flagged>"}


def test_parse_html_table_skips_header_synonym_keys():
    html = "<tr><td>Field Name</td><td>Field Value</td></tr><tr><td>Real</td><td>Yes</td></tr>"
    out = _parse_html_table_attrs(html)
    assert "Field Name" not in out
    assert out == {"Real": "Yes"}


def test_parse_kmz_falls_back_to_html_table_when_no_extendeddata(sphere_kmz: Path):
    doc = parse_kmz(sphere_kmz)
    assert len(doc.polygons) == 3
    poly = doc.polygons[0]
    assert poly.attributes["JBNumber"] == "JB001"
    assert poly.attributes["Unique_ID"] == "PRM100"
    assert poly.attributes["Build_Status"] == "Received"
    assert poly.attributes["Jurisdiction"] == "INDOT"
    assert poly.attributes["Notes"] == "Null"


# ------- inspect_kmz polygon_handling emission -------

def test_inspect_emits_polygon_handling_for_polygon_dominant_input(sphere_kmz: Path):
    mapping = inspect(sphere_kmz)
    assert mapping["input_summary"]["polygon_dominant"] is True
    ph = mapping["polygon_handling"]
    assert ph["enabled"] is True
    assert ph["group_by"] == ["JBNumber"]
    assert ph["merge_at"] == "Unique_ID"
    assert ph["style_by"] == "Build_Status"
    assert "{Unique_ID}" in ph["placemark_label_template"]


def test_inspect_disables_permit_area_inference_when_polygon_dominant(sphere_kmz: Path):
    mapping = inspect(sphere_kmz)
    assert mapping["derive"]["permit_area"] is False


def test_inspect_polygon_dominant_overwrites_existing_descriptions(sphere_kmz: Path):
    mapping = inspect(sphere_kmz)
    assert mapping["balloon"]["preserve_existing_descriptions"] is False


# ------- polygon_merger transformer -------

def _doc_with_two_groups() -> Document:
    polys = [
        PolygonFeature(
            id=f"id_{i}", name=f"SEG-{i}",
            attributes={"JBNumber": jb, "Unique_ID": prm},
            outer_ring=[(-86 + i * 0.001, 40, 0), (-86 + i * 0.001 + 0.0005, 40, 0),
                        (-86 + i * 0.001 + 0.0005, 40.001, 0), (-86 + i * 0.001, 40.001, 0)],
            style_role=StyleRole.BOUNDARY,
        )
        for i, (jb, prm) in enumerate([("JB1", "PRM_A"), ("JB1", "PRM_A"), ("JB1", "PRM_B"), ("JB2", "PRM_C")])
    ]
    return Document(source_path="x", name="T", description="", polygons=polys)


def test_polygon_merger_collapses_same_unique_id_into_one_feature():
    doc = _doc_with_two_groups()
    removed = polygon_merger.apply(doc, polygon_handling={
        "enabled": True, "group_by": ["JBNumber"], "merge_at": "Unique_ID",
    })
    assert removed == 1  # PRM_A had 2 members; one moved to extra_parts
    assert len(doc.polygons) == 3
    primary = next(p for p in doc.polygons if p.attributes["Unique_ID"] == "PRM_A")
    assert len(primary.extra_parts) == 1


def test_polygon_merger_no_op_when_disabled():
    doc = _doc_with_two_groups()
    removed = polygon_merger.apply(doc, polygon_handling={"enabled": False})
    assert removed == 0
    assert len(doc.polygons) == 4


def test_polygon_merger_renders_label_template():
    doc = _doc_with_two_groups()
    polygon_merger.apply(doc, polygon_handling={
        "enabled": True, "group_by": ["JBNumber"], "merge_at": "Unique_ID",
        "placemark_label_template": "{Unique_ID} permit",
    })
    names = sorted(p.name for p in doc.polygons)
    assert names == ["PRM_A permit", "PRM_B permit", "PRM_C permit"]


def test_polygon_merger_strips_orphan_separators_from_template():
    """When a referenced field is Null, the trailing separator should be cleaned up."""
    polys = [
        PolygonFeature(
            id="p1", name="x",
            attributes={"JBNumber": "JB1", "Unique_ID": "PRM1", "Jurisdiction": "Null"},
            outer_ring=[(-86, 40), (-86.001, 40), (-86.001, 40.001), (-86, 40.001)],
            style_role=StyleRole.BOUNDARY,
        ),
    ]
    doc = Document(source_path="x", name="T", description="", polygons=polys)
    polygon_merger.apply(doc, polygon_handling={
        "enabled": True, "group_by": ["JBNumber"], "merge_at": "Unique_ID",
        "placemark_label_template": "{Unique_ID} - {Jurisdiction}",
    })
    assert doc.polygons[0].name == "PRM1"


# ------- folder_refolder polygon_handling routing -------

def test_folder_refolder_uses_group_by_for_polygons():
    polys = [
        PolygonFeature(
            id="p1", name="A",
            attributes={"JBNumber": "JB100", "Unique_ID": "PRM_A"},
            outer_ring=[(-86, 40), (-86.001, 40), (-86.001, 40.001), (-86, 40.001)],
            style_role=StyleRole.BOUNDARY,
        ),
    ]
    doc = Document(source_path="x", name="T", description="", polygons=polys)
    folder_refolder.apply(doc, polygon_handling={
        "enabled": True, "group_by": ["JBNumber"],
    })
    assert doc.polygons[0].folder_path == ["JB100"]


def test_folder_refolder_inserts_top_folder_when_named():
    polys = [
        PolygonFeature(
            id="p1", name="A",
            attributes={"JBNumber": "JB100"},
            outer_ring=[(-86, 40), (-86.001, 40), (-86.001, 40.001), (-86, 40.001)],
            style_role=StyleRole.BOUNDARY,
        ),
    ]
    doc = Document(source_path="x", name="T", description="", polygons=polys)
    folder_refolder.apply(doc, polygon_handling={
        "enabled": True, "top_folder_name": "Permits", "group_by": ["JBNumber"],
    })
    assert doc.polygons[0].folder_path == ["Permits", "JB100"]


def test_folder_refolder_keeps_default_when_polygon_handling_disabled():
    polys = [
        PolygonFeature(
            id="p1", name="A",
            attributes={"JBNumber": "JB1"},
            outer_ring=[(-86, 40), (-86.001, 40), (-86.001, 40.001), (-86, 40.001)],
            style_role=StyleRole.BOUNDARY,
        ),
    ]
    doc = Document(source_path="x", name="T", description="", polygons=polys)
    folder_refolder.apply(doc, polygon_handling=None)
    assert doc.polygons[0].folder_path == ["Permit Area"]


# ------- style_restyler polygon_handling override -------

def test_style_restyler_applies_status_styles_when_polygon_handling_active():
    polys = [
        PolygonFeature(
            id="p1", name="A",
            attributes={"Build_Status": "Received"},
            outer_ring=[(-86, 40), (-86.001, 40), (-86.001, 40.001), (-86, 40.001)],
        ),
    ]
    doc = Document(source_path="x", name="T", description="", polygons=polys)
    style_restyler.apply(
        doc, role_map={}, overrides={},
        polygon_handling={
            "enabled": True,
            "style_by": "Build_Status",
            "status_styles": {"Received": {"line": "ff00ff00", "fill": "8000ff00"}},
        },
    )
    assert doc.polygons[0].style_role == StyleRole.BOUNDARY
    assert doc.polygons[0].style_override == {"line": "ff00ff00", "fill": "8000ff00"}


def test_style_restyler_falls_back_to_default_style_when_status_unknown():
    polys = [
        PolygonFeature(
            id="p1", name="A",
            attributes={"Build_Status": "WeirdStatus"},
            outer_ring=[(-86, 40), (-86.001, 40), (-86.001, 40.001), (-86, 40.001)],
        ),
    ]
    doc = Document(source_path="x", name="T", description="", polygons=polys)
    style_restyler.apply(
        doc, role_map={}, overrides={},
        polygon_handling={
            "enabled": True,
            "style_by": "Build_Status",
            "status_styles": {},
            "default_style": {"line": "ff00ff00", "fill": "8000ff00"},
        },
    )
    assert doc.polygons[0].style_override == {"line": "ff00ff00", "fill": "8000ff00"}


# ------- emit_kml MultiGeometry -------

def test_emit_kml_writes_multigeometry_for_polygons_with_extra_parts(tmp_path: Path):
    poly = PolygonFeature(
        id="p1", name="MERGED",
        attributes={},
        outer_ring=[(-86, 40), (-86.001, 40), (-86.001, 40.001), (-86, 40.001)],
        extra_parts=[
            ([(-86.01, 40), (-86.011, 40), (-86.011, 40.001), (-86.01, 40.001)], []),
        ],
        style_role=StyleRole.BOUNDARY,
        folder_path=["JB1"],
    )
    doc = Document(source_path="x", name="T", description="", polygons=[poly])
    out = tmp_path / "out.kmz"
    write_kmz(doc, out)
    with zipfile.ZipFile(out) as z:
        kml = z.read("doc.kml").decode("utf-8")
    assert "<MultiGeometry" in kml
    # primary + 1 extra part. simplekml may emit <Polygon id="N"> rather than
    # <Polygon>, so count any Polygon open tag.
    assert len(re.findall(r"<Polygon\b", kml)) == 2


# ------- end-to-end -------

def test_e2e_sphere_input_collapses_to_unique_prms(tmp_path: Path, sphere_kmz: Path):
    out = tmp_path / "out.kmz"
    mapping = inspect(sphere_kmz)
    build(sphere_kmz, mapping, out)
    with zipfile.ZipFile(out) as z:
        kml = z.read("doc.kml").decode("utf-8")
    # 3 polygons -> 2 distinct PRMs (PRM100 has 2 polygons that should merge).
    placemarks = re.findall(r"<Placemark", kml)
    assert len(placemarks) == 2
    folders = re.findall(r"<Folder\b", kml)
    # JB001 and JB002 -> 2 folders.
    assert len(folders) == 2
    # Family bright-green boundary style (default + 50% alpha fill).
    assert "ff00ff00" in kml
    assert "8000ff00" in kml
    # MultiGeometry created for the merged PRM100.
    assert "<MultiGeometry" in kml
    # Cleaned balloon (Null Notes row suppressed).
    assert "Notes" not in kml or re.search(r"<td[^>]*>Null</td>", kml) is None


def test_e2e_sphere_input_skips_permit_area_inference(tmp_path: Path, sphere_kmz: Path):
    out = tmp_path / "out.kmz"
    mapping = inspect(sphere_kmz)
    build(sphere_kmz, mapping, out)
    with zipfile.ZipFile(out) as z:
        kml = z.read("doc.kml").decode("utf-8")
    # No "Permit Area" wrapper since polygons themselves are the permit areas.
    # (The default folder for BOUNDARY would be "Permit Area" but polygon_handling
    # routes them under JB folders instead.)
    assert "<name>Permit Area</name>" not in kml
