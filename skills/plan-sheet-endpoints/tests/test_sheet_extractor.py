from pathlib import Path

import fitz
import pytest

from scripts.page_text import get_page_text, get_text_blocks
from scripts.sheet_extractor import (
    SheetData,
    VicinityCoord,
    extract_sheet,
    extract_vicinity_coords,
)


def _open_first_page(pdf_path: Path):
    doc = fitz.open(pdf_path)
    page = doc[0]
    text = get_page_text(page)
    blocks = get_text_blocks(page)
    return doc, page, text, blocks


def test_extract_sheet_full_plan(plan_sheet_pdf: Path):
    doc, page, text, blocks = _open_first_page(plan_sheet_pdf)
    sheet = extract_sheet(page, page_number=1, text=text, blocks=blocks)
    doc.close()

    assert sheet.page_number == 1
    assert sheet.sheet_id == "5"
    assert sheet.start_station == "0+00" or sheet.start_station == "STA 0+00"
    assert sheet.end_station == "12+50" or sheet.end_station == "STA 12+50"
    assert "POLE 32" in sheet.structures
    assert "POLE 35" in sheet.structures
    assert "MAIN ST" in sheet.road_names
    assert 260.0 in sheet.span_lengths_ft
    assert sheet.construction_type == "aerial"
    assert sheet.continues_to_sheet == "6"
    assert sheet.has_native_gps is True
    assert sheet.coords_source == "printed_on_this_sheet"
    assert sheet.start_lat == pytest.approx(34.123456, abs=1e-4)
    assert sheet.start_lon == pytest.approx(-118.123456, abs=1e-4)


def test_extract_sheet_no_coords_marks_none(tmp_path: Path):
    """A sheet with stations but no coordinates: has_native_gps must be False."""
    doc = fitz.open()
    page = doc.new_page(width=1224, height=792)
    page.insert_text((50, 50), "SITE PLAN - 7", fontsize=10)
    page.insert_text((50, 80), "STA 0+00", fontsize=10)
    page.insert_text((200, 80), "STA 5+00", fontsize=10)
    page.insert_text((50, 110), "POLE 1", fontsize=10)
    out = tmp_path / "no_coords.pdf"
    doc.save(out)
    doc.close()

    doc = fitz.open(out)
    page = doc[0]
    text = get_page_text(page)
    blocks = get_text_blocks(page)
    sheet = extract_sheet(page, page_number=1, text=text, blocks=blocks)
    doc.close()

    assert sheet.has_native_gps is False
    assert sheet.coords_source == "none"
    assert sheet.start_lat is None
    assert sheet.start_lon is None
    assert sheet.end_lat is None
    assert sheet.end_lon is None


def test_extract_vicinity_coords(vicinity_pdf: Path):
    doc, page, text, blocks = _open_first_page(vicinity_pdf)
    coords = extract_vicinity_coords(page, page_number=1, page_type="vicinity", text=text)
    doc.close()

    assert len(coords) == 1
    assert isinstance(coords[0], VicinityCoord)
    assert coords[0].lat == pytest.approx(34.123456, abs=1e-4)
    assert coords[0].lon == pytest.approx(-118.123456, abs=1e-4)
    assert coords[0].page_type == "vicinity"
