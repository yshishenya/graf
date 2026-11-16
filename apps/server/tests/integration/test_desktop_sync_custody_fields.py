from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import MediaRevision, Meeting, UploadSession
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.domain.statuses import (
    MediaRevisionSourceKind,
    MediaRevisionStatus,
    UploadSessionStatus,
)
from twobrain_rec_server.ingest.store import (
    archive_audio_for_revision,
    finalized_upload_custody_for_revision,
)


def _sync_state(client, local_recording_id: str) -> dict[str, object]:
    response = client.get(
        f"/api/v1/desktop/recordings/{local_recording_id}/sync-state",
        headers=auth_headers(),
        params={"local_media_revision_id": f"{local_recording_id}--initial"},
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def _tenant_scope() -> TenantScope:
    return TenantScope(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        user_id=USER_ID,
        device_id=DEVICE_ID,
    )


def test_sync_state_exposes_revision_scoped_custody_and_retention(client) -> None:
    finalized = create_finalized_meeting(client, "custody-fields-true", archive_audio=True)
    meeting_id = UUID(str(finalized["meeting"]["meeting_id"]))
    revision_id = UUID(str(finalized["meeting"]["media_revision"]["media_revision_id"]))
    local_revision_id = "custody-fields-true--initial"
    finalized_session_id = str(finalized["session"]["session_id"])

    async def add_started_at() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_scope(db, _tenant_scope())
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            meeting.started_at = datetime.now(UTC) - timedelta(days=1)
            await db.commit()

    asyncio.run(add_started_at())
    body = _sync_state(client, "custody-fields-true")

    assert body["upload_session"]["session_id"] is None
    assert body["upload_session"]["status"] is None
    assert body["playback"]["media_revision_id"] == str(revision_id)
    assert body["playback"]["local_media_revision_id"] == local_revision_id
    assert body["finalized_upload"]["session_id"] == finalized_session_id
    assert body["finalized_upload"]["media_revision_id"] == str(revision_id)
    assert body["finalized_upload"]["local_media_revision_id"] == local_revision_id
    assert body["finalized_upload"]["status"] == "finalized"
    assert body["finalized_upload"]["archive_audio"] is True
    assert body["finalized_upload"]["finalized_at"] is not None
    assert body["meeting"]["retention"]["policy_state"] == "active"
    assert body["meeting"]["retention"]["delete_after"] is not None
    assert body["playback"]["object_verified"] is False


def test_sync_state_exposes_archive_false_as_not_playable_proof(client) -> None:
    finalized = create_finalized_meeting(client, "custody-fields-false", archive_audio=False)

    body = _sync_state(client, "custody-fields-false")

    assert body["upload_session"]["session_id"] is None
    assert body["upload_session"]["status"] is None
    assert body["finalized_upload"]["session_id"] == str(finalized["session"]["session_id"])
    assert body["finalized_upload"]["status"] == "finalized"
    assert body["finalized_upload"]["archive_audio"] is False
    assert body["finalized_upload"]["finalized_at"] is not None
    assert body["finalized_upload"]["local_media_revision_id"] == "custody-fields-false--initial"
    assert body["playback"]["state"] == "unavailable"
    assert body["playback"]["can_play"] is False
    assert body["playback"]["object_verified"] is False
    assert body["playback"]["reason_code"] == "audio_not_archived"


def test_sync_state_keeps_active_revision_two_and_finalized_revision_one_separate(
    client,
) -> None:
    local_id = "custody-fields-active-rev2"
    finalized = create_finalized_meeting(client, local_id, archive_audio=True)
    meeting_id = finalized["meeting"]["meeting_id"]
    revision_one_id = str(finalized["meeting"]["media_revision"]["media_revision_id"])
    finalized_session_id = str(finalized["session"]["session_id"])

    revision_two = client.post(
        f"/api/v1/meetings/{meeting_id}/media-revisions/upload-sessions",
        headers=auth_headers(),
        json={
            "local_media_revision_id": f"{local_id}--rev2",
            "duration_seconds": 60,
        },
    )
    assert revision_two.status_code == 202
    active_session = revision_two.json()["upload_session"]

    body = _sync_state(client, local_id)

    assert body["upload_session"]["session_id"] == active_session["session_id"]
    assert body["upload_session"]["status"] == active_session["status"]
    assert "media_revision_id" not in body["upload_session"]
    assert "archive_audio" not in body["upload_session"]
    assert "finalized_at" not in body["upload_session"]
    assert body["finalized_upload"]["session_id"] == finalized_session_id
    assert body["finalized_upload"]["media_revision_id"] == revision_one_id
    assert body["finalized_upload"]["local_media_revision_id"] == f"{local_id}--initial"
    assert body["finalized_upload"]["status"] == "finalized"
    assert body["playback"]["media_revision_id"] == revision_one_id
    assert body["playback"]["local_media_revision_id"] == f"{local_id}--initial"


def test_custody_lookup_is_exact_revision_and_newest_finalized_first(client) -> None:
    finalized = create_finalized_meeting(client, "custody-fields-isolation", archive_audio=True)
    meeting_id = UUID(str(finalized["meeting"]["meeting_id"]))
    revision_one = UUID(str(finalized["meeting"]["media_revision"]["media_revision_id"]))
    revision_two = uuid4()

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_scope(db, _tenant_scope())
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            db.add(
                MediaRevision(
                    id=revision_two,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    local_media_revision_id="custody-fields-isolation--second",
                    revision_number=2,
                    source_kind=MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value,
                    status=MediaRevisionStatus.ACCEPTED.value,
                    duration_seconds=60,
                    immutable=True,
                )
            )
            await db.flush()
            now = datetime.now(UTC)
            db.add_all(
                [
                    UploadSession(
                        id=uuid4(),
                        meeting_id=meeting.id,
                        media_revision_id=revision_one,
                        workspace_id=meeting.workspace_id,
                        device_id=meeting.device_id,
                        created_by_user_id=meeting.created_by_user_id,
                        status=UploadSessionStatus.FINALIZED.value,
                        archive_audio=False,
                        expected_track_roles=[],
                        expected_track_sizes={},
                        max_package_bytes_snapshot=1,
                        max_track_bytes_snapshot=1,
                        expires_at=now + timedelta(days=1),
                        created_at=now + timedelta(seconds=5),
                        finalized_at=now + timedelta(seconds=5),
                    ),
                    UploadSession(
                        id=uuid4(),
                        meeting_id=meeting.id,
                        media_revision_id=revision_two,
                        workspace_id=meeting.workspace_id,
                        device_id=meeting.device_id,
                        created_by_user_id=meeting.created_by_user_id,
                        status=UploadSessionStatus.FINALIZED.value,
                        archive_audio=True,
                        expected_track_roles=[],
                        expected_track_sizes={},
                        max_package_bytes_snapshot=1,
                        max_track_bytes_snapshot=1,
                        expires_at=now + timedelta(days=1),
                        created_at=now,
                        finalized_at=now,
                    ),
                ]
            )
            await db.commit()

            first = await finalized_upload_custody_for_revision(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=revision_one,
            )
            second = await finalized_upload_custody_for_revision(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=revision_two,
            )
            first_archive = await archive_audio_for_revision(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=revision_one,
            )
            second_archive = await archive_audio_for_revision(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=revision_two,
            )
            return first, second, first_archive, second_archive

    first, second, first_archive, second_archive = asyncio.run(exercise())

    assert first is not None
    assert first.media_revision_id == revision_one
    assert first.local_media_revision_id == "custody-fields-isolation--initial"
    assert first.archive_audio is False
    assert first.finalized_at is not None
    assert second is not None
    assert second.media_revision_id == revision_two
    assert second.local_media_revision_id == "custody-fields-isolation--second"
    assert second.archive_audio is True
    assert first_archive is False
    assert second_archive is True
