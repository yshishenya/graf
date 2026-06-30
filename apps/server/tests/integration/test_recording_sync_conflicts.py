from __future__ import annotations

import asyncio
from uuid import UUID

import twobrain_rec_server.ingest.desktop_sync as desktop_sync_module
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import ORG_ID, WORKSPACE_ID
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import (
    MediaRevision,
    Meeting,
    RegisteredDevice,
    UserIdentity,
    WorkspaceMembership,
)
from twobrain_rec_server.domain.statuses import DeletionState, MediaRevisionStatus, ProcessingStatus


def _sync_state(client, local_recording_id: str, local_media_revision_id: str, headers: dict[str, str] | None = None):
    return client.get(
        f"/api/v1/desktop/recordings/{local_recording_id}/sync-state",
        headers=headers or auth_headers(),
        params={"local_media_revision_id": local_media_revision_id},
    )


def test_sync_state_reports_metadata_conflict_without_overwriting_server_revision(client) -> None:
    local_id = "sync-conflict-metadata-001"
    finalized = create_finalized_meeting(client, local_id)
    server_revision_id = finalized["meeting"]["media_revision"]["media_revision_id"]

    response = _sync_state(client, local_id, "different-local-revision")

    assert response.status_code == 200
    body = response.json()
    assert body["local_media_revision_id"] == f"{local_id}--initial"
    assert body["media_revision"]["media_revision_id"] == server_revision_id
    assert body["conflict"]["state"] == "server_expected_metadata_mismatch"
    assert body["conflict"]["next_action"] == "manual_review"


def test_sync_state_reports_server_deleted_conflict_and_hides_review(client) -> None:
    local_id = "sync-conflict-deleted-001"
    finalized = create_finalized_meeting(client, local_id)
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])

    async def mark_deleted() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            media_revision = await db.get(MediaRevision, media_revision_id)
            assert meeting is not None
            assert media_revision is not None
            meeting.deletion_state = DeletionState.DELETING.value
            media_revision.status = MediaRevisionStatus.DELETED.value
            await db.commit()

    asyncio.run(mark_deleted())

    response = _sync_state(client, local_id, f"{local_id}--initial")

    assert response.status_code == 200
    body = response.json()
    assert body["meeting"]["deletion_state"] == "deleting"
    assert body["media_revision"]["status"] == "deleted"
    assert body["review"]["available"] is False
    assert body["conflict"]["state"] == "server_meeting_deleted"
    assert body["conflict"]["next_action"] == "stop_upload"


def test_sync_state_reports_stale_device_identity_conflict(client) -> None:
    local_id = "sync-conflict-device-001"
    create_finalized_meeting(client, local_id)
    stale_device_id = "40000000-0000-0000-0000-000000000088"

    async def add_device() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                RegisteredDevice(
                    id=UUID(stale_device_id),
                    workspace_id=WORKSPACE_ID,
                    user_id=UUID(auth_headers()["X-User-Id"]),
                    device_public_id="stale-active-device",
                    status="active",
                )
            )
            await db.commit()

    asyncio.run(add_device())

    response = _sync_state(
        client,
        local_id,
        f"{local_id}--initial",
        auth_headers() | {"X-Device-Id": stale_device_id},
    )

    assert response.status_code == 200
    assert response.json()["meeting"]["access_state"] == "stale_device_identity"
    assert response.json()["conflict"]["state"] == "stale_device_identity"
    assert response.json()["conflict"]["next_action"] == "reauthenticate_device"


def test_sync_state_reports_access_revoked_conflict_for_different_owner(client) -> None:
    local_id = "sync-conflict-access-001"
    create_finalized_meeting(client, local_id)
    other_user_id = "30000000-0000-0000-0000-000000000088"
    other_device_id = "40000000-0000-0000-0000-000000000087"

    async def add_user_and_device() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    UserIdentity(
                        id=UUID(other_user_id),
                        organization_id=ORG_ID,
                        external_subject=other_user_id,
                        display_name="Other User",
                    ),
                    WorkspaceMembership(
                        workspace_id=WORKSPACE_ID,
                        user_id=UUID(other_user_id),
                        role="member",
                        status="active",
                    ),
                    RegisteredDevice(
                        id=UUID(other_device_id),
                        workspace_id=WORKSPACE_ID,
                        user_id=UUID(other_user_id),
                        device_public_id="other-user-device",
                        status="active",
                    ),
                ]
            )
            await db.commit()

    asyncio.run(add_user_and_device())

    response = _sync_state(
        client,
        local_id,
        f"{local_id}--initial",
        auth_headers() | {"X-User-Id": other_user_id, "X-Device-Id": other_device_id},
    )

    assert response.status_code == 200
    assert response.json()["meeting"]["access_state"] == "access_revoked"
    assert response.json()["conflict"]["state"] == "access_revoked"
    assert response.json()["conflict"]["next_action"] == "sign_in_again"


def test_sync_state_reports_processing_failure_as_review_state(client) -> None:
    local_id = "sync-conflict-processing-001"
    finalized = create_finalized_meeting(client, local_id)
    meeting_id = UUID(finalized["meeting"]["meeting_id"])

    async def mark_processing_failed() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            meeting.processing_status = ProcessingStatus.FAILED_TERMINAL.value
            await db.commit()

    asyncio.run(mark_processing_failed())

    response = _sync_state(client, local_id, f"{local_id}--initial")

    assert response.status_code == 200
    body = response.json()
    assert body["processing"]["status"] == "failed_terminal"
    assert body["processing"]["reason_code"] == "processing_failed"
    assert body["review"]["available"] is True
    assert body["review"]["status"] == "failed"
    assert body["review"]["transcript_available"] is False
    assert body["review"]["diarization_available"] is False
    assert body["review"]["content_available"] is False
    assert body["review"]["web_url"] == f"/meetings/{meeting_id}"
    assert body["review"]["desktop_url"] == f"/desktop/meetings/{meeting_id}"
    assert body["conflict"]["state"] == "processing_failed"
    assert body["conflict"]["next_action"] == "contact_operator"


def test_sync_state_maps_upload_session_dependency_failure_to_safe_conflict(client, monkeypatch) -> None:
    local_id = "sync-conflict-dependency-001"
    create_finalized_meeting(client, local_id)

    async def fail_session_lookup(*_args, **_kwargs):
        raise RuntimeError("minio signed-url unavailable /private/path/mic.wav")

    monkeypatch.setattr(desktop_sync_module, "load_active_upload_session_for_meeting", fail_session_lookup)

    response = _sync_state(client, local_id, f"{local_id}--initial")

    assert response.status_code == 200
    body = response.json()
    assert body["conflict"]["state"] == "dependency_unavailable"
    assert body["conflict"]["reason"] == "sync_state_dependency_unavailable"
    assert body["conflict"]["next_action"] == "retry_later"
    assert body["review"]["available"] is False
    assert "/private/path" not in response.text
