"""PDF validation, scan-marker detection, preview rendering, and redaction."""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
import os
from pathlib import Path
import re
import tempfile

import fitz


class PDFProcessingError(Exception):
    """An input PDF could not be safely processed."""


class OCRUnavailableError(PDFProcessingError):
    """Local OCR support is unavailable."""


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


def _contains_scan_label(words: list[str]) -> bool:
    text = "".join(words)
    return "scannedwith" in text or "scannedby" in text


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
) -> list[MarkCandidate]:
    ordered = sorted(lines)
    candidates = []
    label_groups = []
    consumed = set()
    for key in ordered:
        if key in consumed:
            continue
        group = [key]
        words = lines[key]
        if not _contains_scan_label([word for word, _ in words]):
            following = (key[0], key[1], key[2] + 1)
            if following in lines and _contains_scan_label(
                [word for word, _ in words + lines[following]]
            ):
                group.append(following)
        if _contains_scan_label(
            [word for group_key in group for word, _ in lines[group_key]]
        ):
            label_groups.append(group)
            consumed.update(group)

    for group in label_groups:
        label_words = [word for key in group for word in lines[key]]
        label_bounds = _union_words(label_words)
        nearby = []
        for context_key in ordered:
            if context_key in group:
                continue
            context_words = lines[context_key]
            context_bounds = _union_words(context_words)
            vertical_gap = max(
                label_bounds.y0 - context_bounds.y1,
                context_bounds.y0 - label_bounds.y1,
                0,
            )
            horizontal_gap = max(
                context_bounds.x0 - label_bounds.x1,
                label_bounds.x0 - context_bounds.x1,
                0,
            )
            if (
                vertical_gap <= max(label_bounds.height * 3, 20)
                and horizontal_gap <= max(label_bounds.height, 12)
            ):
                nearby.append((vertical_gap + horizontal_gap, context_bounds))
        bounds = fitz.Rect(label_bounds)
        if nearby:
            bounds |= min(nearby, key=lambda item: item[0])[1]

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
        bounds = frame or _padded_rect(bounds, page.cropbox.x1, page.cropbox.y1)
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
        tessdata = next(
            (
                str(path)
                for path in (
                    Path("/opt/homebrew/share/tessdata"),
                    Path("/usr/local/share/tessdata"),
                    Path("/usr/share/tessdata"),
                )
                if path.is_dir()
            ),
            None,
        )
        for dpi in (200, 400):
            textpage = page.get_textpage_ocr(
                language="eng", dpi=dpi, full=False, tessdata=tessdata
            )
            candidates = _marker_lines(_pdf_text_lines(page, textpage), page, "ocr")
            if candidates:
                return candidates
    except Exception as exc:
        raise OCRUnavailableError(
            "Local OCR could not read this scanned page. "
            "Install English OCR language data "
            "and make sure the local OCR engine is configured."
        ) from exc
    return []


def _pdf_text_lines(
    page: fitz.Page, textpage: fitz.TextPage | None = None
) -> dict[tuple[int, int, int], list[tuple[str, fitz.Rect]]]:
    lines: dict[tuple[int, int, int], list[tuple[str, fitz.Rect]]] = {}
    for x0, y0, x1, y1, text, block_number, line_number, _ in page.get_text(
        "words", textpage=textpage
    ):
        word = re.sub(r"[^a-z0-9]", "", text.lower())
        if word:
            key = (block_number, 0, line_number)
            lines.setdefault(key, []).append(
                (word, fitz.Rect(x0, y0, x1, y1))
            )
    return lines


def scan_pdf(path: str | Path) -> ProcessingResult:
    """Find scan attribution labels using embedded text and local OCR."""
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
