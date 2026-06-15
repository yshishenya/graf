# Contract: RLS Validation Output

## Purpose

Keep test/disposable RLS probe output and production read-only verification
output truthful and distinct.

## Test/Disposable Probe Output

Required fields:

- `rls_validation_result`: `pass` or `blocked`.
- `environment`: `postgres_test` or `production_like`.
- `live_production_probe`: `not_attempted`.
- `destructive_probe_database`: `disposable` or `explicit_test`.
- `ready_for_production_truth`: `true` only when all required probes pass.

Rules:

- May report that live production was not touched.
- Must not imply live production RLS is disabled or unchanged.
- Must block when `RLS_TEST_DATABASE_URL` points at the live `twobrain_rec`
  service database.

## Production Read-Only Output

Required fields:

- `production_rls_state_result`: `pass` or `blocked`.
- `environment`: `live_production`.
- `live_production_enforcement`: `enabled` only when every covered table is
  enabled and forced.
- `covered_table_count`.
- `failed_table_names` when blocked.

Rules:

- Must not seed rows, mutate rows, or run destructive same/cross-tenant probes.
- Must not output credentials or live secret paths.
