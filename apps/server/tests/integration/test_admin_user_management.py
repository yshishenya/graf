from __future__ import annotations

import asyncio
from uuid import UUID

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.admin import (
    DEFAULT_ADMIN_DEVICE_ID,
    DEFAULT_ADMIN_USER_ID,
    DEFAULT_MEMBER_DEVICE_ID,
    DEFAULT_MEMBER_USER_ID,
    auth_headers_for,
    seed_default_workspace_admin_roles,
)
from twobrain_rec_server.db.models import UserIdentity, WorkspaceMembership, WorkspaceSubscription


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


def test_owner_membership_loss_revokes_recurring_authority(client) -> None:
    async def seed_subscription() -> None:
        async with client.app_state["sessionmaker"]() as db:
            second_owner_id = UUID("10000000-0000-0000-0000-000000000002")
            db.add_all(
                [
                    UserIdentity(
                        id=second_owner_id,
                        organization_id=ORG_ID,
                        external_subject=str(second_owner_id),
                        display_name="Second Owner",
                    ),
                    WorkspaceMembership(
                        workspace_id=WORKSPACE_ID,
                        user_id=second_owner_id,
                        role="owner",
                        status="active",
                    ),
                    WorkspaceSubscription(
                        workspace_id=WORKSPACE_ID,
                        billing_owner_id=USER_ID,
                        state="personal",
                        plan_code="personal",
                        cycle="month",
                        recurring_allowed=True,
                    ),
                ]
            )
            await db.commit()
    asyncio.run(seed_subscription())
    response = client.patch(
        f"/api/v1/admin/users/{USER_ID}/membership",
        headers=auth_headers(),
        json={"role": "member", "reason_code": "handoff"},
    )
    assert response.status_code == 200

    async def read_subscription() -> WorkspaceSubscription:
        async with client.app_state["sessionmaker"]() as db:
            return await db.get(WorkspaceSubscription, WORKSPACE_ID)

    subscription = asyncio.run(read_subscription())
    assert subscription is not None
    assert subscription.recurring_allowed is False
    assert subscription.recurring_authority_version == 1


async def _seed_roles(client) -> None:
    async with client.app_state["sessionmaker"]() as db:
        await seed_default_workspace_admin_roles(db)
