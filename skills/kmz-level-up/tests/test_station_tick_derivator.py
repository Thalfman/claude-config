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
