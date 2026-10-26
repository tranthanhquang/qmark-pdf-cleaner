# Research: PDF Marker Removal

## Decision 1: Use PyMuPDF for PDF operations

- **Decision**: Use PyMuPDF to search embedded text, render pages for review, and redact the target mark region.
- **Rationale**: One dependency covers the core PDF operations needed by the desktop flow. Its official page documentation describes `Page.search_for`, `Page.get_pixmap`, and `Page.apply_redactions`.
- **Alternatives considered**: Separate PDF text, rendering, and editing libraries would add dependencies and integration work. The Python standard library does not provide PDF rendering or redaction.
- **Limit**: Redaction removes content inside a rectangle. On scanned pages, overlapping pixels are blanked rather than reconstructed; OCR boxes can overlap nearby text. Keep per-page review and do not promise restoration of hidden content.
- **License**: PyMuPDF is offered under AGPL or commercial terms. Confirm the applicable terms before distribution.
- **Sources**: [PyMuPDF page operations](https://pymupdf.readthedocs.io/en/latest/page.html#page-search-for), [PyMuPDF redactions](https://pymupdf.readthedocs.io/en/latest/page.html#page-apply-redactions), [PyMuPDF license](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)

## Decision 2: Use local Tesseract OCR only as fallback for image-only pages

- **Decision**: Search embedded PDF text first. For image-only pages, render locally and use Tesseract OCR to find the fixed CamScanner text mark. Do not use OCR to alter the page automatically without review.
- **Rationale**: Tesseract is a local OCR engine and can return recognized text with positions. This avoids sending document content to a service and allows the UI to highlight candidate regions.
- **Alternatives considered**: Supporting text-based PDFs only would exclude scanned pages explicitly in scope. A remote OCR service violates the local-processing requirement. Computer-vision matching for logo-only variants is deferred until representative samples justify it.
- **Limit**: OCR can miss or misplace text, and it cannot determine whether content under a mark is important. Detection accuracy must be measured against representative, authorized sample PDFs.
- **Sources**: [Tesseract command-line usage](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)

## Decision 3: Use a local desktop interface

- **Decision**: Use Tkinter for file selection, affected-page review, per-page remove/keep decisions, and separate output selection.
- **Rationale**: The clarified workflow requires visual review before saving and per-page decisions. A desktop interface aligns with local processing and avoids adding a server.
- **Alternatives considered**: A command-line-only tool cannot provide the required visual preview without another interface or external viewer. A browser interface adds local-server and browser workflow complexity without user value in this scope.

## Decision 4: Blank the marked region; do not attempt inpainting

- **Decision**: Remove the detected mark block, including nearby label text and its frame when detectable, by redacting one region and leaving a plain background. Let the user keep the block on any page where the proposed region is unacceptable.
- **Rationale**: This is the smallest behavior that removes a fixed mark while keeping unaffected page content and avoiding speculative image reconstruction.
- **Alternatives considered**: Background reconstruction/inpainting introduces uncertain visual changes and needs broader image-processing validation. Leaving all marks untouched does not meet the core feature goal.
