from io import BytesIO

import fitz
from PIL import Image
import pytesseract
import pytest

from src.pdf_markers import (
    OCRUnavailableError,
    PDFProcessingError,
    scan_pdf,
    save_cleaned_pdf,
)


def make_text_pdf(path):
    document = fitz.open()
    marked = document.new_page(width=300, height=400)
    marked.insert_text((30, 80), "Report content")
    marked.insert_text((30, 370), "Scanned by CamScanner")
    unmarked = document.new_page(width=300, height=400)
    unmarked.insert_text((30, 80), "Unmarked page")
    document.save(path)
    document.close()


def test_scan_and_save_selected_mark_preserves_source_and_pages(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "cleaned.pdf"
    make_text_pdf(source)
    original = source.read_bytes()

    result = scan_pdf(source)
    assert result.page_count == 2
    assert len(result.pages[0].candidates) == 1
    assert not result.pages[1].candidates

    save_cleaned_pdf(result, destination)

    assert source.read_bytes() == original
    cleaned = fitz.open(destination)
    assert cleaned.page_count == 2
    assert "Scanned by CamScanner" not in cleaned[0].get_text()
    assert "Report content" in cleaned[0].get_text()
    assert "Unmarked page" in cleaned[1].get_text()
    cleaned.close()


def test_keep_choice_retains_mark(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "copy.pdf"
    make_text_pdf(source)
    result = scan_pdf(source)
    result.pages[0].remove = False

    save_cleaned_pdf(result, destination)

    cleaned = fitz.open(destination)
    assert "Scanned by CamScanner" in cleaned[0].get_text()
    cleaned.close()


def test_text_detection_accepts_other_cam_scanner_wording(tmp_path):
    source = tmp_path / "variant.pdf"
    document = fitz.open()
    document.new_page().insert_text((30, 80), "Scanned with CamScanner")
    document.save(source)
    document.close()

    result = scan_pdf(source)

    assert len(result.pages[0].candidates) == 1


def test_removal_covers_surrounding_marker_block(tmp_path):
    source = tmp_path / "block.pdf"
    destination = tmp_path / "cleaned-block.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    frame = fitz.Rect(40, 40, 200, 105)
    page.draw_rect(frame, color=(0.4, 0.4, 0.4), dashes=".[3 2]")
    page.insert_text((60, 65), "Scanned with")
    page.insert_text((60, 90), "CamScanner")
    document.save(source)
    document.close()

    result = scan_pdf(source)
    assert result.pages[0].candidates[0].bounds == tuple(frame)
    save_cleaned_pdf(result, destination)

    cleaned = fitz.open(destination)
    assert "Scanned with" not in cleaned[0].get_text()
    assert "CamScanner" not in cleaned[0].get_text()
    cleaned.close()


def test_source_cannot_be_destination(tmp_path):
    source = tmp_path / "source.pdf"
    make_text_pdf(source)
    result = scan_pdf(source)
    original = source.read_bytes()

    with pytest.raises(PDFProcessingError, match="different from the source"):
        save_cleaned_pdf(result, source)

    assert source.read_bytes() == original


def test_failed_save_does_not_publish_partial_output(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "cleaned.pdf"
    make_text_pdf(source)
    result = scan_pdf(source)
    original = source.read_bytes()

    def fail_save(*args, **kwargs):
        raise RuntimeError("simulated write failure")

    monkeypatch.setattr(fitz.Document, "save", fail_save)
    with pytest.raises(PDFProcessingError, match="could not be completed"):
        save_cleaned_pdf(result, destination)

    assert source.read_bytes() == original
    assert not destination.exists()
    assert list(tmp_path.glob(".pdf-marker-*.tmp.pdf")) == []


def test_no_mark_is_reported_without_candidates(tmp_path):
    source = tmp_path / "unmarked.pdf"
    document = fitz.open()
    document.new_page().insert_text((30, 80), "No target here")
    document.save(source)
    document.close()

    result = scan_pdf(source)

    assert result.page_count == 1
    assert not result.pages[0].candidates


def test_non_pdf_file_is_rejected(tmp_path):
    source = tmp_path / "not-a-pdf.pdf"
    source.write_text("not a PDF")

    with pytest.raises(PDFProcessingError, match="not a valid PDF"):
        scan_pdf(source)


def test_ocr_finds_fixed_mark_and_maps_coordinates(tmp_path, monkeypatch):
    image_bytes = BytesIO()
    Image.new("RGB", (600, 800), "white").save(image_bytes, format="PNG")
    source = tmp_path / "scan.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=400)
    page.insert_image(page.rect, stream=image_bytes.getvalue())
    document.save(source)
    document.close()

    monkeypatch.setattr(
        pytesseract,
        "image_to_data",
        lambda *args, **kwargs: {
            "text": ["Scanned", "with", "CamScanner"],
            "conf": ["90", "92", "93"],
            "left": [20, 90, 120],
            "top": [650, 650, 700],
            "width": [65, 25, 100],
            "height": [18, 18, 18],
            "block_num": [1, 1, 1],
            "par_num": [1, 1, 1],
            "line_num": [1, 1, 2],
        },
    )

    result = scan_pdf(source)

    assert len(result.pages[0].candidates) == 1
    assert result.pages[0].candidates[0].detection_source == "ocr"
    assert result.pages[0].candidates[0].bounds == pytest.approx(
        (0.0, 309.7, 135.0, 374.3)
    )


def test_scanned_pdf_reports_missing_tesseract(tmp_path, monkeypatch):
    image_bytes = BytesIO()
    Image.new("RGB", (100, 100), "white").save(image_bytes, format="PNG")
    source = tmp_path / "scan.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_image(page.rect, stream=image_bytes.getvalue())
    document.save(source)
    document.close()

    def no_tesseract(*args, **kwargs):
        raise pytesseract.pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(pytesseract, "image_to_data", no_tesseract)

    with pytest.raises(OCRUnavailableError, match="Install it locally"):
        scan_pdf(source)
