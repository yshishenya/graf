from __future__ import annotations

from uuid import UUID

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import ORG_ID, USER_ID
from twobrain_rec_server.db.models import RegisteredDevice, Workspace, WorkspaceMembership

OTHER_WORKSPACE_ID = UUID("20000000-0000-0000-0000-0000000000aa")
OTHER_DEVICE_ID = UUID("40000000-0000-0000-0000-0000000000aa")


def seed_second_workspace_for_same_user(client) -> None:
    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                Workspace(
                    id=OTHER_WORKSPACE_ID,
                    organization_id=ORG_ID,
                    slug="other-rls-workspace",
                    name="Other RLS Workspace",
                )
            )
            db.add(
                WorkspaceMembership(
                    workspace_id=OTHER_WORKSPACE_ID,
                    user_id=USER_ID,
                    role="member",
                    status="active",
                )
            )
            db.add(
                RegisteredDevice(
                    id=OTHER_DEVICE_ID,
                    workspace_id=OTHER_WORKSPACE_ID,
                    user_id=USER_ID,
                    device_public_id="other-rls-device",
                    status="active",
                )
            )
            await db.commit()

    client.portal.call(seed)


def other_workspace_headers() -> dict[str, str]:
    return auth_headers() | {
        "X-Workspace-Id": str(OTHER_WORKSPACE_ID),
        "X-Device-Id": str(OTHER_DEVICE_ID),
    }


def test_cross_workspace_upload_session_read_returns_not_found(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "rls-upload-read", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={},
    ).json()
    seed_second_workspace_for_same_user(client)

    response = client.get(
        f"/api/v1/upload-sessions/{session['session_id']}",
        headers=other_workspace_headers(),
    )

    assert response.status_code == 404
    assert response.json()["code"] in {"upload_session_not_found", "tenant_resource_not_found"}


def test_cross_workspace_processing_status_read_returns_not_found(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "rls-processing-read", "duration_seconds": 60},
    ).json()
    seed_second_workspace_for_same_user(client)

    response = client.get(
        f"/api/v1/meetings/{meeting['meeting_id']}/processing",
        headers=other_workspace_headers(),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "meeting_not_found"
