from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from uuid import UUID, uuid4

from twobrain_rec_server.billing.catalog import PlanCatalogSnapshot, plan_descriptor
from twobrain_rec_server.billing.promotions import (
    PromoCode,
    apply_promo,
    normalize_promo,
    promo_code_hash,
)


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


def checkout_preview(
    *,
    plan_code: str,
    cycle: str,
    promo: PromoCode | None = None,
    provider_floor_minor: int = 1,
    catalog_snapshot: PlanCatalogSnapshot | None = None,
) -> CheckoutPreview:
    if catalog_snapshot is not None:
        if catalog_snapshot.plan_code != plan_code or catalog_snapshot.cycle != cycle:
            raise ValueError("catalog snapshot does not match checkout selection")
        amount = catalog_snapshot.amount_minor
    else:
        plan = plan_descriptor(plan_code)  # type: ignore[arg-type]
        amount = plan.monthly_amount_minor if cycle == "month" else plan.annual_amount_minor
    if cycle not in {"month", "year"}:
        raise ValueError("cycle must be month or year")
    if amount is None:
        raise ValueError("selected plan is not payable")
    payable = (
        (0 if promo.benefit_kind == "gift" else apply_promo(
            amount_minor=amount,
            promo=promo,
            plan_code=plan_code,
            provider_floor_minor=provider_floor_minor,
            cycle=cycle,
        ))
        if promo
        else amount
    )
    return CheckoutPreview(plan_code, cycle, amount, payable, promo.code if promo else None)


def checkout_quote_fingerprint(
    catalog: PlanCatalogSnapshot, preview: CheckoutPreview, promo: PromoCode | None,
) -> str:
    """Bind consent to displayed terms and the winning discount, including its version."""
    return _fingerprint({
        "catalog": catalog.as_dict(),
        "payable_amount_minor": preview.payable_amount_minor,
        "discount_code_hash": promo_code_hash(promo.code) if promo else None,
        "discount_percent": promo.discount_percent if promo else None,
        "campaign_version": promo.campaign_version if promo else None,
        "benefit_kind": promo.benefit_kind if promo else None,
        "gift_days": promo.gift_days if promo else None,
        "audience": promo.audience if promo else None,
        "target_user_id": str(promo.target_user_id) if promo and promo.target_user_id else None,
    })


def checkout_request_fingerprint(
    *, plan_code: str, cycle: str, promo_code: str | None, expected_quote: str, actor_id: UUID,
) -> str:
    """Compare retries without rerunning mutable campaign/catalog eligibility."""
    return _fingerprint({
        "plan_code": plan_code, "cycle": cycle, "quote": expected_quote,
        "promo_code_hash": promo_code_hash(normalize_promo(promo_code))
            if promo_code and promo_code.strip() else None,
        "actor_id": str(actor_id),
    })


def _fingerprint(value: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
