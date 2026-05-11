"""PyMuPDF wrappers: page text, positioned blocks, raster-page detection."""
from dataclasses import dataclass
from typing import List

import fitz


@dataclass(frozen=True)
class TextBlock:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


def get_page_text(page: fitz.Page) -> str:
    """Return all extractable text on the page, joined with spaces."""
    return page.get_text("text")


def get_text_blocks(page: fitz.Page) -> List[TextBlock]:
    """Return one TextBlock per PyMuPDF block (text-bearing only)."""
    raw_blocks = page.get_text("blocks")
    out: List[TextBlock] = []
    for b in raw_blocks:
        # Tuple shape: (x0, y0, x1, y1, text, block_no, block_type)
        # block_type 0 == text, 1 == image
        if len(b) < 6:
            continue
        x0, y0, x1, y1, text, *_rest = b
        block_type = b[6] if len(b) >= 7 else 0
        if block_type != 0:
            continue
        text_str = (text or "").strip()
        if not text_str:
            continue
        out.append(TextBlock(text=text_str, x0=float(x0), y0=float(y0), x1=float(x1), y1=float(y1)))
    return out


_RASTER_TEXT_THRESHOLD = 30   # chars; below this and the page is functionally raster


def is_raster_page(page: fitz.Page) -> bool:
    """Return True if the page has effectively no extractable text.

    A scanned-image page reports near-zero text from PyMuPDF; that is the
    signal we use rather than inspecting embedded images directly, because
    a hybrid page (image background + sparse text overlay) is still useful.
    """
    text = get_page_text(page).strip()
    return len(text) < _RASTER_TEXT_THRESHOLD
