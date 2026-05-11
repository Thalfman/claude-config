"""Unit tests for emit_kml -- simplekml writer."""

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


def test_write_kmz_renders_polygon_with_green_translucent_fill(tmp_path):
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
    # Bright green translucent: line ff00ff00, fill 8000ff00
    assert "ff00ff00" in kml
    assert "8000ff00" in kml


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
