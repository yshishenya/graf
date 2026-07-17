# Worker-Interrupted Startup Recovery — Focused Evidence

**Date**: 2026-07-17
**Scope**: T117–T119 / FR-043 / SC-023
**Safety rule**: evidence contains only synthetic aliases, durable states and
test counts; no private meeting, media, transcript, object, URL or credential.

## Change boundary

- The worker's initial reconciliation can select a future-dated `retry_wait`
  job only when its durable reason is `worker_interrupted`.
- It reuses the existing retry transition, audit event, lease and Temporal
  dispatch path. The record and job identity remain unchanged.
- Periodic reconciliation and every other retry reason retain the scheduled
  backoff. There is no user/admin repair control, schema change or native-app
  change.

## Focused regression

```text
uv run --extra dev pytest tests/integration/test_playback_normalization_restart.py -q
7 passed, 1 warning
```

The new synthetic regression creates two future-dated retry-wait jobs. Startup
reconciliation dispatches exactly the `worker_interrupted` job, clears its
retry reason/due time and resets a completed retry cycle through the existing
transition. The `storage_unavailable` job remains `retry_wait` at its original
scheduled time. One Temporal start is recorded; no replacement record or job is
created.

## Related regression and static checks

```text
uv run --extra dev pytest \
  tests/integration/test_playback_normalization_retry.py \
  tests/integration/test_playback_normalization_audit_persistence.py \
  tests/integration/test_playback_normalization_restart.py -q
12 passed, 1 warning

uv run --extra dev ruff check \
  src/twobrain_rec_server/normalization/service.py \
  src/twobrain_rec_server/normalization/pickup.py \
  src/twobrain_rec_server/normalization/worker.py \
  tests/integration/test_playback_normalization_restart.py
All checks passed
```

The warning is the existing third-party TestClient deprecation warning; it does
not affect the results above. Canonical local CI and production recovery proof
remain T120.

## Canonical local gate

```text
infra/scripts/ci-local.sh
ci_local_result=pass
```

The canonical gate completed the macOS build and test suite (`664` passed), the
server suite (`1759` passed, `28` environment-gated skips), server lint, Python
compile, production compose configuration and deployment-evidence scan. Its
RLS helper truthfully reported that a destructive PostgreSQL probe was not
provided; this is an expected local-environment limitation, not a claim about
live enforcement. The gate itself completed successfully and did not modify
production. Release/deploy and the real automatic-recovery proof remain T120.

## Follow-up: active-attempt cleanup race

Production observation showed that the cleanup pass could select an attempt
still owned by a worker. T121–T122 add the narrow lease predicate to both
selector implementations and a migration for PostgreSQL. The focused SQLite
restart suite passes `8` tests; the PostgreSQL regression is environment-gated
locally and will be exercised by canonical CI/deploy. T123 owns release and
production convergence proof. Evidence uses only states, lease facts and test
counts.

## Active-cleanup validation

```text
uv run --extra dev pytest tests/integration/test_playback_normalization_restart.py -q
8 passed, 1 warning

uv run --extra dev pytest tests/integration/test_playback_normalization_postgres.py -k cleanup -q
1 skipped, 12 deselected, 1 warning

infra/scripts/ci-local.sh
ci_local_result=pass
```

The PostgreSQL case is intentionally skipped locally because no disposable
PostgreSQL URL is configured. The same migration is included in the canonical
CI and production deployment gates. Ruff and `git diff --check` pass. The
warning is the pre-existing third-party TestClient deprecation warning.

## Correction before release

The first canonical run rejected the migration's 38-character internal revision
ID and correctly exposed two outdated schema-head test expectations. T124
shortens the ID to `0026_active_cleanup` and updates those exact tests. The
earlier `ci_local_result=pass` claim above applies to the prior startup-recovery
hotfix only; cleanup-hotfix release/deploy remains blocked until the corrected
canonical gate passes.

## Corrected canonical gate

```text
infra/scripts/ci-local.sh
ci_local_result=pass
server: 1761 passed, 28 skipped, 1 warning
macOS: 664 passed
```

The 32-character revision `0026_active_cleanup` passes the migration-ID guard
and exact worker schema-head tests. The warning remains the third-party
TestClient deprecation notice. T123 remains the production deployment and
canonical-ready proof gate.
