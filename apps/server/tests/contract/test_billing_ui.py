import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from starlette.requests import Request

from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.billing.catalog import plan_descriptor
from twobrain_rec_server.billing.receipts import ReceiptState, receipt_label
from twobrain_rec_server.billing.usage import format_duration
from twobrain_rec_server.cabinet.templates import render_template
from twobrain_rec_server.cabinet.view_models import AccountProfileView, settings_category_navigation
from twobrain_rec_server.cabinet.web_routes import billing as billing_routes
from twobrain_rec_server.cabinet.web_routes.billing import (
    _billing_amount_label,
    _blocking_payment_operation_query,
    _checkout_result_redirect,
    _operation_state_label,
    _processing_threshold_label,
    _receipt_registration_state,
)
from twobrain_rec_server.cabinet.web_routes.billing import (
    router as billing_router,
)
from twobrain_rec_server.db.models import BillingPlanVersion
from twobrain_rec_server.public.offers import (
    PUBLIC_ANNUAL_AMOUNT_MINOR,
    PUBLIC_APPROVED_OFFER_VERSION,
    PUBLIC_MONTHLY_AMOUNT_MINOR,
)

CABINET_CSS = (
    Path(__file__).resolve().parents[4]
    / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
)


@pytest.fixture(autouse=True)
def profile_lookup(monkeypatch):
    # These handler tests isolate billing; profile query/propagation has its own regression.
    lookup = AsyncMock(return_value=AccountProfileView("Synthetic", theme="dark"))
    monkeypatch.setattr(billing_routes, "get_account_profile_view", lookup)
    return lookup


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

    assert "kind IN ('initial_checkout', 'storage_upgrade', 'early_renewal', 'renewal')" in statement
    for state in (
        "scheduled",
        "provider_pending",
        "sent",
        "processing",
        "unknown",
        "pending_reconciliation",
        "manual_resolution",
        "reconciliation_gap",
    ):
        assert f"'{state}'" in statement
    assert "'provider_key_expired'" not in statement
    assert "CASE WHEN" not in statement
    assert "NOT (billing_operations.kind = 'renewal'" in statement
    assert "billing_operations.state = 'scheduled'" in statement
    assert "billing_operations.provider_id IS NULL" in statement
    assert "billing_operations.created_at DESC" in statement
    assert _operation_state_label("observation_expired") == "Срок проверки платежа истек"


def test_in_flight_operation_labels_are_explicit() -> None:
    assert _operation_state_label("sent") == "Платеж отправлен в ЮKassa"
    assert _operation_state_label("processing") == "ЮKassa обрабатывает платеж"


def test_billing_receipt_registration_uses_provider_status_mapping() -> None:
    assert _receipt_registration_state("succeeded") is ReceiptState.AVAILABLE
    assert _receipt_registration_state("pending") is ReceiptState.PENDING
    assert _receipt_registration_state("invalid") is ReceiptState.UNKNOWN


@pytest.mark.asyncio
async def test_cabinet_catalog_uses_the_same_guard_as_the_public_offer() -> None:
    class CatalogSession:
        def __init__(self, rows: list[BillingPlanVersion]) -> None:
            self.rows = rows

        async def scalars(self, _statement: object) -> list[BillingPlanVersion]:
            return self.rows

    common = {
        "plan_code": "personal",
        "version": 1,
        "currency": "RUB",
        "storage_bytes": 5_000_000_000,
        "processing_mode": "unlimited",
        "enabled_for_checkout": True,
        "policy_snapshot": {"offer_version": PUBLIC_APPROVED_OFFER_VERSION},
        "effective_from": datetime(2026, 8, 1, tzinfo=UTC),
    }
    approved_rows = [
        BillingPlanVersion(cycle="month", amount_minor=PUBLIC_MONTHLY_AMOUNT_MINOR, **common),
        BillingPlanVersion(cycle="year", amount_minor=PUBLIC_ANNUAL_AMOUNT_MINOR, **common),
    ]
    approved = await billing_routes._approved_personal_catalog(
        CatalogSession(approved_rows),
        now=datetime(2026, 8, 21, tzinfo=UTC),
    )
    assert set(approved) == {"month", "year"}

    mismatched_rows = [
        approved_rows[0],
        BillingPlanVersion(cycle="year", amount_minor=999_000, **common),
    ]
    rejected = await billing_routes._approved_personal_catalog(
        CatalogSession(mismatched_rows),
        now=datetime(2026, 8, 21, tzinfo=UTC),
    )
    assert rejected == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("observation_enabled", [True, False])
@pytest.mark.parametrize(
    ("registration", "expected_url"),
    (("succeeded", "https://yookassa.test/receipt/1"), ("pending", None), ("invalid", None)),
)
async def test_invoice_receipt_link_requires_registered_receipt(
    monkeypatch: pytest.MonkeyPatch,
    registration: str,
    expected_url: str | None,
    observation_enabled: bool,
) -> None:
    invoice = SimpleNamespace(
        safe_number="INV-RECEIPT1", operation_id=UUID(int=4), workspace_id=UUID(int=2),
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
            self.results = iter((None, invoice, UUID(int=4)))

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
    monkeypatch.setattr(
        billing_routes, "build_request_browser_provider_context", lambda *_a, **_k: {}
    )
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
                state=SimpleNamespace(settings=SimpleNamespace(
                    billing_support_email=None, billing_checkout_enabled=False,
                    billing_provider_observation_enabled=observation_enabled,
                ))
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
    assert invoice_context["can_refresh_receipt"] is (registration == "pending" and observation_enabled)
    assert invoice_context["receipt_label"] == receipt_label(
        _receipt_registration_state(registration)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "selected_cycle", "is_current"),
    ((b"", "month", True), (b"cycle=year", "year", False)),
)
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
    monkeypatch.setattr(
        billing_routes, "build_request_browser_provider_context", lambda *_a, **_k: {}
    )
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
                    settings=SimpleNamespace(
                        billing_checkout_enabled=True, billing_support_email=None
                    )
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
async def test_scheduled_renewal_uses_persisted_invoice_amount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        billing_routes, "effective_paid_storage", AsyncMock(return_value=5_000_000_000)
    )
    monkeypatch.setattr(
        billing_routes, "_next_renewal_label", AsyncMock(return_value="в ближайшее время")
    )

    async def base_composition(_db, *, base, **_kwargs):
        return base, None

    monkeypatch.setattr(billing_routes, "compose_personal_catalog", base_composition)
    principal = SimpleNamespace(user_id=UUID(int=1), session_id=None, auth_via_session=False)
    subscription = SimpleNamespace(
        plan_code="personal",
        state="active",
        paid_through=datetime.now(UTC) + timedelta(days=1),
        trial_ends_at=None,
        renewal_resolution=None,
        capacity_bytes=5_000_000_000,
        cycle="month",
        billing_owner_id=principal.user_id,
        recurring_allowed=True,
    )
    operation = SimpleNamespace(id=UUID(int=4), kind="renewal", state="scheduled")
    invoice = SimpleNamespace(
        safe_number="INV-FROZEN1",
        operation_id=operation.id,
        amount_minor=79_000,
        currency="RUB",
        created_at=datetime.now(UTC),
        status="pending",
        plan_snapshot={"cycle": "month"},
    )

    class FakeSession:
        def __init__(self) -> None:
            self.results = iter((subscription, None, 0, invoice, operation, invoice, None, None))

        async def scalar(self, _statement: object) -> object:
            return next(self.results)

    async def owner_role(*_args: object, **_kwargs: object) -> str:
        return "owner"

    async def catalog(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"month": SimpleNamespace(amount_minor=99_000)}

    async def storage_projection(*_args: object, **_kwargs: object) -> object:
        return SimpleNamespace(used_bytes=0)

    captured: dict[str, object] = {}

    def capture_page(_title: str, **context: object) -> str:
        captured.update(context)
        return "billing"

    monkeypatch.setattr(billing_routes, "_billing_role", owner_role)
    monkeypatch.setattr(billing_routes, "_approved_personal_catalog", catalog)
    monkeypatch.setattr(billing_routes, "project_active_playback_storage", storage_projection)
    monkeypatch.setattr(billing_routes, "_page_shell", capture_page)
    monkeypatch.setattr(billing_routes, "_csrf_token_for_principal", lambda *_a, **_k: "csrf")
    monkeypatch.setattr(
        billing_routes, "build_request_browser_provider_context", lambda *_a, **_k: {}
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "https",
            "server": ("graf.test", 443),
            "path": "/billing",
            "headers": [],
            "query_string": b"",
            "app": SimpleNamespace(
                state=SimpleNamespace(settings=SimpleNamespace(billing_checkout_enabled=True))
            ),
        }
    )

    response = await billing_routes.billing_overview_page(
        request,
        tenant_scope=SimpleNamespace(workspace_id=UUID(int=2), device_id=UUID(int=3)),
        principal=principal,
        db=FakeSession(),
    )

    assert response.status_code == 200
    assert captured["next_charge_amount_label"] == "790 ₽"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("checkout_enabled", "billing_actor_user_id", "expected_url"),
    (
        (True, str(UUID(int=1)), "https://yookassa.test/checkout/existing-payment"),
        (False, str(UUID(int=1)), None),
        (True, str(UUID(int=4)), None),
    ),
)
async def test_checkout_page_only_offers_authorized_persisted_continuation(
    monkeypatch: pytest.MonkeyPatch,
    checkout_enabled: bool,
    billing_actor_user_id: str,
    expected_url: str | None,
) -> None:
    principal = SimpleNamespace(user_id=UUID(int=1), session_id=None, auth_via_session=False)
    blocker = SimpleNamespace(
        id=UUID(int=5),
        kind="initial_checkout",
        state="provider_pending",
        request_snapshot={
            "confirmation_url": "https://yookassa.test/checkout/existing-payment",
            "billing_actor_user_id": billing_actor_user_id,
        },
    )

    class FakeSession:
        def __init__(self) -> None:
            self.results = iter((blocker, None, None, None))

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
    monkeypatch.setattr(
        billing_routes, "build_request_browser_provider_context", lambda *_a, **_k: {}
    )
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
                    settings=SimpleNamespace(
                        billing_checkout_enabled=checkout_enabled,
                    )
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
    assert captured["checkout_blocked"] is True
    assert captured["checkout_continuation_url"] == expected_url


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
    assert 'href="/billing/history"' in html
    assert "Нужна помощь с оплатой?" not in html
    assert "Хранилище" in html
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
        resume_quote_id="synthetic-resume-quote",
        billing_enabled=True,
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
        storage_available=5_000_000_000,
        storage_capacity=5_000_000_000,
        storage_threshold="normal",
        storage_threshold_label="В норме",
        billing_owner=True,
    )
    assert "Включить автопродление" in subscription_html
    assert "01.09.2026, 03:00 (МСК)" in subscription_html
    assert "2026-09-01 00:00:00" not in subscription_html
    assert "Без лимита по минутам и встречам" in usage_html
    assert "Место занимают сохраненные аудиозаписи" in usage_html
    assert "meeting-review.m4a" not in usage_html
    assert "Состояние: <strong>В норме</strong>" in usage_html
    assert "Состояние: normal" not in usage_html
    assert "Управлять архивом" in usage_html
    assert "Увеличить хранилище" in usage_html
    assert "Обработать без сохранения аудио" in usage_html


def test_billing_notices_and_list_statuses_use_one_toned_component() -> None:
    common = {
        "embedded": False,
        "settings_navigation": settings_category_navigation(active="billing"),
        "settings_active": "billing",
        "csrf_token": "synthetic-csrf",
        "active": False,
        "subscription": None,
    }
    subscription_html = {
        result: render_template(
            "cabinet/pages/billing_subscription_content.html", **common, result=result
        )
        for result in ("cancelled", "conflict", "unavailable")
    }
    assert 'class="notice notice--success"' in subscription_html["cancelled"]
    assert 'class="notice notice--error"' in subscription_html["conflict"]
    assert 'class="notice notice--warning"' in subscription_html["unavailable"]

    storage_html = render_template(
        "cabinet/pages/billing_storage_content.html",
        **common,
        result="unavailable",
        current_capacity=None,
        current_capacity_label=None,
        addon_options=(),
        capacity_labels=(),
        eligible=False,
        billing_enabled=False,
    )
    assert 'class="notice notice--error"' in storage_html

    payment_method_html = {
        result: render_template(
            "cabinet/pages/billing_payment_method_content.html",
            **common,
            result=result,
            method_label="•••• 4242",
            method_kind="bank_card",
            billing_enabled=True,
        )
        for result in ("renewal_on", "removed", "none", "conflict")
    }
    assert 'class="notice notice--error"' in payment_method_html["renewal_on"]
    assert 'class="notice notice--success"' in payment_method_html["removed"]
    assert 'class="notice notice--success"' in payment_method_html["none"]
    assert 'class="notice notice--error"' in payment_method_html["conflict"]

    css = CABINET_CSS.read_text(encoding="utf-8")
    assert (
        ".notice { margin: 0; padding: 10px 12px; border: 1px solid var(--line); "
        "border-radius: var(--radius-card); background: var(--surface-2); color: var(--text); }"
    ) in css
    assert '.notice[role="alert"],' in css
    assert (
        ".notice.notice--warning { color: var(--amber); border-color: var(--warning-border); background: var(--warning-surface); }"
        in css
    )
    assert (
        ".notice.notice--success { color: var(--green); border-color: var(--success-border); background: var(--success-surface); }"
        in css
    )
    assert ".notice + .notice { margin-top: 8px; }" in css
    assert (
        ".meeting-status,\n.meeting-content-readiness,\n.meeting-result-count { color: var(--muted); font-size: var(--font-size-helper); }"
        in css
    )
    assert '.meeting-status[data-status-kind="failed"],' in css
    assert '.meeting-content-readiness[data-processing-retry-class="terminal"]' in css
    assert '.meeting-status[data-status-kind="limited"],' in css
    assert '.meeting-content-readiness[data-processing-retry-class="unknown_outcome"]' in css


def test_checkout_offers_optional_recurring_and_requires_offer_consent() -> None:
    html = render_template(
        "cabinet/pages/billing_checkout_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        csrf_token="synthetic-csrf",
        plan=plan_descriptor("personal"),
        billing_enabled=True,
        checkout_idempotency_key="synthetic-key",
        checkout_quote_id="synthetic-quote",
        checkout_result=None,
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
    recurring = re.search(r'<input[^>]*name="recurring_consent"[^>]*>', html)
    offer = re.search(r'<input[^>]*name="offer_consent"[^>]*>', html)
    assert recurring and "checked" in recurring.group(0) and "required" not in recurring.group(0)
    assert offer and "checked" not in offer.group(0) and "required" in offer.group(0)
    assert "Разрешаю автоматические списания" in html
    assert "Отключить можно в «Подписке»" in html
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
        checkout_quote_id="synthetic-quote",
        checkout_result="offer_required",
        monthly_price_label="790 ₽",
        annual_price_label="7 900 ₽",
        annual_saving_label="Экономия 1 580 ₽ (17%)",
    )
    assert "примите оферту" in html.lower()
    assert PUBLIC_APPROVED_OFFER_VERSION in html
    assert "billing-personal-v1" not in html


def test_checkout_offer_version_fallback_has_no_legacy_route_or_template_literal() -> None:
    route_source = Path(billing_routes.__file__).read_text(encoding="utf-8")
    template_source = (
        Path(__file__).resolve().parents[4]
        / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html"
    ).read_text(encoding="utf-8")

    assert "PUBLIC_APPROVED_OFFER_VERSION" in route_source
    assert "_BILLING_OFFER_VERSION" not in route_source
    assert "billing-personal-v1" not in route_source
    assert PUBLIC_APPROVED_OFFER_VERSION in template_source
    assert "billing-personal-v1" not in template_source


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
        checkout_continuation_url="https://yookassa.test/checkout/existing-payment",
        promo_preview_error="Промокод истёк",
    )

    assert "Платеж уже создан" in html
    assert "Продолжить этот платеж в ЮKassa" in html
    assert "Промокод истёк" not in html
    assert 'class="billing-order-summary"' not in html
    assert "790 ₽" not in html


def test_checkout_result_redirect_keeps_promo_out_of_url_and_uses_short_lived_cookie() -> None:
    user, workspace, session, organization, device = (UUID(int=n) for n in range(1, 6))
    principal = AuthenticatedPrincipal(
        user, organization, frozenset({workspace}), str(user),
        session_id=session, auth_via_session=True,
    )
    tenant_scope = TenantScope(organization, workspace, user, device, auth_session_id=session)
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "server": ("graf.test", 443),
            "path": "/billing/checkout/start",
            "headers": [],
            "query_string": b"",
            "app": SimpleNamespace(state=SimpleNamespace(web_csrf_secret="synthetic-secret")),
        }
    )
    response = _checkout_result_redirect(
        request, "promo_invalid", promo_code="WELCOME10", principal=principal,
        tenant_scope=tenant_scope, replace_promo=True,
    )
    assert response.headers["location"] == "/billing/checkout?result=promo_invalid"
    cookie = response.headers.getlist("set-cookie")[0]
    assert "graf_checkout_promo_draft=" in cookie
    assert "WELCOME10" not in cookie
    assert "Max-Age=300" in cookie
    assert "Path=/billing/checkout" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" in cookie

    malformed = _checkout_result_redirect(
        request, "promo_invalid", promo_code="bad\ncode", principal=principal,
        tenant_scope=tenant_scope, replace_promo=True,
    )
    assert "graf_checkout_promo_draft=" in malformed.headers["set-cookie"]
    assert "bad\ncode" not in malformed.headers["set-cookie"]
    assert "Max-Age=300" in malformed.headers["set-cookie"]

    empty = _checkout_result_redirect(
        request, "promo_applied", promo_code="", principal=principal, tenant_scope=tenant_scope,
    )
    assert 'graf_checkout_promo_draft=""' in empty.headers["set-cookie"]
    assert "Max-Age=0" in empty.headers["set-cookie"]


    # Losing the saved input must not hide the actual recovery condition.
    for reason in ("unavailable", "owner_only", "offer_required", "consent_required", "catalog_not_approved"):
        failed = _checkout_result_redirect(
            request, reason, promo_code="WELCOME10", principal=principal,
            tenant_scope=tenant_scope,
        )
        assert failed.headers["location"] == f"/billing/checkout?result={reason}"


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
        current_capacity=5_000_000_000,
        current_capacity_label="2 GB",
        addon_options=(5_000_000_000, 20_000_000_000),
        capacity_labels=("5 GB", "20 GB"),
        eligible=True,
        billing_enabled=True,
    )
    assert "•••• 4242" in method_html
    assert "Данные карты не проходят через GRAF" in method_html
    assert "Место занимают сохраненные аудиозаписи" in storage_html
    assert "Файлы не удаляются" in storage_html
    assert "Рассчитать" not in storage_html  # No catalog was supplied to this fixture.
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
    assert "Данные временно недоступны" in html
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


@pytest.mark.parametrize("plan_code", ["free", "personal"])
@pytest.mark.parametrize("renewal_allowed", [False, True])
def test_pending_billing_overview_exposes_status_without_competing_checkout(plan_code, renewal_allowed) -> None:
    html = render_template(
        "cabinet/pages/billing_overview_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        plan=plan_descriptor(plan_code),
        plan_code=plan_code,
        renewal_allowed=renewal_allowed,
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
        operation_pending=True,
        latest_operation_state="provider_pending",
        latest_operation_label="Ожидаем подтверждение",
    )

    assert 'href="/billing/checkout/status/INV-PENDING1"' in html
    assert 'href="/billing/checkout"' not in html
    assert 'href="/billing/plans"' not in html
    assert html.count("data-billing-primary") == 1
    assert ('href="/billing/subscription"' in html) == renewal_allowed
    assert ("Управлять автопродлением" in html) == renewal_allowed


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
        operation_pending=True,
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
        operation_pending=False,
    )

    assert 'href="/billing/subscription"' in html
    assert 'href="/billing/plans"' in html
    assert 'href="/billing/checkout/status/INV-RNW-SCHEDULED"' not in html


def test_non_owner_billing_overview_hides_invoice_and_usage_but_shows_capacity() -> None:
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
    assert "2 GB" in html
    assert "28.09.2026" not in html
    assert "15.09.2026" not in html
    assert "29.09.2026" not in html
    assert "790 ₽" not in html
    assert "Платежные данные доступны владельцу пространства" in html


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

    assert "Оплатой управляет другой плательщик." in overview
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
    assert "Активным тарифом управляет текущий плательщик" in active_overview
    assert 'href="/billing/plans"' not in active_overview


def test_billing_overview_renders_unavailable_trial_result() -> None:
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
        trial_result="unavailable",
        processing_used_label="0 мин 0 сек",
        free_processing_limit_label="300 минут",
        processing_threshold="normal",
        storage_used_label="0 MB",
        storage_capacity_label="250 MB",
        storage_threshold_label="В норме",
    )

    assert "Пробный период сейчас недоступен" in html


def test_checkout_allows_promo_correction_before_receipt_email_verification() -> None:
    html = render_template(
        "cabinet/pages/billing_checkout_content.html",
        plan=plan_descriptor("personal"),
        billing_enabled=True,
        catalog_ready=True,
        csrf_token="synthetic-csrf",
        receipt_contact_ready=False,
        receipt_contact_action_url="/settings/account",
        checkout_quote_id="synthetic-quote",
        checkout_idempotency_key="synthetic-key",
        checkout_result="promo_invalid",
        checkout_promo_code="BAD<CODE",
        promo_preview_error="Промокод недействителен. Проверьте код.",
    )

    assert '<details class="billing-coupon" open>' in html
    assert 'form="billing-promo-preview" id="billing-promo" name="promo_code"' in html
    assert 'value="BAD&lt;CODE"' in html
    assert 'aria-describedby="billing-checkout-error" aria-invalid="true"' in html
    assert 'value="apply">Применить</button>' in html
    assert "очистите поле и нажмите «Применить»" in html
    assert html.count('name="promo_code"') == 1
    assert 'action="/billing/checkout/preview"' in html
    assert '>Подтвердить почту</a>' in html
    assert 'action="/billing/checkout/start"' not in html
    assert 'name="offer_consent"' not in html
    assert 'name="recurring_consent"' not in html


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
        checkout_quote_id="synthetic-quote",
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


@pytest.mark.parametrize("enabled,pending,owner", [(True, False, True), (False, False, True), (True, True, True), (True, False, False)])
def test_plan_comparison_does_not_label_another_cycle_as_connected(enabled, pending, owner) -> None:
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
        billing_owner=owner,
        billing_enabled=enabled,
        catalog_ready=True,
        operation_pending=pending,
        trial_state="already",
    )

    assert "Другой период оплаты" in html
    assert "Подключен сейчас" not in html
    assert ('href="/billing/checkout?cycle=year"' in html) == (enabled and not pending and owner)


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

    assert "Платеж проверяется" in pending
    assert 'href="/billing/checkout' not in pending
    assert "Оплата временно недоступна" in disabled
    assert "Цена появится после утверждения" not in disabled


def test_plan_comparison_hides_owner_only_links_from_takeover_owner() -> None:
    html = render_template(
        "cabinet/pages/billing_plans_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        csrf_token="synthetic-csrf",
        plans=(),
        selected_cycle="month",
        current_plan_code="personal",
        billing_role="owner",
        billing_owner=False,
        billing_enabled=True,
        catalog_ready=True,
        operation_pending=False,
        trial_state="already",
    )

    assert 'href="/billing/storage"' not in html
    assert 'href="/billing/history"' not in html


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
        billing_owner=True,
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
    assert 'action="/billing/payment-method/delete"' not in html
    assert "Сначала отключите автопродление" in html
    assert 'href="/billing/subscription"' in html


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
        checkout_quote_id="synthetic-quote",
        checkout_result=None,
    )
    assert "Оплата пока недоступна" in html
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
    assert "Проверить оплату" not in recovery_html
    assert "Проверить оплату" in pending_html
    assert "Продолжить оплату" not in pending_html
    assert "Новую оплату не создаем" in processing_html
    assert "Операция не найдена" not in processing_html


def _subscription_view(**changes) -> str:
    """Synthetic state shared by the subscription presentation regressions."""
    return render_template(
        "cabinet/pages/billing_subscription_content.html",
        **{
            "subscription": SimpleNamespace(
                plan_code="personal", state="active", cycle="month",
                paid_through=datetime(2026, 11, 3, 9, 19, tzinfo=UTC),
                recurring_allowed=False, recurring_authority_version=7,
                renewal_resolution=None,
            ),
            "active": True, "subscription_trial_active": False, "result": None,
            "subscription_plan_label": "Личный", "subscription_cycle_label": "месяц",
            "paid_through_label": "03.11.2026, 12:19 (UTC+03:00)",
            "paid_through_short_label": "03.11.2026",
            "next_charge_amount_label": "1 000 ₽", "next_charge_label": "31.10.2026, 12:19 (UTC+03:00)",
            "resume_charge_label": "31.10.2026, 12:19 (UTC+03:00)",
            "billing_enabled": True, "method_available": False,
            "manual_checkout_url": "/billing/checkout?cycle=month",
            "csrf_token": "synthetic-csrf", "receipt_contact_ready": True,
            **changes,
        },
    )


@pytest.mark.parametrize("cycle", ["month", "year"])
def test_subscription_off_without_card_is_normal_and_has_one_cycle_preserving_primary(cycle):
    html = _subscription_view(manual_checkout_url=f"/billing/checkout?cycle={cycle}")
    assert "Возобновление пока недоступно" not in html
    assert html.count("data-billing-primary") == 1
    assert re.search(r'<a[^>]*href="/billing/checkout\?cycle=' + cycle + r'"[^>]*>Продлить подписку</a>', html)
    assert 'action="/billing/subscription/resume"' not in html
    assert 'action="/billing/subscription/early-preview"' not in html
    conditions = re.search(r'<details[^>]*>\s*<summary>Способ оплаты и условия</summary>(.*?)</details>', html, re.S)
    assert conditions and "03.11.2026, 12:19 (UTC+03:00)" in conditions[1]
    assert "03.11.2026, 12:19 (UTC+03:00)" not in html.replace(conditions[0], "")
    assert 'href="/billing/history"' in html
    assert 'href="/billing/history#billing-help"' in html


def test_subscription_resume_is_a_native_disclosure_with_unaccepted_bound_consent():
    html = _subscription_view(method_available=True, payment_method_label="•••• 4242", resume_quote_id="synthetic-resume")
    resume = re.search(r'<details[^>]*>\s*<summary>Включить автопродление</summary>(.*?)</details>', html, re.S)
    assert resume and " open" not in resume[0].split(">", 1)[0]
    assert "1 000 ₽" in resume[1] and "31.10.2026, 12:19 (UTC+03:00)" in resume[1]
    assert "•••• 4242" in resume[1] and "<details" not in resume[1]
    assert 'action="/billing/subscription/resume" method="post"' in resume[1]
    assert 'name="csrf_token" value="synthetic-csrf"' in resume[1]
    assert 'name="expected_authority_version" value="7"' in resume[1]
    assert 'name="resume_quote_id" value="synthetic-resume"' in resume[1]
    consent = re.search(r'<input[^>]*name="resume_consent"[^>]*>', resume[1])
    assert consent and "required" in consent[0] and "checked" not in consent[0]


@pytest.mark.parametrize("resolution", ["pending", "unknown", "unknown_pending", "provider_key_expired"])
@pytest.mark.parametrize("active", [False, True])
@pytest.mark.parametrize("amount", [None, "1 000 ₽"])
def test_subscription_uncertain_payment_never_offers_competing_purchase_or_resume(resolution, active, amount):
    subscription = SimpleNamespace(
        plan_code="personal", state="active", cycle="month", paid_through=datetime(2026, 11, 3, tzinfo=UTC),
        recurring_allowed=False, recurring_authority_version=7, renewal_resolution=resolution,
    )
    html = _subscription_view(
        subscription=subscription, active=active, method_available=True,
        payment_method_label="•••• 4242", resume_quote_id="synthetic-resume",
        pending_charge_amount_label=amount, pending_payment_url="/billing/checkout/status/INV-SYNTHETIC",
    )
    assert 'href="/billing/checkout?cycle=month"' not in html
    assert 'action="/billing/subscription/resume"' not in html
    assert 'action="/billing/subscription/early-preview"' not in html
    assert ('href="/billing/checkout/status/INV-SYNTHETIC"' in html or 'href="/billing/history#billing-help"' in html)
    assert 'role="status"' in html


def test_subscription_prepared_renewal_keeps_early_preview_and_direct_cancel():
    subscription = SimpleNamespace(
        plan_code="personal", state="active", cycle="month", paid_through=datetime(2026, 11, 3, tzinfo=UTC),
        recurring_allowed=True, recurring_authority_version=7, renewal_resolution=None,
    )
    html = _subscription_view(subscription=subscription, method_available=True, payment_method_label="•••• 4242", prepared_charge_amount_label="1 000 ₽")
    assert 'action="/billing/subscription/early-preview" method="post"' in html
    assert 'action="/billing/subscription/cancel" method="post"' in html
    assert "31.10.2026, 12:19 (UTC+03:00)" in html and "1 000 ₽" in html
    assert "Подготовлено" in html and "Уже отправленный платеж" not in html


def test_subscription_trial_never_claims_free_or_paid_access():
    html = _subscription_view(
        subscription=SimpleNamespace(plan_code="trial", cycle="month", paid_through=None, recurring_allowed=False),
        active=False, subscription_trial_active=True, subscription_plan_label="Пробный период",
        trial_ends_at_label="03.11.2026, 12:19 (UTC+03:00)", trial_ends_short_label="03.11.2026",
    )
    assert "Пробный" in html and "03.11.2026" in html
    assert "Сейчас действует бесплатный тариф" not in html
    assert "Оплачено до" not in html


@pytest.mark.asyncio
@pytest.mark.parametrize("plan_code", ["personal", "trial", "free"])
async def test_subscription_route_uses_effective_plan_and_viewer_local_calendar_day(monkeypatch, plan_code):
    from twobrain_rec_server.cabinet import user_time

    cutoff = (datetime.now(UTC) + timedelta(days=30)).replace(hour=23, minute=30, second=0, microsecond=0)
    principal = SimpleNamespace(user_id=UUID(int=1), session_id=None, auth_via_session=False)
    subscription = SimpleNamespace(
        plan_code=plan_code, state=plan_code, cycle="year", paid_through=cutoff,
        trial_ends_at=cutoff if plan_code == "trial" else None,
        billing_owner_id=principal.user_id, recurring_allowed=False,
        recurring_authority_version=7, renewal_resolution=None, next_capacity_bytes=None,
    )
    db = SimpleNamespace(scalar=AsyncMock(side_effect=[subscription, None]), execute=AsyncMock(return_value=[]))
    captured = {}
    monkeypatch.setattr(billing_routes, "_billing_role", AsyncMock(return_value="owner"))
    monkeypatch.setattr(billing_routes, "_next_renewal_label", AsyncMock(return_value=None))
    monkeypatch.setattr(billing_routes, "_verified_receipt_contact", AsyncMock(return_value=None))
    monkeypatch.setattr(billing_routes, "_approved_personal_catalog", AsyncMock(return_value={}))
    monkeypatch.setattr(billing_routes, "_page_shell", lambda _title, **context: captured.update(context) or "subscription")
    monkeypatch.setattr(billing_routes, "_csrf_token_for_principal", lambda *_a, **_k: "synthetic")
    monkeypatch.setattr(billing_routes, "billing_checkout_allowed", lambda *_a: True)
    monkeypatch.setattr(billing_routes, "build_request_browser_provider_context", lambda *_a, **_k: {})
    request = Request({"type": "http", "method": "GET", "scheme": "https", "server": ("graf.test", 443), "path": "/billing/subscription", "headers": [], "query_string": b"", "app": SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace()))})
    token = user_time._display_timezone.set("Europe/Istanbul")
    try:
        response = await billing_routes.billing_subscription_page(request, tenant_scope=SimpleNamespace(workspace_id=UUID(int=2), device_id=UUID(int=3)), principal=principal, db=db)
    finally:
        user_time._display_timezone.reset(token)
    assert response.status_code == 200
    assert captured["active"] is (plan_code == "personal")
    assert captured["subscription_trial_active"] is (plan_code == "trial")
    expected_local_day = (cutoff + timedelta(hours=3)).strftime("%d.%m.%Y")
    if plan_code == "personal":
        assert captured["paid_through_short_label"] == expected_local_day
        assert captured["paid_through_label"] == expected_local_day + ", 02:30 (UTC+03:00)"
    elif plan_code == "trial":
        assert captured["trial_ends_short_label"] == expected_local_day
        assert captured["trial_ends_at_label"] == expected_local_day + ", 02:30 (UTC+03:00)"
    assert captured["manual_checkout_url"] == "/billing/checkout?cycle=year"
