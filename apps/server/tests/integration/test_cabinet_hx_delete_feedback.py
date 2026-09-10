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
    assert response.text == ""


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
    assert response.text == ""


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


def test_repeated_deletion_returns_same_receipt_without_restarting_purge(client) -> None:
    seeds = seed_cabinet_meetings(client)
    url = f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests"
    first = client.post(url, headers=auth_headers(), json={"confirmation_boundary": BOUNDED_DELETE_COPY})
    second = client.post(url, headers=auth_headers(), json={"confirmation_boundary": BOUNDED_DELETE_COPY})
    assert first.status_code == second.status_code == 202
    assert second.json() == first.json()
    assert second.json()["receipt_type"] == "meeting_deletion"
    web_repeat = client.post(
        f"/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers() | {"HX-Request": "true"},
        data={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    assert web_repeat.status_code == 202
    assert web_repeat.text == ""
    invalid = client.post(url, headers=auth_headers(), json={"confirmation_boundary": "invalid"})
    assert invalid.status_code == 422


def test_deletion_index_and_report_remain_reachable_after_row_disappears(client) -> None:
    seeds = seed_cabinet_meetings(client)
    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(), json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    assert response.status_code == 202
    for prefix in ["", "/desktop"]:
        listing = client.get(f"{prefix}/deletions", headers=auth_headers())
        assert listing.status_code == 200
        link = f"{prefix}/meetings/{seeds.ready_id}/deletion-report"
        assert link in listing.text
        assert "data-user-datetime" in listing.text
        report = client.get(link, headers=auth_headers())
        assert report.status_code == 200
        assert f'{prefix}/meetings' in report.text
        empty = client.get(f"{prefix}/deletions?page=2", headers=auth_headers())
        assert empty.status_code == 200
        assert link not in empty.text
        assert "?page=1" in empty.text
    assert client.get("/deletions?page=0", headers=auth_headers()).status_code == 422


def test_deletion_receipts_and_index_do_not_cross_workspace_access(client) -> None:
    from tests.fixtures.cabinet import (
        FOREIGN_DEVICE_ID,
        FOREIGN_ORG_ID,
        FOREIGN_USER_ID,
        FOREIGN_WORKSPACE_ID,
    )
    seeds = seed_cabinet_meetings(client)
    foreign_headers = {
        "X-Organization-Id": str(FOREIGN_ORG_ID), "X-Workspace-Id": str(FOREIGN_WORKSPACE_ID),
        "X-User-Id": str(FOREIGN_USER_ID), "X-Device-Id": str(FOREIGN_DEVICE_ID),
    }
    url = f"/api/v1/cabinet/meetings/{seeds.foreign_id}/deletion-requests"
    deletion = client.post(url, headers=foreign_headers, json={"confirmation_boundary": BOUNDED_DELETE_COPY})
    assert deletion.status_code == 202
    assert str(seeds.foreign_id) in client.get("/deletions", headers=foreign_headers).text
    assert str(seeds.foreign_id) not in client.get("/deletions", headers=auth_headers()).text
    assert client.get(f"/meetings/{seeds.foreign_id}/deletion-report", headers=auth_headers()).status_code == 404
    denied = client.post(url, headers=auth_headers(), json={"confirmation_boundary": BOUNDED_DELETE_COPY})
    assert denied.status_code == 404
    assert deletion.json()["request_id"] not in denied.text
    assert "receipt_type" not in denied.json()
