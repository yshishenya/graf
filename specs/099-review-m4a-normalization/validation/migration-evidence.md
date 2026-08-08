# Migration, PostgreSQL And RLS Receipt

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

**Task**: T097

## Test gate

The migration, PostgreSQL concurrency and RLS filters ran against one
disposable PostgreSQL 17 database, with the destructive probe class explicitly
set to `disposable`:

```text
tests/integration/test_playback_normalization_migrations.py
tests/integration/test_playback_normalization_postgres.py
tests/integration/test_postgres_migrations.py
tests/integration/test_rls_postgres_migrations.py
tests/integration/test_rls_postgres_policies.py
tests/contract/test_playback_normalization_rls_contract.py
tests/contract/test_rls_policy_matrix_contract.py
tests/contract/test_rls_future_table_contract.py
tests/contract/test_rls_migration_rollback_contract.py
```

Result:

- `42 passed`;
- exit code: `0`;
- elapsed time: `6.33s`;
- one pre-existing Starlette/httpx deprecation warning;
- PostgreSQL container residue: `0`.

## Direct RLS probe

```text
PYTHONPATH=src uv run python scripts/verify_rls_hardening.py
```

Result:

- `rls_validation_result=pass`;
- environment: `postgres_test`;
- destructive probe database: `disposable`;
- probe suite: `direct_sql_rls_probes`;
- `ready_for_production_truth=true` for the disposable probe;
- live production was intentionally not inspected in this local gate.

## Proved boundaries

- SQLite upgrades `0021 -> 0022`, preserves legacy rows as unvalidated,
  enforces one canonical profile artifact and downgrades only the 099 schema.
- PostgreSQL migration `0022` is additive and reversible at the schema boundary.
- The partial unique canonical index allows legacy candidates but only one
  validated active canonical artifact, including concurrent publishers.
- Meeting-row locking serializes publisher and deletion so deletion wins.
- All three normalization tables enable and force RLS.
- Request/worker context requires the exact workspace; cross-workspace read and
  write are denied.
- Only `playback_normalization_inventory` and
  `playback_normalization_dispatch` maintenance operations are accepted, only
  for bounded SELECT on jobs/backfill. Attempts and all DML remain tenant-only.
- Downgrade restores the previous maintenance allowlist and does not claim
  object-storage erasure.
- Migration performs no FFmpeg, MinIO or automatic legacy mutation.

This local receipt does not replace the production migration/RLS check in
T114-T115. Feature 097 was not touched.

## Post-review runtime-role rerun

After introducing the separate trusted maintenance role and raw-rollback role
cleanup, the current disposable PostgreSQL 17 normalization/RLS suite passed
`19/19`. The direct RLS probe returned `pass`; API and media roles could not
spoof legacy maintenance, the maintenance role could perform only its expected
legacy operation boundary, scheduler functions remained media-only, and
temporary runtime-role residue was `0`.

An independent exact `upgrade -> bootstrap -> identity probes -> downgrade ->
raw rollback cleanup` reproduction also left `0` runtime roles and denied a
login using the removed legacy API role. No live-production database was read
or changed.
