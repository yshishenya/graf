# 2brain Rec Infrastructure Smoke Evidence

Use this template only for the first infrastructure smoke of feature `021`.
It can support the verdict `infra_smoke_ready`; it must not claim production
readiness, user rollout readiness, or internal pilot readiness.

## Metadata

- run_id:
- date:
- branch_or_commit:
- public_endpoint: `https://rec.2brain.pro`
- endpoint_reachability:
- readiness_verdict: `not_ready` | `blocked` | `infra_smoke_ready`

## Gates

- compose_config_result:
- secret_validation_result:
- backup_reference:
- restore_or_rollback_rehearsal_result:
- migration_version_before:
- migration_version_after:
- health_live_result:
- health_ready_result:

## Smoke Identity

- smoke_identity_class: `internal_smoke`
- smoke_device_class: `internal_smoke`
- organization_id_reference:
- workspace_id_reference:
- user_id_reference:
- device_id_reference:

## Ingest Boundary

- upload_result:
- postgres_persistence_result:
- minio_persistence_result:
- no_forbidden_side_effects_result:

Required zero side-effect assertions:

- mediascribe_jobs_created: `0`
- temporal_workflows_started: `0`
- notes_jobs_created: `0`
- retention_jobs_created: `0`
- deletion_jobs_created: `0`
- content_bearing_langfuse_traces_created: `0`

## Degraded Awareness

- mediascribe_degraded_awareness:
- langfuse_degraded_awareness:
- log_redaction_result:

## Cleanup

- cleanup_result:
- database_records_removed:
- object_keys_removed:
- residue_owner:
- residue_follow_up_reason:

## Open Risks

- DNS/TLS:
- external dependency health:
- operator notes:
