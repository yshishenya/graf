from uuid import UUID

from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.store import AuditEvent
from twobrain_rec_server.observability.redaction import redact_mapping

DENIED_ACCESS_METADATA_KEYS = {
    "request_class",
    "feature_area",
    "reason_category",
    "validation_outcome",
}


def _truncate_metadata(value: object) -> object:
    if isinstance(value, str):
        return value[:240]
    if isinstance(value, dict):
        return {str(key)[:120]: _truncate_metadata(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_truncate_metadata(item) for item in value]
    return value


def record_audit_event(
    *,
    event_type: str,
    workspace_id: UUID,
    meeting_id: UUID | None = None,
    media_revision_id: UUID | None = None,
    upload_session_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    device_id: UUID | None = None,
    metadata: dict[str, object] | None = None,
) -> AuditEvent:
    filtered = _truncate_metadata(redact_mapping(metadata or {}))
    event = AuditEvent(
        event_type=event_type,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        upload_session_id=upload_session_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        metadata=filtered,
    )
    store_module.store.audit_events.append(event)
    return event


def denied_access_metadata(**values: object) -> dict[str, object]:
    return redact_mapping(
        {
            key: _truncate_metadata(value)
            for key, value in values.items()
            if key in DENIED_ACCESS_METADATA_KEYS
        }
    )
