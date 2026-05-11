"""permit_area_inferer - synthesize Permit Area polygon when input lacks one.

Uses a buffered convex hull of all aerial + underground route geometry.
The buffer is provided in feet and converted to lat/lon degrees using a
crude approximation (1 deg ~ 364,000 ft latitude; longitude scaled by cos(lat)).
This is precise enough for the family use-case (visualizing permit work area)
and avoids a pyproj reproject for every job.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, MultiLineString, mapping
from shapely.ops import unary_union

from scripts.kml_model import Document, PolygonFeature, StyleRole


_FT_PER_DEGREE_LAT = 364_000.0


def apply(doc: Document, derive: bool, buffer_ft: float) -> None:
    if not derive:
        return
    if any(p.style_role is StyleRole.BOUNDARY for p in doc.polygons):
        return

    route_lines = [
        LineString(ls.coordinates)
        for ls in doc.linestrings
        if ls.style_role in (StyleRole.AERIAL, StyleRole.UNDERGROUND) and len(ls.coordinates) >= 2
    ]
    if not route_lines:
        return

    merged = unary_union(MultiLineString(route_lines))
    hull = merged.convex_hull

    # Convert buffer_ft to degrees. Use the centroid lat for longitude scale.
    centroid_lat = hull.centroid.y
    deg_per_ft_lat = 1.0 / _FT_PER_DEGREE_LAT
    deg_per_ft_lon = 1.0 / (_FT_PER_DEGREE_LAT * max(math.cos(math.radians(centroid_lat)), 0.01))
    # Use the average of lat/lon scale for an isotropic buffer (good enough at small scales).
    buffer_deg = buffer_ft * (deg_per_ft_lat + deg_per_ft_lon) / 2

    buffered = hull.buffer(buffer_deg, cap_style=2, join_style=2)
    if buffered.is_empty:
        return

    geom = mapping(buffered)
    coords = geom["coordinates"][0]
    outer_ring = [(float(lon), float(lat)) for lon, lat in coords]

    poly = PolygonFeature(
        id="inferred_permit_area",
        name="Permit Area",
        attributes={"_inferred": "true", "_buffer_ft": str(buffer_ft)},
        outer_ring=outer_ring,
        style_role=StyleRole.BOUNDARY,
    )
    doc.polygons.append(poly)
