from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings


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

    search = client.get("/api/v1/cabinet/meetings?q=релиза", headers=auth_headers())
    ready = client.get("/api/v1/cabinet/meetings?status=ready", headers=auth_headers())
    shortest = client.get("/api/v1/cabinet/meetings?sort=duration_asc&limit=2", headers=auth_headers())

    assert search.status_code == 200
    assert [item["title"] for item in search.json()["items"]] == ["Планирование релиза"]
    assert ready.status_code == 200
    assert [item["status"] for item in ready.json()["items"]] == ["ready"]
    assert shortest.status_code == 200
    durations = [item["duration_seconds"] for item in shortest.json()["items"]]
    assert durations == sorted(durations)
    assert len(durations) == 2


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
    assert "Проектный синк" in response.text


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
    assert "Записи встреч" in response.text
    assert "Проектный синк" in response.text
    assert "Upload file" not in response.text
    assert "Record live" not in response.text
    assert "Screen Recording" not in response.text
