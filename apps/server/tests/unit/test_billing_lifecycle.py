from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.billing.history import mask_payment_method
from twobrain_rec_server.billing.notifications import (
    BillingNotification,
    NotificationOutbox,
    build_notification,
    notification_copy,
)
from twobrain_rec_server.billing.receipts import ReceiptState, receipt_label
from twobrain_rec_server.billing.renewal import renewal_due, resolve_renewal
from twobrain_rec_server.billing.storage_addons import (
    choose_storage_addon,
    effective_storage_capacity,
)
from twobrain_rec_server.billing.subscription import (
    SubscriptionControl,
    cancel_auto_renewal,
    project_plan,
    resume_auto_renewal,
)


def test_subscription_cancellation_and_no_grace_projection() -> None:
    paid_through = datetime(2026, 9, 1, tzinfo=UTC)
    control = cancel_auto_renewal(SubscriptionControl(paid_through, True, 1), expected_version=1)
    assert control.recurring_allowed is False
    assert project_plan(now=paid_through, paid_through=paid_through, recurring_allowed=False) == "free"


def test_subscription_resume_requires_active_paid_period_and_bumps_authority() -> None:
    paid_through = datetime(2026, 9, 1, tzinfo=UTC)
    control = resume_auto_renewal(SubscriptionControl(paid_through, False, 2), expected_version=2)
    assert control.recurring_allowed is True
    assert control.authority_version == 3


def test_subscription_resume_rejects_expired_period_and_stale_authority() -> None:
    paid_through = datetime(2026, 8, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="no longer active"):
        resume_auto_renewal(
            SubscriptionControl(paid_through, False, 2),
            expected_version=2,
            now=datetime(2026, 8, 6, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="changed"):
        resume_auto_renewal(
            SubscriptionControl(datetime(2026, 9, 1, tzinfo=UTC), False, 2),
            expected_version=1,
            now=datetime(2026, 8, 6, tzinfo=UTC),
        )


def test_renewal_and_storage_addon_are_bounded() -> None:
    paid_through = datetime(2026, 9, 1, tzinfo=UTC)
    assert renewal_due(now=paid_through - timedelta(hours=72), paid_through=paid_through)
    assert resolve_renewal(now=paid_through, paid_through=paid_through, provider_status="declined") == "free"
    addon = choose_storage_addon(capacity_bytes=5_000_000_000, starts_at=paid_through, ends_at=paid_through + timedelta(days=30))
    assert effective_storage_capacity(plan_code="personal", addon=addon) == 5_000_000_000


def test_receipt_history_and_notification_copy_is_safe() -> None:
    assert mask_payment_method("card_ending_1234") == "card_ending_1234"
    assert receipt_label(ReceiptState.AVAILABLE) == "Открыть чек"
    event = build_notification(event_id="evt-1", kind=BillingNotification.PAYMENT_SUCCEEDED, payload={"invoice": "INV-1", "provider_token": "secret"})
    assert event.safe_payload == {"invoice": "INV-1"}


def test_notification_outbox_is_idempotent_and_keeps_finance_notices() -> None:
    outbox = NotificationOutbox()
    event = build_notification(event_id="evt-1", kind=BillingNotification.PAYMENT_SUCCEEDED, payload={"invoice": "INV-1"})
    first = outbox.enqueue(event, recipient_id="user-1", marketing_allowed=False)
    assert first is not None
    assert outbox.enqueue(event, recipient_id="user-1", marketing_allowed=False) == first
    assert outbox.mark_delivered(event_id="evt-1", recipient_id="user-1", channel="email").state == "delivered"
    assert notification_copy(event) == ("Платёж подтверждён", "Оплата прошла успешно. Номер платежа: INV-1.")
    unsafe = build_notification(
        event_id="evt-2",
        kind=BillingNotification.PAYMENT_SUCCEEDED,
        payload={"invoice": "INV-2", "email": "private@example.com", "provider_id": "pay-1"},
    )
    assert unsafe.safe_payload == {"invoice": "INV-2"}


def test_notification_preferences_retry_and_safe_action_path() -> None:
    outbox = NotificationOutbox()
    optional = build_notification(
        event_id="evt-storage",
        kind=BillingNotification.STORAGE_THRESHOLD,
        payload={"action_path": "/billing/usage", "storage": "private"},
    )
    assert optional.safe_payload == {"action_path": "/billing/usage"}
    assert outbox.enqueue(optional, recipient_id="user-1", marketing_allowed=False) is None
    mandatory = build_notification(
        event_id="evt-late",
        kind=BillingNotification.RENEWAL_LATE_SUCCESS,
        payload={"invoice": "INV-3", "action_path": "/billing"},
    )
    assert outbox.enqueue(mandatory, recipient_id="user-1", marketing_allowed=False) is not None
    failed = outbox.mark_failed(
        event_id="evt-late",
        recipient_id="user-1",
        channel="email",
        error_code="smtp_timeout",
    )
    assert failed.state == "retry" and failed.attempts == 1
