from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_workspace_user,
    auth_headers_for,
    set_artifact_policy,
)


def test_owner_only_artifact_policy_blocks_shared_viewer_but_not_owner(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)
    set_artifact_policy(
        client,
        seeds.ready_id,
        transcript_download="owner_only",
        package_export="owner_only",
    )
    share = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json={
            "grantee_user_id": str(SHARED_USER_ID),
            "content_scope": "full_meeting",
            "can_download": True,
        },
    )
    assert share.status_code == 201

    shared_access = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/access",
        headers=auth_headers_for(),
    ).json()
    shared_download = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/transcript",
        headers=auth_headers_for(),
    )
    owner_download = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/transcript",
        headers=auth_headers(),
    )

    transcript_state = next(
        artifact for artifact in shared_access["artifacts"] if artifact["artifact_class"] == "transcript"
    )
    assert shared_access["access"]["state"] == "shared"
    assert transcript_state["state"] == "owner_only"
    assert shared_download.status_code == 409
    assert owner_download.status_code == 200
