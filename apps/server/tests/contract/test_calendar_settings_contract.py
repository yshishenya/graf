from __future__ import annotations

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
from twobrain_rec_server.api.schemas import ConnectCalendarSourceRequest, SelectCalendarsRequest
from twobrain_rec_server.cabinet.rendering import render_calendar_settings_fragment
from twobrain_rec_server.cabinet.view_models import CALENDAR_PROVIDER_UI, calendar_settings_surface

REQUIRED_PROVIDER_LABELS = {
    "Яндекс Календарь",
    "Mail.ru Календарь",
    "Exchange / Exchange Server / EWS",
    "Bitrix24",
    "VK WorkSpace / custom CalDAV",
    "Mailion / MyOffice",
    "R7-Office",
    "CommuniGate Pro",
    "RuPost",
    "Nextcloud / SOGo-like CalDAV",
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
    assert created.json()["calendars"] == []
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
    assert "Интеграции" in html
    assert "Календари" in html
    assert (
        '<a class="button primary" href="#calendar-providers-title">Выбрать провайдера</a>'
        in html
    )
    assert '<a class="button quiet" href="#calendar-providers-title">Добавить</a>' not in html
    assert '<button class="primary" type="button">Подключить первый календарь</button>' not in html
    assert "Что 2brain Rec делает с календарем" in html
    assert "2brain Rec не меняет события календаря" in html
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
    assert 'class="calendar-provider-button"' in html
    assert 'class="calendar-provider-logo"' in html
    assert 'class="calendar-provider-buttons"' in html
    assert 'class="calendar-provider-dialog"' in html
    assert "data-calendar-provider-open" in html
    assert "data-calendar-provider-dialog" in html
    assert 'aria-haspopup="dialog"' in html
    assert "Реквизиты вводятся в отдельном окне" in html
    assert "Подключить Яндекс Календарь" in html
    assert "Подключить Mail.ru Календарь" in html
    assert 'class="calendar-connect-details"' not in html
    assert 'class="calendar-provider-list"' not in html
    assert 'class="calendar-provider-grid"' not in html
    assert "calendar-provider-grid" not in css
    assert "calendar-connect-details" not in css
    assert "calendar-provider-row" not in css
    assert "calendar-provider-cta" not in css
    assert 'class="calendar-advanced-fields"' in html
    assert "https://calendar.example/caldav…" in html
    assert "https://calendar.example/caldav..." not in html
    assert html.index('id="calendar-sources-title"') < html.index('id="calendar-providers-title"')
    assert html.index('id="calendar-providers-title"') < html.index('id="calendar-boundary-title"')
    assert html.index('class="calendar-advanced-fields"') < html.index('name="account_label"')
    assert_no_forbidden_calendar_settings_content(html)


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
    assert "Будущая синхронизация из этого источника остановится" in html
    assert "Данные подключения будут удалены или отозваны там, где это контролирует 2brain Rec" in html
    assert "Уже связанный контекст встреч живет по политике хранения встречи" in html
    assert "не обещает удалить данные вне своего контроля" in html
    assert "удалит события у провайдера" not in html
    assert_no_forbidden_calendar_settings_content(html)


def test_calendar_settings_accessibility_contract_for_states_and_controls(client) -> None:
    response = client.get("/settings/integrations/calendar", headers=auth_headers())
    css = CALENDAR_CSS.read_text()

    assert response.status_code == 200
    html = response.text
    assert 'id="calendar-settings-region"' in html
    assert 'aria-label="Путь к разделу"' in html
    assert 'aria-labelledby="calendar-boundary-title"' in html
    assert 'aria-labelledby="calendar-sources-title"' in html
    assert 'aria-labelledby="calendar-providers-title"' in html
    assert 'aria-label="Закрыть окно подключения"' in html
    assert 'aria-haspopup="dialog"' in html
    assert 'aria-live="polite"' in html
    assert 'role="status"' in html
    assert 'name="join_prompt_enabled"' in html
    assert 'name="record_prompt_enabled"' in html
    assert 'name="credential_input"' in html
    assert "Если настройка ограничена политикой организации" in html
    assert "Во время загрузки настроек ручная запись остается доступной" in html
    assert "Если настройки календарей временно недоступны" in html
    assert "Private/free-busy события показываются без названия" in html
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
    assert "12:30 - 13:00 UTC" in html
    assert "2brain Rec не выбирает событие автоматически" in html
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
    assert "Поддерживаемые провайдеры" in html
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
    assert "Пароль приложения" in response.text
    assert "может понадобиться настройка организации" in response.text
    assert "Подключить по паролю приложения" not in response.text
    assert "Подключить CalDAV" not in response.text
    assert "Показать условия подключения" not in response.text
    assert "Проверить подключение" in response.text
    assert "Подключить Яндекс Календарь" in response.text
    assert "Подключить Mail.ru Календарь" in response.text
    assert response.text.count('class="calendar-provider-dialog"') >= len(REQUIRED_PROVIDER_LABELS)
    assert "data-calendar-provider-close" in response.text
    assert 'name="credential_input"' in response.text
    assert 'name="caldav_url"' in response.text
    assert (
        "Данные для подключения остаются на сервере 2brain Rec"
        in response.text
    )
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
