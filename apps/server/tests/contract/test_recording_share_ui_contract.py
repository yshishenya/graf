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
    assert "Пригласить" in source
    assert "Что увидят: только итоги" in source
    assert "Отозвать" in source
    assert "data-share-recipient-results" in source
    assert "data-share-revoke-url" in source
    assert "Матрица ролей" not in source
    assert "can_download" not in source
    assert "can_export" not in source


def test_share_focus_and_isolated_styles_are_registered() -> None:
    javascript = JS.read_text(encoding="utf-8")
    assert "initShareDialogs" in javascript
    assert "dialog.showModal()" in javascript
    assert 'event.key !== "Tab"' in javascript
    assert "content_scope: \"summary_only\"" in javascript
    assert "data-share-revoke-url" in javascript
    assert ".share-dialog" in CSS.read_text(encoding="utf-8")
