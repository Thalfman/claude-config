"""Write a Document to a .kmz file using simplekml.

Renders the family color language and folder hierarchy. Folder visibility
defaults match family conventions (Existing Infrastructure visibility=0).
"""
from __future__ import annotations

from pathlib import Path

import simplekml

from scripts.kml_model import (
    Document,
    LineStringFeature,
    PointFeature,
    PolygonFeature,
    StyleRole,
)


# Family color language. KML colors are aabbggrr.
STYLE_DEFS: dict[StyleRole, dict] = {
    StyleRole.AERIAL:      {"line_color": "ff0000ff", "line_width": 3, "dashed": True},
    StyleRole.UNDERGROUND: {"line_color": "ff0000ff", "line_width": 3, "dashed": False},
    StyleRole.REPLACE:     {"line_color": "ff0080ff", "line_width": 3, "dashed": True},
    StyleRole.MARKUP:      {"line_color": "ffff00ff", "line_width": 3, "dashed": True},
    StyleRole.EXISTING:    {"line_color": "ff808080", "line_width": 2, "dashed": False},
    StyleRole.BOUNDARY:    {"line_color": "ff00ff00", "line_width": 4, "fill_color": "8000ff00"},
    StyleRole.POLE:        {"icon": "https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png", "icon_color": "ff0000ff"},
    StyleRole.VAULT:       {"icon": "https://maps.google.com/mapfiles/kml/shapes/placemark_square.png", "icon_color": "ffff0000"},
    StyleRole.STATION:     {"icon": "https://maps.google.com/mapfiles/kml/paddle/wht-blank.png", "icon_color": "ff404040"},
    StyleRole.UNMAPPED:    {"line_color": "ff404040", "line_width": 1, "dashed": False},
}


# Folders with default-off visibility per family conventions.
DEFAULT_OFF_FOLDERS = {"Existing Infrastructure", "Unmapped Routes"}
# Folders that are folded (visible-when-expanded but collapsed by default).
FOLDED_FOLDERS = {"Stations & Labels", "Existing Infrastructure", "Unmapped Routes"}


def write_kmz(doc: Document, out_path: str | Path) -> None:
    out_path = Path(out_path)
    kml = simplekml.Kml()
    kml.document.name = doc.name
    if doc.description:
        # Wrap in CDATA so the HTML balloon renders rather than being escaped.
        kml.document.description = _ensure_cdata(doc.description)

    folder_cache: dict[tuple[str, ...], simplekml.Folder] = {(): kml.document}

    def get_folder(path: tuple[str, ...]) -> simplekml.Folder:
        if path in folder_cache:
            return folder_cache[path]
        parent = get_folder(path[:-1])
        folder = parent.newfolder(name=path[-1])
        if path[-1] in DEFAULT_OFF_FOLDERS:
            folder.visibility = 0
        if path[-1] in FOLDED_FOLDERS:
            folder.open = 0
        folder_cache[path] = folder
        return folder

    for ls in doc.linestrings:
        _emit_linestring(ls, get_folder)
    for pt in doc.points:
        _emit_point(pt, get_folder)
    for poly in doc.polygons:
        _emit_polygon(poly, get_folder)

    kml.savekmz(str(out_path))


def _ensure_cdata(s: str) -> str:
    """Wrap an HTML string in CDATA unless it already is wrapped."""
    if not s:
        return s
    return s if s.lstrip().startswith("<![CDATA[") else f"<![CDATA[{s}]]>"


def _emit_linestring(ls: LineStringFeature, get_folder) -> None:
    folder = get_folder(tuple(ls.folder_path))
    placemark = folder.newlinestring(name=ls.name, coords=[(lon, lat) for lon, lat in ls.coordinates])
    placemark.altitudemode = simplekml.AltitudeMode.clamptoground
    style_def = STYLE_DEFS[ls.style_role]
    placemark.style.linestyle.color = style_def["line_color"]
    placemark.style.linestyle.width = style_def["line_width"]
    _attach_extended_data(placemark, ls.attributes)
    if ls.description_html:
        placemark.description = ls.description_html


def _emit_point(pt: PointFeature, get_folder) -> None:
    folder = get_folder(tuple(pt.folder_path))
    placemark = folder.newpoint(name=pt.name, coords=[pt.coordinates])
    placemark.altitudemode = simplekml.AltitudeMode.clamptoground
    style_def = STYLE_DEFS[pt.style_role]
    if "icon" in style_def:
        placemark.style.iconstyle.icon.href = style_def["icon"]
        placemark.style.iconstyle.color = style_def["icon_color"]
    _attach_extended_data(placemark, pt.attributes)
    if pt.description_html:
        placemark.description = pt.description_html


def _emit_polygon(poly: PolygonFeature, get_folder) -> None:
    folder = get_folder(tuple(poly.folder_path))

    if poly.extra_parts:
        # Multi-part polygon -- emit a Placemark wrapping a MultiGeometry,
        # so all the parts share one balloon and one style.
        placemark = folder.newmultigeometry(name=poly.name)
        placemark.altitudemode = simplekml.AltitudeMode.clamptoground
        primary = placemark.newpolygon(
            outerboundaryis=[(lon, lat) for lon, lat in poly.outer_ring],
        )
        if poly.inner_rings:
            primary.innerboundaryis = [
                [(lon, lat) for lon, lat in ring] for ring in poly.inner_rings
            ]
        for outer, inners in poly.extra_parts:
            part = placemark.newpolygon(
                outerboundaryis=[(lon, lat) for lon, lat in outer],
            )
            if inners:
                part.innerboundaryis = [
                    [(lon, lat) for lon, lat in ring] for ring in inners
                ]
    else:
        placemark = folder.newpolygon(
            name=poly.name,
            outerboundaryis=[(lon, lat) for lon, lat in poly.outer_ring],
        )
        if poly.inner_rings:
            placemark.innerboundaryis = [
                [(lon, lat) for lon, lat in ring] for ring in poly.inner_rings
            ]
        placemark.altitudemode = simplekml.AltitudeMode.clamptoground

    # Style: per-feature override wins, otherwise fall back to the role default.
    if poly.style_override:
        placemark.style.linestyle.color = poly.style_override.get("line", "ff00ff00")
        placemark.style.linestyle.width = poly.style_override.get("line_width", 2)
        placemark.style.polystyle.color = poly.style_override.get("fill", "8000ff00")
        placemark.style.polystyle.fill = 1
        placemark.style.polystyle.outline = 1
    else:
        style_def = STYLE_DEFS[poly.style_role]
        placemark.style.linestyle.color = style_def["line_color"]
        placemark.style.linestyle.width = style_def["line_width"]
        if "fill_color" in style_def:
            placemark.style.polystyle.color = style_def["fill_color"]
            placemark.style.polystyle.fill = 1

    _attach_extended_data(placemark, poly.attributes)
    if poly.description_html:
        placemark.description = _ensure_cdata(poly.description_html)


def _attach_extended_data(placemark, attributes: dict) -> None:
    for k, v in attributes.items():
        placemark.extendeddata.newdata(name=str(k), value=str(v))
