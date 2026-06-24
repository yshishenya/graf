import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting, enable_processing_autostart
from twobrain_rec_server.db.models import ProcessingAuditEvent, ProcessingWorkflow


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


def test_processing_pickup_reuses_workflow_started_by_finalize_autostart(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    enable_processing_autostart(client, client.app.state.temporal_client)
    finalized = create_finalized_meeting(client, "pickup-after-finalize-autostart")
    meeting_id = finalized["meeting"]["meeting_id"]

    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting_id},
    )

    assert response.status_code == 202
    assert response.json()["started_count"] == 0
    assert response.json()["reused_count"] == 1

    async def reuse_audit_metadata() -> dict[str, object]:
        async with client.app_state["sessionmaker"]() as db:
            event = await db.scalar(
                select(ProcessingAuditEvent)
                .where(
                    ProcessingAuditEvent.meeting_id == UUID(meeting_id),
                    ProcessingAuditEvent.event_type == "workflow_duplicate_reused",
                )
                .order_by(ProcessingAuditEvent.created_at.desc())
            )
            assert event is not None
            return event.metadata_json

    metadata = asyncio.run(reuse_audit_metadata())
    assert set(metadata) <= {"workflow_id", "reason_code"}
    assert metadata["reason_code"] == "duplicate_workflow_reused"
    serialized = str(metadata).lower()
    assert all(token not in serialized for token in {"transcript", "audio_download_url", "api_key", "signed_url"})
