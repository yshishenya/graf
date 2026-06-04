# Contract: Deployment Readiness

## Readiness Verdicts

Allowed verdicts for 021:

- `not_ready`: deployment has not passed required gates.
- `blocked`: one or more blocking gates failed or could not be verified.
- `infra_smoke_ready`: production infrastructure passed the 021 first-smoke boundary.

Forbidden verdicts for 021:

- `production_ready`
- `user_rollout_ready`
- `internal_user_pilot_ready`

## Blocking Gates

021 MUST NOT report `infra_smoke_ready` unless all of these are true:

- Production configuration validates with required secrets present.
- Known local/development default secrets are rejected.
- Docker Compose configuration renders for the Rec-owned production stack.
- Rec Postgres and Rec MinIO are dedicated to `2brain_rec`.
- Backup evidence exists before migration.
- Production-like restore/rollback rehearsal passes.
- Migration verification passes.
- Liveness and readiness checks pass for active 012 dependencies.
- Dedicated internal smoke identity/device exists and is not a real user/device.
- Small non-sensitive smoke artifact finalizes at the accepted 012 ingest boundary.
- No MediaScribe jobs, Temporal workflow starts, notes jobs, retention jobs, deletion jobs, or content-bearing Langfuse traces are created.
- Smoke artifacts are cleaned up or truthful residue/follow-up is recorded.
- Evidence and logs pass forbidden-content scan.

## Public Endpoint Rule

`https://rec.2brain.pro` MAY be publicly reachable during first smoke. Public reachability MUST be recorded separately from readiness verdict and MUST NOT be described as user rollout readiness.

## Out-of-Scope Boundary

021 readiness MUST NOT imply readiness for:

- Federated auth or real user login.
- Desktop upload queue.
- MediaScribe processing.
- Temporal processing workflows.
- Meeting dashboard.
- Sharing/downloads.
- Retention/deletion execution.
- macOS driver packaging or release.
