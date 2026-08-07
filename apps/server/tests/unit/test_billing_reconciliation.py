from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.billing.reconciliation import (
    ObservationRecords,
    ProviderObservationError,
    ProviderScope,
    extract_payment_observation,
    extract_receipt_observation,
    extract_refund_observation,
    saved_bank_card_confirmed,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)
SCOPE = ProviderScope("test", "shop-1")


def test_payment_observation_extracts_only_bounded_provider_truth() -> None:
    observation = extract_payment_observation(
        {
            "id": "pay-1",
            "status": "succeeded",
            "amount": {"value": "790.00", "currency": "RUB"},
            "created_at": "2026-08-06T09:00:00Z",
            "receipt_registration": "pending",
            "metadata": {"workspace_id": "must-not-survive"},
            "payment_method": {"card": {"last4": "1111"}},
        },
        scope=SCOPE,
    )

    assert observation.provider_payment_id == "pay-1"
    assert observation.amount_minor == 79_000
    assert observation.currency == "RUB"
    assert observation.status == "succeeded"
    assert observation.receipt_registration == "pending"
    assert not hasattr(observation, "metadata")
    assert not hasattr(observation, "payment_method")


def test_saved_method_projection_exposes_only_safe_capability() -> None:
    assert saved_bank_card_confirmed({"payment_method": {"type": "bank_card", "saved": True, "id": "secret"}})
    assert not saved_bank_card_confirmed({"payment_method": {"type": "bank_card", "saved": False}})
    assert not saved_bank_card_confirmed({"payment_method": {"type": "sbp", "saved": True}})


def test_refund_observation_accepts_only_confirmed_positive_refunds() -> None:
    observation = extract_refund_observation(
        {
            "id": "refund-1",
            "payment_id": "pay-1",
            "status": "succeeded",
            "amount": {"value": "123.45", "currency": "RUB"},
            "created_at": "2026-08-06T10:00:00+00:00",
            "receipt_registration": "succeeded",
            "description": "merchant-only reason must not survive",
        },
        scope=SCOPE,
    )

    assert observation.provider_refund_id == "refund-1"
    assert observation.provider_payment_id == "pay-1"
    assert observation.amount_minor == 12_345
    assert observation.status == "succeeded"
    assert not hasattr(observation, "description")

    with pytest.raises(ProviderObservationError, match="confirmed refund"):
        extract_refund_observation(
            {
                "id": "refund-pending",
                "payment_id": "pay-1",
                "status": "pending",
                "amount": {"value": "1.00", "currency": "RUB"},
                "created_at": "2026-08-06T10:00:00Z",
            },
            scope=SCOPE,
        )


@pytest.mark.parametrize("value", ["0.00", "1.001", "NaN", 1.0])
def test_observation_rejects_unsafe_money(value: object) -> None:
    with pytest.raises(ProviderObservationError):
        extract_payment_observation(
            {
                "id": "pay-1",
                "status": "succeeded",
                "amount": {"value": value, "currency": "RUB"},
                "created_at": "2026-08-06T09:00:00Z",
            },
            scope=SCOPE,
        )


def test_receipt_observation_requires_one_safe_provider_parent() -> None:
    receipt = extract_receipt_observation(
        {
            "id": "rt-1",
            "type": "refund",
            "refund_id": "refund-1",
            "status": "succeeded",
            "registered_at": "2026-08-06T11:00:00Z",
            "customer": {"email": "must-not-survive@example.test"},
            "items": [{"description": "must-not-survive"}],
        },
        scope=SCOPE,
    )

    assert receipt.provider_receipt_id == "rt-1"
    assert receipt.parent_kind == "refund"
    assert receipt.provider_parent_id == "refund-1"
    assert receipt.registered_at == datetime(2026, 8, 6, 11, tzinfo=UTC)
    assert not hasattr(receipt, "customer")
    assert not hasattr(receipt, "items")

    with pytest.raises(ProviderObservationError, match="parent"):
        extract_receipt_observation(
            {"id": "rt-2", "type": "payment", "status": "pending"},
            scope=SCOPE,
        )


def test_observation_records_are_idempotent_and_monotonic() -> None:
    records = ObservationRecords()
    pending = extract_payment_observation(
        {
            "id": "pay-1",
            "status": "pending",
            "amount": {"value": "790.00", "currency": "RUB"},
            "created_at": "2026-08-06T09:00:00Z",
        },
        scope=SCOPE,
    )
    succeeded = extract_payment_observation(
        {
            "id": "pay-1",
            "status": "succeeded",
            "amount": {"value": "790.00", "currency": "RUB"},
            "created_at": "2026-08-06T09:00:00Z",
            "receipt_registration": "pending",
        },
        scope=SCOPE,
    )

    assert records.record(pending, source="poll", observed_at=NOW) == "inserted"
    assert records.record(pending, source="webhook", observed_at=NOW) == "duplicate"
    assert records.record(succeeded, source="poll", observed_at=NOW + timedelta(minutes=1)) == "updated"
    assert records.get(succeeded).sources == frozenset({"poll", "webhook"})

    with pytest.raises(ProviderObservationError, match="regressive"):
        records.record(pending, source="poll", observed_at=NOW + timedelta(minutes=2))


def test_observation_records_reject_conflicting_immutable_truth() -> None:
    records = ObservationRecords()
    first = extract_refund_observation(
        {
            "id": "refund-1",
            "payment_id": "pay-1",
            "status": "succeeded",
            "amount": {"value": "10.00", "currency": "RUB"},
            "created_at": "2026-08-06T10:00:00Z",
        },
        scope=SCOPE,
    )
    conflicting = extract_refund_observation(
        {
            "id": "refund-1",
            "payment_id": "pay-1",
            "status": "succeeded",
            "amount": {"value": "11.00", "currency": "RUB"},
            "created_at": "2026-08-06T10:00:00Z",
        },
        scope=SCOPE,
    )

    records.record(first, source="webhook", observed_at=NOW)
    with pytest.raises(ProviderObservationError, match="conflicting"):
        records.record(conflicting, source="registry", observed_at=NOW)


def test_observation_identity_is_scoped_by_environment_and_shop() -> None:
    payload = {
        "id": "pay-shared",
        "status": "pending",
        "amount": {"value": "1.00", "currency": "RUB"},
        "created_at": "2026-08-06T09:00:00Z",
    }
    records = ObservationRecords()

    assert (
        records.record(
            extract_payment_observation(payload, scope=ProviderScope("test", "shop-1")),
            source="poll",
            observed_at=NOW,
        )
        == "inserted"
    )
    assert (
        records.record(
            extract_payment_observation(payload, scope=ProviderScope("production", "shop-1")),
            source="poll",
            observed_at=NOW,
        )
        == "inserted"
    )
