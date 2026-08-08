import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from twobrain_rec_server.billing.reconciliation import (
    ObservationRecords,
    ProviderObservationError,
    ProviderScope,
    extract_receipt_observation,
    extract_refund_observation,
    record_observed_refund,
)
from twobrain_rec_server.db.models import BillingInvoice, BillingOperation

SCOPE = ProviderScope(environment="test", shop_id="shop-1")
NOW = datetime(2026, 8, 7, 12, tzinfo=UTC)


def test_full_and_partial_refund_observations_are_read_only_and_idempotent() -> None:
    records = ObservationRecords()
    for amount, refund_id, source in ((79000, "refund-full", "webhook"), (1000, "refund-partial", "registry")):
        observation = extract_refund_observation(
            {
                "id": refund_id,
                "payment_id": "pay-1",
                "status": "succeeded",
                "amount": {"value": f"{amount / 100:.2f}", "currency": "RUB"},
                "created_at": NOW.isoformat(),
            },
            scope=SCOPE,
        )
        assert records.record(observation, source=source, observed_at=NOW) == "inserted"
        assert records.record(observation, source="poll", observed_at=NOW) == "duplicate"


def test_receipt_observation_requires_one_parent_and_unknown_webhook_can_use_poll_backstop() -> None:
    receipt = extract_receipt_observation(
        {
            "id": "receipt-1",
            "type": "payment",
            "payment_id": "pay-1",
            "status": "succeeded",
            "registered_at": NOW.isoformat(),
        },
        scope=SCOPE,
    )
    records = ObservationRecords()
    assert records.record(receipt, source="poll", observed_at=NOW) == "inserted"
    with pytest.raises(ProviderObservationError):
        extract_receipt_observation(
            {
                "id": "receipt-2",
                "type": "payment",
                "payment_id": "pay-1",
                "refund_id": "refund-1",
                "status": "succeeded",
            },
            scope=SCOPE,
        )


def test_provider_refund_observation_is_idempotently_bound_without_refund_mutation(monkeypatch) -> None:
    operation = BillingOperation(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        workspace_id=UUID("22222222-2222-4222-8222-222222222222"),
        kind="initial_checkout",
        idempotency_key="checkout-1",
        provider_id="pay-1",
    )
    invoice = BillingInvoice(
        id=UUID("33333333-3333-4333-8333-333333333333"),
        workspace_id=operation.workspace_id,
        operation_id=operation.id,
        safe_number="INV-1",
        amount_minor=79_000,
        currency="RUB",
        plan_snapshot={"billing_actor_user_id": "44444444-4444-4444-8444-444444444444"},
    )
    refund = extract_refund_observation(
        {
            "id": "refund-1",
            "payment_id": "pay-1",
            "status": "succeeded",
            "amount": {"value": "1.00", "currency": "RUB"},
            "created_at": NOW.isoformat(),
        },
        scope=SCOPE,
    )

    class FakeDb:
        def __init__(self):
            self.values = [operation, invoice, None, 0, None]
            self.added = []

        async def scalar(self, _query):
            return self.values.pop(0)

        def add(self, value):
            self.added.append(value)

        async def flush(self):
            return None

    captured = {}

    async def no_reward(*_args, **kwargs):
        captured.update(kwargs)
        return "none"

    monkeypatch.setattr("twobrain_rec_server.billing.reconciliation.reverse_credit_for_payment", no_reward)
    db = FakeDb()
    assert asyncio.run(record_observed_refund(db, workspace_id=operation.workspace_id, observation=refund)) == "inserted"
    assert len(db.added) == 1
    assert db.added[0].amount_minor == 100
    assert captured["invitee_user_id"] == UUID("44444444-4444-4444-8444-444444444444")
