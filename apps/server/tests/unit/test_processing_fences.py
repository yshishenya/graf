from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from sqlalchemy import select

from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import (
    MediaRevision,
    MediaScribeJob,
    ProcessingResult,
    ProcessingWorkflow,
)
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing.fences import (
    is_legacy_lineage,
    legacy_source_fingerprint,
)
from twobrain_rec_server.processing.store import reconcile_legacy_processing_lineage


def test_legacy_lineage_marker_is_explicit_and_revision_scoped() -> None:
    lineage_id = uuid4()
    marker = legacy_source_fingerprint(lineage_id)
    assert marker == f"legacy:{lineage_id}"
    assert is_legacy_lineage(media_revision_id=None, source_fingerprint=marker)
    assert not is_legacy_lineage(media_revision_id=uuid4(), source_fingerprint=marker)
    assert not is_legacy_lineage(media_revision_id=None, source_fingerprint="meeting:legacy")


def test_legacy_reconcile_relinks_only_requested_workspace_rows(client) -> None:
    first = create_finalized_meeting(client, "legacy-reconcile-one")
    second = create_finalized_meeting(client, "legacy-reconcile-two")
    first_meeting_id = UUID(first["meeting"]["meeting_id"])
    second_meeting_id = UUID(second["meeting"]["meeting_id"])
    workspace_id = UUID(first["meeting"]["workspace_id"])

    async def run() -> tuple[
        dict[str, int], UUID | None, UUID | None, UUID | None, UUID | None, str | None
    ]:
        async with client.app_state["sessionmaker"]() as db:
            first_workflow = ProcessingWorkflow(
                workspace_id=workspace_id,
                meeting_id=first_meeting_id,
                workflow_id=f"legacy/{uuid4()}",
                status=ProcessingStatus.FAILED_RETRYABLE.value,
                attempt_count=1,
            )
            second_workflow = ProcessingWorkflow(
                workspace_id=workspace_id,
                meeting_id=second_meeting_id,
                workflow_id=f"legacy/{uuid4()}",
                status=ProcessingStatus.FAILED_RETRYABLE.value,
                attempt_count=1,
            )
            db.add_all([first_workflow, second_workflow])
            await db.flush()
            job = MediaScribeJob(
                workspace_id=workspace_id,
                meeting_id=first_meeting_id,
                processing_workflow_id=first_workflow.id,
                idempotency_key=f"legacy-job:{first_workflow.id}",
                status="not_submitted",
                request_mode="dual_track",
            )
            db.add(job)
            await db.flush()
            result = ProcessingResult(
                workspace_id=workspace_id,
                meeting_id=first_meeting_id,
                mediascribe_job_id=job.id,
                status="imported",
                source_result_hash="legacy-result-hash",
            )
            db.add(result)
            second_revision = await db.scalar(
                select(MediaRevision).where(MediaRevision.meeting_id == second_meeting_id)
            )
            assert second_revision is not None
            second_revision.immutable = False
            await db.commit()

            report = await reconcile_legacy_processing_lineage(db, workspace_id=workspace_id)
            refreshed_first = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.id == first_workflow.id)
            )
            refreshed_second = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.id == second_workflow.id)
            )
            refreshed_job = await db.scalar(
                select(MediaScribeJob).where(MediaScribeJob.id == job.id)
            )
            refreshed_result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.id == result.id)
            )
            assert refreshed_first is not None
            assert refreshed_second is not None
            assert refreshed_job is not None
            assert refreshed_result is not None
            return (
                report,
                refreshed_first.media_revision_id,
                refreshed_job.media_revision_id,
                refreshed_result.media_revision_id,
                refreshed_result.processing_workflow_id,
                refreshed_second.source_fingerprint,
            )

    (
        report,
        first_revision_id,
        job_revision_id,
        result_revision_id,
        result_workflow_id,
        second_marker,
    ) = asyncio.run(run())
    assert report["relinked"] == 1
    assert report["unresolved"] == 1
    assert first_revision_id is not None
    assert job_revision_id == first_revision_id
    assert result_revision_id == first_revision_id
    assert result_workflow_id is not None
    assert second_marker is not None and second_marker.startswith("legacy:")
