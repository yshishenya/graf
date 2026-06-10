# Contract: Smoke Evidence

Committed smoke evidence summaries under `docs/deployments/2brain-rec/` MUST be metadata-only.

## Required Fields

- `run_id`
- `date`
- `branch_or_commit`
- `public_endpoint`
- `endpoint_reachability`
- `readiness_verdict`
- `compose_config_result`
- `secret_validation_result`
- `backup_reference`
- `restore_or_rollback_rehearsal_result`
- `migration_version_before`
- `migration_version_after`
- `health_live_result`
- `health_ready_result`
- `smoke_identity_class`
- `smoke_device_class`
- `upload_result`
- `postgres_persistence_result`
- `minio_persistence_result`
- `no_forbidden_side_effects_result`
- `mediascribe_degraded_awareness`
- `langfuse_degraded_awareness`
- `log_redaction_result`
- `cleanup_result`
- `open_risks`

## Forbidden Evidence Content

Evidence MUST NOT include:

- Live secret values.
- Passwords, API keys, bearer tokens, device tokens, signed URLs, cookies, or auth headers.
- Raw audio bytes or raw meeting artifacts.
- Transcript text or meeting content.
- Raw production logs.
- Unredacted object keys if they contain sensitive identifiers.
- MediaScribe or Langfuse credentials.

## Required Side-Effect Assertions

Each successful 021 smoke evidence summary MUST state:

- `mediascribe_jobs_created=0`
- `temporal_workflows_started=0`
- `notes_jobs_created=0`
- `retention_jobs_created=0`
- `deletion_jobs_created=0`
- `content_bearing_langfuse_traces_created=0`

## Cleanup Assertions

Evidence MUST record one of:

- `cleanup_result=pass`
- `cleanup_result=residue_recorded`
- `cleanup_result=blocked`
- `cleanup_result=failed`

When cleanup is not `pass`, evidence MUST include a non-secret owner and follow-up reason.
