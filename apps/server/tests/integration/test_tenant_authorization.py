from uuid import UUID

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import (
    DEVICE_ID,
    FORGED_USER_ID,
    ORG_ID,
    REVOKED_DEVICE_ID,
    USER_ID,
    WORKSPACE_ID,
)
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.auth.workspace_onboarding import ensure_personal_workspace
from twobrain_rec_server.db.models import (
    AuthSession,
    AuthSessionDeviceBinding,
    Organization,
    RegisteredDevice,
    UploadSession,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)

OTHER_WORKSPACE = UUID("20000000-0000-0000-0000-000000000099")
OTHER_ORG_ID = UUID("10000000-0000-0000-0000-000000000099")
OTHER_USER_ID = UUID("30000000-0000-0000-0000-000000000002")
OTHER_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000002")
OTHER_WORKSPACE_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000004")
INACTIVE_USER_ID = UUID("30000000-0000-0000-0000-000000000003")
INACTIVE_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000003")
QUARANTINED_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000005")
REVOKED_MEMBERSHIP_USER_ID = UUID("30000000-0000-0000-0000-000000000004")
REVOKED_MEMBERSHIP_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000006")


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


def test_quarantined_device_is_denied_for_ingest_operations(client) -> None:
    async def seed_quarantined_device() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                RegisteredDevice(
                    id=QUARANTINED_DEVICE_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=USER_ID,
                    device_public_id="quarantined-device",
                    status="quarantined",
                    registration_state="approved",
                )
            )
            await db.commit()

    client.portal.call(seed_quarantined_device)
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers() | {"X-Device-Id": str(QUARANTINED_DEVICE_ID)},
        json={"local_recording_id": "quarantined-device", "duration_seconds": 60},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "device_quarantined"


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
    assert response.json()["code"] == "device_revoked"


def test_auth_fails_closed_without_persistent_context(client) -> None:
    delattr(client.app.state, "db_sessionmaker")

    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "no-db-auth", "duration_seconds": 60},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "auth_context_unavailable"


def test_production_rejects_legacy_header_auth_without_session(client) -> None:
    original_env = client.app.state.settings.env
    client.app.state.settings.env = "production"
    try:
        response = client.post(
            "/api/v1/meetings",
            headers=auth_headers(),
            json={"local_recording_id": "production-legacy-auth", "duration_seconds": 60},
        )
    finally:
        client.app.state.settings.env = original_env

    assert response.status_code == 401
    assert response.json()["code"] == "legacy_header_auth_disabled"


def test_inactive_membership_is_denied(client) -> None:
    async def seed_inactive_membership() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(UserIdentity(id=INACTIVE_USER_ID, organization_id=ORG_ID, external_subject=str(INACTIVE_USER_ID)))
            await db.flush()
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


def test_revoked_membership_is_denied_for_new_workspace_requests(client) -> None:
    async def seed_revoked_membership() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                UserIdentity(
                    id=REVOKED_MEMBERSHIP_USER_ID,
                    organization_id=ORG_ID,
                    external_subject=str(REVOKED_MEMBERSHIP_USER_ID),
                )
            )
            await db.flush()
            db.add(
                WorkspaceMembership(
                    workspace_id=WORKSPACE_ID,
                    user_id=REVOKED_MEMBERSHIP_USER_ID,
                    role="member",
                    status="revoked",
                )
            )
            db.add(
                RegisteredDevice(
                    id=REVOKED_MEMBERSHIP_DEVICE_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=REVOKED_MEMBERSHIP_USER_ID,
                    device_public_id="revoked-membership-device",
                    status="active",
                )
            )
            await db.commit()

    client.portal.call(seed_revoked_membership)
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers()
        | {
            "X-User-Id": str(REVOKED_MEMBERSHIP_USER_ID),
            "X-Device-Id": str(REVOKED_MEMBERSHIP_DEVICE_ID),
        },
        json={"local_recording_id": "revoked-membership", "duration_seconds": 60},
    )

    assert response.status_code == 403


def test_revoked_scoped_session_is_invalidated_without_retargeting_personal_access(client) -> None:
    corporate_meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "revoked-space-upload", "duration_seconds": 60},
    )
    assert corporate_meeting.status_code == 200
    corporate_upload = client.post(
        f"/api/v1/meetings/{corporate_meeting.json()['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={},
    )
    assert corporate_upload.status_code == 200
    corporate_upload_id = UUID(corporate_upload.json()["session_id"])

    async def seed() -> tuple[str, str, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            personal = await ensure_personal_workspace(
                db,
                organization_id=ORG_ID,
                user_id=USER_ID,
            )
            personal_device = RegisteredDevice(
                workspace_id=personal.id,
                user_id=USER_ID,
                device_public_id="personal-fallback-browser",
                status="active",
                registration_state="approved",
            )
            db.add(personal_device)
            await db.flush()
            corporate_session = await issue_auth_session(
                db,
                user_id=USER_ID,
                workspace_id=WORKSPACE_ID,
                device_id=DEVICE_ID,
                provider="revocation-test",
            )
            personal_session = await issue_auth_session(
                db,
                user_id=USER_ID,
                workspace_id=personal.id,
                device_id=personal_device.id,
                provider="revocation-test",
            )
            db.add_all(
                (
                    AuthSessionDeviceBinding(
                        auth_session_id=corporate_session.id,
                        registered_device_id=DEVICE_ID,
                        device_state="trusted",
                    ),
                    AuthSessionDeviceBinding(
                        auth_session_id=personal_session.id,
                        registered_device_id=personal_device.id,
                        device_state="trusted",
                    ),
                )
            )
            membership = await db.get(
                WorkspaceMembership,
                {"workspace_id": WORKSPACE_ID, "user_id": USER_ID},
            )
            assert membership is not None
            membership.status = "revoked"
            await db.commit()
            return corporate_session.token, personal_session.token, corporate_session.id

    corporate_token, personal_token, corporate_session_id = client.portal.call(seed)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, corporate_token)

    denied = client.get("/desktop/meetings")
    assert denied.status_code == 403
    assert denied.json()["code"] == "workspace_scope_denied"
    assert denied.headers["X-GRAF-Cabinet-Recovery"] == "reselect-space"

    async def read_revoked_session() -> str:
        async with client.app_state["sessionmaker"]() as db:
            session = await db.get(AuthSession, corporate_session_id)
            assert session is not None
            return session.status

    assert client.portal.call(read_revoked_session) == "revoked"
    client.cookies.clear()
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, corporate_token)
    assert client.get("/settings/spaces").status_code == 401

    client.cookies.clear()
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, personal_token)
    fallback = client.get("/settings/spaces")
    assert fallback.status_code == 200
    spaces = fallback.json()["spaces"]
    assert len(spaces) == 1
    assert spaces[0]["name"] == "Личное пространство"
    assert spaces[0]["kind"] == "personal"
    assert spaces[0]["role"] == "owner"
    assert spaces[0]["active"] is True

    blocked_upload = client.get(f"/api/v1/upload-sessions/{corporate_upload_id}")
    assert blocked_upload.status_code in {403, 404}

    async def read_upload_scope() -> UUID:
        async with client.app_state["sessionmaker"]() as db:
            upload = await db.get(UploadSession, corporate_upload_id)
            assert upload is not None
            return upload.workspace_id

    assert client.portal.call(read_upload_scope) == WORKSPACE_ID


def test_device_bound_to_another_user_is_denied(client) -> None:
    async def seed_cross_bound_device() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(UserIdentity(id=OTHER_USER_ID, organization_id=ORG_ID, external_subject=str(OTHER_USER_ID)))
            await db.flush()
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
            await db.flush()
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
            await db.flush()
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
