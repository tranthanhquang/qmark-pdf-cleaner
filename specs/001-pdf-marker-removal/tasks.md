# Tasks: PDF Marker Removal

**Input**: Design documents from `specs/001-pdf-marker-removal/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `quickstart.md`

**Tests**: Automated test tasks are omitted because the specification does not explicitly request TDD. Each story has a manual independent validation criterion; validate against authorized sample PDFs and `quickstart.md`.

## Phase 1: Setup

**Purpose**: Create the minimal application scaffold and record local runtime requirements.

- [x] T001 [P] Create `requirements.txt` with PyMuPDF and pytesseract runtime dependencies and `requirements-dev.txt` with pytest
- [x] T002 [P] Create `README.md` with Python/Tesseract setup, local-only processing, and PyMuPDF license review before distribution
- [x] T003 Create the `src/` application package and launch entry point in `src/__main__.py`

## Phase 2: Foundational

**Purpose**: Establish PDF input/output safety before story work.

- [x] T004 Implement PDF open validation, source/destination path checks, and local temporary-file cleanup in `src/pdf_markers.py`
- [x] T005 Implement a processing result and per-page remove/keep decisions in `src/pdf_markers.py`

**Checkpoint**: The app can open a valid PDF without modifying the source and reject invalid input before creating output.

## Phase 3: User Story 1 - Remove CamScanner Mark (Priority: P1) 🎯 MVP

**Goal**: Find the supported fixed CamScanner mark, let the user choose which pages to clean, and save a separate PDF.

**Independent Test**: Process authorized text-based and scanned sample PDFs; confirm detected pages are reported, a no-mark PDF reports no match, and selected marks are removed in a separate output.

- [x] T006 [P] [US1] Detect the supported CamScanner mark from embedded PDF text and local OCR page coordinates in `src/pdf_markers.py`
- [x] T007 [P] [US1] Collect PDF selection and the user's permission-to-modify confirmation in `src/app.py`
- [x] T008 [US1] Show candidate pages with independent remove/keep choices in `src/app.py`
- [x] T009 [US1] Redact only selected candidate regions and save the accepted result to a separate PDF in `src/pdf_markers.py`
- [x] T010 [US1] Connect mark detection, per-page decisions, and separate output saving in `src/app.py`

**Checkpoint**: A user can process a PDF, choose pages to clean, and receive a separate PDF; no-match input is reported without claiming removal.

## Phase 4: User Story 2 - Review Before Saving (Priority: P2)

**Goal**: Let users visually inspect each candidate and cancel before accepting changes.

**Independent Test**: Open a PDF with a candidate overlapping nearby content, inspect the page preview, choose keep or remove, and cancel another run; confirm cancellation creates no accepted output and leaves the source unchanged.

- [x] T011 [US2] Render source pages and highlight candidate regions in the review UI in `src/app.py`
- [x] T012 [US2] Add page navigation, per-page remove/keep controls, and cancel-before-save flow in `src/app.py`
- [x] T013 [US2] Ensure output generation starts only after the user accepts the reviewed choices in `src/app.py`

**Checkpoint**: Users can inspect candidate placement and reject any or all proposed changes before an output is accepted.

## Phase 5: User Story 3 - Preserve Document Usability (Priority: P3)

**Goal**: Keep page order and count, leave unmarked/retained pages unchanged, and avoid partial output on failure.

**Independent Test**: Compare source and output page count/order and inspect unmarked, retained, and cleaned pages; trigger a processing failure and confirm no partial destination is presented as complete.

- [x] T014 [US3] Copy all source pages in original order and leave pages without selected regions unchanged in `src/pdf_markers.py`
- [x] T015 [US3] Write output to a temporary destination and publish it only after successful completion in `src/pdf_markers.py`
- [x] T016 [US3] Show a clear failure message and remove incomplete temporary output in `src/app.py`

**Checkpoint**: Successful output preserves the document's page sequence, and failed processing leaves the source untouched with no partial accepted output.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate the complete workflow and document measured limits.

- [ ] T017 Run the scenarios in `specs/001-pdf-marker-removal/quickstart.md` and record detection results against authorized representative PDFs in `README.md`
- [x] T018 Confirm processing makes no network requests and verify source PDFs remain unchanged across success, cancel, and failure flows in `README.md`
- [x] T019 Confirm the supported CamScanner mark and PyMuPDF distribution license decision are documented in `README.md`

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: No dependencies; T001 and T002 can run in parallel. T003 creates the entry point after the scaffold decision.
- **Foundational**: Depends on Setup; blocks all user stories.
- **User Stories**: Depend on Foundational and proceed in priority order because review and output safety build on the P1 processing flow.
- **Polish**: Depends on all three user stories.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; delivers the MVP mark-removal flow.
- **US2 (P2)**: Builds on US1 candidate pages and output choices to add visual review and cancellation.
- **US3 (P3)**: Builds on US1 output creation and US2 acceptance flow to guarantee preservation and failure behavior.

### Parallel Opportunities

- T001 and T002 can run in parallel because they create separate files.
- US1 detection in `src/pdf_markers.py` and initial permission/file selection in `src/app.py` can be developed in parallel after T004-T005 if they agree on the processing result shape.
- Tasks within a story that update the same file should remain sequential.

## Implementation Strategy

### MVP First

Complete Setup and Foundational, then US1. Validate detection against authorized text-based and scanned examples before proceeding; the P1 flow must retain marks on pages the user chooses to keep.

### Incremental Delivery

Add US2 visual review and cancellation, then US3 preservation and failure guarantees. Run the quickstart scenarios after all stories are integrated.

## Notes

- Every task uses the required checkbox, sequential ID, applicable parallel/story labels, and a concrete file path.
- No external contracts are required for this local desktop application.
- Do not include user PDFs in the repository; use authorized local samples for manual validation.
- T017 remains unchecked until Tesseract and representative authorized CamScanner PDFs are available for real OCR accuracy validation.
