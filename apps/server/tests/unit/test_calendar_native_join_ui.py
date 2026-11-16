"""Connect the real shared calendar renderer to the Windows document shim."""
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from tests.fixtures.calendar_settings import (
    calendar_settings_calendar,
    calendar_settings_snapshot,
    calendar_settings_source,
)
from twobrain_rec_server.api.schemas import MeetingFilterState, MeetingListResponse
from twobrain_rec_server.cabinet.rendering import _render_home_upcoming
from twobrain_rec_server.cabinet.view_models import calendar_settings_surface


@pytest.mark.browser
@pytest.mark.parametrize("embedded", [False, True])
def test_actual_calendar_join_reaches_native_shim_and_preserves_link_dispatch(embedded: bool) -> None:
    now = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
    source = calendar_settings_source(last_successful_sync_at=now)
    calendar = calendar_settings_calendar(source=source, selected=True)
    event = calendar_settings_snapshot(
        source=source, calendar=calendar, starts_at=now, open_meeting_available=True,
    )
    event.id = UUID("abcdefab-1234-4567-89ab-abcdefabcdef")
    surface = calendar_settings_surface(
        provider_payloads=[], sources=[source], calendars_by_source={source.id: [calendar]},
        preview_events=[event], now=now,
    )
    response = MeetingListResponse(
        items=[], filters=MeetingFilterState(q=None, status=None, access=None, sort="started_desc"),
        generated_at=now,
    )
    html = _render_home_upcoming(
        response, calendar_surface=surface, embedded=embedded, display_timezone="Europe/Moscow",
    )
    empty = _render_home_upcoming(
        response, calendar_surface=calendar_settings_surface(
            provider_payloads=[], sources=[], calendars_by_source={}, preview_events=[], now=now,
        ), embedded=embedded, display_timezone="Europe/Moscow",
    )
    script = Path(__file__).parents[3] / "windows/Tests/GrafWindowsContractTests/CalendarJoinShimTests.cjs"
    subprocess.run(
        ["node", str(script), "--rendered"],
        input=json.dumps({"upcoming": html, "empty": empty}),
        text=True, check=True, timeout=60,
    )
