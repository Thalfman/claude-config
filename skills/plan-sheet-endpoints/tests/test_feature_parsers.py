from scripts.feature_parsers import (
    parse_cable_specs,
    parse_construction_type,
    parse_road_names,
    parse_span_lengths,
    parse_structures,
)


def test_parse_road_names_finds_common_suffixes():
    text = "Route along E 250 N RD, crossing MAIN ST and OAK AVE"
    roads = parse_road_names(text)
    assert "E 250 N RD" in roads
    assert "MAIN ST" in roads
    assert "OAK AVE" in roads


def test_parse_road_names_returns_empty_for_no_match():
    assert parse_road_names("no street suffixes here") == []


def test_parse_road_names_deduplicates():
    text = "MAIN ST runs into MAIN ST"
    assert parse_road_names(text) == ["MAIN ST"]


def test_parse_structures_pole_n():
    structures = parse_structures("POLE 32, POLE 33, P-15, STR #42")
    assert "POLE 32" in structures
    assert "POLE 33" in structures
    assert "P-15" in structures
    assert "STR #42" in structures


def test_parse_structures_returns_empty():
    assert parse_structures("no structures here") == []


def test_parse_span_lengths_apostrophe_form():
    spans = parse_span_lengths("260' span, then 316' to next pole")
    assert 260.0 in spans
    assert 316.0 in spans


def test_parse_span_lengths_ft_form():
    spans = parse_span_lengths("Span: 260 FT followed by 316 ft")
    assert 260.0 in spans
    assert 316.0 in spans


def test_parse_span_lengths_returns_empty():
    assert parse_span_lengths("no measurements") == []


def test_parse_construction_type_aerial():
    assert parse_construction_type("OVERLASH ON EXISTING STRAND, AERIAL ROUTE") == "aerial"


def test_parse_construction_type_underground():
    assert parse_construction_type("BORE AND PLACE 2\" CONDUIT, UNDERGROUND") == "underground"


def test_parse_construction_type_direct_bore():
    assert parse_construction_type("DIRECTIONAL BORE under highway") == "direct_bore"


def test_parse_construction_type_trench():
    assert parse_construction_type("OPEN TRENCH along right-of-way") == "trench"


def test_parse_construction_type_returns_none():
    assert parse_construction_type("plain descriptive text") is None


def test_parse_cable_specs_fiber_count():
    assert parse_cable_specs("288F SM FIBER") == "288F"


def test_parse_cable_specs_count_form():
    assert parse_cable_specs("Place 144 COUNT cable") == "144 COUNT"


def test_parse_cable_specs_returns_none():
    assert parse_cable_specs("nothing fiber-y") is None
