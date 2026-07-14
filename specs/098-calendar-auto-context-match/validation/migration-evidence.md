# Feature 098 Final Migration Evidence

**Recorded**: 2026-07-13 (Europe/Moscow)
**Validation lane**: high-risk active Spec Kit slice
**Task**: T094
**Requirement trace**: FR-016, FR-027, FR-030, FR-035-FR-036, FR-041,
FR-049, FR-052; SC-005, SC-007, SC-011, SC-015-SC-016

## Result

The final 098 migration gate passes on both portable SQLite migration tests and
a disposable PostgreSQL/RLS stack. Upgrade reaches
`0021_calendar_auto_context_match`, direct SQL RLS probes pass, and both the
probe database and the local Docker stack are removed after validation.

This receipt is local pre-PR evidence only. The script explicitly reports that
no live production probe or live production enforcement inspection occurred;
production migration truth remains owned by the later release/deploy gate.

## SQLite Upgrade/Downgrade And Migration Compatibility

Command:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_calendar_auto_context_migrations.py \
  tests/integration/test_postgres_migrations.py
```

Accepted result:

```text
12 passed, 1 existing StarletteDeprecationWarning in 2.78s
```

The executable fixtures prove:

- the migration declares revision `0021_calendar_auto_context_match` with the
  expected RLS boundary;
- SQLite upgrade deterministically reconciles title provenance and duplicate
  legacy context rows into one authoritative row per meeting;
- the new attempt/context uniqueness and lookup structures are present;
- SQLite downgrade restores the 0020 schema and its non-null legacy event
  boundary without fabricating an event for 098-only no-context rows;
- the clean-database migration chain remains present in the server image and
  accepts a seeded identity request.

The detailed legacy-row counts, catalog constraints and lossy rollback boundary
remain recorded in `validation/migration-foundation.md`; this final rerun did not
change the migration implementation.

The final branch base is
`3b62270c2b6c8e236444d521759b682323aa80bf`. Both the SQLite suite and the
disposable PostgreSQL/RLS gate were repeated after the final legacy-title
backfill hardening, so this receipt covers the migration implementation now in
the working diff.

## Disposable PostgreSQL And RLS Gate

Required command:

```sh
infra/scripts/verify-rec-migration.sh --execute
```

The first invocation stopped before migration because this disposable
worktree had no ignored Docker secret files. A controlled retry with only the
database secret then showed that Compose also validates the additional secrets
mounted by `rec-migrate`; that incomplete stack was removed successfully.

The accepted retry supplied fresh test-only values in a temporary directory
outside the repository for exactly the secrets mounted by `rec-migrate`. No
production/user secret was read, copied or changed. The temporary directory was
deleted after the command.

Accepted migration output:

```text
Running upgrade 0019_publish_meeting_registry -> 0020_user_scoped_recording_ids
Running upgrade 0020_user_scoped_recording_ids -> 0021_calendar_auto_context_match
rls_validation_result=pass
environment=postgres_test
live_production_probe=not_attempted
destructive_probe_database=disposable
live_production_enforcement=not_inspected
ready_for_production_truth=true
probe_suite=direct_sql_rls_probes
migration_verification_result=pass
```

Cleanup receipt:

```text
disposable RLS database cleanup: pass
rec-postgres container removed
twobrain-rec-postgres-data volume removed
twobrain-rec-minio-data volume removed
twobrain-rec-private network removed
temporary test-only secret directory removed
local_disposable_stack_cleanup=pass
```

## Exit Decision

- SQLite upgrade and deterministic reconciliation: PASS.
- SQLite downgrade to 0020 boundary: PASS.
- Clean PostgreSQL upgrade through 0021: PASS.
- Direct disposable PostgreSQL RLS probes: PASS.
- Disposable database and local stack cleanup: PASS.
- Production migration/RLS proof: NOT ATTEMPTED here; retained for release.

No migration, RLS or cleanup blocker remains for PR readiness.
