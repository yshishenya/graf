from pathlib import Path

ROOT = Path(__file__).parents[4]
TEMPLATE_ROOT = ROOT / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages"


def test_billing_templates_keep_explicit_actions_and_live_statuses() -> None:
    overview = (TEMPLATE_ROOT / "billing_overview_content.html").read_text(encoding="utf-8")
    subscription = (TEMPLATE_ROOT / "billing_subscription_content.html").read_text(encoding="utf-8")
    history = (TEMPLATE_ROOT / "billing_history_content.html").read_text(encoding="utf-8")
    assert "Без лимита по минутам" in overview
    assert "Отключить автопродление" in subscription
    assert 'role="status"' in history
    assert "refund status" not in history.lower()


def test_every_billing_screen_keeps_payment_help_after_the_primary_panel() -> None:
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
        assert "Нужна помощь с оплатой?" in html
        assert 'href="/billing/history"' in html
        assert html.index("Нужна помощь с оплатой?") > html.index("</section>")


def test_member_billing_surfaces_do_not_render_workspace_usage_values() -> None:
    overview = (TEMPLATE_ROOT / "billing_overview_content.html").read_text(encoding="utf-8")
    usage = (TEMPLATE_ROOT / "billing_usage_content.html").read_text(encoding="utf-8")

    assert 'billing_role in ["member", "corporate_owner"]' in overview
    assert 'billing_role in ["member", "corporate_owner"]' in usage
    assert "Точные объёмы использования видит владелец биллинга" in usage


def test_checkout_uses_amount_specific_yookassa_actions_without_js() -> None:
    html = (TEMPLATE_ROOT / "billing_checkout_content.html").read_text(encoding="utf-8")
    assert 'href="/billing/checkout?cycle=month"' in html
    assert 'href="/billing/checkout?cycle=year"' in html
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
        "billing-offer-title",
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
    assert 'href="/billing/checkout?cycle=month"' in checkout
    assert 'href="/billing/checkout?cycle=year"' in checkout
    assert '<details class="billing-coupon"' in checkout
    assert '<summary' in checkout
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
        monthly_price_label="790 ₽",
        annual_price_label="7 900 ₽",
        checkout_result="promo_applied",
        checkout_promo_code="SAVE10",
        checkout_cycle="month",
        checkout_preview={
            "cycle_label": "месяц",
            "list_amount_label": "790 ₽",
            "discount_label": "−79 ₽ (10%)",
            "payable_amount_label": "711 ₽",
            "next_amount_label": "790 ₽",
        },
        promo_preview_error=None,
    )
    assert "Цена по каталогу" in html
    assert "−79 ₽ (10%)" in html
    assert "711 ₽" in html
    assert 'Оплатить 711 ₽ в YooKassa — месяц' in html
    assert 'href="/billing/checkout?cycle=year"' in html
    assert "Следующее списание" in html
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
    assert 'checkout_promo_active|default(False)' in discounts
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
    script = (ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js").read_text(
        encoding="utf-8"
    )
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
    usage = (TEMPLATE_ROOT / "billing_usage_content.html").read_text(encoding="utf-8")
    script = (ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js").read_text(
        encoding="utf-8"
    )
    assert 'href="/meetings?archive_audio=false#manual-upload"' in usage
    assert 'window.location.hash === "#manual-upload"' in script
    assert 'params.get("archive_audio") === "false"' in script
