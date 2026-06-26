from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import TrackRole
from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.lifecycle_guards import ensure_meeting_accepts_uploads
from twobrain_rec_server.ingest.store import (
    UploadSessionRecord,
    load_active_upload_session_for_meeting,
    load_meeting_record,
    persist_audit_event,
    persist_meeting,
    persist_upload_session,
)


async def create_upload_session(
    *,
    settings: Settings,
    tenant_scope: TenantScope,
    db: AsyncSession | None = None,
    meeting_id: UUID,
    expected_track_roles: list[TrackRole] | None = None,
    expected_track_sizes: dict[TrackRole, int] | None = None,
    idempotency_key: str | None = None,
) -> UploadSessionRecord:
    expected_track_roles = expected_track_roles or [TrackRole.MANIFEST, TrackRole.MICROPHONE, TrackRole.SYSTEM]
    for size in (expected_track_sizes or {}).values():
        if size < 0:
            raise ProblemDetail(status=400, code="invalid_expected_track_size", title="Expected track size must be non-negative")
    unexpected_size_roles = set(expected_track_sizes or {}) - set(expected_track_roles)
    if unexpected_size_roles:
        raise ProblemDetail(
            status=400,
            code="unexpected_expected_track_size_role",
            title="Expected track size provided for a role that is not expected",
        )
    meeting = await load_meeting_record(db, meeting_id=meeting_id)
    if meeting is None:
        meeting = store_module.store.meetings.get(meeting_id)
    if meeting is None or meeting.workspace_id != tenant_scope.workspace_id:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if meeting.created_by_user_id != tenant_scope.user_id or meeting.device_id != tenant_scope.device_id:
        raise ProblemDetail(status=403, code="meeting_scope_denied", title="Meeting scope denied")
    await ensure_meeting_accepts_uploads(
        db=db,
        meeting_id=meeting.id,
        media_revision_status=meeting.media_revision_status,
    )
    active_session = await load_active_upload_session_for_meeting(db, meeting.id)
    if active_session is not None:
        if idempotency_key and active_session.idempotency_key == idempotency_key:
            if (
                active_session.expected_track_roles == expected_track_roles
                and active_session.expected_track_sizes == (expected_track_sizes or {})
            ):
                return active_session
            raise ProblemDetail(status=409, code="idempotency_conflict", title="Idempotency key conflict")
        raise ProblemDetail(
            status=409,
            code="active_upload_session_exists",
            title="Active upload session already exists for meeting",
        )
    session = store_module.store.create_upload_session(
        settings=settings,
        meeting=meeting,
        expected_track_roles=expected_track_roles,
        expected_track_sizes=expected_track_sizes,
        idempotency_key=idempotency_key,
    )
    await persist_meeting(db, meeting, commit=False)
    event = record_audit_event(
        event_type="session_created",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
    )
    await persist_upload_session(db, session, settings, commit=False)
    await persist_audit_event(db, event, commit=False)
    return session
