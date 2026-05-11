from pathlib import Path

import fitz

from scripts.page_text import TextBlock, get_page_text, get_text_blocks, is_raster_page


def test_get_page_text_returns_concatenated_text(text_only_pdf: Path):
    doc = fitz.open(text_only_pdf)
    text = get_page_text(doc[0])
    assert "Hello world" in text
    assert "STA 5+00" in text
    assert "34.123456" in text
    doc.close()


def test_get_text_blocks_returns_positioned_blocks(text_only_pdf: Path):
    doc = fitz.open(text_only_pdf)
    blocks = get_text_blocks(doc[0])
    assert len(blocks) >= 1
    assert all(isinstance(b, TextBlock) for b in blocks)
    hello = [b for b in blocks if "Hello world" in b.text]
    assert len(hello) == 1
    assert hello[0].x0 < hello[0].x1
    assert hello[0].y0 < hello[0].y1
    doc.close()


def test_is_raster_page_returns_false_for_text_pdf(text_only_pdf: Path):
    doc = fitz.open(text_only_pdf)
    assert is_raster_page(doc[0]) is False
    doc.close()


def test_is_raster_page_returns_true_for_empty_page(empty_pdf: Path):
    doc = fitz.open(empty_pdf)
    assert is_raster_page(doc[0]) is True
    doc.close()
