from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from twobrain_rec_server.billing.catalog import plan_descriptor
from twobrain_rec_server.billing.promotions import PromoCode, apply_promo


@dataclass(frozen=True, slots=True)
class CheckoutPreview:
    plan_code: str
    cycle: str
    list_amount_minor: int
    payable_amount_minor: int
    promo_code: str | None


@dataclass(frozen=True, slots=True)
class CheckoutIntent:
    operation_id: UUID
    workspace_id: UUID
    idempotency_key: str
    invoice_number: str
    preview: CheckoutPreview


def build_checkout_intent(*, workspace_id: UUID, idempotency_key: str, preview: CheckoutPreview) -> CheckoutIntent:
    key = idempotency_key.strip()
    if not key or len(key) > 240:
        raise ValueError("idempotency key is invalid")
    operation_id = uuid4()
    return CheckoutIntent(operation_id, workspace_id, key, f"INV-{operation_id.hex[:20].upper()}", preview)


def checkout_preview(*, plan_code: str, cycle: str, promo: PromoCode | None = None, provider_floor_minor: int = 1) -> CheckoutPreview:
    plan = plan_descriptor(plan_code)  # type: ignore[arg-type]
    if cycle not in {"month", "year"}:
        raise ValueError("cycle must be month or year")
    amount = plan.monthly_amount_minor if cycle == "month" else plan.annual_amount_minor
    if amount is None:
        raise ValueError("selected plan is not payable")
    payable = apply_promo(amount_minor=amount, promo=promo, plan_code=plan_code, provider_floor_minor=provider_floor_minor) if promo else amount
    return CheckoutPreview(plan_code, cycle, amount, payable, promo.code if promo else None)
