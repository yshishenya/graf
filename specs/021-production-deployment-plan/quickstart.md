# Quickstart: Production Deployment Plan

This guide defines validation scenarios for 021. It does not perform a real production deployment by itself; it defines the commands and evidence expected from implementation tasks.

## 1. Validate Active Feature

```sh
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

Expected:

- `FEATURE_DIR` points to `specs/021-production-deployment-plan`.
- `FEATURE_SPEC` points to `specs/021-production-deployment-plan/spec.md`.

## 2. Render Production Compose

```sh
docker compose -f infra/docker-compose.yml config
```

Expected:

- Rec API, migration job, Postgres, MinIO, and MinIO init services render.
- Postgres and MinIO use Rec-owned volumes.
- Public exposure is limited to the intended API/reverse-proxy path for `rec.2brain.pro`.
- Internal services are not accidentally exposed publicly.
- App services use Docker secret file paths and placeholder-only credential environment values.
- Temporal and MediaScribe are not required for accepted 012 ingest readiness.

## 3. Validate Fail-Closed Production Secrets

Run production config validation with missing and known development defaults.

Expected:

- Missing required secrets fail before smoke.
- Known development defaults fail.
- MinIO root/admin API credentials fail for the Rec API.
- No live secret values are printed in failure output.

## 4. Run Local Production-Like Stack

Use a production-like local stack or staging host with non-secret dummy values.

Expected:

- Migration job runs explicitly.
- `GET /api/v1/health/live` returns success.
- `GET /api/v1/health/ready` succeeds only when Postgres, MinIO, bucket/init state, and active ingest config are valid.
- Readiness does not require MediaScribe, Langfuse, or Temporal.

## 5. Backup Before Migration

Before a migration that can affect persistent production data, record backup evidence under `docs/deployments/2brain-rec/`.

Expected:

- Backup reference exists before migration execution.
- Backup evidence is metadata-only and contains no live secrets or raw logs.
- Backup scope covers Rec Postgres and Rec MinIO expectations.

## 6. Restore/Rollback Rehearsal

Run a production-like restore or rollback rehearsal before `infra_smoke_ready`.

Expected:

- Rehearsal either passes or records a blocked verdict.
- A failed or skipped rehearsal prevents `infra_smoke_ready`.
- Evidence records the decision without exposing secrets.

## 7. Create Internal Smoke Identity/Device

Provision a dedicated internal smoke identity/device.

Expected:

- Identity class is `internal_smoke`.
- It is not a real user account.
- It is not a desktop uploader credential.
- It is not the local development seed identity.
- Evidence records only non-secret identifiers or class labels.

## 8. First Production Smoke

Upload a small non-sensitive artifact through `https://rec.2brain.pro` or the production-like endpoint.

Expected:

- Smoke uses the internal smoke identity/device.
- Upload strategy remains `server_mediated`.
- Finalize succeeds at `ingested_pending_processing`.
- Postgres stores meeting/session/artifact/audit metadata.
- MinIO stores expected object data.
- No MediaScribe job, Temporal workflow, notes job, retention job, deletion job, or content-bearing Langfuse trace is created.

## 9. Degraded-Awareness Checks

Record MediaScribe and Langfuse configuration/health awareness.

Expected:

- Status is recorded as healthy, degraded, unavailable, or not configured.
- These checks do not block accepted 012 ingest smoke readiness.
- These checks do not create content egress.

## 10. Cleanup Smoke Artifacts

Clean up smoke-created database and object-storage artifacts.

Expected:

- Cleanup passes, or residue is truthfully recorded with owner/follow-up.
- Cleanup evidence is recorded under `docs/deployments/2brain-rec/`.
- No raw artifacts or live credentials are committed.

## 11. Evidence And Verdict

Create a safe evidence summary under `docs/deployments/2brain-rec/`.

Expected:

- Evidence satisfies `contracts/smoke-evidence-contract.md`.
- Forbidden-content scan passes.
- Highest successful verdict is `infra_smoke_ready`.
- Evidence does not use `production_ready`, `user_rollout_ready`, or `internal_user_pilot_ready`.

## 12. Validation Commands

Minimum local validation after implementation tasks:

```sh
infra/scripts/ci-local.sh
```

Expected:

- Tests and lint pass.
- Compose config renders with safe placeholders.
- Secret/content scan finds no live credentials, raw audio, transcript text, signed URLs, or tokens.
