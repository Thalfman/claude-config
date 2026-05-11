"""station_tick_derivator -- emit station-tick point markers at the
midpoint of each LineString that has a chainage attribute.

This is the attribute-driven complement to pole_derivator (which is
geometry-driven). Skipped if no chainage attribute is mapped or if
derive=False.
"""
from __future__ import annotations

from scripts.kml_model import Document, PointFeature, StyleRole


def apply(doc: Document, derive: bool, role_map: dict[str, str]) -> None:
    if not derive:
        return
    chainage_attr = next((k for k, role in role_map.items() if role == "chainage"), None)
    if not chainage_attr:
        return

    new_ticks: list[PointFeature] = []
    for ls in doc.linestrings:
        sta = ls.attributes.get(chainage_attr)
        if sta is None or sta == "":
            continue
        if len(ls.coordinates) < 2:
            continue
        midpoint = _midpoint(ls.coordinates)
        new_ticks.append(PointFeature(
            id=f"derived_tick_{ls.id}",
            name=f"STA {sta}",
            attributes={"_derived": "true", "_source_route": ls.id, chainage_attr: str(sta)},
            coordinates=midpoint,
            style_role=StyleRole.STATION,
        ))

    doc.points.extend(new_ticks)


def _midpoint(coords: list[tuple[float, float]]) -> tuple[float, float]:
    """Geometric midpoint of a polyline by cumulative length."""
    if len(coords) == 2:
        return ((coords[0][0] + coords[1][0]) / 2, (coords[0][1] + coords[1][1]) / 2)
    seg_lens = []
    total = 0.0
    for i in range(1, len(coords)):
        dx = coords[i][0] - coords[i - 1][0]
        dy = coords[i][1] - coords[i - 1][1]
        d = (dx * dx + dy * dy) ** 0.5
        seg_lens.append(d)
        total += d
    if total == 0:
        return coords[0]
    target = total / 2
    walked = 0.0
    for i, d in enumerate(seg_lens):
        if walked + d >= target:
            t = (target - walked) / d if d else 0
            x = coords[i][0] + t * (coords[i + 1][0] - coords[i][0])
            y = coords[i][1] + t * (coords[i + 1][1] - coords[i][1])
            return (x, y)
        walked += d
    return coords[-1]
