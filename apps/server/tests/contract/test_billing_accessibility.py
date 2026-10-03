import json
import subprocess
from pathlib import Path

import pytest

from twobrain_rec_server.cabinet.templates import render_template

ROOT = Path(__file__).parents[4]
TEMPLATE_ROOT = ROOT / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages"


@pytest.mark.browser
def test_billing_keyboard_focus_and_error_recovery_in_browser(tmp_path):
    from twobrain_rec_server.billing.catalog import plan_descriptor

    context = dict(
        plan=plan_descriptor("personal"),
        billing_enabled=True,
        catalog_ready=True,
        checkout_idempotency_key="synthetic",
        checkout_quote_id="synthetic-quote",
        monthly_price_label="1 000 ₽",
        annual_price_label="10 000 ₽",
        csrf_token="synthetic",
        embedded=False,
        receipt_contact_ready=True,
        receipt_contact_label="demo@example.test",
        checkout_cycle="month",
        catalog_storage_label="5 ГБ",
        checkout_has_discount=False,
        checkout_base_price_label="1 000 ₽",
        checkout_period_label="29.09.2026 — 29.10.2026",
        checkout_next_attempt_label="26.10.2026",
        checkout_preview={
            "payable_amount_label": "1 000 ₽", "list_amount_label": "1 000 ₽",
            "discount_label": "0 ₽", "next_amount_label": "1 000 ₽",
            "cycle_label": "месяц",
        },
    )
    pages = {
        name: render_template(
            "cabinet/pages/billing_checkout_content.html",
            **context,
            checkout_result=result,
        )
        for name, result in (("checkout", None), ("error", "offer_changed"))
    }
    for name, changes in {
        "checkout-first-annual": {
            "checkout_cycle": "year",
            "checkout_period_label": "Год после подтверждения оплаты",
            "checkout_next_attempt_label": (
                "За 3 дня до конца оплаченного периода; точная дата появится после оплаты"
            ),
            "receipt_contact_label": "billing.team.with.long.address@example.test",
            "checkout_preview": {
                "payable_amount_label": "10 000 ₽", "list_amount_label": "10 000 ₽",
                "discount_label": "0 ₽", "next_amount_label": "10 000 ₽",
                "cycle_label": "год",
            },
        },
        "checkout-promo-error": {
            "checkout_result": "promo_invalid", "checkout_promo_code": "DEMO",
            "promo_preview_error": "Промокод не подходит для выбранного периода.",
        },
        "checkout-pending": {
            "checkout_blocked": True,
            "checkout_status_url": "/billing/checkout/status/INV-SYNTHETIC",
        },
        "checkout-receipt": {
            "receipt_contact_ready": False, "receipt_contact_label": None,
            "receipt_contact_action_url": "/settings/account?next=%2Fbilling%2Fcheckout%3Fcycle%3Dyear",
        },
    }.items():
        pages[name] = render_template(
            "cabinet/pages/billing_checkout_content.html", **{**context, **changes},
        )
    for result in (None, "refreshed", "unchanged"):
        pages[f"status-{result}"] = render_template(
            "cabinet/pages/billing_operation_status_content.html",
            embedded=False,
            invoice={"safe_number": "INV-SYNTHETIC"},
            amount_label="1 000 ₽",
            operation_state="unknown",
            operation_state_label="Уточняем статус",
            updated_at_label="20.09.2026",
            status_result=result,
            can_refresh_payment=True,
        )
    for state in ("succeeded", "succeeded_refused", "canceled", "failed", "provider_pending"):
        pages[f"status-{state}"] = render_template(
            "cabinet/pages/billing_operation_status_content.html",
            embedded=False, csrf_token="synthetic", billing_enabled=True,
            invoice={"safe_number": "INV-SYNTHETIC"}, amount_label="1 000 ₽",
            operation_state=state, operation_state_label="Статус оплаты",
            updated_at_label="29.09.2026", can_continue_payment=state == "provider_pending",
            support_email="support@example.test", retry_payment_url="/billing/checkout?cycle=year",
        )
    for purpose in ("storage_upgrade", "early_renewal", "storage_schedule"):
        pages[purpose] = render_template(
            "cabinet/pages/billing_purchase_content.html",
            csrf_token="synthetic",
            purchase_error=None,
            purchase={
                "quote_id": "synthetic-quote",
                "purpose": purpose,
                "title": "Подтверждение покупки",
                "capacity_label": "500 ГБ",
                "list_label": "0 ₽" if purpose == "storage_schedule" else "257 500 ₽",
                "payable_label": "0 ₽" if purpose == "storage_schedule" else "2 575 ₽",
                "discount_label": "0 ₽" if purpose == "storage_schedule" else "254 925 ₽",
                "has_discount": purpose != "storage_schedule",
                "next_label": "257 500 ₽",
                "base_label": "10 000 ₽",
                "storage_label": "247 500 ₽",
                "current_capacity_label": "5 ГБ",
                "next_attempt_label": "не запланирована",
                "cycle_label": "год",
                "period_label": "26.09.2026 — 26.09.2027",
                "recurring_allowed": False,
                "method_label": "•••• 4242" if purpose == "early_renewal" else None,
                "deferred": purpose == "storage_schedule",
            },
        )
    pages["packages"] = render_template(
        "cabinet/pages/billing_storage_content.html",
        csrf_token="synthetic", eligible=True, billing_enabled=True,
        current_capacity_label="10 ГБ", selected_package_count=1,
        storage_options=[{
            "package_count": n, "capacity": (n + 1) * 5_000_000_000,
            "label": f"{(n + 1) * 5} ГБ", "addon_label": f"{250 * n} ₽",
            "total_label": f"{1000 + 250 * n} ₽", "cycle_label": "месяц",
        } for n in range(100)],
    )
    invoice = {
        "safe_number": "INV-SYNTHETIC", "amount_label": "1 000 ₽",
        "cycle_label": "месяц", "created_at_label": "29.09.2026",
        "status_label": "Уточняем статус", "receipt_label": "Чек готовится",
        "detail_url": "/billing/invoices/INV-SYNTHETIC",
        "status_url": "/billing/checkout/status/INV-SYNTHETIC",
        "status_action_label": "Проверить оплату",
        "discount_label": None, "receipt_url": None, "refund_mailto": None,
        "payment_method_label": "•••• 4242", "receipt_contact_label": "demo@example.test",
    }
    surface_context = {
        **context, "billing_owner": True, "billing_role": "owner", "result": None,
        "active": True, "billing_result": None, "referral_issue_result": None,
        "plan_code": "personal", "current_plan_code": "personal",
        "support_email": "support@example.test", "trial_state": "already",
        "subscription": {
            "recurring_allowed": True, "recurring_authority_version": 1,
            "state": "active", "cycle": "month", "plan_code": "personal",
            "paid_through": "2026-10-29T12:00:00Z",
        },
        "paid_through_label": "29.10.2026", "next_charge_label": "26.10.2026",
        "next_charge_amount_label": "1 000 ₽", "method_available": True,
        "subscription_plan_label": "Личный", "subscription_cycle_label": "месяц",
        "current_cycle_label": "месяц", "current_price_label": "1 000 ₽",
        "method_label": "•••• 4242", "method_kind": "bank_card",
        "payment_method_label": "•••• 4242", "renewal_allowed": True,
        "processing_unlimited": True, "processing_threshold": "normal",
        "processing_reserved": 0, "processing_reserved_label": "0 минут",
        "processing_used_label": "60 минут", "storage_used_label": "1 ГБ",
        "storage_capacity_label": "5 ГБ", "storage_available_label": "4 ГБ",
        "storage_threshold": "normal", "storage_reserved_label": "0 ГБ",
        "storage_used": 1_000_000_000, "storage_reserved": 0,
        "storage_available": 4_000_000_000, "storage_capacity": 5_000_000_000,
        "meetings_href": "/meetings", "manual_checkout_url": "/billing/checkout?cycle=month",
        "invoice": invoice, "invoices": [invoice], "latest_invoice_summary": invoice,
        "active_promotions": [], "redemptions": [],
        "referral_issued": True, "referral_link": "https://graf.test/r/synthetic",
        "referral_expires_at_label": "29.10.2026", "referral_history": [],
    }
    for name in ("overview", "subscription", "payment_method", "history", "invoice", "usage", "discounts"):
        pages[name] = render_template(
            f"cabinet/pages/billing_{name}_content.html", **surface_context,
        )
    pages["subscription-expired-pending"] = render_template(
        "cabinet/pages/billing_subscription_content.html",
        **{
            **surface_context, "active": False, "paid_through_label": "28.09.2026",
            "subscription": {
                **surface_context["subscription"], "renewal_resolution": "pending",
                "paid_through": "2026-09-28T12:00:00Z",
            },
            "pending_charge_amount_label": "1 000 ₽",
            "pending_payment_url": "/billing/checkout/status/INV-SYNTHETIC",
        },
    )
    for name, changes in {
        "subscription-key-expired": {
            "subscription": {**surface_context["subscription"], "recurring_allowed": False,
                             "renewal_resolution": "provider_key_expired"},
            "method_available": False, "payment_method_label": None,
        },
        "subscription-method-pending": {
            "subscription": {**surface_context["subscription"], "recurring_allowed": False,
                             "renewal_resolution": "method_required"},
            "method_available": False, "payment_method_label": None,
            "pending_charge_amount_label": "1 000 ₽",
            "pending_payment_url": "/billing/checkout/status/INV-SYNTHETIC",
            "renewal_notice": "Автопродление приостановлено. Проверьте способ оплаты.",
            "renewal_action_url": "/billing/payment-method",
            "renewal_action_label": "Проверить способ оплаты",
        },
    }.items():
        pages[name] = render_template(
            "cabinet/pages/billing_subscription_content.html",
            **{**surface_context, **changes},
        )
    pages["subscription-method-pending-on"] = render_template(
        "cabinet/pages/billing_subscription_content.html",
        **{**surface_context,
           "subscription": {**surface_context["subscription"], "renewal_resolution": "method_required"},
           "method_available": False, "payment_method_label": None,
           "pending_charge_amount_label": "1 000 ₽",
           "pending_payment_url": "/billing/checkout/status/INV-SYNTHETIC",
           "renewal_notice": "Автопродление приостановлено. Проверьте способ оплаты.",
           "renewal_action_url": "/billing/payment-method",
           "renewal_action_label": "Проверить способ оплаты"},
    )
    pages["overview-expired-pending"] = render_template(
        "cabinet/pages/billing_overview_content.html",
        **{
            **surface_context, "plan": plan_descriptor("free"), "plan_code": "free",
            "current_plan_code": "free", "active": False, "operation_pending": True,
            "pending_invoice_summary": {"safe_number": "INV-SYNTHETIC"},
            "free_processing_limit_label": "300 минут", "renewal_allowed": True,
            "current_price_label": "0 ₽", "next_charge_label": None,
            "next_charge_amount_label": None, "paid_through_label": None,
            "storage_used_label": "0 Б", "storage_capacity_label": "250 МБ",
        },
    )
    pages["subscription-prepared"] = render_template(
        "cabinet/pages/billing_subscription_content.html",
        **{**surface_context, "prepared_charge_amount_label": "1 000 ₽"},
    )
    subscription_off = {
        **surface_context,
        "subscription": {**surface_context["subscription"], "recurring_allowed": False},
        "paid_through_label": "03.11.2026, 12:19 (UTC+03:00)",
        "paid_through_short_label": "03.11.2026",
        "method_available": False, "payment_method_label": None,
        "resume_quote_id": None,
    }
    for name, changes in {
        "subscription-off-no-card": {},
        "subscription-off-ready": {
            "method_available": True, "payment_method_label": "•••• 4242",
            "resume_quote_id": "synthetic-resume",
            "resume_charge_label": "31.10.2026, 12:19 (UTC+03:00)",
        },
        "subscription-trial": {
            "active": False, "subscription_trial_active": True, "subscription_plan_label": "Пробный период",
            "subscription": {**subscription_off["subscription"], "plan_code": "trial", "paid_through": None},
            "paid_through_label": None, "paid_through_short_label": None,
            "trial_ends_at_label": "03.11.2026, 12:19 (UTC+03:00)",
            "trial_ends_short_label": "03.11.2026",
        },
        "subscription-free": {
            "active": False, "subscription": None, "subscription_plan_label": "Бесплатный",
            "paid_through_label": None, "paid_through_short_label": None,
        },
        **{f"subscription-uncertain-{state}": {
            "subscription": {**subscription_off["subscription"], "renewal_resolution": state},
            "method_available": True, "payment_method_label": "•••• 4242",
            "resume_quote_id": "synthetic-resume", "pending_charge_amount_label": None,
        } for state in ("pending", "unknown", "unknown_pending")},
    }.items():
        pages[name] = render_template(
            "cabinet/pages/billing_subscription_content.html", **{**subscription_off, **changes},
        )
    pages["discounts-error"] = render_template(
        "cabinet/pages/billing_discounts_content.html",
        **{**surface_context, "result": "invalid", "discount_promo_code": "DEMO"},
    )
    for name, changes in {
        "discounts-history-year": {
            "redemptions": [{"discount_label": "Скидка 10%", "state_label": "Применён", "cycle_label": "Год"}],
        },
        "discounts-history-unknown": {
            "redemptions": [{"discount_label": "Скидка 10%", "state_label": "Применён", "cycle_label": ""}],
        },
        "discounts-applied": {"result": "promo_applied", "checkout_promo_active": True},
        "discounts-removed": {"result": "removed"},
    }.items():
        pages[name] = render_template(
            "cabinet/pages/billing_discounts_content.html", **{**surface_context, **changes},
        )
    pages["storage-price-confirmation"] = render_template(
        "cabinet/pages/billing_purchase_content.html", csrf_token="synthetic",
        purchase_error=None,
        purchase={
            "quote_id": "synthetic-quote", "purpose": "storage_schedule",
            "title": "Подтвердите цену следующего периода",
            "capacity_label": "10 ГБ", "current_capacity_label": "10 ГБ",
            "payable_label": "0 ₽", "list_label": "0 ₽", "has_discount": False,
            "next_label": "1 250 ₽", "base_label": "1 000 ₽", "storage_label": "250 ₽",
            "cycle_label": "месяц", "period_label": "Со следующего неоплаченного периода",
            "next_attempt_label": "после сохранения выбора, в ближайшее время",
            "recurring_allowed": True, "method_label": None, "deferred": True,
        },
    )
    pages["referrals"] = render_template("cabinet/pages/referrals_content.html", **surface_context)
    pages["plans"] = render_template(
        "cabinet/pages/billing_plans_content.html", **surface_context,
        selected_cycle="year",
        plans=[{
            "code": code, "label": label, "storage_label": capacity,
            "processing_mode": "limited" if code == "free" else "unlimited",
            "processing_label": "300 минут", "is_current": code == "personal",
            "monthly_amount_label": "1 000 ₽" if code == "personal" else "0 ₽",
            "annual_amount_label": "10 000 ₽" if code == "personal" else "0 ₽",
            "catalog_ready": True,
            "annual_saving_label": "2 000 ₽ экономии за год" if code == "personal" else None,
        } for code, label, capacity in (
            ("free", "Бесплатный", "250 МБ"), ("trial", "Пробный", "500 МБ"),
            ("personal", "Личный", "5 ГБ"),
        )],
    )
    from twobrain_rec_server.cabinet.rendering_shared import _page_shell

    for name in ("checkout", "plans", "packages", "discounts", "discounts-history-year", "discounts-history-unknown", "discounts-error", "subscription-off-no-card", "subscription-off-ready", "subscription"):
        pages[f"shell-{name}"] = _page_shell(
            "Оплата", content=pages[name], embedded=False,
            csrf_token="synthetic", active_nav="settings", settings_active="billing",
        )
    fixture = tmp_path / "billing-pages.json"
    fixture.write_text(json.dumps(pages), encoding="utf-8")
    script = Path(__file__).parents[1] / "browser/billing-accessibility.test.cjs"
    result = subprocess.run(
        ["node", str(script), str(fixture)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_billing_templates_keep_explicit_actions_and_live_statuses() -> None:
    overview = (TEMPLATE_ROOT / "billing_overview_content.html").read_text(encoding="utf-8")
    subscription = (TEMPLATE_ROOT / "billing_subscription_content.html").read_text(encoding="utf-8")
    history = (TEMPLATE_ROOT / "billing_history_content.html").read_text(encoding="utf-8")
    assert "Без лимита" in overview
    assert "Отключить автопродление" in subscription
    assert 'role="status"' in history
    assert "refund status" not in history.lower()


def test_every_billing_screen_keeps_payment_help_or_history_after_the_primary_panel() -> None:
    for name in (
        "billing_overview_content.html",
        "billing_usage_content.html",
        "billing_subscription_content.html",
        "billing_payment_method_content.html",
        "billing_storage_content.html",
        "billing_checkout_content.html",
        "billing_history_content.html",
        "billing_invoice_content.html",
        "billing_plans_content.html",
        "billing_discounts_content.html",
        "billing_operation_status_content.html",
    ):
        html = (TEMPLATE_ROOT / name).read_text(encoding="utf-8")
        if name == "billing_operation_status_content.html":
            html = render_template(
                "cabinet/pages/" + name,
                invoice={"safe_number": "INV-SYNTHETIC"},
                amount_label="1 000 ₽", operation_state="unknown",
                operation_state_label="Уточняем статус", updated_at_label="29.09.2026",
            )
        if name == "billing_overview_content.html":
            assert 'href="/billing/history">История платежей</a>' in html
            assert html.index('href="/billing/history">История платежей</a>') > html.index('id="billing-history-title"')
            assert "Нужна помощь с оплатой?" not in html
            continue
        assert "помощь с оплатой" in html.lower()
        destination = (
            "#billing-help" if name == "billing_history_content.html" else "/billing/history#billing-help"
        )
        assert f'href="{destination}"' in html
        assert html.lower().index("помощь с оплатой") > html.index("</section>")


def test_non_payer_billing_surfaces_keep_quota_state_without_usage_values() -> None:
    from twobrain_rec_server.billing.catalog import plan_descriptor

    values = {
        name: "private-" + name
        for name in (
            "processing_used_label",
            "processing_remaining_label",
            "storage_used_label",
            "storage_reserved_label",
            "storage_available_label",
        )
    }
    context = dict(
        embedded=False,
        settings_navigation=[],
        settings_active="billing",
        plan=plan_descriptor("free"),
        plan_code="free",
        meetings_href="/meetings",
        processing_threshold="approaching",
        processing_reset_at_label="later",
        free_processing_limit_label="300 минут",
        storage_capacity_label="5 ГБ",
        **values,
    )
    for role in (None, "member", "corporate_owner", "owner"):
        for plan_code in ("personal", "free"):
            for threshold in ("normal", "approaching", "exhausted"):
                context.update(
                    plan_code=plan_code,
                    plan=plan_descriptor(plan_code),
                    processing_threshold=threshold,
                    processing_unlimited=plan_code != "free",
                    storage_threshold="full",
                )
                for page in ("billing_overview_content.html", "billing_usage_content.html"):
                    html = render_template(
                        "cabinet/pages/" + page, billing_role=role, billing_owner=False, **context
                    )
                    assert all(value not in html for value in values.values())
                    assert "5 ГБ" in html
                    if plan_code == "free":
                        assert "300 минут" in html
                    assert ("Дождитесь сброса later" in html) == (
                        plan_code == "free" and threshold != "normal"
                    )
                    if page == "billing_usage_content.html":
                        assert ("Без лимита по минутам и встречам" in html) == (
                            plan_code == "personal"
                        )
                        assert "Архив заполнен: новое аудио не сохраняется" in html
                        assert 'href="/meetings">Управлять архивом</a>' in html
                        assert ("?archive_audio=false#manual-upload" in html) == (
                            plan_code == "personal" or threshold != "exhausted"
                        )
                    if plan_code == "free" and threshold == "exhausted":
                        assert (
                            "новая обработка, в том числе без сохранения аудио, недоступна" in html
                        )
    for payer in (False, True):
        unavailable = render_template(
            "cabinet/pages/billing_usage_content.html",
            billing_owner=payer,
            usage_projection_state="unavailable",
            **context,
        )
        assert "Данные использования недоступны" in unavailable
        assert "Количественные данные хранилища временно недоступны" in unavailable
        assert "доступны плательщику" not in unavailable and "видит плательщик" not in unavailable
        assert all(value not in unavailable for value in values.values())
        assert "5 ГБ" not in unavailable and "300 минут" not in unavailable
    owner = render_template(
        "cabinet/pages/billing_overview_content.html",
        billing_role="owner",
        billing_owner=True,
        **context,
    )
    assert values["processing_used_label"] in owner
    assert values["storage_used_label"] in owner


def test_checkout_uses_amount_specific_yookassa_actions_without_js() -> None:
    html = (TEMPLATE_ROOT / "billing_checkout_content.html").read_text(encoding="utf-8")
    assert 'form="billing-promo-preview" type="submit" name="preview_action" value="month"' in html
    assert 'form="billing-promo-preview" type="submit" name="preview_action" value="year"' in html
    assert 'name="cycle" value="{{ checkout_cycle }}"' in html
    assert 'action="/billing/checkout/preview" method="post"' in html
    assert "checkout_preview" in html
    assert "monthly_price_label|default" in html
    assert "annual_price_label|default" in html
    assert "annual_saving_label" in html
    assert "Перейти к оплате" not in html


def test_billing_overview_declares_landmark_order_and_single_primary_contract() -> None:
    html = (TEMPLATE_ROOT / "billing_overview_content.html").read_text(encoding="utf-8")
    ordered_ids = (
        "billing-summary-title",
        "billing-workspace-title",
        "billing-method-title",
        "billing-history-title",
    )
    assert [html.index(section_id) for section_id in ordered_ids] == sorted(
        html.index(section_id) for section_id in ordered_ids
    )
    assert 'class="cabinet-main billing-page billing-overview"' in html
    assert "data-billing-primary" in html
    assert 'role="status"' in html
    assert 'role="alert"' in html


def test_plans_and_checkout_use_named_period_navigation_and_native_coupon_disclosure() -> None:
    plans = (TEMPLATE_ROOT / "billing_plans_content.html").read_text(encoding="utf-8")
    checkout = (TEMPLATE_ROOT / "billing_checkout_content.html").read_text(encoding="utf-8")

    assert 'aria-label="Период тарифа"' in plans
    assert 'aria-current="true"' in plans
    assert 'href="/billing/plans?cycle=month"' in plans
    assert 'href="/billing/plans?cycle=year"' in plans
    assert 'aria-label="Период оплаты"' in checkout
    assert 'action="/billing/checkout/preview" method="post"' in checkout
    assert 'id="billing-promo-preview"' in checkout
    assert 'form="billing-promo-preview" type="submit" name="preview_action" value="month"' in checkout
    assert 'form="billing-promo-preview" type="submit" name="preview_action" value="year"' in checkout
    assert 'form="billing-promo-preview" id="billing-promo"' in checkout
    assert '<details class="billing-coupon"' in checkout
    assert "<summary" in checkout
    assert checkout.count("data-billing-primary") == 1


def test_billing_css_scopes_reflow_and_forced_color_contracts() -> None:
    css = (
        ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
    ).read_text(encoding="utf-8")
    assert ".billing-page" in css
    assert ".billing-plan-grid" in css
    assert ".billing-checkout-card" in css
    assert "@media (max-width: 760px)" in css
    assert "@media (forced-colors: active)" in css
    assert (
        '.billing-period-switch :is(a, button)[aria-current="true"] { outline: 2px solid Highlight;'
        in css
    )


def test_checkout_renders_server_calculated_promo_amounts() -> None:
    from twobrain_rec_server.billing.catalog import plan_descriptor
    from twobrain_rec_server.cabinet.templates import render_template
    from twobrain_rec_server.cabinet.view_models import settings_category_navigation

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
        checkout_result="promo_applied",
        checkout_promo_code="SAVE10",
        checkout_cycle="month",
        checkout_has_discount=True,
        receipt_contact_ready=True,
        checkout_next_attempt_label="26.10.2026",
        checkout_preview={
            "cycle_label": "месяц",
            "list_amount_label": "790 ₽",
            "discount_label": "−79 ₽ (10%)",
            "payable_amount_label": "711 ₽",
            "next_amount_label": "790 ₽",
        },
        promo_preview_error=None,
    )
    assert "Разовая скидка" in html
    assert "−79 ₽ (10%)" in html
    assert "711 ₽" in html
    assert "Оплатить 711 ₽ в ЮKassa" in html
    assert 'action="/billing/checkout/preview"' in html
    assert 'name="promo_code" value="SAVE10"' in html
    assert 'form="billing-promo-preview" type="submit" name="preview_action" value="year"' in html
    assert "Списание при автопродлении" in html
    assert "referral" not in html.lower()


def test_checkout_promo_error_preserves_safe_input_and_associates_error() -> None:
    from twobrain_rec_server.billing.catalog import plan_descriptor
    from twobrain_rec_server.cabinet.templates import render_template
    from twobrain_rec_server.cabinet.view_models import settings_category_navigation

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
        checkout_result="promo_invalid",
        checkout_promo_code="WELCOME10",
    )
    assert 'id="billing-checkout-error" role="alert"' in html
    assert 'id="billing-promo"' in html
    assert 'value="WELCOME10"' in html
    assert 'aria-describedby="billing-checkout-error"' in html
    assert 'aria-invalid="true"' in html

    discounts_html = render_template(
        "cabinet/pages/billing_discounts_content.html",
        embedded=False,
        settings_navigation=settings_category_navigation(active="billing"),
        settings_active="billing",
        csrf_token="synthetic-csrf",
        billing_owner=True,
        result="invalid",
        active_promotions=[],
        redemptions=[],
    )
    assert 'id="billing-discount-error"' in discounts_html
    assert 'role="alert"' in discounts_html
    assert 'aria-describedby="billing-discount-error"' in discounts_html
    assert 'aria-invalid="true"' in discounts_html


def test_payment_method_delete_and_discount_actions_have_csrf_and_labels() -> None:
    method = (TEMPLATE_ROOT / "billing_payment_method_content.html").read_text(encoding="utf-8")
    discounts = (TEMPLATE_ROOT / "billing_discounts_content.html").read_text(encoding="utf-8")
    assert 'action="/billing/payment-method/delete" method="post"' in method
    assert "Удалить способ оплаты" in method
    assert 'action="/billing/discounts/apply" method="post"' in discounts
    assert "checkout_promo_active|default(False)" in discounts
    assert "Применить" in discounts
    assert "Удалить" in discounts


def test_cabinet_css_declares_reflow_focus_and_reduced_motion_guards() -> None:
    css = (
        ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
    ).read_text(encoding="utf-8")
    assert "@media (max-width: 640px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ":focus-visible" in css
    assert ".skip-link:focus" in css


def test_billing_copy_controls_have_a_keyboard_safe_browser_handler() -> None:
    script = (
        ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    ).read_text(encoding="utf-8")
    assert 'querySelectorAll("[data-copy-value], [data-copy-target]")' in script
    assert 'role", "status"' in script
    assert 'document.execCommand("copy")' in script


def test_account_close_has_no_js_confirmation_fallback() -> None:
    template = (TEMPLATE_ROOT / "settings_account_content.html").read_text(encoding="utf-8")
    assert 'method="post"' in template
    assert "Закрыть аккаунт" in template
    assert "csrf" in template.lower()


def test_manual_upload_exposes_explicit_archive_choice_and_transmits_it() -> None:
    fragment = (
        ROOT
        / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/manual_upload.html"
    ).read_text(encoding="utf-8")
    script = (
        ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    ).read_text(encoding="utf-8")
    assert 'ui.switch("archive_audio", "Сохранить аудио", checked=True' in fragment
    assert "data_manual_upload_archive=True" in fragment
    assert 'hint_id="manual-upload-archive-help"' in fragment
    assert "Без аудио останутся расшифровка и итоги. Минуты тарифа спишутся." in fragment
    assert 'data.append("archive_audio", activity.archiveAudio ? "true" : "false")' in script


def test_no_archive_upgrade_cta_opens_manual_upload_with_archive_disabled() -> None:
    script = (
        ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    ).read_text(encoding="utf-8")
    for embedded in (False, True):
        usage = render_template(
            "cabinet/pages/billing_usage_content.html",
            embedded=embedded,
            processing_threshold="normal",
            processing_unlimited=True,
            processing_used_label="0 минут",
            storage_used=0,
            storage_reserved=0,
            storage_available=0,
            storage_capacity=250_000_000,
            storage_threshold="full",
            storage_threshold_label="Архив заполнен",
            billing_owner=True,
        )
        prefix = "/desktop" if embedded else ""
        assert f'href="{prefix}/meetings?archive_audio=false#manual-upload"' in usage
    assert 'window.location.hash === "#manual-upload"' in script
    assert 'params.get("archive_audio") === "false"' in script
