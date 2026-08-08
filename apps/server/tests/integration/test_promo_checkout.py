import pytest

from twobrain_rec_server.billing.checkout import checkout_preview
from twobrain_rec_server.billing.promotions import PromoCode, PromoError, normalize_promo


def test_checkout_preview_revalidates_cycle_and_provider_floor() -> None:
    promo = PromoCode("YEAR10", 10, "personal", 1, cycle="year")
    assert checkout_preview(plan_code="personal", cycle="year", promo=promo).payable_amount_minor == 711_000
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
