from pathlib import Path

ROOT = Path(__file__).parents[4]


def test_public_landing_is_tracked_as_a_separate_manual_gate() -> None:
    review = (ROOT / "docs/evidence/140-user-account-billing/landing-review.md").read_text(encoding="utf-8")
    assert "не выполнено" in review
    assert "200%" in review
    assert "clean-room" in review


def test_billing_ia_contract_names_recoverable_states() -> None:
    contract = (ROOT / "specs/140-user-account-billing/contracts/account-ia-ux-ui-cx.md").read_text(encoding="utf-8")
    for phrase in ("Обработать без сохранения аудио", "Отключить автопродление", "Нужна помощь с оплатой?"):
        assert phrase in contract


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
    assert "можно запустить без сохранения аудио" in overview
    assert 'href="/meetings?archive_audio=false#manual-upload"' in overview
    assert "Переход на «Личный» необязателен" in usage
    assert "Осталось {{ processing_remaining_label }} до сброса {{ processing_reset_at_label }}" in usage
    assert "Увеличить хранилище" in usage
    assert "удалить старые записи" in usage
    assert "обработать без сохранения аудио" in usage
