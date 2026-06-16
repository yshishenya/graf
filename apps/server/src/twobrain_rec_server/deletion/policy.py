from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import RetentionPolicySnapshot
from twobrain_rec_server.deletion.audit import build_lifecycle_audit_metadata
from twobrain_rec_server.domain.statuses import LifecycleAuditOutcome, RetentionPolicySource

RETENTION_POLICY_UNSAFE_REASON = "retention_policy_missing_or_unsafe"


def build_retention_policy_snapshot(
    settings: Settings,
    *,
    workspace_id: UUID,
    policy_source: RetentionPolicySource = RetentionPolicySource.DEPLOYMENT_DEFAULT,
) -> RetentionPolicySnapshot:
    unsafe_reason = _unsafe_reason(settings)
    outcome = LifecycleAuditOutcome.BLOCKED if unsafe_reason else LifecycleAuditOutcome.ACCEPTED
    metadata = {
        "policy_source": policy_source,
        "outcome": outcome,
        "safe_reason": unsafe_reason or "policy_active",
    }
    if settings.retention_backup_expiry_days is not None:
        metadata["backup_expiry_days"] = settings.retention_backup_expiry_days
    return RetentionPolicySnapshot(
        workspace_id=workspace_id,
        policy_source=policy_source.value,
        meeting_delete_after_days=settings.retention_meeting_delete_after_days,
        backup_expiry_days=settings.retention_backup_expiry_days,
        local_buffer_expiry_days=settings.retention_local_buffer_expiry_days,
        unsafe_reason=unsafe_reason,
        metadata_json=build_lifecycle_audit_metadata(**metadata),
    )


async def persist_retention_policy_snapshot(
    db: AsyncSession,
    settings: Settings,
    *,
    workspace_id: UUID,
    policy_source: RetentionPolicySource = RetentionPolicySource.DEPLOYMENT_DEFAULT,
) -> RetentionPolicySnapshot:
    snapshot = build_retention_policy_snapshot(
        settings,
        workspace_id=workspace_id,
        policy_source=policy_source,
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


def retention_policy_allows_actions(snapshot: RetentionPolicySnapshot) -> bool:
    return snapshot.unsafe_reason is None and snapshot.meeting_delete_after_days is not None


def _unsafe_reason(settings: Settings) -> str | None:
    if (
        settings.retention_meeting_delete_after_days is None
        or settings.retention_backup_expiry_days is None
        or settings.retention_local_buffer_expiry_days is None
    ):
        return RETENTION_POLICY_UNSAFE_REASON
    return None
