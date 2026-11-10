from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Literal

from sqlalchemy import select

from twobrain_rec_server.db.models import ExternalIdentity


async def verified_receipt_contact(db, user_id):
    if db is None:
        return None
    return await db.scalar(
        select(ExternalIdentity.email)
        .where(
            ExternalIdentity.user_id == user_id,
            ExternalIdentity.is_active.is_(True),
            ExternalIdentity.is_verified.is_(True),
            ExternalIdentity.email.is_not(None),
        )
        .order_by(ExternalIdentity.created_at.asc())
        .limit(1)
    )


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


def receipt_observation_records(
    snapshot: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    raw = snapshot.get("receipt_observations")
    if raw is None:
        return {}
    if not isinstance(raw, Mapping) or any(
        not isinstance(key, str)
        or not isinstance(value, Mapping)
        or value.get("parent_kind") not in ("payment", "refund")
        for key, value in raw.items()
    ):
        raise ValueError("receipt observation projection is invalid")
    return dict(raw)


def merge_receipt_registration(
    snapshot: Mapping[str, object],
    *,
    status: str,
    payment_binding: tuple[str, str, str] | None = None,
) -> tuple[dict[str, object], bool]:
    """Advance the payment receipt and its existing identity as one transition.

    The binding is the verified (environment, shop, payment ID). A payment GET
    supplies the registration status but cannot replace the receipt ID or time.
    """
    if not isinstance(snapshot, Mapping):
        raise ValueError("invoice snapshot is invalid")
    if not isinstance(status, str) or status not in _REGISTRATION_STATES:
        raise ValueError("receipt registration status is invalid")

    def check_transition(previous: object) -> None:
        if previous is not None and (
            not isinstance(previous, str) or previous not in _REGISTRATION_STATES
        ):
            raise ValueError("stored receipt registration status is invalid")
        if status not in _REGISTRATION_TRANSITIONS[previous]:
            raise ValueError("receipt registration is regressive")

    previous = snapshot.get("receipt_registration")
    check_transition(previous)
    records = receipt_observation_records(snapshot)
    payment = [(key, entry) for key, entry in records.items() if entry["parent_kind"] == "payment"]
    if len(payment) > 1:
        raise ValueError("multiple receipt identities for payment")

    updated = dict(snapshot)
    if payment:
        key, entry = payment[0]
        receipt_id = entry.get("provider_receipt_id")
        if (
            payment_binding is None
            or payment_binding != (entry.get("environment"), entry.get("shop_id"), entry.get("provider_parent_id"))
            or not isinstance(receipt_id, str)
            or not receipt_id
            or key != ":".join((*payment_binding[:2], receipt_id))
        ):
            raise ValueError("payment receipt binding conflicts")
        stored_status = entry.get("status")
        if stored_status is None:
            raise ValueError("stored receipt registration status is invalid")
        check_transition(stored_status)
        if stored_status != status:
            updated["receipt_observations"] = {**records, key: {**entry, "status": status}}

    updated["receipt_registration"] = status
    return updated, previous != status and status == "succeeded"


def receipt_label(state: ReceiptState) -> str:
    return {
        ReceiptState.UNKNOWN: "Чек пока не найден",
        ReceiptState.AVAILABLE: "Чек зарегистрирован",
        ReceiptState.PENDING: "Чек формируется",
        ReceiptState.FAILED: "Чек временно недоступен",
    }[state]
