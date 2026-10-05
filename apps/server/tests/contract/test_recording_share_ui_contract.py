from pathlib import Path
from types import SimpleNamespace

from twobrain_rec_server.cabinet.templates import render_template

REPO_ROOT = Path(__file__).resolve().parents[4]
STATIC = REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet"
TEMPLATES = REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet"


def test_share_fragment_is_summary_only_and_accessible() -> None:
    html = render_template(
        "cabinet/fragments/meeting_share.html", meeting_id="synthetic-meeting",
        share_workspace_id=None, share=SimpleNamespace(),
    )
    for text in ("Поделиться итогами", "По ссылке", "По почте", "Скопировать ссылку", "Отправить"):
        assert text in html
    assert 'aria-modal="true"' in html
    assert 'role="combobox"' in html
    assert 'role="listbox"' in html
    assert 'aria-controls="share-recipient-results-synthetic-meeting"' in html
    assert 'aria-live="polite"' in html
    assert "Любой со ссылкой сможет прочитать итоги" in html
    assert "Запись и расшифровка останутся закрыты" in html
    assert "can_download" not in html and "can_export" not in html
    assert "Редактирование" not in html and "Комментирование" not in html
    assert 'data-summary-link-action="revoke"' in html
    assert 'data-summary-link-action="rotate"' in html
    assert 'data-summary-share-result hidden' in html


def test_only_one_sharing_handler_owns_dialog() -> None:
    legacy = (STATIC / "cabinet.js").read_text()
    script = (STATIC / "summary-sharing.js").read_text()
    assert 'dialog.hasAttribute("data-summary-share-dialog")' in legacy
    assert "dialog.showModal()" in script and "opener?.focus" in script
    assert "navigator.clipboard.writeText" in script
    assert "data-summary-share-url" in script
    assert "idempotency_key:sendKey" in script
    assert "recipient.can_retry" in script
    assert "window.confirm" in script
    assert "full_meeting" not in script
    assert "summary-sharing.js" in (TEMPLATES / "base.html").read_text()


def test_reader_has_one_voluntary_own_meeting_action() -> None:
    source = (TEMPLATES / "pages/shared_meeting_summary_content.html").read_text()
    assert source.count(">Начать со своей встречи</a>") == 1
    assert "'/sign-up?next=%2Fmeetings'" in source
    assert "Получайте такие итоги своих встреч" in source
    assert "workspace_id" not in source


def test_no_javascript_form_reports_the_actual_delivery_result() -> None:
    from twobrain_rec_server.cabinet.rendering import render_summary_sharing_form

    for states, title in (
        (["accepted"], "Итоги отправлены"),
        (["accepted", "failed", "unknown"], "Отправлено не всем"),
        (["accepted", "unknown"], "Проверьте отправку"),
        (["pending", "unknown"], "Отправляем…"),
    ):
        batch = {
            "batch_id": "synthetic-batch",
            "counts": {state: states.count(state) for state in set(states)},
            "recipients": [{"email": "recipient@example.test", "state": state, "can_retry": state == "failed", "recipient_id": str(index)} for index, state in enumerate(states)],
            "can_cancel": "pending" in states,
        }
        html = render_summary_sharing_form(meeting_id="synthetic-meeting", csrf_token="synthetic-csrf", template_key="meeting_minutes", batch=batch)
        assert f"<h1>{title}</h1>" in html
        assert ">Готово</a>" in html
        assert ('value="retry"' in html) == ("failed" in states)
        assert ('value="cancel"' in html) == ("pending" in states)


def test_unavailable_public_reader_returns_a_human_page(client) -> None:
    response = client.get("/api/v1/cabinet/public-shares/synthetic-missing?workspace_id=20000000-0000-0000-0000-000000000001", headers={"Accept": "text/html"})
    assert response.status_code in (404, 503)
    assert "Итоги временно недоступны" in response.text if response.status_code == 503 else "Итоги недоступны" in response.text
    assert "application/problem+json" not in response.headers["content-type"]
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_temporary_reader_error_preserves_retry_header() -> None:
    from twobrain_rec_server.api.problems import ProblemDetail, _summary_unavailable_response

    response = _summary_unavailable_response(ProblemDetail(status=429, code="share_rate_limited", title="Limit", headers={"Retry-After": "60"}))
    assert response.headers["retry-after"] == "60"
    assert "Итоги временно недоступны" in response.body.decode()
    assert "Попросите отправителя" not in response.body.decode()


def test_no_javascript_forms_return_to_login_when_session_expires(client) -> None:
    from urllib.parse import parse_qs, urlsplit

    for path in ("/api/v1/cabinet/summary-sharing/preferences/form", "/api/v1/cabinet/meetings/20000000-0000-0000-0000-000000000001/summary-sharing/form"):
        response = client.get(path, headers={"Accept": "text/html"}, follow_redirects=False)
        assert response.status_code == 303
        location = urlsplit(response.headers["location"])
        assert location.path == "/login"
        assert parse_qs(location.query)["next"] == [path]
