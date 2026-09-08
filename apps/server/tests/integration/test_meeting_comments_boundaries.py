"""Independent HTTP checks for discussion permissions and durable pagination."""
from uuid import UUID, uuid4

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.fixtures.cabinet_access import SHARED_USER_ID, auth_headers_for
from tests.integration.test_meeting_comments import setup_comments
from twobrain_rec_server.db.models import Meeting, WorkspaceMembership


def create(client, url, template, headers=None, **fields):
    response = client.post(url, headers=headers or auth_headers(), json={**template, "request_id": str(uuid4()), **fields})
    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def test_comment_pagination_unicode_and_revocation(client):
    seeds, url, body = setup_comments(client)
    shared = client.post(f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares", headers=auth_headers(),
        json={"audience_type": "user", "audience_id": str(SHARED_USER_ID), "content_scope": "full_meeting", "can_comment": True})
    assert shared.status_code == 201, shared.text
    text = "  🧪\n@Shared User — синтетический текст  "
    start = text.index("@")
    first = create(client, url, body, body=text, mentions=[{"user_id": str(SHARED_USER_ID), "start": start, "end": start + len("@Shared User")}])
    assert first["body"] == text
    assert first["mentions"][0]["start"] == start
    roots = [first] + [create(client, url, body) for _ in range(2)]
    page = client.get(url, headers=auth_headers(), params={"limit": 2}).json()
    next_page = client.get(url, headers=auth_headers(), params={"limit": 2, "cursor": page["next_cursor"]}).json()
    assert [item["id"] for item in page["items"] + next_page["items"]] == [item["id"] for item in roots]
    assert next_page["next_cursor"] is None
    reply_url = url + "/" + first["id"] + "/replies"
    replies = [create(client, reply_url, {"body": "Синтетический ответ", "mentions": []}, auth_headers_for()) for _ in range(3)]
    page = client.get(reply_url, headers=auth_headers(), params={"limit": 2}).json()
    next_page = client.get(reply_url, headers=auth_headers(), params={"limit": 2, "cursor": page["next_cursor"]}).json()
    assert [item["id"] for item in page["items"] + next_page["items"]] == [item["id"] for item in replies]
    assert client.get(url + "/" + replies[1]["id"], headers=auth_headers()).json()["id"] == first["id"]
    assert client.get(url, headers=auth_headers(), params={"cursor": "invalid"}).status_code == 422
    assert client.get(reply_url, headers=auth_headers(), params={"limit": 101}).status_code == 422
    assert client.post(url + "/" + replies[0]["id"] + "/replies", headers=auth_headers(),
        json={"request_id": str(uuid4()), "body": "Nested reply", "mentions": []}).status_code == 422
    grant_id = shared.json()["grant"]["grant_id"]
    assert client.delete(f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares/{grant_id}", headers=auth_headers()).status_code == 204
    assert client.post(reply_url, headers=auth_headers_for(), json={"request_id": str(uuid4()), "body": "Revoked", "mentions": []}).status_code == 404
    assert client.get(url, headers=auth_headers_for()).status_code == 404


def test_legacy_admin_cannot_self_escalate_but_explicit_editor_can_moderate(client):
    seeds, url, body = setup_comments(client)

    async def make_admin():
        async with client.app_state["sessionmaker"]() as db:
            membership = await db.scalar(select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == WORKSPACE_ID, WorkspaceMembership.user_id == SHARED_USER_ID))
            membership.role = "admin"
            await db.commit()
    client.portal.call(make_admin)
    grant_url = f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares"
    shared = client.post(grant_url, headers=auth_headers(), json={"audience_type": "user", "audience_id": str(SHARED_USER_ID), "content_scope": "full_meeting"})
    assert shared.status_code == 201, shared.text
    permission_url = grant_url + "/" + shared.json()["grant"]["grant_id"] + "/permissions"
    desired = {"can_comment": True, "can_edit": True}
    assert client.patch(permission_url, headers=auth_headers_for(), json=desired).status_code == 403
    escalation = client.post(grant_url, headers=auth_headers_for(), json={"audience_type": "user", "audience_id": str(SHARED_USER_ID), "content_scope": "full_meeting", **desired})
    assert escalation.status_code == 403
    root = create(client, url, body)
    assert client.patch(permission_url, headers=auth_headers(), json=desired).status_code == 200
    root_url = url + "/" + root["id"]
    assert client.patch(root_url, headers=auth_headers_for(), json={"expected_version": root["version"], "body": "Cannot replace another author's words", "mentions": []}).status_code == 403
    resolved = client.put(root_url + "/resolution", headers=auth_headers_for(), json={"expected_version": root["version"], "resolved": True})
    assert resolved.status_code == 200, resolved.text
    reopened = client.put(root_url + "/resolution", headers=auth_headers_for(), json={"expected_version": resolved.json()["version"], "resolved": False})
    assert reopened.status_code == 200, reopened.text
    assert client.request("DELETE", root_url, headers=auth_headers_for(), json={"expected_version": reopened.json()["version"]}).status_code == 204


def test_comment_source_range_and_deletion_fences(client):
    seeds, url, body = setup_comments(client)
    for invalid in [{"start_ms": True}, {"start_ms": 10**12}, {"start_ms": 2000, "end_ms": 1000},
                    {"source_segment_id": str(uuid4())}, {"body": "   "},
                    {"mentions": [{"user_id": str(SHARED_USER_ID), "start": 0, "end": 999}]}]:
        response = client.post(url, headers=auth_headers(), json={**body, **invalid})
        assert response.status_code == 422, response.text
    assert client.get(url, headers=auth_headers(), params={"workspace_id": str(uuid4())}).status_code == 404
    root = create(client, url, body)

    async def deleting():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, UUID(str(seeds.ready_id)))
            meeting.deletion_state = "requested"
            await db.commit()
    client.portal.call(deleting)
    assert client.get(url, headers=auth_headers()).status_code == 404
    assert client.patch(url + "/" + root["id"], headers=auth_headers(), json={"expected_version": 1, "body": "Late write", "mentions": []}).status_code == 404
