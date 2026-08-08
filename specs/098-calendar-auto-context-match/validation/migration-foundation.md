# Feature 098 Migration And Foundation Evidence

**Recorded**: 2026-07-13 (Europe/Moscow)
**Validation lane**: high-risk active Spec Kit slice
**Tasks**: T005-T016
**Requirement trace**: FR-016, FR-027, FR-029, FR-030, FR-035, FR-036,
FR-038, FR-039, FR-041, FR-049, FR-051, FR-052; SC-005, SC-007,
SC-011, SC-014, SC-015, SC-016

## Result

The Phase 2 persistence, title-provenance, shared-schema, metadata-only audit
and tenant-boundary foundation is ready. There is no unresolved schema,
migration, RLS or contract blocker for the first user story.

The resolve endpoint is intentionally not registered during foundation. The
shared resolve models have direct schema-ownership tests; runtime route
registration, the `Idempotency-Key` operation contract and canonical OpenAPI
projection remain owned by T024. T014 records the create/context canonical
delta and strict runtime drift only, avoiding a circular dependency between
foundation and the T024 route.

The standalone Codex Security scan remains separately deferred by explicit
user instruction. It was not resumed, completed, failed or counted as 098
evidence.

## SQLite Upgrade And Reconciliation

Command:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_calendar_auto_context_migrations.py
```

Result:

```text
4 passed, 1 existing StarletteDeprecationWarning in 1.69s
```

The deterministic fixture begins at `0020_user_scoped_recording_ids` with
four meetings and six historical context rows across three of them:

- one titled meeting with an older active row and a newer already-unlinked
  row;
- one untitled meeting with two already-unlinked rows;
- one untitled meeting with two active rows whose timestamps are identical,
  forcing the stable UUID tie-break;
- one untitled meeting with no legacy context, reserved for the 098-only
  no-context rollback case.

Verified upgrade result:

- 1 titled meeting -> `title_source=legacy_unknown`;
- 3 untitled meetings -> `title_source=generic`;
- 6 legacy context rows -> 3 authoritative rows, with 3 duplicates removed;
- the active row wins over a newer unlinked row;
- the newest all-unlinked row becomes `cleared_by_user`, with a null event FK
  and no matched title projection;
- an exact timestamp tie selects the lexicographically highest UUID;
- 2 retained active rows become `legacy_linked` and receive only safe title
  and event-time snapshots;
- private/provider content is not copied into the new state fields.

Inspector and write-conflict checks prove:

- all required attempt/state/snapshot/provenance columns exist;
- attempt uniqueness on `(workspace_id, owner_user_id, local_recording_id)`;
- hashed idempotency-key uniqueness on
  `(workspace_id, owner_user_id, idempotency_key_sha256)`;
- one context row per `(workspace_id, meeting_id)`;
- one nullable context reference per `match_attempt_id`;
- both attempt cleanup indexes and both context lookup indexes exist;
- duplicate attempt/context writes raise SQLite integrity errors.

## Rollback Boundary

The downgrade test inserts a real 098 attempt plus a `no_context` row whose
event FK is null, then downgrades to 0020.

Verified result:

- `recording_calendar_match_attempts` is removed;
- meeting provenance columns are removed;
- new context columns and constraints are removed;
- `calendar_event_snapshot_id` is restored to `NOT NULL`;
- the legacy context lookup index is restored;
- both 098-only no-context state and the retained legacy cleared state are
  discarded because 0020 cannot represent a context row without an event;
- both representable active legacy rows survive.

This is an intentional, documented lossy rollback boundary. It never
fabricates or silently reattaches an event merely to satisfy the 0020
non-null constraint.

## Disposable PostgreSQL And RLS

The first local invocation was blocked before migration by missing ignored
Docker secret files. Synthetic disposable values were created only under the
ignored `infra/secrets/` path. An initial cached image stopped at migration
0019 and was rejected as evidence. `rec-migrate` was rebuilt from the current
worktree (image SHA
`603c07ce030b748b1422b2a442c6cb03390bc4ff5a76b6def05a3d5294ba0730`) before
the accepted run.

Accepted command:

```sh
infra/scripts/verify-rec-migration.sh --execute
```

Accepted result:

```text
Running upgrade 0019_publish_meeting_registry -> 0020_user_scoped_recording_ids
Running upgrade 0020_user_scoped_recording_ids -> 0021_calendar_auto_context_match
rls_validation_result=pass
environment=postgres_test
destructive_probe_database=disposable
ready_for_production_truth=true
probe_suite=direct_sql_rls_probes
migration_verification_result=pass
```

A second isolated PostgreSQL 17 database proved the exact 0021 catalog state:

```text
revision=0021_calendar_auto_context_match
constraint=uq_calendar_match_attempts_workspace_owner_idempotency
constraint=uq_calendar_match_attempts_workspace_owner_local
constraint=uq_recording_calendar_context_links_match_attempt
constraint=uq_recording_calendar_context_links_workspace_meeting
index=ix_calendar_context_series_start
index=ix_calendar_context_state_updated
index=ix_calendar_match_attempts_owner_expiry
index=ix_calendar_match_attempts_state_evaluated
rls=true,force=true
```

The same disposable database then completed the real PostgreSQL downgrade:

```text
Running downgrade 0021_calendar_auto_context_match -> 0020_user_scoped_recording_ids
revision=0020_user_scoped_recording_ids
attempt_table=absent
context_event_nullable=false
legacy_context_index=1
meeting_provenance_columns=0
```

All test containers, the created PostgreSQL volume/network and all synthetic
secret files were removed after the receipts. No production or user secret
was read, written or changed.

## RLS Inventory And Policy Aggregation

The new attempt table is present in the production and test inventories, in
migration-policy aggregation, in the 031 RLS matrix and in the PostgreSQL
migration policy assertion. The sorted inventory now contains 68 covered
tables.

Command subset:

```sh
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_calendar_rls_contract.py \
  tests/contract/test_rls_table_inventory_contract.py \
  tests/contract/test_rls_policy_matrix_contract.py \
  tests/integration/test_rls_postgres_migrations.py
```

The combined migration/RLS run passed as part of the 136-test checkpoint
below, and the disposable PostgreSQL probe independently returned
`rls_validation_result=pass`.

## Model, Persistence And Contract Reconciliation

Reconciliation against `data-model.md` found and closed these planning gaps:

- attempts now persist only a SHA-256 idempotency-key fingerprint plus a
  normalized request fingerprint; the raw key is not stored;
- a nullable unique context attempt reference enforces one-time consumption
  at the database boundary;
- only active legacy rows become `legacy_linked`; retained unlinked/deleting
  rows map to terminal safe states;
- the undefined partial-index portability claim was corrected to the actual
  unique/composite indexes introduced by 098;
- the existing unlink -> relink path now updates the authoritative row instead
  of violating the one-row constraint;
- meeting title provenance persists and reloads through both in-memory and SQL
  stores, participates in idempotency comparison and is returned without the
  old synthetic `user` fallback;
- manual upload creation supplies `upload_provided`, `file_name_derived` or
  `generic` provenance and remains outside calendar matching;
- matcher audit outcomes/reasons use strict allowlists and only bounded
  count/version/freshness/decision/boolean metadata survives.

T012 shared enums and schemas are strict (`extra=forbid`) and cap visible
candidates at 10 and roster projections at 100. T014 updates the runtime-owned
create/context schemas and keeps exact OpenAPI equality; T024 owns the future
resolve operation projection.

## Combined Foundation Checkpoint

Command:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_calendar_provider_fixtures.py \
  tests/integration/test_calendar_auto_context_migrations.py \
  tests/integration/test_postgres_migrations.py \
  tests/contract/test_calendar_rls_contract.py \
  tests/contract/test_rls_table_inventory_contract.py \
  tests/contract/test_rls_policy_matrix_contract.py \
  tests/integration/test_rls_postgres_migrations.py \
  tests/integration/test_persistent_ingest_storage.py \
  tests/integration/test_ingest_happy_path.py \
  tests/contract/test_calendar_context_contract.py \
  tests/contract/test_calendar_no_secret_content_egress.py \
  tests/contract/test_openapi_contract_drift.py \
  tests/integration/test_calendar_settings_flow.py
```

Result:

```text
136 passed, 1 existing StarletteDeprecationWarning in 51.14s
```

Focused Ruff result:

```text
All checks passed!
```

The warning is dependency deprecation noise from `starlette.testclient`; no
setup, migration, schema, fixture, assertion, RLS or cleanup failure remains.

## Foundation Exit Decision

### Phase 3 Fingerprint Revalidation

Phase 3 added nullable `meetings.create_request_fingerprint_sha256` so a
meeting-create retry remains identical after automatic calendar title
replacement. The PostgreSQL gate was therefore repeated from a fresh image
built from the current worktree:

```text
image=sha256:010e102090a5ddcbe394fe8deca21ce3a06024665daa691e799d0b324609c66b
```

The first invocation stopped before migrations because the ignored synthetic
CSRF fixture was shorter than the production configuration's 32-character
minimum. No database validation ran in that invocation. The fixture was
corrected without reading or copying any real credential, and the accepted
run returned:

```text
Running upgrade 0019_publish_meeting_registry -> 0020_user_scoped_recording_ids
Running upgrade 0020_user_scoped_recording_ids -> 0021_calendar_auto_context_match
rls_validation_result=pass
environment=postgres_test
destructive_probe_database=disposable
ready_for_production_truth=true
probe_suite=direct_sql_rls_probes
migration_verification_result=pass
```

The isolated PostgreSQL catalog then proved:

```text
revision=0021_calendar_auto_context_match
create_request_fingerprint_sha256=present,nullable

Running downgrade 0021_calendar_auto_context_match -> 0020_user_scoped_recording_ids
revision=0020_user_scoped_recording_ids
create_request_fingerprint_sha256=absent

Running upgrade 0020_user_scoped_recording_ids -> 0021_calendar_auto_context_match
revision=0021_calendar_auto_context_match
```

Cleanup receipts were all `clean`: generated containers, PostgreSQL and MinIO
volumes, private network, rebuilt image, and ignored synthetic secret files.
No production or user secret was read, written, or changed.

- Portable SQLite upgrade/reconciliation/downgrade: PASS.
- Disposable PostgreSQL upgrade/catalog/downgrade: PASS.
- PostgreSQL RLS enable + force + direct probes: PASS.
- Meeting/title/context model and migration parity: PASS.
- Ingest persistence/idempotency compatibility: PASS.
- Shared schemas and strict canonical drift: PASS for the foundation-owned
  surface; resolve route projection explicitly assigned to T024.
- Metadata-only audit/forbidden-content contract: PASS.
- Unresolved schema or tenant blocker: none.

Phase 3 may begin from this checkpoint.
