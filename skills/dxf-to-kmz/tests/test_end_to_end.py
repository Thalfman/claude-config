"""End-to-end: DXF in -> KMZ out, validate the whole pipeline."""
import json
import zipfile
from pathlib import Path

import pytest

from scripts.inspect_dxf import inspect_dxf
from scripts.build_kmz import build_kmz


def test_full_pipeline_tier1(synthetic_dxf_with_prj: Path, tmp_path: Path):
    """Tier 1 (.prj sidecar): inspect -> build -> KMZ valid."""
    mapping_path = tmp_path / "layer_mapping.json"
    inspect_dxf(synthetic_dxf_with_prj, output_path=mapping_path)

    mapping = json.loads(mapping_path.read_text())
    assert mapping["crs"]["tier"] == 1
    assert mapping["crs"]["epsg"] == "EPSG:2965"

    kmz_path = tmp_path / "out.kmz"
    build_kmz(synthetic_dxf_with_prj, mapping_path, output_path=kmz_path)

    with zipfile.ZipFile(kmz_path) as zf:
        kml = zf.read("doc.kml").decode()

    # All the things contractors need
    assert "<name>Permit Area</name>" in kml
    assert "<name>Proposed Route</name>" in kml
    assert "<name>Aerial</name>" in kml
    assert "<name>Underground</name>" in kml
    assert "<name>Existing Infrastructure</name>" in kml

    # Existing folder is visibility=0
    ex_idx = kml.find("<name>Existing Infrastructure</name>")
    assert "<visibility>0</visibility>" in kml[ex_idx:ex_idx + 500]

    # Provenance + disclaimer
    assert "Tier 1" in kml
    assert "Not certified for engineering layout" in kml


def test_full_pipeline_tier3(synthetic_dxf_local_coords: Path, tmp_path: Path):
    """Tier 3 (anchors): inspect -> build_anchors -> build_kmz."""
    from scripts.build_anchors import helmert_transform

    mapping_path = tmp_path / "layer_mapping.json"
    inspect_dxf(synthetic_dxf_local_coords, output_path=mapping_path)
    mapping = json.loads(mapping_path.read_text())
    # Local coords + no .prj + no GEODATA + filename has no region match
    assert mapping["crs"]["tier"] == 3

    anchors = [
        {"dxf_x": 0.0,   "dxf_y": 0.0,   "lat": 40.801, "lon": -86.030},
        {"dxf_x": 600.0, "dxf_y": 400.0, "lat": 40.8014, "lon": -86.0276},
    ]
    transform = helmert_transform(anchors)
    anchors_path = tmp_path / "anchors.json"
    anchors_path.write_text(json.dumps({
        "anchors": anchors,
        "transform": transform,
        "transform_kind": "helmert",
    }))

    kmz_path = tmp_path / "tier3.kmz"
    build_kmz(synthetic_dxf_local_coords, mapping_path,
              anchors_path=anchors_path, output_path=kmz_path)
    assert kmz_path.exists()
