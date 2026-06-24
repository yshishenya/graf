import asyncio
from time import perf_counter
from uuid import UUID

from sqlalchemy import func, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting, enable_processing_autostart
from twobrain_rec_server.db.models import MediaScribeJob, ProcessingResult, ProcessingWorkflow
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus, ProcessingStatus
from twobrain_rec_server.mediascribe.schemas import MediaScribeResult
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.submit import (
    poll_and_import_mediascribe_result,
    submit_to_mediascribe,
)


def test_one_hour_synthetic_recording_orchestration_stays_under_budget(client) -> None:
    temporal = enable_processing_autostart(client, FakeTemporalClient())
    finalized = create_finalized_meeting(client, "one-hour-orchestration-benchmark", duration_seconds=3600)
    meeting = finalized["finalize"]["meeting"]
    meeting_id = UUID(meeting["meeting_id"])
    workspace_id = UUID(meeting["workspace_id"])
    media_revision_id = UUID(meeting["media_revision"]["media_revision_id"])
    workflow_id = f"processing/{media_revision_id}"

    finalize_to_visible_seconds = 0.0
    orchestration_before_submit_seconds = 0.0
    orchestration_after_ready_seconds = 0.0

    visible_started = perf_counter()
    status = client.get(f"/api/v1/meetings/{meeting['meeting_id']}/processing", headers=auth_headers())
    finalize_to_visible_seconds = perf_counter() - visible_started

    assert status.status_code == 200
    assert status.json()["state"] == "workflow_started"
    assert workflow_id in temporal.starts

    fake_mediascribe = FakeMediaScribeClient(
        external_job_id="job_one_hour_synthetic",
        status_sequence=[MediaScribeJobStatus.READY],
        result=MediaScribeResult(external_job_id="job_one_hour_synthetic"),
    )

    async def run_processing() -> dict[str, object]:
        nonlocal orchestration_before_submit_seconds, orchestration_after_ready_seconds
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.get_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            assert workflow is not None
            assert workflow.status == ProcessingStatus.WORKFLOW_STARTED.value

            before_submit_started = perf_counter()
            submitted = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=client.app_state["storage"],
                mediascribe_client=fake_mediascribe,
                workflow=workflow,
            )
            orchestration_before_submit_seconds = perf_counter() - before_submit_started

            after_ready_started = perf_counter()
            imported = await poll_and_import_mediascribe_result(
                db=db,
                workflow=workflow,
                job=submitted.job,
                mediascribe_client=fake_mediascribe,
            )
            orchestration_after_ready_seconds = perf_counter() - after_ready_started

            workflow_count = await db.scalar(
                select(func.count()).select_from(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
            )
            job_count = await db.scalar(
                select(func.count()).select_from(MediaScribeJob).where(MediaScribeJob.meeting_id == meeting_id)
            )
            result_count = await db.scalar(
                select(func.count()).select_from(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            return {
                "imported": imported.imported,
                "workflow_count": workflow_count,
                "job_count": job_count,
                "result_count": result_count,
            }

    benchmark = asyncio.run(run_processing())
    total_product_owned_seconds = orchestration_before_submit_seconds + orchestration_after_ready_seconds

    assert benchmark == {"imported": True, "workflow_count": 1, "job_count": 1, "result_count": 1}
    assert finalize_to_visible_seconds < 60
    assert total_product_owned_seconds < 180
    assert fake_mediascribe.submissions == [
        {
            "mic_size": 16,
            "incoming_size": 24,
            "mic_sha256": finalized["tracks"][1]["sha256"],
            "incoming_sha256": finalized["tracks"][2]["sha256"],
            "diarize": True,
            "summarize": False,
        }
    ]
