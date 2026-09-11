import re
from datetime import UTC, datetime

from twobrain_rec_server.admin.templates import render_template
from twobrain_rec_server.admin.view_models import build_user_detail_view, build_users_view
from twobrain_rec_server.cabinet.rendering import render_settings_page
from twobrain_rec_server.cabinet.view_models import (
    CALENDAR_BOUNDARY_ITEMS,
    AccountProfileView,
    AccountSettingsSurface,
)


def test_account_locale_is_preserved_without_claiming_ui_translation() -> None:
    profile = AccountProfileView(display_name="Synthetic", locale="en-US")
    page = render_settings_page(
        category="account", profile=profile, account_surface=AccountSettingsSurface(profile=profile)
    )
    locale = re.search(r'<input type="hidden" id="account-locale"[^>]*>', page)
    assert locale is not None
    assert 'name="locale" value="en-US"' in locale.group(0)
    assert '<select id="account-locale"' not in page
    assert '<span>Русский</span>' in page
    help_text = re.search(r'id="account-locale-help">(.*?)</span>', page, re.S).group(1)
    assert "Другие языки пока недоступны" in help_text
    summaries = render_settings_page(category="summaries")
    assert "Личные форматы доступны только вам в этом пространстве" in summaries
    assert "во всех ваших встречах" not in summaries
    assert any(
        "Автозапись по приложениям настраивается отдельно" in text
        for _, text in CALENDAR_BOUNDARY_ITEMS
    )


def test_admin_translates_labels_but_submits_original_codes_and_keeps_role_guards() -> None:
    user = {
        "user_id": "synthetic",
        "display_name": "Synthetic",
        "role": "member",
        "status": "active",
        "files": {"server_known": 0},
        "usage": {"recording_minutes": 0, "storage_bytes": 0, "processing_jobs": 0},
        "devices": [{"device_public_id": "synthetic", "platform": "macos", "status": "revoked"}],
        "sessions": {
            "active": 0,
            "recent": [{"provider": "email", "status": "expired", "expires_at": datetime.now(UTC)}],
        },
        "recent_audit": [],
    }
    for actor in ("owner", "admin"):
        view = build_users_view(
            workspace_name="Synthetic",
            actor_role=actor,
            users={
                "members": [user],
                "invitations": [],
            },
            filters={"search": None, "role": None, "status": None, "invitation_status": None},
        )
        page = render_template("admin/users.html", view=view, page_title="Пользователи")
        role_select = re.search(r'<select name="invited_role">(.*?)</select>', page, re.S).group(1)
        roles = re.findall(r'<option value="([^"]+)">([^<]+)</option>', role_select)
        assert roles == (
            [("member", "Участник"), ("admin", "Администратор"), ("owner", "Владелец")]
            if actor == "owner"
            else [("member", "Участник")]
        )
        assert '<option value="active">Активен</option>' in page
        detail = render_template(
            "admin/user_detail.html",
            page_title="Пользователь",
            view=build_user_detail_view(
                workspace_name="Synthetic",
                actor_role=actor,
                user=user,
            ),
        )
        assert "Отозван" in detail and "Срок истёк" in detail
        assert '<option value="member">Участник</option>' in detail
        assert ('<option value="owner">Владелец</option>' in detail) == (actor == "owner")
    user["status"] = "future_state"
    page = render_template(
        "admin/user_detail.html",
        page_title="Пользователь",
        view=build_user_detail_view(
            workspace_name="Synthetic",
            actor_role="owner",
            user=user,
        ),
    )
    assert "future_state" in page
