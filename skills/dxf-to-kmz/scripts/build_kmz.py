"""Build a contractor-ready KMZ from a DXF + layer_mapping.json (+ optional anchors.json)."""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import ezdxf
import simplekml
from pyproj import Transformer
from shapely.geometry import LineString

from scripts.build_anchors import apply_transform


# --- Geometry extraction -----------------------------------------------------

def extract_geometry(dxf_path: Path) -> dict:
    """Return {layer_name: {"polylines": [...], "points": [...], "labels": [...]}}.

    Polylines are lists of (x, y) tuples in DXF coords. Points are (x, y).
    Labels are (x, y, text) tuples.
    """
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    geom: dict = {}

    def layer_bucket(name: str) -> dict:
        return geom.setdefault(name, {"polylines": [], "points": [], "labels": []})

    for e in msp:
        layer = e.dxf.layer
        bucket = layer_bucket(layer)
        kind = e.dxftype()

        if kind == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points()]
            if e.closed and pts and pts[0] != pts[-1]:
                pts = pts + [pts[0]]
            bucket["polylines"].append(pts)
        elif kind == "POLYLINE":
            pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
            if e.is_closed and pts and pts[0] != pts[-1]:
                pts = pts + [pts[0]]
            bucket["polylines"].append(pts)
        elif kind == "LINE":
            bucket["polylines"].append([
                (e.dxf.start.x, e.dxf.start.y),
                (e.dxf.end.x,   e.dxf.end.y),
            ])
        elif kind == "POINT":
            bucket["points"].append((e.dxf.location.x, e.dxf.location.y))
        elif kind == "INSERT":
            bucket["points"].append((e.dxf.insert.x, e.dxf.insert.y))
        elif kind == "TEXT":
            text = e.dxf.text
            # Aligned (non-LEFT) TEXT stores its real position in align_point;
            # default-aligned TEXT uses insert. Both attrs always exist; check halign/valign.
            if e.dxf.halign != 0 or e.dxf.valign != 0:
                pos = e.dxf.align_point
            else:
                pos = e.dxf.insert
            bucket["labels"].append((pos.x, pos.y, text))
        elif kind == "MTEXT":
            # MTEXT uses .text accessor (handles continuation records + format codes).
            text = e.text
            pos = e.dxf.insert
            bucket["labels"].append((pos.x, pos.y, text))

    return geom


# --- Reprojection ------------------------------------------------------------

def reproject_coords(pts: list[tuple[float, float]],
                     source_epsg: Optional[str] = None,
                     source_wkt: Optional[str] = None,
                     anchors_transform: Optional[dict] = None,
                     ) -> list[tuple[float, float]]:
    """Convert (x, y) DXF coords -> (lat, lon) WGS84.

    Either source_epsg, source_wkt, or anchors_transform must be supplied.
    """
    source_crs = source_epsg or source_wkt
    if source_crs:
        transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
        out = []
        for x, y in pts:
            lon, lat = transformer.transform(x, y)
            out.append((lat, lon))
        return out

    if anchors_transform:
        return [apply_transform(anchors_transform, x, y) for x, y in pts]

    raise ValueError("Need source_epsg, source_wkt, or anchors_transform")


# --- Style mapping -----------------------------------------------------------

def _kmz_color(hex_aabbggrr: str) -> str:
    """KML uses aabbggrr; our style strings already match. Pass through."""
    return hex_aabbggrr


def _apply_polyline_style(linestring, style: dict):
    if "color" in style:
        linestring.style.linestyle.color = _kmz_color(style["color"])
    if "width" in style:
        linestring.style.linestyle.width = style["width"]
    # KML doesn't natively support dashed polylines reliably; folder names
    # disambiguate aerial vs underground for the contractor.


def _apply_polygon_style(polygon, style: dict):
    if "line_color" in style:
        polygon.style.linestyle.color = _kmz_color(style["line_color"])
    if "fill_color" in style:
        polygon.style.polystyle.color = _kmz_color(style["fill_color"])
    if "width" in style:
        polygon.style.linestyle.width = style["width"]


# --- Folder hierarchy --------------------------------------------------------

TOP_LEVEL_ORDER = [
    "Permit Area",
    "Proposed Route",
    "Proposed Infrastructure",
    "Stations & Labels",
    "Existing Infrastructure",
    "Other",
]


def _ensure_folder(parent, path: str, visibility: int = 1):
    """Create or fetch a /-separated folder path under parent."""
    parts = path.split("/")
    cur = parent
    for part in parts:
        existing = next((f for f in cur.features if isinstance(f, simplekml.Folder) and f.name == part), None)
        if existing is None:
            existing = cur.newfolder(name=part, visibility=visibility)
        cur = existing
    return cur


# --- Main pipeline -----------------------------------------------------------

def build_kmz(dxf_path: Path,
              mapping_path: Path,
              output_path: Path,
              anchors_path: Optional[Path] = None,
              simplify_ft: float = 0.5) -> Path:
    """Produce a KMZ from a DXF + layer mapping + (optional) anchors."""
    mapping = json.loads(Path(mapping_path).read_text())
    geom = extract_geometry(Path(dxf_path))

    crs_block = mapping.get("crs", {})
    source_epsg = crs_block.get("epsg")
    source_wkt = crs_block.get("wkt") if not source_epsg else None

    anchors_transform = None
    if anchors_path:
        anchors_data = json.loads(Path(anchors_path).read_text())
        anchors_transform = anchors_data["transform"]
        source_epsg = None  # anchors take priority
        source_wkt = None

    if not source_epsg and not source_wkt and not anchors_transform:
        raise ValueError(
            f"No CRS available. Either layer_mapping.json must have crs.epsg or crs.wkt, "
            f"or anchors.json must be supplied. Current crs block: {crs_block}"
        )

    kml = simplekml.Kml()
    doc = kml.document
    doc.name = mapping["kmz_meta"]["title"]

    # Description: provenance + quality bar
    crs_label = source_epsg or (crs_block.get("label") if source_wkt else None) or "manual anchors"
    confidence = crs_block.get("confidence", "MANUAL")
    tier = crs_block.get("tier", 3)
    doc.description = (
        f"{mapping['kmz_meta']['description']}\n\n"
        f"Coordinates derived via Tier {tier} ({crs_label}). "
        f"Confidence: {confidence}.\n\n"
        f"Not certified for engineering layout - for that, use the source DWG in Civil 3D."
    )

    # Pre-create top-level folders so they appear in stable order
    for top in TOP_LEVEL_ORDER:
        vis = 0 if top == "Existing Infrastructure" else 1
        _ensure_folder(doc, top, visibility=vis)

    # Walk layers in mapping order
    for layer_entry in mapping["layers"]:
        if not layer_entry["publish"] and layer_entry["subtype"] != "existing":
            continue
        if layer_entry["feature"] is None:
            continue

        layer_name = layer_entry["name"]
        bucket = geom.get(layer_name, {})
        if not (bucket.get("polylines") or bucket.get("points") or bucket.get("labels")):
            continue

        folder_path = layer_entry["folder"] or "Other"
        is_existing = layer_entry["subtype"] == "existing"
        folder_vis = 0 if is_existing else 1
        folder = _ensure_folder(doc, folder_path, visibility=folder_vis)

        feat = layer_entry["feature"]
        sub = layer_entry["subtype"]
        style = layer_entry["style"]

        # POLYLINES
        for pts in bucket.get("polylines", []):
            if simplify_ft > 0 and len(pts) > 3:
                line = LineString(pts).simplify(simplify_ft, preserve_topology=False)
                pts = list(line.coords)
            reproj = reproject_coords(pts, source_epsg=source_epsg,
                                      source_wkt=source_wkt,
                                      anchors_transform=anchors_transform)
            kml_coords = [(lon, lat) for (lat, lon) in reproj]

            if feat == "polygon":
                poly = folder.newpolygon(name=f"{layer_name}")
                poly.outerboundaryis = kml_coords
                poly.altitudemode = simplekml.AltitudeMode.clamptoground
                _apply_polygon_style(poly, style)
            else:
                ls = folder.newlinestring(name=f"{layer_name}", coords=kml_coords)
                ls.altitudemode = simplekml.AltitudeMode.clamptoground
                _apply_polyline_style(ls, style)

        # POINTS
        for (x, y) in bucket.get("points", []):
            reproj = reproject_coords([(x, y)], source_epsg=source_epsg,
                                      source_wkt=source_wkt,
                                      anchors_transform=anchors_transform)
            lat, lon = reproj[0]
            pt = folder.newpoint(name=f"{layer_name}", coords=[(lon, lat)])
            pt.altitudemode = simplekml.AltitudeMode.clamptoground
            if "color" in style:
                pt.style.iconstyle.color = _kmz_color(style["color"])

        # LABELS
        for (x, y, text) in bucket.get("labels", []):
            reproj = reproject_coords([(x, y)], source_epsg=source_epsg,
                                      source_wkt=source_wkt,
                                      anchors_transform=anchors_transform)
            lat, lon = reproj[0]
            pt = folder.newpoint(name=text, coords=[(lon, lat)])
            pt.altitudemode = simplekml.AltitudeMode.clamptoground
            pt.style.iconstyle.scale = 0  # hide pin, show label only
            if "text_color" in style:
                pt.style.labelstyle.color = _kmz_color(style["text_color"])

    output_path = Path(output_path)
    kml.savekmz(str(output_path))
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Build KMZ from DXF + layer_mapping.json")
    parser.add_argument("dxf_path", type=Path)
    parser.add_argument("mapping_path", type=Path)
    parser.add_argument("--anchors", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=Path("contractor.kmz"))
    parser.add_argument("--simplify", type=float, default=0.5,
                        help="Douglas-Peucker tolerance in source units (default 0.5 ft)")
    args = parser.parse_args()

    out = build_kmz(args.dxf_path, args.mapping_path,
                    output_path=args.output,
                    anchors_path=args.anchors,
                    simplify_ft=args.simplify)
    print(f"Wrote {out}")


if __name__ == "__main__":
    sys.exit(main())
