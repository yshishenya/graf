from datetime import UTC, datetime
from uuid import UUID

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.domain.statuses import MeetingStatus, UploadSessionStatus
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.parts import get_session_for_tenant
from twobrain_rec_server.ingest.store import store


def abort_upload_session(
    *,
    tenant_scope: TenantScope,
    session_id: UUID,
    reason: str | None,
) -> object:
    session = get_session_for_tenant(session_id, tenant_scope)
    meeting = store.meetings[session.meeting_id]
    session.status = UploadSessionStatus.ABORTED
    meeting.status = MeetingStatus.ABORTED
    record_audit_event(
        event_type="aborted",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        metadata={"reason": reason or "user_aborted", "temporary_object_count": len(session.parts)},
    )
    return session


def expire_upload_session(*, tenant_scope: TenantScope, session_id: UUID) -> object:
    session = get_session_for_tenant(session_id, tenant_scope)
    if session.expires_at > datetime.now(UTC):
        raise ProblemDetail(status=409, code="session_not_expired", title="Session has not expired")
    meeting = store.meetings[session.meeting_id]
    session.status = UploadSessionStatus.EXPIRED
    meeting.status = MeetingStatus.EXPIRED
    record_audit_event(
        event_type="expired",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
        metadata={"temporary_object_count": len(session.parts)},
    )
    return session
