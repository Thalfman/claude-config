from pathlib import Path

import pandas as pd

from scripts.output_writer import write_main_csv, write_vicinity_csv
from scripts.pdf_processor import PdfResult
from scripts.sheet_extractor import SheetData, VicinityCoord


def _sample_results() -> list:
    return [PdfResult(
        pdf_file="example.pdf",
        sheets=[
            SheetData(
                page_number=3,
                sheet_id="5",
                start_label="POLE 32",
                start_station="STA 0+00",
                start_lat=34.123,
                start_lon=-118.123,
                end_label="POLE 35",
                end_station="STA 12+50",
                end_lat=34.124,
                end_lon=-118.124,
                road_names=["MAIN ST"],
                structures=["POLE 32", "POLE 35"],
                span_lengths_ft=[260.0],
                construction_type="aerial",
                continues_from_sheet=None,
                continues_to_sheet="6",
                coords_source="printed_on_this_sheet",
                has_native_gps=True,
            ),
            SheetData(
                page_number=4,
                sheet_id="6",
                coords_source="none",
                has_native_gps=False,
            ),
        ],
        vicinity_coords=[
            VicinityCoord(page_number=2, page_type="vicinity", lat=34.10, lon=-118.10, note="decimal_degrees"),
        ],
        raster_pages=[],
    )]


def test_write_main_csv_includes_every_required_column(tmp_path: Path):
    out = tmp_path / "main.csv"
    write_main_csv(_sample_results(), out)
    df = pd.read_csv(out)
    expected_columns = [
        "pdf_file", "page_number", "sheet_id",
        "start_label", "start_station", "start_lat", "start_lon",
        "end_label", "end_station", "end_lat", "end_lon",
        "road_names", "structures", "span_lengths_ft",
        "construction_type", "continues_from_sheet", "continues_to_sheet",
        "coords_source", "has_native_gps",
    ]
    for col in expected_columns:
        assert col in df.columns


def test_write_main_csv_two_rows(tmp_path: Path):
    out = tmp_path / "main.csv"
    write_main_csv(_sample_results(), out)
    df = pd.read_csv(out)
    assert len(df) == 2
    assert df.iloc[0]["pdf_file"] == "example.pdf"
    assert df.iloc[0]["page_number"] == 3
    assert df.iloc[0]["has_native_gps"] is True or df.iloc[0]["has_native_gps"] == "True" or df.iloc[0]["has_native_gps"] == True
    assert df.iloc[1]["coords_source"] == "none"


def test_write_main_csv_serializes_lists_as_pipe_separated(tmp_path: Path):
    out = tmp_path / "main.csv"
    write_main_csv(_sample_results(), out)
    df = pd.read_csv(out)
    assert df.iloc[0]["structures"] == "POLE 32|POLE 35"
    assert df.iloc[0]["span_lengths_ft"] == "260.0"


def test_write_vicinity_csv_columns(tmp_path: Path):
    out = tmp_path / "vicinity.csv"
    write_vicinity_csv(_sample_results(), out)
    df = pd.read_csv(out)
    expected = ["pdf_file", "page_number", "page_type", "lat", "lon", "note"]
    for col in expected:
        assert col in df.columns
    assert len(df) == 1
    assert df.iloc[0]["lat"] == 34.10


def test_write_vicinity_csv_handles_empty(tmp_path: Path):
    """Empty results still produce a file with headers — easier for downstream tools."""
    empty = [PdfResult(pdf_file="empty.pdf")]
    out = tmp_path / "vicinity.csv"
    write_vicinity_csv(empty, out)
    df = pd.read_csv(out)
    assert list(df.columns) == ["pdf_file", "page_number", "page_type", "lat", "lon", "note"]
    assert len(df) == 0


import xml.etree.ElementTree as ET

from scripts.output_writer import write_kml


def test_write_kml_only_includes_native_gps_sheets(tmp_path: Path):
    out = tmp_path / "out.kml"
    write_kml(_sample_results(), out)
    tree = ET.parse(out)
    root = tree.getroot()
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    placemarks = root.findall(".//kml:Placemark", ns)
    # Sample data has 1 sheet with native GPS (start + end coords) and 1 sheet without.
    # The native-GPS sheet should produce 2 placemarks (start pin + end pin).
    assert len(placemarks) == 2


def test_write_kml_excludes_vicinity_coords(tmp_path: Path):
    """Vicinity coords must never appear in the KML — they live only in vicinity_reference.csv."""
    out = tmp_path / "out.kml"
    write_kml(_sample_results(), out)
    tree = ET.parse(out)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    coords_elements = tree.getroot().findall(".//kml:coordinates", ns)
    for c in coords_elements:
        lon, lat, *_ = c.text.strip().split(",")
        # Our vicinity coord was -118.10, 34.10 — assert that pair is NOT present
        assert not (abs(float(lat) - 34.10) < 0.001 and abs(float(lon) - (-118.10)) < 0.001)


def test_write_kml_emits_no_placemarks_when_no_native_gps(tmp_path: Path):
    """Sheet with has_native_gps=False produces zero pins."""
    no_gps = [PdfResult(
        pdf_file="x.pdf",
        sheets=[SheetData(page_number=1, sheet_id="1", coords_source="none", has_native_gps=False)],
    )]
    out = tmp_path / "out.kml"
    write_kml(no_gps, out)
    tree = ET.parse(out)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    placemarks = tree.getroot().findall(".//kml:Placemark", ns)
    assert len(placemarks) == 0


def test_write_kml_pin_label_includes_sheet_id(tmp_path: Path):
    out = tmp_path / "out.kml"
    write_kml(_sample_results(), out)
    text = out.read_text(encoding="utf-8")
    # Sheet 5 had native GPS so its pins should reference the sheet id
    assert "Sheet 5" in text or "SHEET 5" in text or "sheet_id=5" in text
