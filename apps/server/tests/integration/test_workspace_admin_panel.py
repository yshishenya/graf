from __future__ import annotations

from uuid import uuid4

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import ORG_ID, USER_ID
from twobrain_rec_server.db.models import RegisteredDevice, Workspace, WorkspaceMembership


def test_personal_workspace_cannot_open_corporate_team_admin_surface(client) -> None:
    personal_workspace_id = uuid4()
    personal_device_id = uuid4()

    async def seed_personal_workspace() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                Workspace(
                    id=personal_workspace_id,
                    organization_id=ORG_ID,
                    owner_user_id=USER_ID,
                    kind="personal",
                    slug=f"personal-admin-{personal_workspace_id.hex}",
                    name="Личное пространство",
                )
            )
            await db.flush()
            db.add(
                WorkspaceMembership(
                    workspace_id=personal_workspace_id,
                    user_id=USER_ID,
                    role="owner",
                    status="active",
                )
            )
            db.add(
                RegisteredDevice(
                    id=personal_device_id,
                    workspace_id=personal_workspace_id,
                    user_id=USER_ID,
                    device_public_id="personal-admin-device",
                    status="active",
                    registration_state="approved",
                )
            )
            await db.commit()

    client.portal.call(seed_personal_workspace)
    response = client.get(
        "/api/v1/admin/overview",
        headers=auth_headers()
        | {
            "X-Workspace-Id": str(personal_workspace_id),
            "X-Device-Id": str(personal_device_id),
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "corporate_admin_required"
    assert "user_counts" not in response.text
