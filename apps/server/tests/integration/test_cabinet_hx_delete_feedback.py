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


def test_hx_deletion_request_returns_bounded_feedback_fragment(client) -> None:
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
    assert "Удаление запрошено" in response.text
    assert f"/meetings/{seeds.ready_id}/deletion-report" in response.text
    assert "storage_object_key" not in response.text


def test_hx_web_deletion_form_returns_bounded_feedback_fragment(client) -> None:
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
    assert "Удаление запрошено" in response.text
    assert f"/meetings/{seeds.ready_id}/deletion-report" in response.text
    assert "storage_object_key" not in response.text
