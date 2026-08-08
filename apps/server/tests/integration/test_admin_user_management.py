from __future__ import annotations

import asyncio

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.admin import (
    DEFAULT_ADMIN_DEVICE_ID,
    DEFAULT_ADMIN_USER_ID,
    DEFAULT_MEMBER_DEVICE_ID,
    DEFAULT_MEMBER_USER_ID,
    auth_headers_for,
    seed_default_workspace_admin_roles,
)


def test_admin_can_manage_members_but_not_owner_authority(client) -> None:
    asyncio.run(_seed_roles(client))

    block_member = client.patch(
        f"/api/v1/admin/users/{DEFAULT_MEMBER_USER_ID}/membership",
        headers=auth_headers_for(user_id=DEFAULT_ADMIN_USER_ID, device_id=DEFAULT_ADMIN_DEVICE_ID),
        json={"status": "blocked", "reason_code": "policy_violation"},
    )
    assert block_member.status_code == 200
    assert block_member.json()["status"] == "blocked"

    promote_member = client.patch(
        f"/api/v1/admin/users/{DEFAULT_MEMBER_USER_ID}/membership",
        headers=auth_headers_for(user_id=DEFAULT_ADMIN_USER_ID, device_id=DEFAULT_ADMIN_DEVICE_ID),
        json={"role": "admin", "reason_code": "needs_admin"},
    )
    assert promote_member.status_code == 403
    assert promote_member.json()["code"] == "admin_role_authority_forbidden"


def test_last_active_owner_cannot_be_downgraded_or_blocked(client) -> None:
    response = client.patch(
        "/api/v1/admin/users/30000000-0000-0000-0000-000000000001/membership",
        headers=auth_headers(),
        json={"role": "admin", "reason_code": "handoff"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "last_owner_protection"


def test_user_detail_is_workspace_scoped_and_metadata_safe(client) -> None:
    asyncio.run(_seed_roles(client))

    response = client.get(f"/api/v1/admin/users/{DEFAULT_MEMBER_USER_ID}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == str(DEFAULT_MEMBER_USER_ID)
    assert payload["role"] == "member"
    assert "sessions" in payload
    assert payload["devices"][0]["device_id"] == str(DEFAULT_MEMBER_DEVICE_ID)
    assert payload["sessions"]["active"] == 0
    assert "files" in payload
    assert "usage" in payload
    assert "recent_audit" in payload
    assert "transcript_text" not in response.text
    assert "storage_object_key" not in response.text


async def _seed_roles(client) -> None:
    async with client.app_state["sessionmaker"]() as db:
        await seed_default_workspace_admin_roles(db)
