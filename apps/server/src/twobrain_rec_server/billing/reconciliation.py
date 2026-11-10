from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.provider_events import validate_provider_identifier
from twobrain_rec_server.billing.receipts import (
    ReceiptRegistration,
    confirm_payment_receipt_timing,
    confirm_receipt_timing,
    merge_receipt_registration,
    payment_receipt_record,
    receipt_observation_records,
)
from twobrain_rec_server.billing.referral_rewards import reverse_credit_for_payment
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    BillingReceiptIdentity,
    ObservedProviderRefund,
)

ObservationSource = Literal["webhook", "poll", "registry"]
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
            char.isascii() and (char.isalnum() or char in "-_") for char in self.environment
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
    # Our own operation id, echoed by the provider. It lets a payment be matched
    # even when the create-payment response never reached us.
    operation_id: UUID | None = None
    captured_at: datetime | None = None


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
    related_payment_id: str | None = None


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
    try:
        receipt_registration = _receipt_registration(payload.get("receipt_registration"))
    except ProviderObservationError:
        # Fiscal registration is independent from confirmation of the payment.
        receipt_registration = None
    return PaymentObservation(
        scope=scope,
        provider_payment_id=_provider_id(payload.get("id")),
        amount_minor=amount_minor,
        currency=currency,
        status=_payment_status(payload.get("status")),
        provider_created_at=_timestamp(payload.get("created_at"), required=True),
        receipt_registration=receipt_registration,
        operation_id=_operation_id(payload.get("metadata")),
        captured_at=_timestamp(payload.get("captured_at"), required=False),
    )


def validate_renewal_payment(
    payment: Mapping[str, Any], *, operation: BillingOperation, invoice: BillingInvoice
) -> str:
    """Bind authoritative provider truth to the exact local renewal invoice."""
    if (
        operation.kind != "renewal"
        or invoice.operation_id != operation.id
        or invoice.workspace_id != operation.workspace_id
    ):
        raise ProviderObservationError("renewal invoice binding does not match")
    if not operation.provider_id or payment.get("id") != operation.provider_id:
        raise ProviderObservationError("provider payment reference does not match")
    metadata = payment.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ProviderObservationError("provider payment metadata is missing")
    if metadata.get("workspace_id") != str(operation.workspace_id):
        raise ProviderObservationError("provider payment workspace does not match")
    if metadata.get("operation_id") != str(operation.id):
        raise ProviderObservationError("provider payment operation does not match")
    amount_minor, currency = _money(payment.get("amount"))
    if amount_minor != invoice.amount_minor or currency != invoice.currency:
        raise ProviderObservationError("provider payment amount does not match")
    status = payment.get("status")
    if not isinstance(status, str) or not status:
        raise ProviderObservationError("provider payment status is missing")
    return status


def validate_purchase_payment(
    payment: Mapping[str, Any],
    *,
    operation: BillingOperation,
    invoice: BillingInvoice,
    scope: ProviderScope,
) -> str:
    """Verify a GET result before any money, promo or service projection.

    Old operations did not persist a shop binding. They can only be observed
    through the configured shop; present metadata is still checked. Every new
    schema-2 purchase must carry the complete immutable binding.
    """
    if invoice.operation_id != operation.id or invoice.workspace_id != operation.workspace_id:
        raise ProviderObservationError("purchase invoice binding does not match")
    if not operation.provider_id or payment.get("id") != operation.provider_id:
        raise ProviderObservationError("provider payment reference does not match")
    amount, currency = _money(payment.get("amount"))
    if amount != invoice.amount_minor or currency != invoice.currency:
        raise ProviderObservationError("provider payment amount does not match")
    strict = operation.request_snapshot.get("purchase_schema") == 2
    metadata = payment.get("metadata")
    if strict or metadata is not None:
        if not isinstance(metadata, Mapping):
            raise ProviderObservationError("provider metadata is missing")
        for key, expected in {
            "workspace_id": str(operation.workspace_id),
            "operation_id": str(operation.id),
            "invoice_number": invoice.safe_number,
        }.items():
            if (strict or key in metadata) and metadata.get(key) != expected:
                raise ProviderObservationError("provider metadata binding does not match")
    recipient = payment.get("recipient")
    if (strict or recipient is not None) and (
        not isinstance(recipient, Mapping) or recipient.get("account_id") != scope.shop_id
    ):
        raise ProviderObservationError("provider shop does not match")
    if (strict or "test" in payment) and payment.get("test") is not (scope.environment == "test"):
        raise ProviderObservationError("provider environment does not match")
    if strict and (
        operation.request_snapshot.get("provider_shop_id") != scope.shop_id
        or operation.request_snapshot.get("provider_environment") != scope.environment
    ):
        raise ProviderObservationError("operation shop binding does not match")
    return _payment_status(payment.get("status"))


def confirm_receipt_payment_binding(
    operation: BillingOperation,
    invoice: BillingInvoice,
    scope: ProviderScope,
    *,
    verified_payment: Mapping[str, Any] | None = None,
) -> bool:
    """Require a stored binding, or save it after a validated, complete payment GET."""
    request = operation.request_snapshot
    snapshot = invoice.plan_snapshot
    if (
        not isinstance(request, Mapping)
        or not isinstance(snapshot, Mapping)
        or not operation.provider_id
        or invoice.operation_id != operation.id
        or invoice.workspace_id != operation.workspace_id
    ):
        return False
    expected = {"provider_environment": scope.environment, "provider_shop_id": scope.shop_id}
    if any(key in request and request[key] != value for key, value in expected.items()):
        return False
    complete = all(key in request for key in expected)
    if request.get("purchase_schema") == 2 and not complete:
        return False
    binding = {
        "operation_id": str(operation.id),
        "workspace_id": str(operation.workspace_id),
        "payment_id": operation.provider_id,
        "environment": scope.environment,
        "shop_id": scope.shop_id,
    }
    key = "receipt_payment_binding"
    if key in snapshot and snapshot[key] != binding:
        return False
    if verified_payment is None:
        return complete or key in snapshot
    recipient = verified_payment.get("recipient")
    if (
        not isinstance(recipient, Mapping)
        or recipient.get("account_id") != scope.shop_id
        or verified_payment.get("test") is not (scope.environment == "test")
    ):
        return False
    if not complete and key not in snapshot:
        try:
            payment_receipt_record(
                receipt_observation_records(snapshot),
                (scope.environment, scope.shop_id, operation.provider_id),
            )
        except ValueError:
            return False
        invoice.plan_snapshot = {**snapshot, key: binding}
    return True


def _operation_id(metadata: object) -> UUID | None:
    """Read our operation id from provider metadata, ignoring anything malformed."""
    if not isinstance(metadata, Mapping):
        return None
    raw = metadata.get("operation_id")
    if not raw:
        return None
    try:
        return UUID(str(raw))
    except (ValueError, TypeError):
        return None


def saved_bank_card_confirmed(payload: Mapping[str, Any]) -> bool:
    """Return only the safe capability bit; provider method identifiers never enter the ledger."""
    method = payload.get("payment_method")
    return (
        isinstance(method, Mapping)
        and method.get("type") == "bank_card"
        and method.get("saved") is True
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
    if not isinstance(parent_kind, str) or parent_kind not in {"payment", "refund"}:
        raise ProviderObservationError("provider receipt type is invalid")
    parent_field = f"{parent_kind}_id"
    other_field = "refund_id" if parent_kind == "payment" else "payment_id"
    if payload.get(parent_field) is None or (
        parent_kind == "payment" and payload.get(other_field) is not None
    ):
        raise ProviderObservationError("provider receipt parent is invalid")
    status = _receipt_registration(payload.get("status"), required=True)
    registered_at = _timestamp(payload.get("registered_at"), required=False)
    return ReceiptObservation(
        scope=scope,
        provider_receipt_id=_provider_id(payload.get("id")),
        parent_kind=parent_kind,
        provider_parent_id=_provider_id(payload.get(parent_field)),
        status=status,
        registered_at=registered_at,
        related_payment_id=_provider_id(payload["payment_id"])
        if parent_kind == "refund" and payload.get("payment_id") is not None
        else None,
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
    try:
        records = receipt_observation_records(snapshot)
    except ValueError:
        return merged, "conflict"

    scope_key = _receipt_observation_key(observation)
    current = records.get(scope_key)
    if observation.parent_kind == "payment":
        if any(key != scope_key and record["parent_kind"] == "payment" for key, record in records.items()):
            return merged, "conflict"
        try:
            merged, _ = merge_receipt_registration(
                snapshot,
                status=observation.status,
                payment_binding=(
                    observation.scope.environment, observation.scope.shop_id, observation.provider_parent_id
                ),
            )
        except ValueError:
            return dict(snapshot), "conflict"
    if current is None and len(records) >= _MAX_RECEIPT_OBSERVATIONS:
        return dict(snapshot), "conflict"
    if current is not None:
        if (
            current.get("provider_receipt_id") != observation.provider_receipt_id
            or current.get("parent_kind") != observation.parent_kind
            or current.get("provider_parent_id") != observation.provider_parent_id
            or current.get("environment") != observation.scope.environment
            or current.get("shop_id") != observation.scope.shop_id
        ):
            return dict(snapshot), "conflict"
        previous_status = current.get("status")
        if previous_status not in ("pending", "succeeded", "canceled"):
            raise ProviderObservationError("receipt observation status is invalid")
        if not _receipt_state_advances(previous_status, observation.status):
            return dict(snapshot), "conflict"
        if previous_status == observation.status and (
            observation.parent_kind == "refund"
            or observation.registered_at is None
            or current.get("registered_at") is not None
        ):
            return merged, "duplicate" if merged == snapshot else "updated"

    records[scope_key] = {
        **(current or {}),
        "provider_receipt_id": observation.provider_receipt_id,
        "parent_kind": observation.parent_kind,
        "provider_parent_id": observation.provider_parent_id,
        "environment": observation.scope.environment,
        "shop_id": observation.scope.shop_id,
        "status": observation.status,
        "registered_at": observation.registered_at.isoformat()
        if observation.registered_at
        else (current or {}).get("registered_at"),
        "source": source,
        "observed_at": seen_at.isoformat(),
    }
    merged["receipt_observations"] = records
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
) -> tuple[ReceiptObservationResult, bool]:
    """Persist bounded receipt truth without changing entitlement or refunds."""
    invoice: BillingInvoice | None
    refund_scope_confirmed = False
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
        return "unmatched", False
    if observation.parent_kind == "refund":
        operation = await db.scalar(
            select(BillingOperation).where(
                BillingOperation.workspace_id == workspace_id,
                BillingOperation.id == invoice.operation_id,
            )
        )
        if operation is None:
            return "unmatched", False
        if (
            observation.related_payment_id is not None
            and operation.provider_id != observation.related_payment_id
        ):
            raise ProviderObservationError("provider receipt payment conflicts with refund invoice")
    if not confirm_receipt_payment_binding(operation, invoice, observation.scope):
        return "conflict", False
    if observation.parent_kind == "refund":
        refund_scope_confirmed = bool(
            operation.provider_id
            and observed_refund is not None
            and observed_refund.status == "succeeded"
        )
    previous_registration = invoice.plan_snapshot.get("receipt_registration")
    merged, result = merge_receipt_observation_snapshot(
        invoice.plan_snapshot,
        observation,
        source=source,
        observed_at=observed_at or datetime.now(UTC),
    )
    if result == "conflict":
        return "conflict", False

    identity = {
        "environment": observation.scope.environment,
        "shop_id": observation.scope.shop_id,
        "provider_receipt_id": observation.provider_receipt_id,
        "workspace_id": workspace_id,
        "invoice_id": invoice.id,
        "parent_kind": observation.parent_kind,
        "provider_parent_id": observation.provider_parent_id,
    }
    claimed = await db.scalar(
        insert(BillingReceiptIdentity)
        .values(**identity)
        .on_conflict_do_nothing(index_elements=["environment", "shop_id", "provider_receipt_id"])
        .returning(BillingReceiptIdentity.invoice_id)
    )
    if claimed is None and await db.scalar(
        select(BillingReceiptIdentity.invoice_id).filter_by(**identity)
    ) is None:
        return "conflict", False

    if observation.parent_kind == "payment":
        await confirm_payment_receipt_timing(db, invoice.plan_snapshot, merged)
    elif refund_scope_confirmed:
        key = _receipt_observation_key(observation)
        receipts = merged["receipt_observations"]
        previous = receipt_observation_records(invoice.plan_snapshot).get(key, {})
        entry = receipts[key]
        updated = await confirm_receipt_timing(
            db, entry, status=observation.status, was_pending=previous.get("status") == "pending",
        )
        if updated != entry:
            merged["receipt_observations"] = {**receipts, key: updated}
    if merged != invoice.plan_snapshot:
        invoice.plan_snapshot = merged
        await db.flush()
    return result, (
        observation.parent_kind == "payment"
        and previous_registration != "succeeded"
        and merged.get("receipt_registration") == "succeeded"
    )


async def record_observed_refund(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    observation: RefundObservation,
) -> Literal["inserted", "duplicate", "unmatched", "conflict"]:
    """Persist a provider-confirmed refund observation without product mutation."""
    operation = await db.scalar(
        select(BillingOperation)
        .where(
            BillingOperation.workspace_id == workspace_id,
            BillingOperation.provider_id == observation.provider_payment_id,
        )
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
        select(ObservedProviderRefund)
        .where(
            ObservedProviderRefund.workspace_id == workspace_id,
            ObservedProviderRefund.shop_environment == observation.scope.environment,
            ObservedProviderRefund.provider_refund_id == observation.provider_refund_id,
        )
        .with_for_update()
    )
    if existing is not None:
        if (
            existing.amount_minor != observation.amount_minor
            or existing.currency != observation.currency
        ):
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
    invitee_user_id = None
    snapshot = invoice.plan_snapshot
    if isinstance(snapshot, Mapping):
        actor = snapshot.get("billing_actor_user_id")
        if isinstance(actor, str):
            try:
                invitee_user_id = UUID(actor)
            except ValueError:
                invitee_user_id = None
    await reverse_credit_for_payment(
        db,
        workspace_id=workspace_id,
        provider_payment_id=observation.provider_payment_id,
        now=observation.provider_created_at,
        invitee_user_id=invitee_user_id,
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
    try:
        return validate_provider_identifier(value)
    except ValueError:
        raise ProviderObservationError("provider identifier is invalid") from None


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
    if not isinstance(value, str) or value not in {
        "pending", "waiting_for_capture", "succeeded", "canceled"
    }:
        raise ProviderObservationError("provider payment status is invalid")
    return value  # type: ignore[return-value]


def _receipt_registration(
    value: object,
    *,
    required: bool = False,
) -> ReceiptRegistration | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or value not in {"pending", "succeeded", "canceled"}:
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
