from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import delete, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.entitlements import effective_plan_code, entitlement_for_plan
from twobrain_rec_server.billing.source_lifecycle import (
    TRANSIENT_HARD_LIFETIME,
    TRANSIENT_PURGE_AFTER,
    mark_source_transcript_imported,
)
from twobrain_rec_server.billing.usage import (
    QuotaExceeded,
    SourceRange,
    commit_free_usage_ranges,
    find_free_usage_reservation,
    release_free_usage,
    reserve_free_usage,
)
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MediaRevision,
    MediaScribeJob,
    Meeting,
    PlaybackNormalizationJob,
    ProcessingAuditEvent,
    ProcessingDependencyState,
    ProcessingPlaceholder,
    ProcessingResult,
    ProcessingWorkflow,
    TrackArtifact,
    TranscriptSegment,
    WorkspaceSubscription,
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
    source_fingerprint_for_revision,
)
from twobrain_rec_server.mediascribe.client import MediaScribeClientError
from twobrain_rec_server.mediascribe.downloads import safe_download_references
from twobrain_rec_server.mediascribe.schemas import MediaScribeResult
from twobrain_rec_server.normalization.statuses import (
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
    JobState,
)
from twobrain_rec_server.processing.audit import (
    safe_audit_metadata,
    validate_processing_aggregate_event,
)
from twobrain_rec_server.processing.fences import (
    is_legacy_lineage,
    legacy_source_fingerprint,
    lock_meeting_fence,
    meeting_is_deleted_or_deleting,
    record_stale_lifecycle_event,
)
from twobrain_rec_server.processing.lifecycle import (
    TERMINAL_PROCESSING_STATUSES,
    can_transition,
)
from twobrain_rec_server.processing.reasons import (
    BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
    BLOCKED_TEMPORAL_UNAVAILABLE,
)
from twobrain_rec_server.processing.recovery import (
    DEFAULT_DEADLINE,
    schedule_retry,
    schedule_retry_with_settings,
)
from twobrain_rec_server.processing.results import (
    effective_processing_result_query,
    result_is_terminal_input,
)


class ProcessingLifecycleBlocked(RuntimeError):
    """The deletion/source fence won while a provider result was in flight."""


MEDIASCRIBE_SUBMISSION_WAIT_SECONDS = 35.0
MEDIASCRIBE_SUBMISSION_CLAIM_STALE_AFTER = timedelta(minutes=2)
PROCESSING_MANUAL_CHECK_CLAIM_LEASE = timedelta(minutes=2)
_PROVENANCE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:+/-]{1,160}$")
_PROVENANCE_TOKEN_FIELDS = (
    "asr_model_version",
    "diarization_model_version",
    "alignment_algorithm_version",
    "quality_state",
    "worker_build_sha",
    "worker_image_digest",
    "service_version",
    "build_sha",
    "image_digest",
)


def _safe_provenance_projection(result: MediaScribeResult) -> dict[str, object] | None:
    """Persist only bounded provider metadata, never Pydantic extras/content."""

    provenance = result.provenance
    if provenance is None:
        return None
    projected: dict[str, object] = {}
    for field in _PROVENANCE_TOKEN_FIELDS:
        value = getattr(provenance, field, None)
        if isinstance(value, str) and _PROVENANCE_TOKEN_RE.fullmatch(value):
            projected[field] = value
    if (
        isinstance(provenance.detected_speaker_count, int)
        and 0 <= provenance.detected_speaker_count <= 128
    ):
        projected["detected_speaker_count"] = provenance.detected_speaker_count
    if isinstance(provenance.quality_reasons, list):
        reasons = [
            item
            for item in provenance.quality_reasons
            if isinstance(item, str) and _PROVENANCE_TOKEN_RE.fullmatch(item)
        ][:16]
        if reasons:
            projected["quality_reasons"] = reasons
    for field in ("word_timestamps_present", "word_timestamps_complete", "provenance_complete"):
        value = getattr(provenance, field, None)
        if isinstance(value, bool):
            projected[field] = value
    parameters = provenance.effective_diarization_parameters
    if isinstance(parameters, dict):
        safe_parameters = {
            key: value
            for key, value in parameters.items()
            if isinstance(key, str)
            and _PROVENANCE_TOKEN_RE.fullmatch(key)
            and (
                isinstance(value, bool)
                or (isinstance(value, int) and 0 <= value <= 128)
                or (isinstance(value, str) and _PROVENANCE_TOKEN_RE.fullmatch(value))
            )
        }
        if safe_parameters:
            projected["effective_diarization_parameters"] = safe_parameters
    return projected or None


def processing_request_fingerprint(
    *,
    request_mode: str,
    source_fingerprint: str | None,
    mic_artifact: TrackArtifact | None,
    incoming_artifact: TrackArtifact | None,
    source_artifact: TrackArtifact | None,
    diarize: bool,
    summarize: bool,
    speaker_count_mode: str | None,
    num_speakers: int | None,
) -> str:
    """Hash only bounded inputs that determine the multipart request body."""

    def artifact_snapshot(artifact: TrackArtifact | None) -> dict[str, object] | None:
        if artifact is None:
            return None
        return {
            "sha256": artifact.sha256,
            "byte_length": int(artifact.byte_length),
            "codec": artifact.codec,
        }

    material = {
        "request_mode": request_mode,
        "source_fingerprint": source_fingerprint,
        "artifacts": {
            "mic": artifact_snapshot(mic_artifact),
            "incoming": artifact_snapshot(incoming_artifact),
            "source": artifact_snapshot(source_artifact),
        },
        "diarize": bool(diarize),
        "summarize": bool(summarize),
        "speaker_count_mode": speaker_count_mode,
        "num_speakers": num_speakers,
    }
    return hashlib.sha256(
        json.dumps(material, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class ProcessingManualCheckClaim:
    """The durable result of attempting one manual same-job check claim."""

    request_result: str
    command_id: str
    same_job_check: bool = False
    claimed: bool = False
    workflow: ProcessingWorkflow | None = None


_PROCESSING_MANUAL_CHECK_ACTIVE_STATES = {
    ProcessingStatus.STARTING.value,
    ProcessingStatus.WORKFLOW_STARTED.value,
    ProcessingStatus.SUBMITTING.value,
    ProcessingStatus.SUBMITTED.value,
    ProcessingStatus.POLLING.value,
    ProcessingStatus.IMPORTING.value,
}
_PROCESSING_MANUAL_CHECK_RETRY_STATES = {
    ProcessingStatus.WAITING_RETRY.value,
    ProcessingStatus.FAILED_RETRYABLE.value,
    ProcessingStatus.BLOCKED_UNKNOWN.value,
}
_PROCESSING_MANUAL_CHECK_TERMINAL_STATES = {
    ProcessingStatus.PROCESSED.value,
    ProcessingStatus.FAILED_TERMINAL.value,
    ProcessingStatus.CANCELED.value,
}
_UNKNOWN_SUBMISSION_OUTCOME = BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN

_PROCESSING_NEW_ATTEMPT_ACTIVE_STATES = {
    ProcessingStatus.STARTING.value,
    ProcessingStatus.WORKFLOW_STARTED.value,
    ProcessingStatus.SUBMITTING.value,
    ProcessingStatus.SUBMITTED.value,
    ProcessingStatus.POLLING.value,
    ProcessingStatus.IMPORTING.value,
    ProcessingStatus.WAITING_RETRY.value,
    ProcessingStatus.FAILED_RETRYABLE.value,
}
_PROCESSING_NEW_ATTEMPT_CONFIGURATION_REASONS = {
    "blocked_config",
    "blocked_mediascribe_unavailable",
    "mediascribe_auth_failed",
}


def _processing_manual_command_id(
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
    workflow_id: str | None,
    command_key: str | None,
    command_version: int,
) -> str:
    """Return a stable, non-sensitive Temporal command identifier."""

    supplied = command_key.strip() if isinstance(command_key, str) else ""
    seed = supplied or f"slot:{workflow_id or 'missing'}:{command_version}"
    material = "|".join(
        (
            str(workspace_id),
            str(meeting_id),
            str(media_revision_id) if media_revision_id is not None else "legacy",
            seed,
        )
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return f"processing-check-{digest}"


async def claim_processing_manual_check(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
    command_key: str | None = None,
    expected_schedule_generation: int | None = None,
) -> ProcessingManualCheckClaim:
    """Atomically claim one user check and invalidate the old durable timer.

    The meeting fence is acquired before the workflow and provider-job locks.
    ``BLOCKED_UNKNOWN`` is deliberately allowed with only its durable
    idempotency key: the next worker operation is reconciliation, never a new
    multipart upload.
    """

    meeting = await lock_meeting_fence(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    if meeting is None:
        return ProcessingManualCheckClaim(
            request_result="not_safe",
            command_id=_processing_manual_command_id(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=None,
                command_key=command_key,
                command_version=0,
            ),
        )
    if meeting_is_deleted_or_deleting(meeting):
        return ProcessingManualCheckClaim(
            request_result="not_safe",
            command_id=_processing_manual_command_id(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=None,
                command_key=command_key,
                command_version=0,
            ),
        )

    current_revision = await latest_media_revision_for_meeting(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    current_revision_id = current_revision.id if current_revision is not None else None
    if current_revision_id != media_revision_id:
        return ProcessingManualCheckClaim(
            request_result="stale_schedule",
            command_id=_processing_manual_command_id(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=None,
                command_key=command_key,
                command_version=0,
            ),
        )

    workflow_query = (
        select(ProcessingWorkflow)
        .where(
            ProcessingWorkflow.workspace_id == workspace_id,
            ProcessingWorkflow.meeting_id == meeting_id,
            ProcessingWorkflow.media_revision_id == media_revision_id
            if media_revision_id is not None
            else ProcessingWorkflow.media_revision_id.is_(None),
            ProcessingWorkflow.purpose == "transcription",
        )
        .order_by(
            ProcessingWorkflow.attempt_ordinal.desc(),
            ProcessingWorkflow.created_at.desc(),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    workflow = await db.scalar(workflow_query)
    if workflow is None:
        return ProcessingManualCheckClaim(
            request_result="not_safe",
            command_id=_processing_manual_command_id(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=None,
                command_key=command_key,
                command_version=0,
            ),
        )

    command_version = int(workflow.manual_command_version or 0)
    command_id = _processing_manual_command_id(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        workflow_id=workflow.workflow_id,
        command_key=command_key,
        command_version=command_version
        if workflow.status in _PROCESSING_MANUAL_CHECK_ACTIVE_STATES
        else command_version + 1,
    )
    status_value = getattr(workflow.status, "value", workflow.status)

    if status_value in _PROCESSING_MANUAL_CHECK_ACTIVE_STATES:
        claimed_at = workflow.manual_claimed_at
        now = datetime.now(UTC)
        if (
            claimed_at is None
            or claimed_at.tzinfo is None
            or now - claimed_at < PROCESSING_MANUAL_CHECK_CLAIM_LEASE
        ):
            return ProcessingManualCheckClaim(
                request_result="already_in_flight",
                command_id=command_id,
                same_job_check=True,
                workflow=workflow,
            )
        # The API may have died after the DB claim and before Temporal accepted
        # the update. Reopen the same business attempt; the provider job/key
        # remains fenced and no new multipart upload can be created.
        workflow.manual_claimed_at = None
        workflow.manual_claimed_by = None
        workflow.manual_command_version = command_version + 1
        workflow.schedule_generation = int(workflow.schedule_generation or 0) + 1
        workflow.next_attempt_at = None
        workflow.next_attempt_source = None
        workflow.retry_class = "unknown_outcome" if status_value == ProcessingStatus.BLOCKED_UNKNOWN.value else "retryable"
        workflow.status = ProcessingStatus.WAITING_RETRY.value
        workflow.last_reason_code = "manual_check_claim_expired"
        status_value = ProcessingStatus.WAITING_RETRY.value
        command_id = _processing_manual_command_id(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            workflow_id=workflow.workflow_id,
            command_key=command_key,
            command_version=int(workflow.manual_command_version),
        )
    if status_value in _PROCESSING_MANUAL_CHECK_TERMINAL_STATES:
        return ProcessingManualCheckClaim(
            request_result="stale_schedule",
            command_id=command_id,
            same_job_check=False,
            workflow=workflow,
        )
    if status_value not in _PROCESSING_MANUAL_CHECK_RETRY_STATES:
        return ProcessingManualCheckClaim(
            request_result="not_safe",
            command_id=command_id,
            workflow=workflow,
        )
    if (
        expected_schedule_generation is not None
        and int(workflow.schedule_generation or 0) != expected_schedule_generation
    ):
        return ProcessingManualCheckClaim(
            request_result="stale_schedule",
            command_id=command_id,
            workflow=workflow,
        )

    job = await get_mediascribe_job(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        processing_workflow_id=workflow.id,
        active_only=False,
        for_update=True,
    )
    has_same_job = bool(
        job is not None
        and (
            (isinstance(job.external_job_id, str) and bool(job.external_job_id.strip()))
            or (isinstance(job.idempotency_key, str) and bool(job.idempotency_key.strip()))
        )
    )
    unknown_reconciliation = (
        status_value == ProcessingStatus.BLOCKED_UNKNOWN.value
        and job is not None
        and job.last_error_code == _UNKNOWN_SUBMISSION_OUTCOME
    )
    if job is None or not has_same_job:
        return ProcessingManualCheckClaim(
            request_result="not_safe",
            command_id=command_id,
            workflow=workflow,
        )
    job_status = getattr(job.status, "value", job.status)
    if job_status in {
        MediaScribeJobStatus.FAILED.value,
        MediaScribeJobStatus.DELETING.value,
    } or (job_status == MediaScribeJobStatus.BLOCKED.value and not unknown_reconciliation):
        return ProcessingManualCheckClaim(
            request_result="not_safe",
            command_id=command_id,
            same_job_check=has_same_job,
            workflow=workflow,
        )
    if not unknown_reconciliation and not (job.external_job_id or job.idempotency_key):
        return ProcessingManualCheckClaim(
            request_result="not_safe",
            command_id=command_id,
            same_job_check=has_same_job,
            workflow=workflow,
        )

    now = datetime.now(UTC)
    workflow.schedule_generation = int(workflow.schedule_generation or 0) + 1
    workflow.manual_command_version = command_version + 1
    workflow.stage = "status"
    workflow.next_attempt_at = None
    workflow.next_attempt_source = "manual_override"
    workflow.manual_claimed_at = now
    workflow.manual_claimed_by = "user"
    workflow.retry_class = "unknown_outcome" if unknown_reconciliation else "retryable"
    try:
        workflow = await set_workflow_status(
            db,
            workflow,
            ProcessingStatus.POLLING,
            reason_code="manual_processing_check",
        )
    except ProcessingLifecycleBlocked:
        return ProcessingManualCheckClaim(
            request_result="not_safe",
            command_id=command_id,
            same_job_check=has_same_job,
            workflow=workflow,
        )
    return ProcessingManualCheckClaim(
        request_result="accepted",
        command_id=command_id,
        same_job_check=True,
        claimed=True,
        workflow=workflow,
    )


async def release_processing_manual_check_claim(
    db: AsyncSession,
    *,
    workflow_id: UUID,
    manual_command_version: int,
    reason_code: str = "processing_manual_check_dispatch_unavailable",
    settings: object | None = None,
) -> bool:
    """Return a claimed check to a safe recoverable projection if dispatch fails."""

    workflow = await db.scalar(
        select(ProcessingWorkflow)
        .where(ProcessingWorkflow.id == workflow_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if workflow is None or workflow.status != ProcessingStatus.POLLING.value:
        await db.commit()
        return False
    if int(workflow.manual_command_version or 0) != manual_command_version:
        await db.commit()
        return False
    workflow.manual_claimed_at = None
    workflow.manual_claimed_by = None
    unknown_reconciliation = (
        workflow.retry_class == "unknown_outcome"
    )
    workflow.retry_class = "unknown_outcome" if unknown_reconciliation else "retryable"
    scheduler = schedule_retry_with_settings if settings is not None else schedule_retry
    schedule_kwargs = {
        "now": datetime.now(UTC),
        "retry_count": int(workflow.retry_count or 0),
        "generation": int(workflow.schedule_generation or 0),
        "deadline_at": workflow.deadline_at,
        "source": "manual_dispatch_failure",
    }
    schedule = (
        scheduler(settings, **schedule_kwargs)
        if settings is not None
        else scheduler(**schedule_kwargs)
    )
    workflow.next_attempt_at = schedule.next_attempt_at
    workflow.next_attempt_source = schedule.source
    workflow.schedule_generation = schedule.generation
    workflow.retry_count = schedule.retry_count
    if schedule.next_attempt_at is None:
        if unknown_reconciliation:
            workflow.retry_class = "unknown_outcome"
            await set_workflow_status(
                db,
                workflow,
                ProcessingStatus.BLOCKED_UNKNOWN,
                reason_code="processing_recovery_attempt_limit_exceeded",
            )
            return True
        workflow.retry_class = "terminal"
        await set_workflow_status(
            db,
            workflow,
            ProcessingStatus.FAILED_TERMINAL,
            reason_code="processing_recovery_attempt_limit_exceeded",
            terminal=True,
        )
        return True
    await set_workflow_status(
        db,
        workflow,
        ProcessingStatus.BLOCKED_UNKNOWN if unknown_reconciliation else ProcessingStatus.WAITING_RETRY,
        reason_code=reason_code,
    )
    return True


@dataclass(frozen=True, slots=True)
class ProcessingSourceArtifacts:
    """Immutable source selection for one revision.

    The mic/incoming fields are a compatibility drain for pre-v5 accepted
    revisions only. New first-party capture uses source_artifact as one
    canonical WAV and never selects a playback artifact for processing.
    """

    request_mode: str
    source_kind: str
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

    @property
    def is_v5_mixed_recording(self) -> bool:
        return self.source_kind == MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value


@dataclass(frozen=True, slots=True)
class ManualUploadPreparation:
    state: str
    reason_code: str | None = None
    next_attempt_at: datetime | None = None
    source: ProcessingSourceArtifacts | None = None


async def load_manual_upload_preparation(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
) -> ManualUploadPreparation | None:
    if media_revision_id is None:
        return None
    revision = await db.scalar(
        select(MediaRevision).where(
            MediaRevision.id == media_revision_id,
            MediaRevision.workspace_id == workspace_id,
            MediaRevision.meeting_id == meeting_id,
            MediaRevision.status == MediaRevisionStatus.ACCEPTED.value,
            MediaRevision.immutable.is_(True),
        )
    )
    if revision is None or revision.source_kind != MediaRevisionSourceKind.MANUAL_UPLOAD.value:
        return None

    job = await db.scalar(
        select(PlaybackNormalizationJob).where(
            PlaybackNormalizationJob.workspace_id == workspace_id,
            PlaybackNormalizationJob.meeting_id == meeting_id,
            PlaybackNormalizationJob.media_revision_id == media_revision_id,
            PlaybackNormalizationJob.profile_version == CANONICAL_PROFILE_VERSION,
        )
    )
    if job is None:
        return None
    if job.state in {
        JobState.QUEUED.value,
        JobState.RUNNING.value,
        JobState.PUBLISHING.value,
        JobState.RETRY_WAIT.value,
    }:
        return ManualUploadPreparation(
            state="pending",
            reason_code=job.reason_code or "normalization_queued",
            next_attempt_at=job.next_attempt_at,
        )
    if job.state != JobState.READY.value or job.canonical_track_artifact_id is None:
        return ManualUploadPreparation(
            state="cancelled" if job.state == JobState.CANCELLED.value else "terminal",
            reason_code=job.reason_code or "normalization_failed",
        )

    artifact = await db.scalar(
        select(TrackArtifact).where(
            TrackArtifact.id == job.canonical_track_artifact_id,
            TrackArtifact.workspace_id == workspace_id,
            TrackArtifact.meeting_id == meeting_id,
            TrackArtifact.media_revision_id == media_revision_id,
            TrackArtifact.track_role == TrackRole.PLAYBACK.value,
            TrackArtifact.status == "stored",
            TrackArtifact.codec == "m4a-aac-lc",
            TrackArtifact.normalization_profile_version == CANONICAL_PROFILE_VERSION,
            TrackArtifact.validation_version == VALIDATION_VERSION,
            TrackArtifact.validated_at.is_not(None),
            TrackArtifact.source_fingerprint_sha256 == job.source_fingerprint_sha256,
        )
    )
    if artifact is None:
        return ManualUploadPreparation(
            state="terminal",
            reason_code="canonical_artifact_missing",
        )
    return ManualUploadPreparation(
        state="ready",
        source=ProcessingSourceArtifacts(
            request_mode="single_track",
            source_kind=revision.source_kind,
            source_artifact=artifact,
        ),
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
            MediaRevision.status == MediaRevisionStatus.ACCEPTED.value,
            MediaRevision.immutable.is_(True),
        )
        .order_by(desc(MediaRevision.revision_number), desc(MediaRevision.updated_at))
    )


@dataclass(frozen=True, slots=True)
class ProcessingAttemptCreation:
    """Result of the atomic user-authorized new-attempt admission."""

    result: str
    workflow: ProcessingWorkflow | None = None
    media_revision_id: UUID | None = None
    attempt_ordinal: int | None = None


async def _reserve_processing_attempt_quota(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    media_revision: MediaRevision,
) -> bool:
    """Reuse the revision reservation, or admit one new bounded reservation.

    A new business attempt must not consume quota twice for the same source
    lineage.  The reservation key is therefore revision-scoped, while the
    provider idempotency key remains attempt-scoped in ``upsert_mediascribe_job``.
    The caller owns the surrounding transaction; this helper never commits.
    """

    duration_seconds = media_revision.duration_seconds
    if (
        not isinstance(duration_seconds, int)
        or isinstance(duration_seconds, bool)
        or duration_seconds <= 0
    ):
        return False
    reservation_key = f"processing:{media_revision.id}"
    now = datetime.now(UTC)
    reservation = await find_free_usage_reservation(
        db,
        workspace_id=workspace_id,
        reservation_key=reservation_key,
    )
    if reservation is not None:
        if reservation.state == "committed":
            return True
        if reservation.state == "active":
            if reservation.expires_at is None or reservation.expires_at > now:
                return True
            await release_free_usage(db, reservation_id=reservation.id)
        if reservation.state == "released" and reservation.committed_seconds >= reservation.declared_seconds:
            return True

    subscription = await db.scalar(
        select(WorkspaceSubscription)
        .where(WorkspaceSubscription.workspace_id == workspace_id)
        .with_for_update()
    )
    effective_plan = effective_plan_code(
        plan_code=(subscription.plan_code if subscription is not None else "free"),
        state=(subscription.state if subscription is not None else "free"),
        now=now,
        paid_through=subscription.paid_through if subscription is not None else None,
        trial_ends_at=subscription.trial_ends_at if subscription is not None else None,
    )
    if entitlement_for_plan(plan_code=effective_plan).processing_unlimited:
        return True
    try:
        await reserve_free_usage(
            db,
            workspace_id=workspace_id,
            reservation_key=reservation_key,
            declared_seconds=duration_seconds,
            now=now,
            expires_at=now + timedelta(hours=24),
        )
    except QuotaExceeded:
        return False
    return True


async def create_processing_attempt(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    deadline_seconds: int | None = None,
) -> ProcessingAttemptCreation:
    """Admit exactly one fresh attempt after a confirmed terminal failure.

    Meeting is the first lifecycle fence.  All revision-scoped workflow rows
    are then locked and the newest one is authoritative.  The old terminal
    workflow, its provider job, and its result are never mutated or reused.
    This function intentionally leaves commit/rollback to the API boundary so
    Temporal dispatch can be compensated before the new row becomes visible.
    """

    meeting = await lock_meeting_fence(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    if meeting is None:
        return ProcessingAttemptCreation(result="meeting_not_found")
    if meeting_is_deleted_or_deleting(meeting):
        return ProcessingAttemptCreation(result="deletion_closed")

    media_revision = await latest_media_revision_for_meeting(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    if media_revision is None:
        return ProcessingAttemptCreation(result="source_unavailable")
    try:
        source_fingerprint = source_fingerprint_for_revision(media_revision)
    except ValueError:
        return ProcessingAttemptCreation(
            result="source_unavailable",
            media_revision_id=media_revision.id,
        )
    workflows = (
        await db.scalars(
            select(ProcessingWorkflow)
            .where(
                ProcessingWorkflow.workspace_id == workspace_id,
                ProcessingWorkflow.meeting_id == meeting_id,
                ProcessingWorkflow.media_revision_id == media_revision.id,
                ProcessingWorkflow.purpose == "transcription",
            )
            .order_by(
                ProcessingWorkflow.attempt_ordinal.desc(),
                ProcessingWorkflow.created_at.desc(),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    # Purge reconciliation locks the same workflow rows. Check the shared
    # revision source only after that lock so retry cannot race a deletion.
    if await load_processing_source(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision.id,
    ) is None:
        return ProcessingAttemptCreation(
            result="source_unavailable",
            media_revision_id=media_revision.id,
        )
    if not workflows:
        return ProcessingAttemptCreation(
            result="not_terminal",
            media_revision_id=media_revision.id,
        )
    current = workflows[0]
    current_status = getattr(current.status, "value", current.status)
    current_result = await latest_processing_result(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision.id,
    )
    terminal_input_result_is_terminal = bool(
        current_result is not None
        and current_result.media_revision_id == media_revision.id
        and current_result.processing_workflow_id == current.id
        and result_is_terminal_input(current_result)
    )
    if current_status == ProcessingStatus.BLOCKED_UNKNOWN.value and not terminal_input_result_is_terminal:
        return ProcessingAttemptCreation(
            result="unknown_outcome",
            workflow=current,
            media_revision_id=media_revision.id,
            attempt_ordinal=int(current.attempt_ordinal or 1),
        )
    if current_status in _PROCESSING_NEW_ATTEMPT_ACTIVE_STATES and not terminal_input_result_is_terminal:
        return ProcessingAttemptCreation(
            result="already_in_flight",
            workflow=current,
            media_revision_id=media_revision.id,
            attempt_ordinal=int(current.attempt_ordinal or 1),
        )
    if (
        current_status != ProcessingStatus.FAILED_TERMINAL.value
        and not terminal_input_result_is_terminal
    ):
        return ProcessingAttemptCreation(
            result=(
                "configuration_failure"
                if current_status == ProcessingStatus.BLOCKED.value
                else "not_terminal"
            ),
            workflow=current,
            media_revision_id=media_revision.id,
            attempt_ordinal=int(current.attempt_ordinal or 1),
        )
    if (
        not terminal_input_result_is_terminal
        and (
            current.last_reason_code in _PROCESSING_NEW_ATTEMPT_CONFIGURATION_REASONS
            or (
                (current.last_reason_code or "").startswith("blocked_")
                and current.last_reason_code != BLOCKED_TEMPORAL_UNAVAILABLE
            )
        )
    ):
        return ProcessingAttemptCreation(
            result="configuration_failure",
            workflow=current,
            media_revision_id=media_revision.id,
            attempt_ordinal=int(current.attempt_ordinal or 1),
        )
    if int(current.deletion_epoch_at_start or 0) != int(meeting.deletion_epoch or 0):
        return ProcessingAttemptCreation(
            result="deletion_closed",
            workflow=current,
            media_revision_id=media_revision.id,
            attempt_ordinal=int(current.attempt_ordinal or 1),
        )
    if current.source_fingerprint not in {None, source_fingerprint}:
        return ProcessingAttemptCreation(
            result="source_unavailable",
            workflow=current,
            media_revision_id=media_revision.id,
            attempt_ordinal=int(current.attempt_ordinal or 1),
        )
    if (
        not current.archive_audio
        and current.transient_hard_deadline is not None
        and current.transient_hard_deadline <= datetime.now(UTC)
    ):
        return ProcessingAttemptCreation(
            result="source_expired",
            workflow=current,
            media_revision_id=media_revision.id,
            attempt_ordinal=int(current.attempt_ordinal or 1),
        )
    if terminal_input_result_is_terminal and current_status not in {
        ProcessingStatus.PROCESSED.value,
        ProcessingStatus.BLOCKED.value,
        ProcessingStatus.FAILED_TERMINAL.value,
        ProcessingStatus.CANCELED.value,
    }:
        now = datetime.now(UTC)
        current.status = ProcessingStatus.FAILED_TERMINAL.value
        current.retry_class = "terminal"
        current.last_reason_code = current_result.failure_reason
        current.next_attempt_at = None
        current.next_attempt_source = None
        current.manual_claimed_at = None
        current.manual_claimed_by = None
        current.attempt_count = int(current.attempt_count or 0) + 1
        current.ended_at = now
        if not current.archive_audio:
            _mark_transient_terminal(current, now=now)
        await release_processing_usage_reservation(
            db,
            workspace_id=current.workspace_id,
            media_revision_id=current.media_revision_id,
            meeting_id=current.meeting_id,
        )
        # Release the partial unique active-workflow slot before inserting the
        # fresh attempt. Both changes remain atomic in the caller transaction.
        await db.flush([current])
    if not await _reserve_processing_attempt_quota(
        db,
        workspace_id=workspace_id,
        media_revision=media_revision,
    ):
        return ProcessingAttemptCreation(
            result="quota_exceeded",
            workflow=current,
            media_revision_id=media_revision.id,
            attempt_ordinal=int(current.attempt_ordinal or 1),
        )
    if (
        not current.archive_audio
        and current.transient_hard_deadline is not None
        and current.transient_hard_deadline <= datetime.now(UTC)
    ):
        return ProcessingAttemptCreation(
            result="source_expired",
            workflow=current,
            media_revision_id=media_revision.id,
            attempt_ordinal=int(current.attempt_ordinal or 1),
        )

    now = datetime.now(UTC)
    attempt_ordinal = max(int(row.attempt_ordinal or 1) for row in workflows) + 1
    transient_admitted_at = current.transient_admitted_at or now
    from twobrain_rec_server.workflows.temporal_client import processing_workflow_id

    workflow = ProcessingWorkflow(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision.id,
        workflow_id=processing_workflow_id(media_revision.id, attempt_ordinal),
        purpose=current.purpose,
        source_fingerprint=source_fingerprint,
        deletion_epoch_at_start=int(meeting.deletion_epoch or 0),
        status=ProcessingStatus.STARTING.value,
        attempt_ordinal=attempt_ordinal,
        stage="submit",
        retry_class="none",
        archive_audio=bool(current.archive_audio),
        transient_state="processing" if not current.archive_audio else "not_applicable",
        transient_admitted_at=transient_admitted_at if not current.archive_audio else None,
        transient_hard_deadline=(
            current.transient_hard_deadline
            or transient_admitted_at + TRANSIENT_HARD_LIFETIME
            if not current.archive_audio
            else None
        ),
        attempt_count=1,
        last_reason_code="user_new_attempt",
        started_at=now,
        deadline_at=now + (
            timedelta(seconds=deadline_seconds)
            if deadline_seconds is not None
            else DEFAULT_DEADLINE
        ),
    )
    db.add(workflow)
    await db.flush()
    await _sync_meeting_processing_status(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision.id,
        status=ProcessingStatus.STARTING,
    )
    return ProcessingAttemptCreation(
        result="created",
        workflow=workflow,
        media_revision_id=media_revision.id,
        attempt_ordinal=attempt_ordinal,
    )


async def record_processing_attempt_run(
    db: AsyncSession,
    *,
    workflow_id: UUID,
    workflow_run_id: str | None,
) -> bool:
    """Persist Temporal's run reference without regressing lifecycle state."""

    workflow = await db.scalar(
        select(ProcessingWorkflow)
        .where(ProcessingWorkflow.id == workflow_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if workflow is None:
        await db.rollback()
        return False
    workflow.workflow_run_id = workflow_run_id
    await db.commit()
    return True


async def fail_processing_attempt_dispatch(
    db: AsyncSession,
    *,
    workflow_id: UUID,
    reason_code: str = "blocked_temporal_unavailable",
) -> bool:
    """Clear a pre-dispatch ``starting`` row without reopening terminal data."""

    workflow = await db.scalar(
        select(ProcessingWorkflow)
        .where(ProcessingWorkflow.id == workflow_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if workflow is None:
        await db.rollback()
        return False
    if workflow.status == ProcessingStatus.STARTING.value:
        now = datetime.now(UTC)
        # No provider request exists yet. Treat a failed Temporal dispatch as
        # a terminal business attempt so the user can safely start a fresh
        # attempt after infrastructure recovers; leaving it retryable without
        # a Temporal execution would make pickup/manual recovery a dead end.
        workflow.status = ProcessingStatus.FAILED_TERMINAL.value
        workflow.retry_class = "terminal"
        workflow.retry_count = int(workflow.retry_count or 0) + 1
        workflow.attempt_count = int(workflow.attempt_count or 0) + 1
        workflow.last_reason_code = reason_code
        workflow.next_attempt_at = None
        workflow.next_attempt_source = None
        workflow.ended_at = now
        if not workflow.archive_audio:
            _mark_transient_terminal(workflow, now=now)
        await release_processing_usage_reservation(
            db,
            workspace_id=workflow.workspace_id,
            media_revision_id=workflow.media_revision_id,
            meeting_id=workflow.meeting_id,
        )
        await _sync_meeting_processing_status(
            db,
            workspace_id=workflow.workspace_id,
            meeting_id=workflow.meeting_id,
            media_revision_id=workflow.media_revision_id,
            status=ProcessingStatus.FAILED_TERMINAL,
        )
        await db.commit()
        return True
    await db.commit()
    return False


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
    if revision.source_kind in {
        MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value,
        MediaRevisionSourceKind.MANUAL_UPLOAD.value,
        MediaRevisionSourceKind.LOCAL_TRIM.value,
        MediaRevisionSourceKind.REPLACE.value,
        MediaRevisionSourceKind.RESTORE.value,
        MediaRevisionSourceKind.REPROCESS.value,
        MediaRevisionSourceKind.VIDEO_CAPTURE.value,
    }:
        return ProcessingSourceArtifacts(
            request_mode="single_track",
            source_kind=revision.source_kind,
            source_artifact=artifacts_by_role[TrackRole.MEDIA.value],
        )
    if revision.source_kind == MediaRevisionSourceKind.INITIAL_RECORDING.value:
        # Historical compatibility only. New recordings are initial_mixed_recording
        # and take the canonical media branch above.
        return ProcessingSourceArtifacts(
            request_mode="dual_track",
            source_kind=revision.source_kind,
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
    purpose: str = "transcription",
    source_fingerprint: str | None = None,
    active_only: bool = False,
) -> ProcessingWorkflow | None:
    query = select(ProcessingWorkflow).where(
        ProcessingWorkflow.workspace_id == workspace_id,
        ProcessingWorkflow.meeting_id == meeting_id,
        ProcessingWorkflow.purpose == purpose,
    )
    if media_revision_id is None:
        # A legacy callback may omit its revision id. It must only observe the
        # legacy NULL lineage, never a newer revision-scoped workflow.
        query = query.where(ProcessingWorkflow.media_revision_id.is_(None))
    else:
        query = query.where(ProcessingWorkflow.media_revision_id == media_revision_id)
    if source_fingerprint is not None:
        query = query.where(ProcessingWorkflow.source_fingerprint == source_fingerprint)
    if active_only:
        query = query.where(
            ProcessingWorkflow.status.notin_(
                {
                    ProcessingStatus.PROCESSED.value,
                    ProcessingStatus.BLOCKED.value,
                    ProcessingStatus.FAILED_TERMINAL.value,
                    ProcessingStatus.CANCELED.value,
                }
            )
        )
    return await db.scalar(
        query.order_by(
            ProcessingWorkflow.attempt_ordinal.desc(),
            ProcessingWorkflow.created_at.desc(),
        )
    )


async def reconcile_legacy_processing_lineage(
    db: AsyncSession,
    *,
    workspace_id: UUID | None = None,
    limit: int = 500,
) -> dict[str, int]:
    """Backfill pre-revision rows without guessing across multiple sources.

    A meeting with exactly one attested accepted revision can be relinked. A
    row with no attested revision keeps a durable ``legacy:<run-id>`` marker;
    an active row with multiple possible revisions is blocked for operator
    reconciliation instead of being attached to the wrong source.
    """
    if limit <= 0:
        return {
            "scanned": 0,
            "marked_legacy": 0,
            "relinked": 0,
            "jobs_relinked": 0,
            "results_relinked": 0,
            "blocked": 0,
            "unresolved": 0,
        }
    query = (
        select(ProcessingWorkflow)
        .where(ProcessingWorkflow.media_revision_id.is_(None))
        .order_by(ProcessingWorkflow.created_at.asc(), ProcessingWorkflow.id.asc())
        .limit(limit)
    )
    if workspace_id is not None:
        query = query.where(ProcessingWorkflow.workspace_id == workspace_id)
    candidate_workflows = (await db.scalars(query)).all()
    grouped_ids: dict[tuple[UUID, UUID], list[UUID]] = {}
    for candidate in candidate_workflows:
        grouped_ids.setdefault((candidate.workspace_id, candidate.meeting_id), []).append(
            candidate.id
        )
    workflows: list[ProcessingWorkflow] = []
    for (candidate_workspace_id, candidate_meeting_id), candidate_ids in sorted(
        grouped_ids.items(), key=lambda item: tuple(str(value) for value in item[0])
    ):
        # Revision acceptance and deletion both use Meeting as the lifecycle
        # fence. Acquire it before the legacy workflow rows so reconciliation
        # cannot relink a row against a revision that wins concurrently.
        meeting = await lock_meeting_fence(
            db,
            workspace_id=candidate_workspace_id,
            meeting_id=candidate_meeting_id,
        )
        if meeting is None or meeting_is_deleted_or_deleting(meeting):
            continue
        locked_workflows = (
            await db.scalars(
                select(ProcessingWorkflow)
                .where(
                    ProcessingWorkflow.workspace_id == candidate_workspace_id,
                    ProcessingWorkflow.meeting_id == candidate_meeting_id,
                    ProcessingWorkflow.id.in_(candidate_ids),
                    ProcessingWorkflow.media_revision_id.is_(None),
                )
                .order_by(ProcessingWorkflow.created_at.asc(), ProcessingWorkflow.id.asc())
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
        workflows.extend(locked_workflows)
    report = {
        "scanned": len(workflows),
        "marked_legacy": 0,
        "relinked": 0,
        "jobs_relinked": 0,
        "results_relinked": 0,
        "blocked": 0,
        "unresolved": 0,
    }
    for workflow in workflows:
        if not is_legacy_lineage(
            media_revision_id=workflow.media_revision_id,
            source_fingerprint=workflow.source_fingerprint,
        ):
            workflow.source_fingerprint = legacy_source_fingerprint(workflow.id)
            report["marked_legacy"] += 1
        revisions = (
            await db.scalars(
                select(MediaRevision)
                .where(
                    MediaRevision.workspace_id == workflow.workspace_id,
                    MediaRevision.meeting_id == workflow.meeting_id,
                    MediaRevision.status == MediaRevisionStatus.ACCEPTED.value,
                    MediaRevision.immutable.is_(True),
                )
                .order_by(MediaRevision.revision_number.asc(), MediaRevision.id.asc())
            )
        ).all()
        attested = []
        for revision in revisions:
            try:
                fingerprint = source_fingerprint_for_revision(revision)
            except ValueError:
                continue
            attested.append((revision, fingerprint))
        if len(attested) == 1:
            revision, fingerprint = attested[0]
            existing_revision_workflow = await db.scalar(
                select(ProcessingWorkflow)
                .where(
                    ProcessingWorkflow.workspace_id == workflow.workspace_id,
                    ProcessingWorkflow.meeting_id == workflow.meeting_id,
                    ProcessingWorkflow.media_revision_id == revision.id,
                    ProcessingWorkflow.purpose == workflow.purpose,
                    ProcessingWorkflow.source_fingerprint == fingerprint,
                    ProcessingWorkflow.status.notin_(TERMINAL_PROCESSING_STATUSES),
                    ProcessingWorkflow.id != workflow.id,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if existing_revision_workflow is not None:
                # A canonical workflow already owns this source. Do not let a
                # legacy row violate the partial unique index; terminalize it
                # with an explicit safe reason and leave its historical jobs
                # and results attached to their legacy lineage.
                workflow.status = ProcessingStatus.BLOCKED.value
                workflow.last_reason_code = "legacy_lineage_duplicate"
                workflow.ended_at = datetime.now(UTC)
                duplicate_jobs = (
                    await db.scalars(
                        select(MediaScribeJob)
                        .where(
                            MediaScribeJob.workspace_id == workflow.workspace_id,
                            MediaScribeJob.processing_workflow_id == workflow.id,
                            MediaScribeJob.status.notin_(
                                {
                                    MediaScribeJobStatus.FAILED.value,
                                    MediaScribeJobStatus.BLOCKED.value,
                                }
                            ),
                        )
                        .with_for_update()
                        .execution_options(populate_existing=True)
                    )
                ).all()
                for job in duplicate_jobs:
                    job.status = MediaScribeJobStatus.BLOCKED.value
                    job.failed_at = datetime.now(UTC)
                    job.last_error_code = "legacy_lineage_duplicate"
                report["blocked"] += 1
                continue
            workflow.media_revision_id = revision.id
            workflow.source_fingerprint = fingerprint
            report["relinked"] += 1
            jobs = (
                await db.scalars(
                    select(MediaScribeJob)
                    .where(
                        MediaScribeJob.workspace_id == workflow.workspace_id,
                        MediaScribeJob.processing_workflow_id == workflow.id,
                        MediaScribeJob.media_revision_id.is_(None),
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            ).all()
            for job in jobs:
                job.media_revision_id = revision.id
                job.source_fingerprint = job.source_fingerprint or fingerprint
                report["jobs_relinked"] += 1
            job_ids = [job.id for job in jobs]
            results = (
                await db.scalars(
                    select(ProcessingResult)
                    .where(
                        ProcessingResult.workspace_id == workflow.workspace_id,
                        ProcessingResult.media_revision_id.is_(None),
                        (
                            (ProcessingResult.processing_workflow_id == workflow.id)
                            | (
                                ProcessingResult.processing_workflow_id.is_(None)
                                & ProcessingResult.mediascribe_job_id.in_(job_ids)
                            )
                        ),
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            ).all()
            for result in results:
                if result.processing_workflow_id not in {None, workflow.id}:
                    continue
                result.processing_workflow_id = workflow.id
                result.media_revision_id = revision.id
                result.deletion_epoch_at_start = (
                    result.deletion_epoch_at_start
                    if result.deletion_epoch_at_start is not None
                    else workflow.deletion_epoch_at_start
                )
                report["results_relinked"] += 1
            continue
        if len(attested) == 0:
            report["unresolved"] += 1
            continue
        try:
            status = ProcessingStatus(workflow.status)
        except ValueError:
            status = None
        if status not in TERMINAL_PROCESSING_STATUSES:
            workflow.status = ProcessingStatus.BLOCKED.value
            workflow.last_reason_code = "legacy_lineage_ambiguous"
            workflow.ended_at = datetime.now(UTC)
            jobs = (
                await db.scalars(
                    select(MediaScribeJob)
                    .where(
                        MediaScribeJob.workspace_id == workflow.workspace_id,
                        MediaScribeJob.processing_workflow_id == workflow.id,
                        MediaScribeJob.status.notin_(
                            {MediaScribeJobStatus.FAILED.value, MediaScribeJobStatus.BLOCKED.value}
                        ),
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            ).all()
            for job in jobs:
                job.status = MediaScribeJobStatus.BLOCKED.value
                job.failed_at = datetime.now(UTC)
                job.last_error_code = "legacy_lineage_ambiguous"
            report["blocked"] += 1
    await db.commit()
    return report


async def cancel_stale_revision_workflows(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    reason_code: str = "processing_source_revision_stale",
) -> int:
    """Terminalize active workflows whose revision is no longer accepted."""
    meeting = await lock_meeting_fence(db, workspace_id=workspace_id, meeting_id=meeting_id)
    if meeting is None:
        return 0
    latest_revision = await latest_media_revision_for_meeting(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    if latest_revision is None:
        return 0
    stale_revision = ProcessingWorkflow.media_revision_id.is_not(None) & (
        ProcessingWorkflow.media_revision_id != latest_revision.id
    )
    stale_unmarked_legacy = ProcessingWorkflow.media_revision_id.is_(None) & (
        ProcessingWorkflow.source_fingerprint.is_(None)
        | ~ProcessingWorkflow.source_fingerprint.startswith("legacy:")
    )
    stale_workflows = (
        await db.scalars(
            select(ProcessingWorkflow)
            .where(
                ProcessingWorkflow.workspace_id == workspace_id,
                ProcessingWorkflow.meeting_id == meeting_id,
                stale_revision | stale_unmarked_legacy,
                ProcessingWorkflow.status.notin_(
                    {
                        ProcessingStatus.PROCESSED.value,
                        ProcessingStatus.BLOCKED.value,
                        ProcessingStatus.FAILED_TERMINAL.value,
                        ProcessingStatus.CANCELED.value,
                    }
                ),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    now = datetime.now(UTC)
    for workflow in stale_workflows:
        workflow.status = ProcessingStatus.CANCELED.value
        workflow.last_reason_code = reason_code
        workflow.ended_at = workflow.ended_at or now
        await release_processing_usage_reservation(
            db,
            workspace_id=workflow.workspace_id,
            media_revision_id=workflow.media_revision_id,
            meeting_id=workflow.meeting_id,
        )
    if stale_workflows:
        await db.commit()
    return len(stale_workflows)


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
    purpose: str = "transcription",
    source_fingerprint: str | None = None,
    expected_meeting_status: str | None = None,
    expected_media_revision_id: UUID | None = None,
    archive_audio: bool = True,
    deadline_seconds: int | None = None,
) -> ProcessingWorkflow:
    now = datetime.now(UTC)
    meeting = await lock_meeting_fence(db, workspace_id=workspace_id, meeting_id=meeting_id)
    if meeting is None:
        raise ProcessingLifecycleBlocked("meeting_not_found")
    if meeting_is_deleted_or_deleting(meeting):
        raise ProcessingLifecycleBlocked("meeting_deleting")
    if expected_meeting_status is not None and meeting.status != expected_meeting_status:
        raise ProcessingLifecycleBlocked("processing_meeting_state_stale")
    if expected_media_revision_id is not None:
        current_revision = await latest_media_revision_for_meeting(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
        )
        if current_revision is None or current_revision.id != expected_media_revision_id:
            raise ProcessingLifecycleBlocked("processing_source_revision_stale")
    if media_revision_id is not None:
        revision = await db.scalar(
            select(MediaRevision).where(
                MediaRevision.id == media_revision_id,
                MediaRevision.workspace_id == workspace_id,
                MediaRevision.meeting_id == meeting_id,
            )
        )
        try:
            attested_fingerprint = (
                source_fingerprint_for_revision(revision) if revision is not None else None
            )
        except ValueError:
            attested_fingerprint = None
        if attested_fingerprint is None:
            if status != ProcessingStatus.BLOCKED:
                raise ProcessingLifecycleBlocked("processing_source_revision_unavailable")
            source_fingerprint = None
        elif source_fingerprint is not None and source_fingerprint != attested_fingerprint:
            raise ProcessingLifecycleBlocked("processing_source_fingerprint_conflict")
        else:
            source_fingerprint = attested_fingerprint
    else:
        source_fingerprint = source_fingerprint or legacy_source_fingerprint(meeting_id)
    workflow = await get_processing_workflow(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        purpose=purpose,
        source_fingerprint=source_fingerprint,
        active_only=True,
    )
    if workflow is None:
        # Reuse the canonical row after a terminal block; workflow_id is
        # unique, so a retry must not create a second durable lineage row.
        workflow = await db.scalar(
            select(ProcessingWorkflow)
            .where(
                ProcessingWorkflow.workflow_id == workflow_id,
                ProcessingWorkflow.workspace_id == workspace_id,
                ProcessingWorkflow.meeting_id == meeting_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    if workflow is not None:
        if workflow.archive_audio != archive_audio and workflow.status not in {
            ProcessingStatus.BLOCKED.value,
            ProcessingStatus.CANCELED.value,
            ProcessingStatus.FAILED_TERMINAL.value,
            ProcessingStatus.PROCESSED.value,
        }:
            raise ProcessingLifecycleBlocked("processing_archive_mode_conflict")
        try:
            current_status = ProcessingStatus(workflow.status)
        except ValueError:
            current_status = None
        if (
            current_status in TERMINAL_PROCESSING_STATUSES
            and status != current_status
            and not (
                current_status == ProcessingStatus.BLOCKED
                and status
                in {
                    ProcessingStatus.STARTING,
                    ProcessingStatus.WORKFLOW_STARTED,
                }
            )
        ):
            await db.commit()
            return workflow
    if workflow is None:
        workflow = ProcessingWorkflow(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            workflow_id=workflow_id,
            purpose=purpose,
            source_fingerprint=source_fingerprint,
            deletion_epoch_at_start=int(meeting.deletion_epoch or 0),
            workflow_run_id=workflow_run_id,
            status=status.value,
            archive_audio=archive_audio,
            transient_state="processing" if not archive_audio else "not_applicable",
            transient_admitted_at=now if not archive_audio else None,
            transient_hard_deadline=(now + TRANSIENT_HARD_LIFETIME) if not archive_audio else None,
            deadline_at=now + (
                timedelta(seconds=deadline_seconds)
                if deadline_seconds is not None
                else DEFAULT_DEADLINE
            ),
            attempt_count=1,
            last_reason_code=reason_code,
            started_at=now,
        )
        db.add(workflow)
    else:
        if workflow.media_revision_id != media_revision_id:
            raise ProcessingLifecycleBlocked("processing_revision_conflict")
        if (
            workflow.source_fingerprint is not None
            and source_fingerprint is not None
            and workflow.source_fingerprint != source_fingerprint
        ):
            raise ProcessingLifecycleBlocked("processing_source_fingerprint_conflict")
        workflow.source_fingerprint = workflow.source_fingerprint or source_fingerprint
        if workflow.deadline_at is None:
            workflow.deadline_at = (workflow.started_at or now) + (
                timedelta(seconds=deadline_seconds)
                if deadline_seconds is not None
                else DEFAULT_DEADLINE
            )
        if workflow.archive_audio != archive_audio and workflow.status in {
            ProcessingStatus.BLOCKED.value,
            ProcessingStatus.CANCELED.value,
            ProcessingStatus.FAILED_TERMINAL.value,
            ProcessingStatus.PROCESSED.value,
        }:
            workflow.archive_audio = archive_audio
            if archive_audio:
                _clear_transient_lifecycle(workflow)
            else:
                _start_transient_lifecycle(workflow, now=now)
        workflow.workflow_id = workflow_id
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
        if not workflow.archive_audio and workflow.transient_admitted_at is None:
            _start_transient_lifecycle(workflow, now=now)
    if not archive_audio and status in TERMINAL_PROCESSING_STATUSES:
        _mark_transient_terminal(workflow, now=now)
    await _sync_meeting_processing_status(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        status=status,
    )
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
    meeting = await lock_meeting_fence(
        db, workspace_id=workflow.workspace_id, meeting_id=workflow.meeting_id
    )
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        current = await db.scalar(
            select(ProcessingWorkflow)
            .where(ProcessingWorkflow.id == workflow.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if current is None:
            raise ProcessingLifecycleBlocked("workflow_not_found")
        current.status = ProcessingStatus.CANCELED.value
        current.last_reason_code = "meeting_deleting"
        current.ended_at = datetime.now(UTC)
        await release_processing_usage_reservation(
            db,
            workspace_id=current.workspace_id,
            media_revision_id=current.media_revision_id,
            meeting_id=current.meeting_id,
        )
        await db.commit()
        raise ProcessingLifecycleBlocked("meeting_deleting")
    current = await db.scalar(
        select(ProcessingWorkflow)
        .where(ProcessingWorkflow.id == workflow.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if current is None:
        raise ProcessingLifecycleBlocked("workflow_not_found")
    try:
        current_status = ProcessingStatus(current.status)
    except ValueError:
        current_status = None
    if current_status in TERMINAL_PROCESSING_STATUSES:
        await db.commit()
        return current
    if current_status is not None and not can_transition(current_status, status):
        await db.commit()
        return current
    current.status = status.value
    current.last_reason_code = reason_code
    current.attempt_count += 1
    if status in {
        ProcessingStatus.WAITING_RETRY,
        ProcessingStatus.BLOCKED_UNKNOWN,
        ProcessingStatus.PROCESSED,
        ProcessingStatus.BLOCKED,
        ProcessingStatus.FAILED_RETRYABLE,
        ProcessingStatus.FAILED_TERMINAL,
        ProcessingStatus.CANCELED,
    }:
        # A manual claim fences one dispatch only. Clear it once the operation
        # has produced a waiting or terminal projection so the API does not
        # report a stale user command as permanently in flight.
        current.manual_claimed_at = None
        current.manual_claimed_by = None
    if status not in {
        ProcessingStatus.WAITING_RETRY,
        ProcessingStatus.BLOCKED_UNKNOWN,
        ProcessingStatus.FAILED_RETRYABLE,
    }:
        current.next_attempt_at = None
        current.next_attempt_source = None
    if terminal:
        current.ended_at = datetime.now(UTC)
        if not current.archive_audio:
            _mark_transient_terminal(current, now=current.ended_at)
        await release_processing_usage_reservation(
            db,
            workspace_id=current.workspace_id,
            media_revision_id=current.media_revision_id,
            meeting_id=current.meeting_id,
        )
    await _sync_meeting_processing_status(
        db,
        workspace_id=current.workspace_id,
        meeting_id=current.meeting_id,
        media_revision_id=current.media_revision_id,
        status=status,
    )
    await db.commit()
    return current


def _start_transient_lifecycle(workflow: ProcessingWorkflow, *, now: datetime) -> None:
    workflow.archive_audio = False
    workflow.transient_state = "processing"
    workflow.transient_admitted_at = workflow.transient_admitted_at or now
    workflow.transient_hard_deadline = (
        workflow.transient_hard_deadline or workflow.transient_admitted_at + TRANSIENT_HARD_LIFETIME
    )
    workflow.transient_terminal_at = None
    workflow.transient_purge_due_at = None
    workflow.transient_purged_at = None


def _mark_transient_terminal(workflow: ProcessingWorkflow, *, now: datetime) -> None:
    if workflow.archive_audio:
        return
    _start_transient_lifecycle(workflow, now=now)
    workflow.transient_state = "terminal"
    workflow.transient_terminal_at = workflow.transient_terminal_at or now
    workflow.transient_purge_due_at = workflow.transient_terminal_at + TRANSIENT_PURGE_AFTER


def _clear_transient_lifecycle(workflow: ProcessingWorkflow) -> None:
    workflow.transient_state = "not_applicable"
    workflow.transient_admitted_at = None
    workflow.transient_terminal_at = None
    workflow.transient_purge_due_at = None
    workflow.transient_hard_deadline = None
    workflow.transient_purged_at = None


async def _sync_meeting_processing_status(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
    status: ProcessingStatus,
) -> None:
    latest_revision = None
    meeting = await db.get(Meeting, meeting_id)
    if meeting is not None and not meeting_is_deleted_or_deleting(meeting):
        latest_revision = await latest_media_revision_for_meeting(
            db, workspace_id=workspace_id, meeting_id=meeting_id
        )
        if (
            media_revision_id is not None
            and (latest_revision is None or latest_revision.id == media_revision_id)
        ) or (media_revision_id is None and latest_revision is None):
            meeting.processing_status = status.value
    placeholder = await db.scalar(
        select(ProcessingPlaceholder).where(
            ProcessingPlaceholder.workspace_id == workspace_id,
            ProcessingPlaceholder.meeting_id == meeting_id,
        )
    )
    if placeholder is not None and (
        media_revision_id is not None
        and (latest_revision is None or latest_revision.id == media_revision_id)
        or media_revision_id is None
        and latest_revision is None
    ):
        placeholder.status = status.value


async def get_mediascribe_job(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
    processing_workflow_id: UUID | None = None,
    active_only: bool = False,
    for_update: bool = False,
) -> MediaScribeJob | None:
    query = select(MediaScribeJob).where(
        MediaScribeJob.workspace_id == workspace_id,
        MediaScribeJob.meeting_id == meeting_id,
    )
    if media_revision_id is not None:
        query = query.where(MediaScribeJob.media_revision_id == media_revision_id)
    else:
        query = query.where(MediaScribeJob.media_revision_id.is_(None))
    if processing_workflow_id is not None:
        query = query.where(MediaScribeJob.processing_workflow_id == processing_workflow_id)
    if active_only:
        query = query.where(
            MediaScribeJob.status.notin_(
                {MediaScribeJobStatus.FAILED.value, MediaScribeJobStatus.BLOCKED.value}
            )
        )
    if for_update:
        query = query.with_for_update().execution_options(populate_existing=True)
    return await db.scalar(query.order_by(MediaScribeJob.created_at.desc()))


async def upsert_mediascribe_job(
    db: AsyncSession,
    *,
    workflow: ProcessingWorkflow,
    mic_artifact: TrackArtifact | None = None,
    incoming_artifact: TrackArtifact | None = None,
    source_artifact: TrackArtifact | None = None,
    request_mode: str = "dual_track",
    source_fingerprint: str | None = None,
    diarize: bool = True,
    summarize: bool = False,
    speaker_count_mode: str | None = None,
    num_speakers: int | None = None,
) -> MediaScribeJob:
    if request_mode == "dual_track" and (mic_artifact is None or incoming_artifact is None):
        raise ValueError("dual_track_requires_artifact_pair")
    if request_mode == "single_track" and source_artifact is None:
        raise ValueError("single_track_requires_source_artifact")
    request_fingerprint = processing_request_fingerprint(
        request_mode=request_mode,
        source_fingerprint=source_fingerprint or workflow.source_fingerprint,
        mic_artifact=mic_artifact,
        incoming_artifact=incoming_artifact,
        source_artifact=source_artifact,
        diarize=diarize,
        summarize=summarize,
        speaker_count_mode=speaker_count_mode,
        num_speakers=num_speakers,
    )
    workspace_id = workflow.workspace_id
    meeting_id = workflow.meeting_id
    media_revision_id = workflow.media_revision_id
    processing_workflow_id = workflow.id
    job = await get_mediascribe_job(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        processing_workflow_id=processing_workflow_id,
        active_only=True,
    )
    if job is None:
        previous_job = await get_mediascribe_job(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            processing_workflow_id=processing_workflow_id,
        )
        idempotency_key = f"mediascribe:{processing_workflow_id}:{source_fingerprint or workflow.source_fingerprint or 'legacy'}"
        if previous_job is not None:
            job = previous_job
        else:
            job = MediaScribeJob(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                processing_workflow_id=processing_workflow_id,
                idempotency_key=idempotency_key,
                source_fingerprint=source_fingerprint or workflow.source_fingerprint,
                deletion_epoch_at_start=workflow.deletion_epoch_at_start,
                mic_track_artifact_id=mic_artifact.id if mic_artifact is not None else None,
                incoming_track_artifact_id=incoming_artifact.id
                if incoming_artifact is not None
                else None,
                source_track_artifact_id=source_artifact.id
                if source_artifact is not None
                else None,
                status=MediaScribeJobStatus.NOT_SUBMITTED.value,
                request_mode=request_mode,
                diarize=diarize,
                summarize=summarize,
                speaker_count_mode=speaker_count_mode,
                num_speakers=num_speakers,
                request_fingerprint=request_fingerprint,
            )
            db.add(job)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                job = await get_mediascribe_job(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    processing_workflow_id=processing_workflow_id,
                )
                if job is None:
                    raise
    elif job.external_job_id is None:
        if job.request_fingerprint not in {None, request_fingerprint}:
            raise ProcessingLifecycleBlocked("processing_request_fingerprint_conflict")
        job.request_mode = request_mode
        job.mic_track_artifact_id = mic_artifact.id if mic_artifact is not None else None
        job.incoming_track_artifact_id = (
            incoming_artifact.id if incoming_artifact is not None else None
        )
        job.source_track_artifact_id = source_artifact.id if source_artifact is not None else None
        job.diarize = diarize
        job.summarize = summarize
        job.speaker_count_mode = speaker_count_mode
        job.num_speakers = num_speakers
        job.request_fingerprint = request_fingerprint
        await db.commit()
    return job


async def claim_mediascribe_submission(
    db: AsyncSession,
    *,
    job: MediaScribeJob,
) -> str | None:
    """Claim one provider POST without holding a database lock over network I/O."""
    meeting = await lock_meeting_fence(db, workspace_id=job.workspace_id, meeting_id=job.meeting_id)
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        raise ProcessingLifecycleBlocked("meeting_deleting")
    current = await db.scalar(
        select(MediaScribeJob)
        .where(MediaScribeJob.id == job.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if current is None:
        raise MediaScribeClientError("mediascribe_job_not_found", retryable=False)
    if current.external_job_id:
        return None
    if (
        current.status == MediaScribeJobStatus.BLOCKED.value
        and current.last_error_code == BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN
    ):
        raise MediaScribeClientError(
            BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
            retryable=False,
        )
    now = datetime.now(UTC)
    if current.status == MediaScribeJobStatus.SUBMITTING.value:
        claimed_at = current.submission_claimed_at
        if claimed_at is not None and now - claimed_at < MEDIASCRIBE_SUBMISSION_CLAIM_STALE_AFTER:
            return None
        # The provider request carries the durable job idempotency key, so a
        # crashed worker can safely replay the same intent after the claim is
        # stale. Never create a new job row or key here.
        current.status = MediaScribeJobStatus.NOT_SUBMITTED.value
        current.submission_claim_token = None
        current.submission_claimed_at = None
        current.last_error_code = None
        current.last_error_message = None
        current.failed_at = None
        await db.commit()
    token = uuid4().hex
    current.status = MediaScribeJobStatus.SUBMITTING.value
    current.submission_claim_token = token
    current.submission_claimed_at = now
    await db.commit()
    return token


async def wait_for_mediascribe_submission(
    db: AsyncSession,
    *,
    job_id: UUID,
    timeout_seconds: float | None = None,
) -> MediaScribeJob | None:
    """Wait for a competing claimant to persist its opaque provider ID."""
    timeout_seconds = (
        MEDIASCRIBE_SUBMISSION_WAIT_SECONDS if timeout_seconds is None else timeout_seconds
    )
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while True:
        current = await db.scalar(select(MediaScribeJob).where(MediaScribeJob.id == job_id))
        if current is None:
            raise MediaScribeClientError("mediascribe_job_not_found", retryable=False)
        if current.external_job_id:
            return current
        if (
            current.status == MediaScribeJobStatus.BLOCKED.value
            and current.last_error_code == BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN
        ):
            raise MediaScribeClientError(
                BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
                retryable=False,
            )
        if current.status != MediaScribeJobStatus.SUBMITTING.value:
            return None
        await db.rollback()
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            current = await db.scalar(
                select(MediaScribeJob)
                .where(MediaScribeJob.id == job_id)
                .execution_options(populate_existing=True)
            )
            # Keep the live claim intact. The caller will surface a retryable
            # in-progress state; only the stale-claim path may reclaim the
            # durable idempotency key. This is intentionally a plain read:
            # claim_mediascribe_submission acquires Meeting → Job next.
            return current
        await asyncio.sleep(min(0.25, remaining))


async def release_mediascribe_submission_claim(
    db: AsyncSession,
    *,
    job: MediaScribeJob,
    claim_token: str,
) -> None:
    meeting = await lock_meeting_fence(db, workspace_id=job.workspace_id, meeting_id=job.meeting_id)
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        await db.rollback()
        return
    current = await db.scalar(
        select(MediaScribeJob)
        .where(MediaScribeJob.id == job.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        current is None
        or current.submission_claim_token != claim_token
        or current.external_job_id
        or current.status
        in {
            MediaScribeJobStatus.BLOCKED.value,
            MediaScribeJobStatus.FAILED.value,
            MediaScribeJobStatus.READY.value,
        }
    ):
        return
    current.status = MediaScribeJobStatus.NOT_SUBMITTED.value
    current.submission_claim_token = None
    current.submission_claimed_at = None
    await db.commit()


async def _mark_mediascribe_submission_unknown(
    db: AsyncSession,
    job: MediaScribeJob,
    *,
    error_message: str,
) -> None:
    meeting = await lock_meeting_fence(db, workspace_id=job.workspace_id, meeting_id=job.meeting_id)
    current = await db.scalar(
        select(MediaScribeJob)
        .where(MediaScribeJob.id == job.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if current is None:
        return
    current.status = MediaScribeJobStatus.BLOCKED.value
    current.failed_at = datetime.now(UTC)
    current.last_error_code = (
        "meeting_deleting"
        if meeting is None or meeting_is_deleted_or_deleting(meeting)
        else BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN
    )
    current.last_error_message = error_message
    current.submission_claim_token = None
    current.submission_claimed_at = None
    await db.commit()


mark_mediascribe_submission_unknown = _mark_mediascribe_submission_unknown


async def persist_mediascribe_submission(
    db: AsyncSession,
    *,
    job: MediaScribeJob,
    external_job_id: str,
    status: MediaScribeJobStatus,
    submission_claim_token: str | None = None,
    provider_status: str | None = None,
    provider_queue_state: str | None = None,
    provider_attempt: int | None = None,
    provider_max_attempts: int | None = None,
    retry_after_seconds: int | None = None,
    provider_next_retry_at: datetime | None = None,
    request_id: str | None = None,
) -> MediaScribeJob:
    meeting = await lock_meeting_fence(db, workspace_id=job.workspace_id, meeting_id=job.meeting_id)
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        current = await db.scalar(
            select(MediaScribeJob)
            .where(MediaScribeJob.id == job.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if current is not None:
            current.external_job_id = current.external_job_id or external_job_id
            current.submitted_at = current.submitted_at or datetime.now(UTC)
            current.status = MediaScribeJobStatus.BLOCKED.value
            current.failed_at = datetime.now(UTC)
            current.last_error_code = "meeting_deleting"
            current.last_error_message = "provider accepted submission after deletion fence"
            current.submission_claim_token = None
            current.submission_claimed_at = None
        await db.commit()
        raise ProcessingLifecycleBlocked("meeting_deleting")
    current = await db.scalar(
        select(MediaScribeJob)
        .where(MediaScribeJob.id == job.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if current is None:
        raise MediaScribeClientError("mediascribe_job_not_found", retryable=False)
    if current.external_job_id:
        return current
    if (
        submission_claim_token is not None
        and current.submission_claim_token != submission_claim_token
    ):
        # The provider accepted the opaque job while another worker replaced
        # our claim. Persist the provider ID and blocked projection together;
        # splitting these commits can strand an accepted job without lineage.
        current.status = MediaScribeJobStatus.BLOCKED.value
        current.failed_at = datetime.now(UTC)
        current.last_error_code = BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN
        current.last_error_message = "submission_claim_lost_after_provider_response"
        current.submission_claim_token = None
        current.submission_claimed_at = None
        current.external_job_id = external_job_id
        await db.commit()
        raise MediaScribeClientError(
            BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
            retryable=False,
        )
    current.external_job_id = external_job_id
    current.status = status.value
    current.submitted_at = current.submitted_at or datetime.now(UTC)
    current.failed_at = None
    current.last_error_code = None
    current.last_error_message = None
    current.submission_claim_token = None
    current.submission_claimed_at = None
    current.provider_status = provider_status
    current.provider_queue_state = provider_queue_state
    current.provider_attempt = provider_attempt
    current.provider_max_attempts = provider_max_attempts
    current.retry_after_seconds = (
        max(0, int(retry_after_seconds)) if retry_after_seconds is not None else None
    )
    current.provider_next_retry_at = provider_next_retry_at
    current.last_request_id = request_id
    await db.commit()
    return current


async def persist_mediascribe_submission_fallback(
    db: AsyncSession,
    *,
    job: MediaScribeJob,
    external_job_id: str,
    reason_code: str,
    error_message: str | None = None,
) -> MediaScribeJob:
    """Retain a provider job when the post-egress lifecycle fence loses a race.

    The normal persistence path re-checks the meeting fence and therefore must
    reject a deleted or stale source. Once MediaScribe accepted the upload, the
    opaque external ID is still durable lineage needed by deletion and retry
    reconciliation, so this bounded fallback intentionally records only the ID
    and a blocked status without reopening the meeting workflow.
    """
    current = await db.scalar(
        select(MediaScribeJob)
        .where(MediaScribeJob.id == job.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if current is None:
        raise MediaScribeClientError("mediascribe_job_not_found", retryable=False)
    current.external_job_id = current.external_job_id or external_job_id
    current.status = MediaScribeJobStatus.BLOCKED.value
    current.submitted_at = current.submitted_at or datetime.now(UTC)
    current.failed_at = datetime.now(UTC)
    current.last_error_code = reason_code
    current.last_error_message = error_message or reason_code
    current.submission_claim_token = None
    current.submission_claimed_at = None
    await db.commit()
    return current


async def update_mediascribe_job_status(
    db: AsyncSession,
    *,
    job: MediaScribeJob,
    status: MediaScribeJobStatus,
    reason_code: str | None = None,
    error_message: str | None = None,
    retryable: bool | None = None,
    retry_after_seconds: int | None = None,
    provider_next_retry_at: datetime | None = None,
    provider_status: str | None = None,
    provider_queue_state: str | None = None,
    provider_attempt: int | None = None,
    provider_max_attempts: int | None = None,
    request_id: str | None = None,
) -> MediaScribeJob:
    meeting = await lock_meeting_fence(db, workspace_id=job.workspace_id, meeting_id=job.meeting_id)
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        current = await db.scalar(
            select(MediaScribeJob)
            .where(MediaScribeJob.id == job.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if current is not None:
            current.status = MediaScribeJobStatus.BLOCKED.value
            current.last_error_code = "meeting_deleting"
        await db.commit()
        raise ProcessingLifecycleBlocked("meeting_deleting")
    current = await db.scalar(
        select(MediaScribeJob)
        .where(MediaScribeJob.id == job.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if current is None:
        raise MediaScribeClientError("mediascribe_job_not_found", retryable=False)

    terminal_statuses = {
        MediaScribeJobStatus.READY.value,
        MediaScribeJobStatus.FAILED.value,
        MediaScribeJobStatus.BLOCKED.value,
    }
    status_order = {
        MediaScribeJobStatus.NOT_SUBMITTED.value: 0,
        MediaScribeJobStatus.SUBMITTING.value: 1,
        MediaScribeJobStatus.SUBMITTED.value: 2,
        MediaScribeJobStatus.UPLOADED.value: 3,
        MediaScribeJobStatus.TRANSCRIBING.value: 4,
        MediaScribeJobStatus.DIARIZING.value: 5,
        MediaScribeJobStatus.SUMMARIZING.value: 6,
        MediaScribeJobStatus.READY.value: 7,
    }
    effective_status = status
    if status == MediaScribeJobStatus.FAILED and retryable:
        # A transient provider/transport error is not a provider terminal
        # result. Keep the durable job addressable for the next same-job poll
        # or same-key submit; marking it FAILED would make recovery unsafe.
        if current.status == MediaScribeJobStatus.BLOCKED.value:
            return current
        if current.status == MediaScribeJobStatus.FAILED.value:
            effective_status = (
                MediaScribeJobStatus.SUBMITTED
                if current.external_job_id
                else MediaScribeJobStatus.NOT_SUBMITTED
            )
        else:
            try:
                effective_status = MediaScribeJobStatus(current.status)
            except ValueError:
                effective_status = (
                    MediaScribeJobStatus.SUBMITTED
                    if current.external_job_id
                    else MediaScribeJobStatus.NOT_SUBMITTED
                )
    if current.status in terminal_statuses and current.status != effective_status.value:
        return current
    if (
        current.status not in terminal_statuses
        and effective_status.value in status_order
        and status_order.get(effective_status.value, -1) < status_order.get(current.status, -1)
    ):
        return current
    now = datetime.now(UTC)
    current.status = effective_status.value
    current.last_polled_at = now
    current.last_error_code = reason_code
    current.last_error_message = error_message
    if provider_status is not None:
        current.provider_status = provider_status
    if provider_queue_state is not None:
        current.provider_queue_state = provider_queue_state
    if provider_attempt is not None:
        current.provider_attempt = provider_attempt
    if provider_max_attempts is not None:
        current.provider_max_attempts = provider_max_attempts
    if request_id is not None:
        current.last_request_id = request_id
    current.retry_after_seconds = (
        max(0, int(retry_after_seconds)) if retry_after_seconds is not None else None
    )
    current.provider_next_retry_at = provider_next_retry_at
    if effective_status == MediaScribeJobStatus.READY:
        current.ready_at = now
        current.retry_after_seconds = None
        current.provider_next_retry_at = None
    if effective_status in {MediaScribeJobStatus.FAILED, MediaScribeJobStatus.BLOCKED}:
        current.failed_at = now
    elif retryable:
        current.failed_at = None
    await db.commit()
    return current


async def persist_processing_result(
    db: AsyncSession,
    *,
    job: MediaScribeJob,
    result: MediaScribeResult,
    source_result_hash: str,
) -> ProcessingResult:
    meeting = await lock_meeting_fence(db, workspace_id=job.workspace_id, meeting_id=job.meeting_id)
    if meeting is None:
        raise ProcessingLifecycleBlocked("meeting_not_found")
    if meeting_is_deleted_or_deleting(meeting):
        await record_stale_lifecycle_event(
            db,
            workspace_id=job.workspace_id,
            meeting_id=job.meeting_id,
            event_type="processing_result_blocked_by_deletion",
            metadata={"mediascribe_job_id": str(job.id)},
        )
        await db.commit()
        raise ProcessingLifecycleBlocked("meeting_deleting")
    latest_revision = await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == job.workspace_id,
            MediaRevision.meeting_id == job.meeting_id,
            MediaRevision.status == MediaRevisionStatus.ACCEPTED.value,
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
    )
    legacy_lineage = is_legacy_lineage(
        media_revision_id=job.media_revision_id,
        source_fingerprint=job.source_fingerprint,
    )
    source_stale = (
        False
        if legacy_lineage
        else (latest_revision.id if latest_revision is not None else None) != job.media_revision_id
    )
    if latest_revision is not None and not source_stale:
        try:
            source_stale = job.source_fingerprint != source_fingerprint_for_revision(
                latest_revision
            )
        except ValueError:
            source_stale = True
    if source_stale:
        await record_stale_lifecycle_event(
            db,
            workspace_id=job.workspace_id,
            meeting_id=job.meeting_id,
            event_type="processing_result_blocked_by_source_revision",
            metadata={"mediascribe_job_id": str(job.id)},
        )
        await db.commit()
        raise ProcessingLifecycleBlocked("processing_source_revision_stale")
    existing_workflow_hash = None
    if job.processing_workflow_id is not None:
        existing_workflow_hash = await db.scalar(
            select(ProcessingResult)
            .where(
                ProcessingResult.workspace_id == job.workspace_id,
                ProcessingResult.processing_workflow_id == job.processing_workflow_id,
                ProcessingResult.source_result_hash == source_result_hash,
            )
            .order_by(ProcessingResult.created_at.asc(), ProcessingResult.id.asc())
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    if (
        existing_workflow_hash is not None
        and existing_workflow_hash.status == ProcessingResultStatus.IMPORTED.value
    ):
        # A provider retry may arrive through a replacement job for the same
        # workflow. Reuse the immutable result instead of violating the
        # workflow/source-hash invariant or duplicating transcript rows.
        return existing_workflow_hash
    existing_hash = await db.scalar(
        select(ProcessingResult)
        .where(
            ProcessingResult.workspace_id == job.workspace_id,
            ProcessingResult.mediascribe_job_id == job.id,
            ProcessingResult.source_result_hash == source_result_hash,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if existing_hash is not None and existing_hash.status == ProcessingResultStatus.IMPORTED.value:
        return existing_hash
    existing = existing_workflow_hash or existing_hash
    if existing is None:
        existing = await db.scalar(
            select(ProcessingResult)
            .where(
                ProcessingResult.workspace_id == job.workspace_id,
                ProcessingResult.mediascribe_job_id == job.id,
                ProcessingResult.result_version == result.result_version,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    if existing is None or existing.source_result_hash != source_result_hash:
        next_version = await db.scalar(
            select(func.coalesce(func.max(ProcessingResult.result_version), 0)).where(
                ProcessingResult.workspace_id == job.workspace_id,
                ProcessingResult.mediascribe_job_id == job.id,
            )
        )
        existing = ProcessingResult(
            workspace_id=job.workspace_id,
            meeting_id=job.meeting_id,
            media_revision_id=job.media_revision_id,
            mediascribe_job_id=job.id,
            processing_workflow_id=job.processing_workflow_id,
            deletion_epoch_at_start=int(meeting.deletion_epoch or 0),
            result_version=max(int(next_version or 0) + 1, result.result_version),
        )
        db.add(existing)
        await db.flush()
    else:
        # Partial/importing retries reuse the fenced row but replace its child
        # segments; appending would duplicate sequence keys and transcript text.
        await db.execute(
            delete(TranscriptSegment).where(TranscriptSegment.processing_result_id == existing.id)
        )
        await db.execute(
            delete(DiarizationSegment).where(DiarizationSegment.processing_result_id == existing.id)
        )

    existing.status = ProcessingResultStatus.IMPORTED.value
    existing.transcript_status = result.transcript_status.value
    existing.diarization_status = (
        ProcessingAvailabilityStatus.AVAILABLE.value
        if result.diarization
        else ProcessingAvailabilityStatus.UNAVAILABLE.value
    )
    existing.summary_status = result.summary_status.value
    existing.language = result.language
    existing.segment_count = len(result.transcript)
    existing.diarization_segment_count = len(result.diarization)
    attribution_diagnostics = result.attribution_diagnostics
    existing.failure_reason = (
        attribution_diagnostics.result_state
        if attribution_diagnostics is not None
        and attribution_diagnostics.result_state == "degraded_provider_result"
        else result.failure_reason
    )
    existing.failure_source = (
        "mediascribe"
        if attribution_diagnostics is not None
        and attribution_diagnostics.defect_origin == "provider"
        else result.failure_source
    )
    existing.source_result_hash = source_result_hash
    existing.provenance_json = _safe_provenance_projection(result)
    existing.overlaps_json = [item.model_dump(mode="json") for item in result.overlaps]
    existing.acoustic_turns_json = [
        item.model_dump(mode="json") for item in result.acoustic_speaker_turns
    ]
    # Persist only validated relative paths. Provider signed URLs are
    # intentionally resolved at request time and are never durable state.
    existing.downloads_json = safe_download_references(result.downloads)
    imported_at = datetime.now(UTC)
    existing.imported_at = imported_at
    if result.transcript_status == ProcessingAvailabilityStatus.AVAILABLE and result.transcript:
        await mark_source_transcript_imported(
            db,
            workspace_id=job.workspace_id,
            meeting_id=job.meeting_id,
            media_revision_id=job.media_revision_id,
            imported_at=imported_at,
        )

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
                words_json=(
                    [word.model_dump(mode="json", exclude_none=True) for word in segment.words]
                    if segment.words is not None
                    else None
                ),
            )
        )
    await _commit_processing_usage(
        db,
        job=job,
        transcript=result.transcript,
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


def _processing_usage_reservation_key(*, media_revision_id: UUID | None, meeting_id: UUID) -> str:
    return f"processing:{media_revision_id or meeting_id}"


async def _commit_processing_usage(
    db: AsyncSession,
    *,
    job: MediaScribeJob,
    transcript: list[object],
) -> int:
    reservation = await find_free_usage_reservation(
        db,
        workspace_id=job.workspace_id,
        reservation_key=_processing_usage_reservation_key(
            media_revision_id=job.media_revision_id,
            meeting_id=job.meeting_id,
        ),
    )
    if reservation is None or reservation.state != "active":
        return 0
    source_id = job.source_fingerprint or f"meeting:{job.meeting_id}"
    ranges: list[SourceRange] = []
    for segment in transcript:
        start = max(0, math.floor(float(segment.start_seconds)))
        end = math.floor(float(segment.end_seconds))
        if end > start:
            ranges.append(SourceRange(source_id, start, end))
    return await commit_free_usage_ranges(
        db,
        reservation_id=reservation.id,
        ranges=ranges,
    )


async def release_processing_usage_reservation(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    media_revision_id: UUID | None,
    meeting_id: UUID | None = None,
) -> bool:
    if media_revision_id is None and meeting_id is None:
        return False
    reservation = await find_free_usage_reservation(
        db,
        workspace_id=workspace_id,
        reservation_key=_processing_usage_reservation_key(
            media_revision_id=media_revision_id,
            meeting_id=meeting_id or media_revision_id,
        ),
    )
    if reservation is None:
        return False
    return await release_free_usage(db, reservation_id=reservation.id)


async def latest_processing_result(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
) -> ProcessingResult | None:
    return await db.scalar(
        effective_processing_result_query(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
    )


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


async def record_processing_aggregate_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_name: str,
    window: str,
    window_started_at: str,
    window_ended_at: str,
    surface: str,
    count: int,
    dimensions: dict[str, object],
) -> ProcessingAuditEvent:
    """Persist one validated rollup without meeting/provider identifiers."""

    payload = validate_processing_aggregate_event(
        event_name=event_name,
        window=window,
        window_started_at=window_started_at,
        window_ended_at=window_ended_at,
        surface=surface,
        count=count,
        dimensions=dimensions,
    )
    event = ProcessingAuditEvent(
        workspace_id=workspace_id,
        event_type=event_name,
        metadata_json=payload,
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
            ProcessingDependencyState.media_revision_id == media_revision_id,
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
