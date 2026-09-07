"""Server-side promotion policy and reservation primitives.

Promotion campaigns are deliberately supplied by configuration/database.  This
module never invents a live campaign or stores a raw code in an event payload.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Literal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    PromotionCampaign,
    PromotionRedemption,
)


class PromoError(ValueError):
    """A safe, user-facing promotion error with a stable reason code."""

    def __init__(self, message: str, *, code: str = "promo_invalid") -> None:
        super().__init__(message)
        self.code = code


PromoState = Literal["reserved", "redeemed", "released", "expired"]


@dataclass(frozen=True, slots=True)
class PromoCode:
    code: str
    discount_percent: int
    plan_code: str
    max_redemptions: int
    redeemed: int = 0
    cycle: str | None = None
    campaign_version: str = "configured"
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    max_per_workspace: int = 1
    benefit_kind: Literal["discount", "gift"] = "discount"
    gift_days: int | None = None
    audience: str = "all"
    target_user_id: UUID | None = None
    budget_minor: int | None = None
    budget_used_minor: int = 0
    code_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class PromoEligibility:
    normalized_code: str
    code_hash: str
    discount_percent: int
    campaign_version: str
    benefit_kind: Literal["discount", "gift"] = "discount"
    gift_days: int | None = None


@dataclass(frozen=True, slots=True)
class PromoReservation:
    reservation_key: str
    workspace_id: UUID
    code_hash: str
    list_amount_minor: int
    payable_amount_minor: int
    state: PromoState = "reserved"


async def _reserve_promotion_redemption(
    db: AsyncSession,
    *,
    campaign_id: UUID,
    workspace_id: UUID,
    invoice_id: UUID | None,
    reservation_key: str,
    code_hash: str,
    list_amount_minor: int,
    payable_amount_minor: int,
    discount_percent: int,
    expires_at: datetime,
) -> UUID:
    redemption_id = await db.scalar(
        text(
            "select public.billing_reserve_promotion_redemption("
            ":campaign_id,:workspace_id,:invoice_id,:reservation_key,:code_hash,"
            ":list_amount,:payable_amount,:discount,:expires_at)"
        ),
        {
            "campaign_id": campaign_id,
            "workspace_id": workspace_id,
            "invoice_id": invoice_id,
            "reservation_key": reservation_key,
            "code_hash": code_hash,
            "list_amount": list_amount_minor,
            "payable_amount": payable_amount_minor,
            "discount": discount_percent,
            "expires_at": expires_at,
        },
    )
    if not isinstance(redemption_id, UUID):
        raise PromoError("Промокод временно недоступен", code="promo_unavailable")
    return redemption_id


async def _finalize_promotion_redemption(
    db: AsyncSession,
    *,
    redemption_id: UUID,
    to_state: Literal["redeemed", "released", "expired"],
    at: datetime,
) -> bool:
    return bool(await db.scalar(
        text("select public.billing_finalize_promotion_redemption(:id,:state,:at)"),
        {"id": redemption_id, "state": to_state, "at": at},
    ))


def promotion_cost_minor(*, amount_minor: int, promo: PromoCode) -> int:
    """Return the monetary budget consumed by one accepted application."""
    if amount_minor < 0:
        raise PromoError("Сумма акции недоступна", code="promo_invalid")
    if promo.benefit_kind == "gift":
        return amount_minor
    payable = amount_minor * (100 - promo.discount_percent) // 100
    return amount_minor - payable


_DASH_TRANSLATION = str.maketrans({char: "-" for char in "‐‑‒–—﹘﹣－"})


def normalize_promo(value: str) -> str:
    """Normalize a code while rejecting Unicode confusables and whitespace."""
    if not isinstance(value, str):
        raise PromoError("Промокод не распознан")
    normalized = unicodedata.normalize("NFKC", value).translate(_DASH_TRANSLATION).strip().upper()
    if not 3 <= len(normalized) <= 48 or not all(
        char.isascii() and (char.isalnum() or char in "-_") for char in normalized
    ):
        raise PromoError("Промокод не распознан")
    return normalized


def promo_code_hash(value: str) -> str:
    """Return the non-reversible lookup digest used by campaign rows."""
    return sha256(normalize_promo(value).encode("ascii")).hexdigest()


def _aware(now: datetime) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None:
        raise PromoError("Промокод временно недоступен", code="promo_unavailable")
    return now.astimezone(UTC)


def check_eligibility(
    *,
    promo: PromoCode,
    plan_code: str,
    cycle: str,
    now: datetime,
    workspace_redemptions: int = 0,
    active_reservations: int = 0,
    subject_user_id: UUID | None = None,
    has_paid_purchase: bool | None = None,
    has_paid_plan_purchase: bool | None = None,
    active_paid_access: bool | None = None,
    budget_reserved_minor: int = 0,
    budget_cost_minor: int = 0,
) -> PromoEligibility:
    """Validate scope, window and caps before an invoice is created."""
    normalized = normalize_promo(promo.code)
    if promo.plan_code != plan_code or (promo.cycle is not None and promo.cycle != cycle):
        raise PromoError("Промокод недоступен для этого тарифа", code="promo_not_eligible")
    if promo.max_redemptions < 1:
        raise PromoError("Промокод имеет неверные условия", code="promo_invalid")
    if promo.benefit_kind not in {"discount", "gift"}:
        raise PromoError("Промокод имеет неверные условия", code="promo_invalid")
    if promo.benefit_kind == "discount" and not 1 <= promo.discount_percent <= 99:
        raise PromoError("Промокод имеет неверные условия", code="promo_invalid")
    if promo.benefit_kind == "gift" and (promo.gift_days is None or not 1 <= promo.gift_days <= 365):
        raise PromoError("Промокод имеет неверные условия", code="promo_invalid")
    if promo.audience not in {"all", "never_paid", "first_purchase", "selected", "former_paid"}:
        raise PromoError("Промокод имеет неверные условия", code="promo_invalid")
    if promo.target_user_id is not None and promo.target_user_id != subject_user_id:
        raise PromoError("Промокод предназначен для другого пользователя", code="promo_not_eligible")
    if promo.audience == "selected" and promo.target_user_id != subject_user_id:
        raise PromoError("Промокод предназначен для выбранных пользователей", code="promo_not_eligible")
    if promo.audience == "never_paid" and has_paid_purchase is True:
        raise PromoError("Промокод доступен только новым плательщикам", code="promo_not_eligible")
    if promo.audience == "first_purchase" and has_paid_plan_purchase is True:
        raise PromoError("Промокод доступен только для первой покупки тарифа", code="promo_not_eligible")
    if promo.audience == "former_paid" and (has_paid_purchase is not True or active_paid_access is True):
        raise PromoError("Промокод доступен бывшим платным пользователям", code="promo_not_eligible")
    if promo.budget_minor is not None and promo.budget_used_minor + budget_reserved_minor + budget_cost_minor > promo.budget_minor:
        raise PromoError("Бюджет акции исчерпан", code="promo_budget_exhausted")
    if promo.redeemed >= promo.max_redemptions or workspace_redemptions >= promo.max_per_workspace:
        raise PromoError("Лимит промокода уже исчерпан", code="promo_exhausted")
    if active_reservations >= promo.max_redemptions - promo.redeemed:
        raise PromoError("Промокод временно занят, повторите позже", code="promo_reserved")
    current = _aware(now)
    if promo.starts_at is not None and current < _aware(promo.starts_at):
        raise PromoError("Промокод ещё не действует", code="promo_not_started")
    if promo.ends_at is not None and current >= _aware(promo.ends_at):
        raise PromoError("Срок действия промокода закончился", code="promo_expired")
    return PromoEligibility(normalized, promo_code_hash(normalized), promo.discount_percent, promo.campaign_version, promo.benefit_kind, promo.gift_days)


def apply_promo(
    *,
    amount_minor: int,
    promo: PromoCode,
    plan_code: str,
    provider_floor_minor: int,
    cycle: str | None = None,
) -> int:
    if amount_minor <= 0 or provider_floor_minor <= 0:
        raise PromoError("Сумма платежа недоступна", code="promo_invalid")
    # Keep the historical helper deterministic; window/cap checks belong to
    # check_eligibility where the authoritative clock and counters are known.
    if promo.benefit_kind == "gift":
        if promo.plan_code != plan_code or (promo.cycle is not None and cycle is not None and promo.cycle != cycle):
            raise PromoError("Промокод недоступен для этого тарифа", code="promo_not_eligible")
        if promo.gift_days is None or not 1 <= promo.gift_days <= 365:
            raise PromoError("Промокод имеет неверные условия", code="promo_invalid")
        return 0
    if (
        promo.plan_code != plan_code
        or promo.redeemed >= promo.max_redemptions
        or (promo.cycle is not None and cycle is not None and promo.cycle != cycle)
    ):
        raise PromoError("Промокод недоступен для этого тарифа", code="promo_not_eligible")
    if not 1 <= promo.discount_percent <= 99:
        raise PromoError("Промокод имеет неверные условия", code="promo_invalid")
    discounted = amount_minor * (100 - promo.discount_percent) // 100
    if discounted < provider_floor_minor:
        raise PromoError("Скидка не может примениться к минимальной сумме платежа", code="provider_floor")
    return discounted


def choose_best_discount(
    *,
    amount_minor: int,
    plan_code: str,
    cycle: str,
    provider_floor_minor: int,
    candidates: Sequence[PromoCode],
    strict_first: bool = False,
) -> tuple[PromoCode | None, int]:
    """Choose one eligible discount without allowing promo stacking.

    The checkout route still performs the authoritative DB reservation.  This
    helper only makes the deterministic price-selection rule explicit: the
    candidate producing the lowest payable amount wins, ties preserve the
    caller's order (configured promo before the system referral candidate).
    Candidates that do not apply to the selected cycle or fall below the
    provider floor are ignored; an empty result means list price. When the
    first candidate is an explicitly entered code, ``strict_first`` keeps an
    invalid code from silently turning into a full-price checkout.
    """
    if amount_minor <= 0:
        raise PromoError("Сумма платежа недоступна", code="promo_invalid")
    best: tuple[PromoCode, int] | None = None
    for index, candidate in enumerate(candidates):
        try:
            payable = 0 if candidate.benefit_kind == "gift" else apply_promo(
                amount_minor=amount_minor,
                promo=candidate,
                plan_code=plan_code,
                provider_floor_minor=provider_floor_minor,
                cycle=cycle,
            )
        except PromoError:
            if strict_first and index == 0:
                raise
            continue
        if best is None or payable < best[1]:
            best = (candidate, payable)
    return (best if best is not None else (None, amount_minor))


def reserve_promo(
    *,
    reservation_key: str,
    workspace_id: UUID,
    eligibility: PromoEligibility,
    list_amount_minor: int,
    provider_floor_minor: int,
    promo: PromoCode,
) -> PromoReservation:
    """Create an immutable invoice snapshot; persistence/uniqueness is DB-owned."""
    if not reservation_key.strip() or len(reservation_key) > 240:
        raise PromoError("Идентификатор оплаты недействителен", code="promo_invalid")
    payable = 0 if promo.benefit_kind == "gift" else apply_promo(
        amount_minor=list_amount_minor,
        promo=promo,
        plan_code=promo.plan_code,
        provider_floor_minor=provider_floor_minor,
        cycle=promo.cycle,
    )
    return PromoReservation(reservation_key, workspace_id, eligibility.code_hash, list_amount_minor, payable)


async def redeem_invoice_promo(db: AsyncSession, *, invoice_id: UUID, now: datetime) -> Literal["redeemed", "duplicate", "none"]:
    """Commit a reservation only after authoritative provider success."""
    row = await db.scalar(
        select(PromotionRedemption).where(PromotionRedemption.invoice_id == invoice_id)
    )
    if row is None:
        return "none"
    if row.state == "redeemed":
        return "duplicate"
    if row.state != "reserved":
        return "none"
    current = _aware(now)
    if await _finalize_promotion_redemption(db, redemption_id=row.id, to_state="redeemed", at=current):
        return "redeemed"
    # A provider success can race with the campaign cap.  Release the
    # reservation through the same authority boundary; maintenance is the
    # normal caller for this path and may release a succeeded invoice after
    # the cap has been consumed by an earlier payment.
    if await _finalize_promotion_redemption(db, redemption_id=row.id, to_state="released", at=current):
        return "none"
    return "none"


async def redeem_gift_promo(
    db: AsyncSession,
    *,
    campaign_id: UUID,
    code_hash: str,
    workspace_id: UUID,
    subject_user_id: UUID,
    plan_version_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    timezone: str,
    reservation_key: str,
    list_amount_minor: int,
    now: datetime,
) -> Literal["redeemed", "duplicate"]:
    """Atomically consume a gift code without creating an invoice."""
    current = _aware(now)
    existing = await db.scalar(
        select(PromotionRedemption).where(
            PromotionRedemption.workspace_id == workspace_id,
            PromotionRedemption.code_hash == code_hash,
            PromotionRedemption.state == "redeemed",
        )
    )
    if existing is not None:
        return "duplicate"
    redemption_id = await _reserve_promotion_redemption(
        db,
        campaign_id=campaign_id,
        workspace_id=workspace_id,
        invoice_id=None,
        reservation_key=reservation_key,
        code_hash=code_hash,
        list_amount_minor=list_amount_minor,
        payable_amount_minor=0,
        discount_percent=0,
        expires_at=current + timedelta(minutes=15),
    )
    await db.scalar(
        text(
            "select public.billing_redeem_promotion_access("
            ":workspace_id, :subject_user_id, :plan_version_id, :starts_at, :ends_at, "
            ":timezone, :source_ref, :reason)"
        ),
        {
            "workspace_id": workspace_id,
            "subject_user_id": subject_user_id,
            "plan_version_id": plan_version_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "timezone": timezone,
            "source_ref": reservation_key,
            "reason": "Подарочный доступ по опубликованной акции",
        },
    )
    if not await _finalize_promotion_redemption(db, redemption_id=redemption_id, to_state="redeemed", at=current):
        raise PromoError("Промокод не удалось подтвердить", code="promo_unavailable")
    return "redeemed"


async def release_invoice_promo(db: AsyncSession, *, invoice_id: UUID, now: datetime) -> bool:
    """Release a pending reservation after authoritative cancellation/expiry."""
    row = await db.scalar(
        select(PromotionRedemption).where(PromotionRedemption.invoice_id == invoice_id).with_for_update()
    )
    if row is None or row.state != "reserved":
        return False
    return await _finalize_promotion_redemption(
        db, redemption_id=row.id, to_state="released", at=_aware(now)
    )


async def release_payment_promo(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    provider_payment_id: str,
    now: datetime,
) -> bool:
    operation = await db.scalar(
        select(BillingOperation).where(
            BillingOperation.workspace_id == workspace_id,
            BillingOperation.provider_id == provider_payment_id,
        ).with_for_update()
    )
    if operation is None:
        return False
    invoice = await db.scalar(select(BillingInvoice).where(BillingInvoice.operation_id == operation.id).with_for_update())
    if invoice is None:
        return False
    return await release_invoice_promo(db, invoice_id=invoice.id, now=now)


async def expire_promo_reservations(db: AsyncSession, *, now: datetime) -> int:
    """Release only pre-provider reservations; provider-pending stays locked."""
    current = _aware(now)
    rows = await db.execute(
        select(PromotionRedemption, BillingOperation, PromotionCampaign)
        .join(BillingInvoice, BillingInvoice.id == PromotionRedemption.invoice_id)
        .join(BillingOperation, BillingOperation.id == BillingInvoice.operation_id)
        .join(PromotionCampaign, PromotionCampaign.id == PromotionRedemption.campaign_id)
        .where(
            PromotionRedemption.state == "reserved",
            PromotionRedemption.expires_at.is_not(None),
            PromotionRedemption.expires_at <= current,
            BillingOperation.state == "scheduled",
            BillingOperation.provider_id.is_(None),
        )
    )
    expired = 0
    for row, _operation, _campaign in rows:
        if await _finalize_promotion_redemption(
            db, redemption_id=row.id, to_state="expired", at=current
        ):
            expired += 1
    await db.flush()
    return expired
