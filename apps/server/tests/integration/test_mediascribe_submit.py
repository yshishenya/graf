import asyncio
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting, create_finalized_mixed_recording
from twobrain_rec_server.billing.storage import project_active_playback_storage
from twobrain_rec_server.cabinet.access import AccessDecision
from twobrain_rec_server.cabinet.egress import review_playback_state, stored_audio_artifacts
from twobrain_rec_server.db.models import (
    MediaRevision,
    MediaScribeJob,
    Meeting,
    PlaybackNormalizationJob,
    ProcessingWorkflow,
    TrackArtifact,
)
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus, ProcessingStatus
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.mediascribe.client import MediaScribeClientError
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing import submit as submit_module
from twobrain_rec_server.processing.reasons import (
    BLOCKED_AUDIO_TOO_LARGE,
    BLOCKED_MISSING_ARTIFACTS,
    PROCESSING_TEMP_STORAGE_UNAVAILABLE,
)
from twobrain_rec_server.processing.store import ProcessingLifecycleBlocked
from twobrain_rec_server.processing.submit import (
    ManualUploadNormalizationPending,
    submit_to_mediascribe,
)


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


def test_submit_accepts_fresh_temporal_attempt_in_starting_state(client) -> None:
    """A newly admitted attempt may submit before the start projection lands."""
    finalized = create_finalized_meeting(client, "mediascribe-submit-starting")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_starting")

    async def submit_from_starting() -> tuple[str, str, str, int]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.STARTING,
            )
            result = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=StagingOnlyStorage(client.app_state["storage"]),
                mediascribe_client=fake_client,
                workflow=workflow,
            )
            persisted_workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.id == workflow.id)
            )
            persisted_job = await db.scalar(
                select(MediaScribeJob).where(MediaScribeJob.processing_workflow_id == workflow.id)
            )
            assert persisted_workflow is not None
            assert persisted_job is not None
            return (
                result.job.external_job_id or "",
                persisted_workflow.status,
                persisted_job.status,
                len(fake_client.submissions),
            )

    assert asyncio.run(submit_from_starting()) == (
        "job_starting",
        ProcessingStatus.SUBMITTED.value,
        MediaScribeJobStatus.UPLOADED.value,
        1,
    )


def test_submission_claim_loss_persists_provider_id_with_blocked_projection(client) -> None:
    finalized = create_finalized_meeting(client, "mediascribe-submit-claim-loss")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def persist_claim_loss() -> tuple[str | None, str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            job = await store.upsert_mediascribe_job(
                db,
                workflow=workflow,
                mic_artifact=await _track_artifact(db, workspace_id, meeting_id, "microphone"),
                incoming_artifact=await _track_artifact(db, workspace_id, meeting_id, "system"),
                request_mode="dual_track",
            )
            job.status = MediaScribeJobStatus.SUBMITTING.value
            job.submission_claim_token = "new-owner"
            await db.commit()
            with pytest.raises(MediaScribeClientError) as error:
                await store.persist_mediascribe_submission(
                    db,
                    job=job,
                    external_job_id="job_claim_lost",
                    status=MediaScribeJobStatus.UPLOADED,
                    submission_claim_token="old-owner",
                )
            persisted = await db.scalar(
                select(MediaScribeJob)
                .where(MediaScribeJob.id == job.id)
                .execution_options(populate_existing=True)
            )
            assert persisted is not None
            return persisted.external_job_id, persisted.status, error.value.reason_code

    assert asyncio.run(persist_claim_loss()) == (
        "job_claim_lost",
        MediaScribeJobStatus.BLOCKED.value,
        "blocked_mediascribe_submission_outcome_unknown",
    )


def test_submit_does_not_reuse_external_job_from_parallel_workflow_lineage(client) -> None:
    """A provider job is reusable only inside its exact processing workflow."""
    finalized = create_finalized_meeting(client, "mediascribe-submit-lineage-boundary")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job-target-lineage")

    async def submit_with_parallel_job() -> tuple[str | None, UUID, UUID, int]:
        async with client.app_state["sessionmaker"]() as db:
            target = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/target/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            revision = await db.get(MediaRevision, media_revision_id)
            microphone = await db.scalar(
                select(TrackArtifact).where(
                    TrackArtifact.media_revision_id == media_revision_id,
                    TrackArtifact.track_role == "microphone",
                )
            )
            incoming = await db.scalar(
                select(TrackArtifact).where(
                    TrackArtifact.media_revision_id == media_revision_id,
                    TrackArtifact.track_role == "system",
                )
            )
            assert revision is not None and microphone is not None and incoming is not None
            source_fingerprint = source_fingerprint_for_revision(revision)
            parallel = ProcessingWorkflow(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/parallel/{media_revision_id}",
                source_fingerprint=source_fingerprint,
                status=ProcessingStatus.PROCESSED.value,
                attempt_ordinal=0,
                attempt_count=1,
            )
            db.add(parallel)
            await db.flush()
            db.add(
                MediaScribeJob(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    processing_workflow_id=parallel.id,
                    idempotency_key=f"mediascribe:{parallel.id}:{source_fingerprint}",
                    source_fingerprint=source_fingerprint,
                    external_job_id="job-parallel-lineage",
                    status=MediaScribeJobStatus.READY.value,
                    request_mode="dual_track",
                    mic_track_artifact_id=microphone.id,
                    incoming_track_artifact_id=incoming.id,
                )
            )
            await db.commit()
            submitted = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=StagingOnlyStorage(client.app_state["storage"]),
                mediascribe_client=fake_client,
                workflow=target,
            )
            return (
                submitted.job.external_job_id,
                submitted.job.processing_workflow_id,
                target.id,
                len(fake_client.submissions),
            )

    external_job_id, processing_workflow_id, target_workflow_id, submission_count = asyncio.run(
        submit_with_parallel_job()
    )
    assert external_job_id == "job-target-lineage"
    assert processing_workflow_id == target_workflow_id
    assert submission_count == 1


async def _track_artifact(db, workspace_id: UUID, meeting_id: UUID, track_role: str) -> TrackArtifact:
    artifact = await db.scalar(
        select(TrackArtifact).where(
            TrackArtifact.workspace_id == workspace_id,
            TrackArtifact.meeting_id == meeting_id,
            TrackArtifact.track_role == track_role,
        )
    )
    assert artifact is not None
    return artifact


def test_submit_retains_external_job_id_when_final_fence_loses_race(client, monkeypatch) -> None:
    finalized = create_finalized_meeting(client, "mediascribe-submit-fence-race")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_fence_race")
    original_fence = submit_module._ensure_processing_fence
    fence_calls = 0

    async def fail_after_provider_submit(db, workflow, **kwargs):
        nonlocal fence_calls
        fence_calls += 1
        if fence_calls == 3:
            raise ProcessingLifecycleBlocked("meeting_deleting")
        return await original_fence(db, workflow, **kwargs)

    monkeypatch.setattr(submit_module, "_ensure_processing_fence", fail_after_provider_submit)

    async def submit_once() -> tuple[str | None, str, str | None, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            with pytest.raises(ProcessingLifecycleBlocked, match="meeting_deleting"):
                await submit_to_mediascribe(
                    db=db,
                    settings=client.app.state.settings,
                    storage=StagingOnlyStorage(client.app_state["storage"]),
                    mediascribe_client=fake_client,
                    workflow=workflow,
                )
            job = await store.get_mediascribe_job(
                db,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            assert job is not None
            return job.external_job_id, job.status, job.last_error_code, job.last_error_message

    external_job_id, status, error_code, error_message = asyncio.run(submit_once())

    assert fence_calls == 3
    assert len(fake_client.submissions) == 1
    assert external_job_id == "job_fence_race"
    assert status == "blocked"
    assert error_code == "blocked_mediascribe_submission_outcome_unknown"
    assert error_message == "meeting_deleting"


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


@pytest.mark.parametrize("archive_audio", [True, False])
def test_submit_single_track_media_upload_persists_source_and_reuses_existing_job(
    client,
    archive_audio: bool,
) -> None:
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.settings.playback_normalization_automatic_dispatch_enabled = True
    client.app.state.settings.processing_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    source_body = b"manual-media-audio"
    upload = client.post(
        "/api/v1/media-uploads",
        headers={
            "X-Organization-Id": str(UUID("10000000-0000-0000-0000-000000000001")),
            "X-Workspace-Id": str(UUID("20000000-0000-0000-0000-000000000001")),
            "X-User-Id": str(UUID("30000000-0000-0000-0000-000000000001")),
            "X-Device-Id": str(UUID("40000000-0000-0000-0000-000000000001")),
        },
        data={
            "duration_seconds": "60",
            "local_recording_id": f"manual-mediascribe-submit-{archive_audio}",
            "archive_audio": str(archive_audio).lower(),
        },
        files={"file": ("meeting.wav", source_body, "audio/wav")},
    )
    assert upload.status_code == 202
    finalized = upload.json()
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_single_submit")
    canonical_body = b"canonical-manual-media"

    async def submit_twice() -> tuple[str, int, str | None, bool, str, bool, bool, int, int, bool]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
                archive_audio=archive_audio,
            )
            with pytest.raises(ManualUploadNormalizationPending):
                await submit_to_mediascribe(
                    db=db,
                    settings=client.app.state.settings,
                    storage=StagingOnlyStorage(client.app_state["storage"]),
                    mediascribe_client=fake_client,
                    workflow=workflow,
                )
            assert fake_client.submissions == []

            normalization_job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.media_revision_id == media_revision_id
                )
            )
            assert normalization_job is not None
            canonical_id = uuid4()
            canonical_key = f"tests/canonical/{canonical_id}/meeting-review.m4a"
            client.app_state["storage"].put_bytes(canonical_key, canonical_body)
            canonical = TrackArtifact(
                id=canonical_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                track_role="playback",
                codec="m4a-aac-lc",
                sample_rate_hz=48_000,
                channel_count=1,
                duration_seconds=60,
                byte_length=len(canonical_body),
                sha256=sha256(canonical_body).hexdigest(),
                storage_object_key=canonical_key,
                status="stored",
                normalization_profile_version=normalization_job.profile_version,
                validation_version=normalization_job.validation_version,
                validated_at=datetime.now(UTC),
                derivation_kind="single_source_transcode",
                source_fingerprint_sha256=normalization_job.source_fingerprint_sha256,
            )
            db.add(canonical)
            normalization_job.state = "ready"
            normalization_job.canonical_track_artifact_id = canonical.id
            normalization_job.ready_at = datetime.now(UTC)
            await db.commit()
            projection = await project_active_playback_storage(
                db,
                workspace_id=workflow.workspace_id,
                capacity_bytes=1_000_000,
            )
            visible_audio = await stored_audio_artifacts(
                db,
                workspace_id=workflow.workspace_id,
                meeting_id=meeting_id,
            )
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            playback = await review_playback_state(
                db,
                meeting=meeting,
                access=AccessDecision(
                    state="owner",
                    label="Owner",
                    reason=None,
                    can_view=True,
                    can_share=True,
                    can_manage_team_visibility=True,
                    can_download=True,
                    can_export=True,
                ),
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
                projection.used_bytes,
                len(visible_audio),
                playback.can_play,
            )

    (
        request_mode,
        submission_count,
        media_content_type,
        second_submitted,
        external_job_id,
        has_source,
        no_pair,
        used_bytes,
        visible_audio_count,
        can_play,
    ) = asyncio.run(submit_twice())
    assert request_mode == "single_track"
    assert submission_count == 1
    assert media_content_type == "audio/mp4"
    assert second_submitted is False
    assert external_job_id == "job_single_submit"
    assert has_source is True
    assert no_pair is True
    assert used_bytes == (len(canonical_body) if archive_audio else 0)
    assert visible_audio_count == (1 if archive_audio else 0)
    assert can_play is archive_audio
    assert fake_client.submissions[0] == {
        "request_mode": "single_track",
        "media_size": len(canonical_body),
        "media_sha256": sha256(canonical_body).hexdigest(),
        "media_content_type": "audio/mp4",
        "media_filename": "manual-media.m4a",
        "diarize": True,
        "summarize": False,
        "num_speakers": None,
        "speaker_count_mode": None,
        "idempotency_key": fake_client.submissions[0]["idempotency_key"],
    }


def test_failed_pre_egress_job_conflict_terminalizes_transient_workflow(client) -> None:
    finalized = create_finalized_meeting(
        client,
        "stale-pre-egress-lineage",
        archive_audio=False,
    )
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    fake_client = FakeMediaScribeClient(external_job_id="must_not_submit")

    async def exercise() -> tuple[str, bool, bool, int]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
                archive_audio=False,
            )
            microphone = await db.scalar(
                select(TrackArtifact).where(
                    TrackArtifact.media_revision_id == media_revision_id,
                    TrackArtifact.track_role == "microphone",
                )
            )
            assert microphone is not None
            stale_job = await store.upsert_mediascribe_job(
                db,
                workflow=workflow,
                source_artifact=microphone,
                request_mode="single_track",
            )
            stale_job.status = MediaScribeJobStatus.FAILED.value
            await db.commit()

            with pytest.raises(
                ProcessingLifecycleBlocked,
                match="processing_request_fingerprint_conflict",
            ):
                await submit_to_mediascribe(
                    db=db,
                    settings=client.app.state.settings,
                    storage=StagingOnlyStorage(client.app_state["storage"]),
                    mediascribe_client=fake_client,
                    workflow=workflow,
                )
            await db.refresh(workflow)
            await db.refresh(stale_job)
            return (
                workflow.status,
                workflow.transient_purge_due_at is not None,
                stale_job.source_track_artifact_id == microphone.id,
                len(fake_client.submissions),
            )

    assert asyncio.run(exercise()) == (ProcessingStatus.BLOCKED.value, True, True, 0)


def test_v5_mislabeled_media_is_blocked_before_any_provider_submission(client) -> None:
    finalized = create_finalized_mixed_recording(
        client,
        "mediascribe-v5-invalid-wav",
        media_bytes=b"not-a-wave-container",
    )
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_must_not_submit")

    async def run() -> tuple[str, str | None, int]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            with pytest.raises(RuntimeError) as exc:
                await submit_to_mediascribe(
                    db=db,
                    settings=client.app.state.settings,
                    storage=StagingOnlyStorage(client.app_state["storage"]),
                    mediascribe_client=fake_client,
                    workflow=workflow,
                )
            assert str(exc.value) == BLOCKED_MISSING_ARTIFACTS
            return workflow.status, workflow.last_reason_code, len(fake_client.submissions)

    assert asyncio.run(run()) == ("blocked", BLOCKED_MISSING_ARTIFACTS, 0)


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


def test_reprocess_revision_uses_its_single_media_source_for_submission(client) -> None:
    finalized = create_finalized_mixed_recording(client, "mediascribe-reprocess-source")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_reprocess_source")

    async def submit_reprocess() -> tuple[bool, str, int]:
        async with client.app_state["sessionmaker"]() as db:
            revision = await db.get(MediaRevision, media_revision_id)
            assert revision is not None
            revision.source_kind = "reprocess"
            await db.commit()
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            result = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=StagingOnlyStorage(client.app_state["storage"]),
                mediascribe_client=fake_client,
                workflow=workflow,
            )
            await db.commit()
            return result.submitted, workflow.status, len(fake_client.submissions)

    submitted, status, submission_count = asyncio.run(submit_reprocess())
    assert submitted is True
    assert status == ProcessingStatus.SUBMITTED.value
    assert submission_count == 1


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
