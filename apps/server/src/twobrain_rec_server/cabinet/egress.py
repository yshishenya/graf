from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
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
}


@dataclass(frozen=True, slots=True)
class DownloadArtifact:
    filename: str
    media_type: str
    body: bytes


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
    return (
        await db.scalars(
            select(TrackArtifact)
            .where(
                TrackArtifact.workspace_id == workspace_id,
                TrackArtifact.meeting_id == meeting_id,
                TrackArtifact.track_role.in_([TrackRole.SYSTEM.value, TrackRole.MICROPHONE.value]),
                TrackArtifact.status == "stored",
            )
            .order_by(TrackArtifact.track_role.desc())
        )
    ).all()


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
        artifact = (await stored_audio_artifacts(db, workspace_id=meeting.workspace_id, meeting_id=meeting.id))[0]
        get_bytes = getattr(storage, "get_bytes", None)
        if get_bytes is None:
            raise ProblemDetail(status=503, code="storage_unavailable", title="Storage unavailable")
        body = get_bytes(artifact.storage_object_key)
        filename = "meeting-audio.bin"
        media_type = "application/octet-stream"
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
        metadata={"artifact_class": artifact_class, "outcome": "completed", "byte_length": len(body)},
    )
    return DownloadArtifact(filename=filename, media_type=media_type, body=body)


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
    blocked = _policy_blocked_state("audio", policy_value, access, action="download")
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
    blocked = _policy_blocked_state("transcript", policy_value, access, action="download")
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
    blocked = _policy_blocked_state("summary", policy_value, access, action="download")
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
    blocked = _policy_blocked_state("package", policy_value, access, action="export")
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
    *,
    action: str,
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
