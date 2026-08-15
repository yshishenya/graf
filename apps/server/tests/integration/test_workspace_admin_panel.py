from __future__ import annotations

from uuid import uuid4

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import PERSONAL_WORKSPACE_ID, USER_ID
from twobrain_rec_server.db.models import RegisteredDevice


def test_personal_workspace_cannot_open_corporate_team_admin_surface(client) -> None:
    personal_workspace_id = PERSONAL_WORKSPACE_ID
    personal_device_id = uuid4()

    async def seed_personal_workspace() -> None:
        async with client.app_state["sessionmaker"]() as db:
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
