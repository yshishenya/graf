"""Small transactional bridge from billing state changes to the notification outbox."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.notifications import (
    BillingNotification,
    DurableNotificationOutbox,
    build_notification,
)


async def enqueue_billing_notification(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    recipient_id: UUID,
    event_id: str,
    kind: BillingNotification,
    payload: dict[str, object] | None = None,
    marketing_allowed: bool = True,
) -> bool:
    """Build an allowlisted event and persist it in the caller's transaction."""
    event = build_notification(event_id=event_id, kind=kind, payload=payload or {})
    row = await DurableNotificationOutbox().enqueue(
        db,
        event,
        workspace_id=workspace_id,
        recipient_id=recipient_id,
        marketing_allowed=marketing_allowed,
    )
    return row is not None
