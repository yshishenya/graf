from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from starlette.requests import Request

from twobrain_rec_server.billing.catalog import plan_descriptor
from twobrain_rec_server.billing.receipts import ReceiptState, receipt_label
from twobrain_rec_server.billing.usage import format_duration
from twobrain_rec_server.cabinet.templates import render_template
from twobrain_rec_server.cabinet.view_models import settings_category_navigation
from twobrain_rec_server.cabinet.web_routes import billing as billing_routes
from twobrain_rec_server.cabinet.web_routes.billing import (
    _billing_amount_label,
    _checkout_result_redirect,
    _processing_threshold_label,
    _receipt_registration_state,
)
from twobrain_rec_server.cabinet.web_routes.billing import (
    router as billing_router,
)


def test_billing_labels_are_localized_for_user_surfaces() -> None:
    assert _billing_amount_label(79_000, "RUB") == "790 ₽"
    assert _billing_amount_label(79_050, "RUB") == "790.50 ₽"
    assert _processing_threshold_label("normal") == "В норме"
    assert _processing_threshold_label("approaching") == "Приближается к лимиту"
    assert _processing_threshold_label("exhausted") == "Лимит исчерпан"


def test_billing_receipt_registration_uses_provider_status_mapping() -> None:
    assert _receipt_registration_state("succeeded") is ReceiptState.AVAILABLE
    assert _receipt_registration_state("pending") is ReceiptState.PENDING
    assert _receipt_registration_state("invalid") is ReceiptState.UNKNOWN


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("registration", "expected_url"),
    (("succeeded", "https://yookassa.test/receipt/1"), ("pending", None), ("invalid", None)),
)
async def test_invoice_receipt_link_requires_registered_receipt(
    monkeypatch: pytest.MonkeyPatch,
    registration: str,
    expected_url: str | None,
) -> None:
    invoice = SimpleNamespace(
        safe_number="INV-RECEIPT1",
        created_at=datetime(2026, 8, 26, tzinfo=UTC),
        amount_minor=1_000,
        currency="RUB",
        status="succeeded",
        receipt_contact_snapshot=None,
        plan_snapshot={
            "cycle": "month",
            "receipt_registration": registration,
            "receipt_url": "https://yookassa.test/receipt/1",
        },
    )

    class FakeSession:
        def __init__(self) -> None:
            self.results = iter((None, invoice))

        async def scalar(self, _statement: object) -> object:
            return next(self.results)

    captured: dict[str, object] = {}

    async def owner_role(*_args: object, **_kwargs: object) -> str:
        return "owner"

    def capture_page(_title: str, **context: object) -> str:
        captured.update(context)
        return "billing invoice"

    monkeypatch.setattr(billing_routes, "_billing_role", owner_role)
    monkeypatch.setattr(billing_routes, "_page_shell", capture_page)
    monkeypatch.setattr(billing_routes, "build_request_browser_provider_context", lambda *_a, **_k: {})
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "https",
            "server": ("graf.test", 443),
            "path": "/billing/invoices/INV-RECEIPT1",
            "headers": [],
            "query_string": b"",
            "app": SimpleNamespace(
                state=SimpleNamespace(settings=SimpleNamespace(billing_support_email=None))
            ),
        }
    )
    principal = SimpleNamespace(user_id=UUID(int=1), session_id=None, auth_via_session=False)
    tenant_scope = SimpleNamespace(workspace_id=UUID(int=2), device_id=UUID(int=3))

    response = await billing_routes.billing_invoice_detail_page(
        "INV-RECEIPT1",
        request,
        tenant_scope=tenant_scope,
        principal=principal,
        db=FakeSession(),
    )

    assert response.status_code == 200
    invoice_context = captured["invoice"]
    assert isinstance(invoice_context, dict)
    assert invoice_context["receipt_url"] == expected_url
    assert invoice_context["receipt_label"] == receipt_label(_receipt_registration_state(registration))


def test_billing_keeps_legacy_account_alias_on_canonical_surface() -> None:
    paths = {route.path for route in billing_router.routes}
    assert "/settings/billing" in paths
    assert "/account/billing" in paths
    assert "/billing/checkout/preview" in paths


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
        storage_capacity_label="250 MB",
        storage_capacity_exact_label="250 000 000",
        processing_threshold="normal",
        processing_threshold_label="В норме",
        billing_enabled=False,
        trial_result=None,
    )
    assert "0 мин 0 сек" in html
    assert "300 минут" in html
    assert "250 MB" in html
    assert "250 000 000 байт" not in html
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
        paid_through_label="01.09.2026, 03:00 (МСК)",
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
        storage_threshold_label="В норме",
        billing_owner=True,
    )
    assert "Возобновить автопродление" in subscription_html
    assert "01.09.2026, 03:00 (МСК)" in subscription_html
    assert "2026-09-01 00:00:00" not in subscription_html
    assert "Без лимита по минутам и встречам" in usage_html
    assert "meeting-review.m4a" in usage_html
    assert "Состояние: <strong>В норме</strong>" in usage_html
    assert "Состояние: normal" not in usage_html
    assert "Управлять архивом" in usage_html
    assert "Увеличить хранилище" in usage_html
    assert "Обработать без сохранения аудио" in usage_html


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
        receipt_contact_label="y***@example.com",
    )
    assert 'name="recurring_consent"' in html
    assert 'name="offer_consent"' in html
    assert 'href="/billing/plans">Назад к тарифам</a>' in html
    assert 'href="/offer"' in html
    assert "required" in html
    assert "регулярное списание" in html
    assert "Чек отправится на" in html
    assert "y***@example.com" in html


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

    empty = _checkout_result_redirect(request, "promo_applied")
    assert 'graf_checkout_promo=""' in empty.headers["set-cookie"]
    assert "Max-Age=0" in empty.headers["set-cookie"]


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
        current_capacity_label="2 GB",
        addon_options=(5_000_000_000, 20_000_000_000),
        capacity_labels=("5 GB", "20 GB"),
        eligible=True,
        billing_enabled=True,
    )
    assert "•••• 4242" in method_html
    assert "Данные карты не проходят через GRAF" in method_html
    assert "meeting-review.m4a" in storage_html
    assert "Исходный WAV" in storage_html
    assert "Увеличить до 5 GB" in storage_html
    assert "5000000000 байт" not in storage_html


def test_storage_surface_hides_values_and_addons_when_data_is_unavailable() -> None:
    html = render_template(
        "cabinet/pages/billing_storage_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        result="unavailable",
        current_capacity=None,
        current_capacity_label=None,
        addon_options=(),
        capacity_labels=(),
        eligible=False,
        billing_enabled=False,
    )
    assert "Данные хранилища временно недоступны" in html
    assert "Доступные варианты" not in html
    assert "Увеличить хранилище" not in html


def test_billing_overview_hides_usage_cta_when_data_is_unavailable() -> None:
    html = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor("free"),
        plan_code="free",
        billing_data_available=False,
        billing_enabled=False,
        billing_owner=False,
    )
    assert "Данные биллинга временно недоступны" in html
    assert 'href="/billing/usage"' not in html
    assert 'href="/billing/checkout"' not in html


def test_corporate_billing_context_points_to_personal_workspace_without_catalog_cta() -> None:
    html = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor("free"),
        plan_code="free",
        billing_data_available=True,
        billing_enabled=True,
        billing_owner=False,
        billing_result="personal_only",
        processing_used_label="0 мин 0 сек",
        free_processing_limit_label="300 минут",
        processing_threshold="normal",
        storage_capacity_label="250 MB",
        storage_threshold="normal",
        storage_used=0,
        storage_threshold_label="В норме",
        trial_result=None,
        bonus_until_label=None,
        latest_invoice=None,
        latest_operation_label=None,
        latest_operation_state=None,
        next_charge_label=None,
        next_charge_amount_label=None,
        payment_method_label=None,
    )

    assert "Личный тариф оформляется для «Моего пространства»" in html
    assert 'href="/settings/workspace"' in html
    assert 'href="/billing/checkout"' not in html


def test_billing_disabled_does_not_render_recovery_checkout_cta() -> None:
    html = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor("free"),
        plan_code="free",
        billing_data_available=True,
        billing_enabled=False,
        billing_owner=True,
        renewal_failed=True,
        paid_through_label="01.09.2026",
        processing_used_label="0 мин 0 сек",
        free_processing_limit_label="300 минут",
        processing_threshold="normal",
        storage_capacity_label="250 MB",
        storage_threshold="normal",
        storage_used=0,
        storage_threshold_label="В норме",
        trial_result=None,
        bonus_until_label=None,
        latest_invoice=None,
        latest_operation_label=None,
        latest_operation_state=None,
        next_charge_label=None,
        next_charge_amount_label=None,
        payment_method_label=None,
    )
    assert "Оплата временно недоступна" in html
    assert 'href="/billing/checkout"' not in html


def test_usage_surface_localizes_processing_reservation_and_threshold() -> None:
    html = render_template(
        "cabinet/pages/billing_usage_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan_code="free",
        processing_used=60,
        processing_used_label="1 мин 0 сек",
        processing_reserved=90,
        processing_reserved_label="1 мин 30 сек",
        free_processing_limit_label="300 минут",
        processing_threshold="normal",
        processing_threshold_label="В норме",
        processing_unlimited=False,
        storage_used_label="0 MB",
        storage_reserved_label="0 MB",
        storage_available_label="250 MB",
        storage_capacity_label="250 MB",
        storage_threshold="normal",
        storage_threshold_label="В норме",
        billing_owner=False,
    )
    assert "1 мин 30 сек" in html
    assert "90 сек" not in html
    assert "Состояние: В норме" in html
    assert "Состояние: normal" not in html


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
        checkout_promo_active=False,
        result=None,
    )
    assert 'action="/billing/payment-method/delete"' in method_html
    assert "Удалить способ оплаты" in method_html
    assert "08.08.2026, 12:00 (МСК)" in method_html
    assert 'action="/billing/discounts/apply"' in discounts_html
    assert 'action="/billing/discounts/remove"' not in discounts_html
    assert "Применить" in discounts_html

    active_discount_html = render_template(
        "cabinet/pages/billing_discounts_content.html",
        **common,
        active_promotions=[],
        redemptions=[],
        billing_owner=True,
        billing_enabled=True,
        checkout_promo_active=True,
        result=None,
    )
    assert 'action="/billing/discounts/remove"' in active_discount_html
    assert "Удалить выбранный промокод" in active_discount_html


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


def test_manual_checkout_recovery_offers_continue_instead_of_noop_refresh() -> None:
    common = {
        "embedded": False,
        "settings_navigation": settings_category_navigation(active="billing"),
        "settings_active": "billing",
        "csrf_token": "synthetic-csrf",
        "invoice": SimpleNamespace(
            safe_number="INV-RECOVERY1",
            created_at_label="25.08.2026, 15:00 (МСК)",
        ),
        "amount_label": "10 ₽",
        "operation_state_label": "Нужна ручная сверка платежа",
        "updated_at_label": "25.08.2026, 15:01 (МСК)",
        "billing_enabled": True,
        "status_result": "provider_unavailable",
    }
    recovery_html = render_template(
        "cabinet/pages/billing_operation_status_content.html",
        **common,
        operation_state="manual_resolution",
        can_continue_payment=True,
        can_refresh_payment=False,
    )
    pending_html = render_template(
        "cabinet/pages/billing_operation_status_content.html",
        **common,
        operation_state="provider_pending",
        can_continue_payment=False,
        can_refresh_payment=True,
    )

    assert "Продолжить оплату" in recovery_html
    assert "/continue" in recovery_html
    assert "Проверить статус" not in recovery_html
    assert "Проверить статус" in pending_html
    assert "Продолжить оплату" not in pending_html
