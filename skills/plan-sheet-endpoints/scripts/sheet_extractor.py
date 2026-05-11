"""Per-page extraction: combine all parsers into SheetData / VicinityCoord."""
from dataclasses import dataclass, field
from typing import List, Optional

import fitz

from scripts.coord_parser import find_all_coords
from scripts.feature_parsers import (
    parse_cable_specs,
    parse_construction_type,
    parse_road_names,
    parse_span_lengths,
    parse_structures,
)
from scripts.page_text import TextBlock
from scripts.sheet_id_parser import parse_continuation_refs, parse_sheet_id
from scripts.station_parser import parse_stations


@dataclass
class SheetData:
    page_number: int
    sheet_id: Optional[str] = None
    start_label: Optional[str] = None
    start_station: Optional[str] = None
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    end_label: Optional[str] = None
    end_station: Optional[str] = None
    end_lat: Optional[float] = None
    end_lon: Optional[float] = None
    road_names: List[str] = field(default_factory=list)
    structures: List[str] = field(default_factory=list)
    span_lengths_ft: List[float] = field(default_factory=list)
    construction_type: Optional[str] = None
    cable_specs: Optional[str] = None
    continues_from_sheet: Optional[str] = None
    continues_to_sheet: Optional[str] = None
    coords_source: str = "none"
    has_native_gps: bool = False


@dataclass
class VicinityCoord:
    page_number: int
    page_type: str
    lat: float
    lon: float
    note: str = ""


def extract_sheet(page: fitz.Page, page_number: int, text: str, blocks: List[TextBlock]) -> SheetData:
    """Build SheetData from a plan-profile page.

    The function is best-effort: any field that can't be extracted stays None
    (or empty list). It never raises on missing data.
    """
    sheet = SheetData(page_number=page_number)

    sheet.sheet_id = parse_sheet_id(text)

    stations = parse_stations(text)
    if stations:
        stations_sorted = sorted(stations, key=lambda s: s.value)
        sheet.start_station = stations_sorted[0].original
        sheet.end_station = stations_sorted[-1].original
        sheet.start_label = stations_sorted[0].original
        sheet.end_label = stations_sorted[-1].original

    coords = find_all_coords(text)
    if coords:
        sheet.has_native_gps = True
        sheet.coords_source = "printed_on_this_sheet"
        sheet.start_lat, sheet.start_lon = coords[0][0], coords[0][1]
        if len(coords) >= 2:
            sheet.end_lat, sheet.end_lon = coords[1][0], coords[1][1]

    sheet.road_names = parse_road_names(text)
    sheet.structures = parse_structures(text)
    if sheet.structures and not sheet.start_label:
        sheet.start_label = sheet.structures[0]
        sheet.end_label = sheet.structures[-1]

    sheet.span_lengths_ft = parse_span_lengths(text)
    sheet.construction_type = parse_construction_type(text)
    sheet.cable_specs = parse_cable_specs(text)

    refs = parse_continuation_refs(text)
    for r in refs:
        if r.direction == "from":
            sheet.continues_from_sheet = r.target
        elif r.direction == "to":
            sheet.continues_to_sheet = r.target

    return sheet


def extract_vicinity_coords(
    page: fitz.Page, page_number: int, page_type: str, text: str
) -> List[VicinityCoord]:
    """Pull every coord pair from a non-plan page, tagged for the vicinity_reference CSV."""
    coords = find_all_coords(text)
    return [
        VicinityCoord(
            page_number=page_number,
            page_type=page_type,
            lat=lat,
            lon=lon,
            note=fmt,
        )
        for lat, lon, fmt in coords
    ]
