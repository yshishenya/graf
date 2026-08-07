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
