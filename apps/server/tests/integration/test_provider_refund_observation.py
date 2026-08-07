from datetime import UTC, datetime

import pytest

from twobrain_rec_server.billing.reconciliation import (
    ObservationRecords,
    ProviderObservationError,
    ProviderScope,
    extract_receipt_observation,
    extract_refund_observation,
)

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
