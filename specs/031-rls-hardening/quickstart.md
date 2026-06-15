# Quickstart: Backend Tenant Isolation RLS Hardening

This guide defines the validation expected from the implementation. Commands
that reference new tests or scripts become runnable after the implementation
tasks create them.

## Prerequisites

- Python/uv environment for `apps/server`.
- Docker available for Compose checks.
- PostgreSQL test database URL for RLS proof, exported as
  `RLS_TEST_DATABASE_URL`.
- No live production enforcement unless a separate explicit operator decision
  authorizes it.

## 1. Local Regression

```sh
./infra/scripts/ci-local.sh
```

Expected result:

- Existing server tests pass.
- Ruff passes.
- Python compile passes.
- Production Compose config renders.
- Deployment evidence scan passes.

## 2. API Access Outcome Tests

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_rls_access_outcomes.py \
  tests/integration/test_rls_application_boundaries.py
```

Expected result:

- Cross-tenant reads return not found or empty.
- Cross-tenant writes/deletes return authorization failure.
- Missing tenant context returns auth/context failure.
- Same-tenant ingest/auth/processing paths still pass.

## 3. PostgreSQL RLS Migration And Probe Tests

```sh
cd apps/server
RLS_TEST_DATABASE_URL="$RLS_TEST_DATABASE_URL" \
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_rls_postgres_policies.py
```

Expected result:

- Alembic upgrade reaches head on PostgreSQL.
- Every covered tenant-owned table is classified.
- Missing-context probes deny or return no rows.
- Cross-tenant read probes expose no foreign rows.
- Cross-tenant write/delete probes are denied.
- Worker and maintenance context probes match the contracts.

## 4. Migration Rollback Or Halt Evidence

```sh
cd apps/server
RLS_TEST_DATABASE_URL="$RLS_TEST_DATABASE_URL" \
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_rls_rollout_gates.py
```

Expected result:

- Local and production-like gate evidence has pass/blocked verdicts.
- Enforcement is blocked when any required probe fails.
- Live production enforcement decision is recorded as explicit and separate.
- Rollback/halt instructions are available for failed gates.

## 5. Metadata-Only Evidence Scan

```sh
rg -n "transcript_text|signed_url|secret|password|api_key|/Users/|/opt/projects" \
  specs/031-rls-hardening apps/server/tests apps/server/src || true
```

Expected result:

- No raw transcript text, raw audio, credentials, signed URLs, passwords, live
  secret paths, or customer meeting content in specs, tests, logs, or evidence.
- Any matches are reviewed and either removed or proven to be safe placeholder
  names.

## 6. Out-Of-Scope Boundary Check

```sh
rg -n "dashboard|share|download|retention|deletion|billing|admin UI|desktop capture|MediaScribe direct" \
  apps/server/src apps/server/tests specs/031-rls-hardening || true
```

Expected result:

- No new dashboard detail, share/download, retention, deletion execution,
  billing, admin UI, desktop capture/upload behavior, or MediaScribe behavior
  is introduced by this slice.
- Documentation may mention these areas only as out of scope or future
  protected surfaces.

## 7. Production-Like Validation Boundary

Production-like validation may use the deployment/migration tooling to verify
readiness, but it must not enable live production enforcement by itself.

```sh
./infra/scripts/verify-rec-migration.sh
```

Expected result without explicit remote execution:

- The script reports `migration_verification_result=blocked` and
  `reason=remote_execution_required`.
- Live production enforcement remains untouched.

If a later explicit operator decision authorizes remote validation, run that
decision in its own documented step and capture metadata-only evidence.

## 8. RLS-Only Scope Evidence

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_rls_out_of_scope_boundaries.py \
  tests/contract/test_rls_future_table_contract.py \
  tests/contract/test_rls_openapi_scope.py
```

Expected result:

- Future dashboard, share, download, retention, deletion, billing, admin UI,
  desktop capture/upload, and direct MediaScribe routes remain absent.
- Future tenant-owned tables must follow ADR `003-tenant-isolation-rls`.
  `016`, `017`, and `018` must reuse the RLS contract before adding product
  surfaces.

## 9. Validation Results

Recorded on 2026-06-15 in local branch `031-rls-hardening`.

```text
RLS focused suite:
66 passed, 4 skipped

Post-review remediation focused set:
29 passed

PostgreSQL policy suite without RLS_TEST_DATABASE_URL:
4 skipped

PostgreSQL policy suite with disposable local RLS_TEST_DATABASE_URL:
4 passed

RLS validation helper with disposable local RLS_TEST_DATABASE_URL:
rls_validation_result=pass
ready_for_operator_decision=true
probe_suite=direct_sql_rls_probes
```

Command:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_rls_tenant_context.py \
  tests/contract/test_rls_policy_matrix_contract.py \
  tests/contract/test_rls_evidence_contract.py \
  tests/contract/test_rls_access_outcomes.py \
  tests/contract/test_rls_auth_access_outcomes.py \
  tests/contract/test_rls_migration_rollback_contract.py \
  tests/contract/test_rls_production_boundary.py \
  tests/contract/test_rls_out_of_scope_boundaries.py \
  tests/contract/test_rls_future_table_contract.py \
  tests/contract/test_rls_openapi_scope.py \
  tests/integration/test_rls_auth_conflict_handling.py \
  tests/integration/test_rls_postgres_migrations.py \
  tests/integration/test_rls_postgres_policies.py \
  tests/integration/test_rls_meeting_content_policies.py \
  tests/integration/test_rls_application_boundaries.py \
  tests/integration/test_rls_worker_context.py \
  tests/integration/test_rls_maintenance_context.py \
  tests/integration/test_rls_smoke_cleanup_context.py \
  tests/integration/test_rls_identity_policies.py \
  tests/integration/test_rls_stale_session_device_context.py \
  tests/integration/test_rls_rollout_gates.py
```

```text
Full local CI:
314 passed, 4 skipped
Ruff: All checks passed
Python compile: pass
RLS validation boundary: blocked because RLS_TEST_DATABASE_URL is not set
Compose config: pass
Deployment evidence scan: pass
ci_local_result=pass
```

Command:

```sh
./infra/scripts/ci-local.sh
```

The RLS validation helper intentionally reports:

```text
rls_validation_result=blocked
environment=postgres_test
live_production_enforcement=not_changed
reason=postgres_test_database_required
```

This is acceptable for local CI because PostgreSQL RLS proof requires an
explicit `RLS_TEST_DATABASE_URL`. It is not a live-production enforcement
claim.

Post-review remediation status:

- `infra/scripts/verify-rec-migration.sh --execute` now blocks when RLS
  validation does not return `rls_validation_result=pass`.
- Auth session lookup now requires the explicit `auth_session_lookup` context
  and is not part of the maintenance operation allowlist.
- Worker activity payloads without complete tenant scope now fail closed before
  tenant-owned database operations.
- Maintenance context now requires operation, actor, reason, and feature
  metadata in Python helpers and SQL policy.
- Real PostgreSQL policy probes run through a non-owner probe role so PostgreSQL
  RLS is enforced rather than bypassed by a database owner or superuser.
- On 2026-06-15, the PostgreSQL policy suite passed against a disposable local
  PostgreSQL database with `4 passed`.
- On 2026-06-15, `apps/server/scripts/verify_rls_hardening.py` returned
  `rls_validation_result=pass`, `ready_for_operator_decision=true`, and
  `probe_suite=direct_sql_rls_probes` against a disposable local PostgreSQL
  database.
- Production `infra/scripts/verify-rec-migration.sh --execute` creates and
  cleans up a disposable `twobrain_rec_rls_*` PostgreSQL database when
  `RLS_TEST_DATABASE_URL` is not explicitly provided, so direct probes do not
  seed the live production database.
- Live production enforcement is still not changed by this local proof.

Secret/content scan review:

- Matches were reviewed as requirement prohibitions, test placeholders,
  development-only fixture values, or redaction/negative tests.
- No live credential, customer meeting content, raw audio, transcript evidence,
  signed dependency URL, or live secret path was added by this slice.

Out-of-scope scan review:

- Matches were reviewed as spec exclusions, existing placeholder contracts, or
  tests proving future routes remain absent.
- The RLS OpenAPI and route boundary tests passed with `6 passed`.
