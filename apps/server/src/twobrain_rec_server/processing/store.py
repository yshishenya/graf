from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MediaRevision,
    MediaScribeJob,
    Meeting,
    ProcessingAuditEvent,
    ProcessingDependencyState,
    ProcessingPlaceholder,
    ProcessingResult,
    ProcessingWorkflow,
    TrackArtifact,
    TranscriptSegment,
)
from twobrain_rec_server.domain.statuses import (
    MediaRevisionSourceKind,
    MediaRevisionStatus,
    MediaScribeJobStatus,
    ProcessingAvailabilityStatus,
    ProcessingDependencyName,
    ProcessingDependencyStateValue,
    ProcessingResultStatus,
    ProcessingStatus,
    SummaryStatus,
    TrackRole,
)
from twobrain_rec_server.ingest.media_revisions import (
    authoritative_track_roles,
    authoritative_track_sha256_by_role,
)
from twobrain_rec_server.mediascribe.schemas import MediaScribeResult
from twobrain_rec_server.processing.audit import safe_audit_metadata


@dataclass(frozen=True, slots=True)
class ProcessingSourceArtifacts:
    request_mode: str
    mic_artifact: TrackArtifact | None = None
    incoming_artifact: TrackArtifact | None = None
    source_artifact: TrackArtifact | None = None

    @property
    def byte_length(self) -> int:
        if self.request_mode == "single_track":
            return self.source_artifact.byte_length if self.source_artifact is not None else 0
        return (self.mic_artifact.byte_length if self.mic_artifact is not None else 0) + (
            self.incoming_artifact.byte_length if self.incoming_artifact is not None else 0
        )


async def load_meeting_for_workspace(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> Meeting | None:
    return await db.scalar(
        select(Meeting).where(
            Meeting.id == meeting_id,
            Meeting.workspace_id == workspace_id,
        )
    )


async def latest_media_revision_for_meeting(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> MediaRevision | None:
    return await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == workspace_id,
            MediaRevision.meeting_id == meeting_id,
        )
        .order_by(desc(MediaRevision.revision_number), desc(MediaRevision.updated_at))
    )


async def load_track_pair(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
) -> tuple[TrackArtifact | None, TrackArtifact | None]:
    query = select(TrackArtifact).where(
        TrackArtifact.workspace_id == workspace_id,
        TrackArtifact.meeting_id == meeting_id,
        TrackArtifact.status == "stored",
    )
    if media_revision_id is not None:
        query = query.where(TrackArtifact.media_revision_id == media_revision_id)
    artifacts = await db.scalars(query)
    mic: TrackArtifact | None = None
    incoming: TrackArtifact | None = None
    for artifact in artifacts:
        if artifact.track_role == TrackRole.MICROPHONE.value:
            mic = artifact
        elif artifact.track_role == TrackRole.SYSTEM.value:
            incoming = artifact
    return mic, incoming


async def load_processing_source(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
) -> ProcessingSourceArtifacts | None:
    revision_query = select(MediaRevision).where(
        MediaRevision.workspace_id == workspace_id,
        MediaRevision.meeting_id == meeting_id,
        MediaRevision.status == MediaRevisionStatus.ACCEPTED.value,
        MediaRevision.immutable.is_(True),
        MediaRevision.manifest_sha256.is_not(None),
    )
    if media_revision_id is not None:
        revision_query = revision_query.where(MediaRevision.id == media_revision_id)
    else:
        revision_query = revision_query.order_by(
            desc(MediaRevision.revision_number),
            desc(MediaRevision.updated_at),
        )
    revision = await db.scalar(revision_query)
    if revision is None or not revision.track_sha256_by_role:
        return None
    try:
        expected_digests = authoritative_track_sha256_by_role(
            source_kind=revision.source_kind,
            digests_by_role=revision.track_sha256_by_role,
        )
        expected_roles = authoritative_track_roles(revision.source_kind)
    except ValueError:
        return None
    artifacts = list(
        await db.scalars(
            select(TrackArtifact).where(
                TrackArtifact.workspace_id == workspace_id,
                TrackArtifact.meeting_id == meeting_id,
                TrackArtifact.media_revision_id == revision.id,
                TrackArtifact.status == "stored",
                TrackArtifact.track_role.in_(expected_roles),
            )
        )
    )
    artifacts_by_role: dict[str, TrackArtifact] = {}
    for artifact in artifacts:
        if artifact.track_role in artifacts_by_role:
            return None
        if artifact.sha256 != expected_digests.get(artifact.track_role):
            return None
        artifacts_by_role[artifact.track_role] = artifact
    if set(artifacts_by_role) != set(expected_roles):
        return None
    if revision.source_kind == MediaRevisionSourceKind.MANUAL_UPLOAD.value:
        return ProcessingSourceArtifacts(
            request_mode="single_track",
            source_artifact=artifacts_by_role[TrackRole.MEDIA.value],
        )
    if revision.source_kind == MediaRevisionSourceKind.INITIAL_RECORDING.value:
        return ProcessingSourceArtifacts(
            request_mode="dual_track",
            mic_artifact=artifacts_by_role[TrackRole.MICROPHONE.value],
            incoming_artifact=artifacts_by_role[TrackRole.SYSTEM.value],
        )
    return None


async def get_processing_workflow(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
) -> ProcessingWorkflow | None:
    base_query = select(ProcessingWorkflow).where(
            ProcessingWorkflow.workspace_id == workspace_id,
            ProcessingWorkflow.meeting_id == meeting_id,
    )
    query = base_query
    if media_revision_id is not None:
        query = query.where(ProcessingWorkflow.media_revision_id == media_revision_id)
    workflow = await db.scalar(query)
    if workflow is None and media_revision_id is not None:
        workflow = await db.scalar(base_query.where(ProcessingWorkflow.media_revision_id.is_(None)))
    return workflow


async def upsert_processing_workflow(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
    workflow_id: str,
    status: ProcessingStatus,
    workflow_run_id: str | None = None,
    reason_code: str | None = None,
) -> ProcessingWorkflow:
    now = datetime.now(UTC)
    workflow = await get_processing_workflow(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
    )
    if workflow is None and media_revision_id is not None:
        workflow = await get_processing_workflow(db, workspace_id=workspace_id, meeting_id=meeting_id)
    if workflow is None:
        workflow = ProcessingWorkflow(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
            status=status.value,
            attempt_count=1,
            last_reason_code=reason_code,
            started_at=now,
        )
        db.add(workflow)
    else:
        workflow.workflow_id = workflow_id
        if media_revision_id is not None:
            workflow.media_revision_id = media_revision_id
        if workflow_run_id is not None:
            workflow.workflow_run_id = workflow_run_id
        workflow.status = status.value
        workflow.last_reason_code = reason_code
        workflow.attempt_count += 1
        if status not in {
            ProcessingStatus.PROCESSED,
            ProcessingStatus.BLOCKED,
            ProcessingStatus.FAILED_TERMINAL,
            ProcessingStatus.CANCELED,
        }:
            workflow.ended_at = None
        if workflow.started_at is None:
            workflow.started_at = now
    await _sync_meeting_processing_status(db, workspace_id=workspace_id, meeting_id=meeting_id, status=status)
    await db.commit()
    return workflow


async def set_workflow_status(
    db: AsyncSession,
    workflow: ProcessingWorkflow,
    status: ProcessingStatus,
    *,
    reason_code: str | None = None,
    terminal: bool = False,
) -> ProcessingWorkflow:
    workflow.status = status.value
    workflow.last_reason_code = reason_code
    workflow.attempt_count += 1
    if terminal:
        workflow.ended_at = datetime.now(UTC)
    await _sync_meeting_processing_status(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
        status=status,
    )
    await db.commit()
    return workflow


async def _sync_meeting_processing_status(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    status: ProcessingStatus,
) -> None:
    meeting = await db.get(Meeting, meeting_id)
    if meeting is not None:
        meeting.processing_status = status.value
    placeholder = await db.scalar(
        select(ProcessingPlaceholder).where(
            ProcessingPlaceholder.workspace_id == workspace_id,
            ProcessingPlaceholder.meeting_id == meeting_id,
        )
    )
    if placeholder is not None:
        placeholder.status = status.value


async def get_mediascribe_job(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
) -> MediaScribeJob | None:
    query = select(MediaScribeJob).where(
        MediaScribeJob.workspace_id == workspace_id,
        MediaScribeJob.meeting_id == meeting_id,
    )
    if media_revision_id is not None:
        query = query.where(MediaScribeJob.media_revision_id == media_revision_id)
    return await db.scalar(query)


async def upsert_mediascribe_job(
    db: AsyncSession,
    *,
    workflow: ProcessingWorkflow,
    mic_artifact: TrackArtifact | None = None,
    incoming_artifact: TrackArtifact | None = None,
    source_artifact: TrackArtifact | None = None,
    request_mode: str = "dual_track",
) -> MediaScribeJob:
    if request_mode == "dual_track" and (mic_artifact is None or incoming_artifact is None):
        raise ValueError("dual_track_requires_artifact_pair")
    if request_mode == "single_track" and source_artifact is None:
        raise ValueError("single_track_requires_source_artifact")
    job = await get_mediascribe_job(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
        media_revision_id=workflow.media_revision_id,
    )
    if job is None and workflow.media_revision_id is not None:
        job = await get_mediascribe_job(
            db,
            workspace_id=workflow.workspace_id,
            meeting_id=workflow.meeting_id,
        )
    if job is None:
        job = MediaScribeJob(
            workspace_id=workflow.workspace_id,
            meeting_id=workflow.meeting_id,
            media_revision_id=workflow.media_revision_id,
            processing_workflow_id=workflow.id,
            mic_track_artifact_id=mic_artifact.id if mic_artifact is not None else None,
            incoming_track_artifact_id=incoming_artifact.id if incoming_artifact is not None else None,
            source_track_artifact_id=source_artifact.id if source_artifact is not None else None,
            status=MediaScribeJobStatus.NOT_SUBMITTED.value,
            request_mode=request_mode,
            diarize=True,
            summarize=False,
        )
        db.add(job)
        await db.commit()
    elif workflow.media_revision_id is not None and job.media_revision_id is None:
        job.media_revision_id = workflow.media_revision_id
        await db.commit()
    elif job.external_job_id is None:
        job.request_mode = request_mode
        job.mic_track_artifact_id = mic_artifact.id if mic_artifact is not None else None
        job.incoming_track_artifact_id = incoming_artifact.id if incoming_artifact is not None else None
        job.source_track_artifact_id = source_artifact.id if source_artifact is not None else None
        await db.commit()
    return job


async def persist_mediascribe_submission(
    db: AsyncSession,
    *,
    job: MediaScribeJob,
    external_job_id: str,
    status: MediaScribeJobStatus,
) -> MediaScribeJob:
    job.external_job_id = external_job_id
    job.status = status.value
    job.submitted_at = job.submitted_at or datetime.now(UTC)
    job.failed_at = None
    job.last_error_code = None
    job.last_error_message = None
    await db.commit()
    return job


async def update_mediascribe_job_status(
    db: AsyncSession,
    *,
    job: MediaScribeJob,
    status: MediaScribeJobStatus,
    reason_code: str | None = None,
    error_message: str | None = None,
) -> MediaScribeJob:
    now = datetime.now(UTC)
    job.status = status.value
    job.last_polled_at = now
    job.last_error_code = reason_code
    job.last_error_message = error_message
    if status == MediaScribeJobStatus.READY:
        job.ready_at = now
    if status in {MediaScribeJobStatus.FAILED, MediaScribeJobStatus.BLOCKED}:
        job.failed_at = now
    await db.commit()
    return job


async def persist_processing_result(
    db: AsyncSession,
    *,
    job: MediaScribeJob,
    result: MediaScribeResult,
    source_result_hash: str,
) -> ProcessingResult:
    existing = await db.scalar(
        select(ProcessingResult).where(
            ProcessingResult.workspace_id == job.workspace_id,
            ProcessingResult.mediascribe_job_id == job.id,
            ProcessingResult.result_version == result.result_version,
        )
    )
    if existing is None:
        existing = ProcessingResult(
            workspace_id=job.workspace_id,
            meeting_id=job.meeting_id,
            media_revision_id=job.media_revision_id,
            mediascribe_job_id=job.id,
            result_version=result.result_version,
        )
        db.add(existing)
        await db.flush()
    elif job.media_revision_id is not None and existing.media_revision_id is None:
        existing.media_revision_id = job.media_revision_id
    elif existing.source_result_hash == source_result_hash and existing.status == ProcessingResultStatus.IMPORTED.value:
        return existing
    else:
        await db.execute(delete(TranscriptSegment).where(TranscriptSegment.processing_result_id == existing.id))
        await db.execute(delete(DiarizationSegment).where(DiarizationSegment.processing_result_id == existing.id))

    existing.status = ProcessingResultStatus.IMPORTED.value
    existing.transcript_status = result.transcript_status.value
    existing.diarization_status = (
        ProcessingAvailabilityStatus.AVAILABLE.value if result.diarization else ProcessingAvailabilityStatus.UNAVAILABLE.value
    )
    existing.summary_status = result.summary_status.value
    existing.language = result.language
    existing.segment_count = len(result.transcript)
    existing.diarization_segment_count = len(result.diarization)
    existing.failure_reason = result.failure_reason
    existing.failure_source = result.failure_source
    existing.source_result_hash = source_result_hash
    existing.imported_at = datetime.now(UTC)

    for segment in result.transcript:
        db.add(
            TranscriptSegment(
                processing_result_id=existing.id,
                workspace_id=job.workspace_id,
                meeting_id=job.meeting_id,
                sequence=segment.sequence,
                start_seconds=Decimal(str(segment.start_seconds)),
                end_seconds=Decimal(str(segment.end_seconds)),
                text=segment.text,
                source_role=segment.source_role,
                source_role_original=segment.source_role_original,
            )
        )
    for segment in result.diarization:
        db.add(
            DiarizationSegment(
                processing_result_id=existing.id,
                workspace_id=job.workspace_id,
                meeting_id=job.meeting_id,
                sequence=segment.sequence,
                start_seconds=Decimal(str(segment.start_seconds)),
                end_seconds=Decimal(str(segment.end_seconds)),
                speaker_label=segment.speaker_label,
                text=segment.text,
                source_role=segment.source_role,
            )
        )
    await set_dependency_state(
        db,
        workspace_id=job.workspace_id,
        meeting_id=job.meeting_id,
        media_revision_id=job.media_revision_id,
        dependency=ProcessingDependencyName.MEDIASCRIBE,
        state=ProcessingDependencyStateValue.IMPORTED,
        external_reference=job.external_job_id,
    )
    await db.commit()
    return existing


async def latest_processing_result(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
) -> ProcessingResult | None:
    query = select(ProcessingResult).where(
            ProcessingResult.workspace_id == workspace_id,
            ProcessingResult.meeting_id == meeting_id,
    )
    if media_revision_id is not None:
        query = query.where(ProcessingResult.media_revision_id == media_revision_id)
    return await db.scalar(query.order_by(ProcessingResult.imported_at.desc()))


async def record_processing_audit_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_type: str,
    meeting_id: UUID | None = None,
    processing_workflow_id: UUID | None = None,
    mediascribe_job_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    metadata: dict[str, object] | None = None,
) -> ProcessingAuditEvent:
    event = ProcessingAuditEvent(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        processing_workflow_id=processing_workflow_id,
        mediascribe_job_id=mediascribe_job_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        metadata_json=safe_audit_metadata(metadata or {}),
    )
    db.add(event)
    await db.commit()
    return event


async def set_dependency_state(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
    dependency: ProcessingDependencyName,
    state: ProcessingDependencyStateValue,
    external_reference: str | None = None,
    notes: str | None = None,
) -> ProcessingDependencyState:
    existing = await db.scalar(
        select(ProcessingDependencyState).where(
            ProcessingDependencyState.workspace_id == workspace_id,
            ProcessingDependencyState.meeting_id == meeting_id,
            ProcessingDependencyState.dependency == dependency.value,
        )
    )
    if existing is None:
        existing = ProcessingDependencyState(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            dependency=dependency.value,
        )
        db.add(existing)
    elif media_revision_id is not None:
        existing.media_revision_id = media_revision_id
    existing.state = state.value
    existing.external_reference = external_reference
    existing.notes = notes
    existing.last_verified_at = datetime.now(UTC)
    await db.commit()
    return existing


def summary_status_from_result(result: ProcessingResult | None) -> SummaryStatus:
    if result is None:
        return SummaryStatus.NOT_REQUESTED
    return SummaryStatus(result.summary_status)
