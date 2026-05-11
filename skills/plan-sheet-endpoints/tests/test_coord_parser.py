# tests/test_coord_parser.py
import pytest

from scripts.coord_parser import parse_decimal_degrees
from scripts.coord_parser import parse_dms


def test_parse_dd_signed_pair():
    assert parse_decimal_degrees("34.123456, -118.123456") == pytest.approx((34.123456, -118.123456))


def test_parse_dd_hemisphere_suffix():
    assert parse_decimal_degrees("34.123456 N, 118.123456 W") == pytest.approx((34.123456, -118.123456))


def test_parse_dd_hemisphere_with_degree_symbol():
    assert parse_decimal_degrees("34.123456° N, 118.123456° W") == pytest.approx((34.123456, -118.123456))


def test_parse_dd_lat_lon_labels():
    assert parse_decimal_degrees("LAT: 34.123456 LON: -118.123456") == pytest.approx((34.123456, -118.123456))


def test_parse_dd_southern_hemisphere():
    assert parse_decimal_degrees("33.86 S, 151.20 E") == pytest.approx((-33.86, 151.20))


def test_parse_dd_returns_none_for_no_match():
    assert parse_decimal_degrees("just some text with no coords") is None


def test_parse_dd_rejects_out_of_range_latitude():
    assert parse_decimal_degrees("234.567890, -118.123456") is None


def test_parse_dd_labeled_with_hemisphere_markers():
    """Issue I1 regression: labeled coords with hemisphere markers must apply the sign."""
    assert parse_decimal_degrees("LATITUDE: 33.86 S LONGITUDE: 151.20 E") == pytest.approx((-33.86, 151.20))


def test_parse_dms_with_symbols():
    lat, lon = parse_dms("34° 07' 24.4\" N, 118° 07' 24.4\" W")
    assert lat == pytest.approx(34.12344, abs=1e-4)
    assert lon == pytest.approx(-118.12344, abs=1e-4)


def test_parse_dms_with_d_m_s_letters():
    lat, lon = parse_dms("34d 07m 24.4s N, 118d 07m 24.4s W")
    assert lat == pytest.approx(34.12344, abs=1e-4)
    assert lon == pytest.approx(-118.12344, abs=1e-4)


def test_parse_dms_dash_separated():
    lat, lon = parse_dms("34-07-24.4N 118-07-24.4W")
    assert lat == pytest.approx(34.12344, abs=1e-4)
    assert lon == pytest.approx(-118.12344, abs=1e-4)


def test_parse_dms_returns_none_for_no_match():
    assert parse_dms("plain text 34.5, -118.5") is None


from scripts.coord_parser import parse_utm


def test_parse_utm_zone_letter_form():
    # Zone 11N near Los Angeles
    lat, lon = parse_utm("Zone 11N, 372345 E, 3776543 N")
    assert lat == pytest.approx(34.12, abs=0.05)
    assert lon == pytest.approx(-118.38, abs=0.05)


def test_parse_utm_compact_form():
    lat, lon = parse_utm("UTM 11N 372345E 3776543N")
    assert lat == pytest.approx(34.12, abs=0.05)
    assert lon == pytest.approx(-118.38, abs=0.05)


def test_parse_utm_southern_hemisphere():
    # Zone 56H (Sydney area)
    lat, lon = parse_utm("Zone 56H 334897 E 6252001 N")
    assert lat == pytest.approx(-33.86, abs=0.05)
    assert lon == pytest.approx(151.21, abs=0.05)


def test_parse_utm_returns_none_for_no_match():
    assert parse_utm("plain text no zones here") is None


from scripts.coord_parser import parse_coords, find_all_coords


def test_parse_coords_picks_decimal_first():
    result = parse_coords("LAT: 34.123456 LON: -118.123456 (also 34d 07m 24.4s N 118d 07m 24.4s W)")
    assert result is not None
    lat, lon, fmt = result
    assert fmt == "decimal_degrees"
    assert lat == pytest.approx(34.123456, abs=1e-4)


def test_parse_coords_falls_through_to_dms():
    result = parse_coords("Reference: 34° 07' 24.4\" N, 118° 07' 24.4\" W")
    assert result is not None
    lat, lon, fmt = result
    assert fmt == "dms"
    assert lat == pytest.approx(34.12344, abs=1e-4)


def test_parse_coords_falls_through_to_utm():
    result = parse_coords("Stamp: Zone 11N 372345 E 3776543 N")
    assert result is not None
    lat, lon, fmt = result
    assert fmt == "utm"
    assert lat == pytest.approx(34.12, abs=0.05)


def test_parse_coords_returns_none_for_no_match():
    assert parse_coords("no coords in this text") is None


def test_find_all_coords_returns_each_format_once():
    text = (
        "Start LAT: 34.123456 LON: -118.123456\n"
        "Mid 34° 07' 24.4\" N, 118° 07' 24.4\" W\n"
        "End Zone 11N 372500 E 3776600 N\n"
    )
    results = find_all_coords(text)
    formats = sorted(r[2] for r in results)
    assert formats == ["decimal_degrees", "dms", "utm"]
    assert len(results) == 3
