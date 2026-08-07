from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum


class OperationOutcome(StrEnum):
    SUCCESS = "success"
    CANCELED = "canceled"
    UNKNOWN = "unknown"


class BillingEmergencyStop(RuntimeError):
    pass


CHECKOUT_BLOCKING_STATES = frozenset({"scheduled", "provider_pending", "unknown", "method_required"})


def blocks_new_checkout(operation_state: str) -> bool:
    """Unknown payment truth must reconcile before another charge is allowed."""
    return operation_state in CHECKOUT_BLOCKING_STATES


def require_billing_enabled(*, checkout_enabled: bool, emergency_stop: bool) -> None:
    if emergency_stop:
        raise BillingEmergencyStop("billing operations are temporarily stopped")
    if not checkout_enabled:
        raise BillingEmergencyStop("billing checkout is disabled")


def classify_provider_outcome(*, status_code: int | None, provider_status: str | None) -> OperationOutcome:
    if status_code is None or status_code >= 500:
        return OperationOutcome.UNKNOWN
    if provider_status in {"succeeded", "paid"}:
        return OperationOutcome.SUCCESS
    if provider_status in {"canceled", "cancelled"}:
        return OperationOutcome.CANCELED
    return OperationOutcome.UNKNOWN


def provider_key_is_expired(*, expires_at: datetime | None, now: datetime | None = None) -> bool:
    if expires_at is None:
        return False
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return expires_at <= current
