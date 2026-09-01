import asyncio

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from twobrain_rec_server.api.schemas import DesktopSyncConflict
from twobrain_rec_server.db.models import (
    MediaScribeJob,
    Meeting,
    ProcessingResult,
    ProcessingWorkflow,
)
from twobrain_rec_server.domain.statuses import (
    MediaScribeJobStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
    SummaryStatus,
)
from twobrain_rec_server.ingest.desktop_sync import _review_available


def test_desktop_review_url_preserves_initial_recovery_and_hides_canceled() -> None:
    assert all(
        _review_available(DesktopSyncConflict(), status)
        for status in ProcessingStatus
        if status != ProcessingStatus.CANCELED
    )
    assert not _review_available(DesktopSyncConflict(), ProcessingStatus.CANCELED)


def test_desktop_sync_keeps_complete_review_during_active_replacement(client) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id

    async def seed_partial_replacement() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            previous = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
            )
            previous_result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and previous is not None and previous_result is not None
            previous.attempt_ordinal = 1
            replacement = ProcessingWorkflow(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=previous_result.media_revision_id,
                workflow_id=f"processing/{previous_result.media_revision_id}/2",
                status=ProcessingStatus.POLLING.value,
                attempt_ordinal=2,
            )
            db.add(replacement)
            await db.flush()
            replacement_job = MediaScribeJob(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=previous_result.media_revision_id,
                processing_workflow_id=replacement.id,
                external_job_id="fixture-desktop-replacement-job",
                status=MediaScribeJobStatus.TRANSCRIBING.value,
            )
            db.add(replacement_job)
            await db.flush()
            db.add(
                ProcessingResult(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    media_revision_id=previous_result.media_revision_id,
                    mediascribe_job_id=replacement_job.id,
                    processing_workflow_id=replacement.id,
                    result_version=1,
                    status=ProcessingResultStatus.IMPORTED.value,
                    transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
                    diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
                    summary_status=SummaryStatus.NOT_REQUESTED.value,
                    segment_count=1,
                    diarization_segment_count=0,
                )
            )
            meeting.processing_status = ProcessingStatus.POLLING.value
            await db.commit()

    asyncio.run(seed_partial_replacement())

    response = client.get(
        "/api/v1/desktop/recordings/cabinet-ready/sync-state",
        headers=auth_headers(),
        params={"local_media_revision_id": "cabinet-ready--initial"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["processing"]["status"] == ProcessingStatus.POLLING.value
    assert payload["processing"]["workflow_id"].endswith("/2")
    assert payload["review"]["available"] is True
    assert payload["review"]["status"] == "processing"
    assert payload["review"]["transcript_available"] is True
    assert payload["review"]["diarization_available"] is True
    assert payload["review"]["content_available"] is True
    assert payload["review"]["web_url"] == f"/meetings/{meeting_id}"
    assert payload["review"]["desktop_url"] == f"/desktop/meetings/{meeting_id}"
    assert payload["custody"]["review_available"] is True
