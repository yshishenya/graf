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
    assert "My Meetings" in response.text
    assert "Upcoming" in response.text
    assert "Meeting notes" in response.text
    assert "New" in response.text
    assert "Upload file" in response.text
    assert "Filters" in response.text
    assert "Sort" in response.text
    assert "Проектный синк" in response.text

