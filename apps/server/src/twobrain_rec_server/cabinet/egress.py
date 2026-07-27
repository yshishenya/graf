from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

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
)
from twobrain_rec_server.cabinet.access import AccessDecision
from twobrain_rec_server.cabinet.constants import DELETION_TRUTH_COPY
from twobrain_rec_server.cabinet.playback_audio import (
    ReviewAudio,
    ReviewAudioBuildError,
    build_combined_review_wav,
)
from twobrain_rec_server.cabinet.view_models import format_timestamp
from twobrain_rec_server.db.models import (
    ExportPackage,
    Meeting,
    MeetingArtifactPolicy,
    MeetingEgressAuditEvent,
    ProcessingResult,
    TrackArtifact,
    TranscriptSegment,
)
from twobrain_rec_server.domain.statuses import (
    DeletionState,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
    SummaryStatus,
    TrackRole,
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
}


@dataclass(frozen=True, slots=True)
class DownloadArtifact:
    filename: str
    media_type: str
    body: bytes


@dataclass(frozen=True, slots=True)
class PlaybackArtifact:
    media_type: str
    body: bytes
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PlaybackByteRange:
    start: int
    end: int


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
    policy = await resolve_artifact_policy(db, workspace_id=meeting.workspace_id, meeting_id=meeting.id)
    audio_artifacts = await stored_audio_artifacts(db, workspace_id=meeting.workspace_id, meeting_id=meeting.id)
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
        audio_download="owner_only",
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
    return (
        await db.scalars(
            select(TrackArtifact)
            .where(
                TrackArtifact.workspace_id == workspace_id,
                TrackArtifact.meeting_id == meeting_id,
                TrackArtifact.track_role.in_(
                    [TrackRole.PLAYBACK.value, TrackRole.SYSTEM.value, TrackRole.MICROPHONE.value]
                ),
                TrackArtifact.status == "stored",
            )
            .order_by(TrackArtifact.track_role.desc())
        )
    ).all()


def _is_stored_review_m4a(artifact: TrackArtifact) -> bool:
    return (
        artifact.codec == "m4a-aac-lc"
        and artifact.sample_rate_hz == 48_000
        and artifact.channel_count == 1
        and artifact.byte_length > 0
    )


async def review_playback_state(
    db: AsyncSession,
    *,
    meeting: Meeting,
    access: AccessDecision,
    result: ProcessingResult | None,
) -> ArtifactEgressState:
    if meeting_deletion_active(meeting):
        return ArtifactEgressState(
            artifact_class="audio",
            state="deleted",
            label="Review audio deleting",
            reason="meeting_deletion_active",
            action="disabled",
        )
    if not access.can_view:
        return ArtifactEgressState(
            artifact_class="audio",
            state="policy_blocked",
            label="Access required",
            reason="Viewer cannot access this meeting.",
            action="disabled",
        )
    if result is None or result.status != ProcessingResultStatus.IMPORTED.value:
        reason = _playback_result_unavailable_reason(meeting, result)
        state = "failed" if reason in {"processing_failed", "review_result_not_imported"} else "processing"
        return ArtifactEgressState(
            artifact_class="audio",
            state=state,
            label="Review audio unavailable",
            reason=reason,
            action="disabled",
        )

    artifacts = {
        artifact.track_role: artifact
        for artifact in await stored_audio_artifacts(db, workspace_id=meeting.workspace_id, meeting_id=meeting.id)
    }
    playback = artifacts.get(TrackRole.PLAYBACK.value)
    if playback is not None and _is_stored_review_m4a(playback):
        return ArtifactEgressState(
            artifact_class="audio",
            state="available",
            label="Review playback",
            reason="stored_review_m4a",
            action="disabled",
        )
    if TrackRole.MICROPHONE.value not in artifacts or TrackRole.SYSTEM.value not in artifacts:
        return ArtifactEgressState(
            artifact_class="audio",
            state="missing",
            label="Review audio unavailable",
            reason="missing_audio_source",
            action="disabled",
        )
    return ArtifactEgressState(
        artifact_class="audio",
        state="available",
        label="Review playback",
        reason="combined_review_stream",
        action="disabled",
    )


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
        raise ProblemDetail(status=409, code="meeting_deletion_active", title="Meeting deletion is in progress")
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
        metadata={"artifact_class": artifact_class, "viewer_access_state": access.state, "request_class": "download"},
    )
    if artifact_class == "audio":
        try:
            review_audio = await _load_review_audio(db, storage=storage, meeting=meeting)
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
                metadata={"artifact_class": artifact_class, "outcome": "denied", "request_class": "download"},
            )
            await db.commit()
            raise ProblemDetail(status=status, code=code, title=title) from exc
        body = review_audio.body
        filename = _review_audio_filename(review_audio)
        media_type = review_audio.media_type
    elif artifact_class == "transcript":
        body = (await _transcript_text(db, meeting=meeting, result=result)).encode("utf-8")
        filename = "meeting-transcript.txt"
        media_type = "text/plain; charset=utf-8"
    else:
        body = b"Summary artifact is not materialized in this MVP seed.\n"
        filename = "meeting-summary.txt"
        media_type = "text/plain; charset=utf-8"

    await record_egress_audit_event(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="download_completed",
        outcome="completed",
        artifact_class=artifact_class,
        policy_reason="policy_allowed",
        metadata={
            "artifact_class": artifact_class,
            "outcome": "completed",
            "byte_length": len(body),
            "source_mode": review_audio.source_mode if artifact_class == "audio" else None,
        },
    )
    return DownloadArtifact(filename=filename, media_type=media_type, body=body)


async def playback_artifact(
    db: AsyncSession,
    *,
    storage: object,
    meeting: Meeting,
    access: AccessDecision,
    result: ProcessingResult | None,
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
        raise ProblemDetail(status=409, code="meeting_deletion_active", title="Meeting deletion is in progress")

    playback_state = await review_playback_state(db, meeting=meeting, access=access, result=result)
    if playback_state.state != "available":
        await _record_playback_denied(
            db,
            meeting=meeting,
            actor_user_id=actor_user_id,
            device_id=device_id,
            reason=playback_state.reason,
        )
        await db.commit()
        raise ProblemDetail(status=409, code="playback_unavailable", title="Playback unavailable")

    try:
        review_audio = await _load_review_audio(db, storage=storage, meeting=meeting)
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

    try:
        response_body, status_code, headers = _playback_response_for_range(
            review_audio.body,
            range_header,
            filename=_review_audio_filename(review_audio),
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
            "source_mode": review_audio.source_mode,
        },
    )
    await record_egress_audit_event(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type="playback_completed",
        outcome="completed",
        artifact_class="audio",
        policy_reason="server_mediated_review_playback",
        metadata={
            "artifact_class": "audio",
            "outcome": "completed",
            "byte_length": len(response_body),
            "source_mode": review_audio.source_mode,
        },
    )
    return PlaybackArtifact(
        media_type=review_audio.media_type,
        body=response_body,
        status_code=status_code,
        headers=headers,
    )


async def _load_review_audio(
    db: AsyncSession,
    *,
    storage: object,
    meeting: Meeting,
) -> ReviewAudio:
    get_bytes_async = getattr(storage, "get_bytes_async", None)
    get_bytes = getattr(storage, "get_bytes", None)
    if get_bytes_async is None and get_bytes is None:
        raise ReviewAudioBuildError("storage_unavailable")

    async def read_object(object_key: str) -> bytes:
        try:
            if get_bytes_async is not None:
                return await get_bytes_async(object_key)
            return get_bytes(object_key)
        except KeyError:
            raise
        except Exception as exc:
            raise ReviewAudioBuildError("storage_unavailable") from exc

    artifacts = {
        artifact.track_role: artifact
        for artifact in await stored_audio_artifacts(db, workspace_id=meeting.workspace_id, meeting_id=meeting.id)
    }
    playback = artifacts.get(TrackRole.PLAYBACK.value)
    if playback is not None and _is_stored_review_m4a(playback):
        try:
            body = await read_object(playback.storage_object_key)
            return ReviewAudio(
                body=body,
                media_type="audio/mp4",
                duration_seconds=playback.duration_seconds,
                source_mode="stored_review_m4a",
                included_sources=["local_microphone", "incoming_system"],
            )
        except KeyError:
            pass

    mic = artifacts.get(TrackRole.MICROPHONE.value)
    incoming = artifacts.get(TrackRole.SYSTEM.value)
    if mic is None or incoming is None:
        raise ReviewAudioBuildError("missing_audio_source")

    try:
        mic_body = await read_object(mic.storage_object_key)
        incoming_body = await read_object(incoming.storage_object_key)
    except KeyError as exc:
        raise ReviewAudioBuildError("missing_audio_source") from exc
    return build_combined_review_wav(
        [
            ("local_microphone", mic_body),
            ("incoming_system", incoming_body),
        ]
    )


def _review_audio_filename(review_audio: ReviewAudio) -> str:
    if review_audio.media_type == "audio/mp4":
        return "meeting-review.m4a"
    return "meeting-review.wav"


def _playback_response_for_range(
    body: bytes,
    range_header: str | None,
    *,
    filename: str,
) -> tuple[bytes, int, dict[str, str]]:
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{filename}"',
    }
    if not range_header:
        headers["Content-Length"] = str(len(body))
        return body, 200, headers

    byte_range = _parse_playback_byte_range(range_header, total_length=len(body))
    partial = body[byte_range.start : byte_range.end + 1]
    headers["Content-Range"] = f"bytes {byte_range.start}-{byte_range.end}/{len(body)}"
    headers["Content-Length"] = str(len(partial))
    return partial, 206, headers


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


def _playback_result_unavailable_reason(meeting: Meeting, result: ProcessingResult | None) -> str:
    if result is not None:
        return "review_result_not_imported"
    if meeting.processing_status in {ProcessingStatus.FAILED_TERMINAL.value, ProcessingStatus.FAILED_RETRYABLE.value}:
        return "processing_failed"
    if meeting.processing_status in {
        ProcessingStatus.PENDING_PROCESSING.value,
        ProcessingStatus.STARTING.value,
        ProcessingStatus.WORKFLOW_STARTED.value,
        ProcessingStatus.SUBMITTING.value,
        ProcessingStatus.SUBMITTED.value,
        ProcessingStatus.POLLING.value,
        ProcessingStatus.IMPORTING.value,
    }:
        return "processing_not_ready"
    return "review_result_unavailable"


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
        raise ProblemDetail(status=409, code="meeting_deletion_active", title="Meeting deletion is in progress")
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
            policy_reason=package_state.reason if package_state is not None else "package_export_unavailable",
            metadata={"artifact_class": "package", "outcome": "denied"},
        )
        await db.commit()
        raise ProblemDetail(status=409, code="export_unavailable", title="Export unavailable")
    requested = [artifact for artifact in requested_artifacts if artifact != "package"]
    included = [artifact for artifact in requested if states.get(artifact) is not None and states[artifact].state == "available"]
    excluded = [
        ExportPackageExclusion(
            artifact_class=artifact,
            policy_reason=(states[artifact].reason if states.get(artifact) is not None else "unsupported_artifact")
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
        metadata={"artifact_class": "package", "export_id": str(package.id), "byte_length": len(body)},
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
        raise ProblemDetail(status=409, code="meeting_deletion_active", title="Meeting deletion is in progress")
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
        metadata={"artifact_class": "package", "export_id": str(package.id), "byte_length": len(body)},
    )
    return DownloadArtifact(filename="meeting-export.json", media_type="application/json", body=body)


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
    return MeetingActivityResponse(meeting_id=meeting_id, redaction_state="metadata_only", items=items)


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


def _audio_state(policy_value: str, access: AccessDecision, artifacts: list[TrackArtifact]) -> ArtifactEgressState:
    blocked = _policy_blocked_state("audio", policy_value, access)
    if blocked is not None:
        return blocked
    if not artifacts:
        return ArtifactEgressState(
            artifact_class="audio",
            state="missing",
            label="Audio unavailable",
            reason="No stored audio artifact is available.",
            action="disabled",
        )
    return ArtifactEgressState(
        artifact_class="audio",
        state="available",
        label="Download audio",
        reason="Server-mediated download; no storage URL is exposed.",
        action="download",
    )


def _transcript_state(policy_value: str, access: AccessDecision, result: ProcessingResult | None) -> ArtifactEgressState:
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


def _summary_state(policy_value: str, access: AccessDecision, result: ProcessingResult | None) -> ArtifactEgressState:
    blocked = _policy_blocked_state("summary", policy_value, access)
    if blocked is not None:
        return blocked
    if result is not None and result.summary_status == SummaryStatus.AVAILABLE.value:
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
