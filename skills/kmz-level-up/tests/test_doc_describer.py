"""Unit tests for doc_describer."""

from scripts.kml_model import Document, LineStringFeature, PolygonFeature, StyleRole
from scripts.transformers.doc_describer import apply


def test_description_includes_input_filename():
    doc = Document(source_path="C:/path/input.kmz", name="T", description="", linestrings=[], points=[], polygons=[])
    apply(doc, derivation_log={})
    assert "input.kmz" in doc.description


def test_description_includes_crs_provenance():
    doc = Document(source_path="x", name="T", description="", linestrings=[], points=[], polygons=[])
    apply(doc, derivation_log={})
    assert "WGS84" in doc.description
    assert "EPSG:4326" in doc.description


def test_description_excludes_commentary():
    """No classification summary, derivation log, unmapped warning, or quality-bar disclaimer."""
    ls = LineStringFeature(id="u1", name="?", attributes={}, coordinates=[(-86, 40), (-85, 40)], style_role=StyleRole.UNMAPPED)
    doc = Document(source_path="x", name="T", description="", linestrings=[ls], points=[], polygons=[])
    apply(doc, derivation_log={"permit_area": "inferred from buffered route hull (50ft)"})
    body = doc.description.lower()
    assert "classification" not in body
    assert "derived features" not in body
    assert "unmapped" not in body
    assert "not certified" not in body
    assert "civil 3d" not in body
    assert "buffered route hull" not in body
