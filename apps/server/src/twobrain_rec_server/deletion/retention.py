from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.schemas import RetentionRunResponse
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingLifecycleAuditEvent,
    RetentionPolicySnapshot,
)
from twobrain_rec_server.deletion.audit import build_lifecycle_audit_metadata
from twobrain_rec_server.deletion.local_purge import reconcile_expired_local_purge_tasks
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
    LifecycleAuditOutcome,
    ProcessingStatus,
    RetentionPolicySource,
    RetentionPolicyState,
)
from twobrain_rec_server.processing.fences import meeting_is_deleted_or_deleting

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

    await reconcile_expired_local_purge_tasks(db, workspace_id=workspace_id, limit=max(limit * 10, 100))
    now = datetime.now(UTC)
    # Prioritize due, safe meetings so a permanent prefix of active or
    # unconfigured rows cannot starve newer eligible data. Fill any remaining
    # evaluation budget with the oldest rows for the usual audit projection.
    eligible_filter = and_(
        Meeting.workspace_id == workspace_id,
        Meeting.deleted_at.is_(None),
        or_(Meeting.deletion_state.is_(None), Meeting.deletion_state == "none"),
        or_(
            Meeting.processing_status.is_(None),
            ~Meeting.processing_status.in_(PROCESSING_BLOCKING_STATES),
        ),
        or_(
            Meeting.retention_policy_state.is_(None),
            ~Meeting.retention_policy_state.in_(
                {
                    RetentionPolicyState.BLOCKED.value,
                    RetentionPolicyState.UNSAFE.value,
                }
            ),
        ),
        or_(
            and_(
                Meeting.retention_delete_after.is_not(None),
                Meeting.retention_delete_after <= now,
            ),
            and_(
                Meeting.retention_delete_after.is_(None),
                Meeting.started_at.is_not(None),
                snapshot.meeting_delete_after_days is not None,
                Meeting.started_at <= now - timedelta(days=snapshot.meeting_delete_after_days or 0),
            ),
        ),
    )
    eligible_meetings = list(
        (
            await db.scalars(
                select(Meeting)
                .where(eligible_filter)
                .order_by(Meeting.created_at.asc(), Meeting.id.asc())
                .limit(max(limit, 0))
            )
        ).all()
    )
    selected_ids = {meeting.id for meeting in eligible_meetings}
    remaining = max(limit - len(eligible_meetings), 0)
    meetings = eligible_meetings
    if remaining:
        fill_query = (
            select(Meeting)
            .where(Meeting.workspace_id == workspace_id)
            .order_by(Meeting.created_at.asc(), Meeting.id.asc())
            .limit(remaining)
        )
        if selected_ids:
            fill_query = fill_query.where(~Meeting.id.in_(selected_ids))
        meetings.extend(list((await db.scalars(fill_query)).all()))

    evaluated = 0
    created_requests = 0
    skipped = 0
    blocked = 0
    # Keep scalar ids only: a per-meeting rollback expires all ORM instances
    # loaded in this session, so carrying Meeting objects across candidates
    # would trigger an implicit async refresh.
    candidate_ids = [meeting.id for meeting in meetings]
    for candidate_id in candidate_ids:
        # Retention eligibility is a destructive decision. Re-read and lock
        # the Meeting before checking processing status so a worker cannot
        # start processing between the scan snapshot and the tombstone fence.
        meeting = await db.scalar(
            select(Meeting)
            .where(Meeting.workspace_id == workspace_id, Meeting.id == candidate_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if meeting is None:
            continue
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

        try:
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
                local_buffer_expiry_days=snapshot.local_buffer_expiry_days,
                storage=storage,
                temporal_client=temporal_client,
            )
        except Exception:
            # One storage/Temporal failure must not abort the workspace batch.
            # Roll back only this candidate's transaction and leave a safe,
            # metadata-only audit outcome for the next bounded scan.
            await db.rollback()
            # The rollback also removes the snapshot row referenced by later
            # deletion requests.  Re-persist the authoritative policy before
            # continuing the batch and use its new id for all following work.
            snapshot = await persist_retention_policy_snapshot(
                db, settings, workspace_id=workspace_id
            )
            audit_snapshot = snapshot
            failed_meeting = await db.scalar(
                select(Meeting)
                .where(Meeting.workspace_id == workspace_id, Meeting.id == candidate_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if failed_meeting is not None:
                blocked += 1
                await _record_retention_evaluation(
                    db,
                    meeting=failed_meeting,
                    snapshot=audit_snapshot,
                    outcome=LifecycleAuditOutcome.BLOCKED,
                    safe_reason="deletion_request_failed",
                )
            continue
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
    if meeting_is_deleted_or_deleting(meeting):
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
