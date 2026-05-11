"""Unit tests for kml_model -- dataclasses + StyleRole enum."""

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
