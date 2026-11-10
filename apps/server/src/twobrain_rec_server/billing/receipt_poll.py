"""Bounded observation of fiscal receipts, independent of payment settlement."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.database import require_billing_maintenance_database
from twobrain_rec_server.billing.events import enqueue_billing_notification
from twobrain_rec_server.billing.notifications import BillingNotification
from twobrain_rec_server.billing.provider_events import validate_provider_identifier
from twobrain_rec_server.billing.receipts import (
    merge_confirmed_receipt_registration,
    payment_receipt_record,
    receipt_observation_records,
    receipt_utc_timestamp,
    record_receipt_overdue,
)
from twobrain_rec_server.billing.reconciliation import (
    ProviderObservationError,
    ProviderScope,
    confirm_receipt_payment_binding,
    extract_payment_observation,
    extract_receipt_observation,
    record_observed_receipt,
    validate_purchase_payment,
)
from twobrain_rec_server.billing.yookassa import (
    YooKassaClient,
    YooKassaConfigurationError,
    YooKassaProviderError,
    provider_environment,
)
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    BillingReceiptIdentity,
    ObservedProviderRefund,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)

if TYPE_CHECKING:
    from twobrain_rec_server.config import Settings


_ATTEMPT = "last_reserved_poll_at"
_RESULT = "last_poll_result"
_PAYMENT_TIMING = "receipt_registration_timing"
_INTERVAL = timedelta(seconds=300)
_MIN_AGE = timedelta(hours=24)
_MAX_GET = 10
_PASS_SECONDS = 60
_GET_SECONDS = 5

# One logical payment row (even after it gets an ID), and one row per refund receipt.
_CANDIDATES = text("""
    WITH candidates AS (
      SELECT i.id, i.operation_id, i.workspace_id, c.key,
             c.timing ->> 'last_reserved_poll_at' AS attempt
      FROM billing_invoices i
      JOIN billing_operations o ON o.id = i.operation_id AND o.workspace_id = i.workspace_id
      JOIN workspaces w ON w.id = i.workspace_id AND w.kind = 'personal'
      JOIN workspace_memberships m ON m.workspace_id = w.id AND m.user_id = w.owner_user_id
                                   AND m.role = 'owner' AND m.status = 'active'
      CROSS JOIN LATERAL (
        SELECT '' AS key, i.plan_snapshot -> 'receipt_registration_timing' AS timing
        WHERE i.plan_snapshot ->> 'receipt_registration' = 'pending'
        UNION ALL
        SELECT entry.key, entry.value::json
        FROM jsonb_each(CASE
          WHEN json_typeof(i.plan_snapshot -> 'receipt_observations') = 'object'
          THEN CAST(i.plan_snapshot -> 'receipt_observations' AS jsonb)
          ELSE '{}'::jsonb END) entry
        WHERE entry.value ->> 'parent_kind' = 'refund' AND entry.value ->> 'status' = 'pending'
      ) c
      WHERE i.status = 'succeeded'
        AND o.state IN ('succeeded', 'succeeded_projected', 'succeeded_refused')
        AND o.created_at <= :oldest
    )
    SELECT id, operation_id, workspace_id, key, coalesce(attempt, '') AS attempt
    FROM candidates
    WHERE CASE
      WHEN pg_input_is_valid(attempt, 'timestamp with time zone')
      THEN NOT (CAST(attempt AS timestamptz) > :retry_after
                AND CAST(attempt AS timestamptz) <= :now)
      ELSE true
    END
      AND (coalesce(attempt, ''), id, key) > (:after_attempt, :after_id, :after_key)
    ORDER BY coalesce(attempt, ''), id, key
    LIMIT 32
""")


@dataclass(frozen=True, slots=True)
class _Candidate:
    id: UUID
    operation_id: UUID
    workspace_id: UUID
    key: str
    attempt: str


@dataclass(slots=True)
class _LockedReceipt:
    invoice: BillingInvoice
    operation: BillingOperation
    key: str
    receipt_id: str | None
    parent_id: str
    timing: Mapping[str, object]

    @property
    def kind(self) -> str:
        return "refund" if self.key else "payment"

    def write_timing(self, timing: Mapping[str, object]) -> None:
        snapshot = self.invoice.plan_snapshot
        if self.key:
            records = receipt_observation_records(snapshot)
            # The fresh transition may already have changed the refund status.
            self.invoice.plan_snapshot = {
                **snapshot, "receipt_observations": {
                    **records, self.key: {**records[self.key], **timing},
                },
            }
        else:
            self.invoice.plan_snapshot = {**snapshot, _PAYMENT_TIMING: dict(timing)}


class _Ineligible(ValueError):
    def __init__(self, counter: str):
        self.counter = counter


async def _lock_receipt(
    db: AsyncSession, candidate: _Candidate, scope: ProviderScope, now: datetime,
) -> _LockedReceipt | None:
    # Match the existing writer order: payment operation -> invoice, or
    # refund observation -> invoice. The refund path only reads the operation.
    refund = None
    if candidate.key:
        prefix = f"{scope.environment}:{scope.shop_id}:"
        if not candidate.key.startswith(prefix):
            raise _Ineligible("binding_unverified")
        parent = (
            select(BillingReceiptIdentity.provider_parent_id)
            .where(
                BillingReceiptIdentity.workspace_id == candidate.workspace_id,
                BillingReceiptIdentity.invoice_id == candidate.id,
                BillingReceiptIdentity.environment == scope.environment,
                BillingReceiptIdentity.shop_id == scope.shop_id,
                BillingReceiptIdentity.provider_receipt_id == candidate.key[len(prefix):],
                BillingReceiptIdentity.parent_kind == "refund",
            )
            .scalar_subquery()
        )
        refund = await db.scalar(
            select(ObservedProviderRefund).where(
                ObservedProviderRefund.workspace_id == candidate.workspace_id,
                ObservedProviderRefund.invoice_id == candidate.id,
                ObservedProviderRefund.shop_environment == scope.environment,
                ObservedProviderRefund.provider_refund_id == parent,
                ObservedProviderRefund.status == "succeeded",
            ).with_for_update(skip_locked=True).execution_options(populate_existing=True)
        )
        if refund is None:
            raise _Ineligible("binding_unverified")
    operation_query = select(BillingOperation).where(
        BillingOperation.id == candidate.operation_id,
        BillingOperation.workspace_id == candidate.workspace_id,
        BillingOperation.state.in_(("succeeded", "succeeded_projected", "succeeded_refused")),
        BillingOperation.created_at <= now - _MIN_AGE,
    ).execution_options(populate_existing=True)
    if refund is None:
        operation_query = operation_query.with_for_update(skip_locked=True)
    operation = await db.scalar(operation_query)
    if operation is None:
        return None
    invoice = await db.scalar(
        select(BillingInvoice)
        .join(Workspace, Workspace.id == BillingInvoice.workspace_id)
        .join(WorkspaceMembership, (WorkspaceMembership.workspace_id == Workspace.id)
              & (WorkspaceMembership.user_id == Workspace.owner_user_id))
        .where(
            BillingInvoice.id == candidate.id,
            BillingInvoice.workspace_id == candidate.workspace_id,
            BillingInvoice.operation_id == candidate.operation_id,
            BillingInvoice.status == "succeeded",
            Workspace.kind == "personal",
            WorkspaceMembership.role == "owner",
            WorkspaceMembership.status == "active",
        ).with_for_update(of=BillingInvoice, skip_locked=True).execution_options(populate_existing=True)
    )
    if invoice is None:
        return None
    if not confirm_receipt_payment_binding(operation, invoice, scope):
        raise _Ineligible("binding_unverified")
    snapshot = invoice.plan_snapshot
    records = receipt_observation_records(snapshot)
    if len(records) > 16:
        raise _Ineligible("receipt_capacity_reached")
    payment_id = validate_provider_identifier(operation.provider_id)
    if refund is None:
        if snapshot.get("receipt_registration") != "pending":
            return None
        entry = payment_receipt_record(records, (scope.environment, scope.shop_id, payment_id))
        record = entry[1] if entry else None
        parent_id = payment_id
        timing = snapshot.get(_PAYMENT_TIMING, {})
    else:
        record = records.get(candidate.key)
        if record is None or record.get("status") != "pending":
            return None
        parent_id = refund.provider_refund_id
        timing = record
    if not isinstance(timing, Mapping):
        raise _Ineligible("receipt_source_invalid")
    first = timing.get("first_confirmed_pending_at")
    if first is not None and receipt_utc_timestamp(first) > now:
        raise _Ineligible("receipt_source_invalid")
    receipt_id = None
    if record is not None:
        receipt_id = validate_provider_identifier(record.get("provider_receipt_id"))
        kind = "refund" if refund else "payment"
        if (
            record.get("parent_kind") != kind or record.get("status") != "pending"
            or record.get("provider_parent_id") != parent_id
            or record.get("environment") != scope.environment or record.get("shop_id") != scope.shop_id
            or candidate.key and candidate.key != f"{scope.environment}:{scope.shop_id}:{receipt_id}"
        ):
            raise _Ineligible("receipt_state_conflict")
        identity = await db.scalar(select(BillingReceiptIdentity.invoice_id).filter_by(
            environment=scope.environment, shop_id=scope.shop_id, provider_receipt_id=receipt_id,
            workspace_id=invoice.workspace_id, invoice_id=invoice.id,
            parent_kind=kind, provider_parent_id=parent_id,
        ))
        if identity is None:
            raise _Ineligible("binding_unverified")
    return _LockedReceipt(invoice, operation, candidate.key, receipt_id, parent_id, timing)


async def _apply_response(
    db: AsyncSession, receipt: _LockedReceipt, scope: ProviderScope, payload: dict,
    *, confirmed_at: datetime,
) -> None:
    invoice = receipt.invoice
    if receipt.receipt_id is not None:
        observation = extract_receipt_observation(payload, scope=scope)
        if (
            observation.provider_receipt_id != receipt.receipt_id
            or observation.parent_kind != receipt.kind
            or observation.provider_parent_id != receipt.parent_id
        ):
            raise ProviderObservationError("polled receipt binding conflicts")
        result, available = await record_observed_receipt(
            db, workspace_id=invoice.workspace_id, observation=observation, source="poll",
            observed_at=confirmed_at, confirmed_at=confirmed_at,
        )
        if result in {"unmatched", "conflict"}:
            raise ProviderObservationError("polled receipt conflicts with stored truth")
    else:
        if (
            validate_purchase_payment(payload, operation=receipt.operation, invoice=invoice, scope=scope) != "succeeded"
            or not confirm_receipt_payment_binding(
                receipt.operation, invoice, scope, verified_payment=payload,
            )
        ):
            raise ProviderObservationError("polled payment conflicts with confirmed payment")
        status = extract_payment_observation(payload, scope=scope).receipt_registration
        if status is None:
            raise ProviderObservationError("polled payment does not confirm receipt status")
        invoice.plan_snapshot, available = await merge_confirmed_receipt_registration(
            db, invoice.plan_snapshot, status=status,
            payment_binding=(scope.environment, scope.shop_id, receipt.parent_id), confirmed_at=confirmed_at,
        )
    if not available:
        return
    if receipt.receipt_id is None:
        owner = await db.scalar(select(WorkspaceSubscription.billing_owner_id).where(
            WorkspaceSubscription.workspace_id == invoice.workspace_id,
        ))
    else:
        owner = await db.scalar(select(WorkspaceMembership.user_id).where(
            WorkspaceMembership.workspace_id == invoice.workspace_id,
            WorkspaceMembership.role == "owner", WorkspaceMembership.status == "active",
        ).order_by(WorkspaceMembership.user_id).limit(1))
    if owner is not None:
        await enqueue_billing_notification(
            db, workspace_id=invoice.workspace_id, recipient_id=owner,
            event_id=f"receipt:{invoice.id}:available", kind=BillingNotification.RECEIPT_AVAILABLE,
            payload={"invoice": invoice.safe_number, "action_path": f"/billing/invoices/{invoice.safe_number}"},
            marketing_allowed=False,
        )


async def _clock(db: AsyncSession) -> datetime:
    return (await db.scalar(select(func.clock_timestamp()))).astimezone(UTC)


async def _attempt(
    db: AsyncSession, provider: YooKassaClient, receipt: _LockedReceipt, scope: ProviderScope,
    *, before_get: datetime, budget_left: float,
) -> str:
    try:
        async with asyncio.timeout(min(_GET_SECONDS, budget_left)):
            if receipt.receipt_id is None:
                payload = await provider.get_payment(receipt.parent_id)
            else:
                payload = await provider.get_receipt(receipt.receipt_id)
    except (TimeoutError, YooKassaProviderError, httpx.HTTPError):
        outcome = "unavailable"
    except ValueError:
        outcome = "conflict"
    else:
        outcome = "confirmed"

    now = await _clock(db)
    if now < before_get:
        receipt.write_timing({**receipt.timing, _RESULT: "clock_rollback"})
        return "clock_rollback"
    if outcome == "unavailable":
        timing = record_receipt_overdue(receipt.timing, now=now, freshness="unknown")
        receipt.write_timing({**timing, _RESULT: outcome})
        return outcome
    if outcome == "confirmed":
        try:
            async with db.begin_nested():
                await _apply_response(db, receipt, scope, payload, confirmed_at=now)
        except ValueError:
            # Restore the locked object after rolling back a conflicting transition.
            await db.refresh(receipt.invoice)
            outcome = "conflict"

    timing = {} if receipt.key else receipt.invoice.plan_snapshot[_PAYMENT_TIMING]
    receipt.write_timing({**timing, _RESULT: outcome})
    return outcome


async def reconcile_pending_receipts(db: AsyncSession, settings: Settings) -> dict[str, int]:
    """Run one maintenance-only observation pass without changing paid access."""
    counters = dict.fromkeys((
        "legacy_pending_unknown", "binding_unverified", "receipt_state_conflict",
        "receipt_source_invalid", "receipt_capacity_reached", "receipt_poll_incomplete",
        "receipt_gets",
    ), 0)
    if not (settings.billing_provider_observation_enabled or settings.billing_checkout_enabled):
        return counters
    loop = asyncio.get_running_loop()
    deadline = loop.time() + _PASS_SECONDS
    cursor = ("", UUID(int=0), "")
    reserved: set[tuple[UUID, str]] = set()
    try:
        async with asyncio.timeout_at(deadline):
            await require_billing_maintenance_database(db)
            scope = ProviderScope(
                provider_environment(settings.billing_yookassa_environment),
                settings.billing_yookassa_shop_id,
            )
            async with YooKassaClient(settings) as provider:
                while True:
                    now = await _clock(db)
                    page = (await db.execute(_CANDIDATES, {
                        "oldest": now - _MIN_AGE, "retry_after": now - _INTERVAL, "now": now,
                        "after_attempt": cursor[0], "after_id": cursor[1], "after_key": cursor[2],
                    })).all()
                    await db.commit()
                    if not page:
                        break
                    for row in page:
                        candidate = _Candidate(*row)
                        cursor = (candidate.attempt, candidate.id, candidate.key)
                        logical_key = (candidate.id, candidate.key)
                        if logical_key in reserved:
                            continue
                        try:
                            now = await _clock(db)
                            receipt = await _lock_receipt(db, candidate, scope, now)
                            if receipt is None:
                                await db.commit()
                                continue
                            now = await _clock(db)
                            attempt = receipt.timing.get(_ATTEMPT)
                            if attempt is not None:
                                previous = receipt_utc_timestamp(attempt)
                                if now < previous:
                                    raise _Ineligible("receipt_source_invalid")
                                if now - previous < _INTERVAL:
                                    await db.commit()
                                    continue
                            if (
                                receipt.timing.get("first_confirmed_pending_at") is None
                                or receipt.timing.get("legacy_pending_unknown") is True
                            ):
                                counters["legacy_pending_unknown"] += 1
                            if counters["receipt_gets"] >= _MAX_GET or deadline - loop.time() <= _GET_SECONDS:
                                timing = record_receipt_overdue(receipt.timing, now=now, freshness="unknown")
                                if timing != receipt.timing:
                                    receipt.write_timing(timing)
                                await db.commit()
                                counters["receipt_poll_incomplete"] += 1
                                return counters
                            reservation = now.isoformat()
                            expected = (receipt.kind, receipt.receipt_id, receipt.parent_id)
                            receipt.write_timing({**receipt.timing, _ATTEMPT: reservation, _RESULT: "reserved"})
                            await db.commit()
                            reserved.add(logical_key)
                            now = await _clock(db)
                            receipt = await _lock_receipt(db, candidate, scope, now)
                            if (
                                receipt is None or receipt.timing.get(_ATTEMPT) != reservation
                                or receipt.timing.get(_RESULT) != "reserved"
                                or (receipt.kind, receipt.receipt_id, receipt.parent_id) != expected
                            ):
                                counters["receipt_poll_incomplete"] += 1
                                await db.commit()
                                continue
                            before_get = await _clock(db)
                            if before_get < receipt_utc_timestamp(reservation):
                                raise _Ineligible("receipt_source_invalid")
                            counters["receipt_gets"] += 1
                            outcome = await _attempt(
                                db, provider, receipt, scope, before_get=before_get, budget_left=deadline - loop.time(),
                            )
                            if outcome != "confirmed":
                                counters["receipt_poll_incomplete"] += 1
                            if outcome == "conflict":
                                counters["receipt_state_conflict"] += 1
                            if outcome == "clock_rollback":
                                counters["receipt_source_invalid"] += 1
                            await db.commit()
                        except (_Ineligible, ValueError) as exc:
                            counter = exc.counter if isinstance(exc, _Ineligible) else "receipt_source_invalid"
                            counters[counter] += 1
                            counters["receipt_poll_incomplete"] += 1
                            await db.rollback()
    except (TimeoutError, YooKassaConfigurationError, ValueError):
        counters["receipt_poll_incomplete"] += 1
        await db.rollback()
    return counters
