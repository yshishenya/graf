from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.domain.statuses import MeetingStatus, UploadSessionStatus
from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.state_machine import is_terminal_upload_status
from twobrain_rec_server.ingest.store import (
    UploadSessionRecord,
    persist_audit_event,
    persist_meeting,
    persist_upload_session,
)


def _utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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
    if _utc_aware(session.expires_at) <= datetime.now(UTC):
        meeting = store_module.store.meetings[session.meeting_id]
        session.status = UploadSessionStatus.EXPIRED
        meeting.status = MeetingStatus.EXPIRED
        event = record_audit_event(
            event_type=event_type,
            workspace_id=session.workspace_id,
            meeting_id=meeting.id,
            upload_session_id=session.id,
            actor_user_id=session.created_by_user_id,
            device_id=session.device_id,
            metadata={"temporary_object_count": len(session.parts)},
        )
        await persist_meeting(db, meeting)
        await persist_upload_session(db, session)
        await persist_audit_event(db, event)
        raise ProblemDetail(status=409, code="session_expired", title="Upload session is expired")
