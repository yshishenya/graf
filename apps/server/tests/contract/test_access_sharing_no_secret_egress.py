import json

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import SHARED_USER_ID, add_workspace_user


def _dump(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_share_token_and_storage_identifiers_do_not_leak_into_detail_or_activity(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)

    share = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json={"grantee_user_id": str(SHARED_USER_ID)},
    )
    assert share.status_code == 201
    raw_share_url = share.json()["share_url"]

    detail = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())
    activity = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}/activity", headers=auth_headers())

    body = _dump({"detail": detail.json(), "activity": activity.json()})
    assert raw_share_url not in body
    assert "share_token_hash" not in body
    assert "storage_object_key" not in body
    assert "sha256" not in body
    assert "metadata_only" in body
