import pytest

from twobrain_rec_server.billing.monitoring import (
    BillingMetricSnapshot,
    merge_billing_metric_snapshots,
)
from twobrain_rec_server.readiness.checks import (
    billing_readiness_status,
    evaluate_billing_readiness,
)


def test_billing_metric_snapshot_is_counter_only_and_aggregates() -> None:
    snapshot = merge_billing_metric_snapshots(
        BillingMetricSnapshot(payment_success=2, storage_used_bytes=10),
        BillingMetricSnapshot(payment_success=1, notification_failures=2),
    )
    assert snapshot.as_safe_dict()["payment_success"] == 3
    assert snapshot.as_safe_dict()["storage_used_bytes"] == 10
    assert "provider_payment_id" not in snapshot.as_safe_dict()
    with pytest.raises(ValueError):
        BillingMetricSnapshot(notification_failures=-1)


def test_billing_readiness_fails_closed_and_exposes_only_gate_names() -> None:
    blocked = evaluate_billing_readiness(
        checkout_enabled=True,
        emergency_stop=False,
        required_evidence={"legal": True, "test_shop": False},
    )
    assert blocked.provider_mutations_allowed is False
    assert blocked.blocked_reasons == ("evidence_missing:test_shop",)
    assert evaluate_billing_readiness(
        checkout_enabled=True,
        emergency_stop=False,
        required_evidence={"legal": True},
    ).provider_mutations_allowed
    with pytest.raises(ValueError):
        evaluate_billing_readiness(checkout_enabled=True, emergency_stop=False, required_evidence={"legal": 1})


def test_billing_readiness_status_is_bounded_and_health_safe() -> None:
    assert billing_readiness_status(checkout_enabled=False, emergency_stop=False) == "disabled"
    assert billing_readiness_status(checkout_enabled=True, emergency_stop=True) == "emergency_stop"
    assert billing_readiness_status(checkout_enabled=True, emergency_stop=False) == "ready"
