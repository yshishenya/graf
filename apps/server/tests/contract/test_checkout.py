from twobrain_rec_server.billing.checkout import checkout_preview
from twobrain_rec_server.billing.promotions import PromoCode


def test_checkout_preview_snapshots_cycle_and_discounted_price() -> None:
    preview = checkout_preview(
        plan_code="personal",
        cycle="year",
        promo=PromoCode("YEAR10", 10, "personal", 100),
    )
    assert preview.list_amount_minor == 790_000
    assert preview.payable_amount_minor == 711_000
    assert preview.promo_code == "YEAR10"
