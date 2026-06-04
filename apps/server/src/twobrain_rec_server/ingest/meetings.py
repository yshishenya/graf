from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.policy import validate_recording_duration
from twobrain_rec_server.ingest.store import MeetingRecord, store


def create_or_get_meeting(
    *,
    settings: Settings,
    tenant_scope: TenantScope,
    local_recording_id: str,
    duration_seconds: int,
    title: str | None,
) -> MeetingRecord:
    validate_recording_duration(settings, duration_seconds)
    meeting = store.create_or_get_meeting(
        settings=settings,
        organization_id=tenant_scope.organization_id,
        workspace_id=tenant_scope.workspace_id,
        user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        local_recording_id=local_recording_id,
        duration_seconds=duration_seconds,
        title=title,
    )
    record_audit_event(
        event_type="meeting_created",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        metadata={"local_recording_id": local_recording_id},
    )
    return meeting
