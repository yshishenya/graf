# US3 Automatic Recovery Receipt

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

**Tasks**: T047-T056

## Outcome

Temporary normalization failures now recover without user or workspace-admin
work. One Temporal cycle has four bounded attempts at 30, 60 and 120 second
failure delays; an exhausted cycle remains durable and resumes automatically
after 15 minutes, 1 hour, 6 hours, 24 hours and then once per day while the
accepted source remains eligible. Permanent objective source failures stop
truthfully instead of retrying forever.

The durable reconciler runs at worker startup and every 60 seconds. It recovers
lost post-commit dispatch, expired activity leases, unpublished attempt objects,
missing ready objects and due cooldown cycles. Activity leases are renewed every
30 seconds, expire after 90 seconds, and are bound to the exact Temporal activity
attempt by a stored SHA-256 owner identity. A late worker or stale heartbeat
cannot overwrite or extend a replacement attempt; its immutable output is
automatically cleaned.

Browser and embedded review surfaces only poll the existing read route. Refresh,
reconnect and two tabs converge on the same meeting, accepted revision, job and
playback status. There is no public retry, reprocess or backfill endpoint and no
repair button.

## Red receipt

The US3 tests were introduced before the recovery implementation and exposed the
missing four-attempt schedule, long-term cooldown persistence, lost-dispatch and
expired-lease reconciliation, safe incident deduplication, late-worker ownership
guard and read-only reconnect behavior. The tests became green only after those
durable paths were implemented; no test expectation was weakened into a manual
repair flow.

## Green receipt

From `apps/server`:

```text
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js

uv run ruff check \
  src/twobrain_rec_server/normalization \
  src/twobrain_rec_server/workflows/playback_normalization_workflow.py \
  src/twobrain_rec_server/workflows/temporal_client.py \
  src/twobrain_rec_server/support/incidents.py \
  tests/unit/test_playback_normalization_retry.py \
  tests/unit/test_playback_normalization_worker.py \
  tests/unit/test_playback_normalization_workflow_identity.py \
  tests/integration/test_playback_normalization_retry.py \
  tests/integration/test_playback_normalization_restart.py \
  tests/integration/test_playback_normalization_incidents.py \
  tests/integration/test_playback_normalization_idempotency.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/contract/test_playback_status_contract.py \
  tests/integration/test_playback_normalization_postgres.py

uv run pytest -q \
  tests/unit/test_playback_normalization_retry.py \
  tests/unit/test_playback_normalization_worker.py \
  tests/unit/test_playback_normalization_workflow_identity.py \
  tests/integration/test_playback_normalization_retry.py \
  tests/integration/test_playback_normalization_restart.py \
  tests/integration/test_playback_normalization_incidents.py \
  tests/integration/test_playback_normalization_idempotency.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/contract/test_playback_status_contract.py
```

Result:

- JavaScript syntax: pass;
- Ruff: all checks passed;
- pytest: `44 passed`;
- exit code: `0`;
- elapsed time: `29.38s`;
- one pre-existing Starlette/httpx test-client deprecation warning.

The focused post-race-hardening subset separately reported `18 passed` before
the full 44-test rerun.

## PostgreSQL concurrency receipt

A unique disposable database was created in the already-running local
PostgreSQL test service, migrated to `head`, exercised, then force-dropped:

```text
RLS_TEST_DATABASE_URL=<disposable-postgresql-url> \
  uv run pytest -q tests/integration/test_playback_normalization_postgres.py
```

Result:

- `5 passed`, exit code `0`, elapsed time `1.75s`;
- two simultaneous due-job pickups produced exactly one claimed durable lease
  and one deterministic reuse result under the real PostgreSQL row lock;
- two simultaneous canonical publishers produced exactly one canonical row and
  one partial-unique-index conflict;
- meeting publication/deletion row locking remained serialized;
- the disposable database was dropped after the run; database residue: `0`.

## Recovery and idempotency receipts

- The exact short and long retry cadence is deterministic, timezone-aware and
  persisted. Each exhausted cycle emits one deduplicated metadata-only incident.
- A real failing attempt leaves the accepted source untouched, removes local and
  object-storage attempt residue, and returns to automatic preparation.
- Lost finalize dispatch is discovered once; duplicate pickup reuses one
  deterministic Temporal workflow identity.
- A worker heartbeat renews only the active tenant job and exact activity owner.
  A stale owner is refused.
- An expired worker is recovered to `retry_wait`; a late completion cannot
  publish and its output is removed.
- A missing ready object demotes the false ready pointer and dispatches automatic
  regeneration from retained accepted source.
- A late duplicate publisher cleans its losing object and returns the existing
  canonical winner.
- Two tabs and reconnect read one durable preparing state. Polling is GET-only
  and stops when preparation is no longer active.
- OpenAPI and rendered HTML contain no retry/reprocess/backfill mutation or
  repair control.

## Requirement receipts

| Requirement | Receipt |
|---|---|
| FR-010 | Refresh, reconnect, duplicate finalize, workflow pickup and publication converge on one durable identity; PostgreSQL grants one lease. |
| FR-011 | Transient reasons persist automatic retry state; permanent objective source reasons persist terminal truth with no retry action. |
| FR-012 | Reason classes separate permanent source, lifecycle and automatic-retry failures. |
| FR-013 | Unpublished, expired, failed and late-attempt objects are hidden and cleaned; only a validated canonical winner is ready. |
| FR-023 | Four-attempt cycles and long-term cooldowns continue from the retained accepted source without re-upload or user/admin action. |
| FR-024 | Retry and reconciliation retain the existing meeting, accepted revision, job and source artifacts. |
| FR-035 | Exact activity-owner leases, row locks, immutable attempt keys and the canonical partial unique index prevent competing active output. |
| FR-040 | Supported valid sources remain on an unbounded-in-time but bounded-per-cycle automatic convergence path; impossible inputs alone may terminate. |

## Success-criteria receipts

- SC-004 and SC-005: duplicate triggers create zero duplicate records and zero
  duplicate active canonical artifacts.
- SC-010: incidents and this receipt contain only synthetic aliases, safe reason
  codes, owner hashes, counts and timing; no media, transcript, object key, URL,
  credential or low-level process output is recorded.
- SC-012: transient failures retry with no source re-upload and no user/admin
  action.
- SC-015: late, partial, failed and missing outputs never project ready.
- SC-016: concurrent pickup and publication converge on one lease and one
  canonical artifact.
- SC-020: automatic recovery exposes no manual repair surface.

## Scope truth

This receipt closes the US3 automatic-recovery checkpoint. Legacy backfill,
the complete impossible-media matrix, deletion/retention races, production
worker/deploy readiness, real Chrome evidence, release and production closeout
remain later tasks. Feature 097 and its separate Codex Security scan were not
touched. No implementation commit was created.
