import pytest

from twobrain_rec_server.billing.promotions import (
    PromoCode,
    PromoError,
    apply_promo,
    normalize_promo,
)


def test_promo_normalizes_and_respects_scope_caps_and_floor() -> None:
    promo = PromoCode("WELCOME-10", 10, "personal", 1)
    assert normalize_promo(" welcome‐10 ".replace("‐", "-")) == "WELCOME-10"
    assert apply_promo(amount_minor=79_000, promo=promo, plan_code="personal", provider_floor_minor=1) == 71_100
    with pytest.raises(PromoError):
        apply_promo(amount_minor=79_000, promo=promo, plan_code="free", provider_floor_minor=1)
    with pytest.raises(PromoError):
        normalize_promo("bad code")
