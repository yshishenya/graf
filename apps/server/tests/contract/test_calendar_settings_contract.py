from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.calendar_settings import (
    calendar_settings_calendar,
    calendar_settings_snapshot,
    calendar_settings_source,
)
from twobrain_rec_server.api.schemas import (
    ConnectCalendarSourceRequest,
    MeetingFilterState,
    MeetingListResponse,
    SelectCalendarsRequest,
)
from twobrain_rec_server.cabinet.rendering import (
    render_calendar_settings_fragment,
    render_meeting_list_page,
)
from twobrain_rec_server.cabinet.view_models import CALENDAR_PROVIDER_UI, calendar_settings_surface

REQUIRED_PROVIDER_LABELS = {
    "Яндекс Календарь",
    "Mail.ru Календарь",
    "Exchange / Exchange Server / EWS",
    "Bitrix24",
    "VK WorkSpace / свой CalDAV",
    "Mailion / MyOffice",
    "R7-Office",
    "CommuniGate Pro",
    "RuPost",
    "Nextcloud / SOGo через CalDAV",
    "Другой CalDAV",
}
REPO_ROOT = Path(__file__).resolve().parents[4]
CALENDAR_CSS = REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"


def test_select_calendars_request_allows_empty_selection_and_forbids_extra_fields() -> None:
    request = SelectCalendarsRequest.model_validate({"selected_provider_calendar_ids": []})

    assert request.selected_provider_calendar_ids == []
    with pytest.raises(ValidationError):
        SelectCalendarsRequest.model_validate(
            {
                "selected_provider_calendar_ids": [],
                "credential_input": "secret-should-not-be-accepted-here",
            }
        )


def test_connect_calendar_source_request_rejects_unsupported_oauth_mode() -> None:
    with pytest.raises(ValidationError):
        ConnectCalendarSourceRequest.model_validate(
            {
                "provider_family": "caldav_yandex",
                "auth_mode": "oauth",
                "credential_input": "secret-should-not-be-accepted-here",
            }
        )


def test_calendar_source_contract_rejects_provider_auth_mode_mismatch_without_echoing_secret(
    client,
) -> None:
    response = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "manual_url",
            "display_label": "Synthetic calendar",
            "caldav_url": "https://calendar.example.test/dav/user/",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "unsupported_calendar_auth_mode"
    assert "synthetic-secret" not in response.text


def test_calendar_source_contract_accepts_zero_selected_after_connect_and_empty_save(
    client,
) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "display_label": "Synthetic calendar",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": [],
        },
    )

    assert created.status_code == 201
    source_id = created.json()["source"]["source_id"]
    assert created.json()["source"]["selected_calendar_count"] == 0
    assert {calendar["calendar_id"] for calendar in created.json()["calendars"]} >= {
        "primary",
        "secondary",
    }
    assert "synthetic-secret" not in str(created.json())

    empty_saved = client.patch(
        f"/api/v1/calendar/sources/{source_id}/selected-calendars",
        headers=auth_headers(),
        json={"selected_provider_calendar_ids": []},
    )

    assert empty_saved.status_code == 200
    assert empty_saved.json()["source"]["selected_calendar_count"] == 0
    assert empty_saved.json()["source"]["connection_state"] == "active"


def test_calendar_settings_provider_labels_cover_required_user_facing_list() -> None:
    labels = {preset[0] for preset in CALENDAR_PROVIDER_UI.values()}

    assert labels >= REQUIRED_PROVIDER_LABELS


def test_calendar_settings_web_route_renders_working_settings_screen(client) -> None:
    response = client.get("/settings/integrations/calendar", headers=auth_headers())

    assert response.status_code == 200
    html = response.text
    assert 'data-active-nav="settings"' in html
    assert html.count('id="cabinet-sidebar" data-cabinet-navigation') == 1
    assert html.count('aria-label="Навигация кабинета"') == 1
    assert html.count('aria-current="page"') == 1
    assert "Настройки" in html
    assert "Календари" in html
    assert (
        '<a class="button primary" href="#calendar-providers-title">Выбрать провайдера</a>' in html
    )
    assert '<a class="button quiet" href="#calendar-providers-title">Добавить</a>' not in html
    assert '<button class="primary" type="button">Подключить первый календарь</button>' not in html
    assert "Что GRAF делает с календарем" in html
    assert "GRAF не меняет события календаря" in html
    assert "2brain Rec" not in html
    assert "Раздел появится в следующих версиях" not in html
    assert_no_forbidden_calendar_settings_content(html)


def test_calendar_settings_boundary_rendering_explains_privacy_and_recording_limits(client) -> None:
    response = client.get("/settings/integrations/calendar", headers=auth_headers())

    assert response.status_code == 200
    html = response.text
    assert "Только чтение" in html
    assert "Пароли не живут на Mac" in html
    assert "Приложение на Mac их не хранит" in html
    assert "Участники встречи не становятся получателями саммари" in html
    assert "не включает автоматическую запись" in html
    assert "скрытую или автоматическую запись" in html
    assert_no_forbidden_calendar_settings_content(html)


def test_calendar_settings_connection_flow_uses_progressive_disclosure(client) -> None:
    response = client.get("/settings/integrations/calendar", headers=auth_headers())
    css = CALENDAR_CSS.read_text()

    assert response.status_code == 200
    html = response.text
    assert '<section class="calendar-boundary"' not in html
    assert 'class="calendar-provider-button calendar-provider-button--unavailable"' in html
    assert 'class="calendar-provider-logo"' in html
    assert 'class="calendar-provider-buttons"' in html
    assert 'class="calendar-provider-dialog"' not in html
    assert "data-calendar-provider-open" not in html
    assert "data-calendar-provider-dialog" not in html
    assert 'aria-haspopup="dialog"' not in html
    assert "Доступные подключения работают только на чтение" in html
    assert "Яндекс Календарь" in html
    assert "Mail.ru Календарь" in html
    assert 'data-calendar-mutation="connect"' not in html
    assert "data-calendar-mutation-status" not in html
    assert "Google Calendar" in html
    assert "Скоро" in html
    assert "Подключение появится после полной проверки." in html
    assert 'class="calendar-connect-details"' not in html
    assert 'class="calendar-provider-list"' not in html
    assert 'class="calendar-provider-grid"' not in html
    assert "calendar-provider-grid" not in css
    assert "calendar-connect-details" not in css
    assert "calendar-provider-row" not in css
    assert "calendar-provider-cta" not in css
    assert 'class="calendar-advanced-fields"' not in html
    assert "https://calendar.example/caldav…" not in html
    assert html.index('id="calendar-sources-title"') < html.index('id="calendar-providers-title"')
    assert html.index('id="calendar-providers-title"') < html.index('id="calendar-boundary-title"')
    assert_no_forbidden_calendar_settings_content(html)


def test_meeting_home_renders_authoritative_calendar_upcoming_projection() -> None:
    source = calendar_settings_source(
        sync_state="synced",
        last_successful_sync_at=datetime(2026, 8, 20, tzinfo=UTC),
    )
    calendar = calendar_settings_calendar(source=source, selected=True)
    snapshot = calendar_settings_snapshot(
        source=source,
        calendar=calendar,
        starts_at=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
        open_meeting_available=True,
    )
    surface = calendar_settings_surface(
        provider_payloads=[],
        sources=[source],
        calendars_by_source={source.id: [calendar]},
        preview_events=[snapshot],
        now=datetime(2026, 8, 20, tzinfo=UTC),
    )
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="started_desc"),
            generated_at=datetime(2026, 8, 20, tzinfo=UTC),
        ),
        calendar_surface=surface,
        display_timezone="Europe/Moscow",
    )

    assert 'aria-label="Ближайшие встречи"' in page
    assert "Из выбранных календарей" in page
    assert snapshot.title in page
    assert f"/api/v1/calendar/events/{snapshot.id}/open" in page
    assert ">Подключиться</a>" in page
    assert "synthetic-envelope" not in page
    assert "/settings/integrations/calendar" in page


def test_meeting_home_names_credential_recovery_without_false_freshness() -> None:
    source = calendar_settings_source(sync_state="credential_failed")
    source.last_safe_error_code = "invalid_credentials"
    calendar = calendar_settings_calendar(source=source, selected=True)
    snapshot = calendar_settings_snapshot(
        source=source,
        calendar=calendar,
        starts_at=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
        open_meeting_available=True,
    )
    surface = calendar_settings_surface(
        provider_payloads=[],
        sources=[source],
        calendars_by_source={source.id: [calendar]},
        preview_events=[snapshot],
        now=datetime(2026, 8, 20, tzinfo=UTC),
    )
    page = render_meeting_list_page(
        MeetingListResponse(
            items=[],
            filters=MeetingFilterState(q=None, status=None, access=None, sort="started_desc"),
            generated_at=datetime(2026, 8, 20, tzinfo=UTC),
        ),
        calendar_surface=surface,
    )

    assert "Нужно переподключить календарь" in page
    assert "Календарь нужно переподключить" in page
    assert "Ручная запись по-прежнему доступна" in page
    assert "Календарь обновляется" not in page
    assert snapshot.title not in page
    assert f"/api/v1/calendar/events/{snapshot.id}/open" not in page


def test_calendar_settings_disconnect_confirmation_copy_is_truthful_and_safe() -> None:
    source = calendar_settings_source(connection_state="active", sync_state="synced")
    calendar = calendar_settings_calendar(source, selected=True)
    surface = calendar_settings_surface(
        provider_payloads=[],
        sources=[source],
        calendars_by_source={source.id: [calendar]},
    )

    html = render_calendar_settings_fragment(surface)

    assert "Отключить календарь?" in html
    assert ">Отключить</button>" in html
    assert '<dialog class="calendar-provider-dialog calendar-disconnect-dialog"' in html
    assert 'aria-haspopup="dialog"' in html
    assert "Новые встречи перестанут появляться в GRAF" in html
    assert "Уже созданные встречи останутся" in html
    assert "удалены или отозваны" not in html
    assert "отозвать доступ" not in html.lower()
    assert "удалит события у провайдера" not in html
    assert_no_forbidden_calendar_settings_content(html)


def test_calendar_reconnect_action_requires_matching_available_provider_dialog() -> None:
    source = calendar_settings_source(sync_state="credential_failed")
    unavailable_surface = calendar_settings_surface(
        provider_payloads=[
            {
                "provider_family": source.provider_family,
                "runtime_available": False,
            }
        ],
        sources=[source],
    )
    available_surface = calendar_settings_surface(
        provider_payloads=[
            {
                "provider_family": source.provider_family,
                "runtime_available": True,
            }
        ],
        sources=[source],
    )

    unavailable_html = render_calendar_settings_fragment(unavailable_surface)
    available_html = render_calendar_settings_fragment(available_surface)
    dialog_id = f"calendar-provider-dialog-{source.provider_family}"

    assert "Переподключить" not in unavailable_html
    assert f'id="{dialog_id}"' not in unavailable_html
    assert "Переподключить" in available_html
    assert f'aria-controls="{dialog_id}"' in available_html
    assert f'id="{dialog_id}"' in available_html


def test_calendar_dialog_escape_closes_and_restores_focus() -> None:
    script = (
        REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    ).read_text()
    calendar_dialog_source = script[
        script.index("const dialogOpeners = new WeakMap()") : script.index(
            "const initSettingsFormState"
        )
    ]

    assert 'dialog.addEventListener("cancel"' in calendar_dialog_source
    assert 'dialog.addEventListener("keydown"' in calendar_dialog_source
    assert 'event.key !== "Escape"' in calendar_dialog_source
    assert "event.preventDefault()" in calendar_dialog_source
    assert "closeCalendarDialog(dialog)" in calendar_dialog_source


def test_calendar_selection_limit_message_has_priority_over_dirty_state() -> None:
    script = (
        REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    ).read_text()

    assert 'form.addEventListener("keyup", (event) =>' in script
    assert '(event.key !== " " && event.key !== "Spacebar")' in script
    assert "selectedCalendarCount() !== selectionLimit" in script
    assert 'status.dataset.preserveMessage = "true"' in script
    assert "delete status.dataset.preserveMessage" in script
    assert 'status.dataset.preserveMessage !== "true"' in script


def test_calendar_settings_accessibility_contract_for_states_and_controls(client) -> None:
    response = client.get("/settings/integrations/calendar", headers=auth_headers())
    css = CALENDAR_CSS.read_text()

    assert response.status_code == 200
    html = response.text
    assert 'id="calendar-settings-region"' in html
    assert 'id="calendar-providers-title" tabindex="-1"' in html
    assert 'aria-labelledby="calendar-boundary-title"' in html
    assert 'aria-labelledby="calendar-sources-title"' in html
    assert 'aria-labelledby="calendar-providers-title"' in html
    assert 'aria-label="Закрыть окно подключения"' not in html
    status_nodes = re.findall(r"<[^>]*role=\"status\"[^>]*>", html)
    assert status_nodes
    assert all('aria-live="polite"' in node for node in status_nodes)
    assert 'aria-haspopup="dialog"' not in html
    assert 'role="dialog" aria-modal="true"' not in html
    assert 'data-calendar-has-result="false"' in html
    assert 'aria-live="polite"' in html
    assert 'role="status"' in html
    assert 'name="join_prompt_enabled"' in html
    assert 'name="record_prompt_enabled"' in html
    assert html.count('role="switch"') == 4
    assert 'aria-describedby="calendar-join-prompt-help"' in html
    assert 'id="calendar-join-prompt-help" role="tooltip"' in html
    calendar_template = (
        REPO_ROOT
        / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html"
    ).read_text()
    assert 'type="checkbox" name="selected_provider_calendar_ids"' in calendar_template
    for preference in (
        "include_events_without_participants",
        "include_events_without_link_or_location",
        "include_all_day_events",
        "include_private_free_busy_prompt_candidates",
    ):
        assert f'ui.checkbox("{preference}"' in calendar_template
    assert 'name="credential_input"' not in html
    assert "data-settings-form-disable-pristine" in html
    assert "data-settings-form-reset" in html
    assert "Отменить изменения" in html
    assert "Если настройка ограничена политикой организации" in html
    assert "Во время загрузки настроек ручная запись остается доступной" in html
    assert "Если настройки календарей временно недоступны" in html
    assert "Приватные события и события только со статусом занятости" in html
    assert "onclick=" not in html
    assert "onkeydown=" not in html
    assert "summary:focus-visible" in css
    assert "prefers-reduced-motion: reduce" in css
    assert_no_forbidden_calendar_settings_content(html)


def test_calendar_settings_provider_return_states_render_safe_messages(client) -> None:
    response = client.get(
        "/settings/integrations/calendar?connect_result=denied&policy_limited=admin_required&token=secret",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    html = response.text
    assert "Календарь не подключен" in html
    assert "Провайдер не дал доступ только для чтения" in html
    assert "Ограничено политикой организации" in html
    assert (
        "Некоторые способы подключения или календари может включить только администратор организации"
        in html
    )
    assert "admin_required" not in html
    assert "secret" not in html
    assert_no_forbidden_calendar_settings_content(html)


def test_calendar_settings_overlap_conflict_renders_explicit_choice() -> None:
    first_source = calendar_settings_source(provider_family="caldav_yandex")
    first_calendar = calendar_settings_calendar(first_source, selected=True)
    second_source = calendar_settings_source(
        provider_family="caldav_mail_ru",
        provider_label="Mail.ru Календарь",
    )
    second_calendar = calendar_settings_calendar(second_source, selected=True)
    first = calendar_settings_snapshot(
        first_source,
        first_calendar,
        provider_event_id="event-1200-1300",
        starts_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        ends_at=datetime(2026, 7, 1, 13, 0, tzinfo=UTC),
    )
    second = calendar_settings_snapshot(
        second_source,
        second_calendar,
        provider_event_id="event-1230-1330",
        starts_at=datetime(2026, 7, 1, 12, 30, tzinfo=UTC),
        ends_at=datetime(2026, 7, 1, 13, 30, tzinfo=UTC),
    )
    surface = calendar_settings_surface(
        provider_payloads=[],
        sources=[],
        preview_events=[first, second],
        now=datetime(2026, 7, 1, 12, 45, tzinfo=UTC),
    )

    html = render_calendar_settings_fragment(surface)

    assert "Нужно выбрать событие для пересечения" in html
    assert "data-calendar-local-time" in html
    assert "12:30 - 13:00 UTC" not in html
    assert "GRAF не выбирает событие автоматически" in html
    assert "Можно продолжить без календарного контекста" in html
    assert "Вариант:" in html
    assert '<button type="button" class="quiet">Выбрать:' not in html
    assert (
        '<button type="button" class="quiet">Продолжить без календарного контекста</button>'
        not in html
    )
    assert_no_forbidden_calendar_settings_content(html)


def test_calendar_settings_embedded_route_reuses_settings_screen_inside_desktop_cabinet(
    client,
) -> None:
    response = client.get("/desktop/settings/integrations/calendar", headers=auth_headers())

    assert response.status_code == 200
    html = response.text
    assert "desktop-embedded" in html
    assert 'data-active-nav="settings"' in html
    assert html.count('id="cabinet-sidebar" data-cabinet-navigation') == 1
    assert html.count('aria-current="page"') == 1
    assert "/desktop/settings/integrations/calendar" in html
    assert 'role="group" aria-labelledby="calendar-providers-title"' in html
    assert "Ручной старт и стоп записи остаются доступны всегда" in html
    assert_no_forbidden_calendar_settings_content(html)


def test_calendar_settings_hx_route_returns_fragment_without_shell(client) -> None:
    response = client.get(
        "/settings/integrations/calendar",
        headers=auth_headers() | {"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert 'data-cabinet-fragment="calendar-settings"' in response.text
    assert "app-shell" not in response.text
    assert "data-cabinet-shell" not in response.text
    assert "data-cabinet-navigation" not in response.text
    assert "cabinet-sidebar" not in response.text
    assert "cabinet-rail-toggle" not in response.text


def test_calendar_settings_html_lists_all_required_providers(client) -> None:
    response = client.get("/settings/integrations/calendar", headers=auth_headers())

    assert response.status_code == 200
    for label in REQUIRED_PROVIDER_LABELS:
        assert label in response.text
    assert "Скоро" in response.text
    assert "Подключение появится после полной проверки." in response.text
    assert "Подключить по паролю приложения" not in response.text
    assert "Подключить CalDAV" not in response.text
    assert "Показать условия подключения" not in response.text
    assert "Неподдерживаемые сервисы отмечены честно" in response.text
    assert "Яндекс Календарь" in response.text
    assert "Mail.ru Календарь" in response.text
    assert 'class="calendar-provider-dialog"' not in response.text
    assert "data-calendar-provider-open" not in response.text
    assert "data-calendar-provider-close" not in response.text
    assert 'name="credential_input"' not in response.text
    assert 'name="caldav_url"' not in response.text
    assert "secret-app-password" not in response.text


def assert_no_forbidden_calendar_settings_content(html: str) -> None:
    forbidden = [
        "secret-should-not-be-accepted-here",
        "raw_token",
        "access_token",
        "refresh_token",
        "Bearer ",
        "sk-",
        "attendee@example",
        "organizer@example",
        "passcode=",
        "signed_url",
        "presigned",
        "/Users/",
    ]
    for value in forbidden:
        assert value not in html
