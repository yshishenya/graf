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


def test_owner_admin_member_workspace_access_outcomes(client) -> None:
    asyncio.run(_seed_roles(client))

    owner = client.get("/api/v1/admin/overview", headers=auth_headers())
    admin = client.get(
        "/api/v1/admin/overview",
        headers=auth_headers_for(user_id=DEFAULT_ADMIN_USER_ID, device_id=DEFAULT_ADMIN_DEVICE_ID),
    )
    member = client.get(
        "/api/v1/admin/overview",
        headers=auth_headers_for(user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID),
    )
    unauthenticated = client.get("/api/v1/admin/overview")

    assert owner.status_code == 200
    assert admin.status_code == 200
    assert member.status_code == 403
    assert unauthenticated.status_code == 401


async def _seed_roles(client) -> None:
    async with client.app_state["sessionmaker"]() as db:
        await seed_default_workspace_admin_roles(db)

