from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_workspace_user,
    audit_events,
    auth_headers_for,
)


def test_login_required_share_link_resolves_for_grantee_and_can_be_revoked(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)

    share = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json={"grantee_user_id": str(SHARED_USER_ID)},
    )
    assert share.status_code == 201
    payload = share.json()
    token_url = payload["share_url"]

    resolved = client.get(
        f"/api/v1{token_url}",
        headers=auth_headers_for(),
        follow_redirects=False,
    )
    assert resolved.status_code == 302
    assert resolved.headers["location"] == f"/meetings/{seeds.ready_id}"

    grant_id = payload["grant"]["grant_id"]
    revoked = client.delete(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares/{grant_id}",
        headers=auth_headers(),
    )
    blocked = client.get(
        f"/api/v1{token_url}",
        headers=auth_headers_for(),
        follow_redirects=False,
    )

    assert revoked.status_code == 204
    assert blocked.status_code == 404
    event_dump = [event.event_type for event in audit_events(client, seeds.ready_id)]
    assert event_dump == ["share_granted", "share_link_opened", "share_revoked"]
    for event in audit_events(client, seeds.ready_id):
        assert "token" not in event.metadata_json
        assert "share_token_hash" not in event.metadata_json
