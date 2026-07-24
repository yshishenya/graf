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
from twobrain_rec_server.ingest.parts import get_session_for_tenant
from twobrain_rec_server.ingest.state_machine import is_terminal_upload_status
from twobrain_rec_server.ingest.store import (
    load_meeting_record,
    persist_audit_event,
    persist_meeting,
    persist_upload_session,
    restore_meeting_after_upload_session_lifecycle,
)
from twobrain_rec_server.processing.fences import lock_meeting_fence, meeting_is_deleted_or_deleting


def _utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def _lock_lifecycle_session(
    *,
    db: AsyncSession,
    tenant_scope: TenantScope,
    session_id: UUID,
) -> tuple[object, object]:
    """Acquire the shared Meeting → UploadSession lifecycle fence."""
    snapshot = await get_session_for_tenant(session_id, tenant_scope, db)
    locked_meeting = await lock_meeting_fence(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=snapshot.meeting_id,
    )
    if locked_meeting is None or meeting_is_deleted_or_deleting(locked_meeting):
        raise ProblemDetail(status=409, code="meeting_deletion_active", title="Meeting deletion is active")
    meeting = await load_meeting_record(db, meeting_id=locked_meeting.id)
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    session = await get_session_for_tenant(session_id, tenant_scope, db, for_update=True)
    return meeting, session


async def _expire_locked_session(
    *,
    db: AsyncSession | None,
    meeting: object,
    session: object,
    event_type: str,
) -> None:
    session.status = UploadSessionStatus.EXPIRED
    restored = await restore_meeting_after_upload_session_lifecycle(
        db,
        meeting=meeting,
        session=session,
    )
    if not restored:
        meeting.status = MeetingStatus.EXPIRED
        await mark_media_revision_blocked_for_lifecycle(db=db, meeting=meeting)
    event = record_audit_event(
        event_type=event_type,
        workspace_id=session.workspace_id,
        meeting_id=meeting.id,
        media_revision_id=session.media_revision_id or meeting.media_revision_id,
        upload_session_id=session.id,
        actor_user_id=session.created_by_user_id,
        device_id=session.device_id,
        metadata={"temporary_object_count": len(session.parts)},
    )
    await persist_meeting(db, meeting, commit=False)
    await persist_upload_session(db, session, commit=False)
    await persist_audit_event(db, event, commit=False)
    if db is not None:
        await db.commit()


async def mark_media_revision_blocked_for_lifecycle(
    *,
    db: AsyncSession | None,
    meeting: object,
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
    if db is None:
        session = await get_session_for_tenant(session_id, tenant_scope, db)
        meeting = store_module.store.meetings[session.meeting_id]
    else:
        meeting, session = await _lock_lifecycle_session(
            db=db,
            tenant_scope=tenant_scope,
            session_id=session_id,
        )
    if session.status == UploadSessionStatus.EXPIRED:
        raise ProblemDetail(status=409, code="session_expired", title="Upload session is expired")
    if is_terminal_upload_status(session.status):
        raise ProblemDetail(status=409, code="session_terminal", title="Upload session is terminal")
    if _utc_aware(session.expires_at) <= datetime.now(UTC):
        await _expire_locked_session(db=db, meeting=meeting, session=session, event_type="expired")
        raise ProblemDetail(status=409, code="session_expired", title="Upload session is expired")
    session.status = UploadSessionStatus.ABORTED
    restored = await restore_meeting_after_upload_session_lifecycle(
        db,
        meeting=meeting,
        session=session,
    )
    if not restored:
        meeting.status = MeetingStatus.ABORTED
        await mark_media_revision_blocked_for_lifecycle(db=db, meeting=meeting)
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
    await persist_meeting(db, meeting, commit=False)
    await persist_upload_session(db, session, commit=False)
    await persist_audit_event(db, event, commit=False)
    if db is not None:
        await db.commit()
    return session


async def expire_upload_session(*, tenant_scope: TenantScope, db: AsyncSession | None = None, session_id: UUID) -> object:
    session = await get_session_for_tenant(session_id, tenant_scope, db)
    if session.status == UploadSessionStatus.EXPIRED:
        raise ProblemDetail(status=409, code="session_expired", title="Upload session is expired")
    if is_terminal_upload_status(session.status):
        raise ProblemDetail(status=409, code="session_terminal", title="Upload session is terminal")
    if _utc_aware(session.expires_at) > datetime.now(UTC):
        raise ProblemDetail(status=409, code="session_not_expired", title="Session has not expired")
    if db is None:
        meeting = store_module.store.meetings[session.meeting_id]
    else:
        meeting, session = await _lock_lifecycle_session(
            db=db,
            tenant_scope=tenant_scope,
            session_id=session_id,
        )
        if session.status == UploadSessionStatus.EXPIRED:
            raise ProblemDetail(status=409, code="session_expired", title="Upload session is expired")
        if is_terminal_upload_status(session.status):
            raise ProblemDetail(status=409, code="session_terminal", title="Upload session is terminal")
        if _utc_aware(session.expires_at) > datetime.now(UTC):
            raise ProblemDetail(status=409, code="session_not_expired", title="Session has not expired")
    await _expire_locked_session(db=db, meeting=meeting, session=session, event_type="expired")
    return session
