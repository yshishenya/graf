"""F262 scope and origin-only acceptance against PostgreSQL and real API auth."""

import asyncio
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet_access import (
    SHARED_DEVICE_ID,
    SHARED_USER_ID,
    add_workspace_user,
)
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.db.models import (
    AuthSession,
    AuthSessionDeviceBinding,
    LocalPurgeTask,
    Meeting,
    MeetingDeletionArtifactState,
    MeetingDeletionReport,
    MeetingDeletionRequest,
    MeetingLifecycleAuditEvent,
    RecordingOriginCancellation,
    RetentionPolicySnapshot,
    WorkspaceMembership,
)
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY
from twobrain_rec_server.main import create_app


async def _manager_session(client, *, revoke_session_id=None):
    async with client.app_state["sessionmaker"]() as db:
        if revoke_session_id is not None:
            previous = await db.get(AuthSession, revoke_session_id)
            previous.status = "revoked"
        session = await issue_auth_session(
            db, user_id=SHARED_USER_ID, workspace_id=WORKSPACE_ID,
            device_id=SHARED_DEVICE_ID, provider="synthetic-f262",
        )
        db.add(AuthSessionDeviceBinding(
            auth_session_id=session.id, registered_device_id=SHARED_DEVICE_ID,
            device_state="trusted",
        ))
        await db.commit()
        return session


def _manager_headers(session):
    # No legacy identity headers: the route resolves the actor from a real DB session.
    return {
        "X-Auth-Session": session.token,
        "X-Graf-Expected-Actor": str(SHARED_USER_ID),
        "X-Graf-Expected-Workspace": str(WORKSPACE_ID),
    }


@pytest.mark.parametrize("manager_role", ["owner", "admin"])
def test_manager_delete_reauthorizes_current_role_after_session_and_app_restart(client, manager_role):
    add_workspace_user(client, role=manager_role)
    meeting_ids = []
    for _ in range(2):
        created = client.post("/api/v1/meetings", headers=auth_headers(), json={
            "local_recording_id": str(uuid4()), "duration_seconds": 10,
            "title": "Synthetic F262 manager scope",
        })
        assert created.status_code == 200
        meeting_ids.append(UUID(created.json()["meeting_id"]))
    deleted_id, untouched_id = meeting_ids
    delete_url = f"/api/v1/cabinet/meetings/{deleted_id}/deletion-requests"
    report_url = f"/api/v1/cabinet/meetings/{deleted_id}/deletion-report"
    payload = {"confirmation_boundary": BOUNDED_DELETE_COPY}

    first_session = asyncio.run(_manager_session(client))
    deleted = client.post(delete_url, headers=_manager_headers(first_session), json=payload)
    assert deleted.status_code == 202
    receipt = deleted.json()
    assert receipt["meeting_id"] == str(deleted_id)
    assert receipt["receipt_type"] == "meeting_deletion"

    async def inspect_author_and_actor():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, deleted_id)
            request = await db.get(MeetingDeletionRequest, UUID(receipt["request_id"]))
            assert meeting.created_by_user_id == USER_ID != SHARED_USER_ID
            assert meeting.deleted_at is not None and meeting.deletion_epoch > 0
            assert request.requested_by_user_id == SHARED_USER_ID
            assert request.requested_by_device_id == SHARED_DEVICE_ID
            assert request.workspace_id == meeting.workspace_id == WORKSPACE_ID

    asyncio.run(inspect_author_and_actor())
    second_session = asyncio.run(_manager_session(client, revoke_session_id=first_session.id))
    rejected_old_session = client.post(delete_url, headers=_manager_headers(first_session), json=payload)
    assert rejected_old_session.status_code == 401
    assert receipt["request_id"] not in rejected_old_session.text

    # Fresh application, connection pool, request client and cookies; only PostgreSQL
    # and synthetic object storage survive. This is not an OS process restart.
    with patch("twobrain_rec_server.main.get_storage", return_value=client.app_state["storage"]):
        restarted_app = create_app(client.app.state.settings)
    assert restarted_app is not client.app
    assert restarted_app.state.db_engine is not client.app.state.db_engine
    with TestClient(restarted_app) as restarted:
        repeated = restarted.post(delete_url, headers=_manager_headers(second_session), json=payload)
        assert repeated.status_code == 202
        assert repeated.json() == receipt
        assert restarted.get(report_url, headers=_manager_headers(second_session)).status_code == 200

        async def remove_manager_permission():
            async with client.app_state["sessionmaker"]() as db:
                membership = await db.get(WorkspaceMembership, {
                    "workspace_id": WORKSPACE_ID, "user_id": SHARED_USER_ID,
                })
                membership.role = "member"
                await db.commit()

        asyncio.run(remove_manager_permission())
        third_session = asyncio.run(_manager_session(client))
        for session in (second_session, third_session):
            # Neither a formerly privileged session nor a newly issued session can
            # replay the old receipt or delete another creator's live meeting now.
            for meeting_id in (deleted_id, untouched_id):
                denied = restarted.post(
                    f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
                    headers=_manager_headers(session), json=payload,
                )
                assert denied.status_code == 404
                assert denied.json()["code"] == "meeting_not_found"
                assert receipt["request_id"] not in denied.text
                assert "receipt_type" not in denied.json()
            assert restarted.get(report_url, headers=_manager_headers(session)).status_code == 404

    async def inspect_no_denied_mutation():
        async with client.app_state["sessionmaker"]() as db:
            untouched = await db.get(Meeting, untouched_id)
            assert untouched.deleted_at is None and untouched.deletion_state == "none"
            assert await db.scalar(select(func.count()).select_from(MeetingDeletionRequest)) == 1
            assert await db.scalar(select(func.count()).select_from(MeetingDeletionReport)) == 1

    asyncio.run(inspect_no_denied_mutation())


def test_origin_only_receipt_creates_no_meeting_or_meeting_purge_foreign_keys(client):
    origin = str(uuid4())
    meeting_models = (
        Meeting, MeetingDeletionRequest, MeetingDeletionReport, MeetingDeletionArtifactState,
        LocalPurgeTask, MeetingLifecycleAuditEvent, RetentionPolicySnapshot,
    )

    async def counts():
        async with client.app_state["sessionmaker"]() as db:
            assert db.bind.dialect.name == "postgresql"
            return {model.__tablename__: await db.scalar(select(func.count()).select_from(model))
                    for model in meeting_models}

    before = asyncio.run(counts())
    assert set(before.values()) == {0}
    url = f"/api/v1/desktop/recordings/{origin}/deletion-requests"
    payload = {"operation_id": str(uuid4()), "confirmation_boundary": BOUNDED_DELETE_COPY}
    first = client.post(url, headers=auth_headers(), json=payload)
    assert first.status_code == 202
    receipt = first.json()
    assert receipt["receipt_type"] == "origin_cancellation"
    assert "meeting_id" not in receipt
    assert client.post(url, headers=auth_headers(), json=payload).json() == receipt
    lookup = client.post("/api/v1/desktop/recordings/lifecycle", headers=auth_headers(), json={
        "origins": [origin],
    })
    assert lookup.status_code == 200
    assert lookup.json()[0]["receipt"] == receipt
    assert lookup.json()[0]["state"] == "canceled_before_creation"
    late_create = client.post("/api/v1/meetings", headers=auth_headers(), json={
        "local_recording_id": origin, "duration_seconds": 10,
    })
    assert late_create.status_code == 409
    assert late_create.json()["code"] == "recording_deletion_active"
    assert asyncio.run(counts()) == before

    async def inspect_only_marker():
        async with client.app_state["sessionmaker"]() as db:
            markers = (await db.scalars(select(RecordingOriginCancellation))).all()
            assert len(markers) == 1
            marker = markers[0]
            assert marker.id == UUID(receipt["request_id"])
            assert marker.created_by_user_id == USER_ID
            assert marker.workspace_id == WORKSPACE_ID
            assert marker.local_recording_id == origin

    asyncio.run(inspect_only_marker())
