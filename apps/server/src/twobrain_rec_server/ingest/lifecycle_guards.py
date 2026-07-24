from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.db.models import MediaRevision
from twobrain_rec_server.db.models import Meeting as MeetingModel
from twobrain_rec_server.domain.statuses import (
    MediaRevisionStatus,
    MeetingStatus,
    UploadSessionStatus,
)
from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.state_machine import is_terminal_upload_status
from twobrain_rec_server.ingest.store import (
    UploadSessionRecord,
    load_meeting_record,
    load_upload_session_record,
    persist_audit_event,
    persist_meeting,
    persist_upload_session,
    restore_meeting_after_upload_session_lifecycle,
)
from twobrain_rec_server.processing.fences import (
    lock_meeting_fence,
    meeting_is_deleted_or_deleting,
)


def _utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def ensure_meeting_accepts_uploads(
    *,
    db: AsyncSession | None,
    meeting_id: UUID,
    media_revision_status: MediaRevisionStatus | None = None,
) -> None:
    if media_revision_status == MediaRevisionStatus.DELETED:
        raise ProblemDetail(status=409, code="meeting_deletion_active", title="Meeting deletion is active")
    if db is None:
        return
    meeting = await db.scalar(
        select(MeetingModel)
        .where(MeetingModel.id == meeting_id)
        .execution_options(populate_existing=True)
    )
    if meeting is not None and meeting_is_deleted_or_deleting(meeting):
        raise ProblemDetail(status=409, code="meeting_deletion_active", title="Meeting deletion is active")


async def ensure_upload_session_mutable(
    *,
    db: AsyncSession | None,
    session: UploadSessionRecord,
    event_type: str,
) -> None:
    if session.status == UploadSessionStatus.EXPIRED:
        raise ProblemDetail(status=409, code="session_expired", title="Upload session is expired")
    if is_terminal_upload_status(session.status):
        raise ProblemDetail(status=409, code="session_terminal", title="Upload session is terminal")
    await ensure_meeting_accepts_uploads(db=db, meeting_id=session.meeting_id)
    if _utc_aware(session.expires_at) > datetime.now(UTC):
        return

    if db is None:
        meeting = store_module.store.meetings[session.meeting_id]
        session.status = UploadSessionStatus.EXPIRED
        restored = await restore_meeting_after_upload_session_lifecycle(
            db,
            meeting=meeting,
            session=session,
        )
        if not restored:
            meeting.status = MeetingStatus.EXPIRED
        record_audit_event(
            event_type=event_type,
            workspace_id=session.workspace_id,
            meeting_id=meeting.id,
            upload_session_id=session.id,
            actor_user_id=session.created_by_user_id,
            device_id=session.device_id,
            metadata={"temporary_object_count": len(session.parts)},
        )
        raise ProblemDetail(status=409, code="session_expired", title="Upload session is expired")

    # Expiry is a lifecycle mutation, so it must take the same Meeting →
    # UploadSession fence as accept/finalize/deletion.  Never lock the session
    # first and then discover the Meeting row.
    persisted_meeting = await lock_meeting_fence(
        db,
        workspace_id=session.workspace_id,
        meeting_id=session.meeting_id,
    )
    if persisted_meeting is None or meeting_is_deleted_or_deleting(persisted_meeting):
        raise ProblemDetail(status=409, code="meeting_deletion_active", title="Meeting deletion is active")
    current = await load_upload_session_record(db, session.id, for_update=True)
    if current is None:
        raise ProblemDetail(status=404, code="upload_session_not_found", title="Upload session not found")
    if current.status == UploadSessionStatus.EXPIRED:
        raise ProblemDetail(status=409, code="session_expired", title="Upload session is expired")
    if is_terminal_upload_status(current.status):
        raise ProblemDetail(status=409, code="session_terminal", title="Upload session is terminal")
    if _utc_aware(current.expires_at) > datetime.now(UTC):
        # The expiry snapshot changed while the request was waiting.  Do not
        # continue with a stale mutable session; retry against the new state.
        await db.rollback()
        raise ProblemDetail(status=409, code="upload_session_changed", title="Upload session changed; retry the request")

    meeting = await load_meeting_record(db, meeting_id=current.meeting_id)
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    current.status = UploadSessionStatus.EXPIRED
    restored = await restore_meeting_after_upload_session_lifecycle(
        db,
        meeting=meeting,
        session=current,
    )
    if not restored:
        meeting.status = MeetingStatus.EXPIRED
        if current.media_revision_id is not None:
            revision = await db.get(MediaRevision, current.media_revision_id)
            if revision is not None and revision.status != MediaRevisionStatus.ACCEPTED.value:
                revision.status = MediaRevisionStatus.BLOCKED.value
    event = record_audit_event(
        event_type=event_type,
        workspace_id=current.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=current.id,
        actor_user_id=current.created_by_user_id,
        device_id=current.device_id,
        metadata={"temporary_object_count": len(current.parts)},
    )
    await persist_meeting(db, meeting, commit=False)
    await persist_upload_session(db, current, commit=False)
    await persist_audit_event(db, event, commit=False)
    await db.commit()
    raise ProblemDetail(status=409, code="session_expired", title="Upload session is expired")
