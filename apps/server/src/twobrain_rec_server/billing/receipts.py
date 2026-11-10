from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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


def payment_receipt_record(
    records: Mapping[str, Mapping[str, object]],
    payment_binding: tuple[str, str, str] | None,
) -> tuple[str, Mapping[str, object]] | None:
    payment = [(key, entry) for key, entry in records.items() if entry["parent_kind"] == "payment"]
    if not payment:
        return None
    if len(payment) > 1:
        raise ValueError("multiple receipt identities for payment")
    key, entry = payment[0]
    receipt_id = entry.get("provider_receipt_id")
    if (
        payment_binding is None
        or payment_binding != (
            entry.get("environment"), entry.get("shop_id"), entry.get("provider_parent_id")
        )
        or not isinstance(receipt_id, str)
        or not receipt_id
        or key != ":".join((*payment_binding[:2], receipt_id))
    ):
        raise ValueError("payment receipt binding conflicts")
    return key, entry


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
    payment = payment_receipt_record(records, payment_binding)
    updated = dict(snapshot)
    if payment is not None:
        key, entry = payment
        stored_status = entry.get("status")
        if stored_status is None:
            raise ValueError("stored receipt registration status is invalid")
        check_transition(stored_status)
        if stored_status != status:
            updated["receipt_observations"] = {**records, key: {**entry, "status": status}}

    updated["receipt_registration"] = status
    return updated, previous != status and status == "succeeded"


async def confirm_receipt_timing(
    db: AsyncSession,
    timing: Mapping[str, object],
    *,
    status: str,
    was_pending: bool,
) -> Mapping[str, object]:
    if not isinstance(timing, Mapping):
        raise ValueError("receipt timing is invalid")
    if status == "pending" and "pending_overdue" not in timing:
        confirmed_at = (await db.scalar(select(func.clock_timestamp()))).astimezone(UTC)
        first = timing.get("first_confirmed_pending_at")
        if first is None:
            return {
                **timing,
                "first_confirmed_pending_at": confirmed_at.isoformat(),
                "legacy_pending_unknown": was_pending,
            }
        if not isinstance(first, str):
            raise ValueError("receipt pending timestamp is invalid")
        try:
            first_at = datetime.fromisoformat(first)
        except ValueError:
            raise ValueError("receipt pending timestamp is invalid") from None
        if first_at.utcoffset() != timedelta(0):
            raise ValueError("receipt pending timestamp must be UTC")
        if confirmed_at < first_at:
            raise ValueError("receipt confirmation clock moved backwards")
        if confirmed_at - first_at >= timedelta(hours=72):
            return {
                **timing,
                "pending_overdue": {
                    "detected_at": confirmed_at.isoformat(),
                    "due_at": (first_at + timedelta(hours=72)).isoformat(),
                    "freshness": "confirmed",
                },
            }
    if status == "canceled" and "canceled" not in timing:
        confirmed_at = await db.scalar(select(func.clock_timestamp()))
        timestamp = confirmed_at.astimezone(UTC).isoformat()
        return {
            **timing,
            "canceled": {"detected_at": timestamp, "due_at": timestamp, "freshness": "confirmed"},
        }
    return timing


async def confirm_payment_receipt_timing(
    db: AsyncSession,
    previous: Mapping[str, object],
    merged: dict[str, object],
) -> None:
    key = "receipt_registration_timing"
    timing = previous.get(key, {})
    status = merged["receipt_registration"]
    if status == "succeeded" and not isinstance(timing, Mapping):
        return
    was_pending = previous.get("receipt_registration") == "pending" or any(
        row.get("parent_kind") == "payment" and row.get("status") == "pending"
        for row in receipt_observation_records(previous).values()
    )
    updated = await confirm_receipt_timing(
        db, timing, status=status, was_pending=was_pending,
    )
    if updated != timing:
        merged[key] = updated


async def merge_confirmed_receipt_registration(
    db: AsyncSession,
    snapshot: Mapping[str, object],
    *,
    status: str,
    payment_binding: tuple[str, str, str] | None,
) -> tuple[dict[str, object], bool]:
    merged, available = merge_receipt_registration(
        snapshot, status=status, payment_binding=payment_binding,
    )
    if payment_binding is not None:
        await confirm_payment_receipt_timing(db, snapshot, merged)
    return merged, available


def receipt_label(state: ReceiptState) -> str:
    return {
        ReceiptState.UNKNOWN: "Чек пока не найден",
        ReceiptState.AVAILABLE: "Чек зарегистрирован",
        ReceiptState.PENDING: "Чек формируется",
        ReceiptState.FAILED: "Чек временно недоступен",
    }[state]
