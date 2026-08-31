# Research: Legacy retirement program

## Decision 1 — Inventory is metadata-only and exact-SHA bound

**Decision**: Store contour category, relative source path, stable ID, digest, owner, risk and status; never store user rows, audio, transcripts, credentials or raw logs.

**Rationale**: Capture, auth, migration, Temporal and update compatibility surfaces require safe, comparable evidence.

**Alternatives considered**: A full code/data dump was rejected because it leaks sensitive material and is not a stable comparison artifact.

## Decision 2 — Inventory and removal are separate slices

**Decision**: Feature 220 first produces inventory and classification. Each `remove` result becomes its own Spec Kit feature/task with independent tests, cutover and rollback.

**Rationale**: A single mass deletion cannot prove migration, replay, client or rollback safety.

## Decision 3 — Exceptions are finite and fail-closed

**Decision**: `retain-with-exception` requires owner, future expiry, removal trigger, risk, validation and linked retirement issue.

**Rationale**: Compatibility is a temporary contract, not an undocumented permanent fallback.

## Decision 4 — Protected domains get specialized rehearsal

**Decision**: Migrations require isolated backup/restore and expand/contract checks; Temporal requires replay/idempotency evidence; Sparkle requires signing/trust continuity. Production remains out of scope.

## Decision 5 — Current Dev migration drift remains a separate dependency

**Decision**: Existing volume revision `0074_calendar_sync_maintenance` is handled by Feature 221. Feature 220 references it but does not repair, stamp or reset it.
