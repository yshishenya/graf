from uuid import UUID

from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.store import AuditEvent


def record_audit_event(
    *,
    event_type: str,
    workspace_id: UUID,
    meeting_id: UUID | None = None,
    upload_session_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    device_id: UUID | None = None,
    metadata: dict[str, object] | None = None,
) -> AuditEvent:
    safe_metadata = metadata or {}
    forbidden_keys = {"raw_audio", "transcript", "token", "authorization", "secret", "password"}
    filtered = {
        key[:120]: value[:240] if isinstance(value, str) else value
        for key, value in safe_metadata.items()
        if key.lower() not in forbidden_keys
    }
    event = AuditEvent(
        event_type=event_type,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        upload_session_id=upload_session_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        metadata=filtered,
    )
    store_module.store.audit_events.append(event)
    return event
