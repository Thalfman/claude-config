from scripts.station_parser import Station, parse_stations, station_to_value


def test_station_to_value_basic():
    assert station_to_value("21+37") == 2137
    assert station_to_value("0+00") == 0
    assert station_to_value("100+50") == 10050


def test_station_to_value_with_decimal():
    assert station_to_value("21+37.5") == 2137  # truncate to int feet


def test_parse_stations_with_letter_prefix():
    stations = parse_stations("Route runs B 21+37 to B 24+50")
    assert len(stations) == 2
    assert stations[0] == Station(prefix="B", value=2137, original="B 21+37")
    assert stations[1] == Station(prefix="B", value=2450, original="B 24+50")


def test_parse_stations_with_sta_prefix():
    stations = parse_stations("Stations: STA 5+00 and STA 12+50")
    assert len(stations) == 2
    assert stations[0].prefix == "STA"
    assert stations[0].value == 500
    assert stations[1].value == 1250


def test_parse_stations_bare_form():
    stations = parse_stations("0+00 to 12+50 along the route")
    assert len(stations) == 2
    assert stations[0] == Station(prefix=None, value=0, original="0+00")
    assert stations[1] == Station(prefix=None, value=1250, original="12+50")


def test_parse_stations_returns_empty_for_no_match():
    assert parse_stations("just plain text with no stations") == []


def test_parse_stations_does_not_match_phone_numbers():
    # 555-1234 looks vaguely station-y but has no '+' separator
    assert parse_stations("Call 555-1234") == []
