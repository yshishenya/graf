from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Literal


class ReceiptState(StrEnum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    PENDING = "pending"
    FAILED = "failed"


# YooKassa's registration status is deliberately kept separate from the
# customer-facing state.  ``succeeded`` means that the fiscal document was
# registered; it does not mean that an email was delivered.  This boundary is
# important because receipt delivery failures must not roll back a paid
# entitlement.
ReceiptRegistration = Literal["pending", "succeeded", "canceled"]

_REGISTRATION_STATES = frozenset({"pending", "succeeded", "canceled"})
_REGISTRATION_TRANSITIONS: dict[str | None, frozenset[str]] = {
    None: frozenset(_REGISTRATION_STATES),
    "pending": frozenset({"pending", "succeeded", "canceled"}),
    "succeeded": frozenset({"succeeded"}),
    "canceled": frozenset({"canceled"}),
}


def receipt_state_for_registration(status: str | None) -> ReceiptState:
    """Map provider registration truth to a safe presentation state.

    ``None`` is intentionally ``UNKNOWN``: a successful payment may be
    confirmed before YooKassa has created its receipt.  We never infer
    availability from payment success alone.
    """

    if status is None:
        return ReceiptState.UNKNOWN
    if status == "pending":
        return ReceiptState.PENDING
    if status == "succeeded":
        return ReceiptState.AVAILABLE
    if status == "canceled":
        return ReceiptState.FAILED
    raise ValueError("receipt registration status is invalid")


def merge_receipt_registration(
    snapshot: Mapping[str, object],
    *,
    status: str,
) -> tuple[dict[str, object], bool]:
    """Apply one monotonic provider receipt status to an invoice snapshot.

    The invoice snapshot contains only metadata needed by the cabinet.  Raw
    receipt payloads and provider URLs/identifiers never cross this helper.
    The returned boolean is true only for the first transition to
    ``succeeded`` and is suitable for idempotent mandatory-notification
    enqueueing.
    """

    if status not in _REGISTRATION_STATES:
        raise ValueError("receipt registration status is invalid")
    previous = snapshot.get("receipt_registration")
    if previous is not None and previous not in _REGISTRATION_STATES:
        raise ValueError("stored receipt registration status is invalid")
    if status not in _REGISTRATION_TRANSITIONS[previous]:
        raise ValueError("receipt registration is regressive")
    if previous == status:
        return dict(snapshot), False
    updated = dict(snapshot)
    updated["receipt_registration"] = status
    return updated, status == "succeeded"


def receipt_label(state: ReceiptState) -> str:
    return {
        ReceiptState.UNKNOWN: "Чек пока не найден",
        ReceiptState.AVAILABLE: "Чек зарегистрирован",
        ReceiptState.PENDING: "Чек формируется",
        ReceiptState.FAILED: "Чек временно недоступен",
    }[state]
