import pytest

from twobrain_rec_server.billing.catalog import PlanCatalogSnapshot
from twobrain_rec_server.billing.checkout import checkout_preview
from twobrain_rec_server.billing.promotions import PromoCode, PromoError, normalize_promo
from twobrain_rec_server.cabinet.web_routes.billing import (
    _choose_checkout_discount,
    checkout_preview_labels,
)


def test_checkout_preview_revalidates_cycle_and_provider_floor() -> None:
    promo = PromoCode("YEAR10", 10, "personal", 1, cycle="year")
    assert checkout_preview(plan_code="personal", cycle="year", promo=promo).payable_amount_minor == 900_000
    with pytest.raises(PromoError):
        checkout_preview(
            plan_code="personal",
            cycle="month",
            promo=promo,
            provider_floor_minor=100,
        )


def test_promo_checkout_input_is_normalized_before_any_snapshot() -> None:
    assert normalize_promo("  save‐10 ") == "SAVE-10"
    with pytest.raises(PromoError):
        normalize_promo("SАVE-10")


def test_checkout_preview_labels_show_discount_and_full_next_period_amount() -> None:
    preview = checkout_preview(
        plan_code="personal",
        cycle="month",
        promo=PromoCode("SAVE10", 10, "personal", 1),
        catalog_snapshot=PlanCatalogSnapshot(
            plan_code="personal",
            version=1,
            cycle="month",
            amount_minor=79_000,
            currency="RUB",
            storage_bytes=2_000_000_000,
            processing_mode="unlimited",
            offer_version="test-v1",
            policy_snapshot={},
        ),
    )
    labels = checkout_preview_labels(preview, discount_percent=10)
    assert labels == {
        "cycle_label": "месяц",
        "list_amount_label": "790 ₽",
        "discount_label": "−79 ₽ (10%)",
        "payable_amount_label": "711 ₽",
        "next_amount_label": "790 ₽",
    }
    referral_labels = checkout_preview_labels(
        preview,
        discount_percent=10,
        discount_source="referral",
    )
    assert referral_labels["discount_label"] == "−79 ₽ (реферальная скидка, 10%)"


def test_checkout_preview_uses_the_better_referral_without_stacking() -> None:
    configured = PromoCode("SAVE5", 5, "personal", 1)
    referral = PromoCode("REFERRAL_INTRO", 10, "personal", 1)

    chosen, source = _choose_checkout_discount(
        amount_minor=79_000,
        cycle="month",
        provider_floor_minor=100,
        promo=configured,
        referral_candidate=referral,
    )

    assert chosen == referral
    assert source == "referral"
