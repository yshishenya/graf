from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from twobrain_rec_server.db.models import (
    IngestAuditEvent,
    MediaRevision,
    MeetingDeletionArtifactState,
)
from twobrain_rec_server.domain.statuses import MediaRevisionStatus

BOUNDED_COPY = "Delete this meeting everywhere GRAF controls."


def _create_meeting(client, local_recording_id: str) -> dict:
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "local_media_revision_id": f"{local_recording_id}--initial",
            "duration_seconds": 60,
        },
    )
    assert response.status_code == 200
    return response.json()


def _create_upload_session(client, meeting_id: str) -> dict:
    response = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        headers=auth_headers(),
        json={"expected_tracks": ["manifest", "microphone", "system"]},
    )
    assert response.status_code == 200
    return response.json()


def test_aborted_upload_marks_media_revision_blocked_and_audit_links_revision(client) -> None:
    meeting = _create_meeting(client, "lifecycle-abort-revision-001")
    session = _create_upload_session(client, meeting["meeting_id"])
    media_revision_id = UUID(meeting["media_revision"]["media_revision_id"])

    response = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/abort",
        headers=auth_headers(),
        json={"reason": "user_cancelled"},
    )

    async def load_rows() -> tuple[str | None, UUID | None]:
        async with client.app_state["sessionmaker"]() as db:
            revision_status = await db.scalar(
                select(MediaRevision.status).where(MediaRevision.id == media_revision_id)
            )
            audit_revision_id = await db.scalar(
                select(IngestAuditEvent.media_revision_id).where(
                    IngestAuditEvent.upload_session_id == UUID(session["session_id"]),
                    IngestAuditEvent.event_type == "aborted",
                )
            )
            return revision_status, audit_revision_id

    revision_status, audit_revision_id = asyncio.run(load_rows())

    assert response.status_code == 200
    assert response.json()["media_revision_id"] == str(media_revision_id)
    assert revision_status == MediaRevisionStatus.BLOCKED.value
    assert audit_revision_id == media_revision_id


def test_deletion_report_accounts_for_media_revision_lifecycle_artifact(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )

    async def load_artifact_classes() -> dict[str, dict]:
        async with client.app_state["sessionmaker"]() as db:
            rows = (
                await db.scalars(
                    select(MeetingDeletionArtifactState).where(
                        MeetingDeletionArtifactState.meeting_id == seeds.ready_id
                    )
                )
            ).all()
            return {row.artifact_class: row.metadata_json for row in rows}

    artifact_classes = asyncio.run(load_artifact_classes())

    assert response.status_code == 202
    assert "media_revision" in artifact_classes
    assert artifact_classes["media_revision"]["artifact_class"] == "media_revision"
