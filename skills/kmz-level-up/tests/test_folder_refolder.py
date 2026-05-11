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
