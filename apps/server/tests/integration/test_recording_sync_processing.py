from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import ProcessingWorkflow


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
