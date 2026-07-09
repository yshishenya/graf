import asyncio
from pathlib import Path
from uuid import UUID

import pytest
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing import submit as submit_module
from twobrain_rec_server.processing.reasons import (
    BLOCKED_AUDIO_TOO_LARGE,
    PROCESSING_TEMP_STORAGE_UNAVAILABLE,
)
from twobrain_rec_server.processing.submit import submit_to_mediascribe

from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting


class StagingOnlyStorage:
    def __init__(self, delegate: object) -> None:
        self.delegate = delegate

    def get_bytes(self, _object_key: str) -> bytes:
        raise AssertionError("processing submit must not load full audio objects into memory")

    async def get_bytes_async(self, _object_key: str) -> bytes:
        raise AssertionError("processing submit must not load full audio objects into memory")

    def download_to_path(self, object_key: str, destination_path: str | Path, *, chunk_size: int) -> int:
        return self.delegate.download_to_path(object_key, destination_path, chunk_size=chunk_size)

    async def download_to_path_async(self, object_key: str, destination_path: str | Path, *, chunk_size: int) -> int:
        return await self.delegate.download_to_path_async(object_key, destination_path, chunk_size=chunk_size)


def test_submit_persists_external_job_id_before_retry_continues(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "mediascribe-submit")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_submit")

    async def submit_twice() -> tuple[str | None, int, bool]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            first = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=StagingOnlyStorage(client.app_state["storage"]),
                mediascribe_client=fake_client,
                workflow=workflow,
            )
            second = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=StagingOnlyStorage(client.app_state["storage"]),
                mediascribe_client=fake_client,
                workflow=workflow,
            )
            return first.job.external_job_id, len(fake_client.submissions), second.submitted

    external_job_id, submission_count, second_submitted = asyncio.run(submit_twice())
    assert external_job_id == "job_submit"
    assert submission_count == 1
    assert second_submitted is False


def test_submit_blocks_large_track_pair_before_loading_audio_bytes(client) -> None:
    finalized = create_finalized_meeting(client, "mediascribe-large-track-pair")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_should_not_submit")
    original_limit = client.app.state.settings.processing_max_submit_audio_bytes
    client.app.state.settings.processing_max_submit_audio_bytes = 1

    class NonReadingStorage:
        def get_bytes(self, _object_key: str) -> bytes:
            raise AssertionError("processing must block before loading audio bytes")

        def download_to_path(self, _object_key: str, _destination_path: str | Path, *, chunk_size: int) -> int:
            raise AssertionError("processing must block before staging audio")

    async def submit_large_pair() -> tuple[str, str | None, int]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            with pytest.raises(RuntimeError, match=BLOCKED_AUDIO_TOO_LARGE):
                await submit_to_mediascribe(
                    db=db,
                    settings=client.app.state.settings,
                    storage=NonReadingStorage(),
                    mediascribe_client=fake_client,
                    workflow=workflow,
                )
            return workflow.status, workflow.last_reason_code, len(fake_client.submissions)

    try:
        status, reason_code, submission_count = asyncio.run(submit_large_pair())
    finally:
        client.app.state.settings.processing_max_submit_audio_bytes = original_limit

    assert status == ProcessingStatus.BLOCKED.value
    assert reason_code == BLOCKED_AUDIO_TOO_LARGE
    assert submission_count == 0


def test_submit_marks_temp_storage_unavailable_retryable_before_staging(client, monkeypatch) -> None:
    finalized = create_finalized_meeting(client, "mediascribe-temp-storage-unavailable")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_should_not_submit")

    class LowDiskUsage:
        free = 0

    monkeypatch.setattr(submit_module.shutil, "disk_usage", lambda _path: LowDiskUsage())

    async def submit_without_temp_capacity() -> tuple[str, str | None, int]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            with pytest.raises(RuntimeError, match=PROCESSING_TEMP_STORAGE_UNAVAILABLE):
                await submit_to_mediascribe(
                    db=db,
                    settings=client.app.state.settings,
                    storage=StagingOnlyStorage(client.app_state["storage"]),
                    mediascribe_client=fake_client,
                    workflow=workflow,
                )
            return workflow.status, workflow.last_reason_code, len(fake_client.submissions)

    status, reason_code, submission_count = asyncio.run(submit_without_temp_capacity())

    assert status == ProcessingStatus.FAILED_RETRYABLE.value
    assert reason_code == PROCESSING_TEMP_STORAGE_UNAVAILABLE
    assert submission_count == 0
