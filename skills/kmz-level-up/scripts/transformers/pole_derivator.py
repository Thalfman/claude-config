"""pole_derivator - synthesize pole point markers from aerial LineString
vertices whose deflection from the previous segment exceeds a threshold.

Skipped if the input already has any Point with style_role POLE OR with a
folder_path containing 'Poles' (the latter catches ungrouped point poles
the user authored manually). Also skipped if derive=False.
"""
from __future__ import annotations

import math

from scripts.kml_model import Document, PointFeature, StyleRole


def apply(doc: Document, derive: bool, deflection_deg: float) -> None:
    if not derive:
        return
    if _input_has_poles(doc):
        return

    threshold_rad = math.radians(deflection_deg)
    new_poles: list[PointFeature] = []

    for ls in doc.linestrings:
        if ls.style_role is not StyleRole.AERIAL:
            continue
        for i in range(1, len(ls.coordinates) - 1):
            prev = ls.coordinates[i - 1]
            curr = ls.coordinates[i]
            nxt = ls.coordinates[i + 1]
            angle = _deflection_angle(prev, curr, nxt)
            if angle >= threshold_rad:
                new_poles.append(PointFeature(
                    id=f"derived_pole_{ls.id}_{i}",
                    name=f"Pole {len(new_poles) + 1}",
                    attributes={"_derived": "true", "_source_route": ls.id},
                    coordinates=curr,
                    style_role=StyleRole.POLE,
                ))

    doc.points.extend(new_poles)


def _input_has_poles(doc: Document) -> bool:
    for pt in doc.points:
        if pt.style_role is StyleRole.POLE:
            return True
        if any("pole" in p.lower() for p in pt.folder_path):
            return True
    return False


def _deflection_angle(p0, p1, p2) -> float:
    """Angle between segment p0->p1 and p1->p2 (radians, 0 = straight)."""
    v1x, v1y = p1[0] - p0[0], p1[1] - p0[1]
    v2x, v2y = p2[0] - p1[0], p2[1] - p1[1]
    n1 = math.hypot(v1x, v1y)
    n2 = math.hypot(v2x, v2y)
    if n1 == 0 or n2 == 0:
        return 0.0
    cos_a = (v1x * v2x + v1y * v2y) / (n1 * n2)
    cos_a = max(-1.0, min(1.0, cos_a))
    return math.acos(cos_a)
