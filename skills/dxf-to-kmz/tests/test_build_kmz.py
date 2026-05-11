"""Tests for build_kmz: geometry extraction, reprojection, KMZ structure."""
import json
import zipfile
from pathlib import Path

import pytest

from scripts.build_kmz import (
    extract_geometry,
    reproject_coords,
    build_kmz,
)
from scripts.inspect_dxf import inspect_dxf


def test_extract_geometry_returns_polylines_for_lwpolyline_layers(synthetic_dxf_path: Path):
    geom = extract_geometry(synthetic_dxf_path)
    aerial = geom["E_FIBER_AERIAL_NEW"]
    assert len(aerial["polylines"]) >= 1
    assert len(aerial["polylines"][0]) >= 2  # at least 2 vertices


def test_extract_geometry_returns_points_for_point_layers(synthetic_dxf_path: Path):
    geom = extract_geometry(synthetic_dxf_path)
    poles = geom["PROPOSED_POLE"]
    assert len(poles["points"]) == 1


def test_extract_geometry_closed_polyline_for_boundary(synthetic_dxf_path: Path):
    geom = extract_geometry(synthetic_dxf_path)
    boundary = geom["PERMIT_BOUNDARY"]
    poly = boundary["polylines"][0]
    # Closed polyline: first point == last point
    assert poly[0] == poly[-1]


def test_reproject_epsg2965_to_wgs84_lands_in_indiana():
    """EPSG:2965 (Indiana East ftUS) coords near Peru -> ~40.8 lat, -86.03 lon."""
    pts = [(190100, 1860100)]  # near Peru, IN in NAD83 Indiana East ftUS
    out = reproject_coords(pts, source_epsg="EPSG:2965")
    lat, lon = out[0]
    # Expected: somewhere in northern Indiana
    assert 39.0 < lat < 42.0
    assert -88.0 < lon < -85.0


def test_build_kmz_emits_valid_kmz(synthetic_dxf_with_prj: Path, tmp_path: Path):
    mapping = inspect_dxf(synthetic_dxf_with_prj,
                          output_path=tmp_path / "lm.json")
    out_kmz = tmp_path / "test.kmz"
    build_kmz(synthetic_dxf_with_prj, tmp_path / "lm.json", output_path=out_kmz)
    assert out_kmz.exists()
    with zipfile.ZipFile(out_kmz) as zf:
        names = zf.namelist()
    assert "doc.kml" in names


def test_build_kmz_folder_structure(synthetic_dxf_with_prj: Path, tmp_path: Path):
    mapping = inspect_dxf(synthetic_dxf_with_prj, output_path=tmp_path / "lm.json")
    out_kmz = tmp_path / "test.kmz"
    build_kmz(synthetic_dxf_with_prj, tmp_path / "lm.json", output_path=out_kmz)

    with zipfile.ZipFile(out_kmz) as zf:
        kml = zf.read("doc.kml").decode()

    # Top-level folders we expect
    assert "<name>Permit Area</name>" in kml
    assert "<name>Proposed Route</name>" in kml
    assert "<name>Existing Infrastructure</name>" in kml


def test_build_kmz_existing_infrastructure_default_off(synthetic_dxf_with_prj: Path, tmp_path: Path):
    inspect_dxf(synthetic_dxf_with_prj, output_path=tmp_path / "lm.json")
    out_kmz = tmp_path / "test.kmz"
    build_kmz(synthetic_dxf_with_prj, tmp_path / "lm.json", output_path=out_kmz)

    with zipfile.ZipFile(out_kmz) as zf:
        kml = zf.read("doc.kml").decode()

    # Must contain a folder with name "Existing Infrastructure" and visibility 0
    idx = kml.find("<name>Existing Infrastructure</name>")
    assert idx > 0
    # Within ~500 chars after that name, expect <visibility>0</visibility>
    assert "<visibility>0</visibility>" in kml[idx:idx + 500]


def test_build_kmz_doc_description_contains_provenance(synthetic_dxf_with_prj: Path, tmp_path: Path):
    inspect_dxf(synthetic_dxf_with_prj, output_path=tmp_path / "lm.json")
    out_kmz = tmp_path / "test.kmz"
    build_kmz(synthetic_dxf_with_prj, tmp_path / "lm.json", output_path=out_kmz)

    with zipfile.ZipFile(out_kmz) as zf:
        kml = zf.read("doc.kml").decode()

    assert "Tier 1" in kml or "tier=1" in kml.lower() or "EPSG:2965" in kml
    assert "Not certified for engineering layout" in kml


def test_build_kmz_with_anchors(synthetic_dxf_local_coords: Path, tmp_path: Path):
    """Tier 3 path: provide anchors.json instead of CRS EPSG."""
    from scripts.build_anchors import helmert_transform
    anchors = [
        {"dxf_x": 0.0,   "dxf_y": 0.0,   "lat": 40.801, "lon": -86.030},
        {"dxf_x": 600.0, "dxf_y": 400.0, "lat": 40.802, "lon": -86.025},
    ]
    transform = helmert_transform(anchors)
    anchors_path = tmp_path / "anchors.json"
    anchors_path.write_text(json.dumps({
        "anchors": anchors,
        "transform": transform,
        "transform_kind": "helmert",
    }))

    inspect_dxf(synthetic_dxf_local_coords, output_path=tmp_path / "lm.json")
    out_kmz = tmp_path / "anchored.kmz"
    build_kmz(synthetic_dxf_local_coords, tmp_path / "lm.json",
              anchors_path=anchors_path, output_path=out_kmz)
    assert out_kmz.exists()


def test_build_kmz_with_wkt_only_crs(synthetic_dxf_path: Path, tmp_path: Path):
    """When CRS detection produces WKT but no EPSG, build_kmz should still work."""
    # Create a layer_mapping.json by hand with wkt-only CRS
    from scripts.inspect_dxf import inspect_dxf
    mapping = inspect_dxf(synthetic_dxf_path)
    # Simulate the WKT-only case: pyproj parsed WKT but couldn't ID an EPSG
    mapping["crs"] = {
        "tier": 1,
        "epsg": None,
        "label": "Custom Indiana East variant",
        "wkt": (
            'PROJCS["NAD83 / Indiana East (ftUS)",GEOGCS["NAD83",'
            'DATUM["North_American_Datum_1983",SPHEROID["GRS 1980",6378137,298.257222101]],'
            'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],'
            'PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",37.5],'
            'PARAMETER["central_meridian",-85.66666666666667],PARAMETER["scale_factor",0.999966667],'
            'PARAMETER["false_easting",328083.333],PARAMETER["false_northing",820208.333],'
            'UNIT["US survey foot",0.3048006096012192]]'
        ),
        "source": "geodata_xrecord",
        "confidence": "HIGH",
    }
    mapping_path = tmp_path / "lm.json"
    mapping_path.write_text(json.dumps(mapping))

    out_kmz = tmp_path / "wkt_only.kmz"
    build_kmz(synthetic_dxf_path, mapping_path, output_path=out_kmz)
    assert out_kmz.exists()


def test_extract_geometry_aligned_text_uses_align_point(tmp_path: Path):
    """TEXT with non-default alignment stores position in dxf.align_point, not dxf.insert."""
    import ezdxf
    doc = ezdxf.new(setup=True)
    doc.layers.add(name="STATION_LABELS")
    msp = doc.modelspace()
    # Create a center-aligned TEXT entity (halign=4 = MIDDLE in DXF)
    text = msp.add_text("STA 5+00", dxfattribs={"layer": "STATION_LABELS"})
    # set_placement with align method moves data to align_point
    text.set_placement((123456.78, 987654.32), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    dxf_out = tmp_path / "aligned.dxf"
    doc.saveas(dxf_out)

    geom = extract_geometry(dxf_out)
    labels = geom["STATION_LABELS"]["labels"]
    assert len(labels) == 1
    x, y, txt = labels[0]
    assert x == pytest.approx(123456.78, abs=0.01)
    assert y == pytest.approx(987654.32, abs=0.01)
    assert txt == "STA 5+00"


def test_build_kmz_includes_station_labels(synthetic_dxf_with_prj: Path, tmp_path: Path):
    """Station labels (subtype='station', publish=True after C1 fix) must appear in KMZ."""
    from scripts.inspect_dxf import inspect_dxf
    inspect_dxf(synthetic_dxf_with_prj, output_path=tmp_path / "lm.json")
    out_kmz = tmp_path / "with_stations.kmz"
    build_kmz(synthetic_dxf_with_prj, tmp_path / "lm.json", output_path=out_kmz)

    import zipfile
    with zipfile.ZipFile(out_kmz) as zf:
        kml = zf.read("doc.kml").decode()

    # The conftest synthetic_dxf adds TEXT "STA 1+00" on layer STATION_LABELS
    assert "STA 1+00" in kml
    # And the Stations & Labels folder should contain it
    stations_idx = kml.find("<name>Stations &amp; Labels</name>")
    if stations_idx < 0:
        # Some KML emitters use literal & ; check both
        stations_idx = kml.find("<name>Stations & Labels</name>")
    assert stations_idx > 0
