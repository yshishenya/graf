from uuid import UUID

from twobrain_rec_server.ingest.store import AuditEvent, store


def record_audit_event(
    *,
    event_type: str,
    workspace_id: UUID,
    meeting_id: UUID | None = None,
    upload_session_id: UUID | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    safe_metadata = metadata or {}
    forbidden_keys = {"raw_audio", "transcript", "token", "authorization", "secret", "password"}
    filtered = {key: value for key, value in safe_metadata.items() if key.lower() not in forbidden_keys}
    store.audit_events.append(
        AuditEvent(
            event_type=event_type,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            upload_session_id=upload_session_id,
            metadata=filtered,
        )
    )
