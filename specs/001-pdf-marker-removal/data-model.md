# Data Model: PDF Marker Removal

## Processing Session

- **Purpose**: Represents one in-memory attempt to process a user-selected PDF.
- **Fields**:
  - Source PDF path
  - User authorization confirmation
  - Processing status: selected, detecting, review, saved, cancelled, or failed
  - Destination PDF path, present only after successful save
- **Rules**: The source path and destination path must differ. A cancelled or failed session creates no accepted output. Session data is local and temporary.

## Page Review

- **Purpose**: Holds candidate occurrences of the CamScanner wordmark and the user's decision for one source page.
- **Fields**:
  - Source page number
  - Candidate mark regions, each represented by page-relative bounds and detection source (embedded text or OCR)
  - User decision: remove or keep
- **Rules**: Every candidate is shown for review. A page without a candidate remains unchanged. The user decision is independent for each page.

## Output PDF

- **Purpose**: The separate PDF accepted by the user.
- **Fields**:
  - Destination path
  - Page count and order corresponding to the source
  - Set of page regions removed
- **Rules**: The source remains unchanged. Pages marked keep retain their CamScanner mark. Removed regions may have a blank background; hidden content is not reconstructed.
