from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.api.schemas import DesktopSyncConflict
from twobrain_rec_server.db.models import ProcessingWorkflow
from twobrain_rec_server.domain.statuses import (
    CustodyProcessingState,
    CustodyState,
    CustodyUploadState,
    MeetingStatus,
    ProcessingStatus,
    SyncConflictState,
    UploadSessionStatus,
)
from twobrain_rec_server.ingest.desktop_sync import _custody_read_model, _processing_status


def test_desktop_sync_fails_closed_for_unknown_processing_status() -> None:
    assert _processing_status("unknown-persisted-status") == ProcessingStatus.BLOCKED


def test_processing_pickup_keys_workflow_by_media_revision(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "processing-media-revision-042")
    meeting = finalized["meeting"]
    meeting_id = UUID(meeting["meeting_id"])
    media_revision_id = UUID(meeting["media_revision"]["media_revision_id"])

    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": str(meeting_id)},
    )

    assert response.status_code == 202
    assert response.json()["started_count"] == 1

    async def load_workflow() -> ProcessingWorkflow:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id))
            assert workflow is not None
            return workflow

    workflow = asyncio.run(load_workflow())
    assert workflow.media_revision_id == media_revision_id
    assert workflow.workflow_id == f"processing/{media_revision_id}"
    assert client.app.state.temporal_client.starts[workflow.workflow_id]["payload"]["media_revision_id"] == str(media_revision_id)


def test_notification_context_is_scoped_and_does_not_need_calendar(client) -> None:
    response = client.get("/api/v1/desktop/notification-context", headers=auth_headers())
    assert response.headers["Cache-Control"] == "no-store"
    assert response.status_code == 200
    assert set(response.json()) == {"user_id", "workspace_id", "recording_deletion_protocol_version"}
    assert response.json()["recording_deletion_protocol_version"] == 1
    assert client.get("/api/v1/desktop/notification-context").status_code in {401, 403}


def test_unavailable_deletion_target_has_no_receipt_and_next_target_can_be_deleted(client) -> None:
    from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY

    missing_id = str(uuid4())
    confirmation = {"confirmation_boundary": BOUNDED_DELETE_COPY}
    missing = client.post(
        f"/api/v1/cabinet/meetings/{missing_id}/deletion-requests",
        headers=auth_headers(), json=confirmation,
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "meeting_not_found"
    lookup = client.post(
        "/api/v1/desktop/recordings/lifecycle", headers=auth_headers(),
        json={"meeting_ids": [missing_id]},
    )
    assert lookup.status_code == 200
    assert lookup.json()[0]["state"] == "unavailable"
    assert lookup.json()[0]["receipt"] is None
    created = client.post("/api/v1/meetings", headers=auth_headers(), json={
        "local_recording_id": str(uuid4()), "duration_seconds": 10,
    })
    assert created.status_code == 200
    meeting_id = created.json()["meeting_id"]
    accepted = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(), json=confirmation,
    )
    assert accepted.status_code == 202
    assert accepted.json()["receipt_type"] == "meeting_deletion"
    assert accepted.json()["meeting_id"] == meeting_id


def test_processing_failure_keeps_upload_finalized_in_custody_read_model() -> None:
    meeting = type(
        "Meeting",
        (),
        {
            "id": uuid4(),
            "status": MeetingStatus.INGESTED_PENDING_PROCESSING,
            "created_at": None,
            "updated_at": None,
        },
    )()
    session = type("Session", (), {"status": UploadSessionStatus.FINALIZED})()
    custody = _custody_read_model(
        meeting=meeting,
        session=session,
        accepted_bytes_by_track={"microphone": 120, "system": 160},
        processing_status=ProcessingStatus.FAILED_TERMINAL,
        conflict=DesktopSyncConflict(
            state=SyncConflictState.PROCESSING_FAILED,
            reason="processing_failed",
            next_action="contact_operator",
        ),
        review_available=False,
        review_desktop_url=None,
    )

    assert custody.state == CustodyState.PROCESSING
    assert custody.upload_state == CustodyUploadState.FINALIZED
    assert custody.processing_state == CustodyProcessingState.FAILED_TERMINAL
    assert custody.safe_incident_available is True
    assert custody.incident is not None
    assert custody.incident.lifecycle_state == CustodyState.PROCESSING


def test_server_deletion_keeps_upload_and_deletion_truth_separate() -> None:
    meeting = type(
        "Meeting",
        (),
        {
            "id": uuid4(),
            "status": MeetingStatus.INGESTED_PENDING_PROCESSING,
            "created_at": None,
            "updated_at": None,
        },
    )()
    custody = _custody_read_model(
        meeting=meeting,
        session=None,
        accepted_bytes_by_track={},
        processing_status=ProcessingStatus.PENDING_PROCESSING,
        conflict=DesktopSyncConflict(
            state=SyncConflictState.SERVER_MEETING_DELETED,
            reason="server_meeting_deleted",
            next_action="stop_upload",
        ),
        review_available=False,
        review_desktop_url=None,
    )

    assert custody.state == CustodyState.RETAINED_AWAITING_CONDITION
    assert custody.upload_state == CustodyUploadState.FINALIZED
    assert custody.processing_state == CustodyProcessingState.PENDING_PROCESSING
    assert custody.safe_incident_available is True
