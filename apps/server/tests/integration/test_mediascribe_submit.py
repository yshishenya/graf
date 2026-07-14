import asyncio
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import MediaRevision, TrackArtifact
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing import submit as submit_module
from twobrain_rec_server.processing.reasons import (
    BLOCKED_AUDIO_TOO_LARGE,
    BLOCKED_MISSING_ARTIFACTS,
    PROCESSING_TEMP_STORAGE_UNAVAILABLE,
)
from twobrain_rec_server.processing.submit import submit_to_mediascribe


class StagingOnlyStorage:
    def __init__(self, delegate: object) -> None:
        self.delegate = delegate

    def get_bytes(self, _object_key: str) -> bytes:
        raise AssertionError("processing submit must not load full audio objects into memory")

    async def get_bytes_async(self, _object_key: str) -> bytes:
        raise AssertionError("processing submit must not load full audio objects into memory")

    def download_to_path(
        self,
        object_key: str,
        destination_path: str | Path,
        *,
        chunk_size: int,
    ) -> int:
        return self.delegate.download_to_path(
            object_key,
            destination_path,
            chunk_size=chunk_size,
        )

    async def download_to_path_async(
        self,
        object_key: str,
        destination_path: str | Path,
        *,
        chunk_size: int,
    ) -> int:
        return await self.delegate.download_to_path_async(
            object_key,
            destination_path,
            chunk_size=chunk_size,
        )


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

        def download_to_path(
            self,
            _object_key: str,
            _destination_path: str | Path,
            *,
            chunk_size: int,
        ) -> int:
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


def test_submit_sync_storage_staging_runs_off_event_loop(client, monkeypatch) -> None:
    finalized = create_finalized_meeting(client, "mediascribe-sync-storage-thread")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_sync_storage")
    original_sha256_file = submit_module._sha256_file

    def loop_checking_sha256_file(path: Path) -> str:
        with pytest.raises(RuntimeError):
            asyncio.get_running_loop()
        return original_sha256_file(path)

    monkeypatch.setattr(submit_module, "_sha256_file", loop_checking_sha256_file)

    class LoopCheckingStorage:
        def __init__(self, delegate: object) -> None:
            self.delegate = delegate

        def get_bytes(self, _object_key: str) -> bytes:
            raise AssertionError("processing submit must not load full audio objects into memory")

        def download_to_path(
            self,
            object_key: str,
            destination_path: str | Path,
            *,
            chunk_size: int,
        ) -> int:
            with pytest.raises(RuntimeError):
                asyncio.get_running_loop()
            return self.delegate.download_to_path(
                object_key,
                destination_path,
                chunk_size=chunk_size,
            )

    async def submit_with_sync_storage() -> tuple[bool, int]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            result = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=LoopCheckingStorage(client.app_state["storage"]),
                mediascribe_client=fake_client,
                workflow=workflow,
            )
            return result.submitted, len(fake_client.submissions)

    submitted, submission_count = asyncio.run(submit_with_sync_storage())

    assert submitted is True
    assert submission_count == 1


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


def test_submit_single_track_media_upload_persists_source_and_reuses_existing_job(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    upload = client.post(
        "/api/v1/media-uploads",
        headers={
            "X-Organization-Id": str(UUID("10000000-0000-0000-0000-000000000001")),
            "X-Workspace-Id": str(UUID("20000000-0000-0000-0000-000000000001")),
            "X-User-Id": str(UUID("30000000-0000-0000-0000-000000000001")),
            "X-Device-Id": str(UUID("40000000-0000-0000-0000-000000000001")),
        },
        data={"duration_seconds": "60", "local_recording_id": "manual-mediascribe-submit"},
        files={"file": ("meeting.wav", b"manual-media-audio", "audio/wav")},
    )
    assert upload.status_code == 202
    finalized = upload.json()
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_single_submit")

    async def submit_twice() -> tuple[str, int, str | None, bool, str, bool, bool]:
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
            return (
                first.job.request_mode,
                len(fake_client.submissions),
                str(fake_client.submissions[0]["media_content_type"]),
                second.submitted,
                first.job.external_job_id,
                first.job.source_track_artifact_id is not None,
                first.job.mic_track_artifact_id is None and first.job.incoming_track_artifact_id is None,
            )

    (
        request_mode,
        submission_count,
        media_content_type,
        second_submitted,
        external_job_id,
        has_source,
        no_pair,
    ) = asyncio.run(submit_twice())
    assert request_mode == "single_track"
    assert submission_count == 1
    assert media_content_type == "audio/wav"
    assert second_submitted is False
    assert external_job_id == "job_single_submit"
    assert has_source is True
    assert no_pair is True
    assert fake_client.submissions[0]["request_mode"] == "single_track"


def test_processing_source_requires_accepted_revision_and_matching_authoritative_digests(
    client,
) -> None:
    finalized = create_finalized_meeting(client, "mediascribe-accepted-custody")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])

    async def exercise_boundary():
        async with client.app_state["sessionmaker"]() as db:
            accepted = await store.load_processing_source(
                db,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            revision = await db.get(MediaRevision, media_revision_id)
            assert revision is not None
            revision.status = "pending_upload"
            await db.commit()
            pending = await store.load_processing_source(
                db,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            revision.status = "accepted"
            microphone = await db.scalar(
                select(TrackArtifact).where(
                    TrackArtifact.media_revision_id == media_revision_id,
                    TrackArtifact.track_role == "microphone",
                )
            )
            assert microphone is not None
            microphone.sha256 = "f" * 64
            await db.commit()
            mismatched = await store.load_processing_source(
                db,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            return accepted, pending, mismatched

    accepted, pending, mismatched = asyncio.run(exercise_boundary())
    assert accepted is not None
    assert accepted.request_mode == "dual_track"
    assert pending is None
    assert mismatched is None


def test_first_party_mediascribe_ignores_competing_media_and_playback_derivatives(
    client,
) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "mediascribe-source-role-boundary")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_role_boundary")
    rogue_media = b"rogue-parallel-media-source"
    playback_derivative = b"derived-playback-output"

    async def seed_and_submit():
        async with client.app_state["sessionmaker"]() as db:
            for role, body in (
                ("media", rogue_media),
                ("playback", playback_derivative),
            ):
                artifact_id = uuid4()
                object_key = f"tests/accepted-boundary/{artifact_id}"
                client.app_state["storage"].put_bytes(object_key, body)
                db.add(
                    TrackArtifact(
                        id=artifact_id,
                        meeting_id=meeting_id,
                        media_revision_id=media_revision_id,
                        workspace_id=workspace_id,
                        track_role=role,
                        codec="audio/wav" if role == "media" else "m4a-aac-lc",
                        sample_rate_hz=48_000,
                        channel_count=1,
                        duration_seconds=60,
                        byte_length=len(body),
                        sha256=sha256(body).hexdigest(),
                        storage_object_key=object_key,
                        status="stored",
                    )
                )
            await db.commit()
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            submitted = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=StagingOnlyStorage(client.app_state["storage"]),
                mediascribe_client=fake_client,
                workflow=workflow,
            )
            return submitted

    submitted = asyncio.run(seed_and_submit())
    expected_by_role = {track["track_role"]: track for track in finalized["tracks"]}
    assert submitted.job.request_mode == "dual_track"
    assert submitted.job.source_track_artifact_id is None
    assert submitted.job.mic_track_artifact_id is not None
    assert submitted.job.incoming_track_artifact_id is not None
    assert len(fake_client.submissions) == 1
    assert fake_client.submissions[0]["mic_sha256"] == expected_by_role["microphone"]["sha256"]
    assert (
        fake_client.submissions[0]["incoming_sha256"]
        == expected_by_role["system"]["sha256"]
    )


def test_mediascribe_staging_rejects_same_size_source_object_digest_mismatch(client) -> None:
    finalized = create_finalized_meeting(client, "mediascribe-object-digest-boundary")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_must_not_submit")

    async def corrupt_and_submit():
        async with client.app_state["sessionmaker"]() as db:
            microphone = await db.scalar(
                select(TrackArtifact).where(
                    TrackArtifact.media_revision_id == media_revision_id,
                    TrackArtifact.track_role == "microphone",
                )
            )
            assert microphone is not None
            client.app_state["storage"].put_bytes(
                microphone.storage_object_key,
                b"x" * microphone.byte_length,
            )
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            with pytest.raises(RuntimeError, match=BLOCKED_MISSING_ARTIFACTS):
                await submit_to_mediascribe(
                    db=db,
                    settings=client.app.state.settings,
                    storage=StagingOnlyStorage(client.app_state["storage"]),
                    mediascribe_client=fake_client,
                    workflow=workflow,
                )
            return workflow.status, workflow.last_reason_code

    status, reason_code = asyncio.run(corrupt_and_submit())
    assert status == ProcessingStatus.BLOCKED.value
    assert reason_code == BLOCKED_MISSING_ARTIFACTS
    assert fake_client.submissions == []
