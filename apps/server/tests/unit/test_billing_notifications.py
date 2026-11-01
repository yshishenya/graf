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


def test_refused_late_success_copy_requires_static_support_contact() -> None:
    event = build_notification(
        event_id="renewal:invoice-1:late-success-refused",
        kind=BillingNotification.RENEWAL_LATE_SUCCESS_REFUSED,
        payload={"invoice": "INV-1", "action_path": "/billing/history"},
    )

    title, body = notification_copy(event, support_email="billing@example.test")

    assert "после отключения продления" in title
    assert "billing@example.test" in body
    assert "не включен" in body


def test_renewal_attempt_failure_copy_states_the_access_end_date() -> None:
    event = build_notification(
        event_id="renewal:invoice-1:attempt-failed",
        kind=BillingNotification.RENEWAL_ATTEMPT_FAILED,
        payload={
            "invoice": "INV-RNW-1",
            "access_until": "10.08.2026 03:00",
            "action_path": "/billing/subscription",
            "email": "private@example.test",
        },
    )

    assert event.safe_payload == {
        "invoice": "INV-RNW-1",
        "access_until": "10.08.2026 03:00",
        "action_path": "/billing/subscription",
    }
    title, body = notification_copy(event)
    assert "не прошло" in title
    assert "Доступ отключится 10.08.2026 03:00 МСК" in body
    assert "INV-RNW-1" in body
    assert "private@example.test" not in body


def test_renewal_attempt_failure_is_mandatory_and_drops_an_unusable_date() -> None:
    outbox = NotificationOutbox()
    event = build_notification(
        event_id="renewal:1:attempt-failed",
        kind=BillingNotification.RENEWAL_ATTEMPT_FAILED,
        payload={"invoice": "INV-1", "access_until": "скоро"},
    )

    assert event.safe_payload == {"invoice": "INV-1"}
    assert outbox.enqueue(event, recipient_id="user-1", marketing_allowed=False) is not None
    _, body = notification_copy(event)
    assert "в конце оплаченного периода" in body


@pytest.mark.parametrize("access_until", ["10.08.2026 03:00", "завтра", None])
def test_final_failure_copy_uses_only_a_valid_historical_cutoff(access_until) -> None:
    event = build_notification(
        event_id="renewal:1:failed",
        kind=BillingNotification.PAYMENT_FAILED,
        payload={"invoice": "INV-1", "access_until": access_until, "email": "private@example.test"},
    )
    title, body = notification_copy(event)
    assert title == "Продление не состоялось"
    assert "был выбран бесплатный тариф" in body
    assert "Актуальный статус и доступные действия — в кабинете" in body
    assert "private@example.test" not in body
    if access_until == "10.08.2026 03:00":
        assert "Оплаченный период завершился 10.08.2026 03:00 МСК" in body
    else:
        assert "access_until" not in event.safe_payload
        assert "Оплаченный период завершился;" in body


@pytest.mark.parametrize("cycle,period", [("month", "месяц"), ("year", "год")])
def test_upcoming_copy_preserves_exact_price_and_historical_schedule(cycle, period):
    event = build_notification(
        event_id="renewal:period:upcoming", kind=BillingNotification.RENEWAL_UPCOMING,
        payload={
            "amount_minor": "1234567890123456789", "currency": "RUB", "cycle": cycle,
            "scheduled_at": "01.11.2026 03:00", "access_until": "04.11.2026 03:00",
            "last4": "0042", "action_path": "/billing/subscription",
            "masked_label": "private@example.test", "provider_id": "private-provider",
        },
    )
    title, body = notification_copy(event)
    assert title == "Напоминание о продлении"
    assert f"Тариф «Личный», период: {period}" in body
    assert "12 345 678 901 234 567,89 ₽" in body
    assert "по расписанию на момент события" in body
    assert "01.11.2026 03:00 МСК" in body and "04.11.2026 03:00 МСК" in body
    assert "•••• 0042" in body and "private" not in body
    assert "masked_label" not in event.safe_payload and "provider_id" not in event.safe_payload
    assert NotificationOutbox().enqueue(event, recipient_id="owner", marketing_allowed=False)


@pytest.mark.parametrize("payload", [
    {}, {"amount_minor": "-1", "currency": "USD", "cycle": "week", "last4": "12345"},
    {"amount_minor": "1.00", "last4": "１２３４", "scheduled_at": "soon"},
    {"amount_minor": True, "last4": "private@example.test"},
    {"amount_minor": "0", "last4": "1234\n"},
])
def test_upcoming_rejects_untrusted_fields_and_uses_generic_method(payload):
    event = build_notification(
        event_id="renewal:period:upcoming", kind=BillingNotification.RENEWAL_UPCOMING,
        payload=payload,
    )
    assert event.safe_payload == {}
    _, body = notification_copy(event)
    assert "сохранённый способ оплаты" in body
    assert "указана в кабинете" in body
