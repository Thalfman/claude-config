"""Unit tests for inspect_kmz."""

import json
import zipfile
from pathlib import Path

from scripts.inspect_kmz import inspect, main


SIMPLE_KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Test Doc</name>
    <Placemark>
      <name>Aerial Run</name>
      <ExtendedData>
        <Data name="TYPE"><value>AERIAL</value></Data>
        <Data name="STA"><value>37+25</value></Data>
        <Data name="SPAN_FT"><value>169</value></Data>
      </ExtendedData>
      <LineString><coordinates>-86.03,40.80,0 -86.02,40.80,0</coordinates></LineString>
    </Placemark>
    <Placemark>
      <name>EX_FIBER</name>
      <ExtendedData>
        <Data name="TYPE"><value>AERIAL</value></Data>
      </ExtendedData>
      <LineString><coordinates>-86.03,40.81,0 -86.02,40.81,0</coordinates></LineString>
    </Placemark>
  </Document>
</kml>
"""


def _write_kmz(tmp_path, kml=SIMPLE_KML):
    p = tmp_path / "in.kmz"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("doc.kml", kml)
    return p


def test_inspect_returns_mapping_dict(tmp_path):
    kmz = _write_kmz(tmp_path)
    mapping = inspect(kmz)
    assert "input_summary" in mapping
    assert "attribute_roles" in mapping
    assert "value_classifications" in mapping
    assert "derive" in mapping
    assert "balloon" in mapping
    assert "placemarks" in mapping


def test_inspect_classifies_attribute_names(tmp_path):
    kmz = _write_kmz(tmp_path)
    mapping = inspect(kmz)
    assert mapping["attribute_roles"]["TYPE"] == "construction_type"
    assert mapping["attribute_roles"]["STA"] == "chainage"
    assert mapping["attribute_roles"]["SPAN_FT"] == "span_length"


def test_inspect_classifies_placemarks(tmp_path):
    kmz = _write_kmz(tmp_path)
    mapping = inspect(kmz)
    by_name = {pm["name"]: pm for pm in mapping["placemarks"]}
    assert by_name["Aerial Run"]["auto_role"] == "aerial"
    assert by_name["EX_FIBER"]["auto_role"] == "existing"


def test_inspect_includes_input_summary(tmp_path):
    kmz = _write_kmz(tmp_path)
    mapping = inspect(kmz)
    assert mapping["input_summary"]["linestring_count"] == 2
    assert "TYPE" in mapping["input_summary"]["detected_attribute_keys"]


def test_inspect_default_derive_block(tmp_path):
    kmz = _write_kmz(tmp_path)
    mapping = inspect(kmz)
    derive = mapping["derive"]
    assert derive["permit_area"] is True
    assert derive["poles"] is True
    assert derive["station_ticks"] is True


def test_main_writes_json_to_disk(tmp_path):
    kmz = _write_kmz(tmp_path)
    out = tmp_path / "mapping.json"
    main([str(kmz), "--output", str(out)])
    assert out.exists()
    data = json.loads(out.read_text())
    assert "attribute_roles" in data


def test_inspect_fails_when_no_attributes(tmp_path):
    """Per spec: empty-attribute KMZ should fail with a guidance message."""
    kml_no_attrs = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Just geometry</name>
      <LineString><coordinates>-86.03,40.80,0 -86.02,40.80,0</coordinates></LineString>
    </Placemark>
  </Document>
</kml>
"""
    kmz = _write_kmz(tmp_path, kml=kml_no_attrs)
    import pytest
    with pytest.raises(SystemExit):
        main([str(kmz), "--output", str(tmp_path / "x.json")])
