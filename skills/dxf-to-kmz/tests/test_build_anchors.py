"""Tests for Helmert + affine transforms."""
import math
from pathlib import Path

import pytest

from scripts.build_anchors import (
    helmert_transform,
    affine_transform,
    apply_transform,
    enumerate_anchor_candidates,
)


def test_helmert_two_anchors_identity():
    """If DXF coords already match lat/lon, transform should be identity."""
    anchors = [
        {"dxf_x": 0.0,   "dxf_y": 0.0,   "lat": 0.0,   "lon": 0.0},
        {"dxf_x": 100.0, "dxf_y": 0.0,   "lat": 0.0,   "lon": 100.0},
    ]
    transform = helmert_transform(anchors)
    lat, lon = apply_transform(transform, dxf_x=50.0, dxf_y=0.0)
    assert lat == pytest.approx(0.0, abs=1e-6)
    assert lon == pytest.approx(50.0, abs=1e-6)


def test_helmert_two_anchors_translation_and_scale():
    """Two anchors in a coord system rotated/scaled relative to lat/lon."""
    anchors = [
        {"dxf_x": 1000.0, "dxf_y": 1000.0, "lat": 40.0, "lon": -86.0},
        {"dxf_x": 2000.0, "dxf_y": 1000.0, "lat": 40.0, "lon": -85.99},
    ]
    transform = helmert_transform(anchors)
    # Midpoint of dxf coords should map to midpoint of lat/lon
    lat, lon = apply_transform(transform, dxf_x=1500.0, dxf_y=1000.0)
    assert lat == pytest.approx(40.0, abs=1e-6)
    assert lon == pytest.approx(-85.995, abs=1e-6)


def test_affine_three_anchors_handles_nonuniform_scale():
    """3 anchors should fit a 6-parameter affine (different x/y scales)."""
    anchors = [
        {"dxf_x": 0.0,    "dxf_y": 0.0,    "lat": 40.0,  "lon": -86.0},
        {"dxf_x": 1000.0, "dxf_y": 0.0,    "lat": 40.0,  "lon": -85.99},
        {"dxf_x": 0.0,    "dxf_y": 500.0,  "lat": 40.005, "lon": -86.0},  # different y scale
    ]
    transform = affine_transform(anchors)
    # Test the third anchor round-trips
    lat, lon = apply_transform(transform, dxf_x=0.0, dxf_y=500.0)
    assert lat == pytest.approx(40.005, abs=1e-6)
    assert lon == pytest.approx(-86.0, abs=1e-6)


def test_helmert_collinear_anchors_raises():
    """Two anchors with identical positions can't be solved."""
    anchors = [
        {"dxf_x": 0.0, "dxf_y": 0.0, "lat": 40.0, "lon": -86.0},
        {"dxf_x": 0.0, "dxf_y": 0.0, "lat": 40.0, "lon": -86.0},
    ]
    with pytest.raises(ValueError):
        helmert_transform(anchors)


def test_affine_collinear_three_anchors_raises():
    """3 collinear anchors -> singular matrix -> ValueError."""
    anchors = [
        {"dxf_x": 0.0,    "dxf_y": 0.0,    "lat": 40.0,    "lon": -86.0},
        {"dxf_x": 1000.0, "dxf_y": 0.0,    "lat": 40.0,    "lon": -85.99},
        {"dxf_x": 2000.0, "dxf_y": 0.0,    "lat": 40.0,    "lon": -85.98},
    ]
    with pytest.raises(ValueError):
        affine_transform(anchors)


def test_enumerate_anchor_candidates_finds_mon_blocks(synthetic_dxf_local_coords: Path):
    candidates = enumerate_anchor_candidates(synthetic_dxf_local_coords)
    # Two POINT entities on layer "MON"
    mon_pts = [c for c in candidates if c["layer"] == "MON"]
    assert len(mon_pts) == 2
