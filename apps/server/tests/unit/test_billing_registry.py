import pytest

from twobrain_rec_server.billing.registry import (
    RegistryInputError,
    registry_parts_complete,
    summarize_registry_csv,
)


def test_registry_summary_keeps_metadata_only_identity() -> None:
    summary = summarize_registry_csv(
        "payment_id,amount\nprovider-secret,790.00\n",
        registry_kind="payments",
        environment="test",
        required_columns=("payment_id", "amount"),
    )
    assert summary.registry_kind == "payments"
    assert summary.row_count == 1
    assert len(summary.content_sha256) == 64
    assert not hasattr(summary, "payment_id")


def test_registry_rejects_missing_columns_and_malformed_rows() -> None:
    with pytest.raises(RegistryInputError, match="columns"):
        summarize_registry_csv(
            "payment_id\npay-1\n",
            registry_kind="payments",
            environment="test",
            required_columns=("payment_id", "amount"),
        )
    with pytest.raises(RegistryInputError, match="width"):
        summarize_registry_csv(
            "payment_id,amount\npay-1\n",
            registry_kind="payments",
            environment="test",
            required_columns=("payment_id", "amount"),
        )


def test_registry_part_completeness_is_explicit() -> None:
    assert registry_parts_complete(required_parts=("payments", "refunds"), observed_parts={"payments"}) is False
    assert registry_parts_complete(required_parts=("payments", "refunds"), observed_parts={"payments", "refunds"}) is True
