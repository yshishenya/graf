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
    invitation_page = (
        REPO_ROOT
        / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/share_invitation_content.html"
    ).read_text(encoding="utf-8")
    assert "data-share-invitation-auto-accept-form" in invitation_page
    assert "Открываем запись" in invitation_page
    assert "Открываем итоги" in invitation_page
    assert "Приглашение недоступно" in invitation_page
    assert "Ссылка уже использована, отозвана или срок ее действия истек." in invitation_page
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


def test_share_capability_block_switches_copy_by_state() -> None:
    from types import SimpleNamespace

    from twobrain_rec_server.cabinet.templates import render_template

    def render(capability_state: str, capability_reason: str | None, can_manage_roles: bool) -> str:
        return render_template(
            "cabinet/fragments/meeting_share.html",
            meeting_id="meeting-1",
            share=SimpleNamespace(
                capability_state=capability_state,
                capability_reason=capability_reason,
                can_manage_roles=can_manage_roles,
                external_invitation_state="available",
                active_grants=[],
                active_invitations=[],
            ),
            share_workspace_id=None,
        )

    available = render("available", None, True)
    assert "Внешний доступ: запись · просмотр" in available
    assert (
        "Итоги, расшифровка, прослушивание и скачивание аудио. Доступ можно отозвать в любой момент."
        in available
    )
    assert "Внешний доступ недоступен" not in available

    unavailable = render(
        "auth_required",
        "Для управления доступом войдите в аккаунт с правом владельца.",
        False,
    )
    assert "Внешний доступ недоступен" in unavailable
    assert "Для управления доступом войдите в аккаунт с правом владельца." in unavailable
    assert "Внешний доступ: запись · просмотр" not in unavailable
    assert (
        "Итоги, расшифровка, прослушивание и скачивание аудио. Доступ можно отозвать в любой момент."
        not in unavailable
    )


def test_share_focus_and_isolated_styles_are_registered() -> None:
    javascript = JS.read_text(encoding="utf-8")
    assert "initShareDialogs" in javascript
    assert "dialog.showModal()" in javascript
    assert 'event.key !== "Tab"' in javascript
    assert 'content_scope: collaborationRole ? "full_meeting" : "summary_only"' in javascript
    assert 'role === "commenter" || role === "editor"' in javascript
    assert 'can_edit: role === "editor"' in javascript
    assert "content_scope: \"full_meeting\"" in javascript
    assert "can_download: true" in javascript
    assert "can_export: true" in javascript
    assert "data-share-revoke-url" in javascript
    assert "renderExternalInvitationConfirmation" in javascript
    assert "setConfirmationVisible" in javascript
    assert "Отправить приглашение" in javascript
    assert "shareRequestErrorMessage" in javascript
    assert "Повторить" in javascript
    assert "initShareInvitationAutoAccept" in javascript
    assert "form.requestSubmit()" in javascript
    assert ".share-dialog" in CSS.read_text(encoding="utf-8")
