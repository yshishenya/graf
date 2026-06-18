from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    ArtifactDeletionState,
    DeletionRequestResponse,
    DeletionVerificationReport,
    LocalPurgeTask,
)
from twobrain_rec_server.db.models import (
    LocalPurgeTask as LocalPurgeTaskModel,
)
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingDeletionArtifactState,
    MeetingDeletionReport,
    MeetingDeletionRequest,
    MeetingEgressAuditEvent,
    MeetingLifecycleAuditEvent,
)
from twobrain_rec_server.deletion.audit import build_lifecycle_audit_metadata
from twobrain_rec_server.deletion.local_purge import create_local_purge_tasks_for_request
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
)
from twobrain_rec_server.processing.lifecycle import MEDIA_REVISION_DELETION_SAFE_REASON

TERMINAL_REQUEST_STATES = {
    DeletionState.COMPLETE.value,
    DeletionState.TERMINAL_FAILED.value,
}

DEFAULT_BACKUP_EXPIRY_DAYS = 30

POST_EGRESS_REPORT_EVENT_TYPES = {
    "download_completed",
    "export_completed",
    "share_granted",
    "share_link_opened",
}

RETRY_UNAVAILABLE_GUIDANCE = "Retry is unavailable for the current lifecycle state. Open the deletion report for safe status details."
RETRY_OPERATOR_GUIDANCE = "Retry is available only after operator review confirms the failed artifact class is safe to retry."


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
) -> DeletionRequestResponse:
    if confirmation_boundary != BOUNDED_DELETE_COPY:
        raise ProblemDetail(status=422, code="invalid_deletion_confirmation", title="Invalid deletion confirmation")
    if (meeting.deletion_state or DeletionState.NONE.value) != DeletionState.NONE.value:
        raise ProblemDetail(status=409, code="meeting_deletion_active", title="Meeting deletion is already active")
    active_request = await db.scalar(
        select(MeetingDeletionRequest)
        .where(MeetingDeletionRequest.workspace_id == meeting.workspace_id)
        .where(MeetingDeletionRequest.meeting_id == meeting.id)
        .where(MeetingDeletionRequest.state.notin_(TERMINAL_REQUEST_STATES))
        .order_by(desc(MeetingDeletionRequest.created_at))
    )
    if active_request is not None:
        raise ProblemDetail(status=409, code="meeting_deletion_active", title="Meeting deletion is already active")

    now = datetime.now(UTC)
    deletion_request = MeetingDeletionRequest(
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
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

    audit = MeetingLifecycleAuditEvent(
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        deletion_request_id=deletion_request.id,
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
    local_purge_tasks = await create_local_purge_tasks_for_request(
        db,
        meeting=meeting,
        deletion_request_id=deletion_request.id,
    )
    post_egress_safe_reason = await _post_egress_safe_reason(db, meeting=meeting)
    artifact_states = _initial_artifact_states(
        meeting,
        deletion_request.id,
        local_purge_requested=bool(local_purge_tasks),
        backup_expiry_days=backup_expiry_days,
        post_egress_safe_reason=post_egress_safe_reason,
    )
    report = MeetingDeletionReport(
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        deletion_request_id=deletion_request.id,
        overall_state=DeletionState.DELETING.value,
        summary_label="Deleting meeting",
        bounded_copy=BOUNDED_DELETE_COPY,
        artifact_summary_json=[
            _artifact_state_json(state)
            for state in artifact_states
        ],
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
    db.add_all([*artifact_states, report])
    await _flush_or_fail_closed(db)
    return DeletionRequestResponse(
        request_id=deletion_request.id,
        meeting_id=meeting.id,
        lifecycle=lifecycle_state(DeletionState.DELETING),
        report_url=f"/api/v1/cabinet/meetings/{meeting.id}/deletion-report",
    )


async def lifecycle_for_meeting(db: AsyncSession, *, meeting: Meeting) -> DeletionState:
    return DeletionState(meeting.deletion_state or DeletionState.NONE.value)


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
        raise ProblemDetail(status=404, code="deletion_report_not_found", title="Deletion report not found")
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
    if deletion_request is not None and deletion_request.request_source == DeletionRequestSource.RETENTION_JOB.value:
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


async def _flush_or_fail_closed(db: AsyncSession) -> None:
    try:
        await db.flush()
    except SQLAlchemyError as exc:
        raise ProblemDetail(
            status=503,
            code="deletion_audit_unavailable",
            title="Deletion audit unavailable",
            detail="Deletion failed closed before destructive action because lifecycle evidence could not be persisted.",
        ) from exc


def _initial_artifact_states(
    meeting: Meeting,
    deletion_request_id: UUID,
    *,
    local_purge_requested: bool = False,
    backup_expiry_days: int | None = DEFAULT_BACKUP_EXPIRY_DAYS,
    post_egress_safe_reason: str = "Delivered copies are outside 2brain Rec control",
) -> list[MeetingDeletionArtifactState]:
    local_purge_state = (
        DeletionArtifactState.LOCAL_PENDING
        if local_purge_requested
        else DeletionArtifactState.NOT_APPLICABLE
    )
    local_purge_reason = "Local purge pending" if local_purge_requested else "Local purge task not created yet"
    backup_reason = (
        f"backup_expiry_days:{backup_expiry_days}"
        if backup_expiry_days is not None
        else "backup_expiry_policy_missing"
    )
    rows = [
        (DeletionArtifactClass.MEETING_ROW, DeletionControlScope.CONTROLLED, DeletionArtifactState.METADATA_RETAINED, "Meeting row retained as deletion report metadata"),
        (DeletionArtifactClass.MEDIA_REVISION, DeletionControlScope.CONTROLLED, DeletionArtifactState.METADATA_RETAINED, MEDIA_REVISION_DELETION_SAFE_REASON),
        (DeletionArtifactClass.AUDIO_OBJECT, DeletionControlScope.CONTROLLED, DeletionArtifactState.PURGE_REQUESTED, "Server audio purge requested"),
        (DeletionArtifactClass.TRANSCRIPT, DeletionControlScope.CONTROLLED, DeletionArtifactState.PURGE_REQUESTED, "Transcript purge requested"),
        (DeletionArtifactClass.DIARIZATION, DeletionControlScope.CONTROLLED, DeletionArtifactState.PURGE_REQUESTED, "Diarization purge requested"),
        (DeletionArtifactClass.NOTES_SUMMARY, DeletionControlScope.CONTROLLED, DeletionArtifactState.NOT_APPLICABLE, "Notes are not materialized in this MVP seed"),
        (DeletionArtifactClass.EXPORT_PACKAGE, DeletionControlScope.CONTROLLED, DeletionArtifactState.PURGE_REQUESTED, "Export package purge requested"),
        (DeletionArtifactClass.SHARE_GRANT, DeletionControlScope.CONTROLLED, DeletionArtifactState.PURGE_REQUESTED, "Share grants disabled for this meeting"),
        (DeletionArtifactClass.UPLOAD_TEMP, DeletionControlScope.CONTROLLED, DeletionArtifactState.PURGE_REQUESTED, "Temporary upload purge requested"),
        (DeletionArtifactClass.PROCESSING_WORKFLOW, DeletionControlScope.CONTROLLED, DeletionArtifactState.METADATA_RETAINED, "Workflow metadata retained without content"),
        (DeletionArtifactClass.MEDIASCRIBE, DeletionControlScope.EXTERNAL, DeletionArtifactState.UNKNOWN, "External deletion support is not confirmed"),
        (DeletionArtifactClass.LANGFUSE, DeletionControlScope.EXTERNAL, DeletionArtifactState.METADATA_RETAINED, "Langfuse is metadata-only by default"),
        (DeletionArtifactClass.DIAGNOSTICS, DeletionControlScope.CONTROLLED, DeletionArtifactState.METADATA_RETAINED, "Diagnostics metadata retained without content"),
        (DeletionArtifactClass.BACKUP, DeletionControlScope.BACKUP, DeletionArtifactState.PENDING_EXPIRY, backup_reason),
        (DeletionArtifactClass.LOCAL_DESKTOP_BUFFER, DeletionControlScope.LOCAL_DEVICE, local_purge_state, local_purge_reason),
        (DeletionArtifactClass.POST_EGRESS_COPY, DeletionControlScope.POST_EGRESS, DeletionArtifactState.OUTSIDE_2BRAIN_CONTROL, post_egress_safe_reason),
        (DeletionArtifactClass.SEARCH_INDEX, DeletionControlScope.CONTROLLED, DeletionArtifactState.NOT_APPLICABLE, "Search index is not materialized in this MVP seed"),
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
        return "Delivered copies are outside 2brain Rec control"
    return "post_egress_events:" + ",".join(unique_event_types)


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
