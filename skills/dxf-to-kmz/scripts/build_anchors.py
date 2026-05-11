"""Tier 3: build manual anchors for local-coordinate DXFs.

Provides:
    helmert_transform(anchors)   -> 4-param transform from 2+ anchors
    affine_transform(anchors)    -> 6-param transform from 3+ anchors
    apply_transform(t, x, y)     -> (lat, lon)
    enumerate_anchor_candidates  -> list of likely anchor points in the DXF
    main()                       -> interactive CLI
"""
import argparse
import json
import math
import sys
from pathlib import Path

import ezdxf
import numpy as np


# Layer-name patterns that suggest control points / benchmarks
ANCHOR_LAYER_HINTS = ("MON", "BENCHMARK", "BM", "CTRL_PT", "CONTROL", "GPS")


def helmert_transform(anchors: list[dict]) -> dict:
    """4-parameter Helmert: translation + uniform scale + rotation.

    With 2 anchors: solves exactly.
    With 3+: least-squares fit.

    Note on accuracy: Helmert applies a single uniform scale factor in degrees
    per DXF unit. That assumption is only strictly correct near the equator;
    1 degree of longitude is shorter at higher latitudes than 1 degree of
    latitude. For sub-meter accuracy outside the tropics or for linear extents
    over a few thousand feet, prefer affine (3+ anchors) which fits the lon/lat
    scales independently.
    """
    if len(anchors) < 2:
        raise ValueError("Helmert requires 2+ anchors")

    # Detect degenerate input (identical points)
    pts = [(a["dxf_x"], a["dxf_y"]) for a in anchors]
    if len(set(pts)) < 2:
        raise ValueError("Anchors are coincident; need 2 distinct DXF points")

    # Build linear system for [a, b, tx, ty]:
    #   lon = a*x - b*y + tx
    #   lat = b*x + a*y + ty
    rows = []
    rhs = []
    for a in anchors:
        x, y = a["dxf_x"], a["dxf_y"]
        rows.append([x, -y, 1.0, 0.0]); rhs.append(a["lon"])
        rows.append([y,  x, 0.0, 1.0]); rhs.append(a["lat"])
    A = np.array(rows)
    b = np.array(rhs)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    return {"kind": "helmert", "params": sol.tolist()}


def affine_transform(anchors: list[dict]) -> dict:
    """6-parameter affine. Needs 3+ anchors. Fails on collinear input."""
    if len(anchors) < 3:
        raise ValueError("Affine requires 3+ anchors")

    rows = []
    rhs_lon = []
    rhs_lat = []
    for a in anchors:
        x, y = a["dxf_x"], a["dxf_y"]
        rows.append([x, y, 1.0])
        rhs_lon.append(a["lon"])
        rhs_lat.append(a["lat"])
    A = np.array(rows)
    if abs(np.linalg.det(A[:3])) < 1e-9:
        raise ValueError("Anchors collinear; affine is singular")

    lon_params, *_ = np.linalg.lstsq(A, np.array(rhs_lon), rcond=None)
    lat_params, *_ = np.linalg.lstsq(A, np.array(rhs_lat), rcond=None)
    return {"kind": "affine", "lon_params": lon_params.tolist(), "lat_params": lat_params.tolist()}


def apply_transform(transform: dict, dxf_x: float, dxf_y: float) -> tuple[float, float]:
    """Apply a Helmert or affine transform to a single (x, y) -> (lat, lon)."""
    if transform["kind"] == "helmert":
        a, b, tx, ty = transform["params"]
        lon = a * dxf_x - b * dxf_y + tx
        lat = b * dxf_x + a * dxf_y + ty
        return lat, lon
    if transform["kind"] == "affine":
        ax, ay, atx = transform["lon_params"]
        bx, by, btx = transform["lat_params"]
        lon = ax * dxf_x + ay * dxf_y + atx
        lat = bx * dxf_x + by * dxf_y + btx
        return lat, lon
    raise ValueError(f"Unknown transform kind: {transform['kind']}")


def enumerate_anchor_candidates(dxf_path: Path) -> list[dict]:
    """Find likely anchor points: POINT/INSERT entities on hint-named layers."""
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    candidates = []

    for entity in msp:
        layer = entity.dxf.layer
        if not any(h in layer.upper() for h in ANCHOR_LAYER_HINTS):
            continue
        kind = entity.dxftype()
        if kind == "POINT":
            p = entity.dxf.location
            candidates.append({"layer": layer, "kind": "POINT", "dxf_x": p.x, "dxf_y": p.y})
        elif kind == "INSERT":
            p = entity.dxf.insert
            candidates.append({"layer": layer, "kind": "INSERT", "dxf_x": p.x, "dxf_y": p.y,
                               "block_name": entity.dxf.name})

    return candidates


def main():
    parser = argparse.ArgumentParser(description="Build manual anchors for local-coord DXFs")
    parser.add_argument("dxf_path", type=Path)
    parser.add_argument("--output", type=Path, default=Path("anchors.json"))
    args = parser.parse_args()

    cands = enumerate_anchor_candidates(args.dxf_path)
    print(f"Found {len(cands)} anchor candidates:")
    for i, c in enumerate(cands):
        print(f"  [{i}] layer={c['layer']} dxf=({c['dxf_x']:.2f}, {c['dxf_y']:.2f})")

    if len(cands) < 2:
        print("Not enough anchor candidates. Add CTRL_PT/BENCHMARK/MON points to the DXF, "
              "or supply anchors manually below.")

    print("\nFor each anchor, enter lat/lon (e.g., '40.801166, -86.030433').")
    print("Enter blank line to finish (need at least 2).\n")

    anchors = []
    for c in cands:
        prompt = f"Anchor at DXF=({c['dxf_x']:.2f}, {c['dxf_y']:.2f}) on layer {c['layer']} -> lat,lon: "
        line = input(prompt).strip()
        if not line:
            break
        lat_s, lon_s = line.split(",")
        anchors.append({"dxf_x": c["dxf_x"], "dxf_y": c["dxf_y"],
                        "lat": float(lat_s.strip()), "lon": float(lon_s.strip()),
                        "layer": c["layer"]})

    if len(anchors) < 2:
        print("ERROR: Need at least 2 anchors. Aborting.")
        sys.exit(1)

    if len(anchors) >= 3:
        try:
            transform = affine_transform(anchors)
            kind = "affine"
        except ValueError as exc:
            # Most likely cause is collinear anchors (singular A matrix), but a
            # bare except ValueError would catch any value error from upstream.
            # Print the original message so misconfiguration doesn't get masked
            # by the fallback path.
            print(f"affine_transform failed ({exc}); falling back to Helmert.")
            transform = helmert_transform(anchors)
            kind = f"helmert (fallback from affine: {exc})"
    else:
        transform = helmert_transform(anchors)
        kind = "helmert"

    out = {"anchors": anchors, "transform": transform, "transform_kind": kind}
    args.output.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {args.output} ({len(anchors)} anchors, transform={kind})")


if __name__ == "__main__":
    sys.exit(main())
