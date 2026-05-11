"""Tests for CRS detection tiers."""
import json
from pathlib import Path

import ezdxf
import pytest

from scripts.detect_crs import (
    detect_from_prj_sidecar,
    detect_from_geodata,
    detect_from_regional_default,
    detect_crs,
)


def test_prj_sidecar_returns_epsg(synthetic_dxf_with_prj: Path):
    result = detect_from_prj_sidecar(synthetic_dxf_with_prj)
    assert result is not None
    assert result["epsg"] == "EPSG:2965"
    assert result["confidence"] == "HIGH"
    assert result["source"] == "prj_sidecar"


def test_prj_sidecar_missing_returns_none(synthetic_dxf_path: Path):
    result = detect_from_prj_sidecar(synthetic_dxf_path)
    assert result is None


def test_geodata_xrecord_returns_epsg(tmp_path: Path):
    """A DXF written with ezdxf set_geodata() should be detected."""
    doc = ezdxf.new(setup=True)
    geodata = doc.modelspace().new_geodata()
    geodata.coordinate_system_definition = (
        'PROJCS["NAD83 / Indiana East (ftUS)",GEOGCS["NAD83",'
        'DATUM["North_American_Datum_1983",SPHEROID["GRS 1980",6378137,298.257222101]]],'
        'PROJECTION["Transverse_Mercator"]]'
    )
    out = tmp_path / "with_geodata.dxf"
    doc.saveas(out)

    result = detect_from_geodata(out)
    assert result is not None
    assert "Indiana East" in result["label"]


def test_geodata_missing_returns_none(synthetic_dxf_path: Path):
    """A vanilla DXF without GEODATA should return None."""
    result = detect_from_geodata(synthetic_dxf_path)
    assert result is None


def test_regional_default_filename_match(tmp_path: Path):
    defaults = {"Indiana": "EPSG:2965", "Florida-North": "EPSG:2238"}
    defaults_path = tmp_path / "defaults.json"
    defaults_path.write_text(json.dumps(defaults))

    fake_dxf = tmp_path / "PERU_INDIANA_FIBER.dxf"
    fake_dxf.touch()

    result = detect_from_regional_default(fake_dxf, defaults_path)
    assert result is not None
    assert result["epsg"] == "EPSG:2965"
    assert result["confidence"] == "MEDIUM"


def test_regional_default_no_match_returns_none(tmp_path: Path):
    defaults = {"Indiana": "EPSG:2965"}
    defaults_path = tmp_path / "defaults.json"
    defaults_path.write_text(json.dumps(defaults))

    fake_dxf = tmp_path / "drawing.dxf"
    fake_dxf.touch()

    result = detect_from_regional_default(fake_dxf, defaults_path)
    assert result is None


def test_detect_crs_falls_through_tiers(synthetic_dxf_with_prj: Path):
    """Tier 1 (prj sidecar) should win when present."""
    result = detect_crs(synthetic_dxf_with_prj)
    assert result["tier"] == 1
    assert result["epsg"] == "EPSG:2965"


def test_detect_crs_returns_manual_when_all_tiers_fail(synthetic_dxf_local_coords: Path,
                                                        tmp_path: Path):
    """A vanilla DXF with no .prj, no GEODATA, no filename hint -> tier=3 manual."""
    empty_defaults = tmp_path / "empty_defaults.json"
    empty_defaults.write_text("{}")
    result = detect_crs(synthetic_dxf_local_coords, defaults_path=empty_defaults)
    assert result["tier"] == 3
    assert result["epsg"] is None
    assert result["confidence"] == "MANUAL"


def test_prj_sidecar_returns_wkt_when_epsg_unidentifiable(synthetic_dxf_path: Path):
    """For ESRI WKT variants pyproj can't pin to a canonical EPSG (some State Plane
    ftUS dialects), we still want HIGH confidence with WKT preserved. This pins the
    contract for build_kmz.py: when epsg is None but wkt is present, the WKT is
    authoritative and should be passed to Transformer.from_crs() directly.
    """
    # Create a .prj sidecar with a slightly-non-canonical WKT that pyproj parses
    # but cannot identify by EPSG. Using a custom-named PROJCS achieves this.
    prj = synthetic_dxf_path.with_suffix(".prj")
    prj.write_text(
        'PROJCS["Custom_Plane_Coords",GEOGCS["NAD83",'
        'DATUM["North_American_Datum_1983",SPHEROID["GRS 1980",6378137,298.257222101]],'
        'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],'
        'PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",37.5],'
        'PARAMETER["central_meridian",-85.66666666666667],PARAMETER["scale_factor",0.999966667],'
        'PARAMETER["false_easting",328083.333],PARAMETER["false_northing",820208.333],'
        'UNIT["foot_us",0.3048006096012192]]'
    )
    result = detect_from_prj_sidecar(synthetic_dxf_path)
    assert result is not None
    assert result["confidence"] == "HIGH"
    # Either pyproj identifies it (epsg set) or it doesn't (wkt preserved)
    if result["epsg"] is None:
        assert result["wkt"]  # WKT is preserved for downstream consumption
        assert "Custom_Plane_Coords" in result["wkt"] or "Custom" in result.get("label", "")


def test_detect_from_regional_default_uses_packaged_defaults_by_default(tmp_path: Path):
    """No defaults_path arg -> uses scripts/dxf_crs_defaults.json shipped with the skill."""
    fake_dxf = tmp_path / "PERU_INDIANA_FIBER.dxf"
    fake_dxf.touch()
    result = detect_from_regional_default(fake_dxf)
    assert result is not None
    assert result["epsg"] == "EPSG:2965"  # Indiana East per packaged defaults


def test_detect_from_regional_default_longer_key_wins(tmp_path: Path):
    """Reorder regression: 'Indiana-West' must win over 'IN' for an INDIANA_WEST filename."""
    defaults = {"IN": "EPSG:2965", "Indiana-West": "EPSG:2966"}  # IN listed first
    defaults_path = tmp_path / "defaults.json"
    defaults_path.write_text(json.dumps(defaults))

    fake_dxf = tmp_path / "PERU_INDIANA_WEST_FIBER.dxf"
    fake_dxf.touch()

    result = detect_from_regional_default(fake_dxf, defaults_path)
    assert result is not None
    assert result["epsg"] == "EPSG:2966"  # Indiana-West, not IN
    assert result["matched_region"] == "Indiana-West"


def test_detect_from_regional_default_handles_malformed_json(tmp_path: Path):
    """Corrupted defaults JSON should return None, not crash."""
    bad_defaults = tmp_path / "bad.json"
    bad_defaults.write_text("{ not valid json")

    fake_dxf = tmp_path / "PERU_INDIANA_FIBER.dxf"
    fake_dxf.touch()

    result = detect_from_regional_default(fake_dxf, bad_defaults)
    assert result is None
