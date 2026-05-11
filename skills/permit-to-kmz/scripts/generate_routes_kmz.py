#!/usr/bin/env python3
"""
generate_routes_kmz.py — Drafter-ready KMZ from JB-grouped route polylines.

Folder layout (ruthlessly minimal — everything not drafted is stripped):

    <JB0001914985>/                         [VISIBLE]
        NEW <STATUS> <CONSTR> <CT>ct <FT>'   one LineString per cable run
        ...
        MARKUP <reviewer note>               reviewer-drawn segments (same folder
                                             as new work so drafters pick them up)
    <JB0001970651>/
        ...
    UNASSIGNED/                              [VISIBLE, only if present]
        ...
    Design Notes/                            [VISIBLE, but open=0 so drafter can
                                              collapse it with one click]
        <FreeText callout>

There is NO folder for existing infrastructure, transitions, or control points.
Drafters do not draft context, so we do not ship it.

The KMZ works identically for originals (no markups) and revisions. Originals
simply have zero MARKUP lines and a possibly-empty Design Notes folder.

Usage:
    python generate_routes_kmz.py extracted_routes.json control_points.json \\
        --output permit_routes.kmz
"""

import argparse
import json
import math
import sys
from collections import defaultdict

try:
    import simplekml
except ImportError:
    print("ERROR: simplekml not installed. Run: pip install simplekml --break-system-packages")
    sys.exit(1)

import numpy as np


# KML colors are AABBGGRR.
STYLE_TABLE = {
    ("NEW", "AERIAL"):       ("ff0088ff", 4),   # bright orange
    ("NEW", "UNDERGROUND"):  ("ff0000cc", 4),   # deep red
    ("NEW", "UNKNOWN"):      ("ff00aaff", 4),
    ("REPLACE", "AERIAL"):       ("ffc0a0e0", 3),   # lavender/pink
    ("REPLACE", "UNDERGROUND"):  ("ff9900cc", 3),
    ("REPLACE", "UNKNOWN"):      ("ffa060b0", 3),
    ("MARKUP", "AERIAL"):       ("ff0066ff", 5),  # same orange family, thicker
    ("MARKUP", "UNDERGROUND"):  ("ff0044dd", 5),
    ("MARKUP", "UNKNOWN"):      ("ff0077ff", 5),
}

WIDTH_BUMP_BY_COUNT = {
    1728: 3, 864: 3, 576: 3, 432: 2, 288: 2, 216: 2,
    144: 2, 96: 1, 72: 1, 48: 1, 24: 0, 12: 0, 6: 0, None: 0,
}
CONSTR_SHORT = {"AERIAL": "AER", "UNDERGROUND": "UG", "UNKNOWN": "UNK"}


def compute_affine_transform(control_points):
    n = len(control_points)
    if n < 3:
        raise ValueError(f"Need at least 3 control points, got {n}")

    A = np.zeros((n, 3))
    b_lon = np.zeros(n)
    b_lat = np.zeros(n)
    for i, cp in enumerate(control_points):
        A[i, 0] = cp["pdf_x"]
        A[i, 1] = cp["pdf_y"]
        A[i, 2] = 1.0
        b_lon[i] = cp["lon"]
        b_lat[i] = cp["lat"]
    lon_coeffs, *_ = np.linalg.lstsq(A, b_lon, rcond=None)
    lat_coeffs, *_ = np.linalg.lstsq(A, b_lat, rcond=None)

    t = {
        "lon_a": lon_coeffs[0], "lon_b": lon_coeffs[1], "lon_c": lon_coeffs[2],
        "lat_a": lat_coeffs[0], "lat_b": lat_coeffs[1], "lat_c": lat_coeffs[2],
    }
    residuals = []
    for cp in control_points:
        pred_lon = t["lon_a"] * cp["pdf_x"] + t["lon_b"] * cp["pdf_y"] + t["lon_c"]
        pred_lat = t["lat_a"] * cp["pdf_x"] + t["lat_b"] * cp["pdf_y"] + t["lat_c"]
        dlat = (pred_lat - cp["lat"]) * 111320
        dlon = (pred_lon - cp["lon"]) * 111320 * math.cos(math.radians(cp["lat"]))
        residuals.append({"name": cp["name"],
                          "error_meters": round(math.sqrt(dlat ** 2 + dlon ** 2), 1)})
    return t, residuals


def to_lonlat(x, y, t):
    lon = t["lon_a"] * x + t["lon_b"] * y + t["lon_c"]
    lat = t["lat_a"] * x + t["lat_b"] * y + t["lat_c"]
    return (lon, lat)


def style_for(status, construction, count):
    color, width = STYLE_TABLE.get((status, construction), ("ff888888", 2))
    width += WIDTH_BUMP_BY_COUNT.get(count, 0)
    return color, width


def _description(pl, job, default_sub):
    rows = [
        ("Job", job),
        ("Sub-area", pl.get("sub_area") or default_sub or "(none)"),
        ("Status", pl["status"]),
        ("Construction", pl["construction"]),
        ("Cable count", f"{pl['cable_count']}ct" if pl.get("cable_count") else "(none)"),
        ("Footage", f"{pl['footage_ft']}'" if pl.get("footage_ft") else "(none)"),
        ("Source", pl.get("source", "vector")),
    ]
    if pl.get("note"):
        rows.append(("Reviewer note", pl["note"]))
    if pl.get("stroke_color"):
        rows.append(("Stroke color", str(pl["stroke_color"])))
    inner = "".join(f"<tr><td><b>{k}</b></td><td>{v}</td></tr>" for k, v in rows)
    return f'<table border="1" cellpadding="4" cellspacing="0">{inner}</table>'


def _line_name(pl, job):
    status = pl["status"]
    constr_lbl = CONSTR_SHORT.get(pl["construction"], "UNK")
    ct_lbl = f"{pl['cable_count']}ct" if pl.get("cable_count") else ""
    ft_lbl = f"{pl['footage_ft']:.0f}'" if pl.get("footage_ft") else ""
    if status == "MARKUP":
        tag = "MARKUP"
        # Include reviewer note if it is short enough
        note = (pl.get("note") or "").splitlines()[0] if pl.get("note") else ""
        note = note[:40].strip()
        parts = [tag, note, constr_lbl, ct_lbl, ft_lbl]
    else:
        parts = [status, constr_lbl, ct_lbl, ft_lbl]
    name = " ".join(p for p in parts if p)
    return name or f"{job} {status}"


def generate_kmz(routes_path, control_points_path, output_path):
    with open(routes_path) as f:
        routes = json.load(f)
    with open(control_points_path) as f:
        cp_data = json.load(f)

    transform, residuals = compute_affine_transform(cp_data["control_points"])

    print("--- Control point residuals ---")
    max_err = 0.0
    for r in residuals:
        flag = "OK" if r["error_meters"] < 50 else ("WARN" if r["error_meters"] < 100 else "BAD")
        print(f"  {r['name']}: {r['error_meters']:.1f}m [{flag}]")
        max_err = max(max_err, r["error_meters"])
    if max_err > 100:
        print(f"WARNING: max residual {max_err:.1f}m — verify control points.")

    kml = simplekml.Kml(name="Sphere Permit Routes")

    # Group polylines by JB. Skip EXISTING entirely.
    by_job = defaultdict(list)
    for pl in routes["polylines"]:
        if pl["status"] == "EXISTING":
            continue
        by_job[pl.get("job") or "UNASSIGNED"].append(pl)

    # Emit jobs in a stable order: real JBs first, then UNASSIGNED.
    def _sort_key(job):
        if job == "UNASSIGNED":
            return (99, job)
        return (0, job)

    written = defaultdict(int)
    for job in sorted(by_job.keys(), key=_sort_key):
        plys = by_job[job]
        fld = kml.newfolder(name=job)
        fld.visibility = 1
        fld.open = 1

        # Pick a default sub-area string for the description if most polylines
        # in this job share one
        sub_counts = defaultdict(int)
        for pl in plys:
            if pl.get("sub_area"):
                sub_counts[pl["sub_area"]] += 1
        default_sub = max(sub_counts, key=sub_counts.get) if sub_counts else None

        for pl in plys:
            coords_ll = [to_lonlat(x, y, transform) for (x, y) in pl["coords"]]
            ls = fld.newlinestring(name=_line_name(pl, job))
            ls.coords = coords_ll
            ls.description = _description(pl, job, default_sub)
            color, width = style_for(pl["status"], pl["construction"], pl.get("cable_count"))
            ls.style.linestyle.color = color
            ls.style.linestyle.width = width
            # MARKUP: always visible
            if pl["status"] == "MARKUP":
                ls.visibility = 1
            written[(job, pl["status"])] += 1

    # Design notes in a collapsible folder. Visible=1, open=0 so the drafter
    # can hide it with one click without losing access to the text.
    notes = routes.get("design_notes", [])
    notes_fld = kml.newfolder(name="Design Notes")
    notes_fld.visibility = 1
    notes_fld.open = 0
    for n in notes:
        lon, lat = to_lonlat(n["pdf_x"], n["pdf_y"], transform)
        text = n.get("text") or "(no content)"
        first_line = text.splitlines()[0][:60] if text else "(note)"
        pnt = notes_fld.newpoint(name=first_line)
        pnt.coords = [(lon, lat)]
        pnt.description = f"<pre>{text}</pre>"
        pnt.style.iconstyle.icon.href = "http://maps.google.com/mapfiles/kml/pal3/icon31.png"
        pnt.style.iconstyle.scale = 0.7
        pnt.style.labelstyle.scale = 0.6

    kml.savekmz(output_path)

    # --- Summary ---
    summary = {
        "output_path": output_path,
        "jobs": sorted(by_job.keys(), key=_sort_key),
        "lines_by_job_status": {f"{j} / {s}": n for (j, s), n in sorted(written.items())},
        "design_notes": len(notes),
        "max_control_point_error_m": round(max_err, 1),
    }
    print("\n" + "=" * 50)
    print(f"KMZ saved to: {output_path}")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("=" * 50)
    return summary


def main():
    ap = argparse.ArgumentParser(description="Generate drafter-ready KMZ grouped by JB job")
    ap.add_argument("routes", help="Path to extracted_routes.json")
    ap.add_argument("control_points", help="Path to control_points.json")
    ap.add_argument("--output", default="permit_routes.kmz")
    args = ap.parse_args()

    result = generate_kmz(args.routes, args.control_points, args.output)
    report_path = args.output.replace(".kmz", "_report.json")
    with open(report_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    main()
