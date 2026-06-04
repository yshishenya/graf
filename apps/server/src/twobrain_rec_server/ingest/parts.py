from hashlib import sha256
from uuid import UUID

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import TrackRole, UploadSessionStatus
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.policy import validate_track_bytes
from twobrain_rec_server.ingest.state_machine import ensure_can_accept_part
from twobrain_rec_server.ingest.store import UploadPartRecord, UploadSessionRecord, store
from twobrain_rec_server.storage.object_keys import build_track_object_key


def get_session_for_tenant(session_id: UUID, tenant_scope: TenantScope) -> UploadSessionRecord:
    session = store.sessions.get(session_id)
    if session is None or session.workspace_id != tenant_scope.workspace_id:
        raise ProblemDetail(status=404, code="upload_session_not_found", title="Upload session not found")
    if session.device_id != tenant_scope.device_id:
        raise ProblemDetail(status=403, code="device_scope_denied", title="Device scope denied")
    return session


def accept_part(
    *,
    settings: Settings,
    tenant_scope: TenantScope,
    session_id: UUID,
    track_role: TrackRole,
    part_number: int,
    byte_offset: int,
    content_sha256: str,
    data: bytes,
) -> UploadPartRecord:
    session = get_session_for_tenant(session_id, tenant_scope)
    try:
        ensure_can_accept_part(session.status)
    except ValueError as exc:
        raise ProblemDetail(status=409, code="session_terminal", title="Upload session is terminal") from exc
    validate_track_bytes(settings, len(data))
    actual_sha = sha256(data).hexdigest()
    if actual_sha != content_sha256:
        raise ProblemDetail(status=400, code="checksum_mismatch", title="Checksum mismatch")

    part_key = (track_role, part_number)
    existing = session.parts.get(part_key)
    if existing:
        if existing.sha256 == content_sha256 and existing.byte_length == len(data):
            return existing
        record_audit_event(
            event_type="part_conflict",
            workspace_id=tenant_scope.workspace_id,
            meeting_id=session.meeting_id,
            upload_session_id=session.id,
            metadata={"track_role": track_role.value, "part_number": part_number},
        )
        raise ProblemDetail(status=409, code="checksum_conflict", title="Checksum conflict")

    meeting = store.meetings[session.meeting_id]
    object_key = build_track_object_key(
        organization_id=tenant_scope.organization_id,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        track_role=track_role,
        part_number=part_number,
    )
    part = UploadPartRecord(
        track_role=track_role,
        part_number=part_number,
        byte_offset=byte_offset,
        byte_length=len(data),
        sha256=content_sha256,
        object_key=object_key,
        data=data,
    )
    session.parts[part_key] = part
    session.status = UploadSessionStatus.UPLOADING
    record_audit_event(
        event_type="part_accepted",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        metadata={"track_role": track_role.value, "part_number": part_number, "byte_length": len(data)},
    )
    return part
