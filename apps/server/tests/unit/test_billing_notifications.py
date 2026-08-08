import pytest

from twobrain_rec_server.billing.notifications import (
    BillingNotification,
    NotificationOutbox,
    build_notification,
    notification_copy,
)


def test_notification_event_allowlist_strips_private_fields_and_renders_safe_copy() -> None:
    event = build_notification(
        event_id="payment:invoice-1:succeeded",
        kind=BillingNotification.PAYMENT_SUCCEEDED,
        payload={
            "invoice": "INV-2026-0001",
            "action_path": "/billing",
            "email": "private@example.test",
            "provider_id": "pay_secret",
        },
    )

    assert event.safe_payload == {"invoice": "INV-2026-0001", "action_path": "/billing"}
    assert "INV-2026-0001" in notification_copy(event)[1]
    assert "private@example.test" not in notification_copy(event)[1]


def test_mandatory_notice_bypasses_marketing_preference_but_optional_notice_does_not() -> None:
    outbox = NotificationOutbox()
    mandatory = build_notification(
        event_id="payment:1:failed",
        kind=BillingNotification.PAYMENT_FAILED,
        payload={},
    )
    optional = build_notification(
        event_id="trial:1:ending",
        kind=BillingNotification.TRIAL_ENDING,
        payload={},
    )

    assert outbox.enqueue(mandatory, recipient_id="user-1", marketing_allowed=False) is not None
    assert outbox.enqueue(optional, recipient_id="user-1", marketing_allowed=False) is None


def test_outbox_is_idempotent_and_caps_retry_attempts() -> None:
    outbox = NotificationOutbox()
    event = build_notification(
        event_id="receipt:1:available",
        kind=BillingNotification.RECEIPT_AVAILABLE,
        payload={"invoice": "INV-1"},
    )

    first = outbox.enqueue(event, recipient_id="user-1")
    duplicate = outbox.enqueue(event, recipient_id="user-1")
    assert first == duplicate
    assert first is not None

    for _ in range(5):
        result = outbox.mark_failed(
            event_id=event.event_id,
            recipient_id="user-1",
            channel="email",
            error_code="smtp_unavailable",
        )
    assert result.state == "failed"
    assert result.attempts == 5


def test_outbox_rejects_invalid_recipient_and_channel() -> None:
    outbox = NotificationOutbox()
    event = build_notification(
        event_id="trial:1:expired",
        kind=BillingNotification.TRIAL_EXPIRED,
        payload={},
    )

    with pytest.raises(ValueError):
        outbox.enqueue(event, recipient_id=" ")
    with pytest.raises(ValueError):
        outbox.enqueue(event, recipient_id="user-1", channel="sms")
