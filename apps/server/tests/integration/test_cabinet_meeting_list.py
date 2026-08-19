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
from twobrain_rec_server.db.models import (
    Meeting,
    RecordingCalendarContextLink,
    UploadSession,
)
from twobrain_rec_server.domain.statuses import (
    MeetingStatus,
    ProcessingStatus,
    UploadSessionStatus,
)


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


def test_browser_and_embedded_lists_default_to_started_desc_and_normalize_unknown_sort(
    client,
) -> None:
    seed_cabinet_meetings(client)

    for route in ("/meetings", "/desktop/meetings"):
        default_page = client.get(route, headers=auth_headers())
        unknown_page = client.get(
            route,
            params={"sort": "unknown"},
            headers=auth_headers(),
            follow_redirects=False,
        )
        unknown_htmx_page = client.get(
            route,
            params={"sort": "unknown"},
            headers={**auth_headers(), "HX-Request": "true"},
        )
        updated_page = client.get(
            route,
            params={"sort": "updated_desc"},
            headers=auth_headers(),
        )
        oldest_updated_page = client.get(
            route,
            params={"sort": "updated_asc"},
            headers=auth_headers(),
        )

        assert default_page.status_code == 200
        assert 'aria-label="Сортировка: Сначала новые"' in default_page.text
        assert 'value="started_desc" selected' in default_page.text
        assert unknown_page.status_code == 303
        assert unknown_page.headers["location"] == f"{route}?sort=started_desc"
        canonical_page = client.get(unknown_page.headers["location"], headers=auth_headers())
        assert canonical_page.status_code == 200
        assert 'aria-label="Сортировка: Сначала новые"' in canonical_page.text
        assert 'value="started_desc" selected' in canonical_page.text
        assert unknown_htmx_page.status_code == 200
        assert unknown_htmx_page.headers["HX-Replace-Url"] == f"{route}?sort=started_desc"
        assert f'hx-get="{route}?sort=started_desc"' in unknown_htmx_page.text
        assert updated_page.status_code == 200
        assert 'aria-label="Сортировка: Недавно обновлённые"' in updated_page.text
        assert 'value="updated_desc" selected' in updated_page.text
        assert oldest_updated_page.status_code == 200
        assert 'aria-label="Сортировка: Давно обновлённые"' in oldest_updated_page.text
        assert 'value="updated_asc" selected' in oldest_updated_page.text


def test_browser_lists_normalize_legacy_status_urls_and_reject_hidden_access(client) -> None:
    seed_cabinet_meetings(client)

    for route in ("/meetings", "/desktop/meetings"):
        legacy_status = client.get(
            route,
            params={"status": "uploading"},
            headers=auth_headers(),
            follow_redirects=False,
        )
        legacy_status_htmx = client.get(
            route,
            params={"q": "Планирование", "status": "uploading", "sort": "started_asc"},
            headers={**auth_headers(), "HX-Request": "true"},
        )
        hidden_access = client.get(
            route,
            params={"access": "denied"},
            headers=auth_headers(),
        )

        assert legacy_status.status_code == 303
        assert legacy_status.headers["location"] == f"{route}?status=processing"
        canonical_status_page = client.get(
            route,
            params={"status": "processing"},
            headers=auth_headers(),
        )
        assert canonical_status_page.status_code == 200
        assert 'value="processing" selected' in canonical_status_page.text
        assert legacy_status_htmx.status_code == 200
        assert legacy_status_htmx.headers["HX-Replace-Url"] == (
            f"{route}?q=%D0%9F%D0%BB%D0%B0%D0%BD%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5&status=processing&sort=started_asc"
        )
        assert (
            'hx-get="'
            + legacy_status_htmx.headers["HX-Replace-Url"].replace("&", "&amp;")
            + '"'
            in legacy_status_htmx.text
        )
        assert "Планирование релиза" in legacy_status_htmx.text
        assert hidden_access.status_code == 422


def test_meeting_list_toolbar_has_one_clear_hierarchy_and_contextual_result_count(client) -> None:
    seed_cabinet_meetings(client)

    for route in ("/meetings", "/desktop/meetings"):
        page = client.get(
            route,
            params={"q": "Проектный", "status": "ready", "sort": "started_desc"},
            headers=auth_headers(),
        )

        assert page.status_code == 200
        assert page.text.count('<h1 data-list-title tabindex="-1">Мои встречи</h1>') == 1
        assert page.text.count('id="meeting-search"') == 1
        assert 'id="meeting-search" name="q" type="search"' in page.text
        assert 'maxlength="120"' in page.text
        assert page.text.count("data-filter-disclosure") == 1
        assert page.text.count("data-sort-disclosure") == 1
        assert page.text.count("data-manual-upload-open") == 1
        assert "Фильтры: 1" in page.text
        assert "Найдено: 1" in page.text
        assert "Загрузить запись" in page.text
        assert "Записи встреч" not in page.text
        assert "data-current-sort-label" not in page.text


def test_refined_count_discloses_truncation_without_changing_public_api(client) -> None:
    for index in range(2):
        created = client.post(
            "/api/v1/meetings",
            headers=auth_headers(),
            json={
                "local_recording_id": f"truncated-count-{index}",
                "title": f"Счётчик результатов {index}",
                "title_source": "user_confirmed",
                "duration_seconds": 60,
            },
        )
        assert created.status_code == 200

    page = client.get(
        "/meetings",
        params={"q": "Счётчик результатов", "limit": 1},
        headers=auth_headers(),
    )
    api_response = client.get(
        "/api/v1/cabinet/meetings",
        params={"q": "Счётчик результатов", "limit": 1},
        headers=auth_headers(),
    )

    assert page.status_code == 200
    assert "Найдено: больше 1" in page.text
    assert api_response.status_code == 200
    assert set(api_response.json()) == {"items", "filters", "generated_at"}


def test_public_status_filters_remain_exact_while_web_labels_group_related_states(client) -> None:
    status_rows = (
        (uuid4(), "submitted", ProcessingStatus.NOT_SUBMITTED, MeetingStatus.INGESTED_PENDING_PROCESSING),
        (uuid4(), "processing", ProcessingStatus.POLLING, MeetingStatus.INGESTED_PENDING_PROCESSING),
        (uuid4(), "blocked", ProcessingStatus.BLOCKED, MeetingStatus.INGESTED_PENDING_PROCESSING),
        (uuid4(), "failed", ProcessingStatus.FAILED_TERMINAL, MeetingStatus.INGESTED_PENDING_PROCESSING),
        (uuid4(), "unavailable", ProcessingStatus.CANCELED, MeetingStatus.INGESTED_PENDING_PROCESSING),
        (uuid4(), "aborted", ProcessingStatus.NOT_SUBMITTED, MeetingStatus.ABORTED),
        (uuid4(), "expired", ProcessingStatus.NOT_SUBMITTED, MeetingStatus.EXPIRED),
    )

    async def seed_status_rows() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    Meeting(
                        id=meeting_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id=f"status-group-{status}",
                        title=f"Status group {status}",
                        started_at=datetime(2026, 7, 14, 8, 0, tzinfo=UTC),
                        duration_seconds=60,
                        status=meeting_status.value,
                        processing_status=processing_status.value,
                    )
                    for meeting_id, status, processing_status, meeting_status in status_rows
                ]
            )
            await db.commit()

    client.portal.call(seed_status_rows)

    processing = client.get(
        "/api/v1/cabinet/meetings?q=status-group&status=processing",
        headers=auth_headers(),
    )
    needs_help = client.get(
        "/api/v1/cabinet/meetings?q=status-group&status=failed",
        headers=auth_headers(),
    )
    submitted = client.get(
        "/api/v1/cabinet/meetings?q=status-group&status=submitted",
        headers=auth_headers(),
    )
    web_processing = client.get(
        "/meetings",
        params={"q": "Status group", "status": "processing"},
        headers=auth_headers(),
    )
    web_needs_help = client.get(
        "/desktop/meetings",
        params={"q": "Status group", "status": "failed"},
        headers=auth_headers(),
    )

    assert processing.status_code == 200
    assert {item["status"] for item in processing.json()["items"]} == {"processing"}
    assert needs_help.status_code == 200
    assert {item["status"] for item in needs_help.json()["items"]} == {"failed"}
    terminal_ids = {
        str(meeting_id)
        for meeting_id, status, _processing_status, _meeting_status in status_rows
        if status in {"aborted", "expired"}
    }
    assert terminal_ids.isdisjoint(
        {item["meeting_id"] for item in needs_help.json()["items"]}
    )
    assert submitted.status_code == 200
    submitted_items = {item["meeting_id"]: item for item in submitted.json()["items"]}
    assert terminal_ids <= submitted_items.keys()
    assert {submitted_items[meeting_id]["status"] for meeting_id in terminal_ids} == {
        "submitted"
    }
    for meeting_id in terminal_ids:
        detail = client.get(
            f"/api/v1/cabinet/meetings/{meeting_id}",
            headers=auth_headers(),
        )
        assert detail.status_code == 200
        assert detail.json()["meeting"]["meeting_id"] == meeting_id
        assert detail.json()["meeting"]["status"] == "submitted"
        assert detail.json()["processing"]["state"] == "submitted"
    assert web_processing.status_code == 200
    assert "Status group submitted" in web_processing.text
    assert "Status group processing" in web_processing.text
    assert "Status group failed" not in web_processing.text
    assert web_needs_help.status_code == 200
    assert "Status group blocked" in web_needs_help.text
    assert "Status group failed" in web_needs_help.text
    assert "Status group unavailable" in web_needs_help.text
    assert "Status group aborted" in web_needs_help.text
    assert "Status group expired" in web_needs_help.text
    assert "Status group processing" not in web_needs_help.text
    assert "Status group aborted" not in web_processing.text
    assert "Status group expired" not in web_processing.text


def test_search_prefilters_nonmatching_rows_before_access_and_media_projection(
    client, monkeypatch
) -> None:
    seed_cabinet_meetings(client)

    async def fail_if_projected(*_args, **_kwargs):
        raise AssertionError("nonmatching rows must be filtered in SQL")

    monkeypatch.setattr(
        "twobrain_rec_server.cabinet.queries.decide_meeting_access",
        fail_if_projected,
    )
    monkeypatch.setattr(
        "twobrain_rec_server.cabinet.queries._latest_media_revision",
        fail_if_projected,
    )

    response = client.get(
        "/api/v1/cabinet/meetings?q=definitely-missing-title",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_visible_time_search_prefilters_nonmatching_rows_before_access_projection(
    client, monkeypatch
) -> None:
    created = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "bounded-visible-time-search",
            "title": "Ограниченный поиск",
            "title_source": "user_confirmed",
            "started_at": "2026-07-14T02:30:00Z",
            "duration_seconds": 60,
        },
    )
    assert created.status_code == 200

    async def fail_if_projected(*_args, **_kwargs):
        raise AssertionError("nonmatching projected rows must be filtered in SQL")

    monkeypatch.setattr(
        "twobrain_rec_server.cabinet.queries.decide_meeting_access",
        fail_if_projected,
    )
    monkeypatch.setattr(
        "twobrain_rec_server.cabinet.queries._latest_media_revision",
        fail_if_projected,
    )

    response = client.get(
        "/meetings",
        params={"q": "03:30"},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert "Ничего не найдено" in response.text


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
    hidden_identifier_page = client.get(
        "/desktop/meetings?q=cabinet-upload-progress", headers=auth_headers()
    )
    visible_title_page = client.get(
        "/desktop/meetings",
        params={"q": "Запись"},
        headers=auth_headers(),
    )
    processing_page = client.get(
        "/desktop/meetings",
        params={"q": "Запись", "status": "processing"},
        headers=auth_headers(),
    )
    legacy_uploading_page = client.get(
        "/desktop/meetings",
        params={"q": "Запись", "status": "uploading"},
        headers=auth_headers(),
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
    assert hidden_identifier_page.status_code == 200
    assert "Ничего не найдено" in hidden_identifier_page.text
    assert "data-meeting-row" not in hidden_identifier_page.text
    assert visible_title_page.status_code == 200
    assert 'aria-label="Открыть встречу Запись, Без даты"' in visible_title_page.text
    for filtered_page in (processing_page, legacy_uploading_page):
        assert filtered_page.status_code == 200
        assert f'data-meeting-id="{meeting_id}"' in filtered_page.text
        assert 'value="processing" selected' in filtered_page.text

    page = client.get("/desktop/meetings", headers=auth_headers())

    assert page.status_code == 200
    assert "cabinet-upload-progress" not in page.text
    assert 'aria-label="Открыть встречу Запись, Без даты"' in page.text
    assert "Отправляем 40%" in page.text
    assert 'aria-label="Прогресс отправки записи"' in page.text
    assert 'hx-trigger="every 1s"' in page.text


def test_terminal_upload_uses_attention_group_without_changing_public_status_filter(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "cabinet-terminal-upload",
            "title": "Terminal upload failure",
            "title_source": "user_confirmed",
            "duration_seconds": 60,
        },
    )
    assert meeting.status_code == 200
    meeting_id = meeting.json()["meeting_id"]
    session = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 8, "microphone": 16, "system": 16}},
    )
    assert session.status_code == 200

    async def mark_upload_failed() -> None:
        async with client.app_state["sessionmaker"]() as db:
            upload = await db.get(UploadSession, UUID(session.json()["session_id"]))
            assert upload is not None
            upload.status = UploadSessionStatus.EXPIRED.value
            await db.commit()

    client.portal.call(mark_upload_failed)

    public_uploading = client.get(
        "/api/v1/cabinet/meetings",
        params={"q": "Terminal upload failure", "status": "uploading"},
        headers=auth_headers(),
    )
    public_failed = client.get(
        "/api/v1/cabinet/meetings",
        params={"q": "Terminal upload failure", "status": "failed"},
        headers=auth_headers(),
    )
    web_needs_help = client.get(
        "/desktop/meetings",
        params={"q": "Terminal upload failure", "status": "failed"},
        headers=auth_headers(),
    )
    web_processing = client.get(
        "/meetings",
        params={"q": "Terminal upload failure", "status": "processing"},
        headers=auth_headers(),
    )

    assert public_uploading.status_code == 200
    assert [item["meeting_id"] for item in public_uploading.json()["items"]] == [meeting_id]
    assert public_uploading.json()["items"][0]["status"] == "uploading"
    assert public_failed.status_code == 200
    assert public_failed.json()["items"] == []
    assert web_needs_help.status_code == 200
    assert f'data-meeting-id="{meeting_id}"' in web_needs_help.text
    assert "Terminal upload failure" in web_needs_help.text
    assert 'data-status-kind="failed"' in web_needs_help.text
    assert "Не удалось обработать" in web_needs_help.text
    assert web_processing.status_code == 200
    assert f'data-meeting-id="{meeting_id}"' not in web_processing.text


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
    assert "Ничего не найдено" in response.text
    assert "Измените запрос или сбросьте фильтры." in response.text
    assert 'hx-trigger="every 1s"' in response.text
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
    assert "aaa-visible-fallback" not in titles
    assert "Запись 26 июн, 08:00" in titles
    assert "bbb-visible-title" in titles


def test_web_title_sort_uses_projected_visible_titles_without_changing_api_sort(client) -> None:
    fallback_id = uuid4()
    named_id = uuid4()

    async def seed_projected_title_rows() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    Meeting(
                        id=fallback_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id="projected-title-fallback",
                        title=None,
                        title_source="generic",
                        duration_seconds=60,
                        status=MeetingStatus.DRAFT.value,
                        processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                    ),
                    Meeting(
                        id=named_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id="projected-title-named",
                        title="Запись А",
                        title_source="user_confirmed",
                        duration_seconds=60,
                        status=MeetingStatus.DRAFT.value,
                        processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                    ),
                ]
            )
            await db.commit()

    client.portal.call(seed_projected_title_rows)

    api = client.get("/api/v1/cabinet/meetings?sort=title_asc", headers=auth_headers())
    page = client.get("/meetings?sort=title_asc", headers=auth_headers())

    assert api.status_code == 200
    assert page.status_code == 200
    api_ids = [item["meeting_id"] for item in api.json()["items"]]
    assert api_ids.index(str(named_id)) < api_ids.index(str(fallback_id))
    assert page.text.index(f"/meetings/{fallback_id}") < page.text.index(f"/meetings/{named_id}")


def test_web_list_preserves_and_searches_authoritative_fallback_looking_title(client) -> None:
    meeting_id = uuid4()

    async def seed_authoritative_title() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                Meeting(
                    id=meeting_id,
                    workspace_id=WORKSPACE_ID,
                    created_by_user_id=USER_ID,
                    device_id=DEVICE_ID,
                    local_recording_id="authoritative-fallback-looking-title",
                    title="Запись без названия",
                    title_source="user_confirmed",
                    duration_seconds=60,
                    status=MeetingStatus.DRAFT.value,
                    processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                )
            )
            await db.commit()

    client.portal.call(seed_authoritative_title)

    page = client.get(
        "/meetings",
        params={"q": "без названия", "sort": "title_asc"},
        headers=auth_headers(),
    )

    assert page.status_code == 200
    assert f'href="/meetings/{meeting_id}"' in page.text
    assert ">Запись без названия<" in page.text


def test_web_visible_title_prefilter_is_a_superset_of_safe_projection(client) -> None:
    whitespace_id = uuid4()
    filename_id = uuid4()
    unsafe_id = uuid4()
    prefixed_title_id = uuid4()
    compact_generated_id = uuid4()
    manual_prefix_title_id = uuid4()
    domain_boundary_title_id = uuid4()
    empty_cleaned_filename_id = uuid4()
    fallback_looking_title_id = uuid4()

    async def seed_projected_search_rows() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    Meeting(
                        id=whitespace_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id="projected-whitespace-title",
                        title="Quarterly   sync",
                        title_source="user_confirmed",
                        started_at=datetime(2026, 7, 14, 9, 0, tzinfo=UTC),
                        duration_seconds=60,
                        status=MeetingStatus.DRAFT.value,
                        processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                    ),
                    Meeting(
                        id=filename_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id="projected-filename-title",
                        title="/private/Release___review.m4a",
                        title_source="generic",
                        started_at=datetime(2026, 7, 14, 10, 0, tzinfo=UTC),
                        duration_seconds=60,
                        status=MeetingStatus.DRAFT.value,
                        processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                    ),
                    Meeting(
                        id=unsafe_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id="projected-unsafe-title",
                        title=("x" * 460) + " https://private.example/transcript",
                        title_source="user_confirmed",
                        started_at=datetime(2026, 7, 14, 11, 0, tzinfo=UTC),
                        duration_seconds=60,
                        status=MeetingStatus.DRAFT.value,
                        processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                    ),
                    Meeting(
                        id=prefixed_title_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id="projected-prefixed-title",
                        title="Zoom - quarterly sync",
                        title_source="generic",
                        started_at=datetime(2026, 7, 14, 12, 0, tzinfo=UTC),
                        duration_seconds=60,
                        status=MeetingStatus.DRAFT.value,
                        processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                    ),
                    Meeting(
                        id=compact_generated_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id="projected-compact-generated-title",
                        title="Zoom-2026-07-14 13:00",
                        title_source="generic",
                        started_at=datetime(2026, 7, 14, 13, 0, tzinfo=UTC),
                        duration_seconds=60,
                        status=MeetingStatus.DRAFT.value,
                        processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                    ),
                    Meeting(
                        id=manual_prefix_title_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id="projected-manual-prefix-title",
                        title="manual-upload-project planning",
                        title_source="generic",
                        started_at=datetime(2026, 7, 14, 14, 0, tzinfo=UTC),
                        duration_seconds=60,
                        status=MeetingStatus.DRAFT.value,
                        processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                    ),
                    Meeting(
                        id=domain_boundary_title_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id="projected-domain-boundary-title",
                        title="project_foo.com/path",
                        title_source="user_confirmed",
                        started_at=datetime(2026, 7, 14, 15, 0, tzinfo=UTC),
                        duration_seconds=60,
                        status=MeetingStatus.DRAFT.value,
                        processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                    ),
                    Meeting(
                        id=empty_cleaned_filename_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id="projected-empty-cleaned-filename",
                        title="__.wav",
                        title_source="generic",
                        started_at=datetime(2026, 7, 14, 16, 0, tzinfo=UTC),
                        duration_seconds=60,
                        status=MeetingStatus.DRAFT.value,
                        processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                    ),
                    Meeting(
                        id=fallback_looking_title_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id="projected-fallback-looking-title",
                        title="Запись без названия",
                        title_source="generic",
                        started_at=datetime(2026, 7, 14, 17, 0, tzinfo=UTC),
                        duration_seconds=60,
                        status=MeetingStatus.DRAFT.value,
                        processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                    ),
                ]
            )
            await db.commit()

    client.portal.call(seed_projected_search_rows)

    whitespace = client.get(
        "/meetings", params={"q": "Quarterly sync"}, headers=auth_headers()
    )
    filename = client.get(
        "/meetings", params={"q": "Release review 14 июл"}, headers=auth_headers()
    )
    unsafe = client.get(
        "/meetings", params={"q": "Запись 14 июл"}, headers=auth_headers()
    )
    prefixed_title = client.get(
        "/meetings",
        params={"q": "Zoom - quarterly sync 14 июл"},
        headers=auth_headers(),
    )
    compact_generated = client.get(
        "/meetings", params={"q": "Запись 14 июл"}, headers=auth_headers()
    )
    manual_prefix_title = client.get(
        "/meetings",
        params={"q": "manual-upload-project planning 14 июл"},
        headers=auth_headers(),
    )
    domain_boundary_title = client.get(
        "/meetings",
        params={"q": "project_foo.com/path 14 июл"},
        headers=auth_headers(),
    )
    empty_cleaned_filename = client.get(
        "/meetings",
        params={"q": "Загруженная запись 14 июл"},
        headers=auth_headers(),
    )
    fallback_looking_title = client.get(
        "/meetings",
        params={"q": "Запись 1 мин 14 июл"},
        headers=auth_headers(),
    )

    assert whitespace.status_code == 200
    assert f'href="/meetings/{whitespace_id}"' in whitespace.text
    assert filename.status_code == 200
    assert f'href="/meetings/{filename_id}"' in filename.text
    assert unsafe.status_code == 200
    assert f'href="/meetings/{unsafe_id}"' in unsafe.text
    assert "private.example" not in unsafe.text
    assert prefixed_title.status_code == 200
    assert f'href="/meetings/{prefixed_title_id}"' in prefixed_title.text
    assert ">Zoom - quarterly sync<" in prefixed_title.text
    assert compact_generated.status_code == 200
    assert f'href="/meetings/{compact_generated_id}"' in compact_generated.text
    assert manual_prefix_title.status_code == 200
    assert f'href="/meetings/{manual_prefix_title_id}"' in manual_prefix_title.text
    assert ">manual-upload-project planning<" in manual_prefix_title.text
    assert domain_boundary_title.status_code == 200
    assert f'href="/meetings/{domain_boundary_title_id}"' in domain_boundary_title.text
    assert ">project_foo.com/path<" in domain_boundary_title.text
    assert empty_cleaned_filename.status_code == 200
    assert f'href="/meetings/{empty_cleaned_filename_id}"' in empty_cleaned_filename.text
    assert ">Загруженная запись<" in empty_cleaned_filename.text
    assert fallback_looking_title.status_code == 200
    assert f'href="/meetings/{fallback_looking_title_id}"' in fallback_looking_title.text
    assert ">Запись<" in fallback_looking_title.text


def test_web_search_keeps_generated_recording_visible_date_and_time_searchable(client) -> None:
    meeting_id = uuid4()
    named_meeting_id = uuid4()

    async def seed_generated_recording() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                Meeting(
                    id=meeting_id,
                    workspace_id=WORKSPACE_ID,
                    created_by_user_id=USER_ID,
                    device_id=DEVICE_ID,
                    local_recording_id="generated-visible-time-search",
                    title="Meeting - 2026-07-13 23:30",
                    title_source="generic",
                    started_at=datetime(2026, 7, 13, 23, 30, tzinfo=UTC),
                    recording_display_timezone_offset_minutes=180,
                    duration_seconds=14 * 60,
                    status=MeetingStatus.DRAFT.value,
                    processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                )
            )
            db.add(
                Meeting(
                    id=named_meeting_id,
                    workspace_id=WORKSPACE_ID,
                    created_by_user_id=USER_ID,
                    device_id=DEVICE_ID,
                    local_recording_id="named-visible-time-search",
                    title="Проектный синк",
                    title_source="user_confirmed",
                    started_at=datetime(2026, 7, 13, 23, 30, tzinfo=UTC),
                    recording_display_timezone_offset_minutes=180,
                    duration_seconds=74 * 60,
                    status=MeetingStatus.DRAFT.value,
                    processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                )
            )
            await db.commit()

    client.portal.call(seed_generated_recording)

    for query in ("14", "июл", "02:30"):
        page = client.get("/meetings", params={"q": query}, headers=auth_headers())

        assert page.status_code == 200
        assert f'href="/meetings/{meeting_id}"' in page.text
        assert ">Запись 14 июл, 02:30<" in page.text
        assert "14 июл, 02:30" in page.text
        if query == "02:30":
            assert f'href="/meetings/{named_meeting_id}"' in page.text

    combined = client.get(
        "/meetings",
        params={"q": "Запись 14 июл"},
        headers=auth_headers(),
    )
    named_time = client.get(
        "/meetings",
        params={"q": "Проектный синк 14 июл"},
        headers=auth_headers(),
    )

    assert combined.status_code == 200
    assert f'href="/meetings/{meeting_id}"' in combined.text
    assert named_time.status_code == 200
    assert f'href="/meetings/{named_meeting_id}"' in named_time.text

    generated_duration = client.get(
        "/meetings",
        params={"q": "14 мин"},
        headers=auth_headers(),
    )
    named_duration = client.get(
        "/meetings",
        params={"q": "1 ч 14 мин"},
        headers=auth_headers(),
    )
    named_duration_time = client.get(
        "/meetings",
        params={"q": "Проектный синк 1 ч 14 мин 14 июл"},
        headers=auth_headers(),
    )

    assert generated_duration.status_code == 200
    assert f'href="/meetings/{meeting_id}"' in generated_duration.text
    assert named_duration.status_code == 200
    assert f'href="/meetings/{named_meeting_id}"' in named_duration.text
    assert f'href="/meetings/{meeting_id}"' not in named_duration.text
    assert named_duration_time.status_code == 200
    assert f'href="/meetings/{named_meeting_id}"' in named_duration_time.text

    missing = client.get("/meetings", params={"q": "03:30"}, headers=auth_headers())
    assert missing.status_code == 200
    assert f'href="/meetings/{meeting_id}"' not in missing.text
    assert f'href="/meetings/{named_meeting_id}"' not in missing.text


def test_web_meeting_filters_accept_empty_neighbor_controls(client) -> None:
    seed_cabinet_meetings(client)

    desktop = client.get(
        "/desktop/meetings?q=&status=ready&access=&sort=updated_desc",
        headers=auth_headers(),
    )
    browser = client.get(
        "/meetings?q=&status=&access=owner&sort=updated_desc",
        headers=auth_headers(),
    )

    assert desktop.status_code == 200
    assert "Проектный синк" in desktop.text
    assert "Планирование релиза" not in desktop.text
    assert browser.status_code == 200
    assert "Проектный синк" in browser.text


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
    legacy_web = client.get("/meetings", headers=auth_headers())

    assert detail.status_code == 200
    assert detail.json()["meeting"]["started_at"].startswith("2026-06-16T08:00:00")
    assert legacy_list.status_code == 200
    legacy_item = legacy_list.json()["items"][0]
    assert legacy_item["title"] == "Запись без названия"
    assert legacy_item["started_at"] is None
    assert legacy_web.status_code == 200
    assert "legacy-no-recording-date" not in legacy_web.text
    assert 'aria-label="Открыть встречу Запись, Без даты"' in legacy_web.text
    assert "Без даты" in legacy_web.text


def test_cabinet_list_uses_recording_display_timezone_offset_for_date_label(client) -> None:
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "timezone-crossing-visible-day",
            "title": "Meeting - 2026-07-13 23:30",
            "started_at": "2026-07-13T23:30:00Z",
            "recording_display_timezone_offset_minutes": 180,
            "duration_seconds": 60,
        },
    )
    assert response.status_code == 200

    page = client.get("/meetings", headers=auth_headers())

    assert page.status_code == 200
    assert 'aria-label="Открыть встречу Запись 14 июл, 02:30"' in page.text
    assert "14 июл, 02:30" in page.text
    assert "timezone-crossing-visible-day" not in page.text


def test_cabinet_list_humanizes_generated_capture_and_manual_upload_titles(client) -> None:
    generated_title = "Current display system audio - 2026-07-13 12:14"
    manual_title = "manual-upload-mrc4escf-hbo5nhsk"
    generated = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "generated-capture-title",
            "title": generated_title,
            "title_source": "app_context",
            "started_at": "2026-07-13T09:14:00Z",
            "recording_display_timezone_offset_minutes": 180,
            "duration_seconds": 27,
        },
    )
    manual = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": manual_title,
            "title": manual_title,
            "duration_seconds": 4_440,
        },
    )
    assert generated.status_code == 200
    assert manual.status_code == 200

    generated_list = client.get(
        "/api/v1/cabinet/meetings?q=generated-capture-title",
        headers=auth_headers(),
    )
    manual_list = client.get(
        f"/api/v1/cabinet/meetings?q={manual_title}",
        headers=auth_headers(),
    )
    generated_visible_search = client.get(
        "/api/v1/cabinet/meetings",
        params={"q": "Current display system audio — 13 июл, 12:14"},
        headers=auth_headers(),
    )
    manual_visible_search = client.get(
        "/api/v1/cabinet/meetings",
        params={"q": "Загруженная запись"},
        headers=auth_headers(),
    )
    page = client.get("/desktop/meetings", headers=auth_headers())

    assert generated_list.status_code == 200
    assert generated_list.json()["items"][0]["title"] == "Current display system audio — 13 июл, 12:14"
    assert manual_list.status_code == 200
    assert manual_list.json()["items"][0]["title"] == "Загруженная запись"
    assert generated_visible_search.status_code == 200
    assert [item["meeting_id"] for item in generated_visible_search.json()["items"]] == [
        generated.json()["meeting_id"]
    ]
    assert manual_visible_search.status_code == 200
    assert [item["meeting_id"] for item in manual_visible_search.json()["items"]] == [
        manual.json()["meeting_id"]
    ]
    assert generated_title not in page.text
    assert manual_title not in page.text
    assert 'aria-label="Открыть встречу Current display system audio — 13 июл, 12:14"' in page.text
    assert "13 июл, 12:14" in page.text
    assert "Загруженная запись" in page.text
    assert "27 с" in page.text
    assert "1 ч 14 мин" in page.text


def test_cabinet_list_web_shell_renders_reference_informed_controls(client) -> None:
    seed_cabinet_meetings(client)

    response = client.get("/meetings", headers=auth_headers())

    assert response.status_code == 200
    assert "Мои встречи" in response.text
    assert "Ближайшие" not in response.text
    assert "Подключить календари" not in response.text
    assert "Пробный период" not in response.text
    assert "Пригласить" not in response.text
    assert "Командный синк" not in response.text
    assert "Записи встреч" not in response.text
    assert "<span>Загрузить запись</span>" in response.text
    assert "Загрузить медиа" not in response.text
    assert "Фильтры" in response.text
    assert "Сортировка" in response.text
    assert response.text.count('id="meeting-search"') == 1
    assert 'aria-label="Поиск встреч"' in response.text
    assert "data-filter-disclosure" in response.text
    assert "data-sort-disclosure" in response.text
    assert 'aria-label="Сохраненные"' not in response.text
    assert 'aria-label="Применить фильтры"' not in response.text
    assert 'value="started_desc"' in response.text
    assert 'value="started_asc"' in response.text
    assert "Сначала новые" in response.text
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
    # Destructive deletion is deliberately exposed only from the authorized
    # meeting detail, never as an eager list-level action.
    assert item["governance"]["delete"]["state"] == "disabled"
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
    assert 'href="/desktop/settings"' in response.text
    assert 'href="/meetings"' not in response.text
    assert f'href="{CABINET_STATIC_URL}/cabinet.css?v=' in response.text
    assert "Записи встреч" not in response.text
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
            "/meetings",
            params={"q": "Synthetic T082 Current"},
            headers=auth_headers(),
        ),
        "embedded": client.get(
            "/desktop/meetings",
            params={"q": "Synthetic T082 Current"},
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
    assert 'data-settings-primary-nav-item="calendar"' in web.text
    assert 'href="/settings/integrations/calendar"' in web.text
    assert "Календари" in web.text
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
        assert response.text.count("Нужен выбор") == 1, surface
        assert (
            response.text.count(
                'class="mini-link calendar-context-list-action"'
            )
            == 1
        ), surface
        assert '>Выбрать встречу</a>' in response.text, surface
        assert (
            'aria-label="Выбрать встречу t050-owner-ambiguous-list, '
            '13 июл, 09:10"'
            in response.text
        ), surface
        assert 'data-status-kind="calendar_choice"' in response.text, surface
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
        assert "Без календарного контекста" not in response.text
        assert "Нужен выбор" not in response.text
        assert "calendar-context-list-action" not in response.text
        assert "ambiguous" not in response.text
        assert "multiple_time_candidates" not in response.text
        assert "data-meeting-select" not in response.text
        assert "data-row-delete" not in response.text
        assert response.text.count("row-contextual-placeholder") == 2


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
