import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import ProcessingWorkflow


def test_processing_pickup_starts_workflow_and_reuses_duplicate(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "pickup-start")
    meeting_id = finalized["meeting"]["meeting_id"]
    media_revision_id = finalized["meeting"]["media_revision"]["media_revision_id"]

    first = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting_id},
    )
    assert first.status_code == 202
    assert first.json()["started_count"] == 1
    assert first.json()["reused_count"] == 0

    second = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting_id},
    )
    assert second.status_code == 202
    assert second.json()["started_count"] == 0
    assert second.json()["reused_count"] == 1

    async def workflow_count() -> tuple[int, str]:
        async with client.app_state["sessionmaker"]() as db:
            rows = (await db.scalars(select(ProcessingWorkflow))).all()
            return len(rows), rows[0].workflow_id

    count, workflow_id = asyncio.run(workflow_count())
    assert count == 1
    assert workflow_id == f"processing/{media_revision_id}"


def test_processing_pickup_without_temporal_blocks_safely(client) -> None:
    finalized = create_finalized_meeting(client, "pickup-no-temporal")
    meeting_id = finalized["meeting"]["meeting_id"]
    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting_id},
    )
    assert response.status_code == 202
    assert response.json()["blocked_count"] == 1

    async def reason_code() -> str | None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == UUID(meeting_id))
            )
            assert workflow is not None
            return workflow.last_reason_code

    assert asyncio.run(reason_code()) == "blocked_temporal_unavailable"
