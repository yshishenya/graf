from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.schemas import RetentionRunResponse
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingLifecycleAuditEvent,
    RetentionPolicySnapshot,
)
from twobrain_rec_server.deletion.audit import build_lifecycle_audit_metadata
from twobrain_rec_server.deletion.policy import (
    RETENTION_POLICY_UNSAFE_REASON,
    persist_retention_policy_snapshot,
    retention_policy_allows_actions,
)
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY
from twobrain_rec_server.deletion.service import request_meeting_deletion
from twobrain_rec_server.domain.statuses import (
    DeletionReasonCode,
    DeletionRequestSource,
    DeletionState,
    LifecycleAuditOutcome,
    ProcessingStatus,
    RetentionPolicySource,
    RetentionPolicyState,
)

PROCESSING_BLOCKING_STATES = {
    ProcessingStatus.PENDING_PROCESSING.value,
    ProcessingStatus.STARTING.value,
    ProcessingStatus.WORKFLOW_STARTED.value,
    ProcessingStatus.SUBMITTING.value,
    ProcessingStatus.SUBMITTED.value,
    ProcessingStatus.POLLING.value,
    ProcessingStatus.IMPORTING.value,
}


async def run_retention_scan(
    db: AsyncSession,
    *,
    settings: Settings,
    workspace_id: UUID,
    limit: int = 100,
    dry_run: bool = False,
    storage: object | None = None,
    temporal_client: object | None = None,
) -> RetentionRunResponse:
    snapshot = await persist_retention_policy_snapshot(db, settings, workspace_id=workspace_id)
    if not retention_policy_allows_actions(snapshot):
        await _record_retention_policy_blocked(db, snapshot=snapshot, workspace_id=workspace_id)
        return RetentionRunResponse(
            evaluated=0,
            created_requests=0,
            skipped=0,
            blocked=1,
            policy_snapshot_id=snapshot.id,
        )

    meetings = (
        await db.scalars(
            select(Meeting)
            .where(Meeting.workspace_id == workspace_id)
            .order_by(Meeting.created_at.asc())
            .limit(limit)
        )
    ).all()

    evaluated = 0
    created_requests = 0
    skipped = 0
    blocked = 0
    now = datetime.now(UTC)

    for meeting in meetings:
        evaluated += 1
        skip_reason, outcome = _skip_or_block_reason(meeting, snapshot=snapshot, now=now)
        if skip_reason is not None:
            if outcome == LifecycleAuditOutcome.BLOCKED:
                blocked += 1
            else:
                skipped += 1
            await _record_retention_evaluation(
                db,
                meeting=meeting,
                snapshot=snapshot,
                outcome=outcome,
                safe_reason=skip_reason,
            )
            continue

        if dry_run:
            skipped += 1
            await _record_retention_evaluation(
                db,
                meeting=meeting,
                snapshot=snapshot,
                outcome=LifecycleAuditOutcome.SKIPPED,
                safe_reason="dry_run_eligible",
            )
            continue

        await request_meeting_deletion(
            db,
            meeting=meeting,
            actor_user_id=None,
            device_id=None,
            confirmation_boundary=BOUNDED_DELETE_COPY,
            request_source=DeletionRequestSource.RETENTION_JOB,
            reason_code=DeletionReasonCode.RETENTION_EXPIRED,
            policy_snapshot_id=snapshot.id,
            backup_expiry_days=snapshot.backup_expiry_days,
            storage=storage,
            temporal_client=temporal_client,
        )
        meeting.retention_policy_state = RetentionPolicyState.EXPIRED.value
        created_requests += 1
        await _record_retention_evaluation(
            db,
            meeting=meeting,
            snapshot=snapshot,
            outcome=LifecycleAuditOutcome.ACCEPTED,
            safe_reason=DeletionReasonCode.RETENTION_EXPIRED.value,
        )

    await db.flush()
    return RetentionRunResponse(
        evaluated=evaluated,
        created_requests=created_requests,
        skipped=skipped,
        blocked=blocked,
        policy_snapshot_id=snapshot.id,
    )


def _skip_or_block_reason(
    meeting: Meeting,
    *,
    snapshot: RetentionPolicySnapshot,
    now: datetime,
) -> tuple[str | None, LifecycleAuditOutcome]:
    if (meeting.deletion_state or DeletionState.NONE.value) != DeletionState.NONE.value:
        return "already_deleting_or_deleted", LifecycleAuditOutcome.SKIPPED
    if meeting.processing_status in PROCESSING_BLOCKING_STATES:
        return "processing_active", LifecycleAuditOutcome.SKIPPED
    if meeting.retention_policy_state == RetentionPolicyState.BLOCKED.value:
        return "policy_blocked", LifecycleAuditOutcome.BLOCKED
    if meeting.retention_policy_state == RetentionPolicyState.UNSAFE.value:
        return "policy_unsafe", LifecycleAuditOutcome.BLOCKED

    deadline = _retention_deadline(meeting, snapshot=snapshot)
    if deadline is None:
        return "retention_not_configured", LifecycleAuditOutcome.SKIPPED
    if deadline > now:
        return "retention_window_pending", LifecycleAuditOutcome.SKIPPED
    return None, LifecycleAuditOutcome.ACCEPTED


def _retention_deadline(meeting: Meeting, *, snapshot: RetentionPolicySnapshot) -> datetime | None:
    if meeting.retention_delete_after is not None:
        return _as_utc(meeting.retention_delete_after)
    if meeting.started_at is None or snapshot.meeting_delete_after_days is None:
        return None
    return _as_utc(meeting.started_at) + timedelta(days=snapshot.meeting_delete_after_days)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def _record_retention_policy_blocked(
    db: AsyncSession,
    *,
    snapshot: RetentionPolicySnapshot,
    workspace_id: UUID,
) -> None:
    db.add(
        MeetingLifecycleAuditEvent(
            workspace_id=workspace_id,
            meeting_id=None,
            deletion_request_id=None,
            actor_user_id=None,
            device_id=None,
            event_type="retention_policy_blocked",
            outcome=LifecycleAuditOutcome.BLOCKED.value,
            safe_reason=RETENTION_POLICY_UNSAFE_REASON,
            metadata_json=build_lifecycle_audit_metadata(
                policy_source=RetentionPolicySource(snapshot.policy_source),
                outcome=LifecycleAuditOutcome.BLOCKED,
                safe_reason=RETENTION_POLICY_UNSAFE_REASON,
            ),
            created_at=datetime.now(UTC),
        )
    )
    await db.flush()


async def _record_retention_evaluation(
    db: AsyncSession,
    *,
    meeting: Meeting,
    snapshot: RetentionPolicySnapshot,
    outcome: LifecycleAuditOutcome,
    safe_reason: str,
) -> None:
    db.add(
        MeetingLifecycleAuditEvent(
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            deletion_request_id=None,
            actor_user_id=None,
            device_id=None,
            event_type="retention_evaluated",
            outcome=outcome.value,
            safe_reason=safe_reason,
            metadata_json=build_lifecycle_audit_metadata(
                state=RetentionPolicyState(meeting.retention_policy_state or RetentionPolicyState.NOT_CONFIGURED.value),
                policy_source=RetentionPolicySource(snapshot.policy_source),
                outcome=outcome,
                safe_reason=safe_reason,
                request_source=DeletionRequestSource.RETENTION_JOB,
                reason_code=DeletionReasonCode.RETENTION_EXPIRED,
            ),
            created_at=datetime.now(UTC),
        )
    )
    await db.flush()
