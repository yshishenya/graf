from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import MediaRevision, Meeting, UploadSession
from twobrain_rec_server.domain.statuses import (
    MediaRevisionStatus,
    MeetingStatus,
    UploadSessionStatus,
)


def test_reprocess_upload_creates_revision_scoped_session_and_reuses_idempotency(client) -> None:
    finalized = create_finalized_meeting(client, "revision-reprocess-api")
    meeting_id = finalized["meeting"]["meeting_id"]
    payload = {
        "local_media_revision_id": "revision-reprocess-api--second",
        "source_kind": "reprocess",
        "duration_seconds": 60,
        "expected_tracks": ["manifest", "media"],
        "expected_track_sizes": {"manifest": 2, "media": 4},
    }
    headers = auth_headers() | {"Idempotency-Key": "revision-reprocess-idempotent"}

    first = client.post(
        f"/api/v1/meetings/{meeting_id}/media-revisions/upload-sessions",
        headers=headers,
        json=payload,
    )
    second = client.post(
        f"/api/v1/meetings/{meeting_id}/media-revisions/upload-sessions",
        headers=headers,
        json=payload,
    )

    assert first.status_code == 202
    assert second.status_code == 202
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["media_revision"]["revision_number"] == 2
    assert first_payload["media_revision"]["status"] == "pending_upload"
    assert first_payload["upload_session"]["media_revision_id"] == first_payload["media_revision"]["media_revision_id"]
    assert second_payload["upload_session"]["session_id"] == first_payload["upload_session"]["session_id"]


def test_reprocess_revision_and_session_are_isolated_from_initial_revision(client) -> None:
    finalized = create_finalized_meeting(client, "revision-reprocess-isolation")
    meeting_id = finalized["meeting"]["meeting_id"]
    response = client.post(
        f"/api/v1/meetings/{meeting_id}/media-revisions/upload-sessions",
        headers=auth_headers() | {"Idempotency-Key": "revision-reprocess-isolated"},
        json={
            "local_media_revision_id": "revision-reprocess-isolation--second",
            "source_kind": "reprocess",
            "duration_seconds": 60,
        },
    )
    assert response.status_code == 202
    revision_id = response.json()["media_revision"]["media_revision_id"]
    session_id = response.json()["upload_session"]["session_id"]

    async def inspect() -> tuple[list[MediaRevision], UploadSession | None]:
        async with client.app_state["sessionmaker"]() as db:
            revisions = list(
                await db.scalars(
                    select(MediaRevision)
                    .where(MediaRevision.meeting_id == meeting_id)
                    .order_by(MediaRevision.revision_number)
                )
            )
            session = await db.get(UploadSession, session_id)
            return revisions, session

    revisions, session = asyncio.run(inspect())
    assert [revision.revision_number for revision in revisions] == [1, 2]
    assert revisions[0].id != revisions[1].id
    assert str(revisions[1].id) == revision_id
    assert session is not None and str(session.media_revision_id) == revision_id


def test_reprocess_upload_rejects_second_active_revision_for_same_meeting(client) -> None:
    finalized = create_finalized_meeting(client, "revision-reprocess-overlap")
    meeting_id = finalized["meeting"]["meeting_id"]
    first = client.post(
        f"/api/v1/meetings/{meeting_id}/media-revisions/upload-sessions",
        headers=auth_headers() | {"Idempotency-Key": "revision-reprocess-overlap-first"},
        json={
            "local_media_revision_id": "revision-reprocess-overlap--first",
            "source_kind": "reprocess",
            "duration_seconds": 60,
        },
    )
    second = client.post(
        f"/api/v1/meetings/{meeting_id}/media-revisions/upload-sessions",
        headers=auth_headers() | {"Idempotency-Key": "revision-reprocess-overlap-second"},
        json={
            "local_media_revision_id": "revision-reprocess-overlap--second",
            "source_kind": "reprocess",
            "duration_seconds": 60,
        },
    )
    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["code"] == "active_upload_session_exists"


def test_aborting_reprocess_restores_previous_accepted_revision(client) -> None:
    finalized = create_finalized_meeting(client, "revision-reprocess-abort")
    meeting_id = finalized["meeting"]["meeting_id"]
    previous_revision_id = finalized["meeting"]["media_revision"]["media_revision_id"]
    response = client.post(
        f"/api/v1/meetings/{meeting_id}/media-revisions/upload-sessions",
        headers=auth_headers() | {"Idempotency-Key": "revision-reprocess-abort"},
        json={
            "local_media_revision_id": "revision-reprocess-abort--second",
            "source_kind": "reprocess",
            "duration_seconds": 60,
        },
    )
    assert response.status_code == 202
    session_id = response.json()["upload_session"]["session_id"]
    aborted = client.post(
        f"/api/v1/upload-sessions/{session_id}/abort",
        headers=auth_headers(),
        json={"reason": "user_aborted"},
    )
    assert aborted.status_code == 200

    async def inspect() -> tuple[object, object, object]:
        async with client.app_state["sessionmaker"]() as db:
            return (
                await db.get(Meeting, meeting_id),
                await db.get(UploadSession, session_id),
                await db.get(MediaRevision, previous_revision_id),
            )

    meeting, session, revision = asyncio.run(inspect())
    assert meeting is not None
    assert meeting.status == MeetingStatus.INGESTED_PENDING_PROCESSING.value
    assert session is not None and session.status == UploadSessionStatus.ABORTED.value
    assert revision is not None and revision.status == MediaRevisionStatus.ACCEPTED.value


def test_expiring_reprocess_restores_previous_accepted_revision(client) -> None:
    finalized = create_finalized_meeting(client, "revision-reprocess-expire")
    meeting_id = finalized["meeting"]["meeting_id"]
    previous_revision_id = finalized["meeting"]["media_revision"]["media_revision_id"]
    local_revision_id = "revision-reprocess-expire--second"
    response = client.post(
        f"/api/v1/meetings/{meeting_id}/media-revisions/upload-sessions",
        headers=auth_headers() | {"Idempotency-Key": "revision-reprocess-expire"},
        json={
            "local_media_revision_id": local_revision_id,
            "source_kind": "reprocess",
            "duration_seconds": 60,
        },
    )
    assert response.status_code == 202
    session_id = response.json()["upload_session"]["session_id"]

    async def expire() -> None:
        async with client.app_state["sessionmaker"]() as db:
            session = await db.get(UploadSession, session_id)
            assert session is not None
            session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()

    asyncio.run(expire())
    sync = client.get(
        "/api/v1/desktop/recordings/revision-reprocess-expire/sync-state",
        headers=auth_headers(),
        params={"local_media_revision_id": local_revision_id},
    )
    assert sync.status_code == 200

    async def inspect() -> tuple[object, object, object]:
        async with client.app_state["sessionmaker"]() as db:
            return (
                await db.get(Meeting, meeting_id),
                await db.get(UploadSession, session_id),
                await db.get(MediaRevision, previous_revision_id),
            )

    meeting, session, revision = asyncio.run(inspect())
    assert meeting is not None
    assert meeting.status == MeetingStatus.INGESTED_PENDING_PROCESSING.value
    assert session is not None and session.status == UploadSessionStatus.EXPIRED.value
    assert revision is not None and revision.status == MediaRevisionStatus.ACCEPTED.value


def test_reprocess_upload_enforces_recording_duration_limit(client) -> None:
    finalized = create_finalized_meeting(client, "revision-reprocess-duration-limit")
    meeting_id = finalized["meeting"]["meeting_id"]
    response = client.post(
        f"/api/v1/meetings/{meeting_id}/media-revisions/upload-sessions",
        headers=auth_headers() | {"Idempotency-Key": "revision-reprocess-duration-limit"},
        json={
            "local_media_revision_id": "revision-reprocess-duration-limit--second",
            "source_kind": "reprocess",
            "duration_seconds": 10_000_000,
            "expected_tracks": ["manifest", "media"],
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "recording_duration_exceeded"
