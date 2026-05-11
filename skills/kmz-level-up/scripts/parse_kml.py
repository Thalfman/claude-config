"""Read a KMZ/KML file into the internal kml_model.Document.

We use lxml directly with Clark-notation XPath ({namespace}tag) to avoid
namespace-prefix mixing issues. Handles every KML construct we care about:
LineString, Point, Polygon, ExtendedData/Data, ExtendedData/SchemaData/
SimpleData, gx:Track. Also handles ESRI/ArcGIS/Sphere exports that put
attributes in HTML <table> blocks inside <description> rather than
<ExtendedData>.
"""
from __future__ import annotations

import html as _html_lib
import re
import zipfile
from pathlib import Path

from lxml import etree

from scripts.kml_model import (
    Document,
    LineStringFeature,
    PointFeature,
    PolygonFeature,
)


KML_NS = "http://www.opengis.net/kml/2.2"
GX_NS = "http://www.google.com/kml/ext/2.2"


def _qn(ns: str, tag: str) -> str:
    """Clark notation QName."""
    return f"{{{ns}}}{tag}"


def parse_kmz(path: str | Path) -> Document:
    """Parse a KMZ or KML file into a Document.

    Accepts a `.kmz` (zip with `doc.kml` inside) or a raw `.kml` file path.
    """
    path = Path(path)
    if path.suffix.lower() == ".kmz":
        kml_bytes = _extract_doc_kml(path)
    else:
        kml_bytes = path.read_bytes()

    root = etree.fromstring(kml_bytes)
    # Most KMLs nest content under a top-level Document; some skip it.
    doc_el = root.find(_qn(KML_NS, "Document"))
    if doc_el is None:
        doc_el = root

    name_el = doc_el.find(_qn(KML_NS, "name"))
    name = name_el.text if name_el is not None and name_el.text else path.stem

    desc_el = doc_el.find(_qn(KML_NS, "description"))
    description = desc_el.text if desc_el is not None and desc_el.text else ""

    doc = Document(
        source_path=str(path),
        name=name,
        description=description,
    )

    placemarks = doc_el.findall(f".//{_qn(KML_NS, 'Placemark')}")
    for i, pm in enumerate(placemarks):
        feature = _parse_placemark(pm, fallback_id=f"fid_{i}")
        if isinstance(feature, LineStringFeature):
            doc.linestrings.append(feature)
        elif isinstance(feature, PointFeature):
            doc.points.append(feature)
        elif isinstance(feature, PolygonFeature):
            doc.polygons.append(feature)

    return doc


def _extract_doc_kml(kmz_path: Path) -> bytes:
    with zipfile.ZipFile(kmz_path, "r") as zf:
        names = zf.namelist()
        # Prefer the conventional "doc.kml" filename; fall back to the first .kml entry.
        target = "doc.kml" if "doc.kml" in names else next(
            (n for n in names if n.lower().endswith(".kml")), None
        )
        if target is None:
            raise ValueError(f"No .kml entry inside KMZ {kmz_path}")
        return zf.read(target)


def _parse_placemark(pm, fallback_id: str):
    pid = pm.get("id") or fallback_id
    name_el = pm.find(_qn(KML_NS, "name"))
    name = name_el.text if name_el is not None and name_el.text else ""
    desc_el = pm.find(_qn(KML_NS, "description"))
    description_html = desc_el.text if desc_el is not None and desc_el.text else ""
    attributes = _parse_extended_data(pm)
    # ESRI/ArcGIS/Sphere exports embed attributes in an HTML <table> inside
    # <description> rather than <ExtendedData>. Fall back to that when the
    # ExtendedData block is empty.
    if not attributes and description_html:
        attributes = _parse_html_table_attrs(description_html)

    # LineString
    ls_coord = pm.find(f"{_qn(KML_NS, 'LineString')}/{_qn(KML_NS, 'coordinates')}")
    if ls_coord is not None and ls_coord.text:
        coords = _parse_coordinates(ls_coord.text)
        return LineStringFeature(
            id=pid, name=name, attributes=attributes,
            coordinates=coords, description_html=description_html,
        )

    # gx:Track (some hand-builds use this for paths)
    track_coords = pm.findall(f".//{_qn(GX_NS, 'coord')}")
    if track_coords:
        coords = []
        for c in track_coords:
            if c.text:
                parts = c.text.strip().split()
                if len(parts) >= 2:
                    coords.append((float(parts[0]), float(parts[1])))
        if coords:
            return LineStringFeature(
                id=pid, name=name, attributes=attributes,
                coordinates=coords, description_html=description_html,
            )

    # Point
    pt_coord = pm.find(f"{_qn(KML_NS, 'Point')}/{_qn(KML_NS, 'coordinates')}")
    if pt_coord is not None and pt_coord.text:
        coords = _parse_coordinates(pt_coord.text)
        if coords:
            return PointFeature(
                id=pid, name=name, attributes=attributes,
                coordinates=coords[0], description_html=description_html,
            )

    # Polygon
    outer = pm.find(
        f"{_qn(KML_NS, 'Polygon')}/"
        f"{_qn(KML_NS, 'outerBoundaryIs')}/"
        f"{_qn(KML_NS, 'LinearRing')}/"
        f"{_qn(KML_NS, 'coordinates')}"
    )
    if outer is not None and outer.text:
        outer_ring = _parse_coordinates(outer.text)
        inner_rings = []
        for ir in pm.findall(
            f"{_qn(KML_NS, 'Polygon')}/"
            f"{_qn(KML_NS, 'innerBoundaryIs')}/"
            f"{_qn(KML_NS, 'LinearRing')}/"
            f"{_qn(KML_NS, 'coordinates')}"
        ):
            if ir.text:
                inner_rings.append(_parse_coordinates(ir.text))
        return PolygonFeature(
            id=pid, name=name, attributes=attributes,
            outer_ring=outer_ring, inner_rings=inner_rings,
            description_html=description_html,
        )

    return None


def _parse_extended_data(pm) -> dict:
    """Read both <Data name="X"><value>Y</value></Data> and
    <SchemaData><SimpleData name="X">Y</SimpleData></SchemaData> forms."""
    out = {}
    for d in pm.findall(f"{_qn(KML_NS, 'ExtendedData')}/{_qn(KML_NS, 'Data')}"):
        key = d.get("name")
        v = d.find(_qn(KML_NS, "value"))
        if key:
            out[key] = (v.text or "") if v is not None else ""
    for sd in pm.findall(
        f"{_qn(KML_NS, 'ExtendedData')}/"
        f"{_qn(KML_NS, 'SchemaData')}/"
        f"{_qn(KML_NS, 'SimpleData')}"
    ):
        key = sd.get("name")
        if key:
            out[key] = sd.text or ""
    return out


# Two-cell <td>/<td> rows; header rows that use <th> are not matched and so
# are correctly skipped. ".*?" is non-greedy so adjacent rows don't merge.
_HTML_TABLE_ROW_RE = re.compile(
    r"<tr[^>]*>\s*<td[^>]*>(?P<key>.*?)</td>\s*<td[^>]*>(?P<val>.*?)</td>",
    re.IGNORECASE | re.DOTALL,
)
_INLINE_TAG_RE = re.compile(r"<[^>]+>")


def _strip_inline_html(s: str) -> str:
    """Remove inline tags like <b>/<span> and decode HTML entities."""
    if not s:
        return ""
    return _html_lib.unescape(_INLINE_TAG_RE.sub("", s)).strip()


def _parse_html_table_attrs(description_html: str) -> dict:
    """Pull 'Field | Value' rows out of an HTML table embedded in <description>.

    ESRI / ArcGIS Online / Sphere exports stash attributes here rather than
    in <ExtendedData>. Header rows using <th> are naturally skipped because
    the regex requires both cells to be <td>. Cells containing inline tags
    (<b>, <span>...) are flattened to plain text.
    """
    if not description_html or "<td" not in description_html.lower():
        return {}
    out: dict[str, str] = {}
    for m in _HTML_TABLE_ROW_RE.finditer(description_html):
        key = _strip_inline_html(m.group("key"))
        if not key or key.lower() in {"field name", "field", "name"}:
            continue
        val = _strip_inline_html(m.group("val"))
        out[key] = val
    return out


def _parse_coordinates(text: str) -> list[tuple[float, float]]:
    """KML coordinates are 'lon,lat[,alt] lon,lat[,alt] ...' (whitespace-separated tuples)."""
    coords = []
    for tok in text.strip().split():
        parts = tok.split(",")
        if len(parts) >= 2:
            coords.append((float(parts[0]), float(parts[1])))
    return coords
