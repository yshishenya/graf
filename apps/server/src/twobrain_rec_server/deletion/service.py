from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    ArtifactDeletionState,
    DeletionRequestResponse,
    DeletionVerificationReport,
    LocalPurgeTask,
)
from twobrain_rec_server.calendar.lifecycle import account_meeting_calendar_context_deletion
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    Meeting,
    MeetingDeletionArtifactState,
    MeetingDeletionReport,
    MeetingDeletionRequest,
    MeetingEgressAuditEvent,
    MeetingLifecycleAuditEvent,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    MeetingSpeakerName,
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    ProcessingResult,
    TemporaryUploadObject,
    TrackArtifact,
    TranscriptSegment,
    UploadSession,
)
from twobrain_rec_server.db.models import (
    LocalPurgeTask as LocalPurgeTaskModel,
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
    OutcomeLifecycleState,
)
from twobrain_rec_server.normalization.audit import add_normalization_audit_event
from twobrain_rec_server.normalization.statuses import (
    AttemptState,
    JobState,
    NormalizationReason,
    ensure_attempt_transition,
    ensure_job_transition,
)
from twobrain_rec_server.processing.lifecycle import MEDIA_REVISION_DELETION_SAFE_REASON

TERMINAL_REQUEST_STATES = {
    DeletionState.COMPLETE.value,
    DeletionState.TERMINAL_FAILED.value,
}

DEFAULT_BACKUP_EXPIRY_DAYS = 30

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
    storage: object | None = None,
) -> DeletionRequestResponse:
    if confirmation_boundary != BOUNDED_DELETE_COPY:
        raise ProblemDetail(
            status=422, code="invalid_deletion_confirmation", title="Invalid deletion confirmation"
        )
    locked_meeting = await db.scalar(
        select(Meeting)
        .where(
            Meeting.id == meeting.id,
            Meeting.workspace_id == meeting.workspace_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locked_meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    meeting = locked_meeting
    if (meeting.deletion_state or DeletionState.NONE.value) != DeletionState.NONE.value:
        raise ProblemDetail(
            status=409, code="meeting_deletion_active", title="Meeting deletion is already active"
        )
    active_request = await db.scalar(
        select(MeetingDeletionRequest)
        .where(MeetingDeletionRequest.workspace_id == meeting.workspace_id)
        .where(MeetingDeletionRequest.meeting_id == meeting.id)
        .where(MeetingDeletionRequest.state.notin_(TERMINAL_REQUEST_STATES))
        .order_by(desc(MeetingDeletionRequest.created_at))
    )
    if active_request is not None:
        raise ProblemDetail(
            status=409, code="meeting_deletion_active", title="Meeting deletion is already active"
        )

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
    await _flush_or_fail_closed(db)
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
        deletion_request_id=deletion_request.id,
    )
    outcomes_materialized = await _mark_outcomes_deleting(db, meeting=meeting)
    post_egress_safe_reason = await _post_egress_safe_reason(db, meeting=meeting)
    purge_result = await _purge_server_controlled_content(db, meeting=meeting, storage=storage)
    artifact_states = _initial_artifact_states(
        meeting,
        deletion_request.id,
        local_purge_requested=bool(local_purge_tasks),
        backup_expiry_days=backup_expiry_days,
        post_egress_safe_reason=post_egress_safe_reason,
        outcomes_materialized=outcomes_materialized,
        purged_artifact_classes=purge_result.purged_classes,
        materialized_artifact_classes=purge_result.materialized_classes,
        calendar_context_accounted=calendar_context_artifact_count > 0,
    )
    report = MeetingDeletionReport(
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        deletion_request_id=deletion_request.id,
        overall_state=DeletionState.DELETING.value,
        summary_label="Deleting meeting",
        bounded_copy=BOUNDED_DELETE_COPY,
        artifact_summary_json=[_artifact_state_json(state) for state in artifact_states],
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


async def lifecycle_for_meeting(*, meeting: Meeting) -> DeletionState:
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


async def _purge_server_controlled_content(
    db: AsyncSession,
    *,
    meeting: Meeting,
    storage: object | None,
) -> _ServerPurgeResult:
    result = _ServerPurgeResult()
    now = datetime.now(UTC)

    artifacts = (
        await db.scalars(
            select(TrackArtifact)
            .where(TrackArtifact.workspace_id == meeting.workspace_id)
            .where(TrackArtifact.meeting_id == meeting.id)
            .with_for_update()
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
        and artifact.status == "stored"
        and artifact.validated_at is not None
        and artifact.normalization_profile_version is not None
        for artifact in artifacts
    ):
        result.materialized_classes.add(DeletionArtifactClass.PLAYBACK_CANONICAL)

    normalization_jobs = (
        await db.scalars(
            select(PlaybackNormalizationJob)
            .where(
                PlaybackNormalizationJob.workspace_id == meeting.workspace_id,
                PlaybackNormalizationJob.meeting_id == meeting.id,
            )
            .order_by(PlaybackNormalizationJob.created_at, PlaybackNormalizationJob.id)
            .with_for_update()
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
        )
    ).all()
    if normalization_attempts:
        result.materialized_classes.add(DeletionArtifactClass.NORMALIZATION_ATTEMPT_TEMP)

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

    object_keys = {
        *(artifact.storage_object_key for artifact in artifacts),
        *(attempt.storage_object_key for attempt in normalization_attempts),
        *(temporary_object.storage_object_key for temporary_object in temporary_objects),
    }
    object_presence = {
        object_key: await _storage_object_exists(storage, object_key)
        for object_key in sorted(object_keys)
    }
    for object_key in sorted(object_keys):
        await _delete_storage_object(storage, object_key)

    for artifact in artifacts:
        artifact.status = "purged"
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
    if outcome_sets:
        await _purge_meeting_outcomes(db, meeting=meeting)
        result.materialized_classes.add(DeletionArtifactClass.NOTES_SUMMARY)
        result.purged_classes.add(DeletionArtifactClass.NOTES_SUMMARY)

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
        await delete_object_async(object_key)
        return
    delete_object = getattr(storage, "delete_object", None)
    if delete_object is None:
        raise ProblemDetail(
            status=503,
            code="deletion_storage_unavailable",
            title="Deletion storage unavailable",
            detail="Deletion failed closed because server-owned media could not be purged.",
        )
    delete_object(object_key)


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
            return bool(await object_exists_async(object_key))
        object_exists = getattr(storage, "object_exists", None)
        if object_exists is not None:
            return bool(object_exists(object_key))
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


def _initial_artifact_states(
    meeting: Meeting,
    deletion_request_id: UUID,
    *,
    local_purge_requested: bool = False,
    backup_expiry_days: int | None = DEFAULT_BACKUP_EXPIRY_DAYS,
    post_egress_safe_reason: str = "Delivered copies are outside GRAF control",
    outcomes_materialized: bool = False,
    purged_artifact_classes: set[DeletionArtifactClass] | None = None,
    materialized_artifact_classes: set[DeletionArtifactClass] | None = None,
    calendar_context_accounted: bool = False,
) -> list[MeetingDeletionArtifactState]:
    purged_artifact_classes = purged_artifact_classes or set()
    materialized_artifact_classes = materialized_artifact_classes or set()
    local_purge_state = (
        DeletionArtifactState.LOCAL_PENDING
        if local_purge_requested
        else DeletionArtifactState.NOT_APPLICABLE
    )
    local_purge_reason = (
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
            DeletionArtifactClass.EXPORT_PACKAGE,
            DeletionControlScope.CONTROLLED,
            DeletionArtifactState.PURGE_REQUESTED,
            "Export package purge requested",
        ),
        (
            DeletionArtifactClass.SHARE_GRANT,
            DeletionControlScope.CONTROLLED,
            DeletionArtifactState.PURGE_REQUESTED,
            "Share grants disabled for this meeting",
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
            DeletionArtifactState.METADATA_RETAINED,
            "Langfuse is metadata-only by default",
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


async def _mark_outcomes_deleting(db: AsyncSession, *, meeting: Meeting) -> bool:
    outcome_sets = (
        await db.scalars(
            select(MeetingOutcomeSet)
            .where(MeetingOutcomeSet.workspace_id == meeting.workspace_id)
            .where(MeetingOutcomeSet.meeting_id == meeting.id)
            .where(MeetingOutcomeSet.lifecycle_state == OutcomeLifecycleState.ACTIVE.value)
        )
    ).all()
    for outcome_set in outcome_sets:
        outcome_set.lifecycle_state = OutcomeLifecycleState.DELETING.value
    return bool(outcome_sets)


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
