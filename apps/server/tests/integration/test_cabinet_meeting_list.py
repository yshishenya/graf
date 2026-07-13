import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.artifacts import deterministic_wav_bytes
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    add_workspace_user,
    set_meeting_visibility,
)
from tests.fixtures.cabinet_access import (
    auth_headers_for as shared_auth_headers,
)
from twobrain_rec_server.cabinet.templates import CABINET_STATIC_URL
from twobrain_rec_server.db.models import Meeting, RecordingCalendarContextLink
from twobrain_rec_server.domain.statuses import MeetingStatus, ProcessingStatus


def test_cabinet_list_returns_only_authorized_workspace_meetings(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get("/api/v1/cabinet/meetings", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    ids = {item["meeting_id"] for item in payload["items"]}
    assert str(seeds.ready_id) in ids
    assert str(seeds.processing_id) in ids
    assert str(seeds.failed_id) in ids
    assert str(seeds.partial_id) in ids
    assert str(seeds.foreign_id) not in ids
    assert {item["status"] for item in payload["items"]} == {
        "ready",
        "processing",
        "failed",
        "partial",
    }


def test_cabinet_list_shows_server_upload_progress_for_active_recording(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "cabinet-upload-progress", "duration_seconds": 60},
    )
    assert meeting.status_code == 200
    meeting_id = meeting.json()["meeting_id"]
    session = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 8, "microphone": 16, "system": 16}},
    )
    assert session.status_code == 200
    session_id = session.json()["session_id"]
    data = deterministic_wav_bytes(16)
    digest = sha256(data).hexdigest()
    upload = client.put(
        f"/api/v1/upload-sessions/{session_id}/tracks/microphone/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )
    assert upload.status_code == 200

    response = client.get(
        "/api/v1/cabinet/meetings?q=cabinet-upload-progress", headers=auth_headers()
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["status"] == "uploading"
    assert item["upload"] == {
        "status": "uploading",
        "label": "Отправляем",
        "uploaded_bytes": 16,
        "total_bytes": 40,
        "progress_percent": 40,
        "is_active": True,
    }

    page = client.get("/desktop/meetings?q=cabinet-upload-progress", headers=auth_headers())

    assert page.status_code == 200
    assert "cabinet-upload-progress" in page.text
    assert "Отправляем 40%" in page.text
    assert 'aria-label="Прогресс отправки записи"' in page.text
    assert 'hx-trigger="every 3s"' in page.text


def test_cabinet_list_shows_manual_upload_as_normal_meeting_row(client) -> None:
    upload = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Manual list row",
            "duration_seconds": "90",
            "local_recording_id": "manual-list-row",
        },
        files={"file": ("meeting.wav", deterministic_wav_bytes(72), "audio/wav")},
    )
    assert upload.status_code == 202
    meeting_id = upload.json()["meeting"]["meeting_id"]

    response = client.get("/api/v1/cabinet/meetings?q=Manual%20list%20row", headers=auth_headers())
    page = client.get("/meetings?q=Manual%20list%20row", headers=auth_headers())

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["meeting_id"] == meeting_id
    assert item["title"] == "Manual list row"
    assert item["source"] == "manual_upload"
    assert item["duration_seconds"] == 90
    assert item["status"] == "submitted"
    assert item["primary_action"] == "wait"
    assert page.status_code == 200
    assert "Manual list row" in page.text
    assert 'data-media-kind="медиа"' in page.text


def test_desktop_empty_meeting_list_polls_for_new_local_uploads(client) -> None:
    response = client.get("/desktop/meetings?q=missing-local-upload", headers=auth_headers())

    assert response.status_code == 200
    assert "Нет встреч для выбранного фильтра." in response.text
    assert 'hx-trigger="every 3s"' in response.text
    assert 'hx-get="/desktop/meetings?q=missing-local-upload"' in response.text


def test_cabinet_list_search_filter_sort_and_limit(client) -> None:
    seed_cabinet_meetings(client)
    legacy = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "sort-legacy-no-date", "duration_seconds": 60},
    )
    assert legacy.status_code == 200
    unsafe_legacy_id = uuid4()
    visible_title_id = uuid4()

    async def seed_title_sort_regression_rows() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    Meeting(
                        id=unsafe_legacy_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id="aaa-visible-fallback",
                        title="zzzz https://example.com/?token=secret",
                        started_at=datetime(2026, 6, 26, 8, 0, tzinfo=UTC),
                        duration_seconds=60,
                        status=MeetingStatus.DRAFT.value,
                        processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                    ),
                    Meeting(
                        id=visible_title_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id="bbb-visible-title",
                        title="bbb-visible-title",
                        started_at=datetime(2026, 6, 26, 9, 0, tzinfo=UTC),
                        duration_seconds=60,
                        status=MeetingStatus.DRAFT.value,
                        processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                    ),
                ]
            )
            await db.commit()

    client.portal.call(seed_title_sort_regression_rows)

    search = client.get("/api/v1/cabinet/meetings?q=релиза", headers=auth_headers())
    ready = client.get("/api/v1/cabinet/meetings?status=ready", headers=auth_headers())
    shortest = client.get(
        "/api/v1/cabinet/meetings?sort=duration_asc&limit=2", headers=auth_headers()
    )
    recording_newest = client.get(
        "/api/v1/cabinet/meetings?sort=started_desc", headers=auth_headers()
    )
    recording_oldest = client.get(
        "/api/v1/cabinet/meetings?sort=started_asc", headers=auth_headers()
    )
    title_sorted = client.get("/api/v1/cabinet/meetings?sort=title_asc", headers=auth_headers())

    assert search.status_code == 200
    assert [item["title"] for item in search.json()["items"]] == ["Планирование релиза"]
    assert ready.status_code == 200
    assert [item["status"] for item in ready.json()["items"]] == ["ready"]
    assert shortest.status_code == 200
    durations = [item["duration_seconds"] for item in shortest.json()["items"]]
    assert durations == sorted(durations)
    assert len(durations) == 2
    assert recording_newest.status_code == 200
    newest_dates = [item["started_at"] for item in recording_newest.json()["items"]]
    newest_recorded_dates = [value for value in newest_dates if value is not None]
    assert newest_dates[-1] is None
    assert newest_recorded_dates == sorted(newest_recorded_dates, reverse=True)
    assert recording_oldest.status_code == 200
    oldest_dates = [item["started_at"] for item in recording_oldest.json()["items"]]
    oldest_recorded_dates = [value for value in oldest_dates if value is not None]
    assert oldest_dates[-1] is None
    assert oldest_recorded_dates == sorted(oldest_recorded_dates)
    assert title_sorted.status_code == 200
    titles = [item["title"] for item in title_sorted.json()["items"]]
    assert titles == sorted(titles)
    assert titles.index("aaa-visible-fallback") < titles.index("bbb-visible-title")


def test_cabinet_list_and_detail_use_recording_date_with_legacy_fallback(client) -> None:
    seeds = seed_cabinet_meetings(client)
    legacy = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "legacy-no-recording-date", "duration_seconds": 60},
    )
    assert legacy.status_code == 200

    detail = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())
    legacy_list = client.get(
        "/api/v1/cabinet/meetings?q=legacy-no-recording-date", headers=auth_headers()
    )
    legacy_web = client.get("/meetings?q=legacy-no-recording-date", headers=auth_headers())

    assert detail.status_code == 200
    assert detail.json()["meeting"]["started_at"].startswith("2026-06-16T08:00:00")
    assert legacy_list.status_code == 200
    legacy_item = legacy_list.json()["items"][0]
    assert legacy_item["title"] == "legacy-no-recording-date"
    assert legacy_item["started_at"] is None
    assert legacy_web.status_code == 200
    assert "legacy-no-recording-date" in legacy_web.text
    assert "Без даты" in legacy_web.text


def test_cabinet_list_uses_recording_display_timezone_offset_for_date_label(client) -> None:
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "timezone-offset-label",
            "title": "Meeting - 2026-06-27 00:30",
            "started_at": "2026-06-26T21:30:00Z",
            "recording_display_timezone_offset_minutes": 180,
            "duration_seconds": 60,
        },
    )
    assert response.status_code == 200

    page = client.get("/meetings?q=timezone-offset-label", headers=auth_headers())

    assert page.status_code == 200
    assert "27 июн" in page.text


def test_cabinet_list_web_shell_renders_reference_informed_controls(client) -> None:
    seed_cabinet_meetings(client)

    response = client.get("/meetings", headers=auth_headers())

    assert response.status_code == 200
    assert "Мои встречи" in response.text
    assert "Ближайшие" in response.text
    assert "Ближайшие встречи появятся после подключения календаря." in response.text
    assert 'href="/settings/integrations/calendar"' in response.text
    assert "Подключить календари" in response.text
    assert "Командный синк" not in response.text
    assert "Записи встреч" in response.text
    assert "<span>Загрузить</span>" in response.text
    assert "Загрузить медиа" not in response.text
    assert "Фильтры" in response.text
    assert "Сортировка" in response.text
    assert 'value="started_desc"' in response.text
    assert 'value="started_asc"' in response.text
    assert "Новые по дате записи" in response.text
    assert "Проектный синк" in response.text
    assert "data-cabinet-shell" in response.text
    assert "data-cabinet-navigation" in response.text
    assert response.text.count('id="cabinet-sidebar" data-cabinet-navigation') == 1
    assert response.text.count('aria-label="Навигация кабинета"') == 1
    assert response.text.count('aria-current="page"') == 1
    assert 'data-active-nav="meetings"' in response.text
    assert 'id="meeting-list-region"' in response.text
    assert 'class="cabinet-list-controls"' in response.text
    assert 'method="get"' in response.text
    assert 'data-hx-target="#meeting-list-region"' in response.text
    assert 'data-hx-select="#meeting-list-region"' in response.text
    assert f'href="{CABINET_STATIC_URL}/cabinet.css?v=' in response.text
    assert "<!doctype html>" in response.text
    assert "<style>" not in response.text


def test_cabinet_list_full_page_fallback_without_hx_header(client) -> None:
    seed_cabinet_meetings(client)

    response = client.get("/meetings?sort=duration_asc", headers=auth_headers())

    assert response.status_code == 200
    assert "<!doctype html>" in response.text
    assert "data-cabinet-shell" in response.text
    assert 'data-cabinet-fragment="meeting-list"' in response.text
    assert response.headers.get("Vary") != "HX-Request"


def test_cabinet_list_api_exposes_governance_future_slots_and_artifact_truth(client) -> None:
    seed_cabinet_meetings(client)

    response = client.get("/api/v1/cabinet/meetings", headers=auth_headers())

    assert response.status_code == 200
    item = next(row for row in response.json()["items"] if row["title"] == "Проектный синк")
    assert item["access"]["state"] == "owner"
    assert item["governance"]["share"]["state"] == "available"
    assert item["governance"]["delete"]["state"] == "planned"
    assert {slot["label"] for slot in item["future_slots"]} >= {"Star", "Tag", "Access", "More"}
    assert item["notes_available"] is False
    assert "storage_object_key" not in response.text


def test_desktop_embedded_list_keeps_review_workspace_but_hides_native_creation_controls(
    client,
) -> None:
    seed_cabinet_meetings(client)

    response = client.get("/desktop/meetings", headers=auth_headers())

    assert response.status_code == 200
    assert "desktop-embedded" in response.text
    assert "data-cabinet-shell" in response.text
    assert "data-cabinet-navigation" in response.text
    assert response.text.count('id="cabinet-sidebar" data-cabinet-navigation') == 1
    assert response.text.count('aria-current="page"') == 1
    assert 'data-active-nav="meetings"' in response.text
    assert 'href="/desktop/meetings"' in response.text
    assert 'href="/desktop/settings/integrations/calendar"' in response.text
    assert 'href="/meetings"' not in response.text
    assert f'href="{CABINET_STATIC_URL}/cabinet.css?v=' in response.text
    assert "Записи встреч" in response.text
    assert "Проектный синк" in response.text
    assert "<style>" not in response.text
    assert "Upload file" not in response.text
    assert "Record live" not in response.text
    assert "Screen Recording" not in response.text


def test_098_recurring_pointer_has_browser_and_embedded_meeting_list_route_parity(
    client,
) -> None:
    # FR-024/FR-026/FR-048: one server-owned pointer backs browser and embedded lists.
    previous_id = _create_recurring_list_pair(client)
    responses = {
        "web": client.get(
            "/meetings?q=t082-recurring-current",
            headers=auth_headers(),
        ),
        "embedded": client.get(
            "/desktop/meetings?q=t082-recurring-current",
            headers=auth_headers(),
        ),
    }
    expected_hrefs = {
        "web": f'href="/meetings/{previous_id}"',
        "embedded": f'href="/desktop/meetings/{previous_id}"',
    }

    for surface, response in responses.items():
        assert response.status_code == 200, surface
        upcoming = _upcoming_section(response.text)
        assert upcoming.count("Synthetic T082 Current") == 1, surface
        assert upcoming.count("Предыдущая встреча") == 1, surface
        assert upcoming.count("Synthetic T082 Previous") == 1, surface
        assert expected_hrefs[surface] in upcoming, surface
        assert "summary excerpt" not in upcoming
        assert "transcript excerpt" not in upcoming


def test_cabinet_settings_calendar_anchor_renders_in_web_and_embedded(client) -> None:
    web = client.get("/settings", headers=auth_headers())
    embedded = client.get("/desktop/settings", headers=auth_headers())

    assert web.status_code == 200
    assert embedded.status_code == 200
    assert 'data-active-nav="settings"' in web.text
    assert 'id="calendar-connections"' in web.text
    assert 'href="/settings/integrations/calendar"' in web.text
    assert "Подключить календари" in web.text
    assert "desktop-embedded" in embedded.text
    assert 'href="/desktop/settings/integrations/calendar"' in embedded.text


def test_098_ambiguous_owner_list_has_compact_choose_action_in_web_and_embedded(client) -> None:
    # FR-014/FR-033/FR-043/FR-048; SC-003/SC-012/SC-013: ambiguity is visible but never auto-selected.
    meeting_id = _create_ambiguous_list_meeting(
        client, local_recording_id="t050-owner-ambiguous-list"
    )
    responses = {
        "web": client.get(
            "/meetings?q=t050-owner-ambiguous-list",
            headers=auth_headers(),
        ),
        "embedded": client.get(
            "/desktop/meetings?q=t050-owner-ambiguous-list",
            headers=auth_headers(),
        ),
    }

    for surface, response in responses.items():
        assert response.status_code == 200, surface
        assert response.text.count("Нужно выбрать встречу") == 1, surface
        assert (
            response.text.count(
                '<span class="mini-link calendar-context-list-action">Выбрать</span>'
            )
            == 1
        ), surface
        assert 'data-calendar-context-state="ambiguous"' in response.text, surface
        assert "Synthetic hidden candidate A" not in response.text
        assert "Synthetic hidden candidate B" not in response.text
    assert f'href="/meetings/{meeting_id}#calendar-context-chooser"' in responses["web"].text
    assert (
        f'href="/desktop/meetings/{meeting_id}#calendar-context-chooser"'
        in responses["embedded"].text
    )


def test_098_ambiguous_non_owner_list_is_generic_and_has_no_choose_action(client) -> None:
    # FR-033/FR-037; SC-011/SC-013: non-owner list text and accessible HTML reveal no ambiguity.
    meeting_id = _create_ambiguous_list_meeting(
        client, local_recording_id="t050-shared-context-list"
    )
    add_workspace_user(client)
    set_meeting_visibility(client, meeting_id, "team")

    for path in (
        "/meetings?q=t050-shared-context-list",
        "/desktop/meetings?q=t050-shared-context-list",
    ):
        response = client.get(path, headers=shared_auth_headers())
        assert response.status_code == 200, path
        assert response.text.count("Без календарного контекста") == 1, path
        assert "Нужно выбрать встречу" not in response.text
        assert "calendar-context-list-action" not in response.text
        assert "ambiguous" not in response.text
        assert "multiple_time_candidates" not in response.text


def _create_ambiguous_list_meeting(client, *, local_recording_id: str) -> UUID:
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "title": local_recording_id,
            "started_at": "2026-07-13T09:10:00Z",
            "ended_at": "2026-07-13T09:40:00Z",
            "duration_seconds": 1800,
        },
    )
    assert response.status_code == 200
    meeting_id = UUID(response.json()["meeting_id"])

    async def mark_ambiguous() -> None:
        async with client.app_state["sessionmaker"]() as db:
            context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                    RecordingCalendarContextLink.meeting_id == meeting_id,
                )
            )
            assert context is not None
            context.calendar_event_snapshot_id = None
            context.context_state = "ambiguous"
            context.context_confidence = "ambiguous"
            context.context_reasons_json = ["multiple_time_candidates"]
            context.title_source = "generic"
            context.roster_source = "none"
            context.manual_override_state = "none"
            context.safe_reason_code = "multiple_time_candidates"
            context.decision_source = "automatic"
            context.matcher_version = "calendar_auto_match_v1"
            context.evaluated_at = datetime(2026, 7, 13, 9, 10, tzinfo=UTC)
            context.candidate_event_ids_json = []
            context.candidate_count = 2
            context.matched_title = None
            context.matched_title_state = "unavailable"
            context.matched_roster_json = []
            context.matched_roster_state = "not_available"
            context.matched_roster_count = 0
            await db.commit()

    asyncio.run(mark_ambiguous())
    return meeting_id


def _create_recurring_list_pair(client) -> UUID:
    current_starts_at = datetime.now(UTC).replace(microsecond=0) + timedelta(minutes=30)
    previous_starts_at = current_starts_at - timedelta(days=7)
    previous = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "t082-recurring-previous",
            "title": "Synthetic T082 Previous",
            "title_source": "app_context",
            "started_at": previous_starts_at.isoformat(),
            "ended_at": (previous_starts_at + timedelta(minutes=30)).isoformat(),
            "duration_seconds": 1800,
        },
    )
    current = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "t082-recurring-current",
            "title": "Synthetic T082 Current",
            "title_source": "app_context",
            "started_at": current_starts_at.isoformat(),
            "ended_at": (current_starts_at + timedelta(minutes=30)).isoformat(),
            "duration_seconds": 1800,
        },
    )
    assert previous.status_code == 200
    assert current.status_code == 200
    previous_id = UUID(previous.json()["meeting_id"])
    current_id = UUID(current.json()["meeting_id"])
    series_key = sha256(b"synthetic-t082-recurring-series").hexdigest()

    async def mark_recurring() -> None:
        async with client.app_state["sessionmaker"]() as db:
            contexts = list(
                await db.scalars(
                    select(RecordingCalendarContextLink).where(
                        RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                        RecordingCalendarContextLink.meeting_id.in_([previous_id, current_id]),
                    )
                )
            )
            assert len(contexts) == 2
            starts_at_by_meeting = {
                previous_id: previous_starts_at,
                current_id: current_starts_at,
            }
            title_by_meeting = {
                previous_id: "Synthetic T082 Previous",
                current_id: "Synthetic T082 Current",
            }
            for context in contexts:
                starts_at = starts_at_by_meeting[context.meeting_id]
                context.context_state = "matched_auto"
                context.context_confidence = "high"
                context.context_reasons_json = ["synthetic_recurring_match"]
                context.title_source = "calendar"
                context.roster_source = "none"
                context.manual_override_state = "none"
                context.safe_reason_code = "single_fresh_candidate"
                context.decision_source = "automatic"
                context.matcher_version = "calendar_auto_match_v1"
                context.evaluated_at = starts_at
                context.candidate_event_ids_json = []
                context.candidate_count = 0
                context.matched_event_starts_at = starts_at
                context.matched_event_ends_at = starts_at + timedelta(minutes=30)
                context.matched_title = title_by_meeting[context.meeting_id]
                context.matched_title_state = "available"
                context.matched_roster_json = []
                context.matched_roster_state = "not_available"
                context.matched_roster_count = 0
                context.recurring_series_key_sha256 = series_key
                context.source_version_fingerprint_sha256 = sha256(
                    f"synthetic-source-{context.meeting_id}".encode()
                ).hexdigest()
                context.linked_at = starts_at
            await db.commit()

    client.portal.call(mark_recurring)
    return previous_id


def _upcoming_section(html: str) -> str:
    marker = '<section class="upcoming cabinet-card" aria-label="Ближайшие встречи">'
    before, found, after = html.partition(marker)
    assert before or found
    assert found == marker
    section, closing, _ = after.partition("</section>")
    assert closing == "</section>"
    return section
