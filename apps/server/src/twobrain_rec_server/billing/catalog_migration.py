"""Bounded, resumable historical catalog binding. Never infer a latest offer."""

from __future__ import annotations

import json
from copy import deepcopy
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.catalog import CatalogNotApproved, validate_plan_version
from twobrain_rec_server.db.models.billing import (
    BillingEntitlementGrant,
    BillingInvoice,
    BillingOperation,
    BillingPlan,
    BillingPlanPrice,
    BillingPlanVersion,
    TimeCreditLedgerEntry,
    WorkspaceSubscription,
)


async def exact_snapshot_version(
    db: AsyncSession,
    snapshot: object,
    *,
    lock: bool = True,
) -> tuple[BillingPlanVersion, BillingPlanPrice | None] | None:
    """Resolve only the named historical version, including its original list price."""
    if not isinstance(snapshot, dict):
        return None
    catalog = snapshot.get("catalog_snapshot")
    if (
        not isinstance(catalog, dict) or type(catalog.get("catalog_version")) is not int
        or not isinstance(catalog.get("plan_code"), str)
        or not isinstance(catalog.get("cycle"), str)
    ):
        return None
    if snapshot.get("plan_code") != catalog.get("plan_code") or snapshot.get(
        "cycle"
    ) != catalog.get("cycle"):
        return None
    query = (
        select(BillingPlanVersion)
        .where(
            BillingPlanVersion.plan_code == catalog["plan_code"],
            BillingPlanVersion.version == catalog["catalog_version"],
        )
    )
    version = await db.scalar(query.with_for_update() if lock else query)
    if version is None:
        return None
    price = None
    if version.status != "legacy":
        try:
            if UUID(str(catalog.get("plan_version_id"))) != version.id:
                return None
            price_id = UUID(str(catalog.get("price_id"))) if catalog.get("price_id") else None
        except (TypeError, ValueError):
            return None
        if price_id:
            price = await db.scalar(
                select(BillingPlanPrice).where(
                    BillingPlanPrice.id == price_id, BillingPlanPrice.version_id == version.id
                )
            )
            if price is None:
                return None
    try:
        expected = validate_plan_version(version, price=price, for_checkout=False).as_dict()
    except (CatalogNotApproved, ValueError):
        return None
    if json.dumps(catalog, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
        return None
    amount = snapshot.get("list_amount_minor", expected["amount_minor"])
    if type(amount) is not type(expected["amount_minor"]) or amount != expected["amount_minor"]:
        return None
    return version, price


async def _legacy_price(db: AsyncSession, version: BillingPlanVersion) -> BillingPlanPrice:
    """Catch up catalog rows written after the additive migration, under the version lock."""
    price = await db.scalar(
        select(BillingPlanPrice).where(
            BillingPlanPrice.version_id == version.id,
            BillingPlanPrice.cycle == version.cycle,
            BillingPlanPrice.currency == version.currency,
        )
    )
    if price is not None:
        if price.amount_minor != version.amount_minor:
            raise ValueError("historical price mismatch")
        return price
    if version.plan_id is None:
        await db.execute(
            insert(BillingPlan)
            .values(code=version.plan_code, display_name=version.plan_code)
            .on_conflict_do_nothing(index_elements=[BillingPlan.code])
        )
        version.plan_id = await db.scalar(
            select(BillingPlan.id).where(BillingPlan.code == version.plan_code)
        )
        await db.flush()
    await db.execute(
        insert(BillingPlanPrice)
        .values(
            version_id=version.id,
            cycle=version.cycle,
            amount_minor=version.amount_minor,
            currency=version.currency,
        )
        .on_conflict_do_nothing(
            index_elements=[
                BillingPlanPrice.version_id,
                BillingPlanPrice.cycle,
                BillingPlanPrice.currency,
            ]
        )
    )
    price = await db.scalar(
        select(BillingPlanPrice).where(
            BillingPlanPrice.version_id == version.id,
            BillingPlanPrice.cycle == version.cycle,
            BillingPlanPrice.currency == version.currency,
        )
    )
    if price is None or price.amount_minor != version.amount_minor:
        raise ValueError("historical price mismatch")
    return price


async def pin_subscription_history(db: AsyncSession, subscription: WorkspaceSubscription) -> str:
    subscription.pin_checked_application_version = subscription.application_version
    if subscription.plan_code in ("free", "trial"):
        subscription.pin_state = "not_applicable"
        return "not_applicable"
    # Two rows detect ambiguity at the latest paid start. An old/new offer is never chosen by price.
    rows = (
        await db.execute(
            select(BillingEntitlementGrant, BillingInvoice, BillingOperation)
            .join(BillingInvoice, BillingInvoice.id == BillingEntitlementGrant.invoice_id)
            .join(BillingOperation, BillingOperation.id == BillingInvoice.operation_id)
            .where(
                BillingEntitlementGrant.workspace_id == subscription.workspace_id,
                BillingInvoice.workspace_id == subscription.workspace_id,
                BillingOperation.workspace_id == subscription.workspace_id,
            )
            .order_by(BillingEntitlementGrant.starts_at.desc(), BillingEntitlementGrant.id.desc())
            .limit(2)
        )
    ).all()
    subscription.pin_state = "legacy_pinned"
    evidence = {
        "reason": "confirmed_history_missing",
        "application_version": subscription.application_version,
        "subscription": {
            "plan_code": subscription.plan_code,
            "cycle": subscription.cycle,
            "paid_through": subscription.paid_through.isoformat()
            if subscription.paid_through
            else None,
            "capacity_bytes": subscription.capacity_bytes,
        },
    }
    subscription.legacy_pinned_snapshot = evidence

    # Assign a fresh dict so ORM persists subsequent evidence updates.
    def review(reason: str) -> str:
        subscription.pinned_price_id = None
        subscription.pinned_plan_version_id = None
        subscription.legacy_pinned_snapshot = {**evidence, "reason": reason}
        return "review_required"

    if not rows:
        return review("confirmed_history_missing")
    grant, invoice, operation = rows[0]
    evidence.update(
        invoice_id=str(invoice.id),
        operation_id=str(operation.id),
        grant_id=str(grant.id),
        invoice_snapshot=deepcopy(invoice.plan_snapshot),
        operation_snapshot=deepcopy(operation.request_snapshot),
    )
    if len(rows) > 1 and rows[1][0].starts_at == grant.starts_at:
        return review("ambiguous_paid_interval")
    if (
        invoice.status != "succeeded"
        or operation.state != "succeeded"
        or operation.provider_id != grant.provider_payment_id
        or grant.source not in ("provider_confirmed", "renewal_provider_confirmed")
        or grant.amount_minor != invoice.amount_minor
        or grant.currency != invoice.currency
        or grant.plan_code != subscription.plan_code
        or grant.cycle != subscription.cycle
    ):
        return review("confirmed_history_mismatch")
    # Legacy referral days may extend paid_through; prove the whole extension from their ledger.
    end = grant.ends_at
    if subscription.paid_through is not None and end < subscription.paid_through:
        credits = await db.scalars(
            select(TimeCreditLedgerEntry)
            .where(
                TimeCreditLedgerEntry.workspace_id == subscription.workspace_id,
                TimeCreditLedgerEntry.state == "applied",
                TimeCreditLedgerEntry.applied_start >= end,
            )
            .order_by(TimeCreditLedgerEntry.applied_start, TimeCreditLedgerEntry.id)
            .limit(501)
        )
        credits = list(credits)
        if len(credits) > 500:
            return review("credit_history_requires_review")
        for credit in credits:
            if (
                credit.applied_start != end
                or credit.applied_end is None
                or credit.applied_end <= end
            ):
                return review("credit_interval_mismatch")
            end = credit.applied_end
    if end != subscription.paid_through:
        return review("access_interval_mismatch")
    resolved = await exact_snapshot_version(db, invoice.plan_snapshot)
    if resolved is None:
        return review("catalog_snapshot_mismatch")
    version, price = resolved
    if operation.request_snapshot.get("catalog_snapshot") != invoice.plan_snapshot.get(
        "catalog_snapshot"
    ):
        return review("operation_snapshot_mismatch")
    if version.status == "legacy":
        try:
            price = await _legacy_price(db, version)
        except ValueError:
            return review("historical_price_mismatch")
    if price is None:
        return review("historical_price_missing")
    subscription.pinned_plan_version_id = version.id
    subscription.pinned_price_id = price.id
    subscription.next_charge_at = subscription.paid_through
    subscription.pin_state = "pinned"
    subscription.legacy_pinned_snapshot = {**evidence, "reason": "exact_confirmed_snapshot"}
    grant.plan_version_id = version.id
    return "pinned"


async def backfill_subscription_pins(db: AsyncSession, *, limit: int = 100) -> dict[str, int]:
    """Caller uses maintenance identity and commits each batch. Watermarks are per subscription.

    A writer changing application_version reopens that row for catch-up; a failed batch
    rolls back both changes and watermark. Unknown histories are recorded once for review.
    """
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError("batch limit must be between 1 and 500")
    subscriptions = await db.scalars(
        select(WorkspaceSubscription)
        .where(
            or_(
                WorkspaceSubscription.pin_checked_application_version.is_distinct_from(
                    WorkspaceSubscription.application_version
                ),
                WorkspaceSubscription.pin_state == "pending",
            )
        )
        .order_by(WorkspaceSubscription.workspace_id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    counts = {"processed": 0, "pinned": 0, "review_required": 0, "not_applicable": 0}
    for subscription in subscriptions:
        counts[await pin_subscription_history(db, subscription)] += 1
        counts["processed"] += 1
    await db.flush()
    return counts
