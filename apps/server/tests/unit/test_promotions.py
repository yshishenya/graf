from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from twobrain_rec_server.billing.promotions import (
    PromoCode,
    PromoError,
    apply_promo,
    check_eligibility,
    normalize_promo,
    promo_code_hash,
    reserve_promo,
)


def test_promo_normalizes_and_respects_scope_caps_and_floor() -> None:
    promo = PromoCode("WELCOME-10", 10, "personal", 1)
    assert normalize_promo(" welcome‐10 ".replace("‐", "-")) == "WELCOME-10"
    assert apply_promo(amount_minor=79_000, promo=promo, plan_code="personal", provider_floor_minor=1) == 71_100
    with pytest.raises(PromoError):
        apply_promo(amount_minor=79_000, promo=promo, plan_code="free", provider_floor_minor=1)
    with pytest.raises(PromoError):
        normalize_promo("bad code")


def test_promo_eligibility_distinguishes_window_caps_and_reservation_snapshot() -> None:
    now = datetime(2026, 8, 7, tzinfo=UTC)
    promo = PromoCode(
        "WELCOME-10",
        10,
        "personal",
        2,
        campaign_version="welcome-v2",
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=1),
    )
    eligibility = check_eligibility(
        promo=promo,
        plan_code="personal",
        cycle="month",
        now=now,
    )
    assert eligibility.code_hash == promo_code_hash("welcome-10")
    reservation = reserve_promo(
        reservation_key="checkout-1",
        workspace_id=UUID("11111111-1111-1111-1111-111111111111"),
        eligibility=eligibility,
        list_amount_minor=79_000,
        provider_floor_minor=1,
        promo=promo,
    )
    assert reservation.payable_amount_minor == 71_100
    with pytest.raises(PromoError, match="Срок"):
        check_eligibility(
            promo=promo,
            plan_code="personal",
            cycle="month",
            now=now + timedelta(days=2),
        )


def test_promo_rejects_cyrillic_confusable_and_zero_total() -> None:
    with pytest.raises(PromoError):
        normalize_promo("WЕLCOME")
    with pytest.raises(PromoError, match="минимальной"):
        apply_promo(
            amount_minor=100,
            promo=PromoCode("SAVE99", 99, "personal", 1),
            plan_code="personal",
            provider_floor_minor=2,
        )
