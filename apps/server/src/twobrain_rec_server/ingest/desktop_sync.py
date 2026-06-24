from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    DesktopRecordingSyncStateResponse,
    DesktopSyncConflict,
    DesktopSyncMeetingState,
    DesktopSyncProcessingState,
    DesktopSyncReviewState,
    DesktopSyncUploadSessionState,
    MediaRevisionSummary,
    MissingRange,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import Meeting as MeetingModel
from twobrain_rec_server.db.models import ProcessingResult, ProcessingWorkflow
from twobrain_rec_server.domain.statuses import (
    DeletionState,
    MediaRevisionStatus,
    MeetingStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
    SyncConflictState,
    UploadSessionStatus,
)
from twobrain_rec_server.ingest.media_revisions import normalize_initial_local_media_revision_id
from twobrain_rec_server.ingest.ranges import missing_ranges_for_expected_sizes
from twobrain_rec_server.ingest.store import (
    UploadSessionRecord,
    load_active_upload_session_for_meeting,
    load_meeting_record,
    persist_meeting,
    persist_upload_session,
)


def _utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _accepted_bytes_by_track(session: UploadSessionRecord | None) -> dict[str, int]:
    if session is None:
        return {}
    accepted: dict[str, int] = {}
    for (role, _part_number), part in session.parts.items():
        accepted[role.value] = accepted.get(role.value, 0) + part.byte_length
    return accepted


def _missing_ranges_by_track(session: UploadSessionRecord | None) -> dict[str, list[MissingRange]]:
    if session is None:
        return {}
    ranges = missing_ranges_for_expected_sizes(session, session.expected_track_sizes)
    return {
        role.value: [MissingRange(start=start, end=end) for start, end in role_ranges]
        for role, role_ranges in ranges.items()
    }


def _conflict(
    state: SyncConflictState,
    *,
    reason: str,
    next_action: str,
) -> DesktopSyncConflict:
    return DesktopSyncConflict(state=state, reason=reason, next_action=next_action)


def _first_blocking_conflict(*conflicts: DesktopSyncConflict) -> DesktopSyncConflict:
    for conflict in conflicts:
        if conflict.state != SyncConflictState.NONE:
            return conflict
    return DesktopSyncConflict()


def _safe_deletion_state(value: str | None) -> DeletionState:
    try:
        return DeletionState(value or DeletionState.NONE.value)
    except ValueError:
        return DeletionState.NONE


async def _load_deletion_state(db: AsyncSession | None, meeting_id: object) -> DeletionState:
    if db is None:
        return DeletionState.NONE
    model = await db.get(MeetingModel, meeting_id)
    if model is None:
        return DeletionState.NONE
    return _safe_deletion_state(model.deletion_state)


def _metadata_conflict(*, expected_revision_id: str, actual_revision_id: str | None) -> DesktopSyncConflict:
    if actual_revision_id == expected_revision_id:
        return DesktopSyncConflict()
    return _conflict(
        SyncConflictState.SERVER_EXPECTED_METADATA_MISMATCH,
        reason="media_revision_conflict",
        next_action="manual_review",
    )


def _access_conflict(*, tenant_scope: TenantScope, meeting: object) -> tuple[str, DesktopSyncConflict]:
    if meeting.created_by_user_id != tenant_scope.user_id:
        return (
            "access_revoked",
            _conflict(
                SyncConflictState.ACCESS_REVOKED,
                reason="access_revoked",
                next_action="sign_in_again",
            ),
        )
    if meeting.device_id != tenant_scope.device_id:
        return (
            "stale_device_identity",
            _conflict(
                SyncConflictState.STALE_DEVICE_IDENTITY,
                reason="stale_device_identity",
                next_action="reauthenticate_device",
            ),
        )
    return ("owner", DesktopSyncConflict())


def _deletion_conflict(*, deletion_state: DeletionState, media_revision_status: MediaRevisionStatus) -> DesktopSyncConflict:
    if deletion_state != DeletionState.NONE or media_revision_status == MediaRevisionStatus.DELETED:
        return _conflict(
            SyncConflictState.SERVER_MEETING_DELETED,
            reason="server_meeting_deleted",
            next_action="stop_upload",
        )
    return DesktopSyncConflict()


def _processing_conflict(status: ProcessingStatus) -> DesktopSyncConflict:
    if status in {ProcessingStatus.FAILED_RETRYABLE, ProcessingStatus.FAILED_TERMINAL, ProcessingStatus.CANCELED}:
        return _conflict(
            SyncConflictState.PROCESSING_FAILED,
            reason="processing_failed",
            next_action="contact_operator",
        )
    if status == ProcessingStatus.BLOCKED:
        return _conflict(
            SyncConflictState.PROCESSING_BLOCKED,
            reason="processing_blocked",
            next_action="contact_operator",
        )
    return DesktopSyncConflict()


def _status_value(status: object) -> str:
    return str(getattr(status, "value", status))


def _transcript_available(result: ProcessingResult | None) -> bool:
    return bool(
        result is not None
        and result.status == ProcessingResultStatus.IMPORTED.value
        and result.transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.segment_count > 0
    )


def _diarization_available(result: ProcessingResult | None) -> bool:
    return bool(
        result is not None
        and result.status == ProcessingResultStatus.IMPORTED.value
        and result.diarization_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.diarization_segment_count > 0
    )


def _desktop_review_status(
    *,
    meeting: object,
    result: ProcessingResult | None,
    workflow: ProcessingWorkflow | None,
) -> str:
    has_transcript = _transcript_available(result)
    has_diarization = _diarization_available(result)
    if has_transcript and has_diarization:
        return "ready"
    if has_transcript or has_diarization:
        return "partial"

    lifecycle_status = workflow.status if workflow is not None else _status_value(meeting.processing_status)
    if lifecycle_status in {
        ProcessingStatus.PENDING_PROCESSING.value,
        ProcessingStatus.STARTING.value,
        ProcessingStatus.WORKFLOW_STARTED.value,
        ProcessingStatus.SUBMITTING.value,
        ProcessingStatus.SUBMITTED.value,
        ProcessingStatus.POLLING.value,
        ProcessingStatus.IMPORTING.value,
    }:
        return "processing"
    if lifecycle_status == ProcessingStatus.NOT_SUBMITTED.value:
        return "submitted"
    if lifecycle_status == ProcessingStatus.BLOCKED.value:
        return "blocked"
    if lifecycle_status in {ProcessingStatus.FAILED_RETRYABLE.value, ProcessingStatus.FAILED_TERMINAL.value}:
        return "failed"
    if lifecycle_status == ProcessingStatus.CANCELED.value:
        return "unavailable"

    meeting_status = _status_value(meeting.status)
    if meeting_status == MeetingStatus.DRAFT.value:
        return "local_only"
    if meeting_status == MeetingStatus.UPLOADING.value:
        return "uploading"
    if meeting_status in {MeetingStatus.FAILED.value, MeetingStatus.DEGRADED.value}:
        return "failed"
    return "unavailable"


async def _latest_processing_workflow(
    db: AsyncSession | None,
    *,
    workspace_id: object,
    meeting_id: object,
    media_revision_id: object | None,
) -> ProcessingWorkflow | None:
    if db is None:
        return None
    base_query = select(ProcessingWorkflow).where(
        ProcessingWorkflow.workspace_id == workspace_id,
        ProcessingWorkflow.meeting_id == meeting_id,
    )
    query = base_query
    if media_revision_id is not None:
        query = query.where(ProcessingWorkflow.media_revision_id == media_revision_id)
    workflow = await db.scalar(query.order_by(desc(ProcessingWorkflow.updated_at), desc(ProcessingWorkflow.created_at)))
    if workflow is None and media_revision_id is not None:
        workflow = await db.scalar(
            base_query.where(ProcessingWorkflow.media_revision_id.is_(None)).order_by(
                desc(ProcessingWorkflow.updated_at),
                desc(ProcessingWorkflow.created_at),
            )
        )
    return workflow


async def _latest_processing_result(
    db: AsyncSession | None,
    *,
    workspace_id: object,
    meeting_id: object,
    media_revision_id: object | None,
) -> ProcessingResult | None:
    if db is None or media_revision_id is None:
        return None
    return await db.scalar(
        select(ProcessingResult)
        .where(
            ProcessingResult.workspace_id == workspace_id,
            ProcessingResult.meeting_id == meeting_id,
            ProcessingResult.media_revision_id == media_revision_id,
        )
        .order_by(desc(ProcessingResult.imported_at), desc(ProcessingResult.created_at))
    )


def _review_available(conflict: DesktopSyncConflict, processing_status: ProcessingStatus) -> bool:
    if conflict.state in {
        SyncConflictState.SERVER_MEETING_DELETED,
        SyncConflictState.ACCESS_REVOKED,
        SyncConflictState.STALE_DEVICE_IDENTITY,
        SyncConflictState.SERVER_EXPECTED_METADATA_MISMATCH,
        SyncConflictState.DEPENDENCY_UNAVAILABLE,
    }:
        return False
    return processing_status != ProcessingStatus.CANCELED


async def _mark_expired_if_needed(
    *,
    db: AsyncSession | None,
    meeting: object,
    session: UploadSessionRecord | None,
) -> DesktopSyncConflict:
    if session is None or session.status == UploadSessionStatus.EXPIRED:
        if session is None:
            return DesktopSyncConflict()
        return DesktopSyncConflict(
            state=SyncConflictState.UPLOAD_SESSION_EXPIRED,
            reason="upload_session_expired",
            next_action="create_upload_session",
        )
    if _utc_aware(session.expires_at) > datetime.now(UTC):
        return DesktopSyncConflict()
    session.status = UploadSessionStatus.EXPIRED
    meeting.status = MeetingStatus.EXPIRED
    await persist_meeting(db, meeting)
    await persist_upload_session(db, session)
    return DesktopSyncConflict(
        state=SyncConflictState.UPLOAD_SESSION_EXPIRED,
        reason="upload_session_expired",
        next_action="create_upload_session",
    )


async def get_desktop_recording_sync_state(
    *,
    tenant_scope: TenantScope,
    db: AsyncSession | None,
    local_recording_id: str,
    local_media_revision_id: str | None,
) -> DesktopRecordingSyncStateResponse:
    meeting = await load_meeting_record(
        db,
        workspace_id=tenant_scope.workspace_id,
        local_recording_id=local_recording_id,
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="recording_not_found", title="Recording not found")
    expected_revision_id = normalize_initial_local_media_revision_id(local_recording_id, local_media_revision_id)
    deletion_state = await _load_deletion_state(db, meeting.id)
    access_state, access_conflict = _access_conflict(tenant_scope=tenant_scope, meeting=meeting)
    metadata_conflict = _metadata_conflict(
        expected_revision_id=expected_revision_id,
        actual_revision_id=meeting.local_media_revision_id,
    )
    deletion_conflict = _deletion_conflict(
        deletion_state=deletion_state,
        media_revision_status=meeting.media_revision_status,
    )
    processing_conflict = _processing_conflict(meeting.processing_status)
    review_workflow = await _latest_processing_workflow(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        media_revision_id=meeting.media_revision_id,
    )
    review_result = await _latest_processing_result(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        media_revision_id=meeting.media_revision_id,
    )
    effective_processing_status = (
        ProcessingStatus(review_workflow.status) if review_workflow is not None else meeting.processing_status
    )
    review_status = _desktop_review_status(meeting=meeting, result=review_result, workflow=review_workflow)
    transcript_ready = _transcript_available(review_result)
    diarization_ready = _diarization_available(review_result)
    session: UploadSessionRecord | None = None
    dependency_conflict = DesktopSyncConflict()
    try:
        session = await load_active_upload_session_for_meeting(db, meeting.id)
    except Exception:
        dependency_conflict = _conflict(
            SyncConflictState.DEPENDENCY_UNAVAILABLE,
            reason="sync_state_dependency_unavailable",
            next_action="retry_later",
        )
    session_conflict = (
        DesktopSyncConflict()
        if dependency_conflict.state != SyncConflictState.NONE
        else await _mark_expired_if_needed(db=db, meeting=meeting, session=session)
    )
    conflict = _first_blocking_conflict(
        access_conflict,
        metadata_conflict,
        deletion_conflict,
        processing_conflict,
        dependency_conflict,
        session_conflict,
    )
    return DesktopRecordingSyncStateResponse(
        local_recording_id=meeting.local_recording_id,
        local_media_revision_id=meeting.local_media_revision_id or expected_revision_id,
        meeting=DesktopSyncMeetingState(
            meeting_id=meeting.id,
            status=meeting.status,
            processing_status=meeting.processing_status,
            deletion_state=deletion_state,
            access_state=access_state,
        ),
        media_revision=MediaRevisionSummary(
            media_revision_id=meeting.media_revision_id,
            local_media_revision_id=meeting.local_media_revision_id,
            revision_number=1,
            source_kind=meeting.media_revision_source_kind,
            status=meeting.media_revision_status,
        ),
        upload_session=DesktopSyncUploadSessionState(
            session_id=session.id if session is not None else None,
            status=session.status if session is not None else None,
            accepted_bytes_by_track=_accepted_bytes_by_track(session),
            missing_ranges_by_track=_missing_ranges_by_track(session),
        ),
        processing=DesktopSyncProcessingState(
            status=effective_processing_status,
            workflow_id=review_workflow.workflow_id if review_workflow is not None else None,
            reason_code=review_workflow.last_reason_code if review_workflow is not None else processing_conflict.reason,
        ),
        review=DesktopSyncReviewState(
            available=_review_available(conflict, effective_processing_status),
            status=review_status,
            media_revision_id=meeting.media_revision_id,
            transcript_available=transcript_ready,
            diarization_available=diarization_ready,
            content_available=transcript_ready or diarization_ready,
            web_url=f"/meetings/{meeting.id}" if _review_available(conflict, effective_processing_status) else None,
            desktop_url=f"/desktop/meetings/{meeting.id}" if _review_available(conflict, effective_processing_status) else None,
        ),
        conflict=conflict,
    )
