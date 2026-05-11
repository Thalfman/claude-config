"""polygon_merger -- collapse polygons that share a key attribute into one
placemark with a MultiGeometry.

Used for ESRI/Sphere-style exports where a single permit (PRM, parcel, work
area) is split into multiple polygons. Without merging, a 102-row Sphere
export with 52 unique permits produces 102 placemarks; with merging, it
produces 52, one per permit, each carrying every polygon part for that
permit under one balloon.

Driven by `polygon_handling.merge_at` in attribute_mapping.json:

    "polygon_handling": {
        "enabled": true,
        "group_by": ["JBNumber"],
        "merge_at": "Unique_ID",
        "placemark_label_template": "{Unique_ID} - {Jurisdiction}"
    }

Polygons are grouped by (group_by attribute values) + (merge_at attribute
value). Each group becomes one PolygonFeature with the first member as
primary and the rest moved to `extra_parts`. Group attributes are taken
from the first member (Sphere exports replicate the same attributes
across all polygons sharing a permit, so this is faithful).
"""
from __future__ import annotations

import re
from collections import defaultdict

from scripts.kml_model import Document, PolygonFeature


_TEMPLATE_TOKEN_RE = re.compile(r"\{([^}]+)\}")


def _render_template(template: str, attrs: dict, fallback_value: str = "") -> str:
    """Substitute {KEY} tokens with attrs[KEY]; {value} resolves to fallback_value.

    Unsubstituted tokens are removed. Adjacent separators (' - ', ' [] ',
    ' / ') left orphaned by missing values are cleaned up.
    """
    def replace(m: re.Match) -> str:
        key = m.group(1)
        if key == "value":
            return str(fallback_value).strip()
        v = attrs.get(key, "")
        if v is None:
            return ""
        s = str(v).strip()
        return "" if s.lower() == "null" else s

    rendered = _TEMPLATE_TOKEN_RE.sub(replace, template)
    # Tidy up artifacts left by missing fields: " - " at start/end, doubled
    # separators, empty brackets.
    rendered = re.sub(r"\s*\[\s*\]\s*", " ", rendered)
    rendered = re.sub(r"^[\s\-—/|]+", "", rendered)
    rendered = re.sub(r"[\s\-—/|]+$", "", rendered)
    rendered = re.sub(r"\s{2,}", " ", rendered)
    return rendered.strip()


def apply(doc: Document, polygon_handling: dict | None) -> int:
    """Mutate doc.polygons in place: collapse same-merge_at polygons into one
    feature with extra_parts set. Returns the number of polygons removed
    (i.e., merged into siblings)."""
    polygon_handling = polygon_handling or {}
    if not polygon_handling.get("enabled"):
        return 0
    merge_at = polygon_handling.get("merge_at")
    if not merge_at:
        return 0
    if not doc.polygons:
        return 0

    group_by = polygon_handling.get("group_by", [])
    label_template = polygon_handling.get("placemark_label_template")

    def group_key(p: PolygonFeature) -> tuple:
        return tuple(str(p.attributes.get(k, "")).strip() for k in group_by) + (
            str(p.attributes.get(merge_at, "")).strip(),
        )

    groups: dict[tuple, list[PolygonFeature]] = defaultdict(list)
    for p in doc.polygons:
        groups[group_key(p)].append(p)

    new_polys: list[PolygonFeature] = []
    removed = 0
    for _, members in groups.items():
        primary = members[0]
        for extra in members[1:]:
            primary.extra_parts.append((extra.outer_ring, extra.inner_rings))
            primary.extra_parts.extend(extra.extra_parts)
            removed += 1
        if label_template:
            primary.name = _render_template(
                label_template,
                primary.attributes,
                fallback_value=primary.attributes.get(merge_at, primary.name),
            ) or primary.name
        new_polys.append(primary)

    doc.polygons = new_polys
    return removed
