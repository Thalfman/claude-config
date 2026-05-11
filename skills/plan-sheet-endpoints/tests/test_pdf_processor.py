from pathlib import Path

import fitz

from scripts.pdf_processor import PdfResult, process_input, process_pdf


def test_process_pdf_classifies_each_page(multi_page_pdf: Path):
    result = process_pdf(multi_page_pdf)
    assert isinstance(result, PdfResult)
    assert result.pdf_file == multi_page_pdf.name

    # Two plan sheets (pages 3 and 4)
    assert len(result.sheets) == 2
    assert {s.page_number for s in result.sheets} == {3, 4}

    # One vicinity coord (page 2)
    assert len(result.vicinity_coords) == 1
    assert result.vicinity_coords[0].page_number == 2

    # No raster pages in this fixture
    assert result.raster_pages == []


def test_process_pdf_flags_raster_pages(tmp_path: Path):
    doc = fitz.open()
    doc.new_page(width=1224, height=792)  # blank page → raster
    out = tmp_path / "raster.pdf"
    doc.save(out)
    doc.close()

    result = process_pdf(out)
    assert result.raster_pages == [1]
    assert result.sheets == []


def test_process_input_single_pdf(multi_page_pdf: Path):
    results = process_input(multi_page_pdf)
    assert len(results) == 1
    assert results[0].pdf_file == multi_page_pdf.name


def test_process_input_folder(multi_page_pdf: Path, plan_sheet_pdf: Path, tmp_path: Path):
    folder = tmp_path / "pdfs"
    folder.mkdir()
    (folder / "a.pdf").write_bytes(multi_page_pdf.read_bytes())
    (folder / "b.pdf").write_bytes(plan_sheet_pdf.read_bytes())

    results = process_input(folder)
    assert len(results) == 2
    files = sorted(r.pdf_file for r in results)
    assert files == ["a.pdf", "b.pdf"]
