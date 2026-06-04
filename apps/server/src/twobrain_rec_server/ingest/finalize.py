from datetime import UTC, datetime
from typing import NoReturn
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.domain.statuses import (
    MeetingStatus,
    ProcessingStatus,
    TrackRole,
    UploadSessionStatus,
)
from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.lifecycle_guards import ensure_upload_session_mutable
from twobrain_rec_server.ingest.manifest import ManifestValidationError, validate_required_tracks
from twobrain_rec_server.ingest.parts import get_session_for_tenant
from twobrain_rec_server.ingest.store import (
    MeetingRecord,
    UploadSessionRecord,
    persist_audit_event,
    persist_finalized_tracks,
    persist_meeting,
    persist_upload_session,
)


async def _persist_degraded_finalize_failure(
    *,
    db: AsyncSession | None,
    tenant_scope: TenantScope,
    meeting: MeetingRecord,
    session: UploadSessionRecord,
    code: str,
    title: str,
) -> None:
    meeting.status = MeetingStatus.DEGRADED
    session.status = UploadSessionStatus.DEGRADED
    event = record_audit_event(
        event_type="finalize_degraded",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        metadata={"reason_code": code, "reason": title},
    )
    await persist_meeting(db, meeting)
    await persist_upload_session(db, session)
    await persist_audit_event(db, event)


async def _raise_degraded_finalize_problem(
    *,
    db: AsyncSession | None,
    tenant_scope: TenantScope,
    meeting: MeetingRecord,
    session: UploadSessionRecord,
    status: int,
    code: str,
    title: str,
    cause: Exception | None = None,
) -> NoReturn:
    await _persist_degraded_finalize_failure(
        db=db,
        tenant_scope=tenant_scope,
        meeting=meeting,
        session=session,
        code=code,
        title=title,
    )
    problem = ProblemDetail(status=status, code=code, title=title)
    if cause is not None:
        raise problem from cause
    raise problem


async def finalize_upload(
    *,
    tenant_scope: TenantScope,
    db: AsyncSession | None = None,
    session_id: UUID,
    manifest_sha256: str,
    tracks: list[TrackDescriptor],
) -> tuple[object, object]:
    session = await get_session_for_tenant(session_id, tenant_scope, db)
    await ensure_upload_session_mutable(db=db, session=session, event_type="expired")
    meeting = store_module.store.meetings[session.meeting_id]
    try:
        validate_required_tracks(tracks)
    except ManifestValidationError as exc:
        await _raise_degraded_finalize_problem(
            db=db,
            tenant_scope=tenant_scope,
            meeting=meeting,
            session=session,
            status=400,
            code="manifest_validation_failed",
            title=str(exc),
            cause=exc,
        )

    tracks_by_role = {track.track_role: track for track in tracks}
    if len(tracks_by_role) != len(tracks):
        await _raise_degraded_finalize_problem(
            db=db,
            tenant_scope=tenant_scope,
            meeting=meeting,
            session=session,
            status=400,
            code="duplicate_track_role",
            title="Duplicate track role in finalize manifest",
        )
    manifest_track = tracks_by_role.get(TrackRole.MANIFEST)
    if manifest_track is None or manifest_track.sha256 != manifest_sha256:
        await _raise_degraded_finalize_problem(
            db=db,
            tenant_scope=tenant_scope,
            meeting=meeting,
            session=session,
            status=400,
            code="manifest_checksum_mismatch",
            title="Manifest checksum mismatch",
        )

    uploaded_roles = {role for role, _part_number in session.parts}
    expected_roles = {track.track_role for track in tracks}
    configured_roles = set(session.expected_track_roles)
    if expected_roles != configured_roles:
        await _raise_degraded_finalize_problem(
            db=db,
            tenant_scope=tenant_scope,
            meeting=meeting,
            session=session,
            status=409,
            code="expected_track_role_mismatch",
            title="Finalize track roles do not match expected track roles",
        )
    if not expected_roles.issubset(uploaded_roles):
        await _raise_degraded_finalize_problem(
            db=db,
            tenant_scope=tenant_scope,
            meeting=meeting,
            session=session,
            status=409,
            code="missing_required_parts",
            title="Missing required upload parts",
        )

    for role, track in tracks_by_role.items():
        role_parts = [part for (part_role, _part_number), part in session.parts.items() if part_role == role]
        if len(role_parts) != 1:
            await _raise_degraded_finalize_problem(
                db=db,
                tenant_scope=tenant_scope,
                meeting=meeting,
                session=session,
                status=409,
                code="ambiguous_track_parts",
                title="Expected one uploaded part per track role",
            )
        part = role_parts[0]
        expected_size = session.expected_track_sizes.get(role)
        if expected_size is not None and expected_size != track.byte_length:
            await _raise_degraded_finalize_problem(
                db=db,
                tenant_scope=tenant_scope,
                meeting=meeting,
                session=session,
                status=409,
                code="expected_track_size_mismatch",
                title="Expected track size mismatch",
            )
        if part.byte_length != track.byte_length:
            await _raise_degraded_finalize_problem(
                db=db,
                tenant_scope=tenant_scope,
                meeting=meeting,
                session=session,
                status=400,
                code="track_length_mismatch",
                title="Track byte length mismatch",
            )
        if part.sha256 != track.sha256:
            await _raise_degraded_finalize_problem(
                db=db,
                tenant_scope=tenant_scope,
                meeting=meeting,
                session=session,
                status=400,
                code="track_checksum_mismatch",
                title="Track checksum mismatch",
            )

    meeting.status = MeetingStatus.INGESTED_PENDING_PROCESSING
    meeting.processing_status = ProcessingStatus.NOT_SUBMITTED
    session.status = UploadSessionStatus.FINALIZED
    session.processing_status = ProcessingStatus.NOT_SUBMITTED
    session.finalized_at = datetime.now(UTC)
    event = record_audit_event(
        event_type="finalized",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        metadata={"object_count": len(session.parts)},
    )
    await persist_meeting(db, meeting)
    await persist_upload_session(db, session)
    await persist_finalized_tracks(db, meeting, session, tracks, manifest_sha256)
    await persist_audit_event(db, event)
    return meeting, session
