import pytest

from twobrain_rec_server.billing.monitoring import (
    BillingMetricSnapshot,
    merge_billing_metric_snapshots,
)
from twobrain_rec_server.readiness.checks import (
    billing_readiness_status,
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


def test_billing_readiness_status_is_bounded_and_health_safe() -> None:
    assert billing_readiness_status(checkout_enabled=False, emergency_stop=False) == "disabled"
    assert billing_readiness_status(checkout_enabled=True, emergency_stop=True) == "emergency_stop"
    assert billing_readiness_status(checkout_enabled=True, emergency_stop=False) == "ready"
