from pathlib import Path

import fitz

from scripts.page_classifier import PageType, classify_page
from scripts.page_text import get_page_text, get_text_blocks


def _classify(pdf_path: Path, page_index: int = 0) -> PageType:
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    text = get_page_text(page)
    blocks = get_text_blocks(page)
    result = classify_page(text, blocks)
    doc.close()
    return result


def test_classify_plan_sheet(plan_sheet_pdf: Path):
    assert _classify(plan_sheet_pdf) == PageType.PLAN_PROFILE


def test_classify_cover_sheet(cover_sheet_pdf: Path):
    assert _classify(cover_sheet_pdf) == PageType.COVER


def test_classify_vicinity_map(vicinity_pdf: Path):
    assert _classify(vicinity_pdf) == PageType.VICINITY


def test_classify_empty_page_is_raster(empty_pdf: Path):
    assert _classify(empty_pdf) == PageType.RASTER


def test_classify_multi_page_pdf(multi_page_pdf: Path):
    assert _classify(multi_page_pdf, 0) == PageType.COVER
    assert _classify(multi_page_pdf, 1) == PageType.VICINITY
    assert _classify(multi_page_pdf, 2) == PageType.PLAN_PROFILE
    assert _classify(multi_page_pdf, 3) == PageType.PLAN_PROFILE
    assert _classify(multi_page_pdf, 4) == PageType.LEGEND
