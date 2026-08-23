# Data Model: Upload Status, Processing Visibility, And Upload Date

## Meeting list item

- `started_at`: optional source recording start; preferred meeting date.
- `uploaded_at`: optional server receipt/creation timestamp; used as a display fallback for manual uploads only.
- `recording_display_timezone_offset_minutes`: existing owner display offset.
- `upload`: existing upload session projection with accepted bytes, total bytes, progress percent, and active state.
- `status`: existing review/processing state; remains separate from upload session state.

## Invariants

- `uploaded_at` is read-only projection data sourced from existing `Meeting.created_at`.
- No client-provided date is accepted for this display field.
- `started_at` is never overwritten by `uploaded_at`.
- A percentage is emitted only when accepted bytes and total bytes are valid.
