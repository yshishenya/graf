import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting, enable_processing_autostart
from twobrain_rec_server.db.models import Meeting, ProcessingWorkflow, TemporaryUploadObject


def test_finalize_starts_processing_when_enabled(client) -> None:
    temporal = enable_processing_autostart(client, FakeTemporalClient())

    finalized = create_finalized_meeting(client, "finalize-autostart")
    body = finalized["finalize"]
    meeting = body["meeting"]
    media_revision_id = meeting["media_revision"]["media_revision_id"]

    assert body["workflow_started"] is True
    assert body["mediascribe_job_created"] is False
    assert meeting["status"] == "ingested_pending_processing"
    assert meeting["processing_status"] == "workflow_started"
    assert f"processing/{media_revision_id}" in temporal.starts

    status = client.get(f"/api/v1/meetings/{meeting['meeting_id']}/processing", headers=auth_headers())
    assert status.status_code == 200
    assert status.json()["state"] == "workflow_started"
    assert status.json()["workflow_id"] == f"processing/{media_revision_id}"


def test_finalize_persists_no_archive_choice_through_processing_pickup(client) -> None:
    temporal = enable_processing_autostart(client, FakeTemporalClient())

    finalized = create_finalized_meeting(client, "finalize-no-archive", archive_audio=False)
    body = finalized["finalize"]
    meeting = body["meeting"]
    meeting_id = UUID(meeting["meeting_id"])

    assert body["upload_session"]["archive_audio"] is False
    assert body["workflow_started"] is True
    workflow_id = f"processing/{meeting['media_revision']['media_revision_id']}"
    assert temporal.starts[workflow_id]["payload"]["archive_audio"] == "false"

    async def persisted() -> tuple[bool, str, int]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id))
            objects = (
                await db.scalars(
                    select(TemporaryUploadObject).where(TemporaryUploadObject.upload_session_id == UUID(body["upload_session"]["session_id"]))
                )
            ).all()
            assert workflow is not None
            return workflow.archive_audio, workflow.transient_state, len(objects)

    archive_audio, transient_state, object_count = asyncio.run(persisted())
    assert archive_audio is False
    assert transient_state == "processing"
    assert object_count >= 2

    status = client.get(f"/api/v1/meetings/{meeting['meeting_id']}/processing", headers=auth_headers())
    assert status.status_code == 200
    payload = status.json()
    assert payload["archive_audio"] is False
    assert payload["transient_state"] == "processing"


def test_finalize_dependency_unavailable_keeps_upload_success_and_blocks_processing(client) -> None:
    enable_processing_autostart(client)

    finalized = create_finalized_meeting(client, "finalize-no-temporal")
    body = finalized["finalize"]
    meeting = body["meeting"]

    assert body["workflow_started"] is False
    assert body["mediascribe_job_created"] is False
    assert meeting["status"] == "ingested_pending_processing"
    assert meeting["processing_status"] == "blocked"

    status = client.get(f"/api/v1/meetings/{meeting['meeting_id']}/processing", headers=auth_headers())
    assert status.status_code == 200
    payload = status.json()
    assert payload["state"] == "blocked"
    assert payload["reason_code"] == "blocked_temporal_unavailable"
    assert payload["content_available"] is False

    sync = client.get(
        "/api/v1/desktop/recordings/finalize-no-temporal/sync-state",
        headers=auth_headers(),
        params={"local_media_revision_id": "finalize-no-temporal--initial"},
    )
    assert sync.status_code == 200
    sync_payload = sync.json()
    assert sync_payload["meeting"]["status"] == "ingested_pending_processing"
    assert sync_payload["review"]["available"] is True
    assert sync_payload["review"]["status"] == "blocked"
    assert sync_payload["review"]["transcript_available"] is False
    assert sync_payload["review"]["diarization_available"] is False
    assert sync_payload["review"]["content_available"] is False
    assert sync_payload["review"]["web_url"] == f"/meetings/{meeting['meeting_id']}"
    assert sync_payload["review"]["desktop_url"] == f"/desktop/meetings/{meeting['meeting_id']}"
    assert sync_payload["processing"]["reason_code"] == "blocked_temporal_unavailable"
    assert sync_payload["conflict"]["state"] == "processing_blocked"

    async def persisted_status() -> tuple[str, str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting_row = await db.get(Meeting, UUID(meeting["meeting_id"]))
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == UUID(meeting["meeting_id"]))
            )
            assert meeting_row is not None
            assert workflow is not None
            return meeting_row.status, workflow.status

    assert asyncio.run(persisted_status()) == ("ingested_pending_processing", "blocked")
