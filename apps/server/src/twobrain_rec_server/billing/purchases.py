"""Exact purchase calculations and transactional, workspace-bound financial records.

No function in this module submits a payment. Money is reserved and persisted
before the existing provider dispatch path may send an immutable operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.catalog import ADDON_CAPACITY_BYTES, PERSONAL_STORAGE_BYTES
from twobrain_rec_server.db.models import (
    BillingAcceptanceBudget,
    BillingAcceptanceReservation,
    BillingOperation,
    BillingStoragePriceVersion,
    WorkspaceSubscription,
)

CARD_MINIMUM_MINOR = 100


class PurchaseError(ValueError):
    """Bounded, user-safe explanation; never includes provider data."""


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PurchaseError("Для расчёта требуется точное время с часовым поясом")
    return value.astimezone(UTC)


def _micros(start: datetime, end: datetime) -> int:
    delta = end - start
    return delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds


@dataclass(frozen=True, slots=True)
class StorageSegment:
    base_grant_id: UUID
    starts_at: datetime
    ends_at: datetime
    cycle: str
    capacity_bytes: int
    current_price_minor: int
    target_price_minor: int
    target_catalog_id: UUID


@dataclass(frozen=True, slots=True)
class PricedStorageSegment:
    base_grant_id: UUID
    starts_at: datetime
    ends_at: datetime
    cycle: str
    capacity_bytes: int
    full_period_amount_minor: int
    amount_minor: int
    catalog_version_id: UUID

    def as_dict(self) -> dict[str, object]:
        return {
            "base_grant_id": str(self.base_grant_id),
            "starts_at": self.starts_at.isoformat(),
            "ends_at": self.ends_at.isoformat(),
            "cycle": self.cycle,
            "capacity_bytes": self.capacity_bytes,
            "full_period_amount_minor": self.full_period_amount_minor,
            "amount_minor": self.amount_minor,
            "catalog_version_id": str(self.catalog_version_id),
        }


@dataclass(frozen=True, slots=True)
class StoragePurchaseCalculation:
    list_amount_minor: int
    payable_amount_minor: int
    segments: tuple[PricedStorageSegment, ...]
    ends_at: datetime
    next_capacity_bytes: int
    deferred_to_renewal: bool = False


def quote_storage_purchase(
    *,
    segments: list[StorageSegment],
    target_capacity_bytes: int,
    now: datetime,
    discount_percent: int = 0,
    provider_floor_minor: int = CARD_MINIMUM_MINOR,
    bonus_interval: bool = False,
    allow_bonus_gaps: bool = False,
) -> StoragePurchaseCalculation:
    current = utc(now)
    if target_capacity_bytes not in (PERSONAL_STORAGE_BYTES, *ADDON_CAPACITY_BYTES):
        raise PurchaseError("Этот объём недоступен")
    if type(discount_percent) is not int or not 0 <= discount_percent <= 99:
        raise PurchaseError("Недопустимая скидка")
    if type(provider_floor_minor) is not int or provider_floor_minor <= 0:
        raise PurchaseError("Минимальная сумма не настроена")
    floor = max(CARD_MINIMUM_MINOR, provider_floor_minor)
    ordered = sorted(segments, key=lambda item: utc(item.starts_at))
    previous_end = None
    active = []
    for item in ordered:
        start, end = utc(item.starts_at), utc(item.ends_at)
        if end <= start or item.cycle not in {"month", "year"}:
            raise PurchaseError("Оплаченный период требует сверки")
        if previous_end is not None and start < previous_end:
            raise PurchaseError("Оплаченные периоды пересекаются")
        if (
            previous_end is not None
            and start > previous_end
            and not (bonus_interval or allow_bonus_gaps)
        ):
            raise PurchaseError("Между оплаченными периодами есть разрыв")
        previous_end = end
        if (
            type(item.current_price_minor) is not int
            or type(item.target_price_minor) is not int
            or min(item.current_price_minor, item.target_price_minor) < 0
        ):
            raise PurchaseError("Цена периода требует сверки")
        if end > current:
            active.append(item)
    if not active:
        raise PurchaseError("Оплаченный период закончился")
    horizon = utc(active[-1].ends_at)
    if bonus_interval or target_capacity_bytes <= active[0].capacity_bytes:
        return StoragePurchaseCalculation(0, 0, (), horizon, target_capacity_bytes, True)
    quoted = []
    for item in active:
        if target_capacity_bytes <= item.capacity_bytes:
            continue  # A greater prepaid future capacity is never sold again or reduced.
        start, end = utc(item.starts_at), utc(item.ends_at)
        service_start = max(start, current)
        amount = (
            max(0, item.target_price_minor - item.current_price_minor)
            * _micros(service_start, end)
            // _micros(start, end)
        )
        quoted.append(
            PricedStorageSegment(
                item.base_grant_id,
                service_start,
                end,
                item.cycle,
                target_capacity_bytes,
                item.target_price_minor,
                amount,
                item.target_catalog_id,
            )
        )
    total = sum(item.amount_minor for item in quoted)
    if total < floor:
        return StoragePurchaseCalculation(0, 0, (), horizon, target_capacity_bytes, True)
    payable = total * (100 - discount_percent) // 100
    if payable < floor:
        raise PurchaseError(
            "Сумма со скидкой меньше минимального платежа. Уберите промокод или выберите другой объём"
        )
    return StoragePurchaseCalculation(total, payable, tuple(quoted), horizon, target_capacity_bytes)


async def reserve_acceptance_budget(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    operation_id: UUID,
    amount_minor: int,
    now: datetime,
) -> UUID | None:
    """Reserve under the budget row lock. No budget means an ordinary customer.

    A disabled/expired budget remains a fence for this dedicated acceptance
    workspace; changing the promo cannot bypass an exhausted or closed budget.
    The caller persists the operation and owns the transaction.
    """
    if type(amount_minor) is not int or amount_minor < CARD_MINIMUM_MINOR:
        raise PurchaseError("Сумма меньше минимального платежа")
    budget = await db.scalar(
        select(BillingAcceptanceBudget)
        .where(
            BillingAcceptanceBudget.workspace_id == workspace_id,
        )
        .with_for_update()
    )
    if budget is None:
        return None
    operation = await db.scalar(
        select(BillingOperation).where(
            BillingOperation.id == operation_id,
            BillingOperation.workspace_id == workspace_id,
        )
    )
    if operation is None:
        raise PurchaseError("Платёжная операция не найдена")
    existing = await db.scalar(
        select(BillingAcceptanceReservation)
        .where(
            BillingAcceptanceReservation.workspace_id == workspace_id,
            BillingAcceptanceReservation.operation_id == operation_id,
        )
        .with_for_update()
    )
    if not budget.enabled or utc(budget.expires_at) <= utc(now):
        raise PurchaseError("Проверочное окно оплаты закрыто")
    if existing is not None:
        if existing.amount_minor != amount_minor or existing.state == "released":
            raise PurchaseError("Состояние платёжной операции изменилось")
        return budget.id
    if budget.reserved_minor + budget.spent_minor + amount_minor > budget.limit_minor:
        raise PurchaseError("Достигнут общий предел проверочных списаний")
    budget.reserved_minor += amount_minor
    db.add(
        BillingAcceptanceReservation(
            workspace_id=workspace_id,
            budget_id=budget.id,
            operation_id=operation_id,
            amount_minor=amount_minor,
            state="reserved",
        )
    )
    await db.flush()
    return budget.id


async def settle_acceptance_budget(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    operation_id: UUID,
    succeeded: bool,
) -> None:
    """Only an authoritative terminal payment result may settle a reservation.

    Refunds and repeated canceled observations never release already spent
    money. An unknown result must not call this function.
    """
    budget = await db.scalar(
        select(BillingAcceptanceBudget)
        .where(
            BillingAcceptanceBudget.workspace_id == workspace_id,
        )
        .with_for_update()
    )
    if budget is None:
        return
    reservation = await db.scalar(
        select(BillingAcceptanceReservation)
        .where(
            BillingAcceptanceReservation.workspace_id == workspace_id,
            BillingAcceptanceReservation.operation_id == operation_id,
        )
        .with_for_update()
    )
    if reservation is None or reservation.state == "spent":
        return
    if reservation.state == "released":
        if succeeded:
            raise PurchaseError("Противоречивый результат платежа требует финансовой сверки")
        return
    budget.reserved_minor -= reservation.amount_minor
    if succeeded:
        budget.spent_minor += reservation.amount_minor
        reservation.state = "spent"
    else:
        reservation.state = "released"
    await db.flush()


async def storage_catalog(
    db: AsyncSession, *, now: datetime
) -> dict[tuple[int, str], BillingStoragePriceVersion]:
    current = utc(now)
    rows = await db.scalars(
        select(BillingStoragePriceVersion)
        .where(
            BillingStoragePriceVersion.enabled_for_checkout.is_(True),
            BillingStoragePriceVersion.effective_from <= current,
            (
                BillingStoragePriceVersion.effective_until.is_(None)
                | (BillingStoragePriceVersion.effective_until > current)
            ),
        )
        .order_by(BillingStoragePriceVersion.version.desc())
    )
    catalog = {}
    for row in rows:
        if (
            row.currency != "RUB"
            or row.amount_minor <= 0
            or row.capacity_bytes not in ADDON_CAPACITY_BYTES
            or row.cycle not in {"month", "year"}
        ):
            continue
        catalog.setdefault((row.capacity_bytes, row.cycle), row)
    return catalog


async def effective_paid_storage(
    db: AsyncSession, *, subscription: WorkspaceSubscription, now: datetime
) -> int:
    """Project only active financial rights; reading future grants never downgrades now.

    Historical expanded caches without a storage journal are preserved for
    reconciliation, rather than silently taking away an existing paid volume.
    """
    from sqlalchemy import func

    from twobrain_rec_server.billing.catalog import FREE_STORAGE_BYTES, TRIAL_STORAGE_BYTES
    from twobrain_rec_server.db.models import (
        BillingEntitlementGrant,
        BillingInvoice,
        BillingStorageEntitlementGrant,
        TimeCreditLedgerEntry,
    )

    current = utc(now)
    if subscription.plan_code == "trial":
        return (
            TRIAL_STORAGE_BYTES
            if subscription.trial_ends_at and utc(subscription.trial_ends_at) > current
            else FREE_STORAGE_BYTES
        )
    if (
        subscription.plan_code != "personal"
        or not subscription.paid_through
        or utc(subscription.paid_through) <= current
    ):
        return FREE_STORAGE_BYTES
    bonus = await db.scalar(
        select(TimeCreditLedgerEntry)
        .where(
            TimeCreditLedgerEntry.workspace_id == subscription.workspace_id,
            TimeCreditLedgerEntry.state == "applied",
            TimeCreditLedgerEntry.applied_start <= current,
            TimeCreditLedgerEntry.applied_end > current,
        )
        .order_by(TimeCreditLedgerEntry.applied_start.desc())
        .limit(1)
    )
    if bonus is not None:
        return max(
            PERSONAL_STORAGE_BYTES,
            bonus.capacity_snapshot_bytes or subscription.capacity_bytes or PERSONAL_STORAGE_BYTES,
        )
    active = await db.scalar(
        select(func.max(BillingStorageEntitlementGrant.capacity_bytes)).where(
            BillingStorageEntitlementGrant.workspace_id == subscription.workspace_id,
            BillingStorageEntitlementGrant.starts_at <= current,
            BillingStorageEntitlementGrant.ends_at > current,
        )
    )
    if active is not None:
        return max(PERSONAL_STORAGE_BYTES, int(active))
    base_invoice = await db.scalar(
        select(BillingInvoice)
        .join(
            BillingEntitlementGrant,
            (BillingEntitlementGrant.invoice_id == BillingInvoice.id)
            & (BillingEntitlementGrant.workspace_id == BillingInvoice.workspace_id),
        )
        .where(
            BillingEntitlementGrant.workspace_id == subscription.workspace_id,
            BillingEntitlementGrant.starts_at <= current,
            BillingEntitlementGrant.ends_at > current,
        )
        .order_by(BillingEntitlementGrant.starts_at.desc())
        .limit(1)
    )
    if base_invoice is not None:
        snapshot = base_invoice.plan_snapshot or {}
        if snapshot.get("purchase_schema") == 2:
            return PERSONAL_STORAGE_BYTES  # Explicit base-only interval, including a downgrade.
        legacy_capacity = (snapshot.get("catalog_snapshot") or {}).get("storage_bytes")
        if type(legacy_capacity) is int and legacy_capacity > PERSONAL_STORAGE_BYTES:
            return legacy_capacity
        if (subscription.capacity_bytes or 0) > PERSONAL_STORAGE_BYTES:
            return subscription.capacity_bytes
    has_journal = await db.scalar(
        select(BillingStorageEntitlementGrant.id)
        .where(
            BillingStorageEntitlementGrant.workspace_id == subscription.workspace_id,
        )
        .limit(1)
    )
    if (
        base_invoice is None
        and has_journal is None
        and (subscription.capacity_bytes or PERSONAL_STORAGE_BYTES) > PERSONAL_STORAGE_BYTES
    ):
        return subscription.capacity_bytes
    return PERSONAL_STORAGE_BYTES


def subscription_quote_key(subscription: WorkspaceSubscription | None) -> str:
    import hashlib
    import json

    values = (
        None
        if subscription is None
        else {
            "application_version": subscription.application_version or 0,
            "selection_version": subscription.next_capacity_version or 0,
            "capacity": subscription.capacity_bytes,
            "next_capacity": subscription.next_capacity_bytes,
            "cycle": subscription.cycle,
            "paid_through": utc(subscription.paid_through).isoformat()
            if subscription.paid_through
            else None,
            "owner": str(subscription.billing_owner_id) if subscription.billing_owner_id else None,
            "authority": subscription.recurring_authority_version or 0,
            "recurring": bool(subscription.recurring_allowed),
        }
    )
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


async def create_purchase_quote(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    owner_user_id: UUID,
    purpose: str,
    subscription: WorkspaceSubscription | None,
    snapshot: dict[str, object],
    now: datetime,
):
    import json
    from datetime import timedelta

    from twobrain_rec_server.db.models import BillingPurchaseQuote

    if purpose not in {
        "initial_checkout",
        "storage_upgrade",
        "early_renewal",
        "storage_schedule",
        "resume_renewal",
    }:
        raise PurchaseError("Назначение покупки недоступно")
    if subscription is not None and subscription.workspace_id != workspace_id:
        raise PurchaseError("Подписка недоступна")
    # Copy JSON values so later mutation of a view model cannot change this offer.
    saved = json.loads(json.dumps(snapshot))
    saved["subscription_key"] = subscription_quote_key(subscription)
    # Keep consumed financial evidence; reclaim only expired unused offers,
    # in a bounded batch within the current workspace and owner.
    stale_ids = list(
        await db.scalars(
            select(BillingPurchaseQuote.id)
            .where(
                BillingPurchaseQuote.workspace_id == workspace_id,
                BillingPurchaseQuote.owner_user_id == owner_user_id,
                BillingPurchaseQuote.consumed_operation_id.is_(None),
                BillingPurchaseQuote.expires_at <= utc(now),
            )
            .order_by(BillingPurchaseQuote.expires_at)
            .limit(100)
            .with_for_update(skip_locked=True)
        )
    )
    if stale_ids:
        await db.execute(delete(BillingPurchaseQuote).where(BillingPurchaseQuote.id.in_(stale_ids)))
    for existing in await db.scalars(
        select(BillingPurchaseQuote)
        .where(
            BillingPurchaseQuote.workspace_id == workspace_id,
            BillingPurchaseQuote.owner_user_id == owner_user_id,
            BillingPurchaseQuote.purpose == purpose,
            BillingPurchaseQuote.consumed_operation_id.is_(None),
            BillingPurchaseQuote.expires_at > utc(now),
        )
        .order_by(BillingPurchaseQuote.created_at.desc())
        .limit(10)
    ):
        if existing.snapshot == saved:
            return existing
    quote = BillingPurchaseQuote(
        workspace_id=workspace_id,
        owner_user_id=owner_user_id,
        purpose=purpose,
        subscription_version=subscription.application_version or 0 if subscription else 0,
        selection_version=subscription.next_capacity_version or 0 if subscription else 0,
        snapshot=saved,
        created_at=utc(now),
        expires_at=utc(now) + timedelta(minutes=10),
    )
    db.add(quote)
    await db.flush()
    return quote


async def validate_purchase_quote(
    db: AsyncSession,
    *,
    quote_id: UUID,
    workspace_id: UUID,
    owner_user_id: UUID,
    purpose: str,
    subscription: WorkspaceSubscription | None,
    now: datetime,
    expected_snapshot: dict[str, object] | None = None,
):
    from twobrain_rec_server.db.models import BillingPurchaseQuote

    quote = await db.scalar(
        select(BillingPurchaseQuote)
        .where(
            BillingPurchaseQuote.id == quote_id,
            BillingPurchaseQuote.workspace_id == workspace_id,
            BillingPurchaseQuote.owner_user_id == owner_user_id,
        )
        .with_for_update()
    )
    if (
        quote is None
        or quote.purpose != purpose
        or quote.consumed_operation_id is not None
        or utc(quote.expires_at) <= utc(now)
        or quote.snapshot.get("subscription_key") != subscription_quote_key(subscription)
    ):
        raise PurchaseError(
            "Расчёт изменился или устарел. Проверьте сумму и подтвердите покупку заново"
        )
    if expected_snapshot is not None and any(
        quote.snapshot.get(key) != value for key, value in expected_snapshot.items()
    ):
        raise PurchaseError("Цена или условия изменились. Проверьте новый расчёт перед оплатой")
    return quote


async def compose_personal_catalog(
    db: AsyncSession,
    *,
    base,
    subscription: WorkspaceSubscription | None,
    now: datetime,
):
    from dataclasses import replace
    from datetime import timedelta

    capacity = PERSONAL_STORAGE_BYTES
    if (
        subscription
        and subscription.plan_code == "personal"
        and subscription.paid_through
        and utc(subscription.paid_through) > utc(now)
    ):
        capacity = (
            subscription.next_capacity_bytes
            or subscription.capacity_bytes
            or PERSONAL_STORAGE_BYTES
        )
        if subscription.next_capacity_bytes is None:
            # The next unpaid period follows all prepaid periods, so a stale
            # cache of today's volume must not price a future renewal.
            capacity = await effective_paid_storage(
                db,
                subscription=subscription,
                now=utc(subscription.paid_through) - timedelta(microseconds=1),
            )
    capacity = max(PERSONAL_STORAGE_BYTES, capacity)
    if capacity == PERSONAL_STORAGE_BYTES:
        return base, None
    price = (await storage_catalog(db, now=now)).get((capacity, base.cycle))
    if price is None:
        raise PurchaseError("Цена выбранного объёма временно недоступна")
    return replace(
        base, amount_minor=base.amount_minor + price.amount_minor, storage_bytes=capacity
    ), price


def storage_price_snapshot(price: BillingStoragePriceVersion | None) -> dict[str, object] | None:
    if price is None:
        return None
    return {
        "id": str(price.id),
        "version": price.version,
        "cycle": price.cycle,
        "capacity_bytes": price.capacity_bytes,
        "amount_minor": price.amount_minor,
        "currency": price.currency,
        "policy_snapshot": dict(price.policy_snapshot or {}),
    }


def accept_storage_price(subscription, snapshot: dict | None) -> None:
    """Only explicit, validated user confirmation calls this; never a callback."""
    if snapshot is None:
        return
    key = f"{snapshot['capacity_bytes']}:{snapshot['cycle']}"
    subscription.storage_price_consents = {
        **(subscription.storage_price_consents or {}),
        key: dict(snapshot),
    }


def accept_base_price(
    subscription, catalog_snapshot: dict, storage_snapshot: dict | None = None
) -> None:
    """Persist explicit agreement to the base component alongside storage terms."""
    snapshot = dict(catalog_snapshot)
    if storage_snapshot:
        snapshot["amount_minor"] -= storage_snapshot["amount_minor"]
        snapshot["storage_bytes"] = PERSONAL_STORAGE_BYTES
    subscription.storage_price_consents = {
        **(subscription.storage_price_consents or {}),
        f"base:{snapshot['cycle']}": snapshot,
    }


def base_price_is_accepted(subscription, base) -> bool:
    return (subscription.storage_price_consents or {}).get(f"base:{base.cycle}") == base.as_dict()


def storage_price_is_accepted(subscription, price) -> bool:
    if price is None:
        return True
    snapshot = storage_price_snapshot(price)
    key = f"{price.capacity_bytes}:{price.cycle}"
    return (subscription.storage_price_consents or {}).get(key) == snapshot


def checkout_quote_snapshot(*, catalog, storage_price, preview, promo, discount_source):
    from twobrain_rec_server.billing.promotions import promo_code_hash

    return {
        "cycle": preview.cycle,
        "list_amount_minor": preview.list_amount_minor,
        "payable_amount_minor": preview.payable_amount_minor,
        "catalog_snapshot": catalog.as_dict(),
        "storage_price_snapshot": storage_price_snapshot(storage_price),
        "promo_code_hash": promo_code_hash(promo.code) if promo else None,
        "campaign_version": promo.campaign_version if promo else None,
        "discount_percent": promo.discount_percent if promo else None,
        "discount_source": discount_source,
    }


async def append_purchased_storage(db: AsyncSession, *, grant, snapshot: dict) -> None:
    """A composite renewal buys storage for exactly its new base period."""
    from twobrain_rec_server.db.models import BillingStorageEntitlementGrant

    price = snapshot.get("storage_price_snapshot")
    if price is None:
        return  # Historical base-only invoices remain valid.
    try:
        catalog_id = UUID(price["id"])
        capacity, amount = price["capacity_bytes"], price["amount_minor"]
        if capacity not in ADDON_CAPACITY_BYTES or type(amount) is not int or amount <= 0:
            raise ValueError
        if price["cycle"] != grant.cycle or price["currency"] != "RUB":
            raise ValueError
    except (KeyError, TypeError, ValueError) as exc:
        raise PurchaseError("Состав оплаченной услуги требует сверки") from exc
    await db.flush()  # Grant and invoice must exist before the period FK/trigger.
    db.add(
        BillingStorageEntitlementGrant(
            workspace_id=grant.workspace_id,
            invoice_id=grant.invoice_id,
            base_grant_id=grant.id,
            capacity_bytes=capacity,
            starts_at=grant.starts_at,
            ends_at=grant.ends_at,
            catalog_version_id=catalog_id,
            full_period_amount_minor=amount,
        )
    )
    await db.flush()


async def grant_confirmed_storage(db: AsyncSession, *, operation, invoice, now: datetime) -> str:
    """Apply the exact quoted segments once; expired purchases require a remedy."""
    from datetime import timedelta

    from twobrain_rec_server.billing.events import enqueue_billing_notification
    from twobrain_rec_server.billing.notifications import BillingNotification
    from twobrain_rec_server.billing.promotions import redeem_invoice_promo
    from twobrain_rec_server.db.models import BillingStorageEntitlementGrant

    if operation.kind != "storage_upgrade":
        raise PurchaseError("Назначение платежа требует сверки")
    existing = await db.scalar(
        select(BillingStorageEntitlementGrant.id)
        .where(
            BillingStorageEntitlementGrant.workspace_id == operation.workspace_id,
            BillingStorageEntitlementGrant.invoice_id == invoice.id,
        )
        .limit(1)
    )
    if existing:
        return (
            "service_expired"
            if invoice.plan_snapshot.get("service_resolution") == "storage_period_expired"
            else "duplicate"
        )
    subscription = await db.scalar(
        select(WorkspaceSubscription)
        .where(
            WorkspaceSubscription.workspace_id == operation.workspace_id,
        )
        .with_for_update()
    )
    snapshot = operation.request_snapshot
    segments = snapshot.get("storage_segments")
    if subscription is None or not isinstance(segments, list) or not segments:
        operation.state = "reconciliation_gap"
        return "snapshot_invalid"
    current = utc(now)
    expired_indices = [
        index
        for index, segment in enumerate(segments)
        if utc(datetime.fromisoformat(segment["ends_at"])) <= current
    ]
    valid_segments = [
        segment for index, segment in enumerate(segments) if index not in expired_indices
    ]
    for segment in valid_segments:
        db.add(
            BillingStorageEntitlementGrant(
                workspace_id=operation.workspace_id,
                invoice_id=invoice.id,
                base_grant_id=UUID(segment["base_grant_id"]),
                capacity_bytes=segment["capacity_bytes"],
                starts_at=utc(datetime.fromisoformat(segment["starts_at"])),
                ends_at=utc(datetime.fromisoformat(segment["ends_at"])),
                catalog_version_id=UUID(segment["catalog_version_id"]),
                full_period_amount_minor=segment["full_period_amount_minor"],
            )
        )
    await db.flush()
    if valid_segments:
        # A delayed old payment must not overwrite a later deliberate selection.
        if snapshot.get("selection_version") == subscription.next_capacity_version:
            subscription.next_capacity_bytes = snapshot["target_capacity_bytes"]
            subscription.next_capacity_version += 1
        subscription.capacity_bytes = await effective_paid_storage(
            db, subscription=subscription, now=current
        )
        subscription.application_version = (subscription.application_version or 0) + 1
    if expired_indices:
        invoice.status = "succeeded"
        operation.state = "reconciliation_gap"
        invoice.plan_snapshot = {
            **invoice.plan_snapshot,
            "service_resolution": "storage_period_expired",
        }
        operation.request_snapshot = {
            **snapshot,
            "reconciliation_detail": snapshot.get("reconciliation_detail")
            or {
                "code": "storage_period_expired",
                "expired_segment_indices": expired_indices,
                "incident_owner": "billing_operator",
                "financial_operator": "finance_operator",
                "detected_at": current.isoformat(),
                "review_by": (current + timedelta(hours=24)).isoformat(),
            },
        }
        await redeem_invoice_promo(db, invoice_id=invoice.id, now=current)
        if subscription.billing_owner_id is not None:
            await enqueue_billing_notification(
                db,
                workspace_id=operation.workspace_id,
                recipient_id=subscription.billing_owner_id,
                event_id=f"payment:{invoice.id}:service_gap",
                kind=BillingNotification.SERVICE_RECONCILIATION,
                payload={
                    "invoice": invoice.safe_number,
                    "action_path": f"/billing/invoices/{invoice.safe_number}",
                },
                marketing_allowed=False,
            )
        await db.flush()
        return "service_expired"
    invoice.status = "succeeded"
    operation.state = "succeeded"
    await redeem_invoice_promo(db, invoice_id=invoice.id, now=current)
    if subscription.billing_owner_id is not None:
        await enqueue_billing_notification(
            db,
            workspace_id=operation.workspace_id,
            recipient_id=subscription.billing_owner_id,
            event_id=f"payment:{invoice.id}:succeeded",
            kind=BillingNotification.PAYMENT_SUCCEEDED,
            payload={"invoice": invoice.safe_number, "action_path": "/billing/storage"},
            marketing_allowed=False,
        )
    await db.flush()
    return "granted"


async def calculate_storage_purchase(
    db: AsyncSession,
    *,
    subscription: WorkspaceSubscription,
    target_capacity_bytes: int,
    now: datetime,
    discount_percent: int = 0,
    provider_floor_minor: int = 100,
) -> StoragePurchaseCalculation:
    from twobrain_rec_server.db.models import (
        BillingEntitlementGrant,
        BillingStorageEntitlementGrant,
        TimeCreditLedgerEntry,
    )

    current = utc(now)
    if (
        subscription.plan_code != "personal"
        or not subscription.paid_through
        or utc(subscription.paid_through) <= current
    ):
        raise PurchaseError("Для увеличения места нужен действующий тариф «Личный»")
    if target_capacity_bytes not in (PERSONAL_STORAGE_BYTES, *ADDON_CAPACITY_BYTES):
        raise PurchaseError("Этот объём недоступен")
    # Selecting the same or a smaller future capacity never sells the current
    # interval. This also lets legacy owners accept a new renewal price without
    # fabricating a historical storage grant or altering their paid rights.
    if target_capacity_bytes <= await effective_paid_storage(
        db, subscription=subscription, now=current
    ):
        return StoragePurchaseCalculation(
            0, 0, (), utc(subscription.paid_through), target_capacity_bytes, True
        )
    credits = list(
        await db.scalars(
            select(TimeCreditLedgerEntry)
            .where(
                TimeCreditLedgerEntry.workspace_id == subscription.workspace_id,
                TimeCreditLedgerEntry.state == "applied",
                TimeCreditLedgerEntry.applied_end > current,
            )
            .order_by(TimeCreditLedgerEntry.applied_start)
        )
    )
    # A future bonus keeps its original capacity. Do not sell an upgrade on
    # both sides of that gap while promising continuous increased storage.
    if any(
        utc(item.applied_start) < utc(subscription.paid_through) and utc(item.applied_end) > current
        for item in credits
    ):
        return StoragePurchaseCalculation(
            0, 0, (), utc(subscription.paid_through), target_capacity_bytes, True
        )
    catalog = await storage_catalog(db, now=current)
    grants = list(
        await db.scalars(
            select(BillingEntitlementGrant)
            .where(
                BillingEntitlementGrant.workspace_id == subscription.workspace_id,
                BillingEntitlementGrant.ends_at > current,
            )
            .order_by(BillingEntitlementGrant.starts_at)
        )
    )
    if not grants or utc(grants[0].starts_at) > current:
        raise PurchaseError("Оплаченные периоды требуют сверки. Обратитесь в поддержку")
    segments = []
    previous_end = None
    for grant in grants:
        if previous_end is not None and utc(grant.starts_at) > previous_end:
            cursor = previous_end
            for credit in credits:
                if utc(credit.applied_start) == cursor:
                    cursor = utc(credit.applied_end)
            if cursor != utc(grant.starts_at):
                raise PurchaseError("Оплаченные периоды требуют сверки. Обратитесь в поддержку")
        previous_end = utc(grant.ends_at)
        storage = await db.scalar(
            select(BillingStorageEntitlementGrant)
            .where(
                BillingStorageEntitlementGrant.workspace_id == subscription.workspace_id,
                BillingStorageEntitlementGrant.base_grant_id == grant.id,
                BillingStorageEntitlementGrant.starts_at <= max(current, utc(grant.starts_at)),
                BillingStorageEntitlementGrant.ends_at == grant.ends_at,
            )
            .order_by(BillingStorageEntitlementGrant.capacity_bytes.desc())
            .limit(1)
        )
        capacity = storage.capacity_bytes if storage else PERSONAL_STORAGE_BYTES
        if (
            storage is not None
            and storage.capacity_bytes > PERSONAL_STORAGE_BYTES
            and (storage.catalog_version_id is None or storage.full_period_amount_minor <= 0)
        ):
            raise PurchaseError(
                "Цена ранее оплаченного объёма требует сверки. Обратитесь в поддержку"
            )
        if (
            storage is None
            and utc(grant.starts_at) <= current
            and await effective_paid_storage(db, subscription=subscription, now=current)
            > PERSONAL_STORAGE_BYTES
        ):
            raise PurchaseError("Ранее оплаченный объём требует сверки. Обратитесь в поддержку")
        target_price = catalog.get((target_capacity_bytes, grant.cycle))
        if target_capacity_bytes != PERSONAL_STORAGE_BYTES and target_price is None:
            raise PurchaseError("Цена выбранного объёма временно недоступна")
        segments.append(
            StorageSegment(
                grant.id,
                utc(grant.starts_at),
                utc(grant.ends_at),
                grant.cycle,
                capacity,
                storage.full_period_amount_minor if storage else 0,
                target_price.amount_minor if target_price else 0,
                target_price.id if target_price else grant.id,
            )
        )
    return quote_storage_purchase(
        segments=segments,
        target_capacity_bytes=target_capacity_bytes,
        now=current,
        discount_percent=discount_percent,
        provider_floor_minor=provider_floor_minor,
        allow_bonus_gaps=True,
    )


async def storage_period_timeline(
    db: AsyncSession, *, subscription, now: datetime, upgraded_segments=()
) -> list[dict]:
    from twobrain_rec_server.db.models import BillingEntitlementGrant, TimeCreditLedgerEntry

    replacements = {str(item.base_grant_id): item.capacity_bytes for item in upgraded_segments}
    periods = list(
        await db.scalars(
            select(BillingEntitlementGrant)
            .where(
                BillingEntitlementGrant.workspace_id == subscription.workspace_id,
                BillingEntitlementGrant.ends_at > now,
            )
            .order_by(BillingEntitlementGrant.starts_at)
        )
    )
    timeline = []
    for period in periods:
        start = max(utc(now), utc(period.starts_at))
        capacity = replacements.get(str(period.id))
        if capacity is None:
            capacity = await effective_paid_storage(db, subscription=subscription, now=start)
        timeline.append(
            {
                "starts_at": start.isoformat(),
                "ends_at": utc(period.ends_at).isoformat(),
                "capacity_bytes": capacity,
                "bonus": False,
            }
        )
    credits = await db.scalars(
        select(TimeCreditLedgerEntry).where(
            TimeCreditLedgerEntry.workspace_id == subscription.workspace_id,
            TimeCreditLedgerEntry.state == "applied",
            TimeCreditLedgerEntry.applied_end > now,
        )
    )
    for credit in credits:
        start = max(utc(now), utc(credit.applied_start))
        timeline.append(
            {
                "starts_at": start.isoformat(),
                "ends_at": utc(credit.applied_end).isoformat(),
                "capacity_bytes": max(
                    PERSONAL_STORAGE_BYTES,
                    credit.capacity_snapshot_bytes
                    or subscription.capacity_bytes
                    or PERSONAL_STORAGE_BYTES,
                ),
                "bonus": True,
            }
        )
    return sorted(timeline, key=lambda item: item["starts_at"])


async def validate_acceptance_campaign(
    db: AsyncSession, *, policy: dict, workspace_id: UUID, now: datetime
) -> None:
    """A scoped acceptance campaign cannot silently become an unlimited promo."""
    budget_id = policy.get("acceptance_budget_id")
    if budget_id is None:
        return
    try:
        identifier = UUID(budget_id)
    except (TypeError, ValueError, AttributeError) as exc:
        raise PurchaseError("Проверочная акция недоступна") from exc
    budget = await db.scalar(
        select(BillingAcceptanceBudget).where(
            BillingAcceptanceBudget.id == identifier,
            BillingAcceptanceBudget.workspace_id == workspace_id,
        )
    )
    if (
        policy.get("workspace_id") != str(workspace_id)
        or budget is None
        or not budget.enabled
        or utc(budget.expires_at) <= utc(now)
    ):
        raise PurchaseError("Проверочное окно оплаты закрыто")
