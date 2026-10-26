# Implementation Plan: PDF Marker Removal

**Branch**: `001-pdf-marker-removal` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-pdf-marker-removal/spec.md`

## Summary

Build a small desktop tool that processes PDFs entirely on the user's device. It finds readable "CamScanner" wordmark text through embedded text and local OCR for image-only pages, previews affected pages, and lets the user remove or retain the mark page by page. Removal blanks the selected mark region; it does not reconstruct content hidden beneath the mark.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: PyMuPDF for PDF text search, rendering, and redaction; Tesseract OCR for image-only pages; Python Tkinter for the local desktop interface

**Storage**: User-selected source and destination PDF files only; temporary page images stay local and are removed when the session ends

**Testing**: pytest with text-based and scanned PDF fixtures; manually inspect page previews and output PDFs

**Target Platform**: Desktop environments with Python and Tesseract installed; initial implementation should validate macOS, with other platforms considered if setup remains straightforward

**Project Type**: Desktop application

**Performance Goals**: A 20-page representative PDF should become reviewable within 30 seconds on a typical current laptop

**Constraints**: No PDF content leaves the device. Never overwrite the source. Only remove the fixed CamScanner mark. Redaction replaces the marked region and cannot restore background pixels or obscured content. Confirm PyMuPDF licensing terms before distributing the tool.

**Scale/Scope**: One local user processes one PDF at a time; no accounts, server, cloud storage, or arbitrary marker configuration

## Constitution Check

The repository constitution contains template placeholders rather than ratified project principles, so it defines no enforceable gates. This plan follows the feature's explicit constraints: local processing, a separate output file, user review, and narrow CamScanner-only scope.

**Gate**: Pass. No constitution violations identified.

## Project Structure

### Documentation (this feature)

```text
specs/001-pdf-marker-removal/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/       # Not needed: the desktop tool exposes no external interface
```

### Source Code (repository root)

```text
src/
├── app.py            # Desktop workflow and page review
├── pdf_markers.py   # Mark detection and PDF output
└── __main__.py       # Application entry point

tests/
├── fixtures/         # Small synthetic PDFs; no user documents
└── test_pdf_markers.py
```

**Structure Decision**: Use one small Python desktop application with a focused PDF module and a single test directory. There is no existing application structure to preserve.

## Complexity Tracking

No constitution gates or additional architectural layers are required.
