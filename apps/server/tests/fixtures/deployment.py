from twobrain_rec_server.config import SMOKE_IDENTITY_CLASS
from twobrain_rec_server.deployment import DegradedAwarenessStatus, SmokeEvidenceRecord


def smoke_evidence_payload(**overrides):
    payload = {
        "run_id": "smoke-20260604-0001",
        "date": "2026-06-04",
        "branch_or_commit": "021-production-deployment-plan",
        "public_endpoint": "https://rec.2brain.pro",
        "endpoint_reachability": "public_during_smoke_not_user_rollout_ready",
        "readiness_verdict": "infra_smoke_ready",
        "compose_config_result": "pass",
        "secret_validation_result": "pass",
        "backup_reference": "backup-ref-redacted",
        "restore_or_rollback_rehearsal_result": "pass",
        "migration_version_before": "base",
        "migration_version_after": "head",
        "health_live_result": "pass",
        "health_ready_result": "pass",
        "smoke_identity_class": SMOKE_IDENTITY_CLASS,
        "smoke_device_class": "internal_smoke",
        "upload_result": "pass",
        "postgres_persistence_result": "pass",
        "minio_persistence_result": "pass",
        "no_forbidden_side_effects_result": "pass",
        "mediascribe_degraded_awareness": DegradedAwarenessStatus(
            dependency="mediascribe",
            configured=False,
            health_status="not_configured",
        ),
        "langfuse_degraded_awareness": DegradedAwarenessStatus(
            dependency="langfuse",
            configured=False,
            health_status="not_configured",
        ),
        "log_redaction_result": "pass",
        "cleanup_result": "pass",
        "open_risks": [],
    }
    payload.update(overrides)
    return payload


def smoke_evidence_record(**overrides) -> SmokeEvidenceRecord:
    return SmokeEvidenceRecord(**smoke_evidence_payload(**overrides))
