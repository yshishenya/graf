from datetime import UTC, datetime
from types import SimpleNamespace

from starlette.requests import Request

from twobrain_rec_server.billing.catalog import plan_descriptor
from twobrain_rec_server.billing.usage import format_duration
from twobrain_rec_server.cabinet.templates import render_template
from twobrain_rec_server.cabinet.view_models import settings_category_navigation
from twobrain_rec_server.cabinet.web_routes.billing import _checkout_result_redirect


def test_billing_hub_uses_exact_free_copy_and_external_refund_boundary() -> None:
    html = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor("free"),
        plan_code="free",
        storage_used=0,
        storage_capacity=250_000_000,
        storage_threshold="normal",
        processing_used=0,
        processing_used_label=format_duration(0),
        free_processing_limit_label="300 минут",
        storage_capacity_label="250 000 000",
        storage_capacity_exact_label="250 000 000",
        processing_threshold="normal",
        billing_enabled=False,
        trial_result=None,
    )
    assert "0 мин 0 сек" in html
    assert "300 минут" in html
    assert "250 000 000 байт" in html
    assert "только письмом" in html
    assert "автоматической заявки" in html
    assert "Способ оплаты и увеличение хранилища доступны только владельцу" in html
    assert 'href="/billing/payment-method"' not in html
    assert 'href="/billing/storage"' not in html


def test_subscription_and_usage_surfaces_keep_no_grace_and_unlimited_copy() -> None:
    common = {
        "embedded": False,
        "settings_navigation": settings_category_navigation(active="billing"),
        "settings_active": "billing",
        "csrf_token": "synthetic-csrf",
    }
    subscription_html = render_template(
        "cabinet/pages/billing_subscription_content.html",
        **common,
        subscription=SimpleNamespace(
            plan_code="personal",
            paid_through=datetime(2026, 9, 1, tzinfo=UTC),
            recurring_allowed=False,
            recurring_authority_version=1,
        ),
        active=True,
        result=None,
        method_available=True,
        next_charge_amount_label="790 ₽",
    )
    usage_html = render_template(
        "cabinet/pages/billing_usage_content.html",
        **common,
        plan_code="personal",
        processing_used=0,
        processing_used_label="0 мин 0 сек",
        free_processing_limit_label="300 мин 0 сек",
        processing_threshold="normal",
        processing_unlimited=True,
        storage_used=0,
        storage_reserved=0,
        storage_available=2_000_000_000,
        storage_capacity=2_000_000_000,
        storage_threshold="normal",
    )
    assert "Возобновить автопродление" in subscription_html
    assert "Без лимита по минутам и встречам" in usage_html
    assert "meeting-review.m4a" in usage_html


def test_checkout_requires_explicit_recurring_consent_copy() -> None:
    html = render_template(
        "cabinet/pages/billing_checkout_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        csrf_token="synthetic-csrf",
        plan=plan_descriptor("personal"),
        billing_enabled=True,
        checkout_idempotency_key="synthetic-key",
        checkout_result="consent_required",
        monthly_price_label="790 ₽",
        annual_price_label="7 900 ₽",
        annual_saving_label="Экономия 1 580 ₽ (17%)",
    )
    assert 'name="recurring_consent"' in html
    assert 'name="offer_consent"' in html
    assert 'href="/offer"' in html
    assert "required" in html
    assert "регулярное списание" in html


def test_checkout_offer_consent_error_is_explicit() -> None:
    html = render_template(
        "cabinet/pages/billing_checkout_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        csrf_token="synthetic-csrf",
        plan=plan_descriptor("personal"),
        billing_enabled=True,
        checkout_idempotency_key="synthetic-key",
        checkout_result="offer_required",
        monthly_price_label="790 ₽",
        annual_price_label="7 900 ₽",
        annual_saving_label="Экономия 1 580 ₽ (17%)",
    )
    assert "примите оферту" in html.lower()
    assert "billing-personal-v1" in html


def test_checkout_result_redirect_keeps_promo_out_of_url_and_uses_short_lived_cookie() -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "server": ("graf.test", 443),
            "path": "/billing/checkout/start",
            "headers": [],
            "query_string": b"",
        }
    )
    response = _checkout_result_redirect(request, "promo_invalid", promo_code="WELCOME10")
    assert response.headers["location"] == "/billing/checkout?result=promo_invalid"
    cookie = response.headers["set-cookie"]
    assert "graf_checkout_promo=WELCOME10" in cookie
    assert "Max-Age=300" in cookie
    assert "Path=/billing/checkout" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" in cookie

    malformed = _checkout_result_redirect(request, "promo_invalid", promo_code="bad\ncode")
    assert 'graf_checkout_promo=""' in malformed.headers["set-cookie"]
    assert "Max-Age=0" in malformed.headers["set-cookie"]


def test_payment_method_and_storage_surfaces_keep_safe_boundaries() -> None:
    common = {
        "embedded": False,
        "settings_navigation": settings_category_navigation(active="billing"),
        "settings_active": "billing",
    }
    method_html = render_template(
        "cabinet/pages/billing_payment_method_content.html",
        **common,
        method_label="•••• 4242",
        method_kind="bank_card",
        billing_enabled=True,
    )
    storage_html = render_template(
        "cabinet/pages/billing_storage_content.html",
        **common,
        current_capacity=2_000_000_000,
        addon_options=(5_000_000_000, 20_000_000_000),
        eligible=True,
        billing_enabled=True,
    )
    assert "•••• 4242" in method_html
    assert "Данные карты не проходят через GRAF" in method_html
    assert "meeting-review.m4a" in storage_html
    assert "Исходный WAV" in storage_html
    assert "Увеличить до 5000000000 байт" in storage_html


def test_payment_method_and_discount_screens_expose_recoverable_owner_actions() -> None:
    common = {
        "embedded": False,
        "settings_navigation": settings_category_navigation(active="billing"),
        "settings_active": "billing",
        "csrf_token": "synthetic-csrf",
    }
    method_html = render_template(
        "cabinet/pages/billing_payment_method_content.html",
        **common,
        method_label="•••• 4242",
        method_kind="bank_card",
        method_present=True,
        renewal_allowed=False,
        paid_until_label="08.08.2026, 12:00 (МСК)",
        billing_enabled=True,
        result=None,
    )
    discounts_html = render_template(
        "cabinet/pages/billing_discounts_content.html",
        **common,
        active_promotions=[],
        redemptions=[],
        billing_owner=True,
        billing_enabled=True,
        result=None,
    )
    assert 'action="/billing/payment-method/delete"' in method_html
    assert "Удалить способ оплаты" in method_html
    assert "08.08.2026, 12:00 (МСК)" in method_html
    assert 'action="/billing/discounts/apply"' in discounts_html
    assert 'action="/billing/discounts/remove"' in discounts_html
    assert "Применить" in discounts_html
    assert "Удалить" in discounts_html


def test_payment_method_delete_guard_remains_visible_when_renewal_is_enabled() -> None:
    html = render_template(
        "cabinet/pages/billing_payment_method_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        csrf_token="synthetic-csrf",
        method_label="•••• 4242",
        method_kind="bank_card",
        method_present=True,
        renewal_allowed=True,
        paid_until_label="08.08.2026, 12:00 (МСК)",
        billing_enabled=True,
        result=None,
    )
    assert 'action="/billing/payment-method/delete"' in html
    assert "Сначала отключите автопродление" in html
    assert "Подтвердить удаление" in html


def test_checkout_hides_publishable_price_when_store_is_disabled() -> None:
    html = render_template(
        "cabinet/pages/billing_checkout_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        csrf_token="synthetic-csrf",
        plan=plan_descriptor("personal"),
        billing_enabled=False,
        checkout_idempotency_key="synthetic-key",
        checkout_result=None,
    )
    assert "магазин не включён" in html
    assert 'name="cycle" value="month"' not in html
    assert "Оплатить 790 ₽" not in html
