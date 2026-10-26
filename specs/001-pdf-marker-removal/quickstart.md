# Quickstart: Validate PDF Marker Removal

This guide describes the end-to-end checks for the local desktop tool.

## Prerequisites

- Python 3.12
- A local OCR engine supported by PyMuPDF for image-only pages
- An authorized text-based PDF and an authorized scanned PDF containing a readable scan attribution label

## Setup and launch

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest
python -m src
```

## Validation scenarios

1. Select a PDF containing the fixed mark on several pages and confirm the app identifies each candidate without network access.
2. Review pages individually; choose remove for one page and keep for another. Save to a new destination.
3. Confirm the source file is unchanged, output page count and order match the source, and only selected regions are blanked.
4. Cancel during review and confirm no output is created.
5. Open a PDF with no supported mark and confirm the app reports no candidate rather than claiming success.
6. Try an unreadable or unsupported PDF and confirm the app reports failure without creating a partial output.

For scanned samples, compare OCR candidate boxes with the visible wordmark and neighboring content. Track detection misses and false matches against a representative authorized sample set before claiming the 95% success target.

Automated checks cover embedded text, redaction, source preservation, per-page keep decisions, and OCR coordinate handling with simulated OCR output. They do not replace validation with a local OCR engine and representative scanned PDFs.
