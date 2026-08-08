"""Metadata-only billing health projections for operator diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class BillingMetricSnapshot:
    payment_success: int = 0
    payment_canceled: int = 0
    renewal_unknown: int = 0
    webhook_lag_seconds: int = 0
    immediate_free_projections: int = 0
    duplicate_prevented: int = 0
    storage_used_bytes: int = 0
    storage_reserved_bytes: int = 0
    reconciliation_gaps: int = 0
    notification_failures: int = 0

    def __post_init__(self) -> None:
        if any(value < 0 for value in asdict(self).values()):
            raise ValueError("billing metrics cannot be negative")

    def as_safe_dict(self) -> dict[str, int]:
        """Return counters only; payment/provider/content identifiers are excluded."""
        return {key: int(value) for key, value in asdict(self).items()}


def merge_billing_metric_snapshots(*snapshots: BillingMetricSnapshot) -> BillingMetricSnapshot:
    """Aggregate bounded counters across workspaces without retaining identity."""
    if not snapshots:
        return BillingMetricSnapshot()
    names = BillingMetricSnapshot.__dataclass_fields__
    return BillingMetricSnapshot(
        **{
            name: sum(getattr(snapshot, name) for snapshot in snapshots)
            for name in names
        }
    )
