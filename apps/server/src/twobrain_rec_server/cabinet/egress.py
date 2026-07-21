from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from anyio import to_thread
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    ArtifactClass,
    ArtifactEgressState,
    ExportPackageExclusion,
    ExportPackageResponse,
    MeetingActivityItem,
    MeetingActivityResponse,
    PlaybackPreparationState,
)
from twobrain_rec_server.cabinet.access import AccessDecision
from twobrain_rec_server.cabinet.constants import DELETION_TRUTH_COPY
from twobrain_rec_server.cabinet.view_models import (
    format_timestamp,
    playback_reason_copy,
    playback_terminal_reason,
)
from twobrain_rec_server.db.models import (
    ExportPackage,
    MediaRevision,
    Meeting,
    MeetingArtifactPolicy,
    MeetingEgressAuditEvent,
    PlaybackNormalizationJob,
    ProcessingResult,
    TrackArtifact,
    TranscriptSegment,
)
from twobrain_rec_server.domain.statuses import (
    DeletionState,
    MediaRevisionStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    SummaryStatus,
    TrackRole,
)
from twobrain_rec_server.normalization.media import MAX_OUTPUT_BYTES
from twobrain_rec_server.normalization.statuses import (
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
    JobState,
)
from twobrain_rec_server.observability.redaction import redact_mapping

ALLOWED_AUDIT_KEYS = {
    "artifact_class",
    "policy_reason",
    "viewer_access_state",
    "request_class",
    "outcome",
    "byte_length",
    "export_id",
    "share_grant_id",
    "source_mode",
    "range_end",
    "range_start",
    "stream_state",
}


@dataclass(frozen=True, slots=True)
class DownloadArtifact:
    filename: str
    media_type: str
    body: bytes | Iterator[bytes]
    byte_length: int


@dataclass(frozen=True, slots=True)
class PlaybackArtifact:
    media_type: str
    body: Iterator[bytes]
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PlaybackByteRange:
    start: int
    end: int


class ReviewAudioBuildError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def safe_audit_metadata(metadata: Mapping[str, object] | None) -> dict[str, object]:
    if not metadata:
        return {}
    redacted = redact_mapping(metadata)
    safe: dict[str, object] = {}
    for key, value in redacted.items():
        if key not in ALLOWED_AUDIT_KEYS:
            continue
        if isinstance(value, str | int | float | bool) or value is None:
            safe[key] = value
    return safe


async def record_egress_audit_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID | None,
    actor_user_id: UUID | None,
    device_id: UUID | None,
    event_type: str,
    outcome: str,
    artifact_class: ArtifactClass | None = None,
    policy_reason: str | None = None,
    metadata: Mapping[str, object] | None = None,
) -> MeetingEgressAuditEvent:
    event = MeetingEgressAuditEvent(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type=event_type,
        artifact_class=artifact_class,
        policy_reason=policy_reason,
        outcome=outcome,
        metadata_json=safe_audit_metadata(metadata),
        created_at=datetime.now(UTC),
    )
    db.add(event)
    try:
        await db.flush()
    except SQLAlchemyError as exc:
        raise ProblemDetail(
            status=503,
            code="audit_unavailable",
            title="Audit unavailable",
            detail="The action failed closed because audit evidence could not be persisted.",
        ) from exc
    return event


async def artifact_egress_states(
    db: AsyncSession,
    *,
    meeting: Meeting,
    access: AccessDecision,
    result: ProcessingResult | None,
) -> list[ArtifactEgressState]:
    if meeting_deletion_active(meeting):
        return _deleted_artifact_states()
    policy = await resolve_artifact_policy(
        db, workspace_id=meeting.workspace_id, meeting_id=meeting.id
    )
    audio_artifacts = await stored_audio_artifacts(
        db, workspace_id=meeting.workspace_id, meeting_id=meeting.id
    )
    states = [
        _audio_state(policy.audio_download, access, audio_artifacts),
        _transcript_state(policy.transcript_download, access, result),
        _summary_state(policy.summary_download, access, result),
    ]
    package_state = _package_state(policy.package_export, access, states)
    return states + [package_state]


async def resolve_artifact_policy(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> MeetingArtifactPolicy:
    policy = await db.scalar(
        select(MeetingArtifactPolicy).where(
            MeetingArtifactPolicy.workspace_id == workspace_id,
            MeetingArtifactPolicy.meeting_id == meeting_id,
        )
    )
    if policy is not None:
        return policy
    return MeetingArtifactPolicy(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        audio_download="disabled",
        transcript_download="disabled",
        summary_download="disabled",
        package_export="disabled",
        policy_source="meeting_default",
    )


async def stored_audio_artifacts(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> list[TrackArtifact]:
    revision = await _latest_accepted_media_revision(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    if revision is None:
        return []
    job = await _normalization_job_for_revision(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=revision.id,
    )
    if job is None or job.state != JobState.READY.value:
        return []
    artifact = await _validated_canonical_artifact(db, job=job)
    return [artifact] if artifact is not None else []


def _is_stored_review_m4a(
    artifact: TrackArtifact,
    *,
    job: PlaybackNormalizationJob | None = None,
) -> bool:
    source_fingerprint = artifact.source_fingerprint_sha256 or ""
    return (
        artifact.track_role == TrackRole.PLAYBACK.value
        and artifact.status == "stored"
        and artifact.media_revision_id is not None
        and artifact.codec == "m4a-aac-lc"
        and artifact.sample_rate_hz == 48_000
        and artifact.channel_count == 1
        and artifact.duration_seconds > 0
        and 0 < artifact.byte_length <= MAX_OUTPUT_BYTES
        and len(artifact.sha256) == 64
        and artifact.normalization_profile_version == CANONICAL_PROFILE_VERSION
        and artifact.validation_version == VALIDATION_VERSION
        and artifact.validated_at is not None
        and len(source_fingerprint) == 64
        and artifact.derivation_kind is not None
        and (
            job is None
            or (
                job.state == JobState.READY.value
                and job.canonical_track_artifact_id == artifact.id
                and job.workspace_id == artifact.workspace_id
                and job.meeting_id == artifact.meeting_id
                and job.media_revision_id == artifact.media_revision_id
                and job.profile_version == artifact.normalization_profile_version
                and job.validation_version == artifact.validation_version
                and job.source_fingerprint_sha256 == artifact.source_fingerprint_sha256
            )
        )
    )


async def review_playback_state(
    db: AsyncSession,
    *,
    meeting: Meeting,
    access: AccessDecision,
    storage: object | None = None,
) -> PlaybackPreparationState:
    deletion_state = meeting.deletion_state or DeletionState.NONE.value
    if deletion_state != DeletionState.NONE.value:
        deleted = deletion_state == DeletionState.COMPLETE.value or meeting.deleted_at is not None
        return PlaybackPreparationState(
            state="deleted" if deleted else "deleting",
            reason_code="meeting_deleted" if deleted else "meeting_deleting",
            label=playback_reason_copy("meeting_deleted" if deleted else "meeting_deleting"),
        )
    if not access.can_view:
        return PlaybackPreparationState(
            state="unavailable",
            reason_code="access_denied",
            label=playback_reason_copy("access_denied"),
        )

    revision = await _latest_accepted_media_revision(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
    )
    if revision is None:
        return PlaybackPreparationState(
            state="unavailable",
            reason_code="no_audio",
            label=playback_reason_copy("no_audio"),
        )
    job = await _normalization_job_for_revision(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        media_revision_id=revision.id,
    )
    if job is None:
        return PlaybackPreparationState(
            state="preparing",
            reason_code="reconciliation_pending",
            label=playback_reason_copy("reconciliation_pending"),
            automatic_recovery=True,
        )

    if job.state == JobState.READY.value:
        playback = await _validated_canonical_artifact(db, job=job)
        if playback is not None:
            object_exists = await _canonical_object_exists(
                storage,
                object_key=playback.storage_object_key,
            )
            if object_exists is not False and (object_exists is not None or storage is None):
                return PlaybackPreparationState(
                    state="available",
                    reason_code="canonical_ready",
                    label=playback_reason_copy("canonical_ready"),
                    can_play=True,
                )
            if object_exists is None:
                return PlaybackPreparationState(
                    state="preparing",
                    reason_code="reconciliation_pending",
                    label=playback_reason_copy("reconciliation_pending"),
                    automatic_recovery=True,
                )
        return PlaybackPreparationState(
            state="preparing",
            reason_code="canonical_artifact_missing",
            label=playback_reason_copy("canonical_artifact_missing"),
            automatic_recovery=True,
        )

    preparing = {
        JobState.QUEUED.value: "normalization_queued",
        JobState.RUNNING.value: "normalization_running",
        JobState.PUBLISHING.value: "normalization_publishing",
        JobState.RETRY_WAIT.value: "normalization_retry_wait",
    }.get(job.state)
    if preparing is not None:
        return PlaybackPreparationState(
            state="preparing",
            reason_code=preparing,
            label=playback_reason_copy(preparing),
            automatic_recovery=True,
        )

    if job.state == JobState.TERMINAL.value:
        reason_code = playback_terminal_reason(job.reason_code)
        return PlaybackPreparationState(
            state="unavailable",
            reason_code=reason_code,
            label=playback_reason_copy(reason_code),
        )

    if job.state == JobState.CANCELLED.value:
        deleted = job.reason_code in {"meeting_deleted", "audio_purged"}
        reason_code = (
            "audio_purged"
            if job.reason_code == "audio_purged"
            else ("meeting_deleted" if deleted else "meeting_deleting")
        )
        return PlaybackPreparationState(
            state="deleted" if deleted else "deleting",
            reason_code=reason_code,
            label=playback_reason_copy(reason_code),
        )

    return PlaybackPreparationState(
        state="preparing",
        reason_code="reconciliation_pending",
        label=playback_reason_copy("reconciliation_pending"),
        automatic_recovery=True,
    )


async def _latest_accepted_media_revision(
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
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
    )


async def _normalization_job_for_revision(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID,
) -> PlaybackNormalizationJob | None:
    return await db.scalar(
        select(PlaybackNormalizationJob).where(
            PlaybackNormalizationJob.workspace_id == workspace_id,
            PlaybackNormalizationJob.meeting_id == meeting_id,
            PlaybackNormalizationJob.media_revision_id == media_revision_id,
            PlaybackNormalizationJob.profile_version == CANONICAL_PROFILE_VERSION,
        )
    )


async def _validated_canonical_artifact(
    db: AsyncSession,
    *,
    job: PlaybackNormalizationJob,
) -> TrackArtifact | None:
    if job.canonical_track_artifact_id is None:
        return None
    artifact = await db.scalar(
        select(TrackArtifact).where(
            TrackArtifact.id == job.canonical_track_artifact_id,
            TrackArtifact.workspace_id == job.workspace_id,
            TrackArtifact.meeting_id == job.meeting_id,
            TrackArtifact.media_revision_id == job.media_revision_id,
        )
    )
    if artifact is None or not _is_stored_review_m4a(artifact, job=job):
        return None
    return artifact


async def _canonical_object_exists(
    storage: object | None,
    *,
    object_key: str,
) -> bool | None:
    if storage is None:
        return None
    exists_async = getattr(storage, "object_exists_async", None)
    if callable(exists_async):
        try:
            return bool(await exists_async(object_key))
        except Exception:
            return None
    exists = getattr(storage, "object_exists", None)
    if not callable(exists):
        return None
    try:
        return bool(await to_thread.run_sync(exists, object_key))
    except Exception:
        return None


async def _ensure_review_audio_storage_size(
    storage: object,
    *,
    object_key: str,
    expected_size: int,
) -> None:
    """Fail closed before exposing headers or bytes for a stale object."""
    stat_async = getattr(storage, "stat_object_async", None)
    stat_sync = getattr(storage, "stat_object", None)
    try:
        if callable(stat_async):
            result = await stat_async(object_key)
        elif callable(stat_sync):
            result = await to_thread.run_sync(stat_sync, object_key)
        else:
            raise ReviewAudioBuildError("storage_unavailable")
        actual_size = result if isinstance(result, int) else getattr(result, "size", None)
        if not isinstance(actual_size, int) or actual_size != expected_size:
            raise ReviewAudioBuildError("storage_object_size_mismatch")
    except ReviewAudioBuildError:
        raise
    except Exception as exc:
        raise ReviewAudioBuildError("storage_unavailable") from exc


async def download_artifact(
    db: AsyncSession,
    *,
    storage: object,
    meeting: Meeting,
    access: AccessDecision,
    artifact_class: ArtifactClass,
    result: ProcessingResult | None,
    actor_user_id: UUID,
    device_id: UUID,
) -> DownloadArtifact:
    if meeting_deletion_active(meeting):
        await record_egress_audit_event(
            db,
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            actor_user_id=actor_user_id,
            device_id=device_id,
            event_type="download_denied",
            outcome="denied",
            artifact_class=artifact_class,
            policy_reason="meeting_deletion_active",
            metadata={"artifact_class": artifact_class, "outcome": "denied"},
        )
        await db.commit()
        raise ProblemDetail(
            status=409, code="meeting_deletion_active", title="Meeting deletion is in progress"
        )
    states = {
        state.artifact_class: state
        for state in await artifact_egress_states(db, meeting=meeting, access=access, result=result)
    }
    state = states.get(artifact_class)
    if state is None or state.state != "available" or artifact_class == "package":
        await record_egress_audit_event(
            db,
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            actor_user_id=actor_user_id,
            device_id=device_id,
            event_type="download_denied",
            outcome="denied",
            artifact_class=artifact_class,
            policy_reason=state.reason if state is not None else "unsupported_artifact",
            metadata={"artifact_class": artifact_class, "outcome": "denied"},
        )
        await db.commit()
        raise ProblemDetail(status=409, code="artifact_unavailable", title="Artifact unavailable")

    await record_egress_audit_event(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="download_requested",
        outcome="allowed",
        artifact_class=artifact_class,
        policy_reason="policy_allowed",
        metadata={
            "artifact_class": artifact_class,
            "viewer_access_state": access.state,
            "request_class": "download",
        },
    )
    if artifact_class == "audio":
        try:
            playback = await _stored_review_m4a_artifact(db, meeting=meeting)
            await _ensure_review_audio_storage_size(
                storage,
                object_key=playback.storage_object_key,
                expected_size=playback.byte_length,
            )
            body = await _stream_storage_object(
                storage,
                playback.storage_object_key,
                offset=0,
                length=playback.byte_length,
            )
        except ReviewAudioBuildError as exc:
            status = 503 if exc.reason == "storage_unavailable" else 409
            code = "storage_unavailable" if status == 503 else "audio_unavailable"
            title = "Storage unavailable" if status == 503 else "Audio unavailable"
            await record_egress_audit_event(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                actor_user_id=actor_user_id,
                device_id=device_id,
                event_type="download_denied",
                outcome="denied",
                artifact_class=artifact_class,
                policy_reason=exc.reason,
                metadata={
                    "artifact_class": artifact_class,
                    "outcome": "denied",
                    "request_class": "download",
                },
            )
            await db.commit()
            raise ProblemDetail(status=status, code=code, title=title) from exc
        filename = "meeting-review.m4a"
        media_type = "audio/mp4"
        byte_length = playback.byte_length
        source_mode = "stored_review_m4a"
    elif artifact_class == "transcript":
        body = (await _transcript_text(db, meeting=meeting, result=result)).encode("utf-8")
        filename = "meeting-transcript.txt"
        media_type = "text/plain; charset=utf-8"
        byte_length = len(body)
        source_mode = None
    else:
        body = b"Summary artifact is not materialized in this MVP seed.\n"
        filename = "meeting-summary.txt"
        media_type = "text/plain; charset=utf-8"
        byte_length = len(body)
        source_mode = None

    download_metadata: dict[str, object] = {
        "artifact_class": artifact_class,
        "outcome": "prepared" if artifact_class == "audio" else "completed",
        "byte_length": byte_length,
        "source_mode": source_mode,
    }
    if artifact_class == "audio":
        download_metadata["stream_state"] = "prepared"

    await record_egress_audit_event(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="download_stream_prepared"
        if artifact_class == "audio"
        else "download_completed",
        outcome="prepared" if artifact_class == "audio" else "completed",
        artifact_class=artifact_class,
        policy_reason="policy_allowed",
        metadata=download_metadata,
    )
    return DownloadArtifact(
        filename=filename, media_type=media_type, body=body, byte_length=byte_length
    )


async def playback_artifact(
    db: AsyncSession,
    *,
    storage: object,
    meeting: Meeting,
    access: AccessDecision,
    actor_user_id: UUID,
    device_id: UUID,
    range_header: str | None = None,
) -> PlaybackArtifact:
    if meeting_deletion_active(meeting):
        await _record_playback_denied(
            db,
            meeting=meeting,
            actor_user_id=actor_user_id,
            device_id=device_id,
            reason="meeting_deletion_active",
        )
        raise ProblemDetail(
            status=409, code="meeting_deletion_active", title="Meeting deletion is in progress"
        )

    playback_state = await review_playback_state(db, meeting=meeting, access=access)
    if not playback_state.can_play:
        await _record_playback_denied(
            db,
            meeting=meeting,
            actor_user_id=actor_user_id,
            device_id=device_id,
            reason=playback_state.reason_code,
        )
        await db.commit()
        raise ProblemDetail(status=409, code="playback_unavailable", title="Playback unavailable")

    try:
        playback = await _stored_review_m4a_artifact(db, meeting=meeting)
        await _ensure_review_audio_storage_size(
            storage,
            object_key=playback.storage_object_key,
            expected_size=playback.byte_length,
        )
    except ReviewAudioBuildError as exc:
        reason = exc.reason if isinstance(exc, ReviewAudioBuildError) else "storage_unavailable"
        status = 503 if reason == "storage_unavailable" else 409
        code = "storage_unavailable" if status == 503 else "review_audio_unavailable"
        title = "Storage unavailable" if status == 503 else "Review audio unavailable"
        await _record_playback_denied(
            db,
            meeting=meeting,
            actor_user_id=actor_user_id,
            device_id=device_id,
            reason=reason,
        )
        await db.commit()
        raise ProblemDetail(status=status, code=code, title=title) from exc

    try:
        status_code, headers, offset, length = _playback_response_for_range(
            playback.byte_length,
            range_header,
            filename="meeting-review.m4a",
        )
    except ProblemDetail:
        await _record_playback_denied(
            db,
            meeting=meeting,
            actor_user_id=actor_user_id,
            device_id=device_id,
            reason="playback_range_not_satisfiable",
        )
        await db.commit()
        raise

    try:
        response_body = await _stream_storage_object(
            storage,
            playback.storage_object_key,
            offset=offset,
            length=length,
        )
    except (KeyError, ReviewAudioBuildError) as exc:
        reason = exc.reason if isinstance(exc, ReviewAudioBuildError) else "storage_unavailable"
        status = 503 if reason == "storage_unavailable" else 409
        code = "storage_unavailable" if status == 503 else "review_audio_unavailable"
        title = "Storage unavailable" if status == 503 else "Review audio unavailable"
        await _record_playback_denied(
            db,
            meeting=meeting,
            actor_user_id=actor_user_id,
            device_id=device_id,
            reason=reason,
        )
        await db.commit()
        raise ProblemDetail(status=status, code=code, title=title) from exc

    await record_egress_audit_event(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="playback_requested",
        outcome="allowed",
        artifact_class="audio",
        policy_reason="server_mediated_review_playback",
        metadata={
            "artifact_class": "audio",
            "viewer_access_state": access.state,
            "request_class": "playback",
            "source_mode": "stored_review_m4a",
        },
    )
    playback_metadata: dict[str, object] = {
        "artifact_class": "audio",
        "outcome": "prepared",
        "byte_length": length,
        "source_mode": "stored_review_m4a",
        "stream_state": "prepared",
    }
    if length > 0:
        playback_metadata["range_start"] = offset
        playback_metadata["range_end"] = offset + length - 1

    await record_egress_audit_event(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="playback_stream_prepared",
        outcome="prepared",
        artifact_class="audio",
        policy_reason="server_mediated_review_playback",
        metadata=playback_metadata,
    )
    return PlaybackArtifact(
        media_type="audio/mp4",
        body=response_body,
        status_code=status_code,
        headers=headers,
    )


async def _stored_review_m4a_artifact(
    db: AsyncSession,
    *,
    meeting: Meeting,
) -> TrackArtifact:
    artifacts = {
        artifact.track_role: artifact
        for artifact in await stored_audio_artifacts(
            db, workspace_id=meeting.workspace_id, meeting_id=meeting.id
        )
    }
    playback = artifacts.get(TrackRole.PLAYBACK.value)
    if playback is None or not _is_stored_review_m4a(playback):
        raise ReviewAudioBuildError("missing_playback_artifact")
    return playback


async def _stream_storage_object(
    storage: object,
    object_key: str,
    *,
    offset: int,
    length: int,
) -> Iterator[bytes]:
    iter_object = getattr(storage, "iter_object", None)
    if iter_object is None:
        raise ReviewAudioBuildError("storage_unavailable")
    try:
        return await to_thread.run_sync(
            lambda: iter_object(object_key, offset=offset, length=length)
        )
    except KeyError as exc:
        raise ReviewAudioBuildError("storage_unavailable") from exc
    except Exception as exc:
        raise ReviewAudioBuildError("storage_unavailable") from exc


def _playback_response_for_range(
    total_length: int,
    range_header: str | None,
    *,
    filename: str,
) -> tuple[int, dict[str, str], int, int]:
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{filename}"',
    }
    if not range_header:
        headers["Content-Length"] = str(total_length)
        return 200, headers, 0, total_length

    byte_range = _parse_playback_byte_range(range_header, total_length=total_length)
    length = byte_range.end - byte_range.start + 1
    headers["Content-Range"] = f"bytes {byte_range.start}-{byte_range.end}/{total_length}"
    headers["Content-Length"] = str(length)
    return 206, headers, byte_range.start, length


def _parse_playback_byte_range(range_header: str, *, total_length: int) -> PlaybackByteRange:
    if total_length <= 0 or not range_header.startswith("bytes="):
        raise ProblemDetail(
            status=416,
            code="playback_range_not_satisfiable",
            title="Playback range not satisfiable",
        )
    range_spec = range_header.removeprefix("bytes=").strip()
    if "," in range_spec or "-" not in range_spec:
        raise ProblemDetail(
            status=416,
            code="playback_range_not_satisfiable",
            title="Playback range not satisfiable",
        )
    start_text, end_text = range_spec.split("-", 1)
    try:
        if start_text == "":
            suffix_length = int(end_text)
            if suffix_length <= 0:
                raise ValueError
            start = max(total_length - suffix_length, 0)
            end = total_length - 1
        else:
            start = int(start_text)
            end = int(end_text) if end_text else total_length - 1
    except ValueError as exc:
        raise ProblemDetail(
            status=416,
            code="playback_range_not_satisfiable",
            title="Playback range not satisfiable",
        ) from exc
    if start < 0 or end < start or start >= total_length:
        raise ProblemDetail(
            status=416,
            code="playback_range_not_satisfiable",
            title="Playback range not satisfiable",
        )
    return PlaybackByteRange(start=start, end=min(end, total_length - 1))


async def _record_playback_denied(
    db: AsyncSession,
    *,
    meeting: Meeting,
    actor_user_id: UUID,
    device_id: UUID,
    reason: str | None,
) -> None:
    await record_egress_audit_event(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="playback_denied",
        outcome="denied",
        artifact_class="audio",
        policy_reason=reason or "playback_unavailable",
        metadata={"artifact_class": "audio", "outcome": "denied", "request_class": "playback"},
    )


async def create_export_package(
    db: AsyncSession,
    *,
    meeting: Meeting,
    access: AccessDecision,
    requested_artifacts: list[ArtifactClass],
    result: ProcessingResult | None,
    actor_user_id: UUID,
    device_id: UUID,
) -> ExportPackageResponse:
    if meeting_deletion_active(meeting):
        await record_egress_audit_event(
            db,
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            actor_user_id=actor_user_id,
            device_id=device_id,
            event_type="export_denied",
            artifact_class="package",
            outcome="denied",
            policy_reason="meeting_deletion_active",
            metadata={"artifact_class": "package", "outcome": "denied"},
        )
        raise ProblemDetail(
            status=409, code="meeting_deletion_active", title="Meeting deletion is in progress"
        )
    states = {
        state.artifact_class: state
        for state in await artifact_egress_states(db, meeting=meeting, access=access, result=result)
    }
    package_state = states.get("package")
    if package_state is None or package_state.state != "available":
        await record_egress_audit_event(
            db,
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            actor_user_id=actor_user_id,
            device_id=device_id,
            event_type="export_denied",
            artifact_class="package",
            outcome="denied",
            policy_reason=package_state.reason
            if package_state is not None
            else "package_export_unavailable",
            metadata={"artifact_class": "package", "outcome": "denied"},
        )
        await db.commit()
        raise ProblemDetail(status=409, code="export_unavailable", title="Export unavailable")
    requested = [artifact for artifact in requested_artifacts if artifact != "package"]
    included = [
        artifact
        for artifact in requested
        if states.get(artifact) is not None and states[artifact].state == "available"
    ]
    excluded = [
        ExportPackageExclusion(
            artifact_class=artifact,
            policy_reason=(
                states[artifact].reason
                if states.get(artifact) is not None
                else "unsupported_artifact"
            )
            or "unavailable",
        )
        for artifact in requested
        if artifact not in included
    ]
    if not included:
        await record_egress_audit_event(
            db,
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            actor_user_id=actor_user_id,
            device_id=device_id,
            event_type="export_denied",
            artifact_class="package",
            outcome="denied",
            policy_reason="no_allowed_artifacts",
            metadata={"artifact_class": "package", "outcome": "denied"},
        )
        await db.commit()
        raise ProblemDetail(status=409, code="export_unavailable", title="Export unavailable")

    manifest = _export_manifest(meeting, included=included, excluded=excluded)
    body = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")
    package = ExportPackage(
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        requested_by_user_id=actor_user_id,
        status="ready",
        included_artifacts=included,
        excluded_artifacts=[item.model_dump(mode="json") for item in excluded],
        manifest_json=manifest,
        byte_length=len(body),
        ready_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    await record_egress_audit_event(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="export_requested",
        artifact_class="package",
        outcome="allowed",
        policy_reason="policy_filtered_package",
        metadata={"artifact_class": "package", "request_class": "export"},
    )
    db.add(package)
    await db.flush()
    await record_egress_audit_event(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="export_completed",
        artifact_class="package",
        outcome="completed",
        policy_reason="policy_filtered_package",
        metadata={
            "artifact_class": "package",
            "export_id": str(package.id),
            "byte_length": len(body),
        },
    )
    return ExportPackageResponse(
        export_id=package.id,
        status="ready",
        included_artifacts=included,
        excluded_artifacts=excluded,
    )


async def export_package_bytes(
    db: AsyncSession,
    *,
    meeting: Meeting,
    access: AccessDecision,
    export_id: UUID,
    actor_user_id: UUID,
    device_id: UUID,
) -> DownloadArtifact:
    if meeting_deletion_active(meeting):
        await record_egress_audit_event(
            db,
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            actor_user_id=actor_user_id,
            device_id=device_id,
            event_type="export_denied",
            artifact_class="package",
            outcome="denied",
            policy_reason="meeting_deletion_active",
            metadata={"artifact_class": "package", "outcome": "denied"},
        )
        raise ProblemDetail(
            status=409, code="meeting_deletion_active", title="Meeting deletion is in progress"
        )
    if not access.can_export:
        raise ProblemDetail(status=403, code="export_forbidden", title="Export is not available")
    package = await db.scalar(
        select(ExportPackage).where(
            ExportPackage.workspace_id == meeting.workspace_id,
            ExportPackage.meeting_id == meeting.id,
            ExportPackage.id == export_id,
            ExportPackage.status == "ready",
        )
    )
    if package is None:
        raise ProblemDetail(status=404, code="export_not_found", title="Export not found")
    body = json.dumps(package.manifest_json, ensure_ascii=False, sort_keys=True).encode("utf-8")
    await record_egress_audit_event(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="export_completed",
        artifact_class="package",
        outcome="completed",
        policy_reason="ready_package_downloaded",
        metadata={
            "artifact_class": "package",
            "export_id": str(package.id),
            "byte_length": len(body),
        },
    )
    return DownloadArtifact(
        filename="meeting-export.json",
        media_type="application/json",
        body=body,
        byte_length=len(body),
    )


async def activity_response(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    viewer_user_id: UUID,
) -> MeetingActivityResponse:
    events = (
        await db.scalars(
            select(MeetingEgressAuditEvent)
            .where(
                MeetingEgressAuditEvent.workspace_id == workspace_id,
                MeetingEgressAuditEvent.meeting_id == meeting_id,
            )
            .order_by(MeetingEgressAuditEvent.created_at.desc())
            .limit(50)
        )
    ).all()
    items = [
        MeetingActivityItem(
            event_id=event.id,
            event_type=event.event_type,
            actor_label="You" if event.actor_user_id == viewer_user_id else "User",
            artifact_class=event.artifact_class,  # type: ignore[arg-type]
            outcome=event.outcome,  # type: ignore[arg-type]
            reason=event.policy_reason,
            created_at=event.created_at,
        )
        for event in events
    ]
    return MeetingActivityResponse(
        meeting_id=meeting_id, redaction_state="metadata_only", items=items
    )


def meeting_deletion_active(meeting: Meeting) -> bool:
    return (meeting.deletion_state or DeletionState.NONE.value) != DeletionState.NONE.value


def _deleted_artifact_states() -> list[ArtifactEgressState]:
    return [
        ArtifactEgressState(
            artifact_class=artifact_class,
            state="deleted",
            label="Deleted",
            reason="Meeting deletion is in progress. Use the deletion report for lifecycle truth.",
            action="disabled",
        )
        for artifact_class in ("audio", "transcript", "summary", "package")
    ]


def _audio_state(
    policy_value: str, access: AccessDecision, artifacts: list[TrackArtifact]
) -> ArtifactEgressState:
    blocked = _policy_blocked_state("audio", policy_value, access)
    if blocked is not None:
        return blocked
    playback = next(
        (
            artifact
            for artifact in artifacts
            if artifact.track_role == TrackRole.PLAYBACK.value and _is_stored_review_m4a(artifact)
        ),
        None,
    )
    if playback is None:
        return ArtifactEgressState(
            artifact_class="audio",
            state="missing",
            label="Audio unavailable",
            reason="missing_playback_artifact",
            action="disabled",
        )
    return ArtifactEgressState(
        artifact_class="audio",
        state="available",
        label="Download audio",
        reason="Server-mediated download; no storage URL is exposed.",
        action="download",
    )


def _transcript_state(
    policy_value: str, access: AccessDecision, result: ProcessingResult | None
) -> ArtifactEgressState:
    blocked = _policy_blocked_state("transcript", policy_value, access)
    if blocked is not None:
        return blocked
    if result is None:
        return ArtifactEgressState(
            artifact_class="transcript",
            state="missing",
            label="Transcript unavailable",
            reason="No transcript result is available.",
            action="disabled",
        )
    if result.status != ProcessingResultStatus.IMPORTED.value:
        return ArtifactEgressState(
            artifact_class="transcript",
            state="processing",
            label="Transcript processing",
            reason="Transcript is still being processed.",
            action="disabled",
        )
    if (
        result.transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.segment_count > 0
    ):
        return ArtifactEgressState(
            artifact_class="transcript",
            state="available",
            label="Download transcript",
            reason="Transcript is available through server-mediated egress.",
            action="download",
        )
    return ArtifactEgressState(
        artifact_class="transcript",
        state="missing",
        label="Transcript unavailable",
        reason="Transcript content is not available.",
        action="disabled",
    )


def _summary_state(
    policy_value: str, access: AccessDecision, result: ProcessingResult | None
) -> ArtifactEgressState:
    blocked = _policy_blocked_state("summary", policy_value, access)
    if blocked is not None:
        return blocked
    if (
        result is not None
        and result.summary_status == SummaryStatus.AVAILABLE.value
        and result.transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.segment_count > 0
    ):
        return ArtifactEgressState(
            artifact_class="summary",
            state="available",
            label="Download summary",
            reason="Summary policy allows server-mediated egress.",
            action="download",
        )
    return ArtifactEgressState(
        artifact_class="summary",
        state="missing",
        label="Summary unavailable",
        reason="Summary notes are not available yet.",
        action="disabled",
    )


def _package_state(
    policy_value: str,
    access: AccessDecision,
    artifact_states: list[ArtifactEgressState],
) -> ArtifactEgressState:
    blocked = _policy_blocked_state("package", policy_value, access)
    if blocked is not None:
        return blocked
    if any(state.state == "available" for state in artifact_states):
        return ArtifactEgressState(
            artifact_class="package",
            state="available",
            label="Export package",
            reason="Package will include only currently allowed artifacts.",
            action="export",
        )
    return ArtifactEgressState(
        artifact_class="package",
        state="missing",
        label="Export unavailable",
        reason="No exportable artifact is currently available.",
        action="disabled",
    )


def _policy_blocked_state(
    artifact_class: ArtifactClass,
    policy_value: str,
    access: AccessDecision,
) -> ArtifactEgressState | None:
    if not access.can_view:
        return ArtifactEgressState(
            artifact_class=artifact_class,
            state="policy_blocked",
            label="Access required",
            reason="Viewer cannot access this meeting.",
            action="disabled",
        )
    if policy_value == "disabled":
        return ArtifactEgressState(
            artifact_class=artifact_class,
            state="policy_blocked",
            label="Disabled by policy",
            reason="Workspace policy disables this artifact egress.",
            action="disabled",
        )
    if policy_value == "owner_only" and access.state != "owner":
        return ArtifactEgressState(
            artifact_class=artifact_class,
            state="owner_only",
            label="Owner only",
            reason="Only the meeting owner can use this artifact action.",
            action="disabled",
        )
    if policy_value not in {"allowed", "owner_only"}:
        return ArtifactEgressState(
            artifact_class=artifact_class,
            state="policy_blocked",
            label="Disabled by policy",
            reason="No accepted egress policy is available.",
            action="disabled",
        )
    return None


async def _transcript_text(
    db: AsyncSession,
    *,
    meeting: Meeting,
    result: ProcessingResult | None,
) -> str:
    if result is None:
        return ""
    segments = (
        await db.scalars(
            select(TranscriptSegment)
            .where(
                TranscriptSegment.workspace_id == meeting.workspace_id,
                TranscriptSegment.meeting_id == meeting.id,
                TranscriptSegment.processing_result_id == result.id,
            )
            .order_by(TranscriptSegment.sequence.asc(), TranscriptSegment.start_seconds.asc())
        )
    ).all()
    lines: list[str] = []
    for segment in segments:
        start = _format_decimal_timestamp(segment.start_seconds)
        lines.append(f"[{start}] {segment.text}")
    return "\n".join(lines) + ("\n" if lines else "")


def _format_decimal_timestamp(value: Decimal) -> str:
    return format_timestamp(value)


def _export_manifest(
    meeting: Meeting,
    *,
    included: list[ArtifactClass],
    excluded: list[ExportPackageExclusion],
) -> dict[str, object]:
    return {
        "meeting_id": str(meeting.id),
        "title": meeting.title or "Untitled meeting",
        "generated_at": datetime.now(UTC).isoformat(),
        "included_artifacts": included,
        "excluded_artifacts": [item.model_dump(mode="json") for item in excluded],
        "deletion_truth": DELETION_TRUTH_COPY,
    }
