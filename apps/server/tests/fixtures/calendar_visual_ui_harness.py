"""Synthetic browser harness for calendar, cabinet, and automatic-theme auth pages.

The harness renders production templates and assets without provider credentials
or private event content. It is intentionally test-only and never imports live
calendar data.

Run from apps/server with:
    .venv/bin/uvicorn tests.fixtures.calendar_visual_ui_harness:app --host 127.0.0.1

The default meeting list stays empty. Use /meetings?mode=populated&theme=light,
/meetings/synthetic-theme?theme=light, /login, or /login/email/code for theme QA.
Cabinet pages also accept theme=dark/system and the /desktop prefix. Auth pages
intentionally follow the OS theme. Playback serves generated silence, not audio
from a meeting; this harness does not exercise authentication or persistence.
"""

from __future__ import annotations

import wave
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from tests.fixtures.calendar_settings import (
    calendar_settings_calendar,
    calendar_settings_snapshot,
    calendar_settings_source,
)
from tests.unit.test_cabinet_web_shell import _item, _review
from twobrain_rec_server.api.schemas import (
    MeetingFilterState,
    MeetingListItem,
    MeetingListResponse,
    MeetingReviewResponse,
    PlaybackReviewState,
    SpeakerLane,
    SpeakerLaneSegment,
    SpeakerReviewState,
    TranscriptReviewState,
    TranscriptSegmentView,
)
from twobrain_rec_server.cabinet.rendering import (
    calendar_settings_notice_codes,
    render_calendar_settings_page,
    render_email_code_page,
    render_login_page,
    render_meeting_detail_page,
    render_meeting_list_page,
)
from twobrain_rec_server.cabinet.review_policy_rendering import render_meeting_share_fragment
from twobrain_rec_server.cabinet.view_models import AccountProfileView, calendar_settings_surface
from twobrain_rec_server.calendar.capabilities import provider_preset_payloads

SYNTHETIC_MEETING_ID = UUID("00000000-0000-4000-8000-000000000240")
SYNTHETIC_DURATION_SECONDS = 40

app = FastAPI()
app.mount(
    "/static/cabinet",
    StaticFiles(
        directory=Path(__file__).resolve().parents[2]
        / "src/twobrain_rec_server/cabinet/static/cabinet"
    ),
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
    return AccountProfileView(
        display_name="Синтетический пользователь",
        primary_email="theme@example.test",
        theme=theme,
    )


def _ready_item(index: int = 0) -> MeetingListItem:
    item = _item()
    item.meeting_id = UUID(int=SYNTHETIC_MEETING_ID.int + index)
    item.title = (
        "Синтетическая проверка темы",
        "Синтетическая встреча с длинным названием для проверки переноса текста",
        "Синтетическое обсуждение",
    )[index]
    item.started_at = datetime(2026, 9, 6, 8, index * 10, tzinfo=UTC)
    item.duration_seconds = SYNTHETIC_DURATION_SECONDS
    item.ended_at = item.started_at + timedelta(seconds=item.duration_seconds)
    item.status = "ready"
    item.status_label = "Готово"
    item.primary_action = "open"
    item.transcript_available = True
    item.diarization_available = True
    return item


def _meeting_response(mode: str = "empty") -> MeetingListResponse:
    return MeetingListResponse(
        items=[_ready_item(index) for index in range(3)] if mode == "populated" else [],
        filters=MeetingFilterState(q=None, status=None, access=None, sort="started_desc"),
        generated_at=datetime.now(UTC),
    )


def _theme_review(index: int = 0) -> MeetingReviewResponse:
    review = _review()
    review.meeting = _ready_item(index)
    review.activity.meeting_id = review.meeting.meeting_id
    review.processing.state = "ready"
    review.processing.stage = None
    review.processing.next_action = "none"
    review.processing.content_available = True
    review.processing.transcript_available = True
    review.processing.diarization_available = True
    segments = [
        TranscriptSegmentView(
            segment_id=f"synthetic-theme-{number}",
            sequence=number,
            start_seconds=number * 20,
            end_seconds=(number + 1) * 20,
            timestamp_label=f"00:{number * 20:02d}",
            speaker_key=f"synthetic-speaker-{number}",
            speaker_label=label,
            source_role="incoming_system",
            text=text,
            attribution_state="confirmed",
            seekable=True,
            seek_seconds=number * 20,
        )
        for number, (label, text) in enumerate(
            (
                ("Тестовый участник А", "Синтетический текст для проверки читаемости темы."),
                ("Тестовый участник Б", "Проверяем подписи участников и элементы плеера."),
            )
        )
    ]
    review.transcript = TranscriptReviewState(
        available=True, language="ru", search_enabled=True, segments=segments
    )
    review.speakers = SpeakerReviewState(
        available=True,
        assignment_state="available",
        can_rename=True,
        speakers=[
            SpeakerLane(
                speaker_key=segment.speaker_key,
                label=segment.speaker_label,
                talk_time_percent=50,
                source_roles=[segment.source_role],
                segments=[
                    SpeakerLaneSegment(
                        start_seconds=segment.start_seconds, end_seconds=segment.end_seconds
                    )
                ],
            )
            for segment in segments
        ],
    )
    review.playback = PlaybackReviewState(
        available=True,
        duration_seconds=SYNTHETIC_DURATION_SECONDS,
        playback_path="/synthetic/theme.wav",
        policy_label="Синтетическая тишина для проверки плеера",
        source_mode="stored_review_m4a",
        included_sources=["incoming_system"],
    )
    review.meeting.playback = review.playback
    return review


@app.get("/meetings", response_class=HTMLResponse)
@app.get("/desktop/meetings", response_class=HTMLResponse)
async def meetings(request: Request) -> HTMLResponse:
    embedded = request.url.path.startswith("/desktop/")
    return HTMLResponse(
        render_meeting_list_page(
            _meeting_response(_mode(request)),
            embedded=embedded,
            calendar_surface=_surface(_mode(request), request),
            display_timezone="Europe/Moscow",
            csrf_token="synthetic-csrf",
            profile=_profile(request),
        )
    )


@app.get("/meetings/synthetic-theme", response_class=HTMLResponse)
@app.get("/desktop/meetings/synthetic-theme", response_class=HTMLResponse)
@app.get("/meetings/{meeting_id:uuid}", response_class=HTMLResponse)
@app.get("/desktop/meetings/{meeting_id:uuid}", response_class=HTMLResponse)
async def meeting_detail(request: Request) -> HTMLResponse:
    meeting_id = request.path_params.get("meeting_id", SYNTHETIC_MEETING_ID)
    index = meeting_id.int - SYNTHETIC_MEETING_ID.int
    if index not in range(3):
        return HTMLResponse("Синтетическая встреча не найдена", status_code=404)
    return HTMLResponse(
        render_meeting_detail_page(
            _theme_review(index),
            embedded=request.url.path.startswith("/desktop/"),
            csrf_token="synthetic-csrf",
            profile=_profile(request),
        )
    )


@app.get(f"/meetings/{SYNTHETIC_MEETING_ID}/share", response_class=HTMLResponse)
@app.get(f"/desktop/meetings/{SYNTHETIC_MEETING_ID}/share", response_class=HTMLResponse)
async def meeting_share() -> HTMLResponse:
    return HTMLResponse(render_meeting_share_fragment(_theme_review()))


@app.get("/synthetic/theme.wav")
async def synthetic_silence() -> Response:
    with BytesIO() as buffer:
        with wave.open(buffer, "wb") as audio:
            audio.setparams((1, 1, 8000, 0, "NONE", "not compressed"))
            audio.writeframes(b"\x80" * 8000 * SYNTHETIC_DURATION_SECONDS)
        return Response(buffer.getvalue(), media_type="audio/wav")


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request) -> HTMLResponse:
    return HTMLResponse(
        render_login_page(
            workspace_id=SYNTHETIC_MEETING_ID,
            providers=[],
            next_path="/meetings?mode=populated",
            error=request.query_params.get("error"),
        )
    )


@app.get("/login/email/code", response_class=HTMLResponse)
async def email_code(request: Request) -> HTMLResponse:
    return HTMLResponse(
        render_email_code_page(
            email="theme@example.test",
            state_nonce="synthetic-email-state",
            next_path="/meetings?mode=populated",
            error=request.query_params.get("error"),
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
