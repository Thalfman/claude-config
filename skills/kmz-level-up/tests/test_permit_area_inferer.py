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
    assert poly.name == "Permit Area"
    assert poly.attributes.get("_inferred") == "true"


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
