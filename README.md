# QMark PDF Cleaner

QMark is a local desktop app for reviewing and removing scan marks from PDF pages. The current version detects the `CamScanner` wordmark. Logo-only marks without readable text are not supported.

## Requirements

- Python 3.12
- Tkinter
- Tesseract OCR installed locally to process scanned/image-only pages

On macOS with Homebrew, install the local runtime components with:

```bash
brew install python-tk@3.12 tesseract
```

## Run

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src
```

## Run automated checks

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Text detection and OCR run on the user's device; the app does not send PDF content to an external service. The source PDF is never overwritten; save the result to a separate path. Removed regions are replaced with a white background, and content hidden beneath the mark is not reconstructed.

## License

This project is licensed under the GNU Affero General Public License v3 (`AGPL-3.0-only`); see [`LICENSE`](LICENSE) for the full text. The project uses PyMuPDF under its AGPL option. If you need to distribute the app under different terms or keep it closed source, replace PyMuPDF with a suitable library or obtain a commercial license from Artifex before distribution. See the [PyMuPDF licensing terms](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright).

## Validation status

All 10 automated checks pass. They cover embedded-text detection with different surrounding wording, full framed-mark removal, per-page keep/remove choices, source and page preservation, OCR coordinate conversion with simulated OCR output, invalid input, and the missing-Tesseract error. Tesseract and representative CamScanner PDFs were not available during implementation, so OCR accuracy on real scans and the 95% detection target have not been verified.

The application source contains no HTTP client or external service calls. PDF processing and OCR use local files and local executables only.
