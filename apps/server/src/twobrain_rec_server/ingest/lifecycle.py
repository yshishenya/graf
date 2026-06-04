from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.domain.statuses import MeetingStatus, UploadSessionStatus
from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.lifecycle_guards import ensure_upload_session_mutable
from twobrain_rec_server.ingest.parts import get_session_for_tenant
from twobrain_rec_server.ingest.store import (
    persist_audit_event,
    persist_meeting,
    persist_upload_session,
)


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
    event = record_audit_event(
        event_type="aborted",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
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
    event = record_audit_event(
        event_type="expired",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        metadata={"temporary_object_count": len(session.parts)},
    )
    await persist_meeting(db, meeting)
    await persist_upload_session(db, session)
    await persist_audit_event(db, event)
    return session
