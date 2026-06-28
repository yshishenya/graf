from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid4

from sqlalchemy import func, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, FORGED_USER_ID, ORG_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.dependencies import (
    DESKTOP_CALENDAR_AUTH_COOKIE_NAME,
    DESKTOP_CALENDAR_AUTH_COOKIE_PATH,
)
from twobrain_rec_server.calendar.credentials import unseal_credential
from twobrain_rec_server.calendar.service import (
    load_calendar_settings_preferences,
    save_calendar_settings_preferences,
)
from twobrain_rec_server.db.models import (
    CalendarAuditEvent,
    CalendarCredentialEnvelope,
    CalendarEventSnapshot,
    CalendarSettingsPreference,
    CalendarSource,
    ExternalCalendar,
    Meeting,
    RecordingCalendarContextLink,
    RegisteredDevice,
    UserIdentity,
    WorkspaceMembership,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0012_calendar_settings_preferences.py"
)


def _csrf_token_from(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def test_calendar_settings_preferences_default_and_save_are_tenant_scoped(client) -> None:
    sessionmaker = client.app_state["sessionmaker"]
    tenant_scope = TenantScope(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        user_id=USER_ID,
        device_id=DEVICE_ID,
    )

    async def exercise() -> None:
        async with sessionmaker() as session:
            preferences = await load_calendar_settings_preferences(session, tenant_scope)
            assert preferences.join_prompt_enabled is True
            assert preferences.record_prompt_enabled is True
            assert preferences.include_all_day_events is False

            saved = await save_calendar_settings_preferences(
                session,
                tenant_scope,
                join_prompt_enabled=False,
                include_all_day_events=True,
                ignored_field=True,
            )
            await session.commit()
            assert saved.join_prompt_enabled is False
            assert saved.include_all_day_events is True
            assert not hasattr(saved, "ignored_field")

        async with sessionmaker() as session:
            rows = list(await session.scalars(select(CalendarSettingsPreference)))
            assert len(rows) == 1
            assert rows[0].workspace_id == WORKSPACE_ID
            assert rows[0].owner_user_id == USER_ID

    asyncio.run(exercise())


def test_calendar_settings_migration_creates_preference_table_with_rls_policy() -> None:
    migration_text = MIGRATION.read_text()
    normalized = migration_text.lower()

    assert "calendar_settings_preferences" in migration_text
    assert "join_prompt_enabled" in migration_text
    assert "include_private_free_busy_prompt_candidates" in migration_text
    assert "enable row level security" in normalized
    assert "calendar_settings_preferences_tenant_isolation" in migration_text


def test_calendar_settings_page_renders_connected_source_that_needs_calendar_selection(
    client,
) -> None:
    sessionmaker = client.app_state["sessionmaker"]

    async def seed() -> None:
        async with sessionmaker() as session:
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label="Яндекс Календарь",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="synced",
                selected_calendar_count=0,
                capabilities_json={},
            )
            session.add(source)
            await session.flush()
            session.add(
                ExternalCalendar(
                    workspace_id=WORKSPACE_ID,
                    calendar_source_id=source.id,
                    provider_calendar_id="primary",
                    display_label="Рабочий календарь",
                    visibility="available",
                )
            )
            await session.commit()

    asyncio.run(seed())

    response = client.get("/settings/integrations/calendar", headers=auth_headers())

    assert response.status_code == 200
    assert "Яндекс Календарь" in response.text
    assert "Рабочий календарь" in response.text
    assert "Нужно выбрать календари" in response.text
    assert "0 из 1" in response.text

    async def load_preferences_count() -> int:
        async with sessionmaker() as session:
            return int(await session.scalar(select(func.count()).select_from(CalendarSettingsPreference)) or 0)

    assert asyncio.run(load_preferences_count()) == 0


def test_calendar_settings_preview_ignores_selected_unavailable_calendar(client) -> None:
    sessionmaker = client.app_state["sessionmaker"]
    now = datetime.now(UTC)

    async def seed() -> None:
        async with sessionmaker() as session:
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label="Яндекс Календарь",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="synced",
                selected_calendar_count=1,
                capabilities_json={},
            )
            session.add(source)
            await session.flush()
            unavailable = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id="unavailable",
                display_label="Архив",
                visibility="unavailable",
                selected=True,
            )
            session.add(unavailable)
            await session.flush()
            session.add(
                CalendarEventSnapshot(
                    workspace_id=WORKSPACE_ID,
                    calendar_source_id=source.id,
                    external_calendar_id=unavailable.id,
                    provider_event_id="unavailable-preview",
                    starts_at=now + timedelta(hours=1),
                    ends_at=now + timedelta(hours=2),
                    title="Unavailable preview meeting",
                    privacy_class="public",
                    source_status="confirmed",
                    conference_summary_json={"meeting_link_present": True},
                    attachments_metadata_json=[],
                    provider_extras_json={},
                    safe_to_show_in_list=True,
                    safe_to_use_as_title=True,
                    sensitivity_reasons_json=[],
                )
            )
            await session.commit()

    asyncio.run(seed())

    response = client.get("/settings/integrations/calendar", headers=auth_headers())

    assert response.status_code == 200
    assert "Нет календарей для чтения" in response.text
    assert "0 из 0" in response.text
    assert "Unavailable preview meeting" not in response.text


def test_calendar_settings_sources_are_scoped_to_current_user(client) -> None:
    sessionmaker = client.app_state["sessionmaker"]
    other_device_id = UUID("40000000-0000-0000-0000-000000000098")

    async def seed() -> UUID:
        async with sessionmaker() as session:
            session.add_all(
                [
                    UserIdentity(
                        id=FORGED_USER_ID,
                        organization_id=ORG_ID,
                        external_subject=str(FORGED_USER_ID),
                        display_name="Other User",
                    ),
                    WorkspaceMembership(
                        workspace_id=WORKSPACE_ID,
                        user_id=FORGED_USER_ID,
                        role="member",
                        status="active",
                    ),
                    RegisteredDevice(
                        id=other_device_id,
                        workspace_id=WORKSPACE_ID,
                        user_id=FORGED_USER_ID,
                        device_public_id="other-calendar-device",
                        status="active",
                    ),
                ]
            )
            own_source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label="Мой календарь",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="never_synced",
                selected_calendar_count=0,
                capabilities_json={},
            )
            other_source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=FORGED_USER_ID,
                provider_family="caldav_mail_ru",
                provider_label="Чужой календарь",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="never_synced",
                selected_calendar_count=0,
                capabilities_json={},
            )
            session.add_all([own_source, other_source])
            await session.flush()
            other_calendar = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=other_source.id,
                provider_calendar_id="other-primary",
                display_label="Чужой рабочий календарь",
                visibility="available",
                selected=True,
            )
            session.add(other_calendar)
            await session.flush()
            session.add(
                CalendarEventSnapshot(
                    workspace_id=WORKSPACE_ID,
                    calendar_source_id=other_source.id,
                    external_calendar_id=other_calendar.id,
                    provider_event_id="other-upcoming",
                    starts_at=datetime.now(UTC) + timedelta(hours=1),
                    ends_at=datetime.now(UTC) + timedelta(hours=2),
                    title="Other user planning",
                    privacy_class="public",
                    source_status="confirmed",
                    conference_summary_json={"meeting_link_present": True},
                    attachments_metadata_json=[],
                    provider_extras_json={},
                    safe_to_show_in_list=True,
                    safe_to_use_as_title=True,
                    sensitivity_reasons_json=[],
                )
            )
            await session.commit()
            return other_source.id

    other_source_id = asyncio.run(seed())

    response = client.get("/settings/integrations/calendar", headers=auth_headers())

    assert response.status_code == 200
    assert "Мой календарь" in response.text
    assert "Чужой календарь" not in response.text

    web_denied = client.post(
        f"/settings/integrations/calendar/sources/{other_source_id}/sync",
        headers=auth_headers(),
        follow_redirects=False,
    )
    api_denied = client.get(
        f"/api/v1/calendar/sources/{other_source_id}",
        headers=auth_headers(),
    )
    upcoming = client.get("/api/v1/calendar/events/upcoming", headers=auth_headers())

    assert web_denied.status_code == 404
    assert api_denied.status_code == 404
    assert upcoming.status_code == 200
    assert "Other user planning" not in upcoming.text


def test_calendar_settings_unknown_source_actions_return_not_found_without_audit(client) -> None:
    sessionmaker = client.app_state["sessionmaker"]
    missing_source_id = uuid4()

    sync_denied = client.post(
        f"/settings/integrations/calendar/sources/{missing_source_id}/sync",
        headers=auth_headers(),
        follow_redirects=False,
    )
    disconnect_denied = client.post(
        f"/settings/integrations/calendar/sources/{missing_source_id}/disconnect",
        headers=auth_headers(),
        follow_redirects=False,
    )

    assert sync_denied.status_code == 404
    assert disconnect_denied.status_code == 404

    async def load_source_audit_events() -> list[CalendarAuditEvent]:
        async with sessionmaker() as session:
            return list(
                await session.scalars(
                    select(CalendarAuditEvent).where(CalendarAuditEvent.calendar_source_id == missing_source_id)
                )
            )

    assert asyncio.run(load_source_audit_events()) == []


def test_embedded_calendar_settings_post_uses_server_owned_desktop_cookie(
    client,
) -> None:
    opened = client.get(
        "https://testserver/desktop/settings/integrations/calendar",
        headers=auth_headers(),
    )

    assert opened.status_code == 200
    set_cookie = opened.headers["set-cookie"]
    assert DESKTOP_CALENDAR_AUTH_COOKIE_NAME in set_cookie
    assert f"Path={DESKTOP_CALENDAR_AUTH_COOKIE_PATH}" in set_cookie
    assert "Secure" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "samesite=strict" in set_cookie.lower()

    missing_csrf = client.post(
        "https://testserver/desktop/settings/integrations/calendar/preferences",
        data={
            "join_prompt_enabled": "on",
            "record_prompt_enabled": "on",
            "show_upcoming_time": "on",
            "show_upcoming_title": "on",
        },
        follow_redirects=False,
    )

    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["code"] == "csrf_token_missing"

    saved = client.post(
        "https://testserver/desktop/settings/integrations/calendar/preferences",
        data={
            "csrf_token": _csrf_token_from(opened.text),
            "join_prompt_enabled": "on",
            "record_prompt_enabled": "on",
            "show_upcoming_time": "on",
            "show_upcoming_title": "on",
        },
        follow_redirects=False,
    )

    assert saved.status_code == 303
    assert (
        saved.headers["location"]
        == "/desktop/settings/integrations/calendar?preferences_result=saved"
    )

    sessionmaker = client.app_state["sessionmaker"]

    async def load_preferences() -> CalendarSettingsPreference | None:
        async with sessionmaker() as session:
            return await session.scalar(select(CalendarSettingsPreference))

    preferences = asyncio.run(load_preferences())
    assert preferences is not None
    assert preferences.workspace_id == WORKSPACE_ID
    assert preferences.owner_user_id == USER_ID
    assert preferences.join_prompt_enabled is True
    assert preferences.show_upcoming_time is True


def test_embedded_calendar_settings_desktop_cookie_survives_legacy_header_shutdown(
    client,
) -> None:
    settings = client.app.state.settings
    original_env = settings.env
    original_legacy_header_auth_enabled = settings.legacy_header_auth_enabled
    settings.env = "production"
    settings.legacy_header_auth_enabled = True
    try:
        opened = client.get(
            "https://testserver/desktop/settings/integrations/calendar",
            headers=auth_headers(),
        )
        assert opened.status_code == 200
        assert DESKTOP_CALENDAR_AUTH_COOKIE_NAME in opened.headers["set-cookie"]

        settings.legacy_header_auth_enabled = False
        saved = client.post(
            "https://testserver/desktop/settings/integrations/calendar/preferences",
            data={
                "csrf_token": _csrf_token_from(opened.text),
                "join_prompt_enabled": "on",
                "record_prompt_enabled": "on",
                "show_upcoming_time": "on",
                "show_upcoming_title": "on",
            },
            follow_redirects=False,
        )
    finally:
        settings.env = original_env
        settings.legacy_header_auth_enabled = original_legacy_header_auth_enabled

    assert saved.status_code == 303
    assert (
        saved.headers["location"]
        == "/desktop/settings/integrations/calendar?preferences_result=saved"
    )


def test_calendar_settings_connect_app_password_creates_source_without_selected_calendars_and_audits(
    client,
) -> None:
    response = client.post(
        "/settings/integrations/calendar/providers/caldav_yandex/connect",
        headers=auth_headers(),
        data={
            "account_label": "Рабочий Яндекс",
            "username": "owner@example.test",
            "credential_input": "secret-app-password",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/settings/integrations/calendar?connect_result=success"
    rendered = client.get(response.headers["location"], headers=auth_headers())
    assert rendered.status_code == 200
    assert "Календарь подключен" in rendered.text
    assert "secret-app-password" not in rendered.text
    assert "owner@example.test" not in rendered.text

    sessionmaker = client.app_state["sessionmaker"]

    async def load_state() -> tuple[
        list[CalendarSource], list[CalendarCredentialEnvelope], list[CalendarAuditEvent]
    ]:
        async with sessionmaker() as session:
            sources = list(await session.scalars(select(CalendarSource)))
            envelopes = list(await session.scalars(select(CalendarCredentialEnvelope)))
            events = list(
                await session.scalars(
                    select(CalendarAuditEvent).order_by(CalendarAuditEvent.created_at.asc())
                )
            )
            return sources, envelopes, events

    sources, envelopes, events = asyncio.run(load_state())

    assert len(sources) == 1
    assert sources[0].provider_family == "caldav_yandex"
    assert sources[0].credential_state == "sealed"
    assert sources[0].selected_calendar_count == 0
    assert len(envelopes) == 1
    sealed_payload = json.loads(
        unseal_credential(envelopes[0].sealed_payload, client.app.state.calendar_credential_key)
    )
    assert sealed_payload == {
        "username": "owner@example.test",
        "credential_input": "secret-app-password",
    }
    assert "secret-app-password" not in str(events)
    assert [event.event_type for event in events] == [
        "calendar_connect_start",
        "calendar_connect_result",
    ]
    assert events[-1].outcome == "completed"
    assert events[-1].calendar_source_id == sources[0].id


def test_calendar_settings_app_password_requires_username(client) -> None:
    response = client.post(
        "/settings/integrations/calendar/providers/caldav_yandex/connect",
        headers=auth_headers(),
        data={"credential_input": "secret-app-password"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/settings/integrations/calendar?connect_result=failed"

    sessionmaker = client.app_state["sessionmaker"]

    async def load_source_count() -> int:
        async with sessionmaker() as session:
            return int(await session.scalar(select(func.count()).select_from(CalendarSource)) or 0)

    assert asyncio.run(load_source_count()) == 0


def test_calendar_settings_provider_result_states_are_safe(client) -> None:
    expected = {
        "cancelled": "Подключение отменено",
        "denied": "Календарь не подключен",
        "failed": "Не удалось подключить календарь",
        "no_readable_calendars": "Нет доступных для чтения календарей",
    }

    for result, copy in expected.items():
        response = client.get(
            f"/settings/integrations/calendar/provider-result?provider_family=caldav_yandex&result={result}",
            headers=auth_headers(),
            follow_redirects=False,
        )

        assert response.status_code == 303
        rendered = client.get(response.headers["location"], headers=auth_headers())
        assert rendered.status_code == 200
        assert copy in rendered.text
        assert "raw_provider_payload" not in rendered.text
        assert "access_token" not in rendered.text


def test_calendar_settings_provider_limited_state_does_not_create_source(client) -> None:
    response = client.post(
        "/settings/integrations/calendar/providers/exchange_ews/connect",
        headers=auth_headers(),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["location"]
        == "/settings/integrations/calendar?policy_limited=provider_limited"
    )
    rendered = client.get(response.headers["location"], headers=auth_headers())
    assert "Есть ограничение провайдера" in rendered.text
    assert "2brain Rec все равно работает только на чтение" in rendered.text

    sessionmaker = client.app_state["sessionmaker"]

    async def load_sources_and_audits() -> tuple[list[CalendarSource], list[CalendarAuditEvent]]:
        async with sessionmaker() as session:
            sources = list(await session.scalars(select(CalendarSource)))
            events = list(
                await session.scalars(
                    select(CalendarAuditEvent).order_by(CalendarAuditEvent.created_at.asc())
                )
            )
            return sources, events

    sources, events = asyncio.run(load_sources_and_audits())

    assert sources == []
    assert [event.event_type for event in events] == [
        "calendar_connect_start",
        "calendar_connect_result",
    ]
    assert events[-1].outcome == "blocked"
    assert events[-1].safe_reason_code == "provider_limited"


def test_calendar_settings_unknown_provider_connect_does_not_create_source(client) -> None:
    response = client.post(
        "/settings/integrations/calendar/providers/unsupported_provider/connect",
        headers=auth_headers(),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/settings/integrations/calendar?connect_result=failed"
    rendered = client.get(response.headers["location"], headers=auth_headers())
    assert "Не удалось подключить календарь" in rendered.text

    sessionmaker = client.app_state["sessionmaker"]

    async def load_sources_and_audits() -> tuple[list[CalendarSource], list[CalendarAuditEvent]]:
        async with sessionmaker() as session:
            sources = list(await session.scalars(select(CalendarSource)))
            events = list(
                await session.scalars(
                    select(CalendarAuditEvent).order_by(CalendarAuditEvent.created_at.asc())
                )
            )
            return sources, events

    sources, events = asyncio.run(load_sources_and_audits())

    assert sources == []
    assert [event.event_type for event in events] == ["calendar_connect_result"]
    assert events[-1].outcome == "failed"
    assert events[-1].safe_reason_code == "unsupported_calendar_provider"


def test_calendar_settings_provider_success_result_does_not_claim_connected_without_source(
    client,
) -> None:
    for provider_family in ("custom_caldav",):
        response = client.get(
            f"/settings/integrations/calendar/provider-result?provider_family={provider_family}&result=success",
            headers=auth_headers(),
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert (
            response.headers["location"]
            == "/settings/integrations/calendar?policy_limited=provider_limited"
        )
        rendered = client.get(response.headers["location"], headers=auth_headers())
        assert "Календарь подключен" not in rendered.text
        assert "Есть ограничение провайдера" in rendered.text

    sessionmaker = client.app_state["sessionmaker"]

    async def load_source_count() -> int:
        async with sessionmaker() as session:
            return int(await session.scalar(select(func.count()).select_from(CalendarSource)) or 0)

    assert asyncio.run(load_source_count()) == 0


def test_calendar_settings_selection_save_empty_and_no_retrospective_matching(client) -> None:
    sessionmaker = client.app_state["sessionmaker"]
    now = datetime.now(UTC)

    async def seed() -> str:
        async with sessionmaker() as session:
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label="Яндекс Календарь",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="synced",
                selected_calendar_count=0,
                capabilities_json={},
            )
            session.add(source)
            await session.flush()
            primary = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id="primary",
                display_label="Рабочий календарь",
                visibility="available",
            )
            noisy = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id="noisy",
                display_label="Шумный календарь",
                visibility="delegated",
            )
            unavailable = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id="unavailable",
                display_label="Архив",
                visibility="unavailable",
            )
            session.add_all([primary, noisy, unavailable])
            await session.flush()
            selected_event = CalendarEventSnapshot(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                external_calendar_id=primary.id,
                provider_event_id="selected-future",
                starts_at=now + timedelta(hours=2),
                ends_at=now + timedelta(hours=3),
                title="Selected preview meeting",
                privacy_class="public",
                source_status="confirmed",
                conference_summary_json={"meeting_link_present": True},
                attachments_metadata_json=[],
                provider_extras_json={},
                safe_to_show_in_list=True,
                safe_to_use_as_title=True,
                sensitivity_reasons_json=[],
            )
            unselected_event = CalendarEventSnapshot(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                external_calendar_id=noisy.id,
                provider_event_id="unselected-future",
                starts_at=now + timedelta(hours=4),
                ends_at=now + timedelta(hours=5),
                title="Unselected preview meeting",
                privacy_class="public",
                source_status="confirmed",
                conference_summary_json={"meeting_link_present": True},
                attachments_metadata_json=[],
                provider_extras_json={},
                safe_to_show_in_list=True,
                safe_to_use_as_title=True,
                sensitivity_reasons_json=[],
            )
            session.add_all([selected_event, unselected_event])
            meeting = Meeting(
                workspace_id=WORKSPACE_ID,
                created_by_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id="existing-calendar-link",
                title="Existing linked recording",
                started_at=now - timedelta(days=1),
                duration_seconds=1800,
            )
            session.add(meeting)
            await session.flush()
            session.add(
                RecordingCalendarContextLink(
                    workspace_id=WORKSPACE_ID,
                    meeting_id=meeting.id,
                    calendar_event_snapshot_id=selected_event.id,
                    context_confidence="manual",
                    context_reasons_json=["existing_link"],
                    title_source="calendar",
                    roster_source="none",
                    linked_at=now - timedelta(days=1),
                )
            )
            await session.commit()
            return str(source.id)

    source_id = asyncio.run(seed())

    selected = client.post(
        f"/settings/integrations/calendar/sources/{source_id}/calendars",
        headers=auth_headers(),
        data={"selected_provider_calendar_ids": ["primary", "unavailable", "unknown-forged"]},
        follow_redirects=False,
    )
    assert selected.status_code == 303
    assert selected.headers["location"] == "/settings/integrations/calendar?selection_result=saved"

    rendered = client.get(selected.headers["location"], headers=auth_headers())
    assert "Выбор календарей сохранен" in rendered.text
    assert "1 из 2" in rendered.text
    assert "Selected preview meeting" in rendered.text
    assert "Unselected preview meeting" not in rendered.text

    async def load_after_selected() -> list[ExternalCalendar]:
        async with sessionmaker() as session:
            return list(
                await session.scalars(
                    select(ExternalCalendar).order_by(ExternalCalendar.provider_calendar_id.asc())
                )
            )

    selected_calendars = asyncio.run(load_after_selected())
    assert {calendar.provider_calendar_id: calendar.selected for calendar in selected_calendars} == {
        "noisy": False,
        "primary": True,
        "unavailable": False,
    }

    empty = client.post(
        f"/settings/integrations/calendar/sources/{source_id}/calendars",
        headers=auth_headers(),
        data={},
        follow_redirects=False,
    )
    assert empty.status_code == 303
    assert empty.headers["location"] == "/settings/integrations/calendar?selection_result=empty"
    rendered_empty = client.get(empty.headers["location"], headers=auth_headers())
    assert "Календари не выбраны" in rendered_empty.text
    assert "0 из 2" in rendered_empty.text
    assert "Выберите хотя бы один календарь" in rendered_empty.text
    assert "Selected preview meeting" not in rendered_empty.text

    forged_only = client.post(
        f"/settings/integrations/calendar/sources/{source_id}/calendars",
        headers=auth_headers(),
        data={"selected_provider_calendar_ids": ["unavailable", "unknown-forged"]},
        follow_redirects=False,
    )
    assert forged_only.status_code == 303
    assert forged_only.headers["location"] == "/settings/integrations/calendar?selection_result=empty"
    rendered_forged_only = client.get(forged_only.headers["location"], headers=auth_headers())
    assert "Календари не выбраны" in rendered_forged_only.text
    assert "Выбор календарей сохранен" not in rendered_forged_only.text

    async def load_after_empty() -> tuple[int, int, list[ExternalCalendar]]:
        async with sessionmaker() as session:
            link_count = await session.scalar(
                select(func.count()).select_from(RecordingCalendarContextLink)
            )
            source_count = await session.scalar(select(func.count()).select_from(CalendarSource))
            calendars = list(
                await session.scalars(
                    select(ExternalCalendar).order_by(ExternalCalendar.provider_calendar_id.asc())
                )
            )
            return int(link_count or 0), int(source_count or 0), calendars

    link_count, source_count, calendars = asyncio.run(load_after_empty())

    assert link_count == 1
    assert source_count == 1
    assert {calendar.provider_calendar_id: calendar.selected for calendar in calendars} == {
        "noisy": False,
        "primary": False,
        "unavailable": False,
    }
    assert {calendar.provider_calendar_id: calendar.visibility for calendar in calendars} == {
        "noisy": "delegated",
        "primary": "available",
        "unavailable": "unavailable",
    }


def test_calendar_settings_saves_event_category_preferences_and_keeps_manual_recording_copy(
    client,
) -> None:
    response = client.post(
        "/settings/integrations/calendar/preferences",
        headers=auth_headers(),
        data={
            "join_prompt_enabled": "on",
            "record_prompt_enabled": "on",
            "show_upcoming_time": "on",
            "show_upcoming_title": "on",
            "include_events_without_participants": "on",
            "include_events_without_link_or_location": "on",
            "include_all_day_events": "on",
            "include_private_free_busy_prompt_candidates": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["location"] == "/settings/integrations/calendar?preferences_result=saved"
    )
    rendered = client.get(response.headers["location"], headers=auth_headers())
    assert "Настройки сохранены" in rendered.text
    assert "Ручной старт и стоп записи остаются доступны всегда" in rendered.text
    assert "Автоматическая запись пока недоступна" in rendered.text

    sessionmaker = client.app_state["sessionmaker"]

    async def load_preferences() -> CalendarSettingsPreference:
        async with sessionmaker() as session:
            return await session.scalar(select(CalendarSettingsPreference))

    preferences = asyncio.run(load_preferences())

    assert preferences is not None
    assert preferences.include_events_without_participants is True
    assert preferences.include_events_without_link_or_location is True
    assert preferences.include_all_day_events is True
    assert preferences.include_private_free_busy_prompt_candidates is True
    assert preferences.join_prompt_enabled is True
    assert preferences.record_prompt_enabled is True


def test_calendar_settings_preview_respects_hidden_time_and_title_preferences(
    client,
) -> None:
    sessionmaker = client.app_state["sessionmaker"]
    now = datetime.now(UTC)

    async def seed() -> None:
        async with sessionmaker() as session:
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label="Яндекс Календарь",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="synced",
                selected_calendar_count=1,
                capabilities_json={},
            )
            session.add(source)
            await session.flush()
            calendar = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id="primary",
                display_label="Рабочий календарь",
                visibility="available",
                selected=True,
            )
            session.add(calendar)
            await session.flush()
            session.add(
                CalendarEventSnapshot(
                    workspace_id=WORKSPACE_ID,
                    calendar_source_id=source.id,
                    external_calendar_id=calendar.id,
                    provider_event_id="hidden-preview",
                    starts_at=now + timedelta(hours=2),
                    ends_at=now + timedelta(hours=3),
                    title="Hidden preview meeting",
                    privacy_class="public",
                    source_status="confirmed",
                    conference_summary_json={"meeting_link_present": True},
                    attachments_metadata_json=[],
                    provider_extras_json={},
                    safe_to_show_in_list=True,
                    safe_to_use_as_title=True,
                    sensitivity_reasons_json=[],
                )
            )
            await session.commit()

    asyncio.run(seed())

    saved = client.post(
        "/settings/integrations/calendar/preferences",
        headers=auth_headers(),
        data={"join_prompt_enabled": "on", "record_prompt_enabled": "on"},
        follow_redirects=False,
    )
    assert saved.status_code == 303

    rendered = client.get("/settings/integrations/calendar", headers=auth_headers())

    assert rendered.status_code == 200
    assert "Время скрыто настройкой" in rendered.text
    assert "Название скрыто настройкой" in rendered.text
    assert "Hidden preview meeting" not in rendered.text


def test_calendar_settings_preview_shows_active_overlap_started_before_now(client) -> None:
    sessionmaker = client.app_state["sessionmaker"]
    now = datetime.now(UTC)

    async def seed() -> None:
        async with sessionmaker() as session:
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label="Яндекс Календарь",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="synced",
                selected_calendar_count=2,
                capabilities_json={},
            )
            session.add(source)
            await session.flush()
            first_calendar = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id="first",
                display_label="Первый календарь",
                visibility="available",
                selected=True,
            )
            second_calendar = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id="second",
                display_label="Второй календарь",
                visibility="available",
                selected=True,
            )
            session.add_all([first_calendar, second_calendar])
            await session.flush()
            session.add_all(
                [
                    CalendarEventSnapshot(
                        workspace_id=WORKSPACE_ID,
                        calendar_source_id=source.id,
                        external_calendar_id=first_calendar.id,
                        provider_event_id="active-first",
                        starts_at=now - timedelta(minutes=45),
                        ends_at=now + timedelta(minutes=15),
                        title="Первое активное событие",
                        privacy_class="public",
                        source_status="confirmed",
                        conference_summary_json={"meeting_link_present": True},
                        attachments_metadata_json=[],
                        provider_extras_json={},
                        safe_to_show_in_list=True,
                        safe_to_use_as_title=True,
                        sensitivity_reasons_json=[],
                    ),
                    CalendarEventSnapshot(
                        workspace_id=WORKSPACE_ID,
                        calendar_source_id=source.id,
                        external_calendar_id=second_calendar.id,
                        provider_event_id="active-second",
                        starts_at=now - timedelta(minutes=30),
                        ends_at=now + timedelta(minutes=30),
                        title="Второе активное событие",
                        privacy_class="public",
                        source_status="confirmed",
                        conference_summary_json={"meeting_link_present": True},
                        attachments_metadata_json=[],
                        provider_extras_json={},
                        safe_to_show_in_list=True,
                        safe_to_use_as_title=True,
                        sensitivity_reasons_json=[],
                    ),
                ]
            )
            await session.commit()

    asyncio.run(seed())

    rendered = client.get("/settings/integrations/calendar", headers=auth_headers())

    assert rendered.status_code == 200
    assert "Нужно выбрать событие для пересечения" in rendered.text
    assert "2brain Rec не выбирает событие автоматически" in rendered.text
    assert "Можно продолжить без календарного контекста" in rendered.text


def test_calendar_settings_preview_applies_preferences_before_limit(client) -> None:
    sessionmaker = client.app_state["sessionmaker"]
    now = datetime.now(UTC)

    async def seed() -> None:
        async with sessionmaker() as session:
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label="Яндекс Календарь",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="synced",
                selected_calendar_count=1,
                capabilities_json={},
            )
            session.add(source)
            await session.flush()
            calendar = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id="primary",
                display_label="Рабочий календарь",
                visibility="available",
                selected=True,
            )
            session.add(calendar)
            await session.flush()
            noisy_events = [
                CalendarEventSnapshot(
                    workspace_id=WORKSPACE_ID,
                    calendar_source_id=source.id,
                    external_calendar_id=calendar.id,
                    provider_event_id=f"preview-all-day-{index}",
                    starts_at=now + timedelta(minutes=index + 1),
                    ends_at=now + timedelta(minutes=index + 61),
                    title=f"Preview all-day noise {index}",
                    all_day=True,
                    privacy_class="public",
                    source_status="confirmed",
                    conference_summary_json={"meeting_link_present": True},
                    attachments_metadata_json=[],
                    provider_extras_json={},
                    safe_to_show_in_list=True,
                    safe_to_use_as_title=True,
                    sensitivity_reasons_json=[],
                )
                for index in range(9)
            ]
            valid_event = CalendarEventSnapshot(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                external_calendar_id=calendar.id,
                provider_event_id="preview-valid-after-noise",
                starts_at=now + timedelta(hours=2),
                ends_at=now + timedelta(hours=3),
                title="Preview valid meeting after noise",
                privacy_class="public",
                source_status="confirmed",
                conference_summary_json={"meeting_link_present": False, "participant_count": 2},
                attachments_metadata_json=[],
                provider_extras_json={},
                safe_to_show_in_list=True,
                safe_to_use_as_title=True,
                sensitivity_reasons_json=[],
            )
            session.add_all([*noisy_events, valid_event])
            await session.commit()

    asyncio.run(seed())

    rendered = client.get("/settings/integrations/calendar", headers=auth_headers())

    assert rendered.status_code == 200
    assert "Preview valid meeting after noise" in rendered.text
    assert "Preview all-day noise" not in rendered.text


def test_calendar_settings_preview_empty_reason_when_selected_calendar_has_no_matching_events(
    client,
) -> None:
    sessionmaker = client.app_state["sessionmaker"]
    now = datetime.now(UTC)

    async def seed() -> None:
        async with sessionmaker() as session:
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label="Яндекс Календарь",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="synced",
                selected_calendar_count=1,
                capabilities_json={},
            )
            session.add(source)
            await session.flush()
            calendar = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id="primary",
                display_label="Рабочий календарь",
                visibility="available",
                selected=True,
            )
            session.add(calendar)
            await session.flush()
            all_day = CalendarEventSnapshot(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                external_calendar_id=calendar.id,
                provider_event_id="all-day-hold",
                starts_at=now + timedelta(days=1),
                ends_at=now + timedelta(days=2),
                title="All-day hold",
                all_day=True,
                privacy_class="public",
                source_status="confirmed",
                conference_summary_json={"meeting_link_present": True},
                attachments_metadata_json=[],
                provider_extras_json={},
                safe_to_show_in_list=True,
                safe_to_use_as_title=True,
                sensitivity_reasons_json=[],
            )
            session.add(all_day)
            await session.commit()

    asyncio.run(seed())

    rendered = client.get("/settings/integrations/calendar", headers=auth_headers())

    assert rendered.status_code == 200
    assert "Нет будущих событий, которые подходят под выбранные настройки" in rendered.text
    assert "All-day hold" not in rendered.text


def test_calendar_settings_preview_marks_stale_private_free_busy_safely(client) -> None:
    sessionmaker = client.app_state["sessionmaker"]
    now = datetime.now(UTC)

    async def seed() -> None:
        async with sessionmaker() as session:
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label="Яндекс Календарь",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="synced",
                selected_calendar_count=1,
                last_successful_sync_at=now - timedelta(days=2),
                capabilities_json={},
            )
            session.add(source)
            await session.flush()
            calendar = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id="private",
                display_label="Личный календарь",
                visibility="private",
                selected=True,
            )
            session.add(calendar)
            await session.flush()
            private_event = CalendarEventSnapshot(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                external_calendar_id=calendar.id,
                provider_event_id="private-free-busy",
                starts_at=now + timedelta(hours=2),
                ends_at=now + timedelta(hours=3),
                title="Private board review",
                privacy_class="private",
                source_status="confirmed",
                conference_summary_json={"meeting_link_present": True},
                attachments_metadata_json=[],
                provider_extras_json={},
                safe_to_show_in_list=False,
                safe_to_use_as_title=False,
                sensitivity_reasons_json=["private"],
            )
            session.add(private_event)
            await session.commit()

    asyncio.run(seed())
    client.post(
        "/settings/integrations/calendar/preferences",
        headers=auth_headers(),
        data={
            "join_prompt_enabled": "on",
            "record_prompt_enabled": "on",
            "show_upcoming_time": "on",
            "show_upcoming_title": "on",
            "include_private_free_busy_prompt_candidates": "on",
        },
        follow_redirects=False,
    )

    rendered = client.get("/settings/integrations/calendar", headers=auth_headers())

    assert rendered.status_code == 200
    assert "Скрытое событие" in rendered.text
    assert "Личный календарь" in rendered.text
    assert "данные синхронизации могут быть устаревшими" in rendered.text
    assert "без ссылки на встречу" in rendered.text
    assert "Private board review" not in rendered.text
    assert "attendee@example" not in rendered.text


def test_calendar_settings_route_saves_prompt_toggles_without_auto_record_behavior(client) -> None:
    response = client.post(
        "/settings/integrations/calendar/preferences",
        headers=auth_headers(),
        data={
            "show_upcoming_time": "on",
            "show_upcoming_title": "on",
            "auto_record_disabled": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["location"] == "/settings/integrations/calendar?preferences_result=saved"
    )
    rendered = client.get(response.headers["location"], headers=auth_headers())
    assert "Автоматическая запись пока недоступна" in rendered.text
    assert "выбрать событие или продолжить без календарного контекста" in rendered.text

    sessionmaker = client.app_state["sessionmaker"]

    async def load_preferences() -> CalendarSettingsPreference:
        async with sessionmaker() as session:
            return await session.scalar(select(CalendarSettingsPreference))

    preferences = asyncio.run(load_preferences())

    assert preferences is not None
    assert preferences.join_prompt_enabled is False
    assert preferences.record_prompt_enabled is False
    assert not hasattr(preferences, "auto_record_disabled")


def test_calendar_settings_manual_sync_results_cover_safe_states_and_audit(client) -> None:
    sessionmaker = client.app_state["sessionmaker"]
    now = datetime.now(UTC)

    async def seed_source(
        name: str,
        *,
        connection_state: str = "active",
        sync_state: str = "synced",
        last_successful_sync_at: datetime | None = None,
        disconnected_at: datetime | None = None,
    ):
        async with sessionmaker() as session:
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label=f"Яндекс Календарь {name}",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state=connection_state,
                sync_state=sync_state,
                selected_calendar_count=0,
                last_successful_sync_at=last_successful_sync_at,
                disconnected_at=disconnected_at,
                capabilities_json={},
            )
            session.add(source)
            await session.flush()
            await session.commit()
            return source.id

    async def load_source(source_id):
        async with sessionmaker() as session:
            return await session.get(CalendarSource, source_id)

    cases = [
        (
            "accepted-stale",
            {
                "sync_state": "stale",
                "last_successful_sync_at": now - timedelta(days=2),
            },
            "accepted",
            "Синхронизация поставлена в очередь",
        ),
        ("already-running", {"sync_state": "syncing"}, "already_running", "Синхронизация уже идет"),
        ("provider-failed", {"sync_state": "provider_unavailable"}, "failed", "Синхронизация не запущена"),
        (
            "needs-action",
            {"connection_state": "needs_action", "sync_state": "credential_failed"},
            "reconnect_required",
            "Нужно действие",
        ),
        ("disabled", {"connection_state": "disabled"}, "unavailable", "Синхронизация недоступна"),
        (
            "disconnected",
            {"connection_state": "disconnected", "disconnected_at": now},
            "unavailable",
            "Синхронизация недоступна",
        ),
    ]

    seen_source_ids = []
    for name, source_kwargs, expected_result, expected_notice in cases:
        source_id = asyncio.run(seed_source(name, **source_kwargs))
        seen_source_ids.append(source_id)

        started = perf_counter()
        response = client.post(
            f"/settings/integrations/calendar/sources/{source_id}/sync",
            headers=auth_headers(),
            follow_redirects=False,
        )
        elapsed = perf_counter() - started

        assert elapsed < 2
        assert response.status_code == 303
        assert (
            response.headers["location"]
            == f"/settings/integrations/calendar?sync_result={expected_result}"
        )
        rendered = client.get(response.headers["location"], headers=auth_headers())
        assert rendered.status_code == 200
        assert expected_notice in rendered.text
        assert "raw_provider_payload" not in rendered.text
        assert "access_token" not in rendered.text

    accepted = asyncio.run(load_source(seen_source_ids[0]))
    already_running = asyncio.run(load_source(seen_source_ids[1]))
    provider_failed = asyncio.run(load_source(seen_source_ids[2]))
    disconnected = asyncio.run(load_source(seen_source_ids[5]))

    assert accepted.sync_state == "queued"
    assert accepted.last_sync_started_at is not None
    assert accepted.last_successful_sync_at is not None
    assert already_running.sync_state == "syncing"
    assert provider_failed.sync_state == "provider_unavailable"
    assert disconnected.sync_state == "failed_closed"

    async def load_sync_audit_events() -> list[CalendarAuditEvent]:
        async with sessionmaker() as session:
            return list(
                await session.scalars(
                    select(CalendarAuditEvent)
                    .where(CalendarAuditEvent.event_type.like("calendar_manual_sync_%"))
                    .order_by(CalendarAuditEvent.created_at.asc())
                )
            )

    events = asyncio.run(load_sync_audit_events())
    result_events = [event for event in events if event.event_type == "calendar_manual_sync_result"]

    assert len(events) == len(cases) * 2
    assert len(result_events) == len(cases)
    assert [event.safe_reason_code for event in result_events] == [
        None,
        "already_running",
        "failed",
        "reconnect_required",
        "unavailable",
        "unavailable",
    ]
    assert "access_token" not in str(events)
    assert "raw_provider_payload" not in str(events)


def test_calendar_settings_disconnect_stops_future_contribution_purges_credentials_and_audits(
    client,
) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "display_label": "Рабочий календарь",
            "username": "owner@example.test",
            "credential_input": "secret-app-password",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    assert created.status_code == 201
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]
    now = datetime.now(UTC)

    async def seed_future_event_and_running_sync() -> None:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            source.sync_state = "syncing"
            calendar = await session.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source_id)
            )
            event = CalendarEventSnapshot(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source_id,
                external_calendar_id=calendar.id,
                provider_event_id="future-after-disconnect",
                starts_at=now + timedelta(hours=2),
                ends_at=now + timedelta(hours=3),
                title="Future calendar event",
                privacy_class="public",
                source_status="confirmed",
                conference_summary_json={"meeting_link_present": True},
                attachments_metadata_json=[],
                provider_extras_json={},
                safe_to_show_in_list=True,
                safe_to_use_as_title=True,
                sensitivity_reasons_json=[],
            )
            session.add(event)
            await session.commit()

    asyncio.run(seed_future_event_and_running_sync())

    response = client.post(
        f"/settings/integrations/calendar/sources/{source_id}/disconnect",
        headers=auth_headers(),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["location"] == "/settings/integrations/calendar?disconnect_result=success"
    )
    rendered = client.get(response.headers["location"], headers=auth_headers())
    assert "Календарь отключен" in rendered.text
    assert "Future calendar event" not in rendered.text
    assert "secret-app-password" not in rendered.text

    async def load_disconnect_state() -> tuple[
        CalendarSource, CalendarCredentialEnvelope, int, list[CalendarAuditEvent]
    ]:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            credential = await session.scalar(
                select(CalendarCredentialEnvelope).where(
                    CalendarCredentialEnvelope.calendar_source_id == source_id
                )
            )
            future_event_count = await session.scalar(
                select(func.count())
                .select_from(CalendarEventSnapshot)
                .where(CalendarEventSnapshot.calendar_source_id == source_id)
            )
            events = list(
                await session.scalars(
                    select(CalendarAuditEvent)
                    .where(CalendarAuditEvent.event_type.like("calendar_disconnect_%"))
                    .order_by(CalendarAuditEvent.created_at.asc())
                )
            )
            return source, credential, int(future_event_count or 0), events

    source, credential, future_event_count, events = asyncio.run(load_disconnect_state())

    assert source.connection_state == "disconnected"
    assert source.credential_state == "purged"
    assert source.sync_state == "failed_closed"
    assert credential.revoked_at is not None
    assert credential.purged_at is not None
    assert future_event_count == 0
    assert [event.event_type for event in events] == [
        "calendar_disconnect_confirmed",
        "calendar_disconnect_result",
    ]
    assert events[-1].outcome == "completed"
    assert "secret-app-password" not in str(events)
    assert "raw_provider_payload" not in str(events)


def test_calendar_settings_disconnect_partial_feedback_is_safe(client) -> None:
    rendered = client.get(
        "/settings/integrations/calendar?disconnect_result=partial&provider_error=raw_provider_payload",
        headers=auth_headers(),
    )

    assert rendered.status_code == 200
    assert "Отключение выполнено частично" in rendered.text
    assert "Будущая синхронизация остановлена" in rendered.text
    assert "raw_provider_payload" not in rendered.text
