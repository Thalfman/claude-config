"""Render PdfResult records to CSV and KML deliverables."""
import csv
from pathlib import Path
from typing import List

import pandas as pd
import simplekml

from scripts.pdf_processor import PdfResult


_MAIN_COLUMNS = [
    "pdf_file", "page_number", "sheet_id",
    "start_label", "start_station", "start_lat", "start_lon",
    "end_label", "end_station", "end_lat", "end_lon",
    "road_names", "structures", "span_lengths_ft",
    "construction_type", "continues_from_sheet", "continues_to_sheet",
    "coords_source", "has_native_gps",
]

_VICINITY_COLUMNS = ["pdf_file", "page_number", "page_type", "lat", "lon", "note"]


def _join_list(values) -> str:
    """Serialize a list as a pipe-separated string.

    Empty lists write as a single dash so that columns containing a mix of
    numeric strings and empty cells are never coerced to float by pd.read_csv.
    """
    if not values:
        return "-"
    return "|".join(str(v) for v in values)


def write_main_csv(results: List[PdfResult], output_path: Path) -> None:
    """Write the per-sheet CSV with one row per plan-profile sheet across all PDFs."""
    rows = []
    for r in results:
        for s in r.sheets:
            rows.append({
                "pdf_file": r.pdf_file,
                "page_number": s.page_number,
                "sheet_id": s.sheet_id,
                "start_label": s.start_label,
                "start_station": s.start_station,
                "start_lat": s.start_lat,
                "start_lon": s.start_lon,
                "end_label": s.end_label,
                "end_station": s.end_station,
                "end_lat": s.end_lat,
                "end_lon": s.end_lon,
                "road_names": _join_list(s.road_names),
                "structures": _join_list(s.structures),
                "span_lengths_ft": _join_list(s.span_lengths_ft),
                "construction_type": s.construction_type,
                "continues_from_sheet": s.continues_from_sheet,
                "continues_to_sheet": s.continues_to_sheet,
                "coords_source": s.coords_source,
                "has_native_gps": s.has_native_gps,
            })
    df = pd.DataFrame(rows, columns=_MAIN_COLUMNS)
    # Force list-serialized columns to stay as strings so pandas doesn't coerce
    # single-element numeric strings (e.g. "260.0") back to float on re-read.
    for col in ("road_names", "structures", "span_lengths_ft"):
        df[col] = df[col].astype(str)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, quoting=csv.QUOTE_NONNUMERIC)


def write_vicinity_csv(results: List[PdfResult], output_path: Path) -> None:
    """Write the vicinity/cover-page reference CSV — never used to geolocate plan sheets."""
    rows = []
    for r in results:
        for v in r.vicinity_coords:
            rows.append({
                "pdf_file": r.pdf_file,
                "page_number": v.page_number,
                "page_type": v.page_type,
                "lat": v.lat,
                "lon": v.lon,
                "note": v.note,
            })
    df = pd.DataFrame(rows, columns=_VICINITY_COLUMNS)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def write_kml(results: List[PdfResult], output_path: Path) -> None:
    """Render KML with start/end pins ONLY for sheets where has_native_gps is True.

    Vicinity-page coordinates are intentionally excluded from the KML —
    they live in vicinity_reference.csv as reference-only data.
    """
    kml = simplekml.Kml()
    folder = kml.newfolder(name="Plan-sheet endpoints (native GPS only)")

    for r in results:
        for s in r.sheets:
            if not s.has_native_gps:
                continue
            sheet_label = f"Sheet {s.sheet_id}" if s.sheet_id else f"Page {s.page_number}"
            if s.start_lat is not None and s.start_lon is not None:
                folder.newpoint(
                    name=f"{sheet_label} start ({s.start_label or s.start_station or ''})".strip(),
                    coords=[(s.start_lon, s.start_lat)],
                    description=(
                        f"PDF: {r.pdf_file}\n"
                        f"Page: {s.page_number}\n"
                        f"Construction: {s.construction_type or 'unknown'}\n"
                        f"Roads: {', '.join(s.road_names) if s.road_names else 'unknown'}"
                    ),
                )
            if s.end_lat is not None and s.end_lon is not None:
                folder.newpoint(
                    name=f"{sheet_label} end ({s.end_label or s.end_station or ''})".strip(),
                    coords=[(s.end_lon, s.end_lat)],
                    description=(
                        f"PDF: {r.pdf_file}\n"
                        f"Page: {s.page_number}\n"
                        f"Continues to: {s.continues_to_sheet or 'unknown'}"
                    ),
                )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    kml.save(str(output_path))
