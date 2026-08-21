from datetime import UTC, datetime
from uuid import UUID

import pytest

from twobrain_rec_server.billing.catalog import (
    CatalogNotApproved,
    plan_descriptor,
    validate_plan_version,
)
from twobrain_rec_server.billing.checkout import (
    CheckoutPreview,
    build_checkout_intent,
    checkout_preview,
)
from twobrain_rec_server.billing.promotions import PromoCode
from twobrain_rec_server.db.models import BillingPlanVersion

WORKSPACE_ID = UUID("22222222-2222-4222-8222-222222222222")


def test_catalog_and_checkout_snapshot_use_rub_minor_units_and_exact_cycles() -> None:
    personal = plan_descriptor("personal")
    assert (personal.monthly_amount_minor, personal.annual_amount_minor) == (100_000, 1_000_000)
    monthly = checkout_preview(plan_code="personal", cycle="month")
    annual = checkout_preview(plan_code="personal", cycle="year")
    assert monthly == CheckoutPreview("personal", "month", 100_000, 100_000, None)
    assert annual == CheckoutPreview("personal", "year", 1_000_000, 1_000_000, None)


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


def test_enabled_catalog_version_is_the_checkout_snapshot_authority() -> None:
    row = BillingPlanVersion(
        plan_code="personal",
        version=7,
        cycle="month",
        amount_minor=81_000,
        currency="RUB",
        storage_bytes=2_000_000_000,
        processing_mode="unlimited",
        enabled_for_checkout=True,
        policy_snapshot={"offer_version": "personal-v7", "receipt_policy": "r2"},
        effective_from=datetime(2026, 8, 1, tzinfo=UTC),
    )
    snapshot = validate_plan_version(row, now=datetime(2026, 8, 8, tzinfo=UTC))
    preview = checkout_preview(
        plan_code="personal",
        cycle="month",
        catalog_snapshot=snapshot,
    )
    assert preview.list_amount_minor == 81_000
    assert snapshot.as_dict()["catalog_version"] == 7
    assert snapshot.as_dict()["offer_version"] == "personal-v7"


@pytest.mark.parametrize(
    "changes",
    [
        {"enabled_for_checkout": False},
        {"policy_snapshot": {}},
        {"effective_until": datetime(2026, 8, 8, tzinfo=UTC)},
    ],
)
def test_catalog_gate_fails_closed_for_unapproved_or_expired_rows(changes: dict[str, object]) -> None:
    values: dict[str, object] = {
        "plan_code": "personal",
        "version": 1,
        "cycle": "month",
        "amount_minor": 79_000,
        "currency": "RUB",
        "storage_bytes": 2_000_000_000,
        "processing_mode": "unlimited",
        "enabled_for_checkout": True,
        "policy_snapshot": {"offer_version": "personal-v1"},
        "effective_from": datetime(2026, 8, 1, tzinfo=UTC),
    }
    values.update(changes)
    with pytest.raises(CatalogNotApproved, match="approved|enabled|expired|offer"):
        validate_plan_version(
            BillingPlanVersion(**values),
            now=datetime(2026, 8, 8, tzinfo=UTC),
        )


def test_catalog_snapshot_rejects_selection_mismatch_without_repricing() -> None:
    row = BillingPlanVersion(
        plan_code="personal",
        version=2,
        cycle="year",
        amount_minor=790_000,
        currency="RUB",
        storage_bytes=2_000_000_000,
        processing_mode="unlimited",
        enabled_for_checkout=True,
        policy_snapshot={"offer_version": "personal-v2"},
    )
    snapshot = validate_plan_version(row, now=datetime.now(UTC))
    with pytest.raises(ValueError, match="does not match"):
        checkout_preview(plan_code="personal", cycle="month", catalog_snapshot=snapshot)


def test_catalog_snapshot_rejects_unbounded_policy_payload() -> None:
    row = BillingPlanVersion(
        plan_code="personal",
        version=3,
        cycle="month",
        amount_minor=79_000,
        currency="RUB",
        storage_bytes=2_000_000_000,
        processing_mode="unlimited",
        enabled_for_checkout=True,
        policy_snapshot={"offer_version": "personal-v3", "provider_payload": {"secret": "no"}},
    )
    with pytest.raises(CatalogNotApproved, match="bounded"):
        validate_plan_version(row, now=datetime.now(UTC))
