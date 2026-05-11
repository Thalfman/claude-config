"""folder_refolder -- set folder_path on every feature based on style_role.

For polygon-dominant inputs with `polygon_handling.group_by` set in the
mapping, polygons get nested folders driven by attribute values instead of
the default single Permit Area folder. LineStrings and Points always use
the role-keyed family folders.
"""
from __future__ import annotations

import re

from scripts.kml_model import Document, PolygonFeature, StyleRole


FOLDER_FOR_ROLE: dict[StyleRole, list[str]] = {
    StyleRole.AERIAL:      ["Proposed Route", "Aerial"],
    StyleRole.UNDERGROUND: ["Proposed Route", "Underground"],
    StyleRole.REPLACE:     ["Proposed Route", "Replace"],
    StyleRole.MARKUP:      ["Proposed Route", "Markup"],
    StyleRole.EXISTING:    ["Existing Infrastructure"],
    StyleRole.BOUNDARY:    ["Permit Area"],
    StyleRole.POLE:        ["Proposed Infrastructure", "Poles"],
    StyleRole.VAULT:       ["Proposed Infrastructure", "Vaults"],
    StyleRole.STATION:     ["Stations & Labels"],
    StyleRole.UNMAPPED:    ["Unmapped Routes"],
}


_TEMPLATE_TOKEN_RE = re.compile(r"\{([^}]+)\}")


def _render_label(template: str, attrs: dict, fallback_value: str) -> str:
    def replace(m: re.Match) -> str:
        key = m.group(1)
        if key == "value":
            return str(fallback_value).strip()
        v = attrs.get(key, "")
        s = "" if v is None else str(v).strip()
        return "" if s.lower() == "null" else s

    s = _TEMPLATE_TOKEN_RE.sub(replace, template)
    s = re.sub(r"\s*\[\s*\]\s*", " ", s)
    s = re.sub(r"^[\s\-—/|]+", "", s)
    s = re.sub(r"[\s\-—/|]+$", "", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip() or fallback_value or "(unknown)"


def _polygon_group_path(poly: PolygonFeature, polygon_handling: dict) -> list[str]:
    top = polygon_handling.get("top_folder_name")
    group_by = polygon_handling.get("group_by", [])
    templates = polygon_handling.get("folder_label_templates", {})
    path: list[str] = []
    if top:
        path.append(top)
    for key in group_by:
        raw = poly.attributes.get(key, "")
        value = "" if raw is None else str(raw).strip()
        if value.lower() == "null":
            value = ""
        template = templates.get(key, "{value}")
        label = _render_label(template, poly.attributes, value or "(unknown)")
        path.append(label)
    return path


def apply(doc: Document, polygon_handling: dict | None = None) -> None:
    """Mutate doc in place; assign folder_path based on style_role + (optional)
    polygon_handling configuration."""
    polygon_handling = polygon_handling or {}
    polygon_grouping_active = bool(
        polygon_handling.get("enabled") and polygon_handling.get("group_by")
    )

    for ls in doc.linestrings:
        ls.folder_path = list(FOLDER_FOR_ROLE[ls.style_role])
    for pt in doc.points:
        pt.folder_path = list(FOLDER_FOR_ROLE[pt.style_role])
    for poly in doc.polygons:
        if polygon_grouping_active and poly.style_role is StyleRole.BOUNDARY:
            poly.folder_path = _polygon_group_path(poly, polygon_handling)
        else:
            poly.folder_path = list(FOLDER_FOR_ROLE[poly.style_role])
