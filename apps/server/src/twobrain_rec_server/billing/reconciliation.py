from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.referral_rewards import reverse_credit_for_payment
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    ObservedProviderRefund,
    WorkspaceSubscription,
)

ObservationSource = Literal["webhook", "poll", "registry"]
ReceiptRegistration = Literal["pending", "succeeded", "canceled"]
ReceiptObservationResult = Literal["inserted", "duplicate", "updated", "unmatched", "conflict"]

_MAX_RECEIPT_OBSERVATIONS = 16


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


def saved_bank_card_confirmed(payload: Mapping[str, Any]) -> bool:
    """Return only the safe capability bit; provider method identifiers never enter the ledger."""
    method = payload.get("payment_method")
    return isinstance(method, Mapping) and method.get("type") == "bank_card" and method.get("saved") is True


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


def merge_receipt_observation_snapshot(
    snapshot: Mapping[str, Any],
    observation: ReceiptObservation,
    *,
    source: ObservationSource,
    observed_at: datetime,
) -> tuple[dict[str, Any], ReceiptObservationResult]:
    """Merge safe receipt truth without allowing an out-of-order regression.

    Invoices predate a dedicated receipt table, so receipt observations live in
    a bounded metadata-only projection on the invoice.  The provider payload is
    never copied: only scoped identifiers, state and timestamps survive.  A
    small map allows payment and refund receipts to coexist while its hard cap
    prevents provider-controlled metadata growth.
    """
    if source not in {"webhook", "poll", "registry"}:
        raise ProviderObservationError("provider observation source is invalid")
    seen_at = _aware_utc(observed_at)
    if not isinstance(snapshot, Mapping):
        raise ProviderObservationError("invoice snapshot is invalid")

    merged = dict(snapshot)
    raw_records = merged.get("receipt_observations")
    records: dict[str, dict[str, Any]] = {}
    if raw_records is not None:
        if not isinstance(raw_records, Mapping):
            raise ProviderObservationError("receipt observation projection is invalid")
        for key, value in raw_records.items():
            if isinstance(key, str) and isinstance(value, Mapping):
                records[key] = dict(value)

    scope_key = _receipt_observation_key(observation)
    current = records.get(scope_key)
    legacy_status = merged.get("receipt_registration")
    if legacy_status is not None and legacy_status not in {"pending", "succeeded", "canceled"}:
        raise ProviderObservationError("invoice receipt status is invalid")
    if current is None and len(records) >= _MAX_RECEIPT_OBSERVATIONS:
        return merged, "conflict"
    if current is not None:
        if (
            current.get("provider_receipt_id") != observation.provider_receipt_id
            or current.get("parent_kind") != observation.parent_kind
            or current.get("provider_parent_id") != observation.provider_parent_id
            or current.get("environment") != observation.scope.environment
            or current.get("shop_id") != observation.scope.shop_id
        ):
            return merged, "conflict"
        previous_status = current.get("status")
        if previous_status not in {"pending", "succeeded", "canceled"}:
            raise ProviderObservationError("receipt observation status is invalid")
        if not _receipt_state_advances(previous_status, observation.status):
            return merged, "conflict"
        if previous_status == observation.status:
            return merged, "duplicate"

    # Legacy snapshots can have a status but no provider receipt identity.  Do
    # not let a late weaker signal regress the user-visible state while the
    # identity is being backfilled.
    if (
        observation.parent_kind == "payment"
        and current is None
        and isinstance(legacy_status, str)
        and not _receipt_state_advances(legacy_status, observation.status)
    ):
        return merged, "conflict"

    records[scope_key] = {
        "provider_receipt_id": observation.provider_receipt_id,
        "parent_kind": observation.parent_kind,
        "provider_parent_id": observation.provider_parent_id,
        "environment": observation.scope.environment,
        "shop_id": observation.scope.shop_id,
        "status": observation.status,
        "registered_at": observation.registered_at.isoformat() if observation.registered_at else None,
        "source": source,
        "observed_at": seen_at.isoformat(),
    }
    merged["receipt_observations"] = records
    # Keep the existing UI projection, but only move it forward.
    if observation.parent_kind == "payment" and (
        legacy_status is None or _receipt_state_advances(legacy_status, observation.status)
    ):
        merged["receipt_registration"] = observation.status
    return merged, "inserted" if current is None else "updated"


def _receipt_observation_key(observation: ReceiptObservation) -> str:
    return ":".join(
        (
            observation.scope.environment,
            observation.scope.shop_id,
            observation.provider_receipt_id,
        )
    )


async def record_observed_receipt(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    observation: ReceiptObservation,
    source: ObservationSource = "webhook",
    observed_at: datetime | None = None,
) -> ReceiptObservationResult:
    """Persist bounded receipt truth without changing entitlement or refunds."""
    invoice: BillingInvoice | None
    if observation.parent_kind == "payment":
        operation = await db.scalar(
            select(BillingOperation)
            .where(
                BillingOperation.workspace_id == workspace_id,
                BillingOperation.provider_id == observation.provider_parent_id,
            )
            .with_for_update()
        )
        invoice = None
        if operation is not None:
            invoice = await db.scalar(
                select(BillingInvoice)
                .where(
                    BillingInvoice.workspace_id == workspace_id,
                    BillingInvoice.operation_id == operation.id,
                )
                .with_for_update()
            )
    else:
        observed_refund = await db.scalar(
            select(ObservedProviderRefund)
            .where(
                ObservedProviderRefund.workspace_id == workspace_id,
                ObservedProviderRefund.shop_environment == observation.scope.environment,
                ObservedProviderRefund.provider_refund_id == observation.provider_parent_id,
            )
            .with_for_update()
        )
        invoice = None
        if observed_refund is not None:
            invoice = await db.scalar(
                select(BillingInvoice)
                .where(
                    BillingInvoice.workspace_id == workspace_id,
                    BillingInvoice.id == observed_refund.invoice_id,
                )
                .with_for_update()
            )
    if invoice is None:
        return "unmatched"
    merged, result = merge_receipt_observation_snapshot(
        invoice.plan_snapshot,
        observation,
        source=source,
        observed_at=observed_at or datetime.now(UTC),
    )
    if result in {"inserted", "updated"}:
        invoice.plan_snapshot = merged
        await db.flush()
    return result


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
    if (
        observation.amount_minor <= 0
        or observation.amount_minor > invoice.amount_minor
        or observation.currency != invoice.currency
    ):
        return "conflict"
    existing = await db.scalar(
        select(ObservedProviderRefund).where(
            ObservedProviderRefund.workspace_id == workspace_id,
            ObservedProviderRefund.shop_environment == observation.scope.environment,
            ObservedProviderRefund.provider_refund_id == observation.provider_refund_id,
        ).with_for_update()
    )
    if existing is not None:
        if existing.amount_minor != observation.amount_minor or existing.currency != observation.currency:
            return "conflict"
        return "duplicate"
    refunded_total = await db.scalar(
        select(func.coalesce(func.sum(ObservedProviderRefund.amount_minor), 0)).where(
            ObservedProviderRefund.invoice_id == invoice.id,
            ObservedProviderRefund.currency == invoice.currency,
            ObservedProviderRefund.status == "succeeded",
        )
    )
    if int(refunded_total or 0) + observation.amount_minor > invoice.amount_minor:
        return "conflict"
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
    subscription = await db.scalar(
        select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace_id)
    )
    await reverse_credit_for_payment(
        db,
        workspace_id=workspace_id,
        provider_payment_id=observation.provider_payment_id,
        now=observation.provider_created_at,
        invitee_user_id=subscription.billing_owner_id if subscription is not None else None,
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
