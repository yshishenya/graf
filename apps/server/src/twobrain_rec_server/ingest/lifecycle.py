from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import MediaRevision
from twobrain_rec_server.domain.statuses import (
    MediaRevisionStatus,
    MeetingStatus,
    UploadSessionStatus,
)
from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.lifecycle_guards import ensure_upload_session_mutable
from twobrain_rec_server.ingest.parts import get_session_for_tenant
from twobrain_rec_server.ingest.store import (
    persist_audit_event,
    persist_meeting,
    persist_upload_session,
)


async def mark_media_revision_blocked_for_lifecycle(
    *,
    db: AsyncSession | None,
    meeting: object,
    reason: str,
) -> None:
    meeting.media_revision_status = MediaRevisionStatus.BLOCKED
    if db is None or meeting.media_revision_id is None:
        return
    revision = await db.get(MediaRevision, meeting.media_revision_id)
    if revision is not None and revision.status != MediaRevisionStatus.ACCEPTED.value:
        revision.status = MediaRevisionStatus.BLOCKED.value


async def abort_upload_session(
    *,
    tenant_scope: TenantScope,
    db: AsyncSession | None = None,
    session_id: UUID,
    reason: str | None,
) -> object:
    session = await get_session_for_tenant(session_id, tenant_scope, db)
    await ensure_upload_session_mutable(db=db, session=session, event_type="expired")
    meeting = store_module.store.meetings[session.meeting_id]
    session.status = UploadSessionStatus.ABORTED
    meeting.status = MeetingStatus.ABORTED
    await mark_media_revision_blocked_for_lifecycle(
        db=db,
        meeting=meeting,
        reason="upload_session_aborted",
    )
    event = record_audit_event(
        event_type="aborted",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        media_revision_id=session.media_revision_id or meeting.media_revision_id,
        upload_session_id=session.id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        metadata={"reason": reason or "user_aborted", "temporary_object_count": len(session.parts)},
    )
    await persist_meeting(db, meeting)
    await persist_upload_session(db, session)
    await persist_audit_event(db, event)
    return session


async def expire_upload_session(*, tenant_scope: TenantScope, db: AsyncSession | None = None, session_id: UUID) -> object:
    session = await get_session_for_tenant(session_id, tenant_scope, db)
    if session.expires_at > datetime.now(UTC):
        raise ProblemDetail(status=409, code="session_not_expired", title="Session has not expired")
    meeting = store_module.store.meetings[session.meeting_id]
    session.status = UploadSessionStatus.EXPIRED
    meeting.status = MeetingStatus.EXPIRED
    await mark_media_revision_blocked_for_lifecycle(
        db=db,
        meeting=meeting,
        reason="upload_session_expired",
    )
    event = record_audit_event(
        event_type="expired",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        media_revision_id=session.media_revision_id or meeting.media_revision_id,
        upload_session_id=session.id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        metadata={"temporary_object_count": len(session.parts)},
    )
    await persist_meeting(db, meeting)
    await persist_upload_session(db, session)
    await persist_audit_event(db, event)
    return session
