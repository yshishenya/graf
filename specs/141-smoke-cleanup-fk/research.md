# Research: Надёжная очистка production smoke-данных

## Decision 1: Use both meeting and media-revision ownership paths

- **Decision**: For child rows that carry `media_revision_id`, cleanup selects
  rows whose `meeting_id` is the smoke meeting or whose `media_revision_id`
  belongs to a media revision of that smoke meeting.
- **Rationale**: The failed deploy proved that meeting-only deletion can leave a
  child row holding a foreign key to a revision. Deleting the child by the
  revision relationship is the smallest root-cause fix and does not require
  changing database constraints.
- **Alternatives considered**:
  - Add `ON DELETE CASCADE`: rejected because it changes production schema and
    deletion semantics for all callers.
  - Delete by workspace/global revision scan: rejected because it weakens the
    smoke identity boundary.
  - Ignore the FK error and continue: rejected because cleanup residue would be
    hidden and the deploy gate would become unsafe.

## Decision 2: Preserve existing transaction and availability guards

- **Decision**: Keep the existing maintenance tenant context, available-table
  detection, single transaction, storage-prefix cleanup and residue check.
- **Rationale**: These are existing safety boundaries; the change only expands
  the precise child-row predicate.
- **Alternatives considered**:
  - Introduce a new cleanup service: rejected as unnecessary abstraction.
  - Add a migration or repair job: rejected because the failure is in smoke
    cleanup logic, not the schema contract.

## Decision 3: Validate through existing disposable Postgres fixtures

- **Decision**: Extend existing smoke cleanup tests with a revision-linked
  dependency scenario and keep the canonical full CI and CD gates.
- **Rationale**: The failure is relational and cannot be proven by unit tests
  alone; the repository already provisions disposable Postgres and MinIO test
  doubles for this path.
- **Alternatives considered**:
  - Test only string ordering: insufficient to prove FK-safe deletion.
  - Probe production data manually: unsafe and not reproducible.
