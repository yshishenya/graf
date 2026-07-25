from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
FRAGMENT = REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_share.html"
CSS = REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"
JS = REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"


def test_share_fragment_is_simple_first_and_accessible() -> None:
    source = FRAGMENT.read_text(encoding="utf-8")

    assert 'role="dialog"' in source
    assert 'aria-modal="true"' in source
    assert 'id="meeting-share-dialog"' in source
    assert "data-share-dialog open" not in source
    assert 'data-share-recipient-input' in source
    assert 'role="combobox"' in source
    assert 'aria-controls="share-recipient-results-{{ meeting_id }}"' in source
    assert 'role="listbox"' in source
    assert "Найти" in source
    assert "Скопировать ссылку" in JS.read_text(encoding="utf-8")
    assert "Открыть доступ к итогам" in JS.read_text(encoding="utf-8")
    assert "Календарь и рабочая область" in JS.read_text(encoding="utf-8")
    assert "Что увидит получатель" in source
    assert "Открыть итоги" in (
        REPO_ROOT
        / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/share_invitation_content.html"
    ).read_text(encoding="utf-8")
    assert "Открыть запись" in (
        REPO_ROOT
        / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/share_invitation_content.html"
    ).read_text(encoding="utf-8")
    assert "Расшифровка и итоги" in (
        REPO_ROOT
        / "apps/server/src/twobrain_rec_server/cabinet/rendering.py"
    ).read_text(encoding="utf-8")
    assert "Отозвать" in source
    assert "data-share-recipient-results" in source
    assert "data-share-recipient-confirmation" in source
    assert "data-share-revoke-url" in source
    assert "data-share-rotate-url" in source
    assert "data-share-capability-state" in source
    assert "Матрица ролей" not in source
    assert "can_download" not in source
    assert "can_export" not in source


def test_share_focus_and_isolated_styles_are_registered() -> None:
    javascript = JS.read_text(encoding="utf-8")
    assert "initShareDialogs" in javascript
    assert "dialog.showModal()" in javascript
    assert 'event.key !== "Tab"' in javascript
    assert "content_scope: \"summary_only\"" in javascript
    assert "content_scope: \"full_meeting\"" in javascript
    assert "can_download: true" in javascript
    assert "can_export: true" in javascript
    assert "data-share-revoke-url" in javascript
    assert "renderExternalInvitationConfirmation" in javascript
    assert "setConfirmationVisible" in javascript
    assert "Отправить приглашение" in javascript
    assert "shareRequestErrorMessage" in javascript
    assert "Повторить" in javascript
    assert ".share-dialog" in CSS.read_text(encoding="utf-8")
