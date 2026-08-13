"""Small transactional bridge from billing state changes to the notification outbox."""

from __future__ import annotations

import re
from enum import StrEnum
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.notification_preferences import (
    NotificationPreferences,
    channel_enabled,
)
from twobrain_rec_server.billing.notifications import (
    BillingNotification,
    DurableNotificationOutbox,
    build_notification,
)


class BillingEvent(StrEnum):
    """Product lifecycle events that may enter the notification outbox.

    The list is deliberately closed.  In particular, provider refund events
    are reconciliation inputs only and can never become a customer message.
    """

    TRIAL_ENDING = "trial.ending"
    TRIAL_EXPIRED = "trial.expired"
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    RENEWAL_UNKNOWN = "renewal.unknown"
    RENEWAL_LATE_SUCCESS = "renewal.late_success"
    RENEWAL_LATE_SUCCESS_REFUSED = "renewal.late_success_refused"
    RENEWAL_MANUAL_RESUME = "renewal.manual_resume"
    STORAGE_THRESHOLD = "storage.threshold"
    RECEIPT_AVAILABLE = "receipt.available"
    REFERRAL_CREDIT = "referral.credit"
    FAIR_USE_REVIEW = "fair_use.review"
    ACCOUNT_CLOSE = "account.close"


_EVENT_NOTIFICATION_KIND: dict[BillingEvent, BillingNotification] = {
    BillingEvent.TRIAL_ENDING: BillingNotification.TRIAL_ENDING,
    BillingEvent.TRIAL_EXPIRED: BillingNotification.TRIAL_EXPIRED,
    BillingEvent.PAYMENT_SUCCEEDED: BillingNotification.PAYMENT_SUCCEEDED,
    BillingEvent.PAYMENT_FAILED: BillingNotification.PAYMENT_FAILED,
    BillingEvent.RENEWAL_UNKNOWN: BillingNotification.RENEWAL_UNKNOWN,
    BillingEvent.RENEWAL_LATE_SUCCESS: BillingNotification.RENEWAL_LATE_SUCCESS,
    BillingEvent.RENEWAL_LATE_SUCCESS_REFUSED: BillingNotification.RENEWAL_LATE_SUCCESS_REFUSED,
    BillingEvent.RENEWAL_MANUAL_RESUME: BillingNotification.RENEWAL_MANUAL_RESUME,
    BillingEvent.STORAGE_THRESHOLD: BillingNotification.STORAGE_THRESHOLD,
    BillingEvent.RECEIPT_AVAILABLE: BillingNotification.RECEIPT_AVAILABLE,
    BillingEvent.REFERRAL_CREDIT: BillingNotification.REFERRAL_CREDIT,
    BillingEvent.FAIR_USE_REVIEW: BillingNotification.FAIR_USE_REVIEW,
    BillingEvent.ACCOUNT_CLOSE: BillingNotification.ACCOUNT_CLOSE,
}

_SAFE_SUBJECT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}\Z")


def notification_kind_for(event_type: BillingEvent | str) -> BillingNotification:
    """Resolve a closed event taxonomy; unknown/refund events are rejected."""
    try:
        event = event_type if isinstance(event_type, BillingEvent) else BillingEvent(event_type)
    except ValueError as exc:
        raise ValueError("billing notification event is not allowlisted") from exc
    return _EVENT_NOTIFICATION_KIND[event]


def event_id_for(*, event_type: BillingEvent | str, subject_ref: str) -> str:
    """Build a deterministic, non-content event id for outbox deduplication."""
    event = event_type if isinstance(event_type, BillingEvent) else BillingEvent(event_type)
    if not _SAFE_SUBJECT.fullmatch(subject_ref):
        raise ValueError("billing notification subject reference is invalid")
    return f"{event.value}:{subject_ref}"


async def enqueue_billing_notification(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    recipient_id: UUID,
    event_id: str,
    kind: BillingNotification,
    payload: dict[str, object] | None = None,
    channel: str = "email",
    marketing_allowed: bool = True,
) -> bool:
    """Build an allowlisted event and persist it in the caller's transaction."""
    event = build_notification(event_id=event_id, kind=kind, payload=payload or {})
    row = await DurableNotificationOutbox().enqueue(
        db,
        event,
        workspace_id=workspace_id,
        recipient_id=recipient_id,
        channel=channel,
        marketing_allowed=marketing_allowed,
    )
    return row is not None


async def enqueue_billing_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    recipient_id: UUID,
    event_type: BillingEvent | str,
    subject_ref: str,
    payload: dict[str, object] | None = None,
    channel: str = "email",
    preferences: NotificationPreferences | None = None,
    marketing_allowed: bool = True,
) -> bool:
    """Map one allowlisted lifecycle event to an idempotent notification.

    `subject_ref` is an opaque safe reference (invoice number, incident id or
    account-close id); raw provider payloads and refund correspondence never
    cross this boundary.
    """
    kind = notification_kind_for(event_type)
    if preferences is not None and not channel_enabled(
        kind,
        channel=channel,
        preferences=preferences,
    ):
        return False
    return await enqueue_billing_notification(
        db,
        workspace_id=workspace_id,
        recipient_id=recipient_id,
        event_id=event_id_for(event_type=event_type, subject_ref=subject_ref),
        kind=kind,
        payload=payload,
        channel=channel,
        marketing_allowed=marketing_allowed,
    )
