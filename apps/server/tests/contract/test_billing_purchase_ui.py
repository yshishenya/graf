from twobrain_rec_server.billing.catalog import plan_descriptor
from twobrain_rec_server.cabinet.templates import render_template


def test_checkout_discloses_components_period_and_undiscounted_renewal():
    html = render_template(
        "cabinet/pages/billing_checkout_content.html",
        billing_enabled=True,
        catalog_ready=True,
        plan=plan_descriptor("personal"),
        checkout_quote_id="synthetic-bound-quote",
        checkout_idempotency_key="synthetic-idempotency",
        checkout_cycle="month",
        monthly_price_label="1 290 ₽",
        annual_price_label="12 900 ₽",
        catalog_storage_label="5 ГБ",
        checkout_base_price_label="1 000 ₽",
        checkout_storage_price_label="290 ₽",
        checkout_period_label="27 сентября — 27 октября 2026",
        checkout_next_attempt_label="24 октября 2026",
        checkout_preview={
            "payable_amount_label": "12.90 ₽",
            "list_amount_label": "1 290 ₽",
            "discount_label": "−1 277.10 ₽ (99%)",
            "next_amount_label": "1 290 ₽",
            "cycle_label": "месяц",
        },
    )
    assert 'name="quote_id" value="synthetic-bound-quote"' in html
    assert "1 000 ₽" in html and "290 ₽" in html
    assert "27 сентября — 27 октября 2026" in html
    assert "24 октября 2026" in html
    assert "Скидка действует только на эту оплату" in html
    assert "Оплатить 12.90 ₽" in html
    assert " checked" not in html


def test_checkout_without_valid_quote_cannot_submit_money():
    html = render_template(
        "cabinet/pages/billing_checkout_content.html",
        billing_enabled=True,
        catalog_ready=True,
        plan=plan_descriptor("personal"),
        promo_preview_error="Расчёт изменился",
    )
    assert 'action="/billing/checkout/start"' not in html
    assert 'role="alert"' in html
