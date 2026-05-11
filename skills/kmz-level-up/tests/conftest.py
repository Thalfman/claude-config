"""pytest fixtures for kmz-level-up.

Synthetic KMZ builders mimicking the four input-shape categories the skill
must handle (per the spec):
- Civil 3D / ArcGIS exports: SchemaData / SimpleData, uppercase attr names
- QGIS exports: <Data> / <value>, lowercase attr names
- Hand-built (Google Earth Pro): minimal attrs, irregular folder structure
- Already conformant: output of dxf-to-kmz / cd-route-stitcher
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest


def _write_kmz(path: Path, kml: str) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("doc.kml", kml)
    return path


@pytest.fixture
def kmz_civil3d_style(tmp_path: Path) -> Path:
    """Civil 3D-style export: SchemaData/SimpleData, uppercase attr names."""
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Civil3D Export</name>
    <Schema id="route_schema" name="Route">
      <SimpleField name="TYPE" type="string"/>
      <SimpleField name="STA" type="string"/>
      <SimpleField name="SPAN_FT" type="string"/>
    </Schema>
    <Placemark id="aerial_1">
      <name>Aerial Run 1</name>
      <ExtendedData><SchemaData schemaUrl="#route_schema">
        <SimpleData name="TYPE">AERIAL</SimpleData>
        <SimpleData name="STA">37+25</SimpleData>
        <SimpleData name="SPAN_FT">169</SimpleData>
      </SchemaData></ExtendedData>
      <LineString><coordinates>-86.030,40.800,0 -86.025,40.800,0 -86.025,40.805,0</coordinates></LineString>
    </Placemark>
    <Placemark id="ug_1">
      <name>UG Run 1</name>
      <ExtendedData><SchemaData schemaUrl="#route_schema">
        <SimpleData name="TYPE">UG</SimpleData>
        <SimpleData name="STA">42+50</SimpleData>
      </SchemaData></ExtendedData>
      <LineString><coordinates>-86.020,40.800,0 -86.015,40.800,0</coordinates></LineString>
    </Placemark>
  </Document>
</kml>
"""
    return _write_kmz(tmp_path / "civil3d.kmz", kml)


@pytest.fixture
def kmz_qgis_style(tmp_path: Path) -> Path:
    """QGIS-style export: Data/value, lowercase attr names."""
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>QGIS Export</name>
    <Placemark id="r1">
      <name>route 1</name>
      <ExtendedData>
        <Data name="construction_type"><value>aerial</value></Data>
        <Data name="chainage"><value>37+25</value></Data>
        <Data name="owner"><value>Comcast</value></Data>
      </ExtendedData>
      <LineString><coordinates>-86.030,40.800,0 -86.025,40.800,0</coordinates></LineString>
    </Placemark>
  </Document>
</kml>
"""
    return _write_kmz(tmp_path / "qgis.kmz", kml)


@pytest.fixture
def kmz_handbuilt(tmp_path: Path) -> Path:
    """Hand-built Google Earth Pro KMZ: minimal attrs, no folder structure."""
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Hand-built</name>
    <Placemark id="hb1">
      <name>my route</name>
      <description>Hand-traced from satellite imagery.</description>
      <ExtendedData>
        <Data name="type"><value>aerial</value></Data>
      </ExtendedData>
      <LineString><coordinates>-86.030,40.800,0 -86.025,40.800,0 -86.025,40.805,0</coordinates></LineString>
    </Placemark>
  </Document>
</kml>
"""
    return _write_kmz(tmp_path / "handbuilt.kmz", kml)


@pytest.fixture
def kmz_already_conformant(tmp_path: Path) -> Path:
    """Output of a family builder skill -- already follows family conventions."""
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>JB12345 -- Permit Package</name>
    <description>Conformant output. Not certified for engineering layout -- for that, use the source DWG in Civil 3D.</description>
    <Folder><name>Permit Area</name>
      <Placemark id="pb1">
        <name>Permit Boundary</name>
        <Polygon><outerBoundaryIs><LinearRing><coordinates>
          -86.035,40.795,0 -86.010,40.795,0 -86.010,40.810,0 -86.035,40.810,0 -86.035,40.795,0
        </coordinates></LinearRing></outerBoundaryIs></Polygon>
      </Placemark>
    </Folder>
    <Folder><name>Proposed Route</name>
      <Folder><name>Aerial</name>
        <Placemark id="cr1">
          <name>Conformant Aerial</name>
          <ExtendedData>
            <Data name="TYPE"><value>AERIAL</value></Data>
            <Data name="STA"><value>37+25</value></Data>
          </ExtendedData>
          <LineString><coordinates>-86.030,40.800,0 -86.025,40.800,0</coordinates></LineString>
        </Placemark>
      </Folder>
    </Folder>
  </Document>
</kml>
"""
    return _write_kmz(tmp_path / "conformant.kmz", kml)
