"""pytest fixtures: synthetic DXFs generated programmatically with ezdxf.

We build small, deterministic DXFs at test time rather than checking binary
fixtures. Each fixture function returns a path to a temporary .dxf the test
can read.
"""
from pathlib import Path

import ezdxf
import pytest


@pytest.fixture
def synthetic_dxf_path(tmp_path: Path) -> Path:
    """A small DXF with one of each conventional layer + simple geometry.

    Coordinates are chosen so a known transform (EPSG:2965 -> WGS84) lands
    in northern Indiana (around 40.35 lat, -86.16 lon).
    """
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()

    layers = [
        "PERMIT_BOUNDARY",
        "E_FIBER_AERIAL_NEW",
        "E_FIBER_UG_BORE",
        "PROPOSED_POLE",
        "VAULT",
        "EX_POLE",
        "EX_FIBER",
        "STATION_LABELS",
        "RANDOM_TEXT_LAYER_42",
    ]
    for layer in layers:
        doc.layers.add(name=layer)

    # Permit boundary: a closed rectangle in EPSG:2965 ftUS coords (northern Indiana).
    boundary_pts = [(190000, 1860000), (190600, 1860000),
                    (190600, 1860400), (190000, 1860400), (190000, 1860000)]
    msp.add_lwpolyline(boundary_pts, close=True, dxfattribs={"layer": "PERMIT_BOUNDARY"})

    # Aerial route segment (LWPOLYLINE)
    msp.add_lwpolyline(
        [(190050, 1860100), (190200, 1860100), (190400, 1860100)],
        dxfattribs={"layer": "E_FIBER_AERIAL_NEW"},
    )

    # Underground route segment
    msp.add_lwpolyline(
        [(190050, 1860200), (190200, 1860200)],
        dxfattribs={"layer": "E_FIBER_UG_BORE"},
    )

    # Proposed pole
    msp.add_point((190100, 1860100), dxfattribs={"layer": "PROPOSED_POLE"})

    # Vault
    msp.add_point((190150, 1860200), dxfattribs={"layer": "VAULT"})

    # Existing pole (should default OFF)
    msp.add_point((190050, 1860100), dxfattribs={"layer": "EX_POLE"})

    # Existing fiber polyline
    msp.add_lwpolyline(
        [(190000, 1860050), (190600, 1860050)],
        dxfattribs={"layer": "EX_FIBER"},
    )

    # Station label TEXT
    msp.add_text("STA 1+00", dxfattribs={"layer": "STATION_LABELS"}).set_placement((190100, 1860050))

    # Random text - should be unmapped
    msp.add_text("misc note", dxfattribs={"layer": "RANDOM_TEXT_LAYER_42"}).set_placement((190200, 1860300))

    out = tmp_path / "synthetic.dxf"
    doc.saveas(out)
    return out


@pytest.fixture
def synthetic_dxf_with_prj(synthetic_dxf_path: Path) -> Path:
    """Same DXF but with a .prj sidecar declaring EPSG:2965."""
    prj = synthetic_dxf_path.with_suffix(".prj")
    # Standard ESRI WKT for NAD83 / Indiana East (ftUS)
    prj.write_text(
        'PROJCS["NAD83 / Indiana East (ftUS)",GEOGCS["NAD83",'
        'DATUM["North_American_Datum_1983",SPHEROID["GRS 1980",6378137,298.257222101]],'
        'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],'
        'PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",37.5],'
        'PARAMETER["central_meridian",-85.66666666666667],PARAMETER["scale_factor",0.999966667],'
        'PARAMETER["false_easting",328083.333],PARAMETER["false_northing",820208.333],'
        'UNIT["US survey foot",0.3048006096012192]]'
    )
    return synthetic_dxf_path


@pytest.fixture
def synthetic_dxf_local_coords(tmp_path: Path) -> Path:
    """A DXF in local coordinates (origin at 0,0) - needs Tier 3 anchors."""
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    doc.layers.add(name="PERMIT_BOUNDARY")
    doc.layers.add(name="E_FIBER_AERIAL_NEW")
    doc.layers.add(name="MON")  # benchmark/control point block layer

    msp.add_lwpolyline([(0, 0), (600, 0), (600, 400), (0, 400), (0, 0)],
                       close=True, dxfattribs={"layer": "PERMIT_BOUNDARY"})
    msp.add_lwpolyline([(50, 100), (550, 100)], dxfattribs={"layer": "E_FIBER_AERIAL_NEW"})

    # Two control points for anchor testing
    msp.add_point((0, 0), dxfattribs={"layer": "MON"})
    msp.add_point((600, 400), dxfattribs={"layer": "MON"})

    out = tmp_path / "synthetic_local.dxf"
    doc.saveas(out)
    return out
