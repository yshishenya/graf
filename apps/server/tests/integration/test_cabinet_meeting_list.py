from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from twobrain_rec_server.cabinet.templates import CABINET_STATIC_URL


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
    assert {item["status"] for item in payload["items"]} == {"ready", "processing", "failed", "partial"}


def test_cabinet_list_search_filter_sort_and_limit(client) -> None:
    seed_cabinet_meetings(client)
    legacy = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "sort-legacy-no-date", "duration_seconds": 60},
    )
    assert legacy.status_code == 200

    search = client.get("/api/v1/cabinet/meetings?q=релиза", headers=auth_headers())
    ready = client.get("/api/v1/cabinet/meetings?status=ready", headers=auth_headers())
    shortest = client.get("/api/v1/cabinet/meetings?sort=duration_asc&limit=2", headers=auth_headers())
    recording_newest = client.get("/api/v1/cabinet/meetings?sort=started_desc", headers=auth_headers())
    recording_oldest = client.get("/api/v1/cabinet/meetings?sort=started_asc", headers=auth_headers())

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


def test_cabinet_list_and_detail_use_recording_date_with_legacy_fallback(client) -> None:
    seeds = seed_cabinet_meetings(client)
    legacy = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "legacy-no-recording-date", "duration_seconds": 60},
    )
    assert legacy.status_code == 200

    detail = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())
    legacy_list = client.get("/api/v1/cabinet/meetings?q=legacy-no-recording-date", headers=auth_headers())
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


def test_cabinet_list_web_shell_renders_reference_informed_controls(client) -> None:
    seed_cabinet_meetings(client)

    response = client.get("/meetings", headers=auth_headers())

    assert response.status_code == 200
    assert "Мои встречи" in response.text
    assert "Ближайшие" in response.text
    assert "Записи встреч" in response.text
    assert "Новая" in response.text
    assert "Фильтры" in response.text
    assert "Сортировка" in response.text
    assert 'value="started_desc"' in response.text
    assert 'value="started_asc"' in response.text
    assert "Новые по дате записи" in response.text
    assert "Проектный синк" in response.text
    assert 'data-cabinet-shell' in response.text
    assert 'data-cabinet-navigation' in response.text
    assert 'data-active-nav="meetings"' in response.text
    assert 'id="meeting-list-region"' in response.text
    assert 'class="cabinet-list-controls"' in response.text
    assert 'method="get"' in response.text
    assert 'data-hx-target="#meeting-list-region"' in response.text
    assert 'data-hx-select="#meeting-list-region"' in response.text
    assert f'href="{CABINET_STATIC_URL}/cabinet.css"' in response.text
    assert "<!doctype html>" in response.text
    assert "<style>" not in response.text


def test_cabinet_list_full_page_fallback_without_hx_header(client) -> None:
    seed_cabinet_meetings(client)

    response = client.get("/meetings?sort=duration_asc", headers=auth_headers())

    assert response.status_code == 200
    assert "<!doctype html>" in response.text
    assert 'data-cabinet-shell' in response.text
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


def test_desktop_embedded_list_keeps_review_workspace_but_hides_native_creation_controls(client) -> None:
    seed_cabinet_meetings(client)

    response = client.get("/desktop/meetings", headers=auth_headers())

    assert response.status_code == 200
    assert "desktop-embedded" in response.text
    assert 'data-cabinet-shell' in response.text
    assert 'data-cabinet-navigation' in response.text
    assert 'data-active-nav="meetings"' in response.text
    assert 'href="/desktop/meetings"' in response.text
    assert 'href="/meetings"' not in response.text
    assert f'href="{CABINET_STATIC_URL}/cabinet.css"' in response.text
    assert "Записи встреч" in response.text
    assert "Проектный синк" in response.text
    assert "<style>" not in response.text
    assert "Upload file" not in response.text
    assert "Record live" not in response.text
    assert "Screen Recording" not in response.text
