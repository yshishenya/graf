from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_workspace_user,
    auth_headers_for,
    set_meeting_visibility,
)


def test_owner_access_state_can_manage_sharing_downloads_and_exports(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}/access", headers=auth_headers())

    assert response.status_code == 200
    access = response.json()["access"]
    assert access["state"] == "owner"
    assert access["can_share"] is True
    assert access["can_download"] is True
    assert access["can_export"] is True


def test_same_workspace_member_without_visibility_or_grant_is_denied(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}",
        headers=auth_headers_for(),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "meeting_not_found"


def test_team_visible_meeting_is_visible_to_workspace_member(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)
    set_meeting_visibility(client, seeds.ready_id, "team")

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/access",
        headers=auth_headers_for(),
    )

    assert response.status_code == 200
    assert response.json()["access"]["state"] == "team"


def test_user_share_grant_makes_meeting_available_as_shared(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)

    share = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json={
            "grantee_user_id": str(SHARED_USER_ID),
            "content_scope": "full_meeting",
        },
    )
    detail = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}",
        headers=auth_headers_for(),
    )
    filtered = client.get("/api/v1/cabinet/meetings?access=shared", headers=auth_headers_for())

    assert share.status_code == 201
    assert "/cabinet/share/" in share.json()["share_url"]
    assert detail.status_code == 200
    assert detail.json()["access"]["state"] == "shared"
    assert [item["meeting_id"] for item in filtered.json()["items"]] == [str(seeds.ready_id)]
