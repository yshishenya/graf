from hashlib import sha256
from io import BytesIO
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.upload_stream import BoundedUploadBody
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import TrackRole, UploadSessionStatus
from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.lifecycle_guards import ensure_upload_session_mutable
from twobrain_rec_server.ingest.policy import IngestLimitViolation, validate_track_bytes
from twobrain_rec_server.ingest.state_machine import ensure_can_accept_part
from twobrain_rec_server.ingest.store import (
    UploadPartRecord,
    UploadSessionRecord,
    load_upload_session_record,
    mark_temporary_upload_object_cleanup_status,
    persist_audit_event,
    persist_temporary_upload_object,
    persist_upload_part,
    persist_upload_session,
)
from twobrain_rec_server.storage.object_keys import build_track_object_key


async def get_session_for_tenant(
    session_id: UUID,
    tenant_scope: TenantScope,
    db: AsyncSession | None = None,
) -> UploadSessionRecord:
    session = await load_upload_session_record(db, session_id)
    if session is None:
        session = store_module.store.sessions.get(session_id)
    if session is None or session.workspace_id != tenant_scope.workspace_id:
        raise ProblemDetail(status=404, code="upload_session_not_found", title="Upload session not found")
    if session.device_id != tenant_scope.device_id:
        raise ProblemDetail(status=403, code="device_scope_denied", title="Device scope denied")
    return session


async def accept_part(
    *,
    settings: Settings,
    tenant_scope: TenantScope,
    db: AsyncSession | None = None,
    storage: object | None = None,
    session_id: UUID,
    track_role: TrackRole,
    part_number: int,
    byte_offset: int,
    content_sha256: str,
    data: BoundedUploadBody | bytes,
) -> UploadPartRecord:
    if isinstance(data, bytes):
        actual_sha = sha256(data).hexdigest()
        byte_length = len(data)
        stream = None
    else:
        actual_sha = data.sha256
        byte_length = data.byte_length
        stream = data.stream

    def close_upload_stream() -> None:
        if stream is not None:
            stream.close()

    if part_number < 0:
        close_upload_stream()
        raise ProblemDetail(status=400, code="invalid_part_number", title="Part number must be non-negative")
    if byte_offset < 0:
        close_upload_stream()
        raise ProblemDetail(status=400, code="invalid_byte_offset", title="Byte offset must be non-negative")
    try:
        session = await get_session_for_tenant(session_id, tenant_scope, db)
        await ensure_upload_session_mutable(db=db, session=session, event_type="expired")
    except Exception:
        close_upload_stream()
        raise
    try:
        ensure_can_accept_part(session.status)
    except ValueError as exc:
        close_upload_stream()
        raise ProblemDetail(status=409, code="session_terminal", title="Upload session is terminal") from exc

    try:
        if byte_length > settings.max_upload_part_bytes:
            close_upload_stream()
            raise ProblemDetail(status=413, code="upload_part_bytes_exceeded", title="Upload part byte limit exceeded")
        validate_track_bytes(settings, byte_length)
    except IngestLimitViolation as exc:
        close_upload_stream()
        raise ProblemDetail(
            status=413,
            code=exc.code,
            title="Track byte limit exceeded",
            detail=f"{exc.limit_name}={exc.limit_value}, actual={exc.actual_value}",
        ) from exc
    if actual_sha != content_sha256:
        close_upload_stream()
        raise ProblemDetail(status=400, code="checksum_mismatch", title="Checksum mismatch")

    part_key = (track_role, part_number)
    existing = session.parts.get(part_key)
    if existing:
        if existing.sha256 == content_sha256 and existing.byte_length == byte_length and existing.byte_offset == byte_offset:
            close_upload_stream()
            return existing
        conflict_code = "checksum_conflict" if existing.byte_offset == byte_offset else "range_conflict"
        conflict_title = "Checksum conflict" if conflict_code == "checksum_conflict" else "Upload part replay conflicts with accepted range"
        event = record_audit_event(
            event_type="part_conflict",
            workspace_id=tenant_scope.workspace_id,
            meeting_id=session.meeting_id,
            upload_session_id=session.id,
            actor_user_id=tenant_scope.user_id,
            device_id=tenant_scope.device_id,
            metadata={"track_role": track_role.value, "part_number": part_number},
        )
        await persist_audit_event(db, event)
        close_upload_stream()
        raise ProblemDetail(status=409, code=conflict_code, title=conflict_title)

    new_start = byte_offset
    new_end = byte_offset + byte_length
    expected_size = session.expected_track_sizes.get(track_role)
    if expected_size is not None and new_end > expected_size:
        close_upload_stream()
        raise ProblemDetail(status=409, code="expected_track_size_exceeded", title="Upload part exceeds expected track size")
    accepted_track_bytes = 0
    accepted_package_bytes = 0
    for (part_role, _), accepted_part in session.parts.items():
        accepted_package_bytes += accepted_part.byte_length
        if part_role == track_role:
            accepted_track_bytes += accepted_part.byte_length
            accepted_start = accepted_part.byte_offset
            accepted_end = accepted_part.byte_offset + accepted_part.byte_length
            if new_start < accepted_end and new_end > accepted_start:
                close_upload_stream()
                raise ProblemDetail(status=409, code="range_overlap", title="Upload part overlaps an accepted range")
    if accepted_track_bytes + byte_length > settings.max_track_bytes:
        close_upload_stream()
        raise ProblemDetail(status=413, code="track_bytes_exceeded", title="Track byte limit exceeded")
    if accepted_package_bytes + byte_length > settings.max_package_bytes:
        close_upload_stream()
        raise ProblemDetail(status=413, code="package_bytes_exceeded", title="Package byte limit exceeded")

    meeting = store_module.store.meetings[session.meeting_id]
    object_key = build_track_object_key(
        organization_id=tenant_scope.organization_id,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        track_role=track_role,
        part_number=part_number,
    )
    if storage is not None:
        try:
            ensure_bucket_async = getattr(storage, "ensure_bucket_async", None)
            if ensure_bucket_async is not None:
                await ensure_bucket_async()
            elif hasattr(storage, "ensure_bucket"):
                storage.ensure_bucket()
            put_stream_async = getattr(storage, "put_stream_async", None)
            upload_stream = stream
            if upload_stream is None:
                upload_stream = BytesIO(data)
            upload_stream.seek(0)
            if put_stream_async is not None:
                await put_stream_async(object_key, upload_stream, byte_length)
            else:
                storage.put_stream(object_key, upload_stream, byte_length)
        except Exception as exc:
            close_upload_stream()
            raise ProblemDetail(status=503, code="storage_unavailable", title="Storage unavailable") from exc
    part = UploadPartRecord(
        track_role=track_role,
        part_number=part_number,
        byte_offset=byte_offset,
        byte_length=byte_length,
        sha256=content_sha256,
        object_key=object_key,
        data=b"",
    )
    session.parts[part_key] = part
    session.status = UploadSessionStatus.UPLOADING
    await persist_temporary_upload_object(db, session, part, object_role="accepted_part", commit=False)
    event = record_audit_event(
        event_type="part_accepted",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        metadata={"track_role": track_role.value, "part_number": part_number, "byte_length": byte_length},
    )
    try:
        await persist_upload_session(db, session, settings, commit=False)
        await persist_upload_part(db, session, part, commit=False)
    except Exception as exc:
        await mark_temporary_upload_object_cleanup_status(
            db,
            session,
            object_key,
            "orphaned",
            failure_reason="db_persistence_failed_after_object_write",
            last_error=type(exc).__name__,
        )
        close_upload_stream()
        raise ProblemDetail(status=503, code="persistence_unavailable", title="Persistence unavailable") from exc
    await persist_audit_event(db, event, commit=False)
    close_upload_stream()
    return part
