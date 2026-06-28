from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import CalendarAuditEvent
from twobrain_rec_server.observability.redaction import redact_mapping


def metadata_only_calendar_audit(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return redact_mapping(metadata)


async def write_calendar_audit_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_type: str,
    outcome: str,
    actor_user_id: UUID | None = None,
    device_id: UUID | None = None,
    calendar_source_id: UUID | None = None,
    safe_reason_code: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> CalendarAuditEvent:
    event = CalendarAuditEvent(
        workspace_id=workspace_id,
        calendar_source_id=calendar_source_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type=event_type,
        outcome=outcome,
        safe_reason_code=safe_reason_code,
        metadata_json=metadata_only_calendar_audit(metadata or {}),
    )
    db.add(event)
    await db.flush()
    return event
