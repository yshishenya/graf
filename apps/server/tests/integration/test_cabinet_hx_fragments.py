from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT, seed_cabinet_meetings
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY


def test_hx_meeting_list_returns_only_approved_list_fragment(client) -> None:
    seed_cabinet_meetings(client)

    response = client.get(
        "/meetings?sort=duration_asc",
        headers=auth_headers() | {"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert response.headers["Vary"] == "HX-Request"
    assert '<div id="meeting-list-region"' in response.text
    assert 'data-cabinet-fragment="meeting-list"' in response.text
    assert "Проектный синк" in response.text
    assert "<!doctype html>" not in response.text
    assert "data-cabinet-shell" not in response.text


def test_hx_desktop_meeting_list_uses_embedded_fragment_routes(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(
        "/desktop/meetings",
        headers=auth_headers() | {"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert response.headers["Vary"] == "HX-Request"
    assert f'href="/desktop/meetings/{seeds.ready_id}"' in response.text
    assert '<div id="meeting-list-region"' in response.text
    assert "<!doctype html>" not in response.text


def test_hx_meeting_detail_returns_only_approved_detail_fragment(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(
        f"/meetings/{seeds.ready_id}",
        headers=auth_headers() | {"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert response.headers["Vary"] == "HX-Request"
    assert '<div id="meeting-detail-region"' in response.text
    assert 'data-cabinet-fragment="meeting-detail"' in response.text
    assert SAFE_TRANSCRIPT_TEXT in response.text
    assert "<!doctype html>" not in response.text
    assert "data-cabinet-shell" not in response.text


def test_hx_deletion_report_returns_only_approved_report_fragment(client) -> None:
    seeds = seed_cabinet_meetings(client)
    deletion = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    assert deletion.status_code == 202

    response = client.get(
        f"/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers() | {"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert response.headers["Vary"] == "HX-Request"
    assert '<div id="deletion-report-region"' in response.text
    assert 'data-cabinet-fragment="deletion-report"' in response.text
    assert "Отчет удаления" in response.text
    assert "<!doctype html>" not in response.text
    assert "data-cabinet-shell" not in response.text


def test_hx_desktop_deletion_report_uses_embedded_back_route(client) -> None:
    seeds = seed_cabinet_meetings(client)
    deletion = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    assert deletion.status_code == 202

    response = client.get(
        f"/desktop/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers() | {"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert response.headers["Vary"] == "HX-Request"
    assert 'data-cabinet-fragment="deletion-report"' in response.text
    assert 'href="/desktop/meetings"' in response.text
    assert "<!doctype html>" not in response.text
