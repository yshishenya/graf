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
    ):
        html = (TEMPLATE_ROOT / name).read_text(encoding="utf-8")
        assert "Нужна помощь с оплатой?" in html
        assert 'href="/billing/history"' in html
        assert html.index("Нужна помощь с оплатой?") > html.index("</section>")


def test_checkout_uses_amount_specific_yookassa_actions_without_js() -> None:
    html = (TEMPLATE_ROOT / "billing_checkout_content.html").read_text(encoding="utf-8")
    assert 'name="cycle" value="month"' in html
    assert 'name="cycle" value="year"' in html
    assert "Оплатить 790 ₽ в YooKassa" in html
    assert "Оплатить 7 900 ₽ в YooKassa" in html
    assert "Перейти к оплате" not in html


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
    assert 'data-manual-upload-archive checked' in fragment
    assert "исходное аудио после обработки" in fragment
    assert 'data.append("archive_audio", activity.archiveAudio ? "true" : "false")' in script


def test_no_archive_upgrade_cta_opens_manual_upload_with_archive_disabled() -> None:
    usage = (TEMPLATE_ROOT / "billing_usage_content.html").read_text(encoding="utf-8")
    script = (ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js").read_text(
        encoding="utf-8"
    )
    assert 'href="/meetings?archive_audio=false#manual-upload"' in usage
    assert 'window.location.hash === "#manual-upload"' in script
    assert 'params.get("archive_audio") === "false"' in script
