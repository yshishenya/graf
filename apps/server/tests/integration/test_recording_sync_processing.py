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
from twobrain_rec_server.ingest.desktop_sync import _custody_read_model


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
