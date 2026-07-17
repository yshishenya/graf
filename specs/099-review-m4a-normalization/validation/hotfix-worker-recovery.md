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
