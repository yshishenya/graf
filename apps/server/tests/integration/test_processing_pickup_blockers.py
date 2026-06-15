import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import Meeting, ProcessingWorkflow, TrackArtifact


def test_processing_pickup_blocks_invalid_meeting_states(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "pickup-draft-blocked", "duration_seconds": 60},
    ).json()
    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting["meeting_id"]},
    )
    assert response.status_code == 202
    assert response.json()["blocked_count"] == 1

    async def reason_code() -> str | None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == UUID(meeting["meeting_id"]))
            )
            assert workflow is not None
            persisted_meeting = await db.get(Meeting, UUID(meeting["meeting_id"]))
            assert persisted_meeting.status == "draft"
            return workflow.last_reason_code

    assert asyncio.run(reason_code()) == "blocked_invalid_meeting_state"


def test_processing_pickup_blocks_missing_dual_track_artifacts(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "pickup-missing-artifact")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])

    async def delete_system_artifact() -> None:
        async with client.app_state["sessionmaker"]() as db:
            system = await db.scalar(
                select(TrackArtifact).where(
                    TrackArtifact.meeting_id == meeting_id,
                    TrackArtifact.track_role == "system",
                )
            )
            await db.delete(system)
            await db.commit()

    asyncio.run(delete_system_artifact())
    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": str(meeting_id)},
    )
    assert response.status_code == 202
    assert response.json()["blocked_count"] == 1

    async def reason_code() -> str | None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id))
            assert workflow is not None
            return workflow.last_reason_code

    assert asyncio.run(reason_code()) == "blocked_missing_artifacts"
