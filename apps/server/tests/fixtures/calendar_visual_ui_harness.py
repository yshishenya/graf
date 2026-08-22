"""Synthetic browser harness for the calendar settings and home surfaces.

The harness renders production templates and assets without provider credentials
or private event content. It is intentionally test-only and never imports live
calendar data.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from tests.fixtures.calendar_settings import (
    calendar_settings_calendar,
    calendar_settings_snapshot,
    calendar_settings_source,
)
from twobrain_rec_server.api.schemas import MeetingFilterState, MeetingListResponse
from twobrain_rec_server.cabinet.rendering import (
    calendar_settings_notice_codes,
    render_calendar_settings_page,
    render_meeting_list_page,
)
from twobrain_rec_server.cabinet.view_models import AccountProfileView, calendar_settings_surface
from twobrain_rec_server.calendar.capabilities import provider_preset_payloads

app = FastAPI()
app.mount(
    "/static/cabinet",
    StaticFiles(directory="src/twobrain_rec_server/cabinet/static/cabinet"),
    name="calendar-harness-static",
)


def _surface(mode: str, request: Request):
    now = datetime.now(UTC)
    notices = calendar_settings_notice_codes(
        connect_result=request.query_params.get("connect_result"),
        selection_result=request.query_params.get("selection_result"),
        preferences_result=request.query_params.get("preferences_result"),
        sync_result=request.query_params.get("sync_result"),
        disconnect_result=request.query_params.get("disconnect_result"),
    )
    if mode == "empty":
        return calendar_settings_surface(
            provider_payloads=provider_preset_payloads(google_available=True),
            sources=[],
            notice_codes=notices,
            now=now,
        )

    sync_state = {
        "syncing": "syncing",
        "stale": "failed",
        "credentials": "credential_failed",
    }.get(mode, "synced")
    source = calendar_settings_source(
        provider_family="google_calendar",
        provider_label="Google Calendar",
        auth_mode="oauth",
        sync_state=sync_state,
        selected_calendar_count=0 if mode in {"selection", "selection-limit"} else 2,
        last_successful_sync_at=(
            now - timedelta(hours=26) if mode == "stale" else now - timedelta(minutes=8)
        ),
    )
    if mode == "credentials":
        source.last_safe_error_code = "invalid_credentials"
    if mode == "selection-limit":
        calendars = [
            calendar_settings_calendar(
                source,
                provider_calendar_id=f"synthetic-calendar-{index}",
                display_label=f"Тестовый календарь {index}",
                selected=False,
            )
            for index in range(1, 22)
        ]
        return calendar_settings_surface(
            provider_payloads=provider_preset_payloads(google_available=True),
            sources=[source],
            calendars_by_source={source.id: calendars},
            now=now,
        )
    work = calendar_settings_calendar(
        source,
        provider_calendar_id="synthetic-work",
        display_label="Рабочие встречи",
        selected=mode != "selection",
    )
    team = calendar_settings_calendar(
        source,
        provider_calendar_id="synthetic-team",
        display_label="Командный календарь",
        selected=mode != "selection",
        visibility="shared",
    )
    archive = calendar_settings_calendar(
        source,
        provider_calendar_id="synthetic-archive",
        display_label="Недоступный архив",
        selected=False,
        visibility="unavailable",
    )
    events = ()
    if mode not in {"selection", "credentials"}:
        events = (
            calendar_settings_snapshot(
                source,
                work,
                title="Синтетический проектный синк",
                starts_at=now + timedelta(minutes=35),
                provider_event_id="synthetic-project-sync",
                open_meeting_available=True,
            ),
            calendar_settings_snapshot(
                source,
                team,
                title="Синтетическое обсуждение",
                starts_at=now + timedelta(hours=2),
                provider_event_id="synthetic-review",
                meeting_link_present=False,
            ),
        )
    return calendar_settings_surface(
        provider_payloads=provider_preset_payloads(google_available=True),
        sources=[source],
        calendars_by_source={source.id: [work, team, archive]},
        preview_events=events,
        notice_codes=notices,
        now=now,
    )


def _mode(request: Request) -> str:
    return request.query_params.get("mode", "connected")


def _profile(request: Request) -> AccountProfileView:
    theme = request.query_params.get("theme", "dark")
    return AccountProfileView(display_name="Синтетический пользователь", theme=theme)


def _meeting_response() -> MeetingListResponse:
    return MeetingListResponse(
        items=[],
        filters=MeetingFilterState(q=None, status=None, access=None, sort="started_desc"),
        generated_at=datetime.now(UTC),
    )


@app.get("/meetings", response_class=HTMLResponse)
@app.get("/desktop/meetings", response_class=HTMLResponse)
async def meetings(request: Request) -> HTMLResponse:
    embedded = request.url.path.startswith("/desktop/")
    return HTMLResponse(
        render_meeting_list_page(
            _meeting_response(),
            embedded=embedded,
            calendar_surface=_surface(_mode(request), request),
            display_timezone="Europe/Moscow",
            csrf_token="synthetic-csrf",
            profile=_profile(request),
        )
    )


@app.get("/settings/integrations/calendar", response_class=HTMLResponse)
@app.get("/desktop/settings/integrations/calendar", response_class=HTMLResponse)
async def settings(request: Request) -> HTMLResponse:
    return HTMLResponse(
        render_calendar_settings_page(
            _surface(_mode(request), request),
            embedded=request.url.path.startswith("/desktop/"),
            csrf_token="synthetic-csrf",
            profile=_profile(request),
        )
    )


@app.post("/{path:path}")
async def mutation(path: str) -> RedirectResponse:
    prefix = "/desktop" if path.startswith("desktop/") else ""
    target = f"{prefix}/settings/integrations/calendar"
    if path.endswith("/disconnect"):
        return RedirectResponse(f"{target}?mode=empty&disconnect_result=success", status_code=303)
    if path.endswith("/sync"):
        return RedirectResponse(f"{target}?mode=syncing&sync_result=accepted", status_code=303)
    if path.endswith("/calendars"):
        return RedirectResponse(f"{target}?mode=connected&selection_result=saved", status_code=303)
    if path.endswith("/preferences"):
        return RedirectResponse(
            f"{target}?mode=connected&preferences_result=saved", status_code=303
        )
    return RedirectResponse(f"{target}?mode=selection&connect_result=success", status_code=303)
