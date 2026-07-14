from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import PlaybackNormalizationJob


class CommitObservingTemporalClient(FakeTemporalClient):
    def __init__(self, sessionmaker) -> None:
        super().__init__()
        self.sessionmaker = sessionmaker
        self.job_was_committed_before_start = False

    async def start_workflow(
        self, workflow, payload, *, id: str, task_queue: str, **options: object
    ):
        if id.startswith("playback-normalization/"):
            async with self.sessionmaker() as db:
                job = await db.get(PlaybackNormalizationJob, UUID(payload["job_id"]))
                self.job_was_committed_before_start = job is not None and job.state == "queued"
        return await super().start_workflow(
            workflow,
            payload,
            id=id,
            task_queue=task_queue,
            **options,
        )


class PlaybackFailingTemporalClient(FakeTemporalClient):
    async def start_workflow(
        self, workflow, payload, *, id: str, task_queue: str, **options: object
    ):
        if id.startswith("playback-normalization/"):
            raise RuntimeError("simulated playback Temporal outage")
        return await super().start_workflow(
            workflow,
            payload,
            id=id,
            task_queue=task_queue,
            **options,
        )


def test_finalize_commits_durable_job_before_normalization_dispatch(client) -> None:
    temporal = CommitObservingTemporalClient(client.app_state["sessionmaker"])
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.settings.processing_enabled = False
    client.app.state.temporal_client = temporal

    finalized = create_finalized_meeting(client, "normalization-post-commit-dispatch")
    revision_id = finalized["meeting"]["media_revision"]["media_revision_id"]
    workflow_id = f"playback-normalization/{revision_id}/v1"

    assert temporal.job_was_committed_before_start is True
    assert workflow_id in temporal.starts
    assert all(not started_id.startswith("processing/") for started_id in temporal.starts)


def test_playback_dispatch_failure_preserves_source_and_does_not_block_processing(client) -> None:
    temporal = PlaybackFailingTemporalClient()
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.settings.processing_enabled = True
    client.app.state.temporal_client = temporal

    finalized = create_finalized_meeting(client, "normalization-dispatch-independent")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    revision_id = finalized["meeting"]["media_revision"]["media_revision_id"]

    assert f"processing/{revision_id}" in temporal.starts

    async def load_job() -> PlaybackNormalizationJob | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )

    job = asyncio.run(load_job())
    assert job is not None
    assert job.state == "queued"
    assert job.workflow_run_id is None


def test_staged_rollout_gate_persists_job_without_starting_temporal_workflow(client) -> None:
    temporal = FakeTemporalClient()
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.settings.playback_normalization_automatic_dispatch_enabled = False
    client.app.state.settings.processing_enabled = False
    client.app.state.temporal_client = temporal

    finalized = create_finalized_meeting(client, "normalization-staged-dispatch-gate")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])

    async def load_job() -> PlaybackNormalizationJob | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )

    job = asyncio.run(load_job())
    assert job is not None
    assert job.state == "queued"
    assert all(
        not workflow_id.startswith("playback-normalization/") for workflow_id in temporal.starts
    )
