from pathlib import Path

ROOT = Path(__file__).parents[4]


def test_public_landing_is_tracked_as_a_separate_manual_gate() -> None:
    review = (ROOT / "docs/evidence/140-user-account-billing/landing-review.md").read_text(encoding="utf-8")
    assert "не выполнено" in review or "partial manual pass" in review
    assert "200%" in review
    assert "clean-room" in review


def test_billing_ia_contract_names_recoverable_states() -> None:
    contract = (ROOT / "specs/140-user-account-billing/contracts/account-ia-ux-ui-cx.md").read_text(encoding="utf-8")
    for phrase in ("Обработать без сохранения аудио", "Отключить автопродление", "Нужна помощь с оплатой?"):
        assert phrase in contract


def test_billing_ia_contract_matches_current_server_route_namespace() -> None:
    contract = (ROOT / "specs/140-user-account-billing/contracts/account-ia-ux-ui-cx.md").read_text(
        encoding="utf-8"
    )
    for route in ("`/billing`", "`/billing/usage`", "`/billing/plans`", "`/billing/checkout`", "`/billing/history`"):
        assert route in contract
    assert "`/account/workspaces/{ws}/billing`" not in contract


def test_storage_degraded_state_does_not_redirect_back_to_itself() -> None:
    source = (ROOT / "apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py").read_text(
        encoding="utf-8"
    )
    assert 'return RedirectResponse("/billing/storage?result=unavailable"' not in source
    assert 'result="unavailable"' in source


def test_invoice_surfaces_use_localized_amount_helper() -> None:
    source = (ROOT / "apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py").read_text(
        encoding="utf-8"
    )
    assert '"amount_label": _billing_amount_label' in source
    assert '"amount_label": f"{invoice.amount_minor / 100:.2f} {invoice.currency}"' not in source


def test_invoice_surfaces_do_not_fall_back_to_raw_provider_status() -> None:
    invoice = (
        ROOT / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_invoice_content.html"
    ).read_text(encoding="utf-8")
    history = (
        ROOT / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_history_content.html"
    ).read_text(encoding="utf-8")
    assert "status_label|default(invoice.status)" not in invoice + history
    assert 'status_label|default("Статус уточняется")' in invoice + history


def test_usage_surface_does_not_fall_back_to_raw_storage_threshold() -> None:
    usage = (
        ROOT / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_usage_content.html"
    ).read_text(encoding="utf-8")
    assert "storage_threshold_label|default(storage_threshold)" not in usage
    assert 'storage_threshold_label|default("Состояние уточняется")' in usage


def test_operation_status_does_not_offer_checkout_when_billing_is_disabled() -> None:
    template = (
        ROOT
        / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html"
    ).read_text(encoding="utf-8")
    route = (ROOT / "apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py").read_text(encoding="utf-8")
    assert "billing_enabled|default(False)" in template
    assert "Проверить статус" in template
    assert "Проверить в ЮKassa" not in template
    assert "billing_enabled=bool(request.app.state.settings.billing_checkout_enabled)" in route


def test_status_refresh_defers_cross_workspace_referral_reward() -> None:
    route = (ROOT / "apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py").read_text(encoding="utf-8")
    reconciliation = (
        ROOT / "apps/server/src/twobrain_rec_server/billing/webhook_reconciliation.py"
    ).read_text(encoding="utf-8")
    assert "defer_referral_reward=True" in route
    assert "status_refresh_" in reconciliation
    assert '"referral_reward_deferred": True' in reconciliation


def test_history_uses_localized_timestamp_view_model() -> None:
    template = (
        ROOT / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_history_content.html"
    ).read_text(encoding="utf-8")
    route = (ROOT / "apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py").read_text(encoding="utf-8")
    assert "invoice.created_at.strftime" not in template
    assert "invoice.created_at_label" in template
    assert '"created_at_label": _billing_datetime_label(invoice.created_at)' in route


def test_subscription_and_discount_surfaces_gate_disabled_checkout_actions() -> None:
    subscription = (
        ROOT
        / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html"
    ).read_text(encoding="utf-8")
    discounts = (
        ROOT / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_discounts_content.html"
    ).read_text(encoding="utf-8")
    assert 'billing_enabled|default(False)' in subscription
    assert 'href="/billing/checkout">Выбрать тариф</a>' in subscription
    assert "{% if billing_enabled|default(True) %}<form action=\"/billing/discounts/apply\"" in discounts


def test_billing_surfaces_keep_contextual_non_coercive_upgrade_copy() -> None:
    overview = (
        ROOT
        / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_overview_content.html"
    ).read_text(encoding="utf-8")
    usage = (
        ROOT
        / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_usage_content.html"
    ).read_text(encoding="utf-8")
    assert "Использовано 80% месячного лимита обработки" in overview
    assert "Осталось {{ processing_remaining_label }} до сброса {{ processing_reset_at_label }}" in overview
    assert "После окончания автоматически включится Free" in overview
    assert "Платный режим закончился" in overview
    assert "через {{ trial_remaining_label }}" in overview
    assert "обработка без сохранения аудио также недоступна до этого момента" in overview
    assert 'href="/meetings?archive_audio=false#manual-upload"' not in overview
    assert "Переход на «Личный» необязателен" in usage
    assert "Осталось {{ processing_remaining_label }} до сброса {{ processing_reset_at_label }}" in usage
    assert "Увеличить хранилище" in usage
    assert "удалить старые записи" in usage
    assert "обработать без сохранения аудио" in usage
    assert "Управлять архивом" in usage


def test_billing_navigation_uses_approved_russian_labels() -> None:
    overview = (
        ROOT
        / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_overview_content.html"
    ).read_text(encoding="utf-8")
    plans = (
        ROOT
        / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_plans_content.html"
    ).read_text(encoding="utf-8")
    assert "Управлять хранением" in overview
    assert "Изменить способ оплаты" in overview
    assert "Настроить хранилище" in plans


def test_referral_history_localizes_paid_lifecycle_state() -> None:
    source = (ROOT / "apps/server/src/twobrain_rec_server/cabinet/web_routes/referrals.py").read_text(
        encoding="utf-8"
    )
    assert '"paid": "Оплата подтверждена, бонус ожидает 14 дней"' in source


def test_referrals_use_account_settings_context_instead_of_billing_active_state() -> None:
    source = (ROOT / "apps/server/src/twobrain_rec_server/cabinet/web_routes/referrals.py").read_text(
        encoding="utf-8"
    )
    assert 'settings_active="account"' in source
    assert 'settings_active="billing"' not in source
