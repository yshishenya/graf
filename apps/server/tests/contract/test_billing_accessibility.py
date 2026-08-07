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


def test_account_close_has_no_js_confirmation_fallback() -> None:
    template = (TEMPLATE_ROOT / "settings_account_content.html").read_text(encoding="utf-8")
    assert 'method="post"' in template
    assert "Закрыть аккаунт" in template
    assert "csrf" in template.lower()
