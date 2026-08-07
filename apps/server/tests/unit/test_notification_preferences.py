import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from twobrain_rec_server.billing.events import enqueue_billing_event
from twobrain_rec_server.billing.notification_preferences import (
    NotificationPreferences,
    channel_enabled,
    safe_action_path,
)
from twobrain_rec_server.billing.notifications import BillingNotification, build_notification


def test_mandatory_notification_overrides_optional_preferences() -> None:
    preferences = NotificationPreferences(optional_email_enabled=False, optional_in_app_enabled=False)
    assert channel_enabled(
        BillingNotification.PAYMENT_FAILED,
        channel="email",
        preferences=preferences,
    ) is True
    assert channel_enabled(
        BillingNotification.STORAGE_THRESHOLD,
        channel="email",
        preferences=preferences,
    ) is False
    with pytest.raises(ValueError):
        channel_enabled(BillingNotification.STORAGE_THRESHOLD, channel="sms", preferences=preferences)


def test_safe_action_path_is_same_origin_and_bounded() -> None:
    assert safe_action_path("/billing/usage") == "/billing/usage"
    assert safe_action_path("https://evil.example/billing") is None
    assert safe_action_path("//evil.example/billing") is None
    assert safe_action_path("/billing?next=https://evil.example") is None
    assert safe_action_path("/billing/%2e%2e/admin") is None
    assert safe_action_path("/admin") is None
    event = build_notification(
        event_id="safe-link",
        kind=BillingNotification.STORAGE_THRESHOLD,
        payload={"action_path": "https://evil.example"},
    )
    assert "action_path" not in event.safe_payload


def test_event_enqueue_respects_optional_channel_but_keeps_financial_notice() -> None:
    preferences = NotificationPreferences(optional_email_enabled=False, optional_in_app_enabled=False)
    with patch(
        "twobrain_rec_server.billing.events.enqueue_billing_notification",
        new=AsyncMock(return_value=True),
    ) as enqueue:
        assert asyncio.run(
            enqueue_billing_event(
                object(),
                workspace_id=uuid4(),
                recipient_id=uuid4(),
                event_type="storage.threshold",
                subject_ref="workspace:1",
                preferences=preferences,
            )
        ) is False
        assert asyncio.run(
            enqueue_billing_event(
                object(),
                workspace_id=uuid4(),
                recipient_id=uuid4(),
                event_type="payment.failed",
                subject_ref="invoice:1",
                preferences=preferences,
            )
        ) is True
    assert enqueue.await_count == 1
