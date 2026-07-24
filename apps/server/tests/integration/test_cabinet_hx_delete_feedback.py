from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY


def test_non_hx_deletion_request_keeps_json_contract(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )

    assert response.status_code == 202
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["meeting_id"] == str(seeds.ready_id)
    assert "data-cabinet-fragment" not in response.text


def test_hx_deletion_request_returns_empty_success_body(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers() | {"HX-Request": "true"},
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )

    assert response.status_code == 202
    assert response.headers["Vary"] == "HX-Request"
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-cabinet-fragment="deletion-feedback"' in response.text
    assert 'role="status"' not in response.text
    assert response.text.count("<p>") == 1
    assert "<h2>" not in response.text
    assert "Запись удалена из списка. Очистка данных GRAF продолжается." in response.text
    assert "Запись удалена из списка." in response.text
    assert "Очистка данных GRAF продолжается." in response.text
    assert "Отчет удаления" not in response.text
    assert "/deletion-report" not in response.text
    assert "storage_object_key" not in response.text


def test_hx_web_deletion_form_returns_empty_success_body(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.post(
        f"/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers() | {"HX-Request": "true"},
        data={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )

    assert response.status_code == 202
    assert response.headers["Vary"] == "HX-Request"
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-cabinet-fragment="deletion-feedback"' in response.text
    assert 'role="status"' not in response.text
    assert response.text.count("<p>") == 1
    assert "<h2>" not in response.text
    assert "Запись удалена из списка. Очистка данных GRAF продолжается." in response.text
    assert "Запись удалена из списка." in response.text
    assert "Очистка данных GRAF продолжается." in response.text
    assert "Отчет удаления" not in response.text
    assert "/deletion-report" not in response.text
    assert "storage_object_key" not in response.text


def test_non_hx_web_deletion_request_returns_to_meeting_list(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.post(
        f"/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        data={"confirmation_boundary": BOUNDED_DELETE_COPY},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/meetings"
    assert "/deletion-report" not in response.headers["location"]
