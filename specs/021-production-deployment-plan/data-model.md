# Data Model: Production Deployment Plan

This model describes operational records and contracts for 021. It does not introduce user-facing product data beyond the internal smoke identity/device required to validate the accepted 012 ingest boundary.

## Deployment Environment

- `environment_name`: stable name for the target runtime, e.g. `production` or `production-like`.
- `public_endpoint`: expected public URL, `https://rec.2brain.dev`.
- `host_boundary`: 2brain-controlled infrastructure boundary.
- `compose_project`: Docker Compose project name for the Rec-owned stack.
- `exposure_state`: `public_during_smoke`, `restricted`, or `blocked`.
- `readiness_verdict`: one of `not_ready`, `blocked`, `infra_smoke_ready`.

Validation rules:

- `readiness_verdict` MUST NOT use `production_ready`, `user_rollout_ready`, or `internal_user_pilot_ready` in 021.
- Public reachability MUST be recorded separately from user rollout readiness.

## Service Layout

- `public_services`: reverse proxy or API surfaces reachable from the public endpoint.
- `private_services`: Rec API internals, Postgres, MinIO, migration/init jobs, and internal networks.
- `persistent_services`: Postgres and MinIO.
- `future_scope_services`: Temporal, MediaScribe processing, dashboard, sharing, retention, deletion, uploader, and auth.

Validation rules:

- Postgres and MinIO MUST be Rec-owned and not shared platform dependencies.
- Internal-only services MUST NOT be exposed as public ports unless explicitly justified in the deployment evidence.

## Secret And Environment Policy

- `secret_name`: canonical secret identifier.
- `purpose`: database password, MinIO root credential, MinIO API credential, smoke token, external dependency credential, or other approved purpose.
- `source`: Docker secret or environment template placeholder.
- `owner`: operator/person/team responsible for provisioning and rotation.
- `rotation_expectation`: initial rotation or documented revisit trigger.
- `failure_behavior`: `fail_closed` for required secrets.

Validation rules:

- Live secret values MUST NOT appear in specs, docs, committed env files, logs, screenshots, or evidence.
- Production validation MUST reject missing values and known local/dev defaults.
- Desktop clients MUST NOT receive MinIO, MediaScribe, or Langfuse credentials.

## Persistent Volume

- `volume_name`: Rec-owned Docker volume or host path label.
- `service`: Postgres or MinIO.
- `data_class`: metadata, raw/ingest object data, temp object data, or backup artifact.
- `backup_policy`: included, excluded, or separately handled.
- `restore_policy`: restore rehearsal requirement and owner.
- `disk_full_behavior`: expected fail-closed/degraded behavior.
- `encryption_expectation`: deployment-supported encryption or documented exception.

Validation rules:

- Volumes used by first smoke MUST have backup/restore expectations before migration or artifact creation.
- Disk-full behavior MUST be represented in rollout halt criteria.

## Migration Runbook

- `migration_version_before`: schema version before migration.
- `migration_version_after`: schema version after migration.
- `backup_reference`: redacted pointer to backup evidence.
- `preflight_result`: `pass`, `blocked`, or `failed`.
- `migration_result`: `pass`, `blocked`, or `failed`.
- `verification_result`: `pass`, `blocked`, or `failed`.
- `rollback_decision`: link/reference to rollback decision record when needed.

Validation rules:

- Backup evidence MUST exist before migration execution.
- Restore/rollback rehearsal MUST pass before `infra_smoke_ready`.

## Smoke Identity And Device

- `identity_class`: `internal_smoke`.
- `organization_id`: non-secret identifier for the smoke organization/workspace boundary.
- `workspace_id`: non-secret identifier for the smoke workspace.
- `user_id`: non-secret smoke actor identifier.
- `device_id`: registered smoke device identifier.
- `credential_source`: Docker secret or operator-provisioned runtime secret.
- `expiry_or_rotation`: expected cleanup/rotation after smoke.

Validation rules:

- The smoke identity/device MUST NOT be a real user/device, desktop uploader credential, or local dev seed.
- Evidence may include non-secret identifiers but MUST NOT include bearer tokens or credential values.

## Smoke Test Record

- `run_id`: unique smoke run identifier.
- `started_at` / `ended_at`: timestamp metadata.
- `endpoint_state`: public endpoint reachability and TLS/DNS result.
- `compose_config_result`: `pass`, `blocked`, or `failed`.
- `secret_validation_result`: `pass`, `blocked`, or `failed`.
- `health_result`: liveness/readiness results.
- `migration_result`: migration verification result.
- `upload_result`: small-artifact ingest result.
- `no_side_effects_result`: confirms no MediaScribe jobs, Temporal starts, notes, retention, deletion, or content traces.
- `log_redaction_result`: forbidden-content scan result.
- `cleanup_result`: smoke cleanup result.
- `readiness_verdict`: final verdict.

Validation rules:

- Successful smoke can only produce `infra_smoke_ready`.
- Smoke records MUST be metadata-only and safe to commit.

## Cleanup Record

- `run_id`: smoke run identifier.
- `meeting_id`: non-secret smoke meeting identifier if safe to record.
- `object_keys`: redacted or templated object-key references.
- `database_cleanup`: `pass`, `blocked`, `failed`, or `residue_recorded`.
- `object_cleanup`: `pass`, `blocked`, `failed`, or `residue_recorded`.
- `residue_owner`: owner for any remaining artifact.
- `follow_up_required`: yes/no plus non-secret reason.

Validation rules:

- Cleanup must pass or record truthful residue/follow-up.
- Raw object contents, raw logs, and credentials MUST NOT be committed.

## Rollback Decision

- `trigger`: health, migration, backup, restore, storage, disk-full, smoke upload, public exposure, log leak, or other documented failure.
- `decision`: `continue`, `halt`, `restore`, `rollback`, or `blocked`.
- `prior_state_reference`: redacted reference to prior version/config/backup.
- `operator`: role or non-sensitive owner identifier.
- `evidence_reference`: link to safe deployment evidence.

Validation rules:

- Rollback/halt decision must be recorded when any blocking gate fails.

## Degraded-Awareness Status

- `dependency`: MediaScribe or Langfuse.
- `configured`: yes/no.
- `health_status`: `healthy`, `degraded`, `unavailable`, or `not_checked`.
- `blocks_ingest_smoke`: always `false` for 021 accepted `012` boundary smoke.
- `egress_created`: must be `false` during 021 smoke.

Validation rules:

- Degraded-awareness checks MUST NOT create MediaScribe jobs, content-bearing Langfuse traces, or content egress.
