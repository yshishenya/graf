from uuid import UUID

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.store import UploadSessionRecord, store


def create_upload_session(
    *,
    settings: Settings,
    tenant_scope: TenantScope,
    meeting_id: UUID,
) -> UploadSessionRecord:
    meeting = store.meetings.get(meeting_id)
    if meeting is None or meeting.workspace_id != tenant_scope.workspace_id:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    session = store.create_upload_session(settings=settings, meeting=meeting)
    record_audit_event(
        event_type="session_created",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        upload_session_id=session.id,
    )
    return session
