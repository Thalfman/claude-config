#!/usr/bin/env python3
"""
generate_routes_pdf.py — Per-JB permit PDF, one page per job.

Each page shows the routes of a single JB job over a light-gray basemap
synthesized from the PDF's own EXISTING infrastructure polylines, plus a
spec table on the right with counts, cable-count distribution, total
footage, markup count, and a legend.

Colors mirror the KMZ:
  NEW aerial       = orange solid
  NEW underground  = red dotted
  REPLACE          = pink dash-dot
  MARKUP           = bold orange dashed (same folder as new work in KMZ)

Input: extracted_routes.json + control_points.json.

Usage:
    python generate_routes_pdf.py extracted_routes.json control_points.json \\
        --output permit_by_job.pdf
"""

import argparse
import json
import math
import os
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np


def fit_affine(cps):
    n = len(cps)
    M = np.zeros((2 * n, 6))
    v = np.zeros(2 * n)
    for i, cp in enumerate(cps):
        x, y, lat, lon = cp["pdf_x"], cp["pdf_y"], cp["lat"], cp["lon"]
        M[2 * i, 0] = x;  M[2 * i, 1] = y;  M[2 * i, 2] = 1
        M[2 * i + 1, 3] = x;  M[2 * i + 1, 4] = y;  M[2 * i + 1, 5] = 1
        v[2 * i] = lon
        v[2 * i + 1] = lat
    coef, *_ = np.linalg.lstsq(M, v, rcond=None)
    return coef.reshape(2, 3)


def apply_aff(A, x, y):
    return (A[0, 0] * x + A[0, 1] * y + A[0, 2],
            A[1, 0] * x + A[1, 1] * y + A[1, 2])


def poly_to_latlon(A, coords):
    lons = [A[0, 0] * c[0] + A[0, 1] * c[1] + A[0, 2] for c in coords]
    lats = [A[1, 0] * c[0] + A[1, 1] * c[1] + A[1, 2] for c in coords]
    return lons, lats


def job_bbox(polys, pad=0.002):
    if not polys:
        return None
    xs, ys = [], []
    for pl in polys:
        for c in pl["_lonlat"]:
            xs.append(c[0]); ys.append(c[1])
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def draw_job_page(pdf, job, job_polys, all_existing, design_notes, bbox):
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_axes([0.04, 0.08, 0.60, 0.85])
    tx = fig.add_axes([0.67, 0.08, 0.30, 0.85])
    tx.axis("off")

    ax.set_aspect(1 / math.cos(math.radians((bbox[1] + bbox[3]) / 2)))
    ax.set_xlim(bbox[0], bbox[2])
    ax.set_ylim(bbox[1], bbox[3])
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.2, linewidth=0.3)
    ax.set_title(f"Permit Map — {job}", fontsize=14, weight="bold")

    # Basemap from PDF's own EXISTING infrastructure, light gray
    for lons, lats in all_existing:
        ax.plot(lons, lats, color="#cccccc", linewidth=0.5, zorder=1)

    stats = Counter()
    sub_counter = Counter()
    cable_counter = Counter()
    total_ft = 0.0
    markup_count = 0
    for pl in job_polys:
        lons = [c[0] for c in pl["_lonlat"]]
        lats = [c[1] for c in pl["_lonlat"]]
        status = pl["status"]
        constr = pl.get("construction", "UNKNOWN")
        cc = pl.get("cable_count")
        if pl.get("sub_area"):
            sub_counter[pl["sub_area"]] += 1

        if status == "MARKUP":
            ax.plot(lons, lats, color="#ff6b00", linewidth=3.0,
                    linestyle="--", zorder=5, alpha=0.85)
            markup_count += 1
            continue

        if status == "NEW":
            color = "#d00000" if constr == "UNDERGROUND" else "#ff8800"
            linestyle = ":" if constr == "UNDERGROUND" else "-"
        elif status == "REPLACE":
            color = "#e0a0c0"
            linestyle = "-."
        else:
            continue

        lw = 1.6
        if cc:
            if cc >= 144: lw = 3.6
            elif cc >= 96: lw = 3.0
            elif cc >= 48: lw = 2.4
            else: lw = 2.0
        ax.plot(lons, lats, color=color, linewidth=lw, linestyle=linestyle, zorder=4)

        stats[f"{status}/{constr}"] += 1
        if cc: cable_counter[cc] += 1
        if pl.get("footage_ft"): total_ft += pl["footage_ft"]

    note_count = 0
    for n in design_notes:
        lon, lat = n["_lon"], n["_lat"]
        if bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]:
            ax.plot(lon, lat, marker="s", markersize=4, color="#2060c0",
                    zorder=6, markerfacecolor="#a0c8ff")
            note_count += 1

    # --- Spec panel ---
    y = 0.97
    tx.text(0.0, y, job, fontsize=16, weight="bold", transform=tx.transAxes)
    y -= 0.05
    tx.text(0.0, y, f"Total lines: {len(job_polys)}", fontsize=10, transform=tx.transAxes)
    y -= 0.04
    tx.text(0.0, y, f"Markup segments: {markup_count}", fontsize=10, transform=tx.transAxes)
    y -= 0.04
    tx.text(0.0, y, f"Design notes in view: {note_count}", fontsize=10, transform=tx.transAxes)
    y -= 0.04
    tx.text(0.0, y, f"Total footage (NEW): {total_ft:,.0f} ft", fontsize=10, transform=tx.transAxes)

    y -= 0.06
    tx.text(0.0, y, "Status / Construction", fontsize=11, weight="bold", transform=tx.transAxes)
    y -= 0.04
    for key, n in sorted(stats.items()):
        tx.text(0.02, y, f"{key}: {n}", fontsize=9, transform=tx.transAxes)
        y -= 0.03

    if sub_counter:
        y -= 0.04
        tx.text(0.0, y, "Sub-areas (INCWT) on this page", fontsize=11, weight="bold",
                transform=tx.transAxes)
        y -= 0.04
        for sub, n in sorted(sub_counter.items()):
            tx.text(0.02, y, f"{sub}: {n}", fontsize=9, transform=tx.transAxes)
            y -= 0.03

    y -= 0.04
    tx.text(0.0, y, "Cable count distribution", fontsize=11, weight="bold",
            transform=tx.transAxes)
    y -= 0.04
    for cc, n in sorted(cable_counter.items()):
        tx.text(0.02, y, f"{cc} ct: {n}", fontsize=9, transform=tx.transAxes)
        y -= 0.03

    y -= 0.06
    tx.text(0.0, y, "Legend", fontsize=11, weight="bold", transform=tx.transAxes)
    y -= 0.035
    for label, color, ls, lw in [
        ("NEW Aerial", "#ff8800", "-", 2.5),
        ("NEW Underground", "#d00000", ":", 2.5),
        ("REPLACE", "#e0a0c0", "-.", 2.0),
        ("MARKUP (reviewer)", "#ff6b00", "--", 3.0),
        ("Existing (context)", "#cccccc", "-", 1.5),
    ]:
        tx.plot([0.02, 0.10], [y, y], color=color, linewidth=lw, linestyle=ls,
                transform=tx.transAxes)
        tx.text(0.12, y - 0.004, label, fontsize=9, transform=tx.transAxes)
        y -= 0.035

    y -= 0.02
    tx.text(0.0, y, "Design note  ", fontsize=9, transform=tx.transAxes)
    tx.plot([0.23], [y + 0.006], marker="s", markersize=5, color="#2060c0",
            markerfacecolor="#a0c8ff", transform=tx.transAxes)

    pdf.savefig(fig)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("routes_json")
    ap.add_argument("control_points_json")
    ap.add_argument("--output", default="permit_by_job.pdf")
    args = ap.parse_args()

    data = json.load(open(args.routes_json))
    cp = json.load(open(args.control_points_json))
    A = fit_affine(cp["control_points"])

    existing_segments = []
    by_job = defaultdict(list)
    for pl in data["polylines"]:
        lons, lats = poly_to_latlon(A, pl["coords"])
        pl["_lonlat"] = list(zip(lons, lats))
        if pl["status"] == "EXISTING":
            existing_segments.append((lons, lats))
        else:
            by_job[pl.get("job") or "UNASSIGNED"].append(pl)

    for n in data.get("design_notes", []):
        lon, lat = apply_aff(A, n["pdf_x"], n["pdf_y"])
        n["_lon"] = lon; n["_lat"] = lat

    def _sort(j):
        if j == "UNASSIGNED":
            return (99, j)
        return (0, j)

    with PdfPages(args.output) as pdf:
        # Cover page
        fig = plt.figure(figsize=(11, 8.5))
        fig.text(0.5, 0.93, "Sphere Permit Map — Per-Job Summary",
                 ha="center", fontsize=20, weight="bold")
        fig.text(0.5, 0.88, f"Source: {os.path.basename(data.get('pdf_path', '?'))}",
                 ha="center", fontsize=10, color="#555")
        y = 0.80
        fig.text(0.10, y, "Jobs (JB numbers) in this permit:", fontsize=13, weight="bold")
        y -= 0.04
        for job in sorted(by_job.keys(), key=_sort):
            plys = by_job[job]
            n_new = sum(1 for p in plys if p["status"] == "NEW")
            n_repl = sum(1 for p in plys if p["status"] == "REPLACE")
            n_mkp = sum(1 for p in plys if p["status"] == "MARKUP")
            tot_ft = sum(p.get("footage_ft") or 0 for p in plys)
            fig.text(0.12, y,
                     f"{job:<18s}  NEW {n_new:>3d}  REPLACE {n_repl:>2d}  MARKUP {n_mkp:>2d}  footage {tot_ft:,.0f} ft",
                     fontsize=10, family="monospace")
            y -= 0.03

        y -= 0.05
        fig.text(0.10, y, "Deliverable reminders:", fontsize=13, weight="bold")
        y -= 0.04
        for note in [
            "One page per JB job follows. Orange = new aerial. Red dotted = new underground.",
            "Pink dash-dot = replace / abandoned cable.",
            "Bold orange dashes = reviewer markup — drafter draws cable per these lines.",
            "Light gray lines are existing infrastructure shown for context only.",
            "Blue squares are design-note callouts from the reviewer.",
        ]:
            fig.text(0.12, y, "- " + note, fontsize=10)
            y -= 0.03
        pdf.savefig(fig)
        plt.close(fig)

        for job in sorted(by_job.keys(), key=_sort):
            polys = by_job[job]
            bbox = job_bbox(polys)
            if bbox is None:
                continue
            draw_job_page(pdf, job, polys, existing_segments,
                          data.get("design_notes", []), bbox)

    print(f"[OK] wrote {args.output}")
    print(f"     jobs: {len(by_job)} pages (plus 1 cover)")


if __name__ == "__main__":
    main()
