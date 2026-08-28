from __future__ import annotations

import asyncio
import shutil
import tempfile
from collections.abc import Awaitable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

from anyio import to_thread
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.usage import QuotaExceeded
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    MediaRevision,
    MediaScribeJob,
    PlaybackNormalizationJob,
    ProcessingWorkflow,
    TrackArtifact,
)
from twobrain_rec_server.domain.statuses import (
    MediaScribeJobStatus,
    ProcessingAvailabilityStatus,
    ProcessingStatus,
)
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.mediascribe.client import MediaScribeClientError
from twobrain_rec_server.mediascribe.import_results import (
    MediaScribeResultValidationError,
    normalize_result,
    result_digest,
)
from twobrain_rec_server.mediascribe.schemas import MediaScribePollResponse, MediaScribeResult
from twobrain_rec_server.normalization.statuses import JobState
from twobrain_rec_server.outcomes.ai_service import ensure_automatic_summary_candidate
from twobrain_rec_server.outcomes.service import ensure_outcomes_for_processing_result
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.fences import lock_meeting_fence, meeting_is_deleted_or_deleting
from twobrain_rec_server.processing.reasons import (
    BLOCKED_AUDIO_TOO_LARGE,
    BLOCKED_FREE_PROCESSING_EXHAUSTED,
    BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
    BLOCKED_MISSING_ARTIFACTS,
    DIAGNOSTIC_INPUT_AUDIO_PROBLEM,
    DIAGNOSTIC_MEDIASCRIBE_SERVICE_PROBLEM,
    DIAGNOSTIC_PROCESSED_NO_TRANSCRIPT,
    FAILURE_SOURCE_INPUT_AUDIO,
    FAILURE_SOURCE_MEDIASCRIBE,
    INVALID_AUDIO_PAYLOAD,
    MEDIASCRIBE_MALFORMED_RESPONSE,
    MEDIASCRIBE_SUBMISSION_IN_PROGRESS,
    NO_RECOGNIZABLE_SPEECH,
    PROCESSING_TEMP_STORAGE_UNAVAILABLE,
)
from twobrain_rec_server.processing.recovery import schedule_retry, schedule_retry_with_settings
from twobrain_rec_server.processing.store import ProcessingLifecycleBlocked
from twobrain_rec_server.storage.minio_client import StorageTransferError

DOWNLOAD_CHUNK_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class SubmitProcessingResult:
    job: MediaScribeJob
    submitted: bool


@dataclass(frozen=True, slots=True)
class ImportProcessingResult:
    imported: bool
    status: ProcessingStatus


class ArtifactStagingError(RuntimeError):
    pass


class TempStorageUnavailableError(RuntimeError):
    pass


class ManualUploadNormalizationPending(RuntimeError):
    def __init__(
        self,
        *,
        reason_code: str,
        next_attempt_at: datetime | None,
    ) -> None:
        self.reason_code = reason_code
        self.next_attempt_at = next_attempt_at
        super().__init__(reason_code)


class ManualUploadNormalizationTerminal(RuntimeError):
    def __init__(self, *, reason_code: str, cancelled: bool = False) -> None:
        self.reason_code = reason_code
        self.cancelled = cancelled
        super().__init__(reason_code)


class ProcessingUsageUnavailable(RuntimeError):
    pass


async def _await_provider_egress(operation: Awaitable[Any]) -> Any:
    """Finish initiated provider egress before acknowledging cancellation."""

    task = asyncio.ensure_future(operation)
    deferred_cancel: asyncio.CancelledError | None = None
    while True:
        try:
            result = await asyncio.shield(task)
        except asyncio.CancelledError as exc:
            deferred_cancel = deferred_cancel or exc
            if not task.done():
                continue
            if not task.cancelled():
                with suppress(Exception):
                    task.result()
            raise deferred_cancel from exc
        except Exception as exc:
            if deferred_cancel is not None:
                raise deferred_cancel from exc
            raise
        if deferred_cancel is not None:
            raise deferred_cancel
        return result


def _provider_retry_at(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _schedule_processing_retry(
    workflow: ProcessingWorkflow,
    *,
    retry_after_seconds: int | None,
    provider_next_attempt_at: datetime | None = None,
    settings: object | None = None,
    respect_max_attempts: bool = False,
) -> None:
    scheduler = schedule_retry_with_settings if settings is not None else schedule_retry
    schedule_kwargs = {
        "now": datetime.now(UTC),
        "retry_count": int(workflow.retry_count or 0),
        "generation": int(workflow.schedule_generation or 0),
        "retry_after": (
            timedelta(seconds=max(0, int(retry_after_seconds)))
            if retry_after_seconds is not None
            else None
        ),
        "provider_next_attempt_at": provider_next_attempt_at,
        "deadline_at": workflow.deadline_at,
        "source": (
            "provider_next_retry_at"
            if provider_next_attempt_at is not None
            else "provider_retry_after"
            if retry_after_seconds is not None
            else None
        ),
    }
    schedule = (
        scheduler(settings, respect_max_attempts=respect_max_attempts, **schedule_kwargs)
        if settings is not None
        else scheduler(**schedule_kwargs)
    )
    workflow.retry_class = "retryable"
    workflow.retry_count = schedule.retry_count
    workflow.schedule_generation = schedule.generation
    workflow.next_attempt_at = schedule.next_attempt_at
    workflow.next_attempt_source = schedule.source


async def _cancel_stale_processing(
    db: AsyncSession,
    *,
    workflow: ProcessingWorkflow,
    reason: ProcessingLifecycleBlocked,
) -> None:
    try:
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.CANCELED,
            reason_code=str(reason),
            terminal=True,
        )
    except ProcessingLifecycleBlocked:
        # The deletion fence already persisted the terminal block.
        return


async def _ensure_processing_fence(
    db: AsyncSession,
    workflow: ProcessingWorkflow,
    *,
    mediascribe_job_id: UUID | None = None,
    submission_claim_token: str | None = None,
    manual_canonical_artifact_id: UUID | None = None,
) -> None:
    meeting = await lock_meeting_fence(
        db, workspace_id=workflow.workspace_id, meeting_id=workflow.meeting_id
    )
    if (
        meeting is None
        or meeting_is_deleted_or_deleting(meeting)
        or int(meeting.deletion_epoch or 0) != int(workflow.deletion_epoch_at_start or 0)
    ):
        raise ProcessingLifecycleBlocked("meeting_deleting")
    current_workflow = await db.scalar(
        select(ProcessingWorkflow)
        .where(ProcessingWorkflow.id == workflow.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if current_workflow is None:
        raise ProcessingLifecycleBlocked("processing_workflow_missing")
    latest_workflow = await db.scalar(
        select(ProcessingWorkflow)
        .where(
            ProcessingWorkflow.workspace_id == workflow.workspace_id,
            ProcessingWorkflow.meeting_id == workflow.meeting_id,
            ProcessingWorkflow.media_revision_id == workflow.media_revision_id,
            ProcessingWorkflow.purpose == workflow.purpose,
        )
        .order_by(
            ProcessingWorkflow.attempt_ordinal.desc(),
            ProcessingWorkflow.created_at.desc(),
        )
    )
    if latest_workflow is None or latest_workflow.id != current_workflow.id:
        raise ProcessingLifecycleBlocked("processing_workflow_superseded")
    if not current_workflow.archive_audio and current_workflow.transient_state in {
        "purge_due",
        "purged",
    }:
        raise ProcessingLifecycleBlocked("transient_media_purge_started")
    if mediascribe_job_id is not None:
        current_job = await db.scalar(
            select(MediaScribeJob)
            .where(MediaScribeJob.id == mediascribe_job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            current_job is None
            or not submission_claim_token
            or current_job.submission_claim_token != submission_claim_token
            or current_job.status != MediaScribeJobStatus.SUBMITTING.value
            or current_job.external_job_id is not None
        ):
            raise ProcessingLifecycleBlocked("mediascribe_submission_claim_lost")
        current_job.submission_claimed_at = datetime.now(UTC)
    if manual_canonical_artifact_id is not None:
        normalization_job = await db.scalar(
            select(PlaybackNormalizationJob)
            .where(
                PlaybackNormalizationJob.workspace_id == workflow.workspace_id,
                PlaybackNormalizationJob.meeting_id == workflow.meeting_id,
                PlaybackNormalizationJob.media_revision_id == workflow.media_revision_id,
                PlaybackNormalizationJob.state == JobState.READY.value,
                PlaybackNormalizationJob.canonical_track_artifact_id
                == manual_canonical_artifact_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        canonical = await db.scalar(
            select(TrackArtifact)
            .where(
                TrackArtifact.id == manual_canonical_artifact_id,
                TrackArtifact.workspace_id == workflow.workspace_id,
                TrackArtifact.meeting_id == workflow.meeting_id,
                TrackArtifact.media_revision_id == workflow.media_revision_id,
                TrackArtifact.status == "stored",
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if normalization_job is None or canonical is None:
            raise ProcessingLifecycleBlocked("manual_canonical_source_unavailable")
    latest_revision = await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == workflow.workspace_id,
            MediaRevision.meeting_id == workflow.meeting_id,
            MediaRevision.status == "accepted",
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
    )
    if (latest_revision.id if latest_revision is not None else None) != workflow.media_revision_id:
        raise ProcessingLifecycleBlocked("processing_source_revision_stale")
    if latest_revision is None:
        return
    try:
        current_source_fingerprint = source_fingerprint_for_revision(latest_revision)
    except ValueError as exc:
        raise ProcessingLifecycleBlocked("processing_source_revision_unavailable") from exc
    if workflow.source_fingerprint != current_source_fingerprint:
        raise ProcessingLifecycleBlocked("processing_source_revision_stale")


async def _complete_provider_submission(
    *,
    db: AsyncSession,
    settings: Settings,
    workflow: ProcessingWorkflow,
    job: MediaScribeJob,
    claim_token: str,
    provider_operation: Awaitable[Any],
) -> SubmitProcessingResult:
    try:
        response = await provider_operation
    except OSError as exc:
        await store.release_mediascribe_submission_claim(db, job=job, claim_token=claim_token)
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.FAILED_RETRYABLE,
            reason_code=PROCESSING_TEMP_STORAGE_UNAVAILABLE,
        )
        raise RuntimeError(PROCESSING_TEMP_STORAGE_UNAVAILABLE) from exc
    except MediaScribeClientError as exc:
        malformed = exc.reason_code == MEDIASCRIBE_MALFORMED_RESPONSE
        if exc.egress_state == "unknown":
            await store.mark_mediascribe_submission_unknown(
                db,
                job=job,
                error_message=BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
            )
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.BLOCKED_UNKNOWN,
                reason_code=BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
            )
            raise MediaScribeClientError(
                BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
                retryable=False,
                status_code=exc.status_code,
                egress_state="unknown",
                headers=exc.headers,
                retry_after_seconds=exc.retry_after_seconds,
                request_id=exc.request_id,
                job_id=exc.job_id,
            ) from exc
        status = (
            ProcessingStatus.FAILED_TERMINAL
            if malformed or not exc.retryable
            else ProcessingStatus.FAILED_RETRYABLE
        )
        await store.release_mediascribe_submission_claim(db, job=job, claim_token=claim_token)
        await store.update_mediascribe_job_status(
            db,
            job=job,
            status=MediaScribeJobStatus.FAILED,
            reason_code=exc.reason_code,
            error_message=exc.reason_code,
            retryable=exc.retryable,
            retry_after_seconds=exc.retry_after_seconds,
            request_id=exc.request_id,
        )
        if status == ProcessingStatus.FAILED_RETRYABLE:
            _schedule_processing_retry(
                workflow,
                retry_after_seconds=exc.retry_after_seconds,
                settings=settings,
            )
        await store.set_workflow_status(
            db,
            workflow,
            status,
            reason_code=exc.reason_code,
            terminal=malformed or not exc.retryable,
        )
        raise

    try:
        await _ensure_processing_fence(db, workflow)
    except ProcessingLifecycleBlocked as exc:
        await store.persist_mediascribe_submission_fallback(
            db,
            job=job,
            external_job_id=response.external_job_id,
            reason_code=BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
            error_message=str(exc),
        )
        await _cancel_stale_processing(db, workflow=workflow, reason=exc)
        raise
    await store.persist_mediascribe_submission(
        db,
        job=job,
        external_job_id=response.external_job_id,
        status=response.status,
        submission_claim_token=claim_token,
        provider_status=response.status_raw,
        provider_queue_state=response.queue_state_raw,
        provider_attempt=response.attempt,
        provider_max_attempts=response.max_attempts,
        retry_after_seconds=response.retry_after_seconds,
        provider_next_retry_at=_provider_retry_at(response.next_retry_at),
        request_id=response.request_id,
    )
    if response.retry_after_seconds is not None or response.next_retry_at is not None:
        _schedule_processing_retry(
            workflow,
            retry_after_seconds=response.retry_after_seconds,
            provider_next_attempt_at=_provider_retry_at(response.next_retry_at),
            settings=settings,
        )
        if workflow.next_attempt_at is None:
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.FAILED_RETRYABLE,
                reason_code="processing_retry_deadline_exceeded",
                terminal=False,
            )
        else:
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.WAITING_RETRY,
                reason_code="provider_result_not_ready",
            )
    else:
        await store.set_workflow_status(db, workflow, ProcessingStatus.SUBMITTED)
    return SubmitProcessingResult(job=job, submitted=True)


async def submit_to_mediascribe(
    *,
    db: AsyncSession,
    settings: Settings,
    storage: object,
    mediascribe_client: object,
    workflow: ProcessingWorkflow,
) -> SubmitProcessingResult:
    await _ensure_processing_fence(db, workflow)
    existing_job = await store.get_mediascribe_job(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
        media_revision_id=workflow.media_revision_id,
        processing_workflow_id=workflow.id,
    )
    if existing_job is not None and existing_job.external_job_id:
        if workflow.status in {
            ProcessingStatus.WORKFLOW_STARTED.value,
            ProcessingStatus.SUBMITTING.value,
            ProcessingStatus.FAILED_RETRYABLE.value,
            ProcessingStatus.WAITING_RETRY.value,
        }:
            # A durable timer resumes the same idempotent provider job. Move
            # a crash-recovered pre-submit projection through its required
            # lifecycle boundary before polling the already-known job.
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.SUBMITTING,
                reason_code="submission_recovered",
                deadline_seconds=settings.processing_recovery_deadline_seconds,
            )
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.SUBMITTED,
                reason_code="submission_recovered",
            )
        return SubmitProcessingResult(job=existing_job, submitted=False)
    if (
        existing_job is not None
        and existing_job.status == MediaScribeJobStatus.BLOCKED.value
        and existing_job.last_error_code == BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN
    ):
        # The provider may already have accepted the multipart body.  Keep the
        # durable key and source fingerprint fenced to this workflow, then
        # replay the same request for reconciliation.  A new key is never
        # generated on this path.
        if (
            not existing_job.idempotency_key
            or not existing_job.source_fingerprint
            or existing_job.source_fingerprint != workflow.source_fingerprint
        ):
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.BLOCKED_UNKNOWN,
                reason_code=BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
            )
            raise MediaScribeClientError(
                BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
                retryable=False,
            )
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.BLOCKED_UNKNOWN,
            reason_code=BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
        )
    preparation = await store.load_manual_upload_preparation(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
        media_revision_id=workflow.media_revision_id,
    )
    if preparation is not None and preparation.state == "pending":
        raise ManualUploadNormalizationPending(
            reason_code=preparation.reason_code or "normalization_pending",
            next_attempt_at=preparation.next_attempt_at,
        )
    if preparation is not None and preparation.state in {"terminal", "cancelled"}:
        target = (
            ProcessingStatus.CANCELED
            if preparation.state == "cancelled"
            else ProcessingStatus.FAILED_TERMINAL
        )
        await store.set_workflow_status(
            db,
            workflow,
            target,
            reason_code=preparation.reason_code or "normalization_failed",
            terminal=True,
        )
        raise ManualUploadNormalizationTerminal(
            reason_code=preparation.reason_code or "normalization_failed",
            cancelled=preparation.state == "cancelled",
        )
    source = (
        preparation.source
        if preparation is not None
        else await store.load_processing_source(
            db,
            workspace_id=workflow.workspace_id,
            meeting_id=workflow.meeting_id,
            media_revision_id=workflow.media_revision_id,
        )
    )
    if source is None:
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.BLOCKED,
            reason_code=BLOCKED_MISSING_ARTIFACTS,
            terminal=True,
        )
        raise RuntimeError(BLOCKED_MISSING_ARTIFACTS)

    if source.byte_length > settings.processing_max_submit_audio_bytes:
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.BLOCKED,
            reason_code=BLOCKED_AUDIO_TOO_LARGE,
            terminal=True,
        )
        raise RuntimeError(BLOCKED_AUDIO_TOO_LARGE)

    usage_expires_at = datetime.now(UTC) + timedelta(hours=24)
    if not await store.ensure_processing_usage_reservation(
        db,
        workspace_id=workflow.workspace_id,
        media_revision_id=workflow.media_revision_id,
        expires_at=usage_expires_at,
    ):
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.BLOCKED,
            reason_code=BLOCKED_FREE_PROCESSING_EXHAUSTED,
            terminal=True,
        )
        raise ProcessingUsageUnavailable(BLOCKED_FREE_PROCESSING_EXHAUSTED)

    try:
        job = await store.upsert_mediascribe_job(
            db,
            workflow=workflow,
            mic_artifact=source.mic_artifact,
            incoming_artifact=source.incoming_artifact,
            source_artifact=source.source_artifact,
            request_mode=source.request_mode,
            source_fingerprint=workflow.source_fingerprint,
            diarize=settings.mediascribe_diarize,
            summarize=settings.mediascribe_summarize,
        )
    except ProcessingLifecycleBlocked as exc:
        if str(exc) == "processing_request_fingerprint_conflict":
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.BLOCKED,
                reason_code=str(exc),
                terminal=True,
            )
        raise
    claim_token = await store.claim_mediascribe_submission(db, job=job)
    if claim_token is None:
        resolved = await store.wait_for_mediascribe_submission(db, job_id=job.id)
        if resolved is not None and resolved.external_job_id:
            return SubmitProcessingResult(job=resolved, submitted=False)
        claim_token = await store.claim_mediascribe_submission(db, job=job)
        if claim_token is None:
            raise MediaScribeClientError(
                MEDIASCRIBE_SUBMISSION_IN_PROGRESS,
                retryable=True,
            )
    transitioned = await store.set_workflow_status(
        db,
        workflow,
        ProcessingStatus.SUBMITTING,
        deadline_seconds=settings.processing_recovery_deadline_seconds,
    )
    if transitioned.status != ProcessingStatus.SUBMITTING.value:
        await store.release_mediascribe_submission_claim(db, job=job, claim_token=claim_token)
        raise MediaScribeClientError("processing_workflow_terminal", retryable=False)
    # upsert/claim/status each commit the durable idempotency handoff. Keep an
    # explicit transaction boundary here so staging never inherits a lifecycle
    # row lock from a future store implementation.
    await db.commit()
    try:
        with tempfile.TemporaryDirectory(prefix="twobrain-rec-mediascribe-") as temp_dir:
            temp_path = Path(temp_dir)
            _ensure_temp_capacity(temp_path, source.byte_length)
            if source.request_mode == "single_track":
                media_artifact = source.source_artifact
                if media_artifact is None:
                    raise ArtifactStagingError("source_artifact_missing")
                is_manual_canonical = source.source_kind == "manual_upload"
                media_path = temp_path / (
                    "meeting-transcription.wav"
                    if source.is_v5_mixed_recording
                    else "manual-media.m4a"
                    if is_manual_canonical
                    else "source-media.bin"
                )
                await _stage_artifact(
                    storage,
                    media_artifact.storage_object_key,
                    media_path,
                    expected_bytes=media_artifact.byte_length,
                    expected_sha256=media_artifact.sha256,
                )
                if source.is_v5_mixed_recording:
                    _verify_v5_canonical_wav(media_path)
                await _ensure_processing_fence(
                    db,
                    workflow,
                    mediascribe_job_id=job.id,
                    submission_claim_token=claim_token,
                    manual_canonical_artifact_id=(
                        media_artifact.id if is_manual_canonical else None
                    ),
                )
                # Release the meeting fence before provider I/O. The claim and
                # idempotency key are durable; the post-egress fence below
                # rechecks lifecycle before persisting the opaque job ID.
                await db.commit()
                with media_path.open("rb") as media_file:
                    result = await _await_provider_egress(
                        _complete_provider_submission(
                            db=db,
                            settings=settings,
                            workflow=workflow,
                            job=job,
                            claim_token=claim_token,
                            provider_operation=mediascribe_client.submit_single_track(
                                media_file=media_file,
                                media_content_type="audio/wav"
                                if source.is_v5_mixed_recording
                                else "audio/mp4"
                                if is_manual_canonical
                                else media_artifact.codec,
                                media_filename="meeting-transcription.wav"
                                if source.is_v5_mixed_recording
                                else "manual-media.m4a"
                                if is_manual_canonical
                                else None,
                                diarize=bool(job.diarize),
                                summarize=bool(job.summarize),
                                num_speakers=job.num_speakers,
                                speaker_count_mode=job.speaker_count_mode,
                                idempotency_key=job.idempotency_key,
                            ),
                        )
                    )
            else:
                mic = source.mic_artifact
                incoming = source.incoming_artifact
                if mic is None or incoming is None:
                    raise ArtifactStagingError("track_artifact_missing")
                mic_path = temp_path / "microphone.wav"
                incoming_path = temp_path / "incoming.wav"
                await _stage_artifact(
                    storage,
                    mic.storage_object_key,
                    mic_path,
                    expected_bytes=mic.byte_length,
                    expected_sha256=mic.sha256,
                )
                await _stage_artifact(
                    storage,
                    incoming.storage_object_key,
                    incoming_path,
                    expected_bytes=incoming.byte_length,
                    expected_sha256=incoming.sha256,
                )
                await _ensure_processing_fence(
                    db,
                    workflow,
                    mediascribe_job_id=job.id,
                    submission_claim_token=claim_token,
                )
                await db.commit()
                with mic_path.open("rb") as mic_file, incoming_path.open("rb") as incoming_file:
                    result = await _await_provider_egress(
                        _complete_provider_submission(
                            db=db,
                            settings=settings,
                            workflow=workflow,
                            job=job,
                            claim_token=claim_token,
                            provider_operation=mediascribe_client.submit_dual_track(
                                mic_file=mic_file,
                                incoming_file=incoming_file,
                                diarize=bool(job.diarize),
                                summarize=bool(job.summarize),
                                num_speakers=job.num_speakers,
                                speaker_count_mode=job.speaker_count_mode,
                                idempotency_key=job.idempotency_key,
                            ),
                        )
                    )
    except ProcessingLifecycleBlocked as exc:
        await store.release_mediascribe_submission_claim(db, job=job, claim_token=claim_token)
        await _cancel_stale_processing(db, workflow=workflow, reason=exc)
        raise
    except ArtifactStagingError as exc:
        await store.release_mediascribe_submission_claim(db, job=job, claim_token=claim_token)
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.BLOCKED,
            reason_code=BLOCKED_MISSING_ARTIFACTS,
            terminal=True,
        )
        raise RuntimeError(BLOCKED_MISSING_ARTIFACTS) from exc
    except TempStorageUnavailableError as exc:
        await store.release_mediascribe_submission_claim(db, job=job, claim_token=claim_token)
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.FAILED_RETRYABLE,
            reason_code=PROCESSING_TEMP_STORAGE_UNAVAILABLE,
        )
        raise RuntimeError(PROCESSING_TEMP_STORAGE_UNAVAILABLE) from exc
    except OSError as exc:
        await store.release_mediascribe_submission_claim(db, job=job, claim_token=claim_token)
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.FAILED_RETRYABLE,
            reason_code=PROCESSING_TEMP_STORAGE_UNAVAILABLE,
        )
        raise RuntimeError(PROCESSING_TEMP_STORAGE_UNAVAILABLE) from exc
    return result


def _ensure_temp_capacity(temp_dir: Path, expected_bytes: int) -> None:
    try:
        free_bytes = shutil.disk_usage(temp_dir).free
    except OSError as exc:
        raise TempStorageUnavailableError(PROCESSING_TEMP_STORAGE_UNAVAILABLE) from exc
    if free_bytes < expected_bytes:
        raise TempStorageUnavailableError(PROCESSING_TEMP_STORAGE_UNAVAILABLE)


async def _stage_artifact(
    storage: object,
    object_key: str,
    target_path: Path,
    *,
    expected_bytes: int,
    expected_sha256: str,
) -> None:
    verified_async = getattr(storage, "download_verified_to_path_async", None)
    verified = getattr(storage, "download_verified_to_path", None)
    download_to_path_async = getattr(storage, "download_to_path_async", None)
    download_to_path = getattr(storage, "download_to_path", None)
    try:
        if verified_async is not None:
            await verified_async(
                object_key,
                target_path,
                expected_length=expected_bytes,
                expected_sha256=expected_sha256,
                max_bytes=expected_bytes,
                chunk_size=DOWNLOAD_CHUNK_BYTES,
            )
            return
        if verified is not None:
            await to_thread.run_sync(
                lambda: verified(
                    object_key,
                    target_path,
                    expected_length=expected_bytes,
                    expected_sha256=expected_sha256,
                    max_bytes=expected_bytes,
                    chunk_size=DOWNLOAD_CHUNK_BYTES,
                )
            )
            return
        if download_to_path_async is not None:
            downloaded = await download_to_path_async(
                object_key, target_path, chunk_size=DOWNLOAD_CHUNK_BYTES
            )
        elif download_to_path is not None:
            downloaded = await to_thread.run_sync(
                lambda: download_to_path(object_key, target_path, chunk_size=DOWNLOAD_CHUNK_BYTES)
            )
        else:
            raise ArtifactStagingError("storage_streaming_unavailable")
    except KeyError as exc:
        raise ArtifactStagingError("storage_object_missing") from exc
    except StorageTransferError as exc:
        if exc.reason_code == "source_missing":
            raise ArtifactStagingError("storage_object_missing") from exc
        if exc.reason_code == "source_mismatch":
            raise ArtifactStagingError("storage_object_digest_mismatch") from exc
        raise TempStorageUnavailableError(PROCESSING_TEMP_STORAGE_UNAVAILABLE) from exc
    except OSError as exc:
        raise TempStorageUnavailableError(PROCESSING_TEMP_STORAGE_UNAVAILABLE) from exc
    try:
        actual_bytes = target_path.stat().st_size
    except OSError as exc:
        raise ArtifactStagingError("storage_object_not_staged") from exc
    if downloaded != expected_bytes or actual_bytes != expected_bytes:
        raise ArtifactStagingError("storage_object_size_mismatch")
    try:
        actual_sha256 = await to_thread.run_sync(_sha256_file, target_path)
    except OSError as exc:
        raise ArtifactStagingError("storage_object_not_staged") from exc
    if actual_sha256 != expected_sha256:
        raise ArtifactStagingError("storage_object_digest_mismatch")


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(DOWNLOAD_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_v5_canonical_wav(path: Path) -> None:
    """Verify the exact v5 PCM WAV boundary before any provider request.

    Descriptor validation at ingest is necessary but insufficient: this parses
    the staged bytes so a mislabeled object can never be sent as canonical
    audio. The parser is bounded to the RIFF headers and never loads audio into
    memory.
    """

    try:
        file_size = path.stat().st_size
        with path.open("rb") as stream:
            header = stream.read(12)
            if len(header) != 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
                raise ArtifactStagingError("invalid_v5_wav_header")
            riff_size = int.from_bytes(header[4:8], "little")
            if riff_size + 8 != file_size:
                raise ArtifactStagingError("invalid_v5_wav_size")
            fmt: bytes | None = None
            data_size: int | None = None
            while stream.tell() + 8 <= file_size:
                chunk_header = stream.read(8)
                chunk_id = chunk_header[:4]
                chunk_size = int.from_bytes(chunk_header[4:], "little")
                if chunk_size > file_size - stream.tell():
                    raise ArtifactStagingError("invalid_v5_wav_chunk")
                if chunk_id == b"fmt ":
                    fmt = stream.read(chunk_size)
                elif chunk_id == b"data":
                    data_size = chunk_size
                    stream.seek(chunk_size, 1)
                else:
                    stream.seek(chunk_size, 1)
                if chunk_size % 2:
                    if stream.tell() >= file_size:
                        raise ArtifactStagingError("invalid_v5_wav_padding")
                    stream.seek(1, 1)
    except OSError as exc:
        raise ArtifactStagingError("invalid_v5_wav") from exc

    if fmt is None or len(fmt) < 16 or data_size is None or data_size <= 0:
        raise ArtifactStagingError("invalid_v5_wav_format")
    audio_format = int.from_bytes(fmt[0:2], "little")
    channel_count = int.from_bytes(fmt[2:4], "little")
    sample_rate = int.from_bytes(fmt[4:8], "little")
    block_align = int.from_bytes(fmt[12:14], "little")
    bits_per_sample = int.from_bytes(fmt[14:16], "little")
    if (
        audio_format != 1
        or channel_count != 1
        or sample_rate != 16_000
        or block_align != 2
        or bits_per_sample != 16
        or data_size % block_align != 0
    ):
        raise ArtifactStagingError("invalid_v5_wav_format")


async def poll_and_import_mediascribe_result(
    *,
    db: AsyncSession,
    workflow: ProcessingWorkflow,
    job: MediaScribeJob,
    mediascribe_client: object,
    outcome_generation_enabled: bool = False,
) -> ImportProcessingResult:
    if job.external_job_id is None:
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.FAILED_TERMINAL,
            reason_code="missing_external_job_id",
            terminal=True,
        )
        return ImportProcessingResult(imported=False, status=ProcessingStatus.FAILED_TERMINAL)
    try:
        await _ensure_processing_fence(db, workflow)
    except ProcessingLifecycleBlocked as exc:
        await _cancel_stale_processing(db, workflow=workflow, reason=exc)
        return ImportProcessingResult(imported=False, status=ProcessingStatus.CANCELED)
    await store.set_workflow_status(db, workflow, ProcessingStatus.POLLING)
    try:
        poll = await mediascribe_client.poll_job(job.external_job_id)
    except MediaScribeClientError as exc:
        malformed = exc.reason_code == MEDIASCRIBE_MALFORMED_RESPONSE
        status = (
            ProcessingStatus.FAILED_TERMINAL
            if malformed or not exc.retryable
            else ProcessingStatus.FAILED_RETRYABLE
        )
        await store.update_mediascribe_job_status(
            db,
            job=job,
            status=MediaScribeJobStatus.FAILED,
            reason_code=exc.reason_code,
            error_message=exc.reason_code,
            retryable=exc.retryable,
            retry_after_seconds=exc.retry_after_seconds,
            request_id=exc.request_id,
        )
        await store.set_workflow_status(
            db,
            workflow,
            status,
            reason_code=exc.reason_code,
            terminal=malformed or not exc.retryable,
        )
        return ImportProcessingResult(imported=False, status=status)
    try:
        await _ensure_processing_fence(db, workflow)
    except ProcessingLifecycleBlocked as exc:
        await _cancel_stale_processing(db, workflow=workflow, reason=exc)
        return ImportProcessingResult(imported=False, status=ProcessingStatus.CANCELED)

    if poll.status != MediaScribeJobStatus.READY:
        if poll.status == MediaScribeJobStatus.FAILED:
            await store.update_mediascribe_job_status(
                db,
                job=job,
                status=poll.status,
                reason_code=poll.reason_code,
                error_message=poll.error_origin,
                retryable=False,
                provider_status=poll.status_raw,
                provider_queue_state=poll.queue_state_raw,
                provider_attempt=poll.attempt,
                provider_max_attempts=poll.max_attempts,
                retry_after_seconds=poll.retry_after_seconds,
                provider_next_retry_at=_provider_retry_at(poll.next_retry_at),
                request_id=poll.request_id,
            )
            if _is_input_audio_failure(poll):
                return await _persist_input_audio_failure_result(
                    db=db, workflow=workflow, job=job, poll=poll
                )
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.FAILED_TERMINAL,
                reason_code=poll.reason_code,
                terminal=True,
            )
            await _record_processing_diagnostic(
                db,
                workflow=workflow,
                job=job,
                event_type=DIAGNOSTIC_MEDIASCRIBE_SERVICE_PROBLEM,
                diagnostic_class=DIAGNOSTIC_MEDIASCRIBE_SERVICE_PROBLEM,
                error_code=poll.error_code or poll.reason_code,
                error_origin=poll.error_origin,
                failure_reason=poll.reason_code,
                failure_source=FAILURE_SOURCE_MEDIASCRIBE,
            )
            return ImportProcessingResult(imported=False, status=ProcessingStatus.FAILED_TERMINAL)
        await store.update_mediascribe_job_status(
            db,
            job=job,
            status=poll.status,
            reason_code=poll.reason_code,
            provider_status=poll.status_raw,
            provider_queue_state=poll.queue_state_raw,
            provider_attempt=poll.attempt,
            provider_max_attempts=poll.max_attempts,
            retry_after_seconds=poll.retry_after_seconds,
            provider_next_retry_at=_provider_retry_at(poll.next_retry_at),
            request_id=poll.request_id,
        )
        return ImportProcessingResult(imported=False, status=ProcessingStatus.POLLING)

    await store.update_mediascribe_job_status(
        db,
        job=job,
        status=poll.status,
        reason_code=poll.reason_code,
        provider_status=poll.status_raw,
        provider_queue_state=poll.queue_state_raw,
        provider_attempt=poll.attempt,
        provider_max_attempts=poll.max_attempts,
        request_id=poll.request_id,
    )
    await store.set_workflow_status(db, workflow, ProcessingStatus.IMPORTING)
    try:
        await _ensure_processing_fence(db, workflow)
    except ProcessingLifecycleBlocked as exc:
        await _cancel_stale_processing(db, workflow=workflow, reason=exc)
        return ImportProcessingResult(imported=False, status=ProcessingStatus.CANCELED)
    try:
        result = _classify_ready_result(
            normalize_result(await mediascribe_client.fetch_result(job.external_job_id)),
            diarization_required=bool(job.diarize),
        )
    except MediaScribeClientError as exc:
        malformed = exc.reason_code == MEDIASCRIBE_MALFORMED_RESPONSE
        status = (
            ProcessingStatus.FAILED_TERMINAL
            if malformed or not exc.retryable
            else ProcessingStatus.FAILED_RETRYABLE
        )
        await store.update_mediascribe_job_status(
            db,
            job=job,
            status=MediaScribeJobStatus.FAILED,
            reason_code=exc.reason_code,
            error_message=exc.reason_code,
            retryable=exc.retryable,
            retry_after_seconds=exc.retry_after_seconds,
            request_id=exc.request_id,
        )
        await store.set_workflow_status(
            db,
            workflow,
            status,
            reason_code=exc.reason_code,
            terminal=malformed or not exc.retryable,
        )
        return ImportProcessingResult(imported=False, status=status)
    except MediaScribeResultValidationError:
        await store.update_mediascribe_job_status(
            db,
            job=job,
            status=MediaScribeJobStatus.FAILED,
            reason_code=MEDIASCRIBE_MALFORMED_RESPONSE,
            error_message=MEDIASCRIBE_MALFORMED_RESPONSE,
            retryable=False,
        )
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.FAILED_TERMINAL,
            reason_code=MEDIASCRIBE_MALFORMED_RESPONSE,
            terminal=True,
        )
        return ImportProcessingResult(imported=False, status=ProcessingStatus.FAILED_TERMINAL)
    try:
        await _ensure_processing_fence(db, workflow)
    except ProcessingLifecycleBlocked as exc:
        await _cancel_stale_processing(db, workflow=workflow, reason=exc)
        return ImportProcessingResult(imported=False, status=ProcessingStatus.CANCELED)
    try:
        result_row = await store.persist_processing_result(
            db,
            job=job,
            result=result,
            source_result_hash=result_digest(result),
        )
    except QuotaExceeded:
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.BLOCKED,
            reason_code=BLOCKED_FREE_PROCESSING_EXHAUSTED,
            terminal=True,
        )
        return ImportProcessingResult(imported=False, status=ProcessingStatus.BLOCKED)
    except ProcessingLifecycleBlocked as exc:
        await store.set_workflow_status(
            db, workflow, ProcessingStatus.CANCELED, reason_code=str(exc), terminal=True
        )
        return ImportProcessingResult(imported=False, status=ProcessingStatus.CANCELED)
    try:
        await ensure_outcomes_for_processing_result(
            db,
            result=result_row,
            publish_initial_baseline=True,
        )
    except ProcessingLifecycleBlocked as exc:
        await _cancel_stale_processing(db, workflow=workflow, reason=exc)
        return ImportProcessingResult(imported=True, status=ProcessingStatus.CANCELED)
    if outcome_generation_enabled:
        await ensure_automatic_summary_candidate(
            db,
            workspace_id=result_row.workspace_id,
            meeting_id=result_row.meeting_id,
        )
    imported_status = (
        ProcessingStatus.FAILED_TERMINAL
        if result.failure_reason == MEDIASCRIBE_MALFORMED_RESPONSE
        and result.failure_source == FAILURE_SOURCE_MEDIASCRIBE
        else ProcessingStatus.PROCESSED
    )
    await store.set_workflow_status(
        db,
        workflow,
        imported_status,
        reason_code=result.failure_reason,
        terminal=True,
    )
    await _record_import_diagnostic(db, workflow=workflow, job=job, result=result)
    return ImportProcessingResult(imported=True, status=imported_status)


def _is_input_audio_failure(poll: MediaScribePollResponse) -> bool:
    return (
        poll.error_code == INVALID_AUDIO_PAYLOAD and poll.error_origin == FAILURE_SOURCE_INPUT_AUDIO
    )


def _classify_ready_result(
    result: MediaScribeResult,
    *,
    diarization_required: bool,
) -> MediaScribeResult:
    if (
        result.transcript_status == ProcessingAvailabilityStatus.UNAVAILABLE
        and result.transcript_reason == NO_RECOGNIZABLE_SPEECH
    ):
        return result.model_copy(
            update={
                "failure_reason": NO_RECOGNIZABLE_SPEECH,
                "failure_source": FAILURE_SOURCE_INPUT_AUDIO,
            }
        )
    if (
        result.transcript_status != ProcessingAvailabilityStatus.AVAILABLE
        or not result.transcript
        or diarization_required
        and not result.diarization
    ):
        return result.model_copy(
            update={
                "failure_reason": MEDIASCRIBE_MALFORMED_RESPONSE,
                "failure_source": FAILURE_SOURCE_MEDIASCRIBE,
            }
        )
    return result


async def _persist_input_audio_failure_result(
    *,
    db: AsyncSession,
    workflow: ProcessingWorkflow,
    job: MediaScribeJob,
    poll: MediaScribePollResponse,
) -> ImportProcessingResult:
    result = MediaScribeResult(
        external_job_id=job.external_job_id or poll.external_job_id,
        transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE,
        failure_reason=poll.error_code or poll.reason_code or INVALID_AUDIO_PAYLOAD,
        failure_source=FAILURE_SOURCE_INPUT_AUDIO,
    )
    try:
        result_row = await store.persist_processing_result(
            db,
            job=job,
            result=result,
            source_result_hash=result_digest(result),
        )
    except ProcessingLifecycleBlocked as exc:
        await store.set_workflow_status(
            db, workflow, ProcessingStatus.CANCELED, reason_code=str(exc), terminal=True
        )
        return ImportProcessingResult(imported=False, status=ProcessingStatus.CANCELED)
    try:
        await ensure_outcomes_for_processing_result(db, result=result_row)
    except ProcessingLifecycleBlocked as exc:
        await _cancel_stale_processing(db, workflow=workflow, reason=exc)
        return ImportProcessingResult(imported=True, status=ProcessingStatus.CANCELED)
    await store.set_workflow_status(
        db,
        workflow,
        ProcessingStatus.FAILED_TERMINAL,
        reason_code=result.failure_reason,
        terminal=True,
    )
    await _record_processing_diagnostic(
        db,
        workflow=workflow,
        job=job,
        event_type=DIAGNOSTIC_INPUT_AUDIO_PROBLEM,
        diagnostic_class=DIAGNOSTIC_INPUT_AUDIO_PROBLEM,
        error_code=poll.error_code or poll.reason_code,
        error_origin=poll.error_origin,
        failure_reason=result.failure_reason,
        failure_source=FAILURE_SOURCE_INPUT_AUDIO,
        transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
    )
    return ImportProcessingResult(imported=True, status=ProcessingStatus.FAILED_TERMINAL)


async def _record_import_diagnostic(
    db: AsyncSession,
    *,
    workflow: ProcessingWorkflow,
    job: MediaScribeJob,
    result: MediaScribeResult,
) -> None:
    if (
        result.failure_source == FAILURE_SOURCE_INPUT_AUDIO
        and result.transcript_status == ProcessingAvailabilityStatus.UNAVAILABLE
    ):
        await _record_processing_diagnostic(
            db,
            workflow=workflow,
            job=job,
            event_type=DIAGNOSTIC_PROCESSED_NO_TRANSCRIPT,
            diagnostic_class=DIAGNOSTIC_PROCESSED_NO_TRANSCRIPT,
            transcript_status=result.transcript_status.value,
            transcript_reason=result.transcript_reason,
            failure_reason=result.failure_reason,
            failure_source=result.failure_source,
            segment_count=len(result.transcript),
        )
        return
    if (
        result.failure_source == FAILURE_SOURCE_MEDIASCRIBE
        and result.failure_reason == MEDIASCRIBE_MALFORMED_RESPONSE
    ):
        await _record_processing_diagnostic(
            db,
            workflow=workflow,
            job=job,
            event_type=DIAGNOSTIC_MEDIASCRIBE_SERVICE_PROBLEM,
            diagnostic_class=DIAGNOSTIC_MEDIASCRIBE_SERVICE_PROBLEM,
            failure_reason=result.failure_reason,
            failure_source=result.failure_source,
            transcript_status=result.transcript_status.value,
            segment_count=len(result.transcript),
        )
        return
    attribution_metadata = (
        result.attribution_diagnostics.as_audit_metadata()
        if result.attribution_diagnostics is not None
        else {}
    )
    await store.record_processing_audit_event(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
        processing_workflow_id=workflow.id,
        mediascribe_job_id=job.id,
        event_type="result_imported",
        metadata={
            "mediascribe_job_id": job.id,
            "segment_count": len(result.transcript),
            "diarization_segment_count": len(result.diarization or []),
            "summary_status": result.summary_status.value,
            "transcript_status": result.transcript_status.value,
            "transcript_reason": result.transcript_reason,
            "source_result_hash": result_digest(result),
            **attribution_metadata,
        },
    )


async def _record_processing_diagnostic(
    db: AsyncSession,
    *,
    workflow: ProcessingWorkflow,
    job: MediaScribeJob,
    event_type: str,
    diagnostic_class: str,
    transcript_status: str | None = None,
    transcript_reason: str | None = None,
    error_code: str | None = None,
    error_origin: str | None = None,
    failure_reason: str | None = None,
    failure_source: str | None = None,
    segment_count: int | None = None,
) -> None:
    metadata = {
        "mediascribe_job_id": job.id,
        "transcript_status": transcript_status,
        "transcript_reason": transcript_reason,
        "error_code": error_code,
        "error_origin": error_origin,
        "failure_reason": failure_reason,
        "failure_source": failure_source,
        "diagnostic_class": diagnostic_class,
    }
    if segment_count is not None:
        metadata["segment_count"] = segment_count
    await store.record_processing_audit_event(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
        processing_workflow_id=workflow.id,
        mediascribe_job_id=job.id,
        event_type=event_type,
        metadata={key: value for key, value in metadata.items() if value is not None},
    )
