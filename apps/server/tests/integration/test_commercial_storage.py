"""Assigned capacity is serialized with playback admission and publication."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text

from tests.fixtures.processing import apply_job_worker_scope
from tests.integration.test_playback_normalization_finalize import _accept_first_party_recording
from tests.integration.test_playback_normalization_workflow import FakeNormalizationPipeline
from twobrain_rec_server.billing.admin_grants import create_adjustment
from twobrain_rec_server.db.models import Meeting, PlaybackNormalizationJob, Workspace
from twobrain_rec_server.normalization import service


@pytest.mark.parametrize("stage", ["admission", "publication"])
def test_storage_admission_and_publication_lock_rights_before_meeting(client, tmp_path, monkeypatch, stage):
    meeting, finalized = _accept_first_party_recording(client,
        local_recording_id=f"synthetic-capacity-{stage}", include_playback=True)
    assert finalized["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    reached, proceed = asyncio.Event(), asyncio.Event()
    calls = 0
    original = service._lock_playback_storage_scope
    async def boundary(db, workspace_id):
        nonlocal calls
        calls += 1
        if calls == (1 if stage == "admission" else 2):
            reached.set()
            await proceed.wait()
        await original(db, workspace_id)
    monkeypatch.setattr(service, "_lock_playback_storage_scope", boundary)

    async def race():
        async with client.app_state["sessionmaker"]() as reader:
            job = await reader.scalar(select(PlaybackNormalizationJob).where(PlaybackNormalizationJob.meeting_id == meeting_id))
            assert job is not None
            workspace_id, job_id = job.workspace_id, job.id
        async def normalize():
            async with client.app_state["sessionmaker"]() as db:
                job = await db.get(PlaybackNormalizationJob, job_id)
                await apply_job_worker_scope(db, job)
                return await service.run_normalization_job(db=db, storage=client.app_state["storage"],
                    job_id=job_id, work_directory=tmp_path, pipeline=FakeNormalizationPipeline("copy"))
        task = asyncio.create_task(normalize())
        try:
            await asyncio.wait_for(reached.wait(), timeout=5)
            async with client.app_state["sessionmaker"]() as writer:
                await writer.execute(text("set local lock_timeout='1s'"))
                await writer.scalar(select(Workspace.id).where(Workspace.id == workspace_id).with_for_update())
                proceed.set()
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(asyncio.shield(task), timeout=0.15)
                assert await writer.scalar(select(Meeting.id).where(Meeting.id == meeting_id).with_for_update()) == meeting_id
                assert await writer.scalar(select(PlaybackNormalizationJob.id).where(PlaybackNormalizationJob.id == job_id).with_for_update()) == job_id
                now = datetime.now(UTC)
                await create_adjustment(writer, workspace_id=workspace_id, kind="exact_limit",
                    feature_key="storage_bytes", value=1, unit="bytes", starts_at=now-timedelta(seconds=1),
                    ends_at=now+timedelta(days=1), source_kind="migration", source_ref=f"synthetic:{uuid4()}",
                    reason="Synthetic concurrent capacity reduction")
                await writer.commit()
            if stage == "admission":
                with pytest.raises(service.NormalizationExecutionFailure) as failure:
                    await asyncio.wait_for(task, timeout=5)
                assert failure.value.reason_code.value == "storage_capacity_exceeded"
            else:
                # Already admitted bytes remain reserved after a limit reduction.
                assert (await asyncio.wait_for(task, timeout=5)).canonical_track_artifact_id is not None
        finally:
            proceed.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    asyncio.run(race())
