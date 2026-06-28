from __future__ import annotations

import asyncio
from urllib.parse import parse_qs, urlparse

from tests.contract.test_admin_no_secret_content_egress import FORBIDDEN_MARKERS
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.admin import (
    DEFAULT_ADMIN_DEVICE_ID,
    DEFAULT_ADMIN_USER_ID,
    DEFAULT_MEMBER_DEVICE_ID,
    DEFAULT_MEMBER_USER_ID,
    auth_headers_for,
    seed_default_workspace_admin_roles,
)
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import set_artifact_policy


def test_admin_overview_page_renders_russian_shell_without_forbidden_markers(client) -> None:
    response = client.get("/admin", headers=auth_headers())

    assert response.status_code == 200
    assert "<title>Администрирование · GRAF</title>" in response.text
    assert 'href="/static/cabinet/favicon.ico"' in response.text
    assert 'href="/static/cabinet/graf-logo.svg"' in response.text
    assert '<p class="admin-kicker">GRAF</p>' in response.text
    assert "/static/cabinet/cabinet.css" in response.text
    assert "/static/admin/graf-cyrillic-mic-inverted.png" in response.text
    assert 'alt="ГРАФ"' in response.text
    assert "app-shell admin-app-shell" in response.text
    assert "sidebar admin-sidebar" in response.text
    assert "2brain Rec" not in response.text
    assert "Администрирование" in response.text
    assert "Пользователи" in response.text
    assert "Баланс" in response.text
    assert "Метрики" in response.text
    assert "Аудит" in response.text
    assert "Поддержка" not in response.text
    assert "Analyst" not in response.text
    for marker in FORBIDDEN_MARKERS:
        assert marker not in response.text

    logo = client.get("/static/admin/graf-cyrillic-mic-inverted.png")
    assert logo.status_code == 200
    assert logo.headers["content-type"].startswith("image/png")


def test_admin_browser_without_session_redirects_to_login(client) -> None:
    response = client.get("/admin?tab=users", follow_redirects=False)

    assert response.status_code == 303
    location = urlparse(response.headers["location"])
    query = parse_qs(location.query)
    assert location.path == "/login"
    assert query["next"] == ["/admin?tab=users"]
    assert query["error"][0] in {"missing_auth_context", "legacy_header_auth_disabled"}


def test_admin_overview_page_denies_member_without_counts(client) -> None:
    asyncio.run(_seed_roles(client))

    response = client.get(
        "/admin",
        headers=auth_headers_for(
            user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID
        ),
    )

    assert response.status_code == 403
    assert "Нет доступа" in response.text
    assert "Активные пользователи" not in response.text


async def _seed_roles(client) -> None:
    async with client.app_state["sessionmaker"]() as db:
        await seed_default_workspace_admin_roles(db)


def test_admin_browser_pages_keep_russian_navigation_and_compact_keyboard_css(client) -> None:
    pages = [
        "/admin",
        "/admin/users",
        "/admin/files",
        "/admin/balance",
        "/admin/metrics",
        "/admin/audit",
    ]

    for path in pages:
        response = client.get(path, headers=auth_headers())
        assert response.status_code == 200
        assert "Пользователи" in response.text
        assert "Файлы" in response.text
        assert "Баланс" in response.text
        assert "Метрики" in response.text
        assert "Аудит" in response.text
        assert "Поддержка" not in response.text
        assert "Биллинг" not in response.text
        assert "Analyst" not in response.text
        assert "Delete this meeting everywhere" not in response.text

    css = client.get("/static/admin/admin.css")
    assert css.status_code == 200
    assert ":focus-visible" in css.text
    assert "@media (max-width: 720px)" in css.text
    assert "overflow-x: auto" in css.text


def test_admin_users_page_exposes_invitation_filters_and_management_forms(client) -> None:
    asyncio.run(_seed_roles(client))

    response = client.get("/admin/users", headers=auth_headers())
    admin_response = client.get(
        "/admin/users",
        headers=auth_headers_for(user_id=DEFAULT_ADMIN_USER_ID, device_id=DEFAULT_ADMIN_DEVICE_ID),
    )

    assert response.status_code == 200
    assert admin_response.status_code == 200
    assert 'name="search"' in response.text
    assert 'name="role"' in response.text
    assert 'name="status"' in response.text
    assert 'name="invitation_status"' in response.text
    assert 'method="post" action="/admin/invitations"' in response.text
    assert 'name="target_contact"' in response.text
    assert 'name="invited_role"' in response.text
    admin_invite_select = admin_response.text.split('name="invited_role"', 1)[1].split(
        "</select>", 1
    )[0]
    assert '<option value="admin">admin</option>' not in admin_invite_select
    assert '<option value="owner">owner</option>' not in admin_invite_select


def test_admin_files_pages_expose_filters_and_safe_file_actions(client) -> None:
    asyncio.run(_seed_roles(client))
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(
        client,
        seeds.ready_id,
        audio_download="allowed",
        transcript_download="allowed",
        package_export="allowed",
    )

    files = client.get("/admin/files", headers=auth_headers())
    detail = client.get(f"/admin/files/{seeds.ready_id}", headers=auth_headers())

    assert files.status_code == 200
    for name in (
        "search",
        "owner_user_id",
        "type",
        "date_from",
        "date_to",
        "processing_state",
        "deletion_state",
        "min_size",
        "min_duration",
    ):
        assert f'name="{name}"' in files.text
    assert detail.status_code == 200
    assert f'action="/admin/files/{seeds.ready_id}/review-access"' in detail.text
    assert f"/api/v1/admin/files/{seeds.ready_id}/downloads/audio" in detail.text
    assert f'action="/admin/files/{seeds.ready_id}/exports"' in detail.text
    assert f'action="/admin/files/{seeds.ready_id}/deletion-requests"' in detail.text
    assert "Удаление касается только данных, которыми управляет GRAF." in detail.text
    assert "Подтверждаю удаление в границах GRAF" in detail.text
    assert "2brain Rec" not in detail.text
    assert 'value="retention_expired"' in detail.text
    assert 'value="policy_blocked"' in detail.text
    assert 'value="retention_policy"' not in detail.text
    assert 'value="privacy_request"' not in detail.text
    assert "Delete this meeting everywhere" not in detail.text
