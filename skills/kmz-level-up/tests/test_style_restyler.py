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


def test_existing_point_name_takes_precedence():
    """A point named EX_POLE_42 should get style_role EXISTING."""
    from scripts.kml_model import PointFeature
    pt = PointFeature(id="ex_pt", name="EX_POLE_42", attributes={}, coordinates=(-86, 40))
    doc = Document(source_path="x", name="T", description="", linestrings=[], points=[pt], polygons=[])
    apply(doc, role_map={})
    assert doc.points[0].style_role is StyleRole.EXISTING


def test_polygon_without_boundary_name_stays_unmapped_even_with_route_attribute():
    """A polygon with TYPE=AERIAL but a non-boundary name should stay UNMAPPED, not become AERIAL."""
    from scripts.kml_model import PolygonFeature
    poly = PolygonFeature(
        id="weird", name="Some Polygon", attributes={"TYPE": "AERIAL"},
        outer_ring=[(-86, 40), (-85, 40), (-85, 41), (-86, 41), (-86, 40)],
    )
    doc = Document(source_path="x", name="T", description="", linestrings=[], points=[], polygons=[poly])
    apply(doc, role_map={"TYPE": "construction_type"})
    assert doc.polygons[0].style_role is StyleRole.UNMAPPED  # not AERIAL
