"""F268 US7: история уведомлений живет в общей оболочке кабинета.

Тесты проверяют синтетический рендер шаблона и реальный маршрут: тема,
навигация, карточки уведомлений и отсутствие старой «голой» страницы.
"""

from __future__ import annotations

from uuid import uuid4

from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID, tenant_scope
from tests.integration.test_web_owner_session_context import (
    OWNER_REVIEW_TEST_TOKEN,
    _seed_owner_review_session,
)
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.cabinet.rendering_shared import _page_shell
from twobrain_rec_server.cabinet.view_models import AccountProfileView
from twobrain_rec_server.db.models import Meeting, UserIdentity
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.notifications.inbox import record_event

MEETING_ID = "00000000-0000-0000-0000-000000000011"
NOTICE_ID = "00000000-0000-0000-0000-000000000010"


def _synthetic_item(**overrides) -> dict[str, object]:
    item: dict[str, object] = {
        "id": NOTICE_ID,
        "revision": 2,
        "title": "Не удалось обработать встречу",
        "body": "Расшифровка не завершилась.",
        "meeting_title": "Синтетическая встреча",
        "href": f"/meetings/{MEETING_ID}",
        "requires_action": True,
        "unseen": True,
        "personal": False,
        "created_at": "2026-09-01T10:00:00+00:00",
        "updated_at": "2026-09-01T10:05:00+00:00",
        "resolved": False,
    }
    item.update(overrides)
    return item


def _render_history(*, embedded: bool, filter: str, items: list[dict[str, object]], next_cursor: str | None = None) -> str:
    return _page_shell(
        "Уведомления",
        embedded=embedded,
        content_template="cabinet/pages/notification_history.html",
        csrf_token="synthetic-notification-csrf",
        profile=AccountProfileView(
            display_name="Synthetic Owner",
            primary_email="owner@example.test",
            theme="dark",
        ),
        filter=filter,
        items=items,
        next_cursor=next_cursor,
    )


def test_notification_history_renders_inside_shared_shell_with_theme_and_cards() -> None:
    page = _render_history(embedded=False, filter="important", items=[_synthetic_item()], next_cursor="synthetic-cursor")

    assert page.count("data-cabinet-shell") == 1
    assert 'data-theme="dark"' in page
    assert '<a class="skip-link" href="#cabinet-main">К содержимому</a>' in page
    assert 'aria-label="Навигация кабинета"' in page
    assert "<h1>Уведомления</h1>" in page
    assert 'class="page-title"' in page
    assert "<body><main class=\"notification-history\"" not in page
    assert '<main class="notification-history"' not in page

    assert '<a class="button quiet" href="?filter=important" aria-current="page">Важное</a>' in page
    assert '<a class="button quiet" href="?filter=history">История</a>' in page

    assert 'class="notification-card cabinet-card"' in page
    assert "<h2 class=\"notification-card__title\">Не удалось обработать встречу</h2>" in page
    assert "Синтетическая встреча" in page
    assert "data-user-datetime" in page
    assert f'action="/api/v1/notifications/{NOTICE_ID}/read"' in page
    assert 'name="csrf_token" value="synthetic-notification-csrf"' in page
    assert 'name="revision" value="2"' in page
    assert ">Просмотрено</button>" in page
    assert 'href="?filter=important&amp;cursor=synthetic-cursor"' in page
    assert "Показать еще" in page
    assert 'href="/meetings"' in page
    assert 'href="/settings/notifications"' in page


def test_notification_history_embedded_uses_desktop_links_and_history_state() -> None:
    page = _render_history(
        embedded=True,
        filter="history",
        items=[_synthetic_item(requires_action=False, unseen=False, resolved=True, personal=True)],
    )

    assert 'class="app-shell desktop-embedded"' in page
    assert f'href="/desktop/meetings/{MEETING_ID}"' in page
    assert 'href="/desktop/settings/notifications"' in page
    assert '<a class="button quiet" href="?filter=history" aria-current="page">История</a>' in page
    assert "Проблема решена" in page
    assert "Лично вам" in page
    assert ">Просмотрено</button>" not in page


def test_notification_history_empty_states_use_shared_empty_state() -> None:
    important = _render_history(embedded=False, filter="important", items=[])
    history = _render_history(embedded=False, filter="history", items=[])

    assert 'class="empty-state"' in important
    assert "Сейчас ничего не требует вашего действия" in important
    assert "Здесь появятся готовые результаты и встречи, которыми с вами поделились." in history


def test_notification_history_route_uses_shell_for_browser_and_embedded(client) -> None:
    async def seed() -> None:
        await _seed_owner_review_session(client)
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_scope(db, tenant_scope())
            user = await db.get(UserIdentity, USER_ID)
            assert user is not None
            user.theme = "dark"
            meeting = Meeting(
                id=uuid4(),
                workspace_id=WORKSPACE_ID,
                created_by_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id=str(uuid4()),
                title="Синтетическая встреча",
                duration_seconds=30,
                deletion_state="none",
            )
            db.add(meeting)
            await db.flush()
            await record_event(db, meeting=meeting, kind="processing_failed", source_revision="first")
            await db.commit()

    client.portal.call(seed)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)

    page = client.get("/notifications")
    assert page.status_code == 200
    for marker in (
        "data-cabinet-shell",
        'data-theme="dark"',
        'class="page-title"',
        "notification-card",
        ">Просмотрено</button>",
        'aria-current="page"',
    ):
        assert marker in page.text, marker
    assert '<main class="notification-history"' not in page.text
    assert 'href="/settings/notifications"' in page.text

    embedded = client.get("/desktop/notifications")
    assert embedded.status_code == 200
    assert 'class="app-shell desktop-embedded"' in embedded.text
    assert "/desktop/meetings/" in embedded.text
    assert 'href="/desktop/settings/notifications"' in embedded.text
