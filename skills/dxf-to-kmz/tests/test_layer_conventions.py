"""Tests for layer_conventions.classify(layer_name) → feature dict."""
import pytest

from scripts.layer_conventions import classify


@pytest.mark.parametrize("layer_name,expected", [
    # Permit boundary variants
    ("PERMIT_BOUNDARY",     {"feature": "polygon", "subtype": "boundary", "publish": True}),
    ("WORK_AREA",           {"feature": "polygon", "subtype": "boundary", "publish": True}),
    ("ROW_LIMITS",          {"feature": "polygon", "subtype": "boundary", "publish": True}),
    # Aerial fiber variants
    ("E_FIBER_AERIAL_NEW",  {"feature": "route",   "subtype": "aerial",   "publish": True}),
    ("FIBER_OVH",           {"feature": "route",   "subtype": "aerial",   "publish": True}),
    # Underground fiber variants
    ("E_FIBER_UG_BORE",     {"feature": "route",   "subtype": "underground", "publish": True}),
    ("FIBER_UNDERGRD",      {"feature": "route",   "subtype": "underground", "publish": True}),
    ("FIBER_TRENCH",        {"feature": "route",   "subtype": "underground", "publish": True}),
    # Replace / markup
    ("REPLACE_FIBER",       {"feature": "route",   "subtype": "replace",  "publish": True}),
    ("MARKUP_REVISIONS",    {"feature": "route",   "subtype": "markup",   "publish": True}),
    # Points
    ("PROPOSED_POLE",       {"feature": "point",   "subtype": "pole-new", "publish": True}),
    ("NEW_POLE",            {"feature": "point",   "subtype": "pole-new", "publish": True}),
    ("VAULT",               {"feature": "point",   "subtype": "vault",    "publish": True}),
    ("HANDHOLE_4",          {"feature": "point",   "subtype": "vault",    "publish": True}),
    # Existing — default OFF
    ("EX_POLE",             {"feature": "point",   "subtype": "existing", "publish": False}),
    ("EX_FIBER",            {"feature": "route",   "subtype": "existing", "publish": False}),
    ("E_EXISTING_VAULT",    {"feature": "point",   "subtype": "existing", "publish": False}),
    # Stations
    ("STATION_LABELS",      {"feature": "label",   "subtype": "station",  "publish": True}),
    # Unmapped
    ("RANDOM_TEXT_LAYER_42", {"feature": None,     "subtype": None,       "publish": False}),
    # First-match-wins precedence guards: if a name matches multiple rules,
    # earlier rules in RULES must win. These lock in order so reordering breaks tests.
    ("AERIAL_BORE",         {"feature": "route",   "subtype": "aerial",   "publish": True}),
    ("EX_PERMIT_BOUND",     {"feature": "polygon", "subtype": "boundary", "publish": True}),
])
def test_classify_known_patterns(layer_name, expected):
    result = classify(layer_name)
    assert result["feature"] == expected["feature"]
    assert result["subtype"] == expected["subtype"]
    assert result["publish"] == expected["publish"]


def test_classify_text_layer_does_not_match_ex_rule():
    """Regression: bare 'TEXT' must not match the EX rule (T-EX-T contains 'EX')."""
    result = classify("TEXT")
    # TEXT shouldn't be treated as existing-infrastructure
    assert result["subtype"] != "existing"


def test_classify_records_matched_rule():
    result = classify("E_FIBER_AERIAL_NEW")
    assert result["matched_rule"]  # non-empty string
    assert "AER" in result["matched_rule"]


def test_classify_provides_default_style():
    result = classify("PERMIT_BOUNDARY")
    style = result["style"]
    assert style["fill_color"].endswith("00ffff")  # yellow with alpha
    assert "line_color" in style


def test_classify_aerial_is_dashed_solid_underground():
    aerial = classify("E_FIBER_AERIAL_NEW")
    underground = classify("E_FIBER_UG_BORE")
    assert aerial["style"]["dashed"] is True
    assert underground["style"]["dashed"] is False
