# Research: Dev migration repair

**Feature**: 221 — Восстановить воспроизводимое состояние локальной Dev-базы
**Date**: 2026-08-31

## Confirmed observations

- Existing Dev volume reports revision `0074_calendar_sync_maintenance`.
- The code migration graph contains `0074_linked_workspace_proofs` followed by
  `0075_calendar_sync_maintenance`; the current code head is
  `0085_merge_summary_mediascribe`.
- A clean temporary Dev database reaches `0085_merge_summary_mediascribe` with
  `alembic upgrade head` and reports that revision from `alembic current`.
- The existing volume has not been changed during this feature.

## Decision constraints

1. Treat an unknown revision as a boundary failure, not as permission to stamp
   or rewrite the migration pointer.
2. Prove backup and restore on an isolated copy before touching the existing
   volume.
3. Prefer a normal forward migration when the graph and schema prove it is
   compatible. A data transform or graph repair becomes a separate reviewed
   feature.
4. Keep evidence metadata-only: revision identifiers, digests, sizes, command
   results and timestamps; never rows, transcript text or credentials.

## Alternatives considered

| Option | Result | Reason |
|---|---|---|
| `alembic stamp` to the current head | Rejected | Hides unknown schema state and is irreversible without a verified backup. |
| Manually write `alembic_version` | Rejected | Bypasses migration code and cannot prove compatibility. |
| `docker compose down -v` | Rejected | Destructive data loss and no recovery evidence. |
| Forward upgrade on an isolated copy | Preferred default | Reproducible and testable; does not alter the existing volume. |
| New clean Dev database | Rehearsal only | Establishes the expected head but does not repair existing data. |

## Open evidence needed before implementation

- Read-only volume and compose boundary probe.
- Backup/restore digest comparison on an isolated copy.
- Reviewer-signed repair decision naming the exact target and abort conditions.

## Probe implementation boundary

The `dev-existing` probe now uses only an explicitly supplied
`--database-url` or the private `GRAF_DEV_DATABASE_URL` environment variable.
It accepts the repository's local Dev PostgreSQL database/user on loopback
ports `54329` or `54330`; it never reuses `TWOBRAIN_DATABASE_URL`. The adapter
invokes `psql` with one read-only query against `alembic_version` and stores
only the revision, status and stable reason code. Connection failures are
`blocked` metadata, while production-looking or otherwise disallowed
boundaries are rejected before `psql` starts.

The focused governance tests cover the observed drift
`0074_calendar_sync_maintenance`, code head `0085_merge_summary_mediascribe`,
production host rejection, generic-environment non-fallback, and the absence
of application/user-row queries. No live Dev volume was changed by this probe
work.
