from datetime import UTC, datetime, timedelta
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
    _blocking_payment_operation_query,
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


def test_new_money_mutations_block_initial_checkout_and_renewal_operations() -> None:
    statement = str(
        _blocking_payment_operation_query(UUID(int=2)).compile(
            compile_kwargs={"literal_binds": True}
        )
    )

    assert "kind IN ('initial_checkout', 'renewal')" in statement
    for state in ("scheduled", "sent", "processing", "unknown"):
        assert f"'{state}'" in statement


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


@pytest.mark.asyncio
@pytest.mark.parametrize(("query", "selected_cycle", "is_current"), ((b"", "month", True), (b"cycle=year", "year", False)))
async def test_plans_default_to_current_personal_cycle_without_mislabeling_other_period(
    monkeypatch: pytest.MonkeyPatch,
    query: bytes,
    selected_cycle: str,
    is_current: bool,
) -> None:
    principal = SimpleNamespace(user_id=UUID(int=1), session_id=None, auth_via_session=False)
    subscription = SimpleNamespace(
        plan_code="personal",
        state="active",
        paid_through=datetime.now(UTC) + timedelta(days=1),
        trial_ends_at=None,
        cycle="month",
        billing_owner_id=principal.user_id,
    )

    class FakeSession:
        def __init__(self) -> None:
            self.results = iter((subscription, None))

        async def scalar(self, _statement: object) -> object:
            return next(self.results)

    async def owner_role(*_args: object, **_kwargs: object) -> str:
        return "owner"

    async def empty_catalog(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {}

    captured: dict[str, object] = {}

    def capture_page(_title: str, **context: object) -> str:
        captured.update(context)
        return "plans"

    monkeypatch.setattr(billing_routes, "_billing_role", owner_role)
    monkeypatch.setattr(billing_routes, "_approved_personal_catalog", empty_catalog)
    monkeypatch.setattr(billing_routes, "_page_shell", capture_page)
    monkeypatch.setattr(billing_routes, "_csrf_token_for_principal", lambda *_a, **_k: "csrf")
    monkeypatch.setattr(billing_routes, "build_request_browser_provider_context", lambda *_a, **_k: {})
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "https",
            "server": ("graf.test", 443),
            "path": "/billing/plans",
            "headers": [],
            "query_string": query,
            "app": SimpleNamespace(
                state=SimpleNamespace(
                    settings=SimpleNamespace(billing_checkout_enabled=True, billing_support_email=None)
                )
            ),
        }
    )

    response = await billing_routes.billing_plans_page(
        request,
        tenant_scope=SimpleNamespace(workspace_id=UUID(int=2), device_id=UUID(int=3)),
        principal=principal,
        db=FakeSession(),
    )

    assert response.status_code == 200
    assert captured["selected_cycle"] == selected_cycle
    personal = next(item for item in captured["plans"] if item["code"] == "personal")
    assert personal["is_current"] is is_current


@pytest.mark.asyncio
async def test_checkout_page_blocks_a_persisted_renewal_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal = SimpleNamespace(user_id=UUID(int=1), session_id=None, auth_via_session=False)
    blocker = SimpleNamespace(kind="renewal", state="processing")

    class FakeSession:
        def __init__(self) -> None:
            self.results = iter((blocker, None))

        async def scalar(self, _statement: object) -> object:
            return next(self.results)

    async def owner_role(*_args: object, **_kwargs: object) -> str:
        return "owner"

    async def empty_catalog(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {}

    captured: dict[str, object] = {}

    def capture_page(_title: str, **context: object) -> str:
        captured.update(context)
        return "checkout"

    monkeypatch.setattr(billing_routes, "_billing_role", owner_role)
    monkeypatch.setattr(billing_routes, "_approved_personal_catalog", empty_catalog)
    monkeypatch.setattr(billing_routes, "_page_shell", capture_page)
    monkeypatch.setattr(billing_routes, "_csrf_token_for_principal", lambda *_a, **_k: "csrf")
    monkeypatch.setattr(billing_routes, "build_request_browser_provider_context", lambda *_a, **_k: {})
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "https",
            "server": ("graf.test", 443),
            "path": "/billing/checkout",
            "headers": [],
            "query_string": b"cycle=month",
            "app": SimpleNamespace(
                state=SimpleNamespace(
                    settings=SimpleNamespace(billing_checkout_enabled=True)
                )
            ),
        }
    )

    response = await billing_routes.billing_checkout_page(
        request,
        tenant_scope=SimpleNamespace(workspace_id=UUID(int=2), device_id=UUID(int=3)),
        principal=principal,
        db=FakeSession(),
    )

    assert response.status_code == 200
    assert captured["checkout_result"] == "pending"


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
        billing_owner=True,
        trial_result=None,
    )
    assert "0 мин 0 сек" in html
    assert "300 минут" in html
    assert "250 MB" in html
    assert "250 000 000 байт" not in html
    assert "только письмом" in html
    assert "автоматической заявки" in html
    assert "Вы управляете тарифом выбранного пространства" in html
    assert 'href="/billing/payment-method"' in html
    assert 'href="/billing/storage"' in html


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


def test_pending_checkout_hides_recomputed_order_total() -> None:
    html = render_template(
        "cabinet/pages/billing_checkout_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor("personal"),
        billing_enabled=True,
        catalog_ready=True,
        checkout_result="pending",
        checkout_cycle="month",
        monthly_price_label="790 ₽",
        annual_price_label="7 900 ₽",
    )

    assert "Платёж уже создан" in html
    assert 'class="billing-order-summary"' not in html


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


def test_billing_overview_uses_reference_hierarchy_and_one_primary_action() -> None:
    html = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        csrf_token="synthetic-csrf",
        plan=plan_descriptor("free"),
        plan_code="free",
        current_price_label="0 ₽",
        current_cycle_label="без оплаты",
        billing_data_available=True,
        billing_enabled=True,
        catalog_ready=True,
        billing_owner=True,
        billing_role="owner",
        trial_state="already",
        processing_used_label="0 мин 0 сек",
        processing_remaining_label="300 мин 0 сек",
        processing_reset_at_label="01.09.2026, 00:00 (МСК)",
        free_processing_limit_label="300 минут",
        processing_threshold="normal",
        storage_used_label="0 MB",
        storage_capacity_label="250 MB",
        storage_threshold="normal",
        storage_threshold_label="В норме",
        bonus_until_label="15.09.2026, 12:00 (МСК)",
        latest_invoice_summary=None,
        latest_operation_state=None,
    )

    assert 'class="cabinet-main billing-page billing-overview"' in html
    section_ids = (
        "billing-summary-title",
        "billing-offer-title",
        "billing-workspace-title",
        "billing-method-title",
        "billing-history-title",
    )
    assert all(section_id in html for section_id in section_ids)
    assert [html.index(section_id) for section_id in section_ids] == sorted(
        html.index(section_id) for section_id in section_ids
    )
    assert html.count("data-billing-primary") == 1
    assert 'href="/billing/plans"' in html
    assert 'href="/billing/discounts"' in html
    assert "Бонус до" in html
    assert "15.09.2026, 12:00 (МСК)" in html


def test_billing_overview_never_presents_missing_paid_price_as_free() -> None:
    html = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor("personal"),
        plan_code="personal",
        current_price_label=None,
        current_cycle_label="период уточняется",
        billing_data_available=True,
        billing_enabled=False,
        billing_owner=True,
        processing_used_label="0 мин 0 сек",
        free_processing_limit_label="300 минут",
        processing_threshold="normal",
        storage_used_label="0 MB",
        storage_capacity_label="250 MB",
        storage_threshold="normal",
        storage_threshold_label="В норме",
        latest_invoice_summary=None,
        latest_operation_state=None,
    )

    assert "Сумма уточняется" in html
    assert "<strong>0 ₽</strong>" not in html


def test_pending_billing_overview_exposes_status_without_competing_checkout() -> None:
    html = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor("free"),
        plan_code="free",
        billing_data_available=True,
        billing_enabled=True,
        catalog_ready=True,
        billing_owner=True,
        billing_role="owner",
        billing_result="pending",
        processing_used_label="0 мин 0 сек",
        free_processing_limit_label="300 минут",
        processing_threshold="normal",
        storage_used_label="0 MB",
        storage_capacity_label="250 MB",
        storage_threshold="normal",
        storage_threshold_label="В норме",
        latest_invoice_summary={
            "safe_number": "INV-PENDING1",
            "amount_label": "790 ₽",
            "created_at_label": "29.08.2026, 12:00 (МСК)",
            "status_label": "Проверяем оплату",
        },
        pending_invoice_summary={"safe_number": "INV-PENDING1"},
        latest_operation_state="provider_pending",
        latest_operation_label="Ожидаем подтверждение",
    )

    assert 'href="/billing/checkout/status/INV-PENDING1"' in html
    assert 'href="/billing/checkout"' not in html
    assert 'href="/billing/plans"' not in html
    assert html.count("data-billing-primary") == 1


def test_pending_billing_without_invoice_suppresses_new_checkout() -> None:
    html = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor("free"),
        plan_code="free",
        billing_data_available=True,
        billing_enabled=True,
        catalog_ready=True,
        billing_owner=True,
        billing_role="owner",
        billing_result="pending",
        processing_used_label="0 мин 0 сек",
        free_processing_limit_label="300 минут",
        processing_threshold="normal",
        storage_used_label="0 MB",
        storage_capacity_label="250 MB",
        storage_threshold="normal",
        storage_threshold_label="В норме",
        latest_invoice_summary=None,
        latest_operation_state="provider_pending",
    )

    assert "Новую оплату пока не предлагаем" in html
    assert 'href="/billing/plans"' not in html
    assert "data-billing-primary" not in html


def test_scheduled_renewal_keeps_subscription_cancellation_reachable() -> None:
    html = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor("personal"),
        plan_code="personal",
        current_price_label="790 ₽",
        current_cycle_label="в месяц",
        billing_data_available=True,
        billing_enabled=True,
        catalog_ready=True,
        billing_owner=True,
        billing_role="owner",
        processing_used_label="30 мин 0 сек",
        processing_usage_freshness="fresh",
        processing_threshold="normal",
        storage_used_label="1 GB",
        storage_capacity_label="2 GB",
        storage_threshold="normal",
        storage_threshold_label="В норме",
        latest_invoice_summary={
            "safe_number": "INV-RNW-SCHEDULED",
            "amount_label": "790 ₽",
            "status_label": "Запланирован",
            "created_at_label": "30.08.2026, 00:00 (МСК)",
        },
        latest_operation_kind="renewal",
        latest_operation_state="scheduled",
    )

    assert 'href="/billing/subscription"' in html
    assert 'href="/billing/checkout/status/INV-RNW-SCHEDULED"' not in html


def test_non_owner_billing_overview_hides_invoice_and_exact_storage() -> None:
    html = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor("personal"),
        plan_code="personal",
        current_price_label="790 ₽",
        current_cycle_label="в месяц",
        billing_data_available=True,
        billing_enabled=True,
        billing_owner=False,
        billing_role="member",
        processing_used_label="30 мин 0 сек",
        processing_threshold="normal",
        storage_used_label="1.5 GB",
        storage_capacity_label="2 GB",
        storage_threshold="normal",
        storage_threshold_label="В норме",
        latest_invoice_summary={
            "safe_number": "INV-PRIVATE1",
            "amount_label": "790 ₽",
            "created_at_label": "29.08.2026, 12:00 (МСК)",
            "status_label": "Оплачен",
            "payment_method_label": "•••• 4242",
        },
        paid_through_label="28.09.2026",
        bonus_until_label="15.09.2026",
        next_charge_label="29.09.2026",
        next_charge_amount_label="790 ₽",
    )

    assert "INV-PRIVATE1" not in html
    assert "•••• 4242" not in html
    assert "1.5 GB" not in html
    assert "2 GB" not in html
    assert "28.09.2026" not in html
    assert "15.09.2026" not in html
    assert "29.09.2026" not in html
    assert "Платёжные данные доступны владельцу пространства" in html


def test_workspace_owner_can_start_guarded_billing_takeover() -> None:
    overview = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor("free"),
        plan_code="free",
        current_price_label="0 ₽",
        current_cycle_label="без оплаты",
        billing_data_available=True,
        billing_enabled=True,
        catalog_ready=True,
        billing_owner=False,
        billing_role="owner",
        free_processing_limit_label="300 минут",
        processing_used_label="30 мин 0 сек",
        processing_threshold="normal",
        storage_threshold="normal",
        storage_threshold_label="В норме",
        latest_invoice_summary=None,
        latest_operation_state=None,
    )
    plans = render_template(
        "cabinet/pages/billing_plans_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        csrf_token="synthetic-csrf",
        plans=(
            {
                "code": "personal",
                "label": "Личный",
                "processing_mode": "unlimited",
                "processing_label": "Без лимита",
                "storage_label": "2 GB",
                "monthly_amount_label": "790 ₽",
                "annual_amount_label": "7 900 ₽",
                "annual_saving_label": None,
                "is_current": False,
                "catalog_ready": True,
            },
        ),
        selected_cycle="month",
        current_plan_code="free",
        billing_role="owner",
        billing_owner=False,
        operation_pending=False,
        billing_enabled=True,
        catalog_ready=True,
        trial_state="unavailable",
    )

    assert "платёжный аккаунт закреплён за другим пользователем" in overview
    assert 'data-billing-primary href="/billing/plans"' in overview
    assert 'href="/billing/checkout?cycle=month"' in plans
    assert "Выбрать «Личный»" in plans

    active_overview = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor("personal"),
        plan_code="personal",
        current_price_label="790 ₽",
        current_cycle_label="в месяц",
        billing_data_available=True,
        billing_enabled=True,
        catalog_ready=True,
        billing_owner=False,
        billing_role="owner",
        processing_used_label="30 мин 0 сек",
        processing_threshold="normal",
        storage_threshold="normal",
        storage_threshold_label="В норме",
        latest_invoice_summary=None,
        latest_operation_state=None,
    )
    assert "Активным тарифом управляет текущий владелец биллинга" in active_overview
    assert 'href="/billing/plans"' not in active_overview


def test_checkout_keeps_coupon_collapsed_until_promo_interaction() -> None:
    html = render_template(
        "cabinet/pages/billing_checkout_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        csrf_token="synthetic-csrf",
        plan=plan_descriptor("personal"),
        billing_enabled=True,
        catalog_ready=True,
        checkout_idempotency_key="synthetic-key",
        monthly_price_label="790 ₽",
        annual_price_label="7 900 ₽",
        checkout_result=None,
        checkout_promo_code="",
        checkout_cycle="month",
        checkout_preview={
            "cycle_label": "месяц",
            "list_amount_label": "790 ₽",
            "discount_label": "0 ₽",
            "payable_amount_label": "790 ₽",
            "next_amount_label": "790 ₽",
        },
        promo_preview_error=None,
    )

    assert '<details class="billing-coupon">' in html
    assert '<details class="billing-coupon" open>' not in html


def test_plan_comparison_keeps_server_selected_cycle_and_real_checkout_links() -> None:
    html = render_template(
        "cabinet/pages/billing_plans_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        csrf_token="synthetic-csrf",
        plans=(
            {
                "code": "free",
                "label": "Free",
                "processing_mode": "limited",
                "processing_label": "300 минут",
                "storage_label": "250 MB",
                "monthly_amount_label": "0 ₽",
                "annual_amount_label": "0 ₽",
                "annual_saving_label": None,
                "is_current": True,
                "catalog_ready": True,
            },
            {
                "code": "personal",
                "label": "Личный",
                "processing_mode": "unlimited",
                "processing_label": "Без лимита",
                "storage_label": "2 GB",
                "monthly_amount_label": "790 ₽",
                "annual_amount_label": "7 900 ₽",
                "annual_saving_label": "Экономия 1 580 ₽ (17%)",
                "is_current": False,
                "catalog_ready": True,
            },
        ),
        selected_cycle="year",
        billing_owner=True,
        billing_enabled=True,
        catalog_ready=True,
        trial_state="already",
    )

    assert 'class="billing-period-switch"' in html
    assert 'href="/billing/plans?cycle=year" aria-current="true"' in html
    assert 'href="/billing/checkout?cycle=year"' in html
    assert 'href="/billing/checkout?cycle=month"' not in html
    assert "7 900 ₽" in html


def test_plan_comparison_does_not_label_another_cycle_as_connected() -> None:
    html = render_template(
        "cabinet/pages/billing_plans_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        csrf_token="synthetic-csrf",
        plans=(
            {
                "code": "personal",
                "label": "Личный",
                "processing_mode": "unlimited",
                "processing_label": "Без лимита",
                "storage_label": "2 GB",
                "monthly_amount_label": "790 ₽",
                "annual_amount_label": "7 900 ₽",
                "annual_saving_label": None,
                "is_current": False,
                "catalog_ready": True,
            },
        ),
        selected_cycle="year",
        current_plan_code="personal",
        billing_owner=True,
        billing_enabled=True,
        catalog_ready=True,
        operation_pending=False,
        trial_state="already",
    )

    assert "Другой период оплаты" in html
    assert "Подключён сейчас" not in html
    assert 'href="/billing/checkout' not in html


def test_plan_comparison_explains_pending_and_disabled_checkout_states() -> None:
    common = {
        "embedded": False,
        "settings_navigation": settings_category_navigation(active="billing"),
        "settings_active": "billing",
        "csrf_token": "synthetic-csrf",
        "plans": (
            {
                "code": "personal",
                "label": "Личный",
                "processing_mode": "unlimited",
                "processing_label": "Без лимита",
                "storage_label": "2 GB",
                "monthly_amount_label": "790 ₽",
                "annual_amount_label": "7 900 ₽",
                "annual_saving_label": None,
                "is_current": False,
                "catalog_ready": True,
            },
        ),
        "selected_cycle": "month",
        "current_plan_code": "free",
        "billing_role": "owner",
        "billing_owner": True,
        "catalog_ready": True,
        "trial_state": "already",
    }
    pending = render_template(
        "cabinet/pages/billing_plans_content.html",
        **common,
        billing_enabled=True,
        operation_pending=True,
    )
    disabled = render_template(
        "cabinet/pages/billing_plans_content.html",
        **common,
        billing_enabled=False,
        operation_pending=False,
    )

    assert "Платёж проверяется" in pending
    assert 'href="/billing/checkout' not in pending
    assert "магазин не включён" in disabled
    assert "Цена появится после утверждения" not in disabled


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
    processing_html = render_template(
        "cabinet/pages/billing_operation_status_content.html",
        **common,
        operation_state="processing",
        can_continue_payment=False,
        can_refresh_payment=False,
    )

    assert "Продолжить оплату" in recovery_html
    assert "/continue" in recovery_html
    assert "Проверить статус" not in recovery_html
    assert "Проверить статус" in pending_html
    assert "Продолжить оплату" not in pending_html
    assert "Новую оплату не создаём" in processing_html
    assert "Операция не найдена" not in processing_html
