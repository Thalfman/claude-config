"""Walk a PDF or folder of PDFs and emit PdfResult records."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import fitz

from scripts.page_classifier import PageType, classify_page
from scripts.page_text import get_page_text, get_text_blocks
from scripts.sheet_extractor import SheetData, VicinityCoord, extract_sheet, extract_vicinity_coords


@dataclass
class PdfResult:
    pdf_file: str
    sheets: List[SheetData] = field(default_factory=list)
    vicinity_coords: List[VicinityCoord] = field(default_factory=list)
    raster_pages: List[int] = field(default_factory=list)


_VICINITY_COLLECTING_TYPES = {PageType.COVER, PageType.VICINITY}


def process_pdf(pdf_path: Path) -> PdfResult:
    """Walk every page of one PDF, classify, and extract."""
    pdf_path = Path(pdf_path)
    result = PdfResult(pdf_file=pdf_path.name)

    doc = fitz.open(pdf_path)
    try:
        for i, page in enumerate(doc, start=1):
            text = get_page_text(page)
            blocks = get_text_blocks(page)
            page_type = classify_page(text, blocks)

            if page_type == PageType.RASTER:
                result.raster_pages.append(i)
                continue

            if page_type == PageType.PLAN_PROFILE:
                result.sheets.append(extract_sheet(page, page_number=i, text=text, blocks=blocks))
            elif page_type in _VICINITY_COLLECTING_TYPES:
                result.vicinity_coords.extend(
                    extract_vicinity_coords(page, page_number=i, page_type=page_type.value, text=text)
                )
            # OTHER / LEGEND / NOTES / DETAIL / TRAFFIC_CONTROL: skip silently
    finally:
        doc.close()

    return result


def process_input(input_path: Path) -> List[PdfResult]:
    """Process a single PDF or every PDF under a folder (recursive)."""
    input_path = Path(input_path)
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        return [process_pdf(input_path)]
    if input_path.is_dir():
        results = []
        for pdf in sorted(input_path.rglob("*.pdf")):
            results.append(process_pdf(pdf))
        return results
    raise ValueError(f"Not a PDF or folder: {input_path}")
