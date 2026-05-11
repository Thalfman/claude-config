"""Unit tests for pole_derivator."""

from scripts.kml_model import Document, LineStringFeature, PointFeature, StyleRole
from scripts.transformers.pole_derivator import apply


def _doc_with_aerial_route():
    """A 4-vertex aerial route. Vertex 1 has a 90 degree turn (clear pole),
    vertex 2 is straight (no pole)."""
    return Document(
        source_path="x", name="T", description="",
        linestrings=[
            LineStringFeature(
                id="ls1", name="Run",
                attributes={},
                coordinates=[
                    (-86.030, 40.800),  # endpoint
                    (-86.025, 40.800),  # 90 degree turn
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
    # The 90 degree turn at (-86.025, 40.800) should produce a pole.
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
    """A 10 degree deflection vertex with threshold 30 degrees should not produce a pole."""
    ls = LineStringFeature(
        id="ls1", name="Run", attributes={},
        coordinates=[
            (0.0, 0.0),
            (1.0, 0.0),
            (1.5, 0.087),  # ~10 degree deflection from the previous segment
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
