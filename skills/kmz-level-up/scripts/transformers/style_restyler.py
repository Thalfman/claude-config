"""style_restyler -- classify each feature's style_role.

Behavior:
- Per-placemark `overrides` map (id -> StyleRole) wins over auto-classification.
- Features with style_role != UNMAPPED are left unchanged (idempotent).
- LineStrings: classified via attribute_conventions.classify_feature.
- Polygons named like 'Permit Area' / 'Boundary' / 'Work Area' become BOUNDARY.
- Points: left UNMAPPED unless overridden (pole_derivator and station_tick_derivator
  set roles for derived points; original points stay UNMAPPED unless explicitly tagged).
"""
from __future__ import annotations

import re

from scripts.attribute_conventions import classify_feature
from scripts.kml_model import (
    Document,
    PolygonFeature,
    StyleRole,
)


_BOUNDARY_NAME = re.compile(r"permit|boundary|work\s*area|easement|row\s*lim", re.I)


def apply(
    doc: Document,
    role_map: dict[str, str],
    overrides: dict[str, StyleRole] | None = None,
    polygon_handling: dict | None = None,
) -> None:
    """Mutate doc in place; assign style_role to every feature.

    When `polygon_handling.enabled` is true, polygons that don't otherwise
    classify (e.g. ESRI/Sphere permit-area polygons that aren't named
    "Permit Boundary") are forced to BOUNDARY so they participate in the
    polygon hierarchy.

    When `polygon_handling.style_by` names an attribute and `status_styles`
    maps that attribute's values to color dicts, each polygon gets a
    `style_override` populated for emit_kml.
    """
    overrides = overrides or {}
    polygon_handling = polygon_handling or {}
    poly_mode = bool(polygon_handling.get("enabled"))
    style_by_attr = polygon_handling.get("style_by") if poly_mode else None
    status_styles = polygon_handling.get("status_styles", {}) if poly_mode else {}
    default_style = polygon_handling.get("default_style") if poly_mode else None

    for ls in doc.linestrings:
        if ls.id in overrides:
            ls.style_role = overrides[ls.id]
            continue
        if ls.style_role is not StyleRole.UNMAPPED:
            continue
        ls.style_role = classify_feature(ls, role_map)

    for poly in doc.polygons:
        if poly.id in overrides:
            poly.style_role = overrides[poly.id]
        elif poly.style_role is StyleRole.UNMAPPED:
            if _BOUNDARY_NAME.search(poly.name or "") or poly_mode:
                poly.style_role = StyleRole.BOUNDARY
        if poly_mode and poly.style_role is StyleRole.BOUNDARY:
            if style_by_attr:
                value = str(poly.attributes.get(style_by_attr, "")).strip()
                override = status_styles.get(value) or default_style
            else:
                override = default_style
            if override:
                poly.style_override = dict(override)

    for pt in doc.points:
        if pt.id in overrides:
            pt.style_role = overrides[pt.id]
            continue
        if pt.style_role is not StyleRole.UNMAPPED:
            continue
        pt.style_role = classify_feature(pt, role_map)
