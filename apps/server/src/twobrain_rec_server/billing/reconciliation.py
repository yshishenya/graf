from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import BillingInvoice, BillingOperation, ObservedProviderRefund

ObservationSource = Literal["webhook", "poll", "registry"]
ReceiptRegistration = Literal["pending", "succeeded", "canceled"]


class ProviderObservationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ProviderScope:
    environment: str
    shop_id: str

    def __post_init__(self) -> None:
        if not 1 <= len(self.environment) <= 32 or not all(
            char.isascii() and (char.isalnum() or char in "-_")
            for char in self.environment
        ):
            raise ProviderObservationError("provider environment is invalid")
        _provider_id(self.shop_id)


@dataclass(frozen=True, slots=True)
class PaymentObservation:
    scope: ProviderScope
    provider_payment_id: str
    amount_minor: int
    currency: str
    status: Literal["pending", "waiting_for_capture", "succeeded", "canceled"]
    provider_created_at: datetime
    receipt_registration: ReceiptRegistration | None = None


@dataclass(frozen=True, slots=True)
class RefundObservation:
    scope: ProviderScope
    provider_refund_id: str
    provider_payment_id: str
    amount_minor: int
    currency: str
    status: Literal["succeeded"]
    provider_created_at: datetime
    receipt_registration: ReceiptRegistration | None = None


@dataclass(frozen=True, slots=True)
class ReceiptObservation:
    scope: ProviderScope
    provider_receipt_id: str
    parent_kind: Literal["payment", "refund"]
    provider_parent_id: str
    status: ReceiptRegistration
    registered_at: datetime | None = None


ProviderObservation = PaymentObservation | RefundObservation | ReceiptObservation


@dataclass(frozen=True, slots=True)
class ObservationRecord:
    observation: ProviderObservation
    sources: frozenset[ObservationSource]
    first_observed_at: datetime
    last_observed_at: datetime


def extract_payment_observation(
    payload: Mapping[str, Any],
    *,
    scope: ProviderScope,
) -> PaymentObservation:
    amount_minor, currency = _money(payload.get("amount"))
    return PaymentObservation(
        scope=scope,
        provider_payment_id=_provider_id(payload.get("id")),
        amount_minor=amount_minor,
        currency=currency,
        status=_payment_status(payload.get("status")),
        provider_created_at=_timestamp(payload.get("created_at"), required=True),
        receipt_registration=_receipt_registration(payload.get("receipt_registration")),
    )


def extract_refund_observation(
    payload: Mapping[str, Any],
    *,
    scope: ProviderScope,
) -> RefundObservation:
    if payload.get("status") != "succeeded":
        raise ProviderObservationError("only a provider-confirmed refund can be observed")
    amount_minor, currency = _money(payload.get("amount"))
    return RefundObservation(
        scope=scope,
        provider_refund_id=_provider_id(payload.get("id")),
        provider_payment_id=_provider_id(payload.get("payment_id")),
        amount_minor=amount_minor,
        currency=currency,
        status="succeeded",
        provider_created_at=_timestamp(payload.get("created_at"), required=True),
        receipt_registration=_receipt_registration(payload.get("receipt_registration")),
    )


def extract_receipt_observation(
    payload: Mapping[str, Any],
    *,
    scope: ProviderScope,
) -> ReceiptObservation:
    parent_kind = payload.get("type")
    if parent_kind not in {"payment", "refund"}:
        raise ProviderObservationError("provider receipt type is invalid")
    parent_field = f"{parent_kind}_id"
    other_field = "refund_id" if parent_kind == "payment" else "payment_id"
    if payload.get(parent_field) is None or payload.get(other_field) is not None:
        raise ProviderObservationError("provider receipt must have exactly one parent")
    status = _receipt_registration(payload.get("status"), required=True)
    registered_at = _timestamp(payload.get("registered_at"), required=False)
    return ReceiptObservation(
        scope=scope,
        provider_receipt_id=_provider_id(payload.get("id")),
        parent_kind=parent_kind,
        provider_parent_id=_provider_id(payload.get(parent_field)),
        status=status,
        registered_at=registered_at,
    )


def observation_key(observation: ProviderObservation) -> tuple[str, str, str, str]:
    if isinstance(observation, PaymentObservation):
        kind, object_id = "payment", observation.provider_payment_id
    elif isinstance(observation, RefundObservation):
        kind, object_id = "refund", observation.provider_refund_id
    else:
        kind, object_id = "receipt", observation.provider_receipt_id
    return observation.scope.environment, observation.scope.shop_id, kind, object_id


class ObservationRecords:
    """Small idempotent projection; durable storage keeps the same unique identity."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str, str], ObservationRecord] = {}

    def record(
        self,
        observation: ProviderObservation,
        *,
        source: ObservationSource,
        observed_at: datetime,
    ) -> Literal["inserted", "duplicate", "updated"]:
        if source not in {"webhook", "poll", "registry"}:
            raise ProviderObservationError("provider observation source is invalid")
        seen_at = _aware_utc(observed_at)
        key = observation_key(observation)
        previous = self._records.get(key)
        if previous is None:
            self._records[key] = ObservationRecord(
                observation,
                frozenset({source}),
                seen_at,
                seen_at,
            )
            return "inserted"

        sources = previous.sources | {source}
        first_seen = min(previous.first_observed_at, seen_at)
        last_seen = max(previous.last_observed_at, seen_at)
        if previous.observation == observation:
            self._records[key] = replace(
                previous,
                sources=frozenset(sources),
                first_observed_at=first_seen,
                last_observed_at=last_seen,
            )
            return "duplicate"
        if not _same_immutable_truth(previous.observation, observation):
            raise ProviderObservationError("provider observation has conflicting immutable truth")
        if not _is_monotonic_update(previous.observation, observation):
            raise ProviderObservationError("provider observation is regressive")
        self._records[key] = ObservationRecord(
            observation,
            frozenset(sources),
            first_seen,
            last_seen,
        )
        return "updated"

    def get(self, observation: ProviderObservation) -> ObservationRecord:
        return self._records[observation_key(observation)]


async def record_observed_refund(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    observation: RefundObservation,
) -> Literal["inserted", "duplicate", "unmatched", "conflict"]:
    """Persist a provider-confirmed refund observation without product mutation."""
    operation = await db.scalar(
        select(BillingOperation)
        .where(BillingOperation.workspace_id == workspace_id, BillingOperation.provider_id == observation.provider_payment_id)
        .with_for_update()
    )
    if operation is None:
        return "unmatched"
    invoice = await db.scalar(
        select(BillingInvoice).where(BillingInvoice.operation_id == operation.id).with_for_update()
    )
    if invoice is None:
        return "unmatched"
    existing = await db.scalar(
        select(ObservedProviderRefund).where(
            ObservedProviderRefund.shop_environment == observation.scope.environment,
            ObservedProviderRefund.provider_refund_id == observation.provider_refund_id,
        ).with_for_update()
    )
    if existing is not None:
        if existing.amount_minor != observation.amount_minor or existing.currency != observation.currency:
            return "conflict"
        return "duplicate"
    db.add(
        ObservedProviderRefund(
            workspace_id=workspace_id,
            invoice_id=invoice.id,
            shop_environment=observation.scope.environment,
            provider_refund_id=observation.provider_refund_id,
            amount_minor=observation.amount_minor,
            currency=observation.currency,
            source="provider_observation",
            status="succeeded",
        )
    )
    await db.flush()
    return "inserted"


@dataclass(frozen=True, slots=True)
class ObservedRefund:
    """Legacy safe projection retained for existing referral helpers."""

    provider_refund_id: str
    invoice_number: str
    amount_minor: int
    currency: str
    status: str
    observed_at: datetime


def refund_observation_is_new(*, provider_refund_id: str, known_ids: set[str]) -> bool:
    return provider_refund_id not in known_ids


def referral_correction_needed(*, observed_status: str, referral_credit_state: str) -> bool:
    return observed_status == "succeeded" and referral_credit_state in {
        "pending",
        "matured",
        "applied",
    }


def _provider_id(value: object) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 160:
        raise ProviderObservationError("provider identifier is invalid")
    if value != value.strip() or not all(
        char.isascii() and (char.isalnum() or char in "-_.") for char in value
    ):
        raise ProviderObservationError("provider identifier is invalid")
    return value


def _money(value: object) -> tuple[int, str]:
    if not isinstance(value, Mapping):
        raise ProviderObservationError("provider amount is invalid")
    raw_amount = value.get("value")
    currency = value.get("currency")
    if not isinstance(raw_amount, str):
        raise ProviderObservationError("provider amount is invalid")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isascii():
        raise ProviderObservationError("provider currency is invalid")
    if currency != currency.upper() or not currency.isalpha():
        raise ProviderObservationError("provider currency is invalid")
    try:
        decimal_amount = Decimal(raw_amount)
    except InvalidOperation as exc:
        raise ProviderObservationError("provider amount is invalid") from exc
    minor_amount = decimal_amount * 100
    if (
        not decimal_amount.is_finite()
        or decimal_amount <= 0
        or minor_amount != minor_amount.to_integral_value()
    ):
        raise ProviderObservationError("provider amount is invalid")
    return int(minor_amount), currency


def _payment_status(
    value: object,
) -> Literal["pending", "waiting_for_capture", "succeeded", "canceled"]:
    if value not in {"pending", "waiting_for_capture", "succeeded", "canceled"}:
        raise ProviderObservationError("provider payment status is invalid")
    return value  # type: ignore[return-value]


def _receipt_registration(
    value: object,
    *,
    required: bool = False,
) -> ReceiptRegistration | None:
    if value is None and not required:
        return None
    if value not in {"pending", "succeeded", "canceled"}:
        raise ProviderObservationError("provider receipt status is invalid")
    return value  # type: ignore[return-value]


def _timestamp(value: object, *, required: bool) -> datetime | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or len(value) > 64:
        raise ProviderObservationError("provider timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProviderObservationError("provider timestamp is invalid") from exc
    return _aware_utc(parsed)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProviderObservationError("provider observation timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _same_immutable_truth(
    previous: ProviderObservation,
    current: ProviderObservation,
) -> bool:
    if type(previous) is not type(current):
        return False
    if isinstance(previous, PaymentObservation) and isinstance(current, PaymentObservation):
        return (
            previous.scope,
            previous.provider_payment_id,
            previous.amount_minor,
            previous.currency,
            previous.provider_created_at,
        ) == (
            current.scope,
            current.provider_payment_id,
            current.amount_minor,
            current.currency,
            current.provider_created_at,
        )
    if isinstance(previous, RefundObservation) and isinstance(current, RefundObservation):
        return (
            previous.scope,
            previous.provider_refund_id,
            previous.provider_payment_id,
            previous.amount_minor,
            previous.currency,
            previous.provider_created_at,
        ) == (
            current.scope,
            current.provider_refund_id,
            current.provider_payment_id,
            current.amount_minor,
            current.currency,
            current.provider_created_at,
        )
    if isinstance(previous, ReceiptObservation) and isinstance(current, ReceiptObservation):
        return (
            previous.scope,
            previous.provider_receipt_id,
            previous.parent_kind,
            previous.provider_parent_id,
        ) == (
            current.scope,
            current.provider_receipt_id,
            current.parent_kind,
            current.provider_parent_id,
        )
    return False


def _is_monotonic_update(previous: ProviderObservation, current: ProviderObservation) -> bool:
    if isinstance(previous, PaymentObservation) and isinstance(current, PaymentObservation):
        transitions = {
            "pending": {"pending", "waiting_for_capture", "succeeded", "canceled"},
            "waiting_for_capture": {"waiting_for_capture", "succeeded", "canceled"},
            "succeeded": {"succeeded"},
            "canceled": {"canceled"},
        }
        return current.status in transitions[previous.status] and _receipt_state_advances(
            previous.receipt_registration,
            current.receipt_registration,
        )
    if isinstance(previous, RefundObservation) and isinstance(current, RefundObservation):
        return _receipt_state_advances(
            previous.receipt_registration,
            current.receipt_registration,
        )
    if isinstance(previous, ReceiptObservation) and isinstance(current, ReceiptObservation):
        return _receipt_state_advances(previous.status, current.status) and (
            previous.registered_at is None or previous.registered_at == current.registered_at
        )
    return False


def _receipt_state_advances(
    previous: ReceiptRegistration | None,
    current: ReceiptRegistration | None,
) -> bool:
    if previous == current:
        return True
    if previous is None:
        return True
    return previous == "pending" and current in {"succeeded", "canceled"}
