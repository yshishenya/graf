# Data Model: Legacy retirement

## Legacy Contour

- `contour_id`: stable `L###` identifier.
- `category`: alias, fallback, flag, dependency, fixture, migration, temporal, update, documentation or other.
- `source_path`: repository-relative path only.
- `source_digest`: SHA-256 of inspected source/metadata.
- `owner`: accountable person/team.
- `risk`: low, medium or high with rationale.
- `classification`: `remove`, `retain-with-exception` or `untouched`.
- `status`: candidate, approved, in-progress, retired or blocked.
- `evidence`: links to tests, issue, PR and exact SHA.

## Legacy Exception

- `contour_id` and affected surface.
- `reason` and compatibility boundary.
- `owner`.
- `expiry`: future ISO date.
- `removal_trigger`.
- `risk` and `validation`.
- `retirement_issue`.

## Retirement Slice

- `slice_id` and linked Feature ID/task.
- Input contour IDs.
- Migration/cutover plan.
- Backup/restore or replay rehearsal.
- Rollback target and abort conditions.
- Validation evidence and release gate.

## Inventory Snapshot

- `schema_version`.
- `source_sha`.
- `generated_at`.
- Sorted contour records.
- Aggregate counts by category/classification/status.
- `snapshot_digest`.

All fields are metadata-only. User content is not an allowed field.
