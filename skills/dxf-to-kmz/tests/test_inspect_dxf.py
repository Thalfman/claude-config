"""Tests for inspect_dxf orchestration."""
import json
from pathlib import Path

import pytest

from scripts.inspect_dxf import inspect_dxf


def test_inspect_returns_layer_list(synthetic_dxf_path: Path):
    result = inspect_dxf(synthetic_dxf_path)
    layer_names = {layer["name"] for layer in result["layers"]}
    assert "PERMIT_BOUNDARY" in layer_names
    assert "E_FIBER_AERIAL_NEW" in layer_names
    assert "EX_POLE" in layer_names


def test_inspect_counts_entities_per_layer(synthetic_dxf_path: Path):
    result = inspect_dxf(synthetic_dxf_path)
    by_name = {layer["name"]: layer for layer in result["layers"]}
    assert by_name["E_FIBER_AERIAL_NEW"]["entity_counts"]["LWPOLYLINE"] >= 1
    assert by_name["PROPOSED_POLE"]["entity_counts"].get("POINT", 0) == 1


def test_inspect_applies_conventions(synthetic_dxf_path: Path):
    result = inspect_dxf(synthetic_dxf_path)
    by_name = {layer["name"]: layer for layer in result["layers"]}

    assert by_name["PERMIT_BOUNDARY"]["feature"] == "polygon"
    assert by_name["PERMIT_BOUNDARY"]["publish"] is True

    assert by_name["E_FIBER_AERIAL_NEW"]["feature"] == "route"
    assert by_name["E_FIBER_AERIAL_NEW"]["subtype"] == "aerial"

    assert by_name["EX_POLE"]["publish"] is False  # default off
    assert by_name["EX_POLE"]["subtype"] == "existing"


def test_inspect_includes_crs_block(synthetic_dxf_with_prj: Path):
    result = inspect_dxf(synthetic_dxf_with_prj)
    crs = result["crs"]
    assert crs["tier"] == 1
    assert crs["epsg"] == "EPSG:2965"


def test_inspect_writes_layer_mapping_json(synthetic_dxf_path: Path, tmp_path: Path):
    out_path = tmp_path / "layer_mapping.json"
    inspect_dxf(synthetic_dxf_path, output_path=out_path)
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert "source_dxf" in data
    assert "crs" in data
    assert "layers" in data
    assert isinstance(data["layers"], list)


def test_inspect_unmapped_layer_marked_with_note(synthetic_dxf_path: Path):
    result = inspect_dxf(synthetic_dxf_path)
    by_name = {layer["name"]: layer for layer in result["layers"]}
    rand = by_name["RANDOM_TEXT_LAYER_42"]
    assert rand["feature"] is None
    assert rand["publish"] is False
    assert "_note" in rand and "Unmapped" in rand["_note"]
