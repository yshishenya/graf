# US6 Lifecycle, Privacy And Operations Receipt

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

**Tasks**: T081-T092

## Outcome

Playback publication and meeting deletion now serialize on the same meeting
lock. Deletion enters its lifecycle state first, cancels open jobs, deduplicates
candidate/canonical/attempt/temp object keys, purges controlled content and
keeps metadata-only job/backfill truth. A late worker that loses the race
cannot publish; any object it uploaded is removed while the attempt remains
truthfully purged.

Whole-meeting retention uses the same deletion path and does not wait for
normalization. Reports distinguish candidate, canonical, normalization job,
attempt temp and backfill metadata without exposing object keys, filenames,
paths or content. Each distinct controlled object is deleted at most once.

Every normalization query now requires an exact request, worker or one of the
two normalization-only maintenance contexts on PostgreSQL. The three new
tables remain force-RLS protected; maintenance can enumerate only bounded
job/backfill metadata and cannot read attempts or perform DML.

Media-worker readiness describes worker capability only. It is `ready` only
when dependency/profile, migration `0022`, MinIO, Temporal queue, private work
directory, free-space and synthetic full-decode/cleanup gates all pass;
individual retrying jobs make the state `degraded`, while a missing core gate
makes it `blocked`. Safe admin metrics contain aggregate state/reason/retry,
backfill progress, cleanup-pending and heartbeat facts only.

Production and development compose keep the media target non-root, read-only,
capability-dropped, `no-new-privileges`, one CPU, one GiB, 128 PIDs and worker
concurrency one. The existing processing worker no longer overrides the image
user to root. Rolling deployment is ordered as migration, API/read model,
media capability/profile proof, worker start, then automatic dispatch. A raw
pre-099 rollback is rejected; only a stopped-dispatch forward fix or
compatibility build retaining the legacy playback guard is allowed.

## RED receipts

- The first deletion-state matrix reported `5 failed`; queued, active,
  uploaded, publishing and retry lifecycle ownership was not yet accounted.
- The added real late-worker/deletion race initially reported `1 failed`
  because the losing attempt became merely cleaned rather than preserving the
  stronger deletion-owned `purged` truth.
- The readiness/rolling suite first stopped with three expected import errors
  for the missing feature ID, capability model and rolling/deployment models.
- After those models were implemented, the focused run reported `64 passed, 1
  failed`; the remaining failure proved that `cd-remote.sh` did not yet declare
  the 099 migration/image/profile/worker/recovery/backfill/Range/cleanup gates.

No expectation was weakened into user/admin conversion, retry, repair or
backfill work.

## Green lifecycle and PostgreSQL receipt

From `apps/server`, with a disposable PostgreSQL 17 container and
`RLS_DESTRUCTIVE_PROBE_DATABASE_CLASS=disposable`:

```text
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_playback_normalization_deletion.py \
  tests/integration/test_meeting_deletion_workflow.py \
  tests/integration/test_retention_policy_execution.py \
  tests/integration/test_retention_deletion_migrations.py \
  tests/contract/test_retention_deletion_contract.py \
  tests/contract/test_deletion_no_secret_leakage.py \
  tests/contract/test_playback_normalization_no_secret_egress.py \
  tests/contract/test_playback_normalization_rls_contract.py \
  tests/integration/test_rls_postgres_policies.py \
  tests/integration/test_rls_postgres_migrations.py \
  tests/integration/test_rls_worker_context.py \
  tests/integration/test_rls_maintenance_context.py \
  tests/integration/test_playback_normalization_readiness.py \
  tests/integration/test_playback_normalization_admin_metrics.py \
  tests/integration/test_compose_hardening.py \
  tests/integration/test_deployment_readiness_gates.py \
  tests/unit/test_deployment_rollback_decisions.py \
  tests/unit/test_playback_normalization_worker.py \
  tests/unit/test_playback_normalization_audit.py
```

Result:

- `144 passed`;
- exit code `0`;
- elapsed time `21.77s`;
- one pre-existing Starlette/httpx deprecation warning;
- real PostgreSQL force-RLS, cross-workspace denial, exact maintenance and
  migration policy checks all executed rather than skipped;
- disposable PostgreSQL container residue: `0`.

The narrower readiness/compose/rolling/admin set independently reported `65
passed`, exit code `0`.

## Static and deployment-contract receipt

```text
ruff check <US6 changed modules and tests>
bash -n infra/scripts/cd-remote.sh
docker compose -f infra/docker-compose.yml config --quiet
docker compose -f infra/docker-compose.dev.yml config --quiet
infra/scripts/cd-remote.sh --dry-run --skip-local-ci \
  --branch codex/099-review-m4a-normalization
git diff --check
```

All checks returned exit code `0`. The dry run lists migration `0022`, API read
model, media image capability, profile contract, worker boundary, automatic
dispatch, and the separate post-deploy automatic retry, legacy inventory,
Range playback and normalization cleanup gates.

The execute path now builds the media target but starts the API/read model
first, verifies migration `0022`, runs the non-root isolated synthetic
capability probe with zero residue, validates the exact profile/validator,
starts the one-CPU/one-GiB worker, then enables its durable reconciler. It keeps
the deeper production scenarios explicitly `required_post_deploy`; T114-T115
must turn those into real pass receipts before feature/release completion.

## Requirement receipts

- **FR-018**: canonical, candidate and unpublished attempt objects are
  controlled meeting content; deletion/retention reports account for each
  lifecycle class and deduplicate object deletion.
- **FR-019**: lifecycle tests include requested, started, completed, failed,
  retried, skipped, backfilled, cancelled and temp-cleaned audit boundaries.
- **FR-020**: contract tests and serialized readiness/admin/report assertions
  exclude raw audio, transcript/summary content, filenames, paths, keys, signed
  URLs, provider payloads, credentials and secret paths.
- **FR-030**: local-preparing/uploaded/cleanup-pending attempt output remains
  hidden and cannot become canonical after deletion begins.
- **FR-036**: the common meeting lock and publication recheck make deletion win
  both the database and late-object race.
- **FR-037**: failure, retry, backfill, cleanup and worker capability remain
  observable through fixed safe states and aggregate counters only.

## Scope truth

- This receipt closes the US6 implementation checkpoint. It is not production
  conversion, browser Range, legacy-drain or user-journey proof; those remain
  T093-T115 gates.
- The full canonical CI gate has not yet run after the final code-affecting
  change; T108 owns that evidence.
- Feature 097 and its standalone Codex Security scan were not opened, resumed,
  failed, completed or written.
- No implementation commit, PR, release, tag, deploy or production mutation was
  performed.
