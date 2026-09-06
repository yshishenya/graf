from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest

from twobrain_rec_server.cabinet.web_routes import billing
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import BillingInvoice, BillingOperation

WORKSPACE_ID = UUID("20000000-0000-4000-8000-000000000002")
OPERATION_ID = UUID("10000000-0000-4000-8000-000000000001")


def _operation(*, expires_at: datetime | None, state: str = "manual_resolution") -> BillingOperation:
    return BillingOperation(
        id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        kind="initial_checkout",
        idempotency_key="same-provider-key",
        state=state,
        provider_key_expires_at=expires_at,
        request_snapshot={
            "plan_code": "personal",
            "cycle": "month",
            "payable_amount_minor": 1_000,
            "offer_consent": True,
            "recurring_consent": True,
            "receipt_config": {
                "tax_system_code": 2,
                "vat_code": 1,
                "payment_subject": "service",
                "payment_mode": "full_payment",
            },
        },
    )


def _invoice() -> BillingInvoice:
    return BillingInvoice(
        workspace_id=WORKSPACE_ID,
        operation_id=OPERATION_ID,
        safe_number="INV-RECOVERY1",
        amount_minor=1_000,
        currency="RUB",
        receipt_contact_snapshot="owner@example.test",
    )


@pytest.mark.asyncio
async def test_initial_checkout_continuation_reuses_the_same_provider_key(monkeypatch) -> None:
    now = datetime(2026, 8, 25, 10, tzinfo=UTC)
    operation = _operation(expires_at=now + timedelta(hours=1))
    calls: list[dict[str, object]] = []

    class Provider:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def create_payment(self, **kwargs):
            calls.append(kwargs)
            return {
                "id": "payment-recovered",
                "confirmation": {"confirmation_url": "https://yookassa.test/checkout/recovered"},
            }

    monkeypatch.setattr(billing, "YooKassaClient", lambda _settings: Provider())
    settings = Settings(billing_provider_floor_minor=100)

    first = await billing._create_initial_checkout_payment(
        settings=settings,
        operation=operation,
        invoice=_invoice(),
        return_url="https://rec.example.test/billing/checkout/return?invoice=INV-RECOVERY1",
    )
    second = await billing._create_initial_checkout_payment(
        settings=settings,
        operation=operation,
        invoice=_invoice(),
        return_url="https://rec.example.test/billing/checkout/return?invoice=INV-RECOVERY1",
    )

    assert first == second
    assert [call["idempotence_key"] for call in calls] == [
        "same-provider-key",
        "same-provider-key",
    ]
    assert all(call["amount_minor"] == 1_000 for call in calls)
    assert all(call["metadata"]["operation_id"] == str(OPERATION_ID) for call in calls)


def test_provider_reject_before_provider_id_keeps_only_safe_failure_metadata() -> None:
    now = datetime(2026, 8, 25, 10, tzinfo=UTC)
    operation = _operation(expires_at=now + timedelta(hours=1), state="scheduled")
    invoice = _invoice()
    error = billing.YooKassaProviderError(
        "secret provider response must not be persisted",
        status_code=400,
    )

    billing._record_initial_checkout_failure(operation, invoice, error, now=now)

    assert operation.provider_id is None
    assert operation.state == "manual_resolution"
    assert invoice.status == "manual_resolution"
    assert operation.request_snapshot["provider_failure"] == {
        "class": "provider_rejected",
        "http_status": 400,
        "observed_at": "2026-08-25T10:00:00+00:00",
    }
    assert "secret provider response" not in str(operation.request_snapshot)


def test_expired_provider_key_blocks_continuation() -> None:
    now = datetime(2026, 8, 25, 10, tzinfo=UTC)
    operation = _operation(expires_at=now)

    assert billing._initial_checkout_can_continue(operation, now=now) is False


def test_missing_provider_key_expiry_blocks_continuation() -> None:
    operation = _operation(expires_at=None)

    assert billing._initial_checkout_can_continue(operation) is False


def test_status_refresh_does_not_report_success_when_nothing_was_processed() -> None:
    assert billing._status_refresh_result(
        {"processed": 0, "succeeded": 0, "canceled": 0, "pending": 0, "failed": 0}
    ) == "unchanged"
    assert billing._status_refresh_result(
        {"processed": 1, "succeeded": 0, "canceled": 0, "pending": 1, "failed": 0}
    ) == "refreshed"
    assert billing._status_refresh_result(
        {"processed": 1, "succeeded": 0, "canceled": 0, "pending": 0, "failed": 1}
    ) == "unavailable"


def test_transport_failure_metadata_has_no_exception_text() -> None:
    error = httpx.ReadTimeout("private upstream detail")
    metadata = billing._initial_checkout_failure_metadata(
        error,
        now=datetime(2026, 8, 25, 10, tzinfo=UTC),
    )

    assert metadata == {
        "class": "transport_timeout",
        "observed_at": "2026-08-25T10:00:00+00:00",
    }
    assert "private upstream detail" not in str(metadata)
