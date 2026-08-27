from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, delete, desc, exists, func, or_, select, tuple_, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    ArtifactDeletionState,
    DeletionRequestResponse,
    DeletionVerificationReport,
    LocalPurgeTask,
)
from twobrain_rec_server.billing.source_lifecycle import (
    SOURCE_TRACK_ROLES,
    TRANSIENT_HARD_LIFETIME,
    SourceLifecycleState,
    source_cogs_evidence,
    source_lifecycle_state_for_gates,
)
from twobrain_rec_server.billing.storage import (
    CANONICAL_PLAYBACK_PROFILE,
    logically_release_playback_quota,
)
from twobrain_rec_server.calendar.lifecycle import account_meeting_calendar_context_deletion
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    DispatchIntent,
    ExportPackage,
    MediaScribeJob,
    Meeting,
    MeetingDeletionArtifactState,
    MeetingDeletionReport,
    MeetingDeletionRequest,
    MeetingEgressAuditEvent,
    MeetingLifecycleAuditEvent,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    MeetingShareGrant,
    MeetingShareInvitation,
    MeetingSpeakerName,
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    ProcessingResult,
    ProcessingWorkflow,
    PurgeJournal,
    RetentionPolicySnapshot,
    TemporaryUploadObject,
    TrackArtifact,
    TranscriptSegment,
    UploadPart,
    UploadSession,
)
from twobrain_rec_server.db.models import (
    LocalPurgeTask as LocalPurgeTaskModel,
)
from twobrain_rec_server.deletion.audit import build_lifecycle_audit_metadata
from twobrain_rec_server.deletion.local_purge import (
    _aggregate_local_purge_state,
    _safe_reason_for_aggregate_state,
    create_local_purge_tasks_for_request,
    reconcile_expired_local_purge_tasks,
)
from twobrain_rec_server.deletion.report import (
    BOUNDED_DELETE_COPY,
    artifact_row,
    assemble_verification_report,
    lifecycle_activity_item,
    lifecycle_state,
    retention_policy_activity_row,
)
from twobrain_rec_server.domain.statuses import (
    DeletionArtifactClass,
    DeletionArtifactState,
    DeletionControlScope,
    DeletionReasonCode,
    DeletionRequestSource,
    DeletionState,
    LifecycleAuditOutcome,
    OutcomeLifecycleState,
    ProcessingStatus,
    TrackRole,
    UploadSessionStatus,
)
from twobrain_rec_server.normalization.audit import add_normalization_audit_event
from twobrain_rec_server.normalization.statuses import (
    AttemptState,
    JobState,
    NormalizationReason,
    ensure_attempt_transition,
    ensure_job_transition,
)
from twobrain_rec_server.processing.fences import ensure_deletion_fence
from twobrain_rec_server.processing.lifecycle import (
    MEDIA_REVISION_DELETION_SAFE_REASON,
    TERMINAL_PROCESSING_STATUSES,
)
from twobrain_rec_server.processing.store import (
    MEDIASCRIBE_SUBMISSION_CLAIM_STALE_AFTER,
    release_processing_usage_reservation,
    set_workflow_status,
)

TERMINAL_REQUEST_STATES = {
    DeletionState.COMPLETE.value,
    DeletionState.TERMINAL_FAILED.value,
}

DEFAULT_BACKUP_EXPIRY_DAYS = 30
MAX_PURGE_JOURNAL_ATTEMPTS = 8
STORAGE_CALL_TIMEOUT_SECONDS = 30.0
TRANSIENT_PURGE_OBJECT_LIMIT = 5

POST_EGRESS_REPORT_EVENT_TYPES = {
    "download_completed",
    "download_stream_prepared",
    "export_completed",
    "playback_completed",
    "playback_stream_prepared",
    "share_granted",
    "share_link_opened",
}

RETRY_UNAVAILABLE_GUIDANCE = "Retry is unavailable for the current lifecycle state. Open the deletion report for safe status details."
RETRY_OPERATOR_GUIDANCE = "Retry is available only after operator review confirms the failed artifact class is safe to retry."


@dataclass(slots=True)
class _ServerPurgeResult:
    purged_classes: set[DeletionArtifactClass] = field(default_factory=set)
    materialized_classes: set[DeletionArtifactClass] = field(default_factory=set)


async def request_meeting_deletion(
    db: AsyncSession,
    *,
    meeting: Meeting,
    actor_user_id: UUID | None,
    device_id: UUID | None,
    confirmation_boundary: str,
    request_source: DeletionRequestSource = DeletionRequestSource.OWNER,
    reason_code: DeletionReasonCode = DeletionReasonCode.USER_REQUEST,
    policy_snapshot_id: UUID | None = None,
    backup_expiry_days: int | None = DEFAULT_BACKUP_EXPIRY_DAYS,
    local_buffer_expiry_days: int | None = None,
    storage: object | None = None,
    temporal_client: object | None = None,
) -> DeletionRequestResponse:
    if confirmation_boundary != BOUNDED_DELETE_COPY:
        raise ProblemDetail(
            status=422, code="invalid_deletion_confirmation", title="Invalid deletion confirmation"
        )
    meeting_id = meeting.id
    workspace_id = meeting.workspace_id
    locked_meeting = await db.scalar(
        select(Meeting)
        .where(
            Meeting.id == meeting_id,
            Meeting.workspace_id == workspace_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locked_meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    meeting = locked_meeting
    if (
        meeting.deleted_at is not None
        or (meeting.deletion_state or DeletionState.NONE.value) != DeletionState.NONE.value
    ):
        raise ProblemDetail(
            status=409, code="meeting_deletion_active", title="Meeting deletion is already active"
        )
    active_request = await db.scalar(
        select(MeetingDeletionRequest)
        .where(MeetingDeletionRequest.workspace_id == workspace_id)
        .where(MeetingDeletionRequest.meeting_id == meeting_id)
        .where(MeetingDeletionRequest.state.notin_(TERMINAL_REQUEST_STATES))
        .order_by(desc(MeetingDeletionRequest.created_at))
    )
    if active_request is not None:
        raise ProblemDetail(
            status=409, code="meeting_deletion_active", title="Meeting deletion is already active"
        )

    now = datetime.now(UTC)
    meeting.deletion_epoch = int(meeting.deletion_epoch or 0) + 1
    meeting.deleted_at = now
    meeting.current_outcome_set_id = None
    deletion_fence = await ensure_deletion_fence(db, meeting=meeting)
    deletion_fence.epoch = meeting.deletion_epoch
    deletion_fence.state = "deleting"
    deletion_fence.requested_at = now
    await _flush_or_fail_closed(db)
    deletion_request = MeetingDeletionRequest(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        requested_by_user_id=actor_user_id,
        requested_by_device_id=device_id,
        request_source=request_source.value,
        reason_code=reason_code.value,
        confirmation_boundary=confirmation_boundary,
        state=DeletionState.DELETING.value,
        policy_snapshot_id=policy_snapshot_id,
        accepted_at=now,
        metadata_json=build_lifecycle_audit_metadata(
            state=DeletionState.DELETING,
            request_source=request_source,
            reason_code=reason_code,
            outcome=LifecycleAuditOutcome.ACCEPTED,
        ),
    )
    db.add(deletion_request)
    await _flush_or_fail_closed(db)
    request_id = deletion_request.id

    audit = MeetingLifecycleAuditEvent(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        deletion_request_id=request_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="deletion_requested",
        outcome=LifecycleAuditOutcome.ACCEPTED.value,
        safe_reason=reason_code.value,
        metadata_json=build_lifecycle_audit_metadata(
            state=DeletionState.DELETING,
            request_source=request_source,
            reason_code=reason_code,
            outcome=LifecycleAuditOutcome.ACCEPTED,
        ),
        created_at=now,
    )
    db.add(audit)
    await _flush_or_fail_closed(db)

    meeting.deletion_state = DeletionState.DELETING.value
    meeting.deletion_requested_at = now
    await db.execute(
        update(UploadSession)
        .where(
            UploadSession.workspace_id == workspace_id,
            UploadSession.meeting_id == meeting_id,
            UploadSession.status == UploadSessionStatus.FINALIZED.value,
            UploadSession.processing_status == ProcessingStatus.STARTING.value,
            UploadSession.media_revision_id.is_not(None),
        )
        .values(processing_status=ProcessingStatus.CANCELED.value)
    )
    await _flush_or_fail_closed(db)
    # Quota is a logical projection: release canonical playback bytes under
    # the committed tombstone before object-store deletion.  The artifact key
    # remains in the purge journal so physical deletion and retry evidence are
    # still handled by the existing lifecycle worker.
    await logically_release_playback_quota(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    calendar_context_artifact_count = await account_meeting_calendar_context_deletion(
        db,
        meeting=meeting,
        actor_user_id=actor_user_id,
        device_id=device_id,
        accounted_at=now,
    )
    local_purge_tasks = await create_local_purge_tasks_for_request(
        db,
        meeting=meeting,
        deletion_request_id=request_id,
        local_buffer_expiry_days=local_buffer_expiry_days,
    )
    outcomes_materialized, workflow_ids = await _mark_outcomes_deleting(db, meeting=meeting)
    post_egress_safe_reason = await _post_egress_safe_reason(db, meeting=meeting)
    initial_artifact_states = _initial_artifact_states(
        meeting,
        request_id,
        local_purge_requested=bool(local_purge_tasks),
        backup_expiry_days=backup_expiry_days,
        post_egress_safe_reason=post_egress_safe_reason,
        outcomes_materialized=outcomes_materialized,
        calendar_context_accounted=calendar_context_artifact_count > 0,
    )
    report = MeetingDeletionReport(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        deletion_request_id=request_id,
        overall_state=DeletionState.DELETING.value,
        summary_label="Deleting meeting",
        bounded_copy=BOUNDED_DELETE_COPY,
        artifact_summary_json=[_artifact_state_json(state) for state in initial_artifact_states],
        backup_state=DeletionArtifactState.PENDING_EXPIRY.value,
        local_purge_state=(
            DeletionArtifactState.LOCAL_PENDING.value
            if local_purge_tasks
            else DeletionArtifactState.NOT_APPLICABLE.value
        ),
        external_dependency_state=DeletionArtifactState.UNKNOWN.value,
        generated_at=now,
        updated_at=now,
    )
    # Commit the tombstone, deletion epoch, request, fence, and an initial
    # report before touching object storage.  DB and object-store deletion are
    # not atomic; the tombstone must survive a later storage failure.
    db.add_all([*initial_artifact_states, report])
    await _flush_or_fail_closed(db)
    report_id = report.id
    _ensure_storage_delete_capability(storage)
    await db.commit()
    await _request_temporal_cancellation(
        temporal_client,
        workflow_ids=workflow_ids,
    )
    try:
        purge_result = await _purge_server_controlled_content(
            db,
            meeting=meeting,
            storage=storage,
            deletion_request_id=request_id,
        )
    except Exception as exc:
        report = await db.scalar(
            select(MeetingDeletionReport)
            .where(MeetingDeletionReport.id == report_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        deletion_request = (
            await db.scalar(
                select(MeetingDeletionRequest)
                .where(MeetingDeletionRequest.id == request_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if report is not None
            else None
        )
        if report is not None and report.overall_state == DeletionState.ACTIVE_PURGE_COMPLETE.value:
            await db.rollback()
            return DeletionRequestResponse(
                request_id=request_id,
                meeting_id=meeting_id,
                lifecycle=lifecycle_state(DeletionState.ACTIVE_PURGE_COMPLETE),
                report_url=f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report",
            )
        if report is not None:
            report.overall_state = DeletionState.RETRYABLE_FAILED.value
            report.summary_label = (
                "Deletion requires operator retry"
                if getattr(exc, "code", None) == "deletion_purge_terminal_unknown"
                else "Deletion needs retry"
            )
            report.updated_at = datetime.now(UTC)
            if deletion_request is not None:
                deletion_request.state = DeletionState.RETRYABLE_FAILED.value
                deletion_request.failure_reason = (
                    getattr(exc, "code", None) or "server_controlled_purge_failed"
                )
                deletion_request.failed_at = datetime.now(UTC)
            await db.commit()
        raise
    report = await db.scalar(
        select(MeetingDeletionReport)
        .where(MeetingDeletionReport.id == report_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if report is not None and report.overall_state == DeletionState.ACTIVE_PURGE_COMPLETE.value:
        await db.rollback()
        return DeletionRequestResponse(
            request_id=request_id,
            meeting_id=meeting_id,
            lifecycle=lifecycle_state(DeletionState.ACTIVE_PURGE_COMPLETE),
            report_url=f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report",
        )
    artifact_states = _initial_artifact_states(
        meeting,
        request_id,
        local_purge_requested=bool(local_purge_tasks),
        backup_expiry_days=backup_expiry_days,
        post_egress_safe_reason=post_egress_safe_reason,
        outcomes_materialized=outcomes_materialized,
        purged_artifact_classes=purge_result.purged_classes,
        materialized_artifact_classes=purge_result.materialized_classes,
        calendar_context_accounted=calendar_context_artifact_count > 0,
    )
    report = await db.scalar(
        select(MeetingDeletionReport).where(MeetingDeletionReport.id == report_id).with_for_update()
    )
    if report is None:
        raise ProblemDetail(
            status=503,
            code="deletion_report_unavailable",
            title="Deletion report unavailable",
        )
    report.artifact_summary_json = [_artifact_state_json(state) for state in artifact_states]
    report.updated_at = datetime.now(UTC)
    initial_by_class = {state.artifact_class: state for state in initial_artifact_states}
    for state in artifact_states:
        persisted = initial_by_class.get(state.artifact_class)
        if persisted is None:
            db.add(state)
            continue
        persisted.control_scope = state.control_scope
        persisted.state = state.state
        persisted.safe_reason = state.safe_reason
        persisted.metadata_json = state.metadata_json
        persisted.updated_at = datetime.now(UTC)
    await _flush_or_fail_closed(db)
    completed_at = datetime.now(UTC)
    report.overall_state = DeletionState.ACTIVE_PURGE_COMPLETE.value
    report.summary_label = "Server-controlled meeting data purged"
    report.updated_at = completed_at
    deletion_request.state = DeletionState.ACTIVE_PURGE_COMPLETE.value
    deletion_request.failure_reason = None
    deletion_request.completed_at = completed_at
    meeting.deletion_state = DeletionState.ACTIVE_PURGE_COMPLETE.value
    fence = await ensure_deletion_fence(db, meeting=meeting)
    fence.state = DeletionState.ACTIVE_PURGE_COMPLETE.value
    fence.completed_at = completed_at
    await db.commit()
    return DeletionRequestResponse(
        request_id=request_id,
        meeting_id=meeting_id,
        lifecycle=lifecycle_state(DeletionState.ACTIVE_PURGE_COMPLETE),
        report_url=f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report",
    )


async def lifecycle_for_meeting(*, meeting: Meeting) -> DeletionState:
    if (
        meeting.deleted_at is not None
        and (meeting.deletion_state or DeletionState.NONE.value) == DeletionState.NONE.value
    ):
        return DeletionState.DELETING
    return DeletionState(meeting.deletion_state or DeletionState.NONE.value)


async def fanout_account_close_deletions(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    storage: object | None,
    temporal_client: object | None = None,
    limit: int = 500,
) -> tuple[UUID, ...]:
    """Start the existing meeting-deletion workflow for account finalization.

    Account close must not invent a second purge implementation.  This helper
    snapshots eligible meeting ids, then delegates each row to the same
    tombstone/quota-release/object-purge path used by owner deletion.  A
    storage adapter is required so an unavailable object-store fails closed
    before the account-close request can be marked complete.
    """

    batch_size = max(1, min(limit, 1000))
    accepted: list[UUID] = []
    storage_checked = False
    while True:
        meeting_ids = tuple(
            await db.scalars(
                select(Meeting.id)
                .where(
                    Meeting.workspace_id == workspace_id,
                    Meeting.deleted_at.is_(None),
                    or_(
                        Meeting.deletion_state.is_(None),
                        Meeting.deletion_state == DeletionState.NONE.value,
                    ),
                )
                .order_by(Meeting.created_at, Meeting.id)
                .limit(batch_size)
            )
        )
        if not meeting_ids:
            break
        if not storage_checked:
            _ensure_storage_delete_capability(storage)
            storage_checked = True
        for meeting_id in meeting_ids:
            meeting = await db.scalar(
                select(Meeting)
                .where(Meeting.workspace_id == workspace_id, Meeting.id == meeting_id)
                .with_for_update()
            )
            if (
                meeting is None
                or meeting.deleted_at is not None
                or (meeting.deletion_state or DeletionState.NONE.value) != DeletionState.NONE.value
            ):
                continue
            await request_meeting_deletion(
                db,
                meeting=meeting,
                actor_user_id=None,
                device_id=None,
                confirmation_boundary=BOUNDED_DELETE_COPY,
                request_source=DeletionRequestSource.ACCOUNT_CLOSE,
                reason_code=DeletionReasonCode.ACCOUNT_CLOSE,
                storage=storage,
                temporal_client=temporal_client,
            )
            accepted.append(meeting_id)
        if len(meeting_ids) < batch_size:
            break
    return tuple(accepted)


async def retry_meeting_deletion(
    db: AsyncSession,
    *,
    meeting: Meeting,
    storage: object | None,
    temporal_client: object | None = None,
    _allow_in_progress: bool = False,
    _automatic_reconciliation: bool = False,
) -> DeletionRequestResponse:
    meeting_id = meeting.id
    workspace_id = meeting.workspace_id
    locked_meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.workspace_id == workspace_id, Meeting.id == meeting_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locked_meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    meeting = locked_meeting
    report = await db.scalar(
        select(MeetingDeletionReport)
        .where(
            MeetingDeletionReport.workspace_id == workspace_id,
            MeetingDeletionReport.meeting_id == meeting_id,
        )
        .order_by(desc(MeetingDeletionReport.updated_at))
    )
    allowed_report_states = {DeletionState.RETRYABLE_FAILED.value}
    if _allow_in_progress:
        allowed_report_states.add(DeletionState.DELETING.value)
    if report is None or report.overall_state not in allowed_report_states:
        state = await lifecycle_for_meeting(meeting=meeting)
        raise ProblemDetail(
            status=409,
            code="deletion_retry_unavailable",
            title="Deletion retry is not available",
            detail=deletion_retry_guidance(state),
        )
    report_id = report.id
    report_request_id = report.deletion_request_id
    # Keep retry on Meeting → local tasks → artifact state → report. The
    # report is intentionally discovered unlocked, then reloaded after the
    # subordinate rows are protected to avoid report↔artifact cycles with ACK.
    await db.scalars(
        select(LocalPurgeTaskModel)
        .where(
            LocalPurgeTaskModel.workspace_id == workspace_id,
            LocalPurgeTaskModel.meeting_id == meeting_id,
            LocalPurgeTaskModel.deletion_request_id == report_request_id,
        )
        .order_by(LocalPurgeTaskModel.id.asc())
        .with_for_update()
    )
    await db.scalar(
        select(MeetingDeletionArtifactState)
        .where(
            MeetingDeletionArtifactState.workspace_id == workspace_id,
            MeetingDeletionArtifactState.meeting_id == meeting_id,
            MeetingDeletionArtifactState.deletion_request_id == report_request_id,
            MeetingDeletionArtifactState.artifact_class
            == DeletionArtifactClass.LOCAL_DESKTOP_BUFFER.value,
        )
        .with_for_update()
    )
    report = await db.scalar(
        select(MeetingDeletionReport)
        .where(MeetingDeletionReport.id == report_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if report is None or report.overall_state not in allowed_report_states:
        state = await lifecycle_for_meeting(meeting=meeting)
        raise ProblemDetail(
            status=409,
            code="deletion_retry_unavailable",
            title="Deletion retry is not available",
            detail=deletion_retry_guidance(state),
        )
    deletion_request = await db.scalar(
        select(MeetingDeletionRequest)
        .where(
            MeetingDeletionRequest.id == report_request_id,
            MeetingDeletionRequest.workspace_id == workspace_id,
            MeetingDeletionRequest.meeting_id == meeting_id,
        )
        .with_for_update()
    )
    if deletion_request is None or meeting.deleted_at is None:
        raise ProblemDetail(
            status=409,
            code="deletion_retry_unavailable",
            title="Deletion retry is not available",
            detail=RETRY_UNAVAILABLE_GUIDANCE,
        )
    backup_expiry_days = await _backup_expiry_days_for_retry(
        db,
        deletion_request=deletion_request,
        report=report,
    )
    if not _automatic_reconciliation:
        terminal_journal_rows = (
            await db.scalars(
                select(PurgeJournal)
                .where(
                    PurgeJournal.workspace_id == workspace_id,
                    PurgeJournal.meeting_id == meeting_id,
                    PurgeJournal.state == "terminal_unknown",
                )
                .with_for_update()
            )
        ).all()
        retry_started_at = datetime.now(UTC)
        for journal in terminal_journal_rows:
            journal.state = "retryable_failed"
            journal.safe_reason = "operator_retry_requested"
            journal.next_retry_at = retry_started_at
    _, workflow_ids = await _mark_outcomes_deleting(db, meeting=meeting)
    await db.commit()
    await _request_temporal_cancellation(temporal_client, workflow_ids=workflow_ids)
    try:
        purge_result = await _purge_server_controlled_content(
            db,
            meeting=meeting,
            storage=storage,
            deletion_request_id=report_request_id,
        )
    except Exception as exc:
        report = await db.scalar(
            select(MeetingDeletionReport)
            .where(MeetingDeletionReport.id == report_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        deletion_request = (
            await db.scalar(
                select(MeetingDeletionRequest)
                .where(MeetingDeletionRequest.id == report_request_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if report is not None
            else None
        )
        if report is None or deletion_request is None:
            raise
        if report.overall_state == DeletionState.ACTIVE_PURGE_COMPLETE.value:
            await db.rollback()
            return DeletionRequestResponse(
                request_id=report_request_id,
                meeting_id=meeting_id,
                lifecycle=lifecycle_state(DeletionState.ACTIVE_PURGE_COMPLETE),
                report_url=f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report",
            )
        else:
            report.overall_state = DeletionState.RETRYABLE_FAILED.value
            report.summary_label = (
                "Deletion requires operator retry"
                if getattr(exc, "code", None) == "deletion_purge_terminal_unknown"
                else "Deletion needs retry"
            )
            deletion_request.state = DeletionState.RETRYABLE_FAILED.value
            deletion_request.failure_reason = (
                getattr(exc, "code", None) or "server_controlled_purge_failed"
            )
            deletion_request.failed_at = datetime.now(UTC)
            report.updated_at = datetime.now(UTC)
            await db.commit()
        raise
    # Reacquire the same lifecycle order after storage I/O: Meeting → local
    # tasks → artifact state → report. This prevents a post-purge retry from
    # taking the report first while an ACK refresh takes the artifact first.
    meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.workspace_id == workspace_id, Meeting.id == meeting_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    local_purge_tasks = (
        await db.scalars(
            select(LocalPurgeTaskModel)
            .where(
                LocalPurgeTaskModel.workspace_id == workspace_id,
                LocalPurgeTaskModel.meeting_id == meeting_id,
                LocalPurgeTaskModel.deletion_request_id == report_request_id,
            )
            .order_by(LocalPurgeTaskModel.id.asc())
            .with_for_update()
        )
    ).all()
    persisted_states = (
        await db.scalars(
            select(MeetingDeletionArtifactState)
            .where(
                MeetingDeletionArtifactState.workspace_id == workspace_id,
                MeetingDeletionArtifactState.meeting_id == meeting_id,
                MeetingDeletionArtifactState.deletion_request_id == report_request_id,
            )
            .order_by(MeetingDeletionArtifactState.artifact_class.asc())
            .with_for_update()
        )
    ).all()
    report = await db.scalar(
        select(MeetingDeletionReport)
        .where(MeetingDeletionReport.id == report_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if report is None:
        raise ProblemDetail(
            status=503, code="deletion_report_unavailable", title="Deletion report unavailable"
        )
    deletion_request = await db.scalar(
        select(MeetingDeletionRequest)
        .where(
            MeetingDeletionRequest.id == report_request_id,
            MeetingDeletionRequest.workspace_id == workspace_id,
            MeetingDeletionRequest.meeting_id == meeting_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if deletion_request is None:
        raise ProblemDetail(
            status=503,
            code="deletion_request_unavailable",
            title="Deletion request unavailable",
        )
    if report.overall_state == DeletionState.ACTIVE_PURGE_COMPLETE.value:
        await db.rollback()
        return DeletionRequestResponse(
            request_id=report_request_id,
            meeting_id=meeting_id,
            lifecycle=lifecycle_state(DeletionState.ACTIVE_PURGE_COMPLETE),
            report_url=f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report",
        )
    local_purge_state = (
        _aggregate_local_purge_state(local_purge_tasks) if local_purge_tasks else None
    )
    artifact_states = _initial_artifact_states(
        meeting,
        report_request_id,
        local_purge_requested=bool(local_purge_tasks),
        local_purge_state=local_purge_state,
        local_purge_reason=(
            _safe_reason_for_aggregate_state(local_purge_state)
            if local_purge_state is not None
            else None
        ),
        backup_expiry_days=backup_expiry_days,
        post_egress_safe_reason=await _post_egress_safe_reason(db, meeting=meeting),
        outcomes_materialized=DeletionArtifactClass.NOTES_SUMMARY
        in purge_result.materialized_classes,
        purged_artifact_classes=purge_result.purged_classes,
        materialized_artifact_classes=purge_result.materialized_classes,
    )
    persisted_by_class = {row.artifact_class: row for row in persisted_states}
    for state in artifact_states:
        persisted = persisted_by_class.get(state.artifact_class)
        if persisted is None:
            db.add(state)
            continue
        persisted.control_scope = state.control_scope
        persisted.state = state.state
        persisted.safe_reason = state.safe_reason
        persisted.metadata_json = state.metadata_json
        persisted.updated_at = datetime.now(UTC)
    report.artifact_summary_json = [_artifact_state_json(state) for state in artifact_states]
    completed_at = datetime.now(UTC)
    report.overall_state = DeletionState.ACTIVE_PURGE_COMPLETE.value
    report.summary_label = "Server-controlled meeting data purged"
    report.updated_at = completed_at
    deletion_request.state = DeletionState.ACTIVE_PURGE_COMPLETE.value
    deletion_request.failure_reason = None
    deletion_request.completed_at = completed_at
    meeting.deletion_state = DeletionState.ACTIVE_PURGE_COMPLETE.value
    fence = await ensure_deletion_fence(db, meeting=meeting)
    fence.state = DeletionState.ACTIVE_PURGE_COMPLETE.value
    fence.completed_at = completed_at
    await db.commit()
    return DeletionRequestResponse(
        request_id=report_request_id,
        meeting_id=meeting_id,
        lifecycle=lifecycle_state(DeletionState.ACTIVE_PURGE_COMPLETE),
        report_url=f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report",
    )


async def reconcile_deletion_purges(
    db: AsyncSession,
    *,
    storage: object | None,
    temporal_client: object | None = None,
    limit: int = 20,
) -> int:
    """Resume committed deletion tombstones after a worker or storage outage."""
    now = datetime.now(UTC)
    due_journal_meeting_ids = select(PurgeJournal.meeting_id).where(
        PurgeJournal.artifact_class != "transient_audio",
        PurgeJournal.state.in_({"pending", "deleting", "retryable_failed"}),
        PurgeJournal.attempt_count < MAX_PURGE_JOURNAL_ATTEMPTS,
        PurgeJournal.next_retry_at.is_(None) | (PurgeJournal.next_retry_at <= now),
    )
    pending_report_meeting_ids = select(MeetingDeletionReport.meeting_id).where(
        (MeetingDeletionReport.overall_state == DeletionState.DELETING.value)
        | (
            (MeetingDeletionReport.overall_state == DeletionState.RETRYABLE_FAILED.value)
            & (
                ~exists(
                    select(PurgeJournal.id).where(
                        PurgeJournal.meeting_id == MeetingDeletionReport.meeting_id,
                        PurgeJournal.artifact_class != "transient_audio",
                        PurgeJournal.state.not_in({"purged", "superseded"}),
                    )
                )
                | MeetingDeletionReport.meeting_id.in_(due_journal_meeting_ids)
            )
        )
    )
    # Orphan cleanup intents are also emitted by upload/finalize races for an
    # otherwise active meeting. They are independent of a deletion report and
    # must not be stranded behind the deleted_at/report filter.
    pending_meeting_ids = select(Meeting.id).where(
        or_(
            Meeting.id.in_(pending_report_meeting_ids),
            Meeting.id.in_(due_journal_meeting_ids),
        )
    )
    # Keep only immutable identifiers across iterations. A failed cleanup can
    # roll back the session and expire every ORM instance, so carrying Meeting
    # objects into the next iteration would trigger an implicit async refresh.
    meeting_keys = list(
        (
            await db.execute(
                select(Meeting.id, Meeting.workspace_id)
                .where(Meeting.id.in_(pending_meeting_ids))
                .order_by(Meeting.deletion_requested_at.asc(), Meeting.id.asc())
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    reconciled = 0
    for meeting_id, workspace_id in meeting_keys:
        meeting = await db.scalar(
            select(Meeting)
            .where(Meeting.id == meeting_id, Meeting.workspace_id == workspace_id)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        if meeting is None:
            continue
        report = await db.scalar(
            select(MeetingDeletionReport)
            .where(
                MeetingDeletionReport.workspace_id == workspace_id,
                MeetingDeletionReport.meeting_id == meeting_id,
            )
            .order_by(desc(MeetingDeletionReport.updated_at))
        )
        allowed_report_states = {DeletionState.RETRYABLE_FAILED.value}
        if report is not None and report.overall_state == DeletionState.DELETING.value:
            allowed_report_states.add(DeletionState.DELETING.value)
        try:
            if report is not None and report.overall_state in allowed_report_states:
                await retry_meeting_deletion(
                    db,
                    meeting=meeting,
                    storage=storage,
                    temporal_client=temporal_client,
                    _allow_in_progress=True,
                    _automatic_reconciliation=True,
                )
                reconciled += 1
            elif await _reconcile_orphan_purge_journals(
                db,
                meeting=meeting,
                storage=storage,
            ):
                reconciled += 1
        except Exception:
            await db.rollback()
            continue
    return reconciled


async def reconcile_transient_media_purges(
    db: AsyncSession,
    *,
    storage: object | None,
    now: datetime | None = None,
    limit: int = 20,
    object_limit: int = TRANSIENT_PURGE_OBJECT_LIMIT,
) -> int:
    """Purge persisted no-archive media after terminal/24-hour deadlines.

    The admission and deadlines live on ``ProcessingWorkflow``; object keys
    are read from the existing TrackArtifact, normalization-attempt and
    TemporaryUploadObject lifecycle rows.  This deliberately does not delete
    transcripts/notes and does not use a fake counter as purge evidence.
    """

    now = now or datetime.now(UTC)
    bounded_limit = max(1, min(limit, 100))
    remaining_object_budget = max(1, min(object_limit, 500))
    terminal_processing_statuses = {status.value for status in TERMINAL_PROCESSING_STATUSES}
    active_workflow = aliased(ProcessingWorkflow)
    hard_deadline_due = and_(
        ProcessingWorkflow.transient_hard_deadline.is_not(None),
        ProcessingWorkflow.transient_hard_deadline <= now,
    )
    terminal_deadline_due = and_(
        ProcessingWorkflow.transient_purge_due_at.is_not(None),
        ProcessingWorkflow.transient_purge_due_at <= now,
    )
    no_active_attempt = ~exists().where(
        active_workflow.workspace_id == ProcessingWorkflow.workspace_id,
        active_workflow.meeting_id == ProcessingWorkflow.meeting_id,
        active_workflow.media_revision_id == ProcessingWorkflow.media_revision_id,
        active_workflow.status.not_in(terminal_processing_statuses),
    )
    workflow_due_at = func.min(
        func.least(
            func.coalesce(
                ProcessingWorkflow.transient_hard_deadline,
                ProcessingWorkflow.transient_purge_due_at,
            ),
            func.coalesce(
                ProcessingWorkflow.transient_purge_due_at,
                ProcessingWorkflow.transient_hard_deadline,
            ),
        )
    ).label("due_at")
    due_workflow_revisions = (
        select(
            ProcessingWorkflow.workspace_id.label("workspace_id"),
            ProcessingWorkflow.meeting_id.label("meeting_id"),
            ProcessingWorkflow.media_revision_id.label("media_revision_id"),
            workflow_due_at,
        )
        .where(
            ProcessingWorkflow.archive_audio.is_(False),
            ProcessingWorkflow.media_revision_id.is_not(None),
            ProcessingWorkflow.transient_state.in_(
                {"admitted", "processing", "terminal", "purge_due"}
            ),
            or_(
                hard_deadline_due,
                and_(terminal_deadline_due, no_active_attempt),
            ),
        )
        .group_by(
            ProcessingWorkflow.workspace_id,
            ProcessingWorkflow.meeting_id,
            ProcessingWorkflow.media_revision_id,
        )
        .cte("due_transient_workflow_revisions")
    )
    deferred_journal = exists().where(
        PurgeJournal.workspace_id == due_workflow_revisions.c.workspace_id,
        PurgeJournal.meeting_id == due_workflow_revisions.c.meeting_id,
        PurgeJournal.artifact_class == "transient_audio",
        PurgeJournal.state != "purged",
        PurgeJournal.next_retry_at.is_not(None),
        PurgeJournal.next_retry_at > now,
    )
    due_workflow_rows = list(
        (
            await db.execute(
                select(
                    due_workflow_revisions.c.workspace_id,
                    due_workflow_revisions.c.meeting_id,
                    due_workflow_revisions.c.media_revision_id,
                )
                .join(
                    Meeting,
                    and_(
                        Meeting.workspace_id == due_workflow_revisions.c.workspace_id,
                        Meeting.id == due_workflow_revisions.c.meeting_id,
                    ),
                )
                .where(
                    Meeting.deleted_at.is_(None),
                    or_(
                        Meeting.deletion_state.is_(None),
                        Meeting.deletion_state == DeletionState.NONE.value,
                    ),
                    ~deferred_journal,
                )
                .order_by(
                    due_workflow_revisions.c.due_at,
                    due_workflow_revisions.c.media_revision_id,
                )
                .with_for_update(of=Meeting, skip_locked=True)
                .limit(bounded_limit)
            )
        ).all()
    )
    candidates = [
        (workspace_id, meeting_id, media_revision_id)
        for workspace_id, meeting_id, media_revision_id in due_workflow_rows
        if media_revision_id is not None
    ]
    seen_candidates = set(candidates)
    if len(candidates) < bounded_limit:
        fallback_due_revisions = (
            select(
                UploadSession.workspace_id.label("workspace_id"),
                UploadSession.meeting_id.label("meeting_id"),
                UploadSession.media_revision_id.label("media_revision_id"),
                func.min(UploadSession.finalized_at).label("due_at"),
            )
            .where(
                UploadSession.archive_audio.is_(False),
                UploadSession.status == UploadSessionStatus.FINALIZED.value,
                UploadSession.media_revision_id.is_not(None),
                UploadSession.finalized_at.is_not(None),
                UploadSession.finalized_at <= now - TRANSIENT_HARD_LIFETIME,
                or_(
                    exists().where(
                        TemporaryUploadObject.upload_session_id == UploadSession.id,
                        TemporaryUploadObject.cleanup_status != "purged",
                    ),
                    exists().where(
                        TrackArtifact.workspace_id == UploadSession.workspace_id,
                        TrackArtifact.meeting_id == UploadSession.meeting_id,
                        TrackArtifact.media_revision_id == UploadSession.media_revision_id,
                        TrackArtifact.track_role.in_(
                            (*SOURCE_TRACK_ROLES, TrackRole.PLAYBACK.value)
                        ),
                        TrackArtifact.status.not_in({"purged", "deleted"}),
                    ),
                ),
            )
            .group_by(
                UploadSession.workspace_id,
                UploadSession.meeting_id,
                UploadSession.media_revision_id,
            )
            .cte("due_transient_upload_revisions")
        )
        fallback_deferred_journal = exists().where(
            PurgeJournal.workspace_id == fallback_due_revisions.c.workspace_id,
            PurgeJournal.meeting_id == fallback_due_revisions.c.meeting_id,
            PurgeJournal.artifact_class == "transient_audio",
            PurgeJournal.state != "purged",
            PurgeJournal.next_retry_at.is_not(None),
            PurgeJournal.next_retry_at > now,
        )
        fallback_statement = (
            select(
                fallback_due_revisions.c.workspace_id,
                fallback_due_revisions.c.meeting_id,
                fallback_due_revisions.c.media_revision_id,
            )
            .join(
                Meeting,
                and_(
                    Meeting.workspace_id == fallback_due_revisions.c.workspace_id,
                    Meeting.id == fallback_due_revisions.c.meeting_id,
                ),
            )
            .where(
                Meeting.deleted_at.is_(None),
                or_(
                    Meeting.deletion_state.is_(None),
                    Meeting.deletion_state == DeletionState.NONE.value,
                ),
                ~fallback_deferred_journal,
            )
            .order_by(
                fallback_due_revisions.c.due_at,
                fallback_due_revisions.c.media_revision_id,
            )
            .with_for_update(of=Meeting, skip_locked=True)
            .limit(bounded_limit - len(candidates))
        )
        if seen_candidates:
            fallback_statement = fallback_statement.where(
                tuple_(
                    fallback_due_revisions.c.workspace_id,
                    fallback_due_revisions.c.meeting_id,
                    fallback_due_revisions.c.media_revision_id,
                ).not_in(seen_candidates)
            )
        fallback_rows = (await db.execute(fallback_statement)).all()
        for workspace_id, meeting_id, media_revision_id in fallback_rows:
            candidate = (workspace_id, meeting_id, media_revision_id)
            if media_revision_id is not None and candidate not in seen_candidates:
                candidates.append(candidate)
                seen_candidates.add(candidate)
    await db.rollback()
    purged = 0
    for workspace_id, meeting_id, media_revision_id in candidates[:bounded_limit]:
        meeting = await db.scalar(
            select(Meeting)
            .where(Meeting.workspace_id == workspace_id, Meeting.id == meeting_id)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        if (
            meeting is None
            or meeting.deleted_at is not None
            or meeting.deletion_state
            not in {
                None,
                DeletionState.NONE.value,
            }
        ):
            await db.rollback()
            continue
        workflows = list(
            await db.scalars(
                select(ProcessingWorkflow)
                .where(
                    ProcessingWorkflow.workspace_id == workspace_id,
                    ProcessingWorkflow.meeting_id == meeting_id,
                    ProcessingWorkflow.media_revision_id == media_revision_id,
                )
                .order_by(ProcessingWorkflow.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        mediascribe_jobs = list(
            await db.scalars(
                select(MediaScribeJob)
                .where(
                    MediaScribeJob.workspace_id == workspace_id,
                    MediaScribeJob.meeting_id == meeting_id,
                    MediaScribeJob.media_revision_id == media_revision_id,
                )
                .order_by(MediaScribeJob.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        jobs = list(
            await db.scalars(
                select(PlaybackNormalizationJob)
                .where(
                    PlaybackNormalizationJob.workspace_id == workspace_id,
                    PlaybackNormalizationJob.meeting_id == meeting_id,
                    PlaybackNormalizationJob.media_revision_id == media_revision_id,
                )
                .order_by(PlaybackNormalizationJob.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        attempts = list(
            await db.scalars(
                select(PlaybackNormalizationAttempt)
                .where(
                    PlaybackNormalizationAttempt.workspace_id == workspace_id,
                    PlaybackNormalizationAttempt.meeting_id == meeting_id,
                    PlaybackNormalizationAttempt.media_revision_id == media_revision_id,
                    or_(
                        PlaybackNormalizationAttempt.state != AttemptState.PURGED.value,
                        PlaybackNormalizationAttempt.cleaned_at.is_(None),
                    ),
                )
                .order_by(PlaybackNormalizationAttempt.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        artifacts = list(
            await db.scalars(
                select(TrackArtifact)
                .where(
                    TrackArtifact.workspace_id == workspace_id,
                    TrackArtifact.meeting_id == meeting_id,
                    TrackArtifact.media_revision_id == media_revision_id,
                    TrackArtifact.track_role.in_((*SOURCE_TRACK_ROLES, TrackRole.PLAYBACK.value)),
                    TrackArtifact.status.not_in({"purged", "deleted"}),
                )
                .order_by(TrackArtifact.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        sessions = list(
            await db.scalars(
                select(UploadSession)
                .where(
                    UploadSession.workspace_id == workspace_id,
                    UploadSession.meeting_id == meeting_id,
                    UploadSession.media_revision_id == media_revision_id,
                    UploadSession.status == UploadSessionStatus.FINALIZED.value,
                )
                .order_by(UploadSession.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        temporary_objects = list(
            (
                await db.scalars(
                    select(TemporaryUploadObject)
                    .join(
                        UploadSession, TemporaryUploadObject.upload_session_id == UploadSession.id
                    )
                    .where(
                        TemporaryUploadObject.workspace_id == workspace_id,
                        TemporaryUploadObject.media_revision_id == media_revision_id,
                        UploadSession.workspace_id == workspace_id,
                        UploadSession.meeting_id == meeting_id,
                        UploadSession.media_revision_id == media_revision_id,
                        TemporaryUploadObject.cleanup_status != "purged",
                    )
                    .order_by(TemporaryUploadObject.id)
                    .with_for_update(of=TemporaryUploadObject)
                    .execution_options(populate_existing=True)
                )
            ).all()
        )
        if any(workflow.archive_audio for workflow in workflows) or any(
            session.archive_audio for session in sessions
        ):
            await db.rollback()
            continue
        hard_deadlines = [
            deadline
            for deadline in (
                *(workflow.transient_hard_deadline for workflow in workflows),
                *(
                    session.finalized_at + TRANSIENT_HARD_LIFETIME
                    for session in sessions
                    if session.finalized_at is not None
                ),
            )
            if deadline is not None
        ]
        hard_due = bool(hard_deadlines and min(hard_deadlines) <= now)
        terminal_due = any(
            workflow.transient_purge_due_at is not None and workflow.transient_purge_due_at <= now
            for workflow in workflows
        )
        active_workflow = any(
            workflow.status not in terminal_processing_statuses for workflow in workflows
        )
        fresh_submission_claim = any(
            job.status == "submitting"
            and bool(job.submission_claim_token)
            and job.submission_claimed_at is not None
            and now - job.submission_claimed_at < MEDIASCRIBE_SUBMISSION_CLAIM_STALE_AFTER
            for job in mediascribe_jobs
        )
        fresh_normalization_claim = any(
            job.state in {JobState.RUNNING.value, JobState.PUBLISHING.value}
            and job.lease_expires_at is not None
            and job.lease_expires_at > now
            for job in jobs
        )
        late_put_tombstone_keys = {
            attempt.storage_object_key
            for attempt in attempts
            if attempt.uploaded_at is None
            and attempt.cleaned_at is None
            and attempt.state
            in {
                AttemptState.LOCAL_PREPARING.value,
                AttemptState.CLEANUP_PENDING.value,
                AttemptState.PURGED.value,
            }
        }
        if hard_due and active_workflow:
            for workflow in workflows:
                if workflow.status not in terminal_processing_statuses:
                    await set_workflow_status(
                        db,
                        workflow,
                        ProcessingStatus.CANCELED,
                        reason_code=NormalizationReason.AUDIO_PURGED.value,
                        terminal=True,
                        commit=False,
                    )
            active_workflow = False
        if (fresh_submission_claim and not hard_due) or (
            not hard_due and (not terminal_due or active_workflow)
        ):
            await db.rollback()
            continue

        object_keys = {
            *(artifact.storage_object_key for artifact in artifacts),
            *(attempt.storage_object_key for attempt in attempts),
            *(temporary_object.storage_object_key for temporary_object in temporary_objects),
        }
        if object_keys:
            _ensure_storage_delete_capability(storage)
        journals = {
            row.object_key: row
            for row in (
                await db.scalars(
                    select(PurgeJournal)
                    .where(
                        PurgeJournal.workspace_id == workspace_id,
                        PurgeJournal.meeting_id == meeting_id,
                        PurgeJournal.artifact_class == "transient_audio",
                        PurgeJournal.object_key.in_(object_keys or {""}),
                    )
                    .order_by(PurgeJournal.id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            ).all()
        }
        for object_key in sorted(object_keys):
            if object_key not in journals:
                journal = PurgeJournal(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    artifact_class="transient_audio",
                    object_key=object_key,
                    state="pending",
                    safe_reason="transient_media_purge",
                )
                db.add(journal)
                journals[object_key] = journal
        for workflow in workflows:
            if not workflow.archive_audio and workflow.transient_state != "purged":
                workflow.transient_state = "purge_due"
        for job in jobs:
            if job.state in {
                JobState.QUEUED.value,
                JobState.RUNNING.value,
                JobState.PUBLISHING.value,
                JobState.RETRY_WAIT.value,
                JobState.READY.value,
            }:
                ensure_job_transition(
                    JobState(job.state),
                    JobState.CANCELLED,
                    reason_code=NormalizationReason.AUDIO_PURGED,
                )
                job.state = JobState.CANCELLED.value
                job.reason_code = NormalizationReason.AUDIO_PURGED.value
                job.cancelled_at = now
                job.lease_owner_sha256 = None
                job.lease_expires_at = None
        for attempt in attempts:
            current = AttemptState(attempt.state)
            if current in {
                AttemptState.LOCAL_PREPARING,
                AttemptState.UPLOADED,
                AttemptState.CLEANED,
            }:
                ensure_attempt_transition(current, AttemptState.CLEANUP_PENDING)
                attempt.state = AttemptState.CLEANUP_PENDING.value
                attempt.cleanup_reason = NormalizationReason.AUDIO_PURGED.value
        for artifact in artifacts:
            artifact.status = "purge_pending"
            if artifact.track_role in SOURCE_TRACK_ROLES:
                artifact.source_lifecycle_state = SourceLifecycleState.PURGE_PENDING.value
                artifact.source_retention_purge_due_at = None
            if artifact.track_role == TrackRole.PLAYBACK.value:
                artifact.normalization_profile_version = None
                artifact.validated_at = None
                artifact.derivation_kind = None
                artifact.source_fingerprint_sha256 = None
                artifact.validation_version = None
        for temporary_object in temporary_objects:
            temporary_object.cleanup_status = "purge_pending"
        await db.commit()
        if fresh_submission_claim or fresh_normalization_claim:
            # The durable purge fence is committed, so workers cannot publish
            # or submit again. Let an already-running external I/O call settle
            # before deleting its source or late-PUT target.
            continue

        all_objects_purged = True
        for object_key in sorted(object_keys):
            if remaining_object_budget <= 0:
                all_objects_purged = False
                break
            journal = await db.scalar(
                select(PurgeJournal)
                .where(
                    PurgeJournal.workspace_id == workspace_id,
                    PurgeJournal.meeting_id == meeting_id,
                    PurgeJournal.artifact_class == "transient_audio",
                    PurgeJournal.object_key == object_key,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if journal is None:
                all_objects_purged = False
                await db.rollback()
                continue
            if journal.state == "purged" and object_key not in late_put_tombstone_keys:
                await db.rollback()
                continue
            if journal.state in {"purged", "superseded"}:
                journal.state = "pending"
                journal.attempt_count = 0
                journal.completed_at = None
                journal.next_retry_at = None
            if journal.next_retry_at is not None and journal.next_retry_at > now:
                all_objects_purged = False
                await db.rollback()
                continue
            journal.state = "deleting"
            journal.attempt_count += 1
            journal.started_at = now
            journal.next_retry_at = now + timedelta(seconds=STORAGE_CALL_TIMEOUT_SECONDS)
            journal_id = journal.id
            journal_attempt = journal.attempt_count
            remaining_object_budget -= 1
            await db.commit()
            try:
                object_existed = (
                    await _storage_object_exists(storage, object_key)
                    if object_key in late_put_tombstone_keys
                    else None
                )
                await _delete_storage_object(storage, object_key)
                if await _storage_object_exists(storage, object_key):
                    raise RuntimeError("transient_storage_delete_unverified")
            except Exception:
                await db.rollback()
                journal = await db.scalar(
                    select(PurgeJournal)
                    .where(PurgeJournal.id == journal_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                if (
                    journal is not None
                    and journal.state == "deleting"
                    and journal.attempt_count == journal_attempt
                ):
                    journal.state = "pending"
                    journal.next_retry_at = now + timedelta(minutes=1)
                    journal.safe_reason = "transient_object_delete_retry"
                    await db.commit()
                else:
                    await db.rollback()
                all_objects_purged = False
                continue
            journal = await db.scalar(
                select(PurgeJournal)
                .where(PurgeJournal.id == journal_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if (
                journal is None
                or journal.state != "deleting"
                or journal.attempt_count != journal_attempt
            ):
                await db.rollback()
                all_objects_purged = False
                continue
            if object_key in late_put_tombstone_keys and object_existed is not True:
                journal.state = "pending"
                journal.completed_at = None
                journal.next_retry_at = now + timedelta(minutes=1)
                journal.safe_reason = "transient_late_put_pending_recheck"
                await db.commit()
                all_objects_purged = False
                continue
            journal.state = "purged"
            journal.completed_at = now
            journal.next_retry_at = None
            journal.safe_reason = "transient_object_deleted_verified"
            await db.commit()
        if not all_objects_purged:
            if remaining_object_budget <= 0:
                break
            continue

        meeting = await db.scalar(
            select(Meeting)
            .where(Meeting.workspace_id == workspace_id, Meeting.id == meeting_id)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        if meeting is None:
            await db.rollback()
            continue
        workflows = list(
            await db.scalars(
                select(ProcessingWorkflow)
                .where(
                    ProcessingWorkflow.workspace_id == workspace_id,
                    ProcessingWorkflow.meeting_id == meeting_id,
                    ProcessingWorkflow.media_revision_id == media_revision_id,
                )
                .order_by(ProcessingWorkflow.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        attempts = list(
            await db.scalars(
                select(PlaybackNormalizationAttempt)
                .where(
                    PlaybackNormalizationAttempt.workspace_id == workspace_id,
                    PlaybackNormalizationAttempt.meeting_id == meeting_id,
                    PlaybackNormalizationAttempt.media_revision_id == media_revision_id,
                    or_(
                        PlaybackNormalizationAttempt.state != AttemptState.PURGED.value,
                        PlaybackNormalizationAttempt.cleaned_at.is_(None),
                    ),
                )
                .order_by(PlaybackNormalizationAttempt.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        artifacts = list(
            await db.scalars(
                select(TrackArtifact)
                .where(
                    TrackArtifact.workspace_id == workspace_id,
                    TrackArtifact.meeting_id == meeting_id,
                    TrackArtifact.media_revision_id == media_revision_id,
                    TrackArtifact.track_role.in_((*SOURCE_TRACK_ROLES, TrackRole.PLAYBACK.value)),
                    TrackArtifact.status.not_in({"purged", "deleted"}),
                )
                .order_by(TrackArtifact.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        temporary_objects = list(
            await db.scalars(
                select(TemporaryUploadObject)
                .join(UploadSession, TemporaryUploadObject.upload_session_id == UploadSession.id)
                .where(
                    TemporaryUploadObject.workspace_id == workspace_id,
                    TemporaryUploadObject.media_revision_id == media_revision_id,
                    UploadSession.workspace_id == workspace_id,
                    UploadSession.meeting_id == meeting_id,
                    UploadSession.media_revision_id == media_revision_id,
                    TemporaryUploadObject.cleanup_status != "purged",
                )
                .order_by(TemporaryUploadObject.id)
                .with_for_update(of=TemporaryUploadObject)
                .execution_options(populate_existing=True)
            )
        )
        journals_complete = all(
            journal.state == "purged"
            for journal in await db.scalars(
                select(PurgeJournal).where(
                    PurgeJournal.workspace_id == workspace_id,
                    PurgeJournal.meeting_id == meeting_id,
                    PurgeJournal.artifact_class == "transient_audio",
                    PurgeJournal.object_key.in_(object_keys or {""}),
                )
            )
        )
        if not journals_complete:
            await db.rollback()
            continue
        retry_fence_needed = False
        for attempt in attempts:
            current = AttemptState(attempt.state)
            if current in {
                AttemptState.LOCAL_PREPARING,
                AttemptState.UPLOADED,
                AttemptState.CLEANED,
            }:
                ensure_attempt_transition(current, AttemptState.CLEANUP_PENDING)
                attempt.state = AttemptState.CLEANUP_PENDING.value
                attempt.cleanup_reason = NormalizationReason.AUDIO_PURGED.value
                retry_fence_needed = True
                continue
            ensure_attempt_transition(current, AttemptState.PURGED)
            attempt.state = AttemptState.PURGED.value
            attempt.cleanup_reason = NormalizationReason.AUDIO_PURGED.value
            attempt.cleaned_at = attempt.cleaned_at or now
        for artifact in artifacts:
            artifact.status = "purged"
            if artifact.track_role in SOURCE_TRACK_ROLES:
                artifact.source_lifecycle_state = SourceLifecycleState.PURGED.value
                artifact.source_purged_at = now
                artifact.source_retention_purge_due_at = None
        for temporary_object in temporary_objects:
            temporary_object.cleanup_status = "purged"
            temporary_object.failure_reason = None
            temporary_object.last_error = None
        for workflow in workflows:
            if not workflow.archive_audio and not retry_fence_needed:
                workflow.transient_state = "purged"
                workflow.transient_purged_at = now
        if not retry_fence_needed and not any(
            workflow.status not in terminal_processing_statuses for workflow in workflows
        ):
            await release_processing_usage_reservation(
                db,
                workspace_id=workspace_id,
                media_revision_id=media_revision_id,
                meeting_id=meeting_id,
            )
        await db.commit()
        if retry_fence_needed:
            continue
        purged += 1
    return purged


async def reconcile_source_retention_purges(
    db: AsyncSession,
    *,
    storage: object | None,
    retention_period: timedelta | None,
    policy_version: str,
    backup_expiry_days: int | None,
    now: datetime | None = None,
    limit: int = 20,
) -> int:
    """Purge current/legacy transcription sources only after both gates.

    This worker is intentionally fail-closed: an absent/invalid policy, a
    missing gate, a deleted/deleting meeting or an invalid byte count leaves
    the source recoverable.  Accepted deletion is handled by the mandatory
    meeting purge path and therefore takes precedence over this scan.
    """

    if retention_period is None or retention_period <= timedelta(0) or not policy_version.strip():
        return 0
    now = now or datetime.now(UTC)
    candidate_ids = tuple(
        await db.scalars(
            select(TrackArtifact.id)
            .where(
                TrackArtifact.track_role.in_(tuple(SOURCE_TRACK_ROLES)),
                TrackArtifact.status.not_in({"purged", "deleted"}),
                TrackArtifact.source_lifecycle_state != SourceLifecycleState.PURGED.value,
            )
            .order_by(TrackArtifact.created_at.asc(), TrackArtifact.id.asc())
            .limit(max(1, min(limit, 100)))
        )
    )
    purged = 0
    for artifact_id in candidate_ids:
        meeting = await db.scalar(
            select(Meeting)
            .join(TrackArtifact, TrackArtifact.meeting_id == Meeting.id)
            .where(TrackArtifact.id == artifact_id)
            .with_for_update(of=Meeting)
            .execution_options(populate_existing=True)
        )
        if (
            meeting is None
            or meeting.deleted_at is not None
            or (meeting.deletion_state or DeletionState.NONE.value) != DeletionState.NONE.value
        ):
            continue
        candidate_artifact = await db.scalar(
            select(TrackArtifact).where(
                TrackArtifact.id == artifact_id,
                TrackArtifact.workspace_id == meeting.workspace_id,
            )
        )
        if candidate_artifact is None:
            continue
        # Match deletion/normalization lock order: Meeting -> job -> source
        # artifact.  This prevents a retention scan from racing publication.
        await db.scalars(
            select(PlaybackNormalizationJob)
            .where(
                PlaybackNormalizationJob.workspace_id == meeting.workspace_id,
                PlaybackNormalizationJob.meeting_id == meeting.id,
                (
                    PlaybackNormalizationJob.media_revision_id
                    == candidate_artifact.media_revision_id
                    if candidate_artifact.media_revision_id is not None
                    else PlaybackNormalizationJob.media_revision_id.is_(None)
                ),
            )
            .with_for_update()
        )
        artifact = await db.scalar(
            select(TrackArtifact)
            .where(
                TrackArtifact.id == artifact_id,
                TrackArtifact.workspace_id == meeting.workspace_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            artifact is None
            or artifact.track_role not in SOURCE_TRACK_ROLES
            or artifact.status in {"purged", "deleted"}
            or artifact.source_lifecycle_state == SourceLifecycleState.PURGED.value
        ):
            continue
        active_playback = await db.scalar(
            select(TrackArtifact.id).where(
                TrackArtifact.workspace_id == artifact.workspace_id,
                TrackArtifact.meeting_id == artifact.meeting_id,
                (
                    TrackArtifact.media_revision_id == artifact.media_revision_id
                    if artifact.media_revision_id is not None
                    else TrackArtifact.media_revision_id.is_(None)
                ),
                TrackArtifact.track_role == TrackRole.PLAYBACK.value,
                TrackArtifact.status == "stored",
                TrackArtifact.normalization_profile_version == CANONICAL_PLAYBACK_PROFILE,
                TrackArtifact.validated_at.is_not(None),
            )
        )
        if active_playback is None:
            artifact.source_playback_verified_at = None
            artifact.source_retention_policy_version = None
            artifact.source_retention_purge_due_at = None
            artifact.source_lifecycle_state = SourceLifecycleState.RECOVERABLE.value
            continue

        state, deadline = source_lifecycle_state_for_gates(
            transcript_imported_at=artifact.source_transcript_imported_at,
            playback_verified_at=artifact.source_playback_verified_at,
            now=now,
            retention_period=retention_period,
        )
        artifact.source_retention_policy_version = policy_version
        artifact.source_retention_purge_due_at = deadline
        if state is not SourceLifecycleState.PURGE_DUE:
            artifact.source_lifecycle_state = state.value
            continue
        if artifact.byte_length <= 0 or not artifact.storage_object_key:
            artifact.source_lifecycle_state = SourceLifecycleState.RECOVERABLE.value
            artifact.source_retention_purge_due_at = None
            continue

        artifact.source_lifecycle_state = SourceLifecycleState.PURGE_PENDING.value
        journal = await db.scalar(
            select(PurgeJournal)
            .where(
                PurgeJournal.workspace_id == artifact.workspace_id,
                PurgeJournal.meeting_id == artifact.meeting_id,
                PurgeJournal.artifact_class == "source_retention",
                PurgeJournal.object_key == artifact.storage_object_key,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if journal is None:
            journal = PurgeJournal(
                workspace_id=artifact.workspace_id,
                meeting_id=artifact.meeting_id,
                artifact_class="source_retention",
                object_key=artifact.storage_object_key,
                state="pending",
                safe_reason="source_retention_gate_passed",
            )
            db.add(journal)
            await _flush_or_fail_closed(db)
        journal.metadata_json = source_cogs_evidence(
            byte_length=artifact.byte_length,
            policy_version=policy_version,
            backup_expiry_days=backup_expiry_days,
        )
        if journal.state == "terminal_unknown":
            continue
        if journal.state == "purged":
            journal.state = "pending"
            journal.attempt_count = 0
            journal.completed_at = None
            journal.next_retry_at = None
            journal.safe_reason = "source_object_reintroduced"
        if (
            journal.state == "retryable_failed"
            and journal.next_retry_at is not None
            and journal.next_retry_at > now
        ):
            continue
        _ensure_storage_delete_capability(storage)
        journal.state = "deleting"
        journal.attempt_count += 1
        journal.started_at = now
        journal.next_retry_at = now + timedelta(seconds=STORAGE_CALL_TIMEOUT_SECONDS)
        await _flush_or_fail_closed(db)
        try:
            if await _storage_object_exists(storage, artifact.storage_object_key):
                await _delete_storage_object(storage, artifact.storage_object_key)
                if await _storage_object_exists(storage, artifact.storage_object_key):
                    raise RuntimeError("source_storage_delete_unverified")
        except Exception:
            journal.state = "retryable_failed"
            journal.safe_reason = "source_storage_delete_failed"
            journal.next_retry_at = now + timedelta(
                seconds=min(3600, 15 * (2 ** min(journal.attempt_count - 1, 8)))
            )
            artifact.source_lifecycle_state = SourceLifecycleState.PURGE_PENDING.value
            await db.commit()
            continue
        journal.state = "purged"
        journal.completed_at = now
        journal.next_retry_at = None
        journal.safe_reason = "source_object_deleted_verified"
        artifact.status = "purged"
        artifact.source_lifecycle_state = SourceLifecycleState.PURGED.value
        artifact.source_purged_at = now
        artifact.source_retention_purge_due_at = None
        await db.commit()
        purged += 1
    # Persist deadline recomputation/reopen and terminal-journal evidence even
    # when no object was eligible for physical deletion in this scan.
    await db.commit()
    return purged


async def _object_key_referenced(
    db: AsyncSession,
    *,
    meeting: Meeting,
    object_key: str,
) -> bool:
    """Check authoritative DB ownership before deleting an orphan key."""
    statements = (
        select(TrackArtifact.id).where(
            TrackArtifact.workspace_id == meeting.workspace_id,
            TrackArtifact.meeting_id == meeting.id,
            TrackArtifact.storage_object_key == object_key,
            TrackArtifact.status.not_in({"purged", "deleted"}),
        ),
        select(PlaybackNormalizationAttempt.id).where(
            PlaybackNormalizationAttempt.workspace_id == meeting.workspace_id,
            PlaybackNormalizationAttempt.meeting_id == meeting.id,
            PlaybackNormalizationAttempt.storage_object_key == object_key,
            PlaybackNormalizationAttempt.state.in_({"local_preparing", "uploaded", "published"}),
        ),
        select(TemporaryUploadObject.id)
        .join(UploadSession, TemporaryUploadObject.upload_session_id == UploadSession.id)
        .where(
            TemporaryUploadObject.workspace_id == meeting.workspace_id,
            UploadSession.meeting_id == meeting.id,
            TemporaryUploadObject.storage_object_key == object_key,
            TemporaryUploadObject.cleanup_status.not_in({"orphaned", "purged"}),
        ),
        select(UploadPart.id)
        .join(UploadSession, UploadPart.upload_session_id == UploadSession.id)
        .where(
            UploadSession.workspace_id == meeting.workspace_id,
            UploadSession.meeting_id == meeting.id,
            UploadPart.storage_object_key == object_key,
            UploadPart.status == "accepted",
            UploadSession.status.in_({"pending", "uploading"}),
        ),
    )
    for statement in statements:
        if await db.scalar(statement) is not None:
            return True
    return False


async def _reconcile_orphan_purge_journals(
    db: AsyncSession,
    *,
    meeting: Meeting,
    storage: object | None,
    limit: int = 20,
) -> bool:
    """Retry cleanup intents without rerunning a deletion lifecycle."""
    now = datetime.now(UTC)
    rows = list(
        (
            await db.scalars(
                select(PurgeJournal)
                .where(
                    PurgeJournal.workspace_id == meeting.workspace_id,
                    PurgeJournal.meeting_id == meeting.id,
                    PurgeJournal.artifact_class != "transient_audio",
                    PurgeJournal.state.in_({"pending", "deleting", "retryable_failed"}),
                    PurgeJournal.attempt_count < MAX_PURGE_JOURNAL_ATTEMPTS,
                    PurgeJournal.next_retry_at.is_(None) | (PurgeJournal.next_retry_at <= now),
                )
                .order_by(PurgeJournal.created_at.asc(), PurgeJournal.id.asc())
                .limit(limit)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
    )
    if not rows:
        await db.rollback()
        return True

    snapshots: list[tuple[UUID, str, int]] = []
    blocked_by_reference = False
    for row in rows:
        if await _object_key_referenced(db, meeting=meeting, object_key=row.object_key):
            if meeting.deleted_at is None:
                row.state = "superseded"
                row.safe_reason = "object_reconciled_as_referenced"
                row.completed_at = now
                row.next_retry_at = None
            else:
                blocked_by_reference = True
                row.state = "retryable_failed"
                row.safe_reason = "object_reference_requires_full_deletion_retry"
                row.next_retry_at = now + timedelta(seconds=15)
            continue
        row.state = "deleting"
        row.attempt_count += 1
        row.started_at = now
        row.next_retry_at = now + timedelta(seconds=STORAGE_CALL_TIMEOUT_SECONDS)
        snapshots.append((row.id, row.object_key, row.attempt_count))
    await _flush_or_fail_closed(db)
    await db.commit()

    outcomes: dict[UUID, tuple[int, bool]] = {}
    for row_id, object_key, attempt_count in snapshots:
        try:
            if await _storage_object_exists(storage, object_key):
                await _delete_storage_object(storage, object_key)
                if await _storage_object_exists(storage, object_key):
                    raise RuntimeError("storage_delete_unverified")
            outcomes[row_id] = (attempt_count, True)
        except Exception:
            outcomes[row_id] = (attempt_count, False)

    locked_meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.workspace_id == meeting.workspace_id, Meeting.id == meeting.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locked_meeting is None:
        await db.rollback()
        return False
    current_rows = {
        row.id: row
        for row in (
            await db.scalars(
                select(PurgeJournal)
                .where(PurgeJournal.id.in_(tuple(outcomes)))
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
    }
    failures = False
    stale_claim = False
    for row_id, (attempt_count, deleted) in outcomes.items():
        row = current_rows.get(row_id)
        if row is None or row.state != "deleting" or row.attempt_count != attempt_count:
            stale_claim = True
            continue
        if deleted:
            row.state = "purged"
            row.completed_at = datetime.now(UTC)
            row.safe_reason = "object_deleted_verified"
            row.next_retry_at = None
            continue
        failures = True
        if row.attempt_count >= MAX_PURGE_JOURNAL_ATTEMPTS:
            row.state = "terminal_unknown"
            row.safe_reason = "storage_delete_terminal_unknown"
            row.next_retry_at = None
        else:
            row.state = "retryable_failed"
            row.safe_reason = "storage_delete_failed"
            retry_delay_seconds = min(3600, 15 * (2 ** min(row.attempt_count - 1, 8)))
            row.next_retry_at = datetime.now(UTC) + timedelta(seconds=retry_delay_seconds)

    report = await db.scalar(
        select(MeetingDeletionReport)
        .where(
            MeetingDeletionReport.workspace_id == locked_meeting.workspace_id,
            MeetingDeletionReport.meeting_id == locked_meeting.id,
        )
        .order_by(desc(MeetingDeletionReport.updated_at))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        report is not None
        and (failures or blocked_by_reference)
        and report.overall_state
        not in {
            DeletionState.DELETING.value,
            DeletionState.RETRYABLE_FAILED.value,
        }
    ):
        report.overall_state = DeletionState.RETRYABLE_FAILED.value
        report.summary_label = "Deletion needs retry"
        report.updated_at = datetime.now(UTC)
        deletion_request = await db.scalar(
            select(MeetingDeletionRequest)
            .where(MeetingDeletionRequest.id == report.deletion_request_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if deletion_request is not None:
            deletion_request.state = DeletionState.RETRYABLE_FAILED.value
            deletion_request.failure_reason = "orphan_cleanup_pending"
            deletion_request.failed_at = datetime.now(UTC)
        locked_meeting.deletion_state = DeletionState.RETRYABLE_FAILED.value
    await db.commit()
    return not failures and not blocked_by_reference and not stale_claim


async def retry_orphan_purge_journals(
    db: AsyncSession,
    *,
    meeting: Meeting,
    storage: object | None,
    limit: int = 20,
) -> dict[str, object]:
    """Reset bounded orphan failures only after an explicit operator action."""
    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")
    locked_meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.workspace_id == meeting.workspace_id, Meeting.id == meeting.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locked_meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    rows = list(
        (
            await db.scalars(
                select(PurgeJournal)
                .where(
                    PurgeJournal.workspace_id == locked_meeting.workspace_id,
                    PurgeJournal.meeting_id == locked_meeting.id,
                    PurgeJournal.deletion_request_id.is_(None),
                    PurgeJournal.state == "terminal_unknown",
                )
                .order_by(PurgeJournal.created_at.asc(), PurgeJournal.id.asc())
                .limit(limit)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
    )
    if not rows:
        await db.rollback()
        return {"reset_count": 0, "converged": True}
    retry_started_at = datetime.now(UTC)
    for row in rows:
        row.state = "retryable_failed"
        row.attempt_count = 0
        row.safe_reason = "operator_retry_requested"
        row.next_retry_at = retry_started_at
        row.started_at = None
        row.completed_at = None
    await db.commit()
    converged = await _reconcile_orphan_purge_journals(
        db,
        meeting=locked_meeting,
        storage=storage,
        limit=limit,
    )
    return {"reset_count": len(rows), "converged": converged}


async def deletion_report_response(
    db: AsyncSession,
    *,
    meeting: Meeting,
) -> DeletionVerificationReport:
    report = await db.scalar(
        select(MeetingDeletionReport)
        .where(MeetingDeletionReport.workspace_id == meeting.workspace_id)
        .where(MeetingDeletionReport.meeting_id == meeting.id)
        .order_by(desc(MeetingDeletionReport.updated_at))
    )
    if report is None:
        raise ProblemDetail(
            status=404, code="deletion_report_not_found", title="Deletion report not found"
        )
    expired = await reconcile_expired_local_purge_tasks(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        deletion_request_id=report.deletion_request_id,
    )
    if expired:
        await db.commit()
        report = await db.scalar(
            select(MeetingDeletionReport)
            .where(MeetingDeletionReport.workspace_id == meeting.workspace_id)
            .where(MeetingDeletionReport.meeting_id == meeting.id)
            .where(MeetingDeletionReport.deletion_request_id == report.deletion_request_id)
        )
        if report is None:
            raise ProblemDetail(
                status=404, code="deletion_report_not_found", title="Deletion report not found"
            )
    artifact_states = (
        await db.scalars(
            select(MeetingDeletionArtifactState)
            .where(MeetingDeletionArtifactState.workspace_id == meeting.workspace_id)
            .where(MeetingDeletionArtifactState.meeting_id == meeting.id)
            .where(MeetingDeletionArtifactState.deletion_request_id == report.deletion_request_id)
            .order_by(MeetingDeletionArtifactState.artifact_class.asc())
        )
    ).all()
    local_tasks = (
        await db.scalars(
            select(LocalPurgeTaskModel)
            .where(LocalPurgeTaskModel.workspace_id == meeting.workspace_id)
            .where(LocalPurgeTaskModel.meeting_id == meeting.id)
            .where(LocalPurgeTaskModel.deletion_request_id == report.deletion_request_id)
            .order_by(LocalPurgeTaskModel.created_at.asc())
        )
    ).all()
    deletion_request = await db.get(MeetingDeletionRequest, report.deletion_request_id)
    activity_rows = []
    if (
        deletion_request is not None
        and deletion_request.request_source == DeletionRequestSource.RETENTION_JOB.value
    ):
        activity_rows.append(
            retention_policy_activity_row(policy_snapshot_id=deletion_request.policy_snapshot_id)
        )
    lifecycle_events = (
        await db.scalars(
            select(MeetingLifecycleAuditEvent)
            .where(MeetingLifecycleAuditEvent.workspace_id == meeting.workspace_id)
            .where(MeetingLifecycleAuditEvent.meeting_id == meeting.id)
            .where(MeetingLifecycleAuditEvent.deletion_request_id == report.deletion_request_id)
            .order_by(MeetingLifecycleAuditEvent.created_at.asc())
        )
    ).all()
    return assemble_verification_report(
        meeting_id=meeting.id,
        request_id=report.deletion_request_id,
        overall_state=DeletionState(report.overall_state),
        bounded_copy=report.bounded_copy,
        artifact_states=[_artifact_row_from_model(row) for row in artifact_states] + activity_rows,
        local_purge=[_local_purge_task_from_model(task) for task in local_tasks],
        activity=[
            lifecycle_activity_item(
                event_id=event.id,
                event_type=event.event_type,
                actor_user_id=event.actor_user_id,
                device_id=event.device_id,
                outcome=LifecycleAuditOutcome(event.outcome),
                safe_reason=event.safe_reason,
                created_at=event.created_at,
            )
            for event in lifecycle_events
        ],
        generated_at=report.generated_at,
    )


def deletion_retry_guidance(state: DeletionState) -> str:
    if state == DeletionState.RETRYABLE_FAILED:
        return RETRY_OPERATOR_GUIDANCE
    return RETRY_UNAVAILABLE_GUIDANCE


async def _backup_expiry_days_for_retry(
    db: AsyncSession,
    *,
    deletion_request: MeetingDeletionRequest,
    report: MeetingDeletionReport,
) -> int | None:
    """Keep the original retention snapshot when rebuilding a retry report."""
    if deletion_request.policy_snapshot_id is not None:
        snapshot = await db.scalar(
            select(RetentionPolicySnapshot)
            .where(
                RetentionPolicySnapshot.id == deletion_request.policy_snapshot_id,
                RetentionPolicySnapshot.workspace_id == deletion_request.workspace_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if snapshot is not None:
            return snapshot.backup_expiry_days
    for artifact in report.artifact_summary_json or []:
        if artifact.get("artifact_class") != DeletionArtifactClass.BACKUP.value:
            continue
        safe_reason = str(artifact.get("safe_reason") or "")
        prefix = "backup_expiry_days:"
        if safe_reason.startswith(prefix):
            raw_days = safe_reason.removeprefix(prefix)
            try:
                return int(raw_days)
            except ValueError:
                break
        if safe_reason == "backup_expiry_policy_missing":
            return None
    return DEFAULT_BACKUP_EXPIRY_DAYS


async def _flush_or_fail_closed(db: AsyncSession) -> None:
    try:
        await db.flush()
    except SQLAlchemyError as exc:
        await db.rollback()
        raise ProblemDetail(
            status=503,
            code="deletion_audit_unavailable",
            title="Deletion audit unavailable",
            detail="Deletion failed closed before destructive action because lifecycle evidence could not be persisted.",
        ) from exc


async def _purge_server_controlled_content(
    db: AsyncSession,
    *,
    meeting: Meeting,
    storage: object | None,
    deletion_request_id: UUID | None = None,
) -> _ServerPurgeResult:
    result = _ServerPurgeResult()
    now = datetime.now(UTC)

    # Lifecycle lock order is Meeting -> normalization job -> attempt ->
    # artifact.  Normalization publication/recovery uses the same order; do
    # not move the artifact query ahead of the job locks.
    normalization_jobs = (
        await db.scalars(
            select(PlaybackNormalizationJob)
            .where(
                PlaybackNormalizationJob.workspace_id == meeting.workspace_id,
                PlaybackNormalizationJob.meeting_id == meeting.id,
            )
            .order_by(PlaybackNormalizationJob.created_at, PlaybackNormalizationJob.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    if normalization_jobs:
        result.materialized_classes.add(DeletionArtifactClass.NORMALIZATION_JOB)
    if any(job.backfill_run_id is not None for job in normalization_jobs):
        result.materialized_classes.add(DeletionArtifactClass.NORMALIZATION_BACKFILL)

    normalization_attempts = (
        await db.scalars(
            select(PlaybackNormalizationAttempt)
            .where(
                PlaybackNormalizationAttempt.workspace_id == meeting.workspace_id,
                PlaybackNormalizationAttempt.meeting_id == meeting.id,
            )
            .order_by(
                PlaybackNormalizationAttempt.attempt_number,
                PlaybackNormalizationAttempt.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    if normalization_attempts:
        result.materialized_classes.add(DeletionArtifactClass.NORMALIZATION_ATTEMPT_TEMP)

    artifacts = (
        await db.scalars(
            select(TrackArtifact)
            .where(TrackArtifact.workspace_id == meeting.workspace_id)
            .where(TrackArtifact.meeting_id == meeting.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    if artifacts:
        result.materialized_classes.add(DeletionArtifactClass.AUDIO_OBJECT)
    if any(
        artifact.track_role == "playback"
        and artifact.status in {"candidate", "stored"}
        and artifact.validated_at is None
        for artifact in artifacts
    ):
        result.materialized_classes.add(DeletionArtifactClass.PLAYBACK_CANDIDATE)
    if any(
        artifact.track_role == "playback"
        and artifact.status in {"stored", "deleted"}
        and (artifact.validated_at is not None or artifact.status == "deleted")
        for artifact in artifacts
    ):
        result.materialized_classes.add(DeletionArtifactClass.PLAYBACK_CANONICAL)

    temporary_objects = (
        await db.scalars(
            select(TemporaryUploadObject)
            .join(UploadSession, TemporaryUploadObject.upload_session_id == UploadSession.id)
            .where(TemporaryUploadObject.workspace_id == meeting.workspace_id)
            .where(UploadSession.workspace_id == meeting.workspace_id)
            .where(UploadSession.meeting_id == meeting.id)
            .with_for_update()
        )
    ).all()
    upload_parts = (
        await db.scalars(
            select(UploadPart)
            .join(UploadSession, UploadPart.upload_session_id == UploadSession.id)
            .where(UploadSession.workspace_id == meeting.workspace_id)
            .where(UploadSession.meeting_id == meeting.id)
            .where(UploadPart.status == "accepted")
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()

    live_object_keys = {
        *(artifact.storage_object_key for artifact in artifacts),
        *(attempt.storage_object_key for attempt in normalization_attempts),
        *(temporary_object.storage_object_key for temporary_object in temporary_objects),
        *(part.storage_object_key for part in upload_parts),
    }
    journal_rows = (
        await db.scalars(
            select(PurgeJournal)
            .where(
                PurgeJournal.workspace_id == meeting.workspace_id,
                PurgeJournal.meeting_id == meeting.id,
                PurgeJournal.state.not_in({"purged", "superseded"}),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    object_keys = live_object_keys | {journal.object_key for journal in journal_rows}
    existing_journal = {
        row.object_key: row
        for row in (
            await db.scalars(
                select(PurgeJournal)
                .where(
                    PurgeJournal.workspace_id == meeting.workspace_id,
                    PurgeJournal.meeting_id == meeting.id,
                    PurgeJournal.artifact_class == "object_store",
                    PurgeJournal.object_key.in_(object_keys or {""}),
                )
                .with_for_update()
            )
        ).all()
    }
    for object_key in sorted(object_keys):
        if object_key not in existing_journal:
            db.add(
                PurgeJournal(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    deletion_request_id=deletion_request_id,
                    artifact_class="object_store",
                    object_key=object_key,
                    state="pending",
                )
            )
    await _flush_or_fail_closed(db)
    object_presence = {
        object_key: await _storage_object_exists(storage, object_key)
        for object_key in sorted(object_keys)
    }
    for object_key in sorted(object_keys):
        journal = existing_journal.get(object_key)
        if journal is None:
            journal = await db.scalar(
                select(PurgeJournal).where(
                    PurgeJournal.workspace_id == meeting.workspace_id,
                    PurgeJournal.meeting_id == meeting.id,
                    PurgeJournal.artifact_class == "object_store",
                    PurgeJournal.object_key == object_key,
                )
            )
        if journal is None:
            raise ProblemDetail(
                status=503,
                code="deletion_journal_unavailable",
                title="Deletion journal unavailable",
            )
        if journal.state == "terminal_unknown":
            raise ProblemDetail(
                status=503,
                code="deletion_purge_terminal_unknown",
                title="Deletion requires operator retry",
                detail="An object could not be verified as deleted after bounded retries.",
            )
        if journal.state in {"purged", "superseded"}:
            if object_key not in live_object_keys:
                continue
            # The deterministic key was materialized again after an earlier
            # cleanup. Reopen the journal so the current authoritative object
            # is covered by this deletion request.
            journal.state = "pending"
            journal.attempt_count = 0
            journal.completed_at = None
            journal.safe_reason = "object_reintroduced"
            journal.next_retry_at = None
        if not object_presence.get(object_key, False):
            journal.state = "purged"
            journal.completed_at = now
            journal.safe_reason = "object_already_absent"
            journal.next_retry_at = None
            continue
        journal.state = "deleting"
        journal.attempt_count += 1
        journal.started_at = now
        await _flush_or_fail_closed(db)
        try:
            await _delete_storage_object(storage, object_key)
            if await _storage_object_exists(storage, object_key):
                raise RuntimeError("storage_delete_unverified")
        except Exception:
            if journal.attempt_count >= MAX_PURGE_JOURNAL_ATTEMPTS:
                journal.state = "terminal_unknown"
                journal.safe_reason = "storage_delete_terminal_unknown"
                journal.next_retry_at = None
            else:
                journal.state = "retryable_failed"
                journal.safe_reason = "storage_delete_failed"
                retry_delay_seconds = min(3600, 15 * (2 ** min(journal.attempt_count - 1, 8)))
                journal.next_retry_at = datetime.now(UTC) + timedelta(seconds=retry_delay_seconds)
            await _flush_or_fail_closed(db)
            raise
        journal.state = "purged"
        journal.completed_at = now
        journal.safe_reason = (
            "object_already_absent"
            if not object_presence.get(object_key, False)
            else "object_deleted_verified"
        )
        journal.next_retry_at = None

    for artifact in artifacts:
        artifact.status = "purged"
        if artifact.track_role in SOURCE_TRACK_ROLES:
            artifact.source_lifecycle_state = SourceLifecycleState.PURGED.value
            artifact.source_purged_at = now
            artifact.source_retention_purge_due_at = None
        if artifact.track_role == "playback":
            artifact.normalization_profile_version = None
            artifact.validated_at = None
            artifact.derivation_kind = None
            artifact.source_fingerprint_sha256 = None
            artifact.validation_version = None
    if artifacts:
        result.purged_classes.add(DeletionArtifactClass.AUDIO_OBJECT)
    if DeletionArtifactClass.PLAYBACK_CANDIDATE in result.materialized_classes:
        result.purged_classes.add(DeletionArtifactClass.PLAYBACK_CANDIDATE)
    if DeletionArtifactClass.PLAYBACK_CANONICAL in result.materialized_classes:
        result.purged_classes.add(DeletionArtifactClass.PLAYBACK_CANONICAL)

    cancellable_states = {
        JobState.QUEUED.value,
        JobState.RUNNING.value,
        JobState.PUBLISHING.value,
        JobState.RETRY_WAIT.value,
        JobState.READY.value,
    }
    for job in normalization_jobs:
        if job.state in cancellable_states:
            ensure_job_transition(
                JobState(job.state),
                JobState.CANCELLED,
                reason_code=NormalizationReason.MEETING_DELETING,
            )
            job.state = JobState.CANCELLED.value
            job.reason_code = NormalizationReason.MEETING_DELETING.value
            job.cancelled_at = now
            add_normalization_audit_event(
                db,
                workspace_id=job.workspace_id,
                meeting_id=job.meeting_id,
                media_revision_id=job.media_revision_id,
                actor_user_id=job.requested_by_user_id,
                device_id=job.source_device_id,
                event_type="playback_normalization_cancelled",
                metadata={
                    "reason_code": NormalizationReason.MEETING_DELETING.value,
                    "state": JobState.CANCELLED.value,
                },
                created_at=now,
            )
        job.next_attempt_at = None
        job.lease_owner_sha256 = None
        job.lease_expires_at = None
        job.workflow_run_id = None
        job.canonical_track_artifact_id = None
        job.ready_at = None
        job.last_heartbeat_at = now

    active_attempt_states = {
        AttemptState.LOCAL_PREPARING.value,
        AttemptState.UPLOADED.value,
        AttemptState.PUBLISHED.value,
        AttemptState.CLEANUP_PENDING.value,
    }
    for attempt in normalization_attempts:
        if attempt.state in active_attempt_states:
            current_attempt_state = AttemptState(attempt.state)
            missing_object_needs_recheck = (
                current_attempt_state
                in {
                    AttemptState.LOCAL_PREPARING,
                    AttemptState.CLEANUP_PENDING,
                }
                and not object_presence[attempt.storage_object_key]
            )
            if current_attempt_state in {
                AttemptState.LOCAL_PREPARING,
                AttemptState.UPLOADED,
            }:
                ensure_attempt_transition(
                    current_attempt_state,
                    AttemptState.CLEANUP_PENDING,
                )
                current_attempt_state = AttemptState.CLEANUP_PENDING
            ensure_attempt_transition(current_attempt_state, AttemptState.PURGED)
            attempt.state = AttemptState.PURGED.value
            attempt.cleanup_reason = NormalizationReason.MEETING_DELETING.value
            attempt.cleaned_at = None if missing_object_needs_recheck else attempt.cleaned_at or now
            add_normalization_audit_event(
                db,
                workspace_id=attempt.workspace_id,
                meeting_id=attempt.meeting_id,
                media_revision_id=attempt.media_revision_id,
                event_type="playback_normalization_temp_cleaned",
                metadata={
                    "cleanup_result": (
                        "deleted"
                        if object_presence[attempt.storage_object_key]
                        else (
                            "already_missing_pending_recheck"
                            if missing_object_needs_recheck
                            else "already_missing"
                        )
                    )
                },
                created_at=now,
            )
    if normalization_attempts:
        result.purged_classes.add(DeletionArtifactClass.NORMALIZATION_ATTEMPT_TEMP)

    for temporary_object in temporary_objects:
        temporary_object.cleanup_status = "purged"
        temporary_object.failure_reason = None
        temporary_object.last_error = None
    if temporary_objects:
        result.materialized_classes.add(DeletionArtifactClass.UPLOAD_TEMP)
        result.purged_classes.add(DeletionArtifactClass.UPLOAD_TEMP)

    transcript_delete = await db.execute(
        delete(TranscriptSegment)
        .where(TranscriptSegment.workspace_id == meeting.workspace_id)
        .where(TranscriptSegment.meeting_id == meeting.id)
    )
    if transcript_delete.rowcount:
        result.materialized_classes.add(DeletionArtifactClass.TRANSCRIPT)
        result.purged_classes.add(DeletionArtifactClass.TRANSCRIPT)

    diarization_delete = await db.execute(
        delete(DiarizationSegment)
        .where(DiarizationSegment.workspace_id == meeting.workspace_id)
        .where(DiarizationSegment.meeting_id == meeting.id)
    )
    if diarization_delete.rowcount:
        result.materialized_classes.add(DeletionArtifactClass.DIARIZATION)
        result.purged_classes.add(DeletionArtifactClass.DIARIZATION)

    speaker_name_delete = await db.execute(
        delete(MeetingSpeakerName)
        .where(MeetingSpeakerName.workspace_id == meeting.workspace_id)
        .where(MeetingSpeakerName.meeting_id == meeting.id)
    )
    if speaker_name_delete.rowcount:
        result.materialized_classes.add(DeletionArtifactClass.DIARIZATION)
        result.purged_classes.add(DeletionArtifactClass.DIARIZATION)

    processing_results = (
        await db.scalars(
            select(ProcessingResult)
            .where(ProcessingResult.workspace_id == meeting.workspace_id)
            .where(ProcessingResult.meeting_id == meeting.id)
        )
    ).all()
    for processing_result in processing_results:
        if DeletionArtifactClass.TRANSCRIPT in result.purged_classes:
            processing_result.transcript_status = "purged"
            processing_result.segment_count = 0
        if DeletionArtifactClass.DIARIZATION in result.purged_classes:
            processing_result.diarization_status = "purged"
            processing_result.diarization_segment_count = 0

    outcome_sets = (
        await db.scalars(
            select(MeetingOutcomeSet)
            .where(MeetingOutcomeSet.workspace_id == meeting.workspace_id)
            .where(MeetingOutcomeSet.meeting_id == meeting.id)
        )
    ).all()
    generation_attempts = (
        await db.scalars(
            select(MeetingOutcomeGenerationAttempt)
            .where(MeetingOutcomeGenerationAttempt.workspace_id == meeting.workspace_id)
            .where(MeetingOutcomeGenerationAttempt.meeting_id == meeting.id)
        )
    ).all()
    if outcome_sets or generation_attempts:
        await _purge_meeting_outcomes(db, meeting=meeting)
    if outcome_sets:
        result.materialized_classes.add(DeletionArtifactClass.NOTES_SUMMARY)
        result.purged_classes.add(DeletionArtifactClass.NOTES_SUMMARY)
    if generation_attempts:
        result.materialized_classes.add(DeletionArtifactClass.OUTCOME_ATTEMPT)

    export_packages = (
        await db.scalars(
            select(ExportPackage)
            .where(ExportPackage.workspace_id == meeting.workspace_id)
            .where(ExportPackage.meeting_id == meeting.id)
        )
    ).all()
    if export_packages:
        await db.execute(
            delete(ExportPackage)
            .where(ExportPackage.workspace_id == meeting.workspace_id)
            .where(ExportPackage.meeting_id == meeting.id)
        )
        result.materialized_classes.add(DeletionArtifactClass.EXPORT_PACKAGE)
        result.purged_classes.add(DeletionArtifactClass.EXPORT_PACKAGE)

    share_grants = (
        await db.scalars(
            select(MeetingShareGrant)
            .where(MeetingShareGrant.workspace_id == meeting.workspace_id)
            .where(MeetingShareGrant.meeting_id == meeting.id)
        )
    ).all()
    if share_grants:
        await db.execute(
            delete(MeetingShareGrant)
            .where(MeetingShareGrant.workspace_id == meeting.workspace_id)
            .where(MeetingShareGrant.meeting_id == meeting.id)
        )
        result.materialized_classes.add(DeletionArtifactClass.SHARE_GRANT)
        result.purged_classes.add(DeletionArtifactClass.SHARE_GRANT)

    share_invitations = (
        await db.scalars(
            select(MeetingShareInvitation)
            .where(MeetingShareInvitation.workspace_id == meeting.workspace_id)
            .where(MeetingShareInvitation.meeting_id == meeting.id)
        )
    ).all()
    if share_invitations:
        await db.execute(
            delete(MeetingShareInvitation)
            .where(MeetingShareInvitation.workspace_id == meeting.workspace_id)
            .where(MeetingShareInvitation.meeting_id == meeting.id)
        )
        result.materialized_classes.add(DeletionArtifactClass.SHARE_INVITATION)
        result.purged_classes.add(DeletionArtifactClass.SHARE_INVITATION)

    return result


async def _delete_storage_object(storage: object | None, object_key: str) -> None:
    if storage is None:
        raise ProblemDetail(
            status=503,
            code="deletion_storage_unavailable",
            title="Deletion storage unavailable",
            detail="Deletion failed closed because server-owned media could not be purged.",
        )
    delete_object_async = getattr(storage, "delete_object_async", None)
    if delete_object_async is not None:
        await asyncio.wait_for(
            delete_object_async(object_key), timeout=STORAGE_CALL_TIMEOUT_SECONDS
        )
        return
    delete_object = getattr(storage, "delete_object", None)
    if delete_object is None:
        raise ProblemDetail(
            status=503,
            code="deletion_storage_unavailable",
            title="Deletion storage unavailable",
            detail="Deletion failed closed because server-owned media could not be purged.",
        )
    await asyncio.wait_for(
        asyncio.to_thread(delete_object, object_key), timeout=STORAGE_CALL_TIMEOUT_SECONDS
    )


def _ensure_storage_delete_capability(storage: object | None) -> None:
    """Fail before publishing a tombstone when the adapter cannot delete objects."""
    if storage is None or not any(
        callable(getattr(storage, attribute, None))
        for attribute in ("delete_object_async", "delete_object")
    ):
        raise ProblemDetail(
            status=503,
            code="deletion_storage_unavailable",
            title="Deletion storage unavailable",
            detail="Deletion failed closed because server-owned media could not be purged.",
        )


async def _storage_object_exists(storage: object | None, object_key: str) -> bool:
    if storage is None:
        raise ProblemDetail(
            status=503,
            code="deletion_storage_unavailable",
            title="Deletion storage unavailable",
            detail="Deletion failed closed because server-owned media could not be verified.",
        )
    try:
        object_exists_async = getattr(storage, "object_exists_async", None)
        if object_exists_async is not None:
            return bool(
                await asyncio.wait_for(
                    object_exists_async(object_key), timeout=STORAGE_CALL_TIMEOUT_SECONDS
                )
            )
        object_exists = getattr(storage, "object_exists", None)
        if object_exists is not None:
            return bool(
                await asyncio.wait_for(
                    asyncio.to_thread(object_exists, object_key),
                    timeout=STORAGE_CALL_TIMEOUT_SECONDS,
                )
            )
    except Exception as exc:
        raise ProblemDetail(
            status=503,
            code="deletion_storage_unavailable",
            title="Deletion storage unavailable",
            detail="Deletion failed closed because server-owned media could not be verified.",
        ) from exc
    raise ProblemDetail(
        status=503,
        code="deletion_storage_unavailable",
        title="Deletion storage unavailable",
        detail="Deletion failed closed because server-owned media could not be verified.",
    )


async def _purge_meeting_outcomes(db: AsyncSession, *, meeting: Meeting) -> None:
    outcome_sets = (
        await db.scalars(
            select(MeetingOutcomeSet)
            .where(MeetingOutcomeSet.workspace_id == meeting.workspace_id)
            .where(MeetingOutcomeSet.meeting_id == meeting.id)
        )
    ).all()
    for outcome_set in outcome_sets:
        outcome_set.lifecycle_state = OutcomeLifecycleState.DELETED.value
        outcome_set.failure_reason = "meeting_deleted"
        outcome_set.content_hash = None

    outcome_items = (
        await db.scalars(
            select(MeetingOutcomeItem)
            .where(MeetingOutcomeItem.workspace_id == meeting.workspace_id)
            .where(MeetingOutcomeItem.meeting_id == meeting.id)
        )
    ).all()
    for item in outcome_items:
        item.state = "purged"
        item.text = None
        item.owner_text = None
        item.due_date_text = None
        item.source_refs_json = []
    generation_attempts = (
        await db.scalars(
            select(MeetingOutcomeGenerationAttempt)
            .where(MeetingOutcomeGenerationAttempt.workspace_id == meeting.workspace_id)
            .where(MeetingOutcomeGenerationAttempt.meeting_id == meeting.id)
        )
    ).all()
    for attempt in generation_attempts:
        attempt.status = "cancelled"
        attempt.failure_code = "meeting_deleted"
        # Prompt snapshots are template/provider provenance (not meeting text)
        # and are required to deliver an already-completed GenerationCall to
        # observability after deletion. Keep them immutable for that handoff.
        attempt.metadata_json = {"purged_for_deletion": True}


def _initial_artifact_states(
    meeting: Meeting,
    deletion_request_id: UUID,
    *,
    local_purge_requested: bool = False,
    local_purge_state: DeletionArtifactState | None = None,
    local_purge_reason: str | None = None,
    backup_expiry_days: int | None = DEFAULT_BACKUP_EXPIRY_DAYS,
    post_egress_safe_reason: str = "Delivered copies are outside GRAF control",
    outcomes_materialized: bool = False,
    purged_artifact_classes: set[DeletionArtifactClass] | None = None,
    materialized_artifact_classes: set[DeletionArtifactClass] | None = None,
    calendar_context_accounted: bool = False,
) -> list[MeetingDeletionArtifactState]:
    purged_artifact_classes = purged_artifact_classes or set()
    materialized_artifact_classes = materialized_artifact_classes or set()
    local_purge_state = local_purge_state or (
        DeletionArtifactState.LOCAL_PENDING
        if local_purge_requested
        else DeletionArtifactState.NOT_APPLICABLE
    )
    local_purge_reason = local_purge_reason or (
        "Local purge pending" if local_purge_requested else "Local purge task not created yet"
    )
    backup_reason = (
        f"backup_expiry_days:{backup_expiry_days}"
        if backup_expiry_days is not None
        else "backup_expiry_policy_missing"
    )
    outcomes_state = (
        DeletionArtifactState.PURGED
        if DeletionArtifactClass.NOTES_SUMMARY in purged_artifact_classes
        else DeletionArtifactState.PURGE_REQUESTED
        if outcomes_materialized
        else DeletionArtifactState.NOT_APPLICABLE
    )
    outcomes_reason = (
        "Meeting outcomes purged"
        if DeletionArtifactClass.NOTES_SUMMARY in purged_artifact_classes
        else "Meeting outcomes purge requested"
        if outcomes_materialized
        else "Meeting outcomes not materialized"
    )
    rows = [
        (
            DeletionArtifactClass.MEETING_ROW,
            DeletionControlScope.CONTROLLED,
            DeletionArtifactState.METADATA_RETAINED,
            "Meeting row retained as deletion report metadata",
        ),
        (
            DeletionArtifactClass.CALENDAR_CONTEXT,
            DeletionControlScope.CONTROLLED,
            DeletionArtifactState.PURGED
            if calendar_context_accounted
            else DeletionArtifactState.NOT_APPLICABLE,
            "Calendar context snapshot purged"
            if calendar_context_accounted
            else "Calendar context not materialized",
        ),
        (
            DeletionArtifactClass.MEDIA_REVISION,
            DeletionControlScope.CONTROLLED,
            DeletionArtifactState.METADATA_RETAINED,
            MEDIA_REVISION_DELETION_SAFE_REASON,
        ),
        (
            DeletionArtifactClass.AUDIO_OBJECT,
            DeletionControlScope.CONTROLLED,
            _purge_state(DeletionArtifactClass.AUDIO_OBJECT, purged_artifact_classes),
            _purge_reason(
                "Server audio", DeletionArtifactClass.AUDIO_OBJECT, purged_artifact_classes
            ),
        ),
        _accounted_artifact_row(
            DeletionArtifactClass.PLAYBACK_CANDIDATE,
            "Playback candidate",
            purged_artifact_classes=purged_artifact_classes,
            materialized_artifact_classes=materialized_artifact_classes,
        ),
        _accounted_artifact_row(
            DeletionArtifactClass.PLAYBACK_CANONICAL,
            "Canonical playback",
            purged_artifact_classes=purged_artifact_classes,
            materialized_artifact_classes=materialized_artifact_classes,
        ),
        _accounted_artifact_row(
            DeletionArtifactClass.NORMALIZATION_ATTEMPT_TEMP,
            "Normalization attempt object",
            purged_artifact_classes=purged_artifact_classes,
            materialized_artifact_classes=materialized_artifact_classes,
        ),
        (
            DeletionArtifactClass.NORMALIZATION_JOB,
            DeletionControlScope.CONTROLLED,
            DeletionArtifactState.METADATA_RETAINED
            if DeletionArtifactClass.NORMALIZATION_JOB in materialized_artifact_classes
            else DeletionArtifactState.NOT_APPLICABLE,
            "Normalization job cancelled; metadata retained without content"
            if DeletionArtifactClass.NORMALIZATION_JOB in materialized_artifact_classes
            else "Normalization job not materialized",
        ),
        (
            DeletionArtifactClass.NORMALIZATION_BACKFILL,
            DeletionControlScope.CONTROLLED,
            DeletionArtifactState.METADATA_RETAINED
            if DeletionArtifactClass.NORMALIZATION_BACKFILL in materialized_artifact_classes
            else DeletionArtifactState.NOT_APPLICABLE,
            "Backfill linkage retained as aggregate metadata"
            if DeletionArtifactClass.NORMALIZATION_BACKFILL in materialized_artifact_classes
            else "Backfill linkage not materialized",
        ),
        (
            DeletionArtifactClass.TRANSCRIPT,
            DeletionControlScope.CONTROLLED,
            _purge_state(DeletionArtifactClass.TRANSCRIPT, purged_artifact_classes),
            _purge_reason("Transcript", DeletionArtifactClass.TRANSCRIPT, purged_artifact_classes),
        ),
        (
            DeletionArtifactClass.DIARIZATION,
            DeletionControlScope.CONTROLLED,
            _purge_state(DeletionArtifactClass.DIARIZATION, purged_artifact_classes),
            _purge_reason(
                "Diarization", DeletionArtifactClass.DIARIZATION, purged_artifact_classes
            ),
        ),
        (
            DeletionArtifactClass.NOTES_SUMMARY,
            DeletionControlScope.CONTROLLED,
            outcomes_state,
            outcomes_reason,
        ),
        (
            DeletionArtifactClass.OUTCOME_ATTEMPT,
            DeletionControlScope.CONTROLLED,
            DeletionArtifactState.METADATA_RETAINED
            if DeletionArtifactClass.OUTCOME_ATTEMPT in materialized_artifact_classes
            else DeletionArtifactState.NOT_APPLICABLE,
            "Generation attempt cancelled; prompt linkage retained for pending observability delivery"
            if DeletionArtifactClass.OUTCOME_ATTEMPT in materialized_artifact_classes
            else "Outcome generation attempt not materialized",
        ),
        (
            DeletionArtifactClass.GENERATION_CALL,
            DeletionControlScope.CONTROLLED,
            DeletionArtifactState.OBSERVABILITY_RETAINED,
            "Plaintext Generation Call ledger retained for observability",
        ),
        (
            DeletionArtifactClass.EXPORT_PACKAGE,
            DeletionControlScope.CONTROLLED,
            _purge_state(DeletionArtifactClass.EXPORT_PACKAGE, purged_artifact_classes),
            _purge_reason(
                "Export package",
                DeletionArtifactClass.EXPORT_PACKAGE,
                purged_artifact_classes,
            ),
        ),
        (
            DeletionArtifactClass.SHARE_GRANT,
            DeletionControlScope.CONTROLLED,
            _purge_state(DeletionArtifactClass.SHARE_GRANT, purged_artifact_classes),
            _purge_reason(
                "Share grants and link tokens",
                DeletionArtifactClass.SHARE_GRANT,
                purged_artifact_classes,
            ),
        ),
        (
            DeletionArtifactClass.SHARE_INVITATION,
            DeletionControlScope.CONTROLLED,
            _purge_state(DeletionArtifactClass.SHARE_INVITATION, purged_artifact_classes),
            _purge_reason(
                "Share invitations and token hashes",
                DeletionArtifactClass.SHARE_INVITATION,
                purged_artifact_classes,
            ),
        ),
        (
            DeletionArtifactClass.UPLOAD_TEMP,
            DeletionControlScope.CONTROLLED,
            _purge_state(DeletionArtifactClass.UPLOAD_TEMP, purged_artifact_classes),
            _purge_reason(
                "Temporary upload", DeletionArtifactClass.UPLOAD_TEMP, purged_artifact_classes
            ),
        ),
        (
            DeletionArtifactClass.PROCESSING_WORKFLOW,
            DeletionControlScope.CONTROLLED,
            DeletionArtifactState.METADATA_RETAINED,
            "Workflow metadata retained without content",
        ),
        (
            DeletionArtifactClass.MEDIASCRIBE,
            DeletionControlScope.EXTERNAL,
            DeletionArtifactState.UNKNOWN,
            "External deletion support is not confirmed",
        ),
        (
            DeletionArtifactClass.LANGFUSE,
            DeletionControlScope.EXTERNAL,
            DeletionArtifactState.OBSERVABILITY_RETAINED,
            "Plaintext Langfuse observations retained under operator policy",
        ),
        (
            DeletionArtifactClass.TEMPORAL_HISTORY,
            DeletionControlScope.EXTERNAL,
            DeletionArtifactState.OBSERVABILITY_RETAINED,
            "Plaintext Temporal History retained under operator policy",
        ),
        (
            DeletionArtifactClass.DIAGNOSTICS,
            DeletionControlScope.CONTROLLED,
            DeletionArtifactState.METADATA_RETAINED,
            "Diagnostics metadata retained without content",
        ),
        (
            DeletionArtifactClass.BACKUP,
            DeletionControlScope.BACKUP,
            DeletionArtifactState.PENDING_EXPIRY,
            backup_reason,
        ),
        (
            DeletionArtifactClass.LOCAL_DESKTOP_BUFFER,
            DeletionControlScope.LOCAL_DEVICE,
            local_purge_state,
            local_purge_reason,
        ),
        (
            DeletionArtifactClass.POST_EGRESS_COPY,
            DeletionControlScope.POST_EGRESS,
            DeletionArtifactState.OUTSIDE_2BRAIN_CONTROL,
            post_egress_safe_reason,
        ),
        (
            DeletionArtifactClass.SEARCH_INDEX,
            DeletionControlScope.CONTROLLED,
            DeletionArtifactState.NOT_APPLICABLE,
            "Search index is not materialized in this MVP seed",
        ),
    ]
    return [
        MeetingDeletionArtifactState(
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            deletion_request_id=deletion_request_id,
            artifact_class=artifact_class.value,
            control_scope=control_scope.value,
            state=state.value,
            safe_reason=label,
            metadata_json=build_lifecycle_audit_metadata(
                artifact_class=artifact_class,
                control_scope=control_scope,
                state=state,
                safe_reason="artifact_lifecycle_state",
            ),
        )
        for artifact_class, control_scope, state, label in rows
    ]


def _purge_state(
    artifact_class: DeletionArtifactClass,
    purged_artifact_classes: set[DeletionArtifactClass],
) -> DeletionArtifactState:
    if artifact_class in purged_artifact_classes:
        return DeletionArtifactState.PURGED
    return DeletionArtifactState.PURGE_REQUESTED


def _accounted_artifact_row(
    artifact_class: DeletionArtifactClass,
    label: str,
    *,
    purged_artifact_classes: set[DeletionArtifactClass],
    materialized_artifact_classes: set[DeletionArtifactClass],
) -> tuple[
    DeletionArtifactClass,
    DeletionControlScope,
    DeletionArtifactState,
    str,
]:
    if artifact_class not in materialized_artifact_classes:
        return (
            artifact_class,
            DeletionControlScope.CONTROLLED,
            DeletionArtifactState.NOT_APPLICABLE,
            f"{label} not materialized",
        )
    state = _purge_state(artifact_class, purged_artifact_classes)
    return (
        artifact_class,
        DeletionControlScope.CONTROLLED,
        state,
        f"{label} purged" if state is DeletionArtifactState.PURGED else f"{label} purge requested",
    )


def _purge_reason(
    label: str,
    artifact_class: DeletionArtifactClass,
    purged_artifact_classes: set[DeletionArtifactClass],
) -> str:
    if artifact_class in purged_artifact_classes:
        return f"{label} purged"
    return f"{label} purge requested"


def _artifact_state_json(row: MeetingDeletionArtifactState) -> dict[str, str | int | bool | None]:
    return {
        "artifact_class": row.artifact_class,
        "control_scope": row.control_scope,
        "state": row.state,
        "safe_reason": row.safe_reason,
    }


def _artifact_row_from_model(row: MeetingDeletionArtifactState) -> ArtifactDeletionState:
    return artifact_row(
        artifact_class=row.artifact_class,
        control_scope=DeletionControlScope(row.control_scope),
        state=DeletionArtifactState(row.state),
        label=row.safe_reason or row.artifact_class,
        safe_reason=row.safe_reason,
    )


async def _post_egress_safe_reason(db: AsyncSession, *, meeting: Meeting) -> str:
    events = (
        await db.scalars(
            select(MeetingEgressAuditEvent.event_type)
            .where(MeetingEgressAuditEvent.workspace_id == meeting.workspace_id)
            .where(MeetingEgressAuditEvent.meeting_id == meeting.id)
            .where(MeetingEgressAuditEvent.event_type.in_(POST_EGRESS_REPORT_EVENT_TYPES))
            .order_by(MeetingEgressAuditEvent.created_at.asc())
        )
    ).all()
    unique_event_types = list(dict.fromkeys(events))
    if not unique_event_types:
        return "Delivered copies are outside GRAF control"
    return "post_egress_events:" + ",".join(unique_event_types)


async def _mark_outcomes_deleting(
    db: AsyncSession,
    *,
    meeting: Meeting,
) -> tuple[bool, tuple[str, ...]]:
    outcome_sets = (
        await db.scalars(
            select(MeetingOutcomeSet)
            .where(MeetingOutcomeSet.workspace_id == meeting.workspace_id)
            .where(MeetingOutcomeSet.meeting_id == meeting.id)
            .where(MeetingOutcomeSet.lifecycle_state == OutcomeLifecycleState.ACTIVE.value)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    for outcome_set in outcome_sets:
        outcome_set.lifecycle_state = OutcomeLifecycleState.DELETING.value
    attempts = (
        await db.scalars(
            select(MeetingOutcomeGenerationAttempt)
            .where(MeetingOutcomeGenerationAttempt.workspace_id == meeting.workspace_id)
            .where(MeetingOutcomeGenerationAttempt.meeting_id == meeting.id)
            .where(
                MeetingOutcomeGenerationAttempt.status.in_(
                    {"queued", "generating", "blocked_dependency"}
                )
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    for attempt in attempts:
        attempt.status = "cancelled"
        attempt.failure_code = "meeting_deleting"
    workflow_ids = [attempt.workflow_id for attempt in attempts if attempt.workflow_id]
    processing_workflows = (
        await db.scalars(
            select(ProcessingWorkflow)
            .where(
                ProcessingWorkflow.workspace_id == meeting.workspace_id,
                ProcessingWorkflow.meeting_id == meeting.id,
                ProcessingWorkflow.status.notin_(
                    {"processed", "blocked", "failed_terminal", "canceled"}
                ),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    for workflow in processing_workflows:
        workflow.status = "canceled"
        workflow.last_reason_code = "meeting_deleting"
        workflow.ended_at = datetime.now(UTC)
        await release_processing_usage_reservation(
            db,
            workspace_id=workflow.workspace_id,
            media_revision_id=workflow.media_revision_id,
            meeting_id=workflow.meeting_id,
        )
        if workflow.workflow_id:
            workflow_ids.append(workflow.workflow_id)

    normalization_jobs = (
        await db.scalars(
            select(PlaybackNormalizationJob)
            .where(
                PlaybackNormalizationJob.workspace_id == meeting.workspace_id,
                PlaybackNormalizationJob.meeting_id == meeting.id,
                PlaybackNormalizationJob.state.notin_(
                    {
                        JobState.TERMINAL.value,
                        JobState.CANCELLED.value,
                    }
                ),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    workflow_ids.extend(job.workflow_id for job in normalization_jobs if job.workflow_id)

    mediascribe_jobs = (
        await db.scalars(
            select(MediaScribeJob)
            .where(
                MediaScribeJob.workspace_id == meeting.workspace_id,
                MediaScribeJob.meeting_id == meeting.id,
                MediaScribeJob.status.notin_({"ready", "failed", "blocked"}),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    for job in mediascribe_jobs:
        job.status = "blocked"
        job.last_error_code = "meeting_deleting"
        job.last_error_message = "Meeting deletion fence is active"
        job.submission_claim_token = None
        job.submission_claimed_at = None

    dispatch_intents = (
        await db.scalars(
            select(DispatchIntent)
            .where(
                DispatchIntent.workspace_id == meeting.workspace_id,
                DispatchIntent.meeting_id == meeting.id,
                DispatchIntent.state.in_({"created", "dispatching", "started", "retryable_failed"}),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    for intent in dispatch_intents:
        intent.state = "cancelled"
        intent.reconciliation_state = "cancelled"
        intent.failure_code = "meeting_deleting"
        intent.completed_at = datetime.now(UTC)
        intent.lease_expires_at = None
        if intent.external_workflow_id:
            workflow_ids.append(intent.external_workflow_id)
    # Outcome-attempt accounting is tracked separately in
    # ``materialized_artifact_classes``. Do not report a summary purge when a
    # queued attempt never produced an outcome set.
    return bool(outcome_sets), tuple(dict.fromkeys(workflow_ids))


async def _request_temporal_cancellation(
    temporal_client: object | None,
    *,
    workflow_ids: tuple[str, ...],
) -> None:
    if temporal_client is None:
        return
    get_handle = getattr(temporal_client, "get_workflow_handle", None)
    if get_handle is None:
        return
    for workflow_id in workflow_ids:
        try:
            handle = get_handle(workflow_id)
            cancel = getattr(handle, "cancel", None)
            if cancel is not None:
                await cancel()
        except Exception:
            # The durable deletion tombstone is authoritative; cancellation is
            # best-effort and Temporal History remains retained either way.
            continue


def _local_purge_task_from_model(task: LocalPurgeTaskModel) -> LocalPurgeTask:
    from twobrain_rec_server.domain.statuses import LocalPurgeTaskState, LocalPurgeTaskType

    return LocalPurgeTask(
        task_id=task.id,
        meeting_id=task.meeting_id,
        task_type=LocalPurgeTaskType(task.task_type),
        state=LocalPurgeTaskState(task.state),
        safe_reason=task.reason_code,
        expires_at=task.expires_at,
        ack_url=f"/api/v1/desktop/local-purge-tasks/{task.id}/ack",
    )
