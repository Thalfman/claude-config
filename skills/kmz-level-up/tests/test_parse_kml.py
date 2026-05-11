"""Unit tests for parse_kml -- lxml-based KML/KMZ parsing."""

import zipfile
from pathlib import Path

import pytest

from scripts.kml_model import Document, LineStringFeature
from scripts.parse_kml import parse_kmz


SIMPLE_KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Test Doc</name>
    <description>A simple test KML.</description>
    <Placemark id="ls1">
      <name>Aerial Run 1</name>
      <ExtendedData>
        <Data name="TYPE"><value>AERIAL</value></Data>
        <Data name="STA"><value>37+25</value></Data>
      </ExtendedData>
      <LineString>
        <coordinates>-86.030,40.801,0 -86.025,40.801,0</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>
"""


def write_kmz(tmp_path: Path, kml_content: str, name: str = "test.kmz") -> Path:
    kmz_path = tmp_path / name
    with zipfile.ZipFile(kmz_path, "w") as zf:
        zf.writestr("doc.kml", kml_content)
    return kmz_path


def test_parse_kmz_returns_document(tmp_path):
    kmz = write_kmz(tmp_path, SIMPLE_KML)
    doc = parse_kmz(kmz)
    assert isinstance(doc, Document)
    assert doc.source_path == str(kmz)
    assert doc.name == "Test Doc"


def test_parse_kmz_extracts_linestring(tmp_path):
    kmz = write_kmz(tmp_path, SIMPLE_KML)
    doc = parse_kmz(kmz)
    assert len(doc.linestrings) == 1
    ls = doc.linestrings[0]
    assert isinstance(ls, LineStringFeature)
    assert ls.name == "Aerial Run 1"
    assert ls.attributes["TYPE"] == "AERIAL"
    assert ls.attributes["STA"] == "37+25"
    assert len(ls.coordinates) == 2
    assert ls.coordinates[0] == (-86.030, 40.801)


def test_parse_kml_handles_simpledata_schema(tmp_path):
    """Civil 3D / ArcGIS exports use SchemaData/SimpleData rather than Data."""
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Civil3D Doc</name>
    <Schema id="route_schema" name="Route">
      <SimpleField name="TYPE" type="string"/>
    </Schema>
    <Placemark>
      <name>Run</name>
      <ExtendedData>
        <SchemaData schemaUrl="#route_schema">
          <SimpleData name="TYPE">UG</SimpleData>
        </SchemaData>
      </ExtendedData>
      <LineString>
        <coordinates>-86.03,40.80,0 -86.02,40.80,0</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>
"""
    kmz = write_kmz(tmp_path, kml)
    doc = parse_kmz(kmz)
    assert doc.linestrings[0].attributes["TYPE"] == "UG"


def test_parse_kml_handles_polygon(tmp_path):
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Boundary</name>
      <Polygon>
        <outerBoundaryIs><LinearRing><coordinates>
          -86.03,40.80,0 -86.02,40.80,0 -86.02,40.81,0 -86.03,40.81,0 -86.03,40.80,0
        </coordinates></LinearRing></outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""
    kmz = write_kmz(tmp_path, kml)
    doc = parse_kmz(kmz)
    assert len(doc.polygons) == 1
    assert len(doc.polygons[0].outer_ring) == 5


def test_parse_kml_handles_point(tmp_path):
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Pole 1</name>
      <Point>
        <coordinates>-86.03,40.80,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>
"""
    kmz = write_kmz(tmp_path, kml)
    doc = parse_kmz(kmz)
    assert len(doc.points) == 1
    assert doc.points[0].coordinates == (-86.03, 40.80)


def test_parse_raw_kml_file(tmp_path):
    """Parsing a .kml (not .kmz) directly should work too."""
    kml_path = tmp_path / "test.kml"
    kml_path.write_text(SIMPLE_KML, encoding="utf-8")
    doc = parse_kmz(kml_path)
    assert len(doc.linestrings) == 1


def test_parse_kml_handles_gx_track_namespace(tmp_path):
    """gx:Track placemarks are extracted as LineStrings via the gx namespace."""
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
  <Document>
    <name>Hand-built</name>
    <Placemark>
      <name>Path</name>
      <ExtendedData>
        <Data name="TYPE"><value>AERIAL</value></Data>
      </ExtendedData>
      <gx:Track>
        <gx:coord>-86.03 40.80 0</gx:coord>
        <gx:coord>-86.02 40.80 0</gx:coord>
      </gx:Track>
    </Placemark>
  </Document>
</kml>
"""
    kmz = write_kmz(tmp_path, kml)
    doc = parse_kmz(kmz)
    # gx:Track with coords should be extracted as a LineString.
    assert len(doc.linestrings) == 1
    assert doc.linestrings[0].attributes["TYPE"] == "AERIAL"
