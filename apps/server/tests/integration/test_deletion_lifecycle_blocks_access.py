from __future__ import annotations

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT, seed_cabinet_meetings

BOUNDED_COPY = "Delete this meeting everywhere 2brain Rec controls."


def test_deleting_meeting_is_hidden_from_list_and_blocks_original_content_routes(client) -> None:
    seeds = seed_cabinet_meetings(client)
    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202

    listing = client.get("/api/v1/cabinet/meetings", headers=auth_headers())
    assert listing.status_code == 200
    listed_ids = {item["meeting_id"] for item in listing.json()["items"]}
    assert str(seeds.ready_id) not in listed_ids

    download = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/transcript",
        headers=auth_headers(),
    )
    assert download.status_code in {404, 409}
    assert SAFE_TRANSCRIPT_TEXT not in download.text

    share = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json={"grantee_user_id": "30000000-0000-0000-0000-000000000099"},
    )
    assert share.status_code in {404, 409}
    assert "share_url" not in share.text

    detail_page = client.get(f"/meetings/{seeds.ready_id}", headers=auth_headers())
    assert detail_page.status_code == 404

    report_page = client.get(f"/meetings/{seeds.ready_id}/deletion-report", headers=auth_headers())
    assert report_page.status_code == 200
    assert "Отчет удаления" in report_page.text
    assert "Файлы под контролем GRAF" in report_page.text
    assert SAFE_TRANSCRIPT_TEXT not in report_page.text
    assert "storage_object_key" not in report_page.text
