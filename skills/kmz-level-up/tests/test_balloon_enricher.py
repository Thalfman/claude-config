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
