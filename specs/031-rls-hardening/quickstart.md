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
