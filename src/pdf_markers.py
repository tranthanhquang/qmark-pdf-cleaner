"""PDF validation, CamScanner mark detection, preview rendering, and redaction."""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
import os
from pathlib import Path
import re
import tempfile

import fitz


TARGET_MARK = "camscanner"


class PDFProcessingError(Exception):
    """An input PDF could not be safely processed."""


class OCRUnavailableError(PDFProcessingError):
    """Local OCR is required but Tesseract is unavailable."""


@dataclass
class MarkCandidate:
    bounds: tuple[float, float, float, float]
    detection_source: str


@dataclass
class PageReview:
    page_number: int
    candidates: list[MarkCandidate] = field(default_factory=list)
    remove: bool = True


@dataclass
class ProcessingResult:
    source_path: Path
    page_count: int
    pages: list[PageReview]


def _contains_wordmark(words: list[str]) -> bool:
    return bool(re.search(r"(?<![a-z])cam\s*scanner(?![a-z])", " ".join(words)))


def _union_words(words: list[tuple[str, fitz.Rect]]) -> fitz.Rect:
    bounds = fitz.Rect(words[0][1])
    for _, rect in words[1:]:
        bounds |= rect
    return bounds


def _padded_rect(bounds: fitz.Rect, width: float, height: float) -> fitz.Rect:
    pad_x = max(bounds.width * 0.25, bounds.height * 0.5, 4)
    pad_y = max(bounds.height * 0.45, 4)
    return fitz.Rect(
        max(0, bounds.x0 - pad_x),
        max(0, bounds.y0 - pad_y),
        min(width, bounds.x1 + pad_x),
        min(height, bounds.y1 + pad_y),
    )


def _marker_lines(
    lines: dict[tuple[int, int, int], list[tuple[str, fitz.Rect]]],
    page: fitz.Page,
    source: str,
    scale_x: float = 1,
    scale_y: float = 1,
    pixel_size: tuple[int, int] | None = None,
) -> list[MarkCandidate]:
    ordered = sorted(lines)
    candidates = []
    for key in ordered:
        words = lines[key]
        if not _contains_wordmark([word for word, _ in words]):
            continue
        bounds = _union_words(words)
        for context_key in ordered:
            if context_key == key:
                continue
            context_words = lines[context_key]
            context_text = "".join(word for word, _ in context_words)
            context_bounds = _union_words(context_words)
            vertical_gap = bounds.y0 - context_bounds.y1
            horizontal_gap = max(
                context_bounds.x0 - bounds.x1, bounds.x0 - context_bounds.x1, 0
            )
            if (
                context_text in ("scannedwith", "scannedby")
                and 0 <= vertical_gap <= max(bounds.height * 3, 20)
                and horizontal_gap <= max(bounds.height, 12)
            ):
                bounds |= context_bounds

        if pixel_size:
            bounds = _padded_rect(bounds, *pixel_size)
            bounds = fitz.Rect(
                bounds.x0 / scale_x,
                bounds.y0 / scale_y,
                bounds.x1 / scale_x,
                bounds.y1 / scale_y,
            ) * page.derotation_matrix
        else:
            frame = None
            for drawing in page.get_drawings():
                rect = drawing["rect"]
                if (
                    rect.contains(bounds)
                    and rect.width <= bounds.width * 2.5
                    and rect.height <= bounds.height * 3
                    and (frame is None or rect.width * rect.height < frame.width * frame.height)
                ):
                    frame = rect
            bounds = frame or _padded_rect(
                bounds, page.cropbox.x1, page.cropbox.y1
            )
        candidates.append(MarkCandidate(tuple(bounds), source))
    return candidates


def _validated_source(path: str | Path) -> Path:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise PDFProcessingError("Select an existing PDF file.")
    return source


def _open_pdf(path: Path) -> fitz.Document:
    try:
        document = fitz.open(path)
    except Exception as exc:
        raise PDFProcessingError("The file is not a valid PDF or could not be opened.") from exc
    if not document.is_pdf:
        document.close()
        raise PDFProcessingError("The selected file is not a PDF.")
    if document.needs_pass:
        document.close()
        raise PDFProcessingError("Password-protected PDFs are not supported.")
    if document.page_count == 0:
        document.close()
        raise PDFProcessingError("The PDF contains no pages.")
    return document


def _ocr_mark(page: fitz.Page) -> list[MarkCandidate]:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise OCRUnavailableError(
            "This PDF contains scanned pages. Install the local OCR dependencies to process it."
        ) from exc

    try:
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.open(BytesIO(pixmap.tobytes("png")))
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except pytesseract.pytesseract.TesseractNotFoundError as exc:
        raise OCRUnavailableError(
            "Tesseract OCR is required for scanned pages. Install it locally and try again."
        ) from exc
    except Exception as exc:
        raise PDFProcessingError("Local OCR could not read a scanned page.") from exc

    lines: dict[tuple[int, int, int], list[tuple[str, fitz.Rect]]] = {}
    for i, raw_word in enumerate(data.get("text", [])):
        word = re.sub(r"[^a-z0-9]", "", raw_word.lower())
        if not word:
            continue
        try:
            confidence = float(data["conf"][i])
            if confidence < 20:
                continue
            x = float(data["left"][i])
            y = float(data["top"][i])
            width = float(data["width"][i])
            height = float(data["height"][i])
            key = (
                int(data["block_num"][i]),
                int(data["par_num"][i]),
                int(data["line_num"][i]),
            )
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        lines.setdefault(key, []).append((word, fitz.Rect(x, y, x + width, y + height)))

    scale_x = pixmap.width / page.rect.width
    scale_y = pixmap.height / page.rect.height
    return _marker_lines(
        lines,
        page,
        "ocr",
        scale_x=scale_x,
        scale_y=scale_y,
        pixel_size=(pixmap.width, pixmap.height),
    )


def _pdf_text_lines(
    page: fitz.Page,
) -> dict[tuple[int, int, int], list[tuple[str, fitz.Rect]]]:
    lines: dict[tuple[int, int, int], list[tuple[str, fitz.Rect]]] = {}
    for x0, y0, x1, y1, text, block_number, line_number, _ in page.get_text("words"):
        word = re.sub(r"[^a-z0-9]", "", text.lower())
        if word:
            key = (block_number, 0, line_number)
            lines.setdefault(key, []).append(
                (word, fitz.Rect(x0, y0, x1, y1))
            )
    return lines


def scan_pdf(path: str | Path) -> ProcessingResult:
    """Find readable CamScanner wordmark text using embedded text and local OCR."""
    source = _validated_source(path)
    document = _open_pdf(source)
    pages = []
    try:
        for index, page in enumerate(document):
            candidates = _marker_lines(_pdf_text_lines(page), page, "pdf-text")
            if not candidates and page.get_images(full=True):
                candidates = _ocr_mark(page)
            pages.append(PageReview(index + 1, candidates, bool(candidates)))
        return ProcessingResult(source, document.page_count, pages)
    finally:
        document.close()


def render_page_preview(
    result: ProcessingResult, page_number: int, max_size: tuple[int, int] = (850, 950)
) -> bytes:
    """Render one page as PNG bytes with detected mark regions highlighted."""
    if not 1 <= page_number <= result.page_count:
        raise ValueError("Page number is outside the document.")
    document = _open_pdf(result.source_path)
    try:
        page = document[page_number - 1]
        scale = min(max_size[0] / page.rect.width, max_size[1] / page.rect.height, 1.0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        from PIL import Image, ImageDraw

        image = Image.open(BytesIO(pixmap.tobytes("png")))
        draw = ImageDraw.Draw(image)
        review = result.pages[page_number - 1]
        for candidate in review.candidates:
            bounds = fitz.Rect(candidate.bounds) * page.rotation_matrix
            draw.rectangle(
                (
                    bounds.x0 * scale,
                    bounds.y0 * scale,
                    bounds.x1 * scale,
                    bounds.y1 * scale,
                ),
                outline=(230, 30, 30),
                width=3,
            )
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()
    finally:
        document.close()


def _same_file(source: Path, destination: Path) -> bool:
    if source == destination:
        return True
    return destination.exists() and os.path.samefile(source, destination)


def save_cleaned_pdf(result: ProcessingResult, destination: str | Path) -> Path:
    """Save selected page marks to a separate PDF, publishing only a complete file."""
    try:
        source = result.source_path.resolve(strict=True)
        destination = Path(destination).expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise PDFProcessingError("The source or destination path is unavailable.") from exc
    if _same_file(source, destination):
        raise PDFProcessingError("Choose a destination different from the source PDF.")
    if not destination.parent.is_dir():
        raise PDFProcessingError("The destination folder does not exist.")

    document = _open_pdf(source)
    temporary_path = None
    try:
        for review in result.pages:
            if not review.remove:
                continue
            page = document[review.page_number - 1]
            for candidate in review.candidates:
                page.add_redact_annot(fitz.Rect(candidate.bounds), fill=(1, 1, 1))
            if review.candidates:
                page.apply_redactions()

        handle = tempfile.NamedTemporaryFile(
            prefix=".pdf-marker-", suffix=".tmp.pdf", dir=destination.parent, delete=False
        )
        temporary_path = Path(handle.name)
        handle.close()
        document.save(temporary_path, garbage=4, deflate=True)
        os.replace(temporary_path, destination)
        temporary_path = None
        return destination
    except PDFProcessingError:
        raise
    except Exception as exc:
        raise PDFProcessingError("The cleaned PDF could not be completed.") from exc
    finally:
        document.close()
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
