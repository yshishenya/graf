from uuid import UUID

import pytest

from twobrain_rec_server.billing.catalog import plan_descriptor
from twobrain_rec_server.billing.checkout import (
    CheckoutPreview,
    build_checkout_intent,
    checkout_preview,
)
from twobrain_rec_server.billing.promotions import PromoCode

WORKSPACE_ID = UUID("22222222-2222-4222-8222-222222222222")


def test_catalog_and_checkout_snapshot_use_rub_minor_units_and_exact_cycles() -> None:
    personal = plan_descriptor("personal")
    assert (personal.monthly_amount_minor, personal.annual_amount_minor) == (79_000, 790_000)
    monthly = checkout_preview(plan_code="personal", cycle="month")
    annual = checkout_preview(plan_code="personal", cycle="year")
    assert monthly == CheckoutPreview("personal", "month", 79_000, 79_000, None)
    assert annual == CheckoutPreview("personal", "year", 790_000, 790_000, None)


def test_checkout_intent_has_stable_safe_reference_and_rejects_bad_keys() -> None:
    preview = checkout_preview(plan_code="personal", cycle="month")
    intent = build_checkout_intent(
        workspace_id=WORKSPACE_ID,
        idempotency_key="checkout-2026-08-07",
        preview=preview,
    )
    assert intent.workspace_id == WORKSPACE_ID
    assert intent.invoice_number.startswith("INV-")
    with pytest.raises(ValueError, match="idempotency"):
        build_checkout_intent(workspace_id=WORKSPACE_ID, idempotency_key=" ", preview=preview)


def test_promo_preview_never_drops_below_provider_floor() -> None:
    promo = PromoCode(
        code="WELCOME10",
        plan_code="personal",
        discount_percent=99,
        max_redemptions=10,
    )
    preview = checkout_preview(
        plan_code="personal",
        cycle="month",
        promo=promo,
        provider_floor_minor=100,
    )
    assert preview.payable_amount_minor >= 100
    with pytest.raises(ValueError, match="cycle"):
        checkout_preview(plan_code="personal", cycle="week")
