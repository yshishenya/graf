from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from tests.fixtures.calendar import calendar_event_fixture, private_free_busy_event_fixture
from twobrain_rec_server.db.models import CalendarEventSnapshot, CalendarSource, ExternalCalendar


def calendar_settings_source(
    *,
    provider_family: str = "caldav_yandex",
    provider_label: str = "Яндекс Календарь",
    auth_mode: str = "app_password",
    connection_state: str = "active",
    sync_state: str = "synced",
    selected_calendar_count: int = 0,
    last_successful_sync_at: datetime | None = None,
) -> CalendarSource:
    return CalendarSource(
        id=uuid4(),
        workspace_id=uuid4(),
        owner_user_id=uuid4(),
        provider_family=provider_family,
        provider_label=provider_label,
        auth_mode=auth_mode,
        credential_state="sealed",
        connection_state=connection_state,
        sync_state=sync_state,
        selected_calendar_count=selected_calendar_count,
        last_successful_sync_at=last_successful_sync_at or datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
        capabilities_json={},
    )


def calendar_settings_calendar(
    source: CalendarSource,
    *,
    provider_calendar_id: str = "primary",
    display_label: str = "Рабочий календарь",
    selected: bool = False,
    visibility: str | None = None,
) -> ExternalCalendar:
    return ExternalCalendar(
        id=uuid4(),
        workspace_id=source.workspace_id,
        calendar_source_id=source.id,
        provider_calendar_id=provider_calendar_id,
        display_label=display_label,
        visibility=visibility or "available",
        selected=selected,
    )


def overlap_event_fixtures() -> tuple[dict, dict]:
    first = calendar_event_fixture(
        "caldav_yandex",
        provider_event_id="event-1200-1300",
        starts_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
    )
    second = calendar_event_fixture(
        "caldav_mail_ru",
        provider_event_id="event-1230-1330",
        starts_at=datetime(2026, 7, 1, 12, 30, tzinfo=UTC),
        ends_at=datetime(2026, 7, 1, 13, 30, tzinfo=UTC),
    )
    return first, second


def private_free_busy_settings_fixture() -> dict:
    return private_free_busy_event_fixture("caldav_yandex")


def calendar_settings_snapshot(
    source: CalendarSource,
    calendar: ExternalCalendar,
    *,
    title: str | None = "Synthetic Planning Sync",
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    provider_event_id: str = "synthetic-event",
    meeting_link_present: bool = True,
    safe_to_show: bool = True,
) -> CalendarEventSnapshot:
    start = starts_at or datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    return CalendarEventSnapshot(
        id=uuid4(),
        workspace_id=source.workspace_id,
        calendar_source_id=source.id,
        external_calendar_id=calendar.id,
        provider_event_id=provider_event_id,
        starts_at=start,
        ends_at=ends_at or start + timedelta(hours=1),
        title=title,
        privacy_class="public" if safe_to_show else "private",
        source_status="confirmed",
        conference_summary_json={"meeting_link_present": meeting_link_present},
        attachments_metadata_json=[],
        provider_extras_json={},
        safe_to_show_in_list=safe_to_show,
        safe_to_use_as_title=safe_to_show,
        sensitivity_reasons_json=[] if safe_to_show else ["private"],
    )
