"""Pytest fixtures: synthetic PDFs generated programmatically with PyMuPDF.

We build small, deterministic PDFs at test time. Each fixture returns a path
to a temporary .pdf the test can read.
"""
from pathlib import Path
from typing import List, Tuple

import fitz
import pytest


def _make_pdf(tmp_path: Path, name: str, pages: List[List[Tuple[float, float, str]]]) -> Path:
    """Create a PDF where `pages[i]` is a list of (x, y, text) entries for page i+1."""
    doc = fitz.open()
    for entries in pages:
        page = doc.new_page(width=1224, height=792)  # 17"x11" landscape
        for x, y, text in entries:
            page.insert_text((x, y), text, fontsize=10)
    out = tmp_path / name
    doc.save(out)
    doc.close()
    return out


@pytest.fixture
def text_only_pdf(tmp_path: Path) -> Path:
    """Single page with a few text strings — no images."""
    return _make_pdf(tmp_path, "text_only.pdf", [[
        (50, 50, "Hello world"),
        (50, 80, "STA 5+00"),
        (50, 110, "Lat: 34.123456 Lon: -118.123456"),
    ]])


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    """Single blank page (no text, no images) — should look raster to detector."""
    return _make_pdf(tmp_path, "empty.pdf", [[]])


@pytest.fixture
def plan_sheet_pdf(tmp_path: Path) -> Path:
    """A page that should classify as PLAN_PROFILE: stations, structures, match line, road."""
    return _make_pdf(tmp_path, "plan_sheet.pdf", [[
        (50, 50, "SITE PLAN - 5"),
        (50, 80, "STA 0+00"),
        (200, 80, "STA 12+50"),
        (50, 110, "POLE 32"),
        (200, 110, "POLE 35"),
        (350, 80, "MATCH TO SHEET 6"),
        (50, 140, "MAIN ST"),
        (250, 140, "260' SPAN"),
        (450, 140, "OVERLASH ON EXISTING STRAND"),
        (50, 170, "LAT: 34.123456 LON: -118.123456"),
    ]])


@pytest.fixture
def cover_sheet_pdf(tmp_path: Path) -> Path:
    """A cover page — should classify as COVER, not PLAN_PROFILE."""
    return _make_pdf(tmp_path, "cover.pdf", [[
        (200, 50, "COVER SHEET"),
        (200, 80, "FIBER OPTIC CONSTRUCTION DRAWINGS"),
        (200, 110, "MASTEC COMMUNICATIONS GROUP"),
        (200, 140, "PROJECT: PERU UTILITIES JB123"),
    ]])


@pytest.fixture
def vicinity_pdf(tmp_path: Path) -> Path:
    """A vicinity/overview map page — should classify as VICINITY, not PLAN_PROFILE."""
    return _make_pdf(tmp_path, "vicinity.pdf", [[
        (200, 50, "VICINITY MAP"),
        (200, 80, "OVERVIEW"),
        (200, 110, "Project Site Reference"),
        (200, 140, "LAT: 34.123456 LON: -118.123456"),
    ]])


@pytest.fixture
def multi_page_pdf(tmp_path: Path) -> Path:
    """Cover + vicinity + 2 plan sheets + legend — typical CD package."""
    return _make_pdf(tmp_path, "multi.pdf", [
        # Page 1: Cover
        [(200, 50, "COVER SHEET"), (200, 80, "FIBER CONSTRUCTION")],
        # Page 2: Vicinity
        [(200, 50, "VICINITY MAP"), (200, 80, "Reference 34.10000, -118.10000")],
        # Page 3: Plan sheet 1
        [(50, 50, "SITE PLAN - 1"), (50, 80, "STA 0+00"), (200, 80, "STA 12+50"),
         (50, 110, "POLE 1"), (200, 110, "POLE 5"), (350, 80, "MATCH TO SHEET 4"),
         (50, 140, "MAIN ST"), (50, 170, "LAT: 34.20000 LON: -118.20000")],
        # Page 4: Plan sheet 2
        [(50, 50, "SITE PLAN - 2"), (50, 80, "STA 12+50"), (200, 80, "STA 25+00"),
         (50, 110, "POLE 6"), (200, 110, "POLE 10"), (350, 80, "MATCH TO SHEET 3"),
         (50, 140, "OAK AVE"), (50, 170, "BORE AND PLACE 2\" CONDUIT")],
        # Page 5: Legend
        [(200, 50, "LEGEND"), (200, 80, "SYMBOLS"), (200, 110, "AERIAL FIBER")],
    ])
