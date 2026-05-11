"""Unit tests for attribute_conventions -- regex classification rules."""

from scripts.attribute_conventions import (
    classify_attribute_name,
    classify_construction_value,
    classify_feature,
)
from scripts.kml_model import LineStringFeature, StyleRole


def test_classify_name_construction_type_variants():
    for key in ("TYPE", "type", "construction_type", "const_type", "MAT_TYPE", "method"):
        assert classify_attribute_name(key) == "construction_type"


def test_classify_name_chainage_variants():
    for key in ("STA", "sta", "chainage", "station", "chain_ft"):
        assert classify_attribute_name(key) == "chainage"


def test_classify_name_span_length_variants():
    for key in ("SPAN_FT", "span", "length", "span_length"):
        assert classify_attribute_name(key) == "span_length"


def test_classify_name_owner_variants():
    for key in ("OWNER", "owner", "PRM", "entity"):
        assert classify_attribute_name(key) == "owner"


def test_classify_name_sheet_id_variants():
    for key in ("SHEET_ID", "sheet", "SHT_NUM"):
        assert classify_attribute_name(key) == "sheet_id"


def test_classify_name_unmatched_returns_none():
    assert classify_attribute_name("RANDOM_FIELD_42") is None


def test_classify_construction_value_aerial():
    for v in ("AERIAL", "aerial", "OVH", "OVERHEAD", "OVERLASH", "STRAND"):
        assert classify_construction_value(v) == StyleRole.AERIAL


def test_classify_construction_value_underground():
    for v in ("UNDERGROUND", "UG", "BORE", "TRENCH", "DIRECTIONAL"):
        assert classify_construction_value(v) == StyleRole.UNDERGROUND


def test_classify_construction_value_replace():
    for v in ("REPLACE", "RPLC"):
        assert classify_construction_value(v) == StyleRole.REPLACE


def test_classify_construction_value_markup():
    for v in ("MARKUP", "REVISION", "REDLINE", "RED"):
        assert classify_construction_value(v) == StyleRole.MARKUP


def test_classify_construction_value_unrecognized_is_unmapped():
    assert classify_construction_value("XYZ") == StyleRole.UNMAPPED


def test_classify_feature_existing_takes_precedence_over_construction():
    """A feature named EX_FIBER_AERIAL should be classified as existing,
    not aerial, even though the construction-type would match aerial."""
    f = LineStringFeature(
        id="ex1",
        name="EX_FIBER_AERIAL",
        attributes={"TYPE": "AERIAL"},
        coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
    )
    role_map = {"TYPE": "construction_type"}
    role = classify_feature(f, role_map)
    assert role == StyleRole.EXISTING


def test_classify_feature_existing_attribute_truthy():
    """A feature with existing=true attribute is classified as existing
    regardless of name or construction type."""
    f = LineStringFeature(
        id="x1",
        name="Some Line",
        attributes={"existing": True, "TYPE": "AERIAL"},
        coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
    )
    role_map = {"TYPE": "construction_type"}
    role = classify_feature(f, role_map)
    assert role == StyleRole.EXISTING


def test_classify_feature_aerial_normal_path():
    f = LineStringFeature(
        id="a1",
        name="Run 1",
        attributes={"TYPE": "AERIAL"},
        coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
    )
    role_map = {"TYPE": "construction_type"}
    role = classify_feature(f, role_map)
    assert role == StyleRole.AERIAL


def test_classify_feature_no_construction_attr_is_unmapped():
    f = LineStringFeature(
        id="u1",
        name="Run 2",
        attributes={"OTHER": "value"},
        coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
    )
    role_map = {}
    role = classify_feature(f, role_map)
    assert role == StyleRole.UNMAPPED


def test_classify_feature_word_boundary_ex_does_not_false_positive():
    """A name like 'TEXT_LINE' should NOT match the EX existing rule."""
    f = LineStringFeature(
        id="t1",
        name="TEXT_LINE",
        attributes={"TYPE": "AERIAL"},
        coordinates=[(-86.03, 40.80), (-86.02, 40.80)],
    )
    role_map = {"TYPE": "construction_type"}
    role = classify_feature(f, role_map)
    assert role == StyleRole.AERIAL  # not EXISTING
