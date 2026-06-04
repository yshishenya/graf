from uuid import UUID

from twobrain_rec_server.db.models import (
    Organization,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import (
    FORGED_USER_ID,
    ORG_ID,
    REVOKED_DEVICE_ID,
    WORKSPACE_ID,
)

OTHER_WORKSPACE = UUID("20000000-0000-0000-0000-000000000099")
OTHER_ORG_ID = UUID("10000000-0000-0000-0000-000000000099")
OTHER_USER_ID = UUID("30000000-0000-0000-0000-000000000002")
OTHER_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000002")
OTHER_WORKSPACE_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000004")
INACTIVE_USER_ID = UUID("30000000-0000-0000-0000-000000000003")
INACTIVE_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000003")


def test_cross_workspace_upload_session_read_is_denied_without_existence_leak(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "tenant-denial", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={},
    ).json()
    wrong_headers = auth_headers() | {"X-Workspace-Id": str(OTHER_WORKSPACE)}
    response = client.get(f"/api/v1/upload-sessions/{session['session_id']}", headers=wrong_headers)
    assert response.status_code in {403, 404}
    assert "object_key" not in response.text


def test_forged_user_without_workspace_membership_is_denied(client) -> None:
    forged_headers = auth_headers() | {"X-User-Id": str(FORGED_USER_ID)}
    response = client.post(
        "/api/v1/meetings",
        headers=forged_headers,
        json={"local_recording_id": "forged-user", "duration_seconds": 60},
    )

    assert response.status_code == 403


def test_wrong_organization_header_is_denied(client) -> None:
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers() | {"X-Organization-Id": str(OTHER_ORG_ID)},
        json={"local_recording_id": "wrong-organization", "duration_seconds": 60},
    )

    assert response.status_code == 403


def test_revoked_device_is_denied_for_ingest_operations(client) -> None:
    revoked_headers = auth_headers() | {"X-Device-Id": str(REVOKED_DEVICE_ID)}
    response = client.post(
        "/api/v1/meetings",
        headers=revoked_headers,
        json={"local_recording_id": "revoked-device", "duration_seconds": 60},
    )

    assert response.status_code == 403


def test_auth_fails_closed_without_persistent_context(client) -> None:
    delattr(client.app.state, "db_sessionmaker")

    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "no-db-auth", "duration_seconds": 60},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "auth_context_unavailable"


def test_inactive_membership_is_denied(client) -> None:
    async def seed_inactive_membership() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(UserIdentity(id=INACTIVE_USER_ID, organization_id=ORG_ID, external_subject=str(INACTIVE_USER_ID)))
            db.add(
                WorkspaceMembership(
                    workspace_id=WORKSPACE_ID,
                    user_id=INACTIVE_USER_ID,
                    role="member",
                    status="inactive",
                )
            )
            db.add(
                RegisteredDevice(
                    id=INACTIVE_DEVICE_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=INACTIVE_USER_ID,
                    device_public_id="inactive-device",
                    status="active",
                )
            )
            await db.commit()

    client.portal.call(seed_inactive_membership)
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers() | {"X-User-Id": str(INACTIVE_USER_ID), "X-Device-Id": str(INACTIVE_DEVICE_ID)},
        json={"local_recording_id": "inactive-membership", "duration_seconds": 60},
    )

    assert response.status_code == 403


def test_device_bound_to_another_user_is_denied(client) -> None:
    async def seed_cross_bound_device() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(UserIdentity(id=OTHER_USER_ID, organization_id=ORG_ID, external_subject=str(OTHER_USER_ID)))
            db.add(WorkspaceMembership(workspace_id=WORKSPACE_ID, user_id=OTHER_USER_ID, role="member", status="active"))
            db.add(
                RegisteredDevice(
                    id=OTHER_DEVICE_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=OTHER_USER_ID,
                    device_public_id="other-device",
                    status="active",
                )
            )
            await db.commit()

    client.portal.call(seed_cross_bound_device)
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers() | {"X-Device-Id": str(OTHER_DEVICE_ID)},
        json={"local_recording_id": "wrong-device-user", "duration_seconds": 60},
    )

    assert response.status_code == 403


def test_device_bound_to_another_workspace_is_denied(client) -> None:
    async def seed_other_workspace_device() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(Organization(id=OTHER_ORG_ID, slug="other-org", name="Other Org"))
            db.add(Workspace(id=OTHER_WORKSPACE, organization_id=OTHER_ORG_ID, slug="other", name="Other Workspace"))
            db.add(
                RegisteredDevice(
                    id=OTHER_WORKSPACE_DEVICE_ID,
                    workspace_id=OTHER_WORKSPACE,
                    user_id=UUID("30000000-0000-0000-0000-000000000001"),
                    device_public_id="other-workspace-device",
                    status="active",
                )
            )
            await db.commit()

    client.portal.call(seed_other_workspace_device)
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers() | {"X-Device-Id": str(OTHER_WORKSPACE_DEVICE_ID)},
        json={"local_recording_id": "wrong-device-workspace", "duration_seconds": 60},
    )

    assert response.status_code == 403


def test_same_workspace_meeting_hijack_is_denied(client) -> None:
    async def seed_other_owner() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(UserIdentity(id=OTHER_USER_ID, organization_id=ORG_ID, external_subject=str(OTHER_USER_ID)))
            db.add(WorkspaceMembership(workspace_id=WORKSPACE_ID, user_id=OTHER_USER_ID, role="member", status="active"))
            db.add(
                RegisteredDevice(
                    id=OTHER_DEVICE_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=OTHER_USER_ID,
                    device_public_id="other-owner-device",
                    status="active",
                )
            )
            await db.commit()

    client.portal.call(seed_other_owner)
    other_headers = auth_headers() | {"X-User-Id": str(OTHER_USER_ID), "X-Device-Id": str(OTHER_DEVICE_ID)}
    meeting = client.post(
        "/api/v1/meetings",
        headers=other_headers,
        json={"local_recording_id": "same-workspace-hijack", "duration_seconds": 60},
    ).json()

    response = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "meeting_scope_denied"
