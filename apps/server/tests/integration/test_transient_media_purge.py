from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_minio import FailOnceDeleteStorage
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.artifacts import deterministic_wav_bytes
from tests.fixtures.processing import apply_job_worker_scope
from tests.integration.test_playback_normalization_workflow import (
    FakeManualNormalizationPipeline,
)
from twobrain_rec_server.db.models import (
    MediaRevision,
    MediaScribeJob,
    Meeting,
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    ProcessingResult,
    ProcessingWorkflow,
    PurgeJournal,
    TemporaryUploadObject,
    TrackArtifact,
)
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context,
)
from twobrain_rec_server.deletion.service import (
    MAX_PURGE_JOURNAL_ATTEMPTS,
    reconcile_transient_media_purges,
    retry_orphan_purge_journals,
)
from twobrain_rec_server.normalization.service import (
    NormalizationExecutionDeferred,
    run_normalization_job,
)
from twobrain_rec_server.processing import store


class BlockingVerifiedUploadStorage:
    def __init__(
        self, delegate: object, *, uploaded: asyncio.Event, release: asyncio.Event
    ) -> None:
        self.delegate = delegate
        self.uploaded = uploaded
        self.release = release

    async def upload_verified_path_async(
        self,
        object_key: str,
        source_path: Path,
        *,
        expected_length: int,
        expected_sha256: str,
        max_bytes: int,
    ) -> None:
        assert expected_length <= max_bytes
        with source_path.open("rb") as stream:
            self.delegate.put_stream(object_key, stream, expected_length)
        self.uploaded.set()
        await self.release.wait()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)


def test_transient_delete_failure_stops_after_bounded_attempts(client) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Bounded transient purge",
            "duration_seconds": "60",
            "local_recording_id": "bounded-transient-purge",
            "archive_audio": "false",
        },
        files={"file": ("manual.wav", deterministic_wav_bytes(128), "audio/wav")},
    )
    assert response.status_code == 202
    meeting_id = UUID(response.json()["meeting"]["meeting_id"])
    media_revision_id = UUID(response.json()["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(response.json()["meeting"]["workspace_id"])
    now = datetime.now(UTC)

    async def arrange() -> str:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
            )
            assert workflow is not None
            workflow.status = "failed_terminal"
            workflow.transient_state = "terminal"
            workflow.transient_terminal_at = now - timedelta(minutes=20)
            workflow.transient_purge_due_at = now - timedelta(minutes=5)
            object_keys = set(
                await db.scalars(
                    select(TrackArtifact.storage_object_key).where(
                        TrackArtifact.meeting_id == meeting_id,
                        TrackArtifact.media_revision_id == media_revision_id,
                        TrackArtifact.track_role.in_({"media", "playback"}),
                    )
                )
            )
            object_keys.update(
                await db.scalars(
                    select(TemporaryUploadObject.storage_object_key).where(
                        TemporaryUploadObject.workspace_id == workspace_id,
                        TemporaryUploadObject.media_revision_id == media_revision_id,
                        TemporaryUploadObject.object_role == "transient_source",
                    )
                )
            )
            assert object_keys
            object_key = min(object_keys)
            db.add(
                PurgeJournal(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    artifact_class="transient_audio",
                    object_key=object_key,
                    state="pending",
                    attempt_count=MAX_PURGE_JOURNAL_ATTEMPTS - 1,
                    safe_reason="transient_media_purge",
                )
            )
            await db.commit()
            return object_key

    object_key = asyncio.run(arrange())
    failing_storage = FailOnceDeleteStorage(client.app_state["storage"])
    failing_storage.arm(object_key)

    async def purge(at: datetime) -> int:
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="deletion_purge_reconciliation",
                    actor_id="bounded-transient-purge-test",
                    reason_category="transient_media",
                    feature_area="deletion",
                ),
            )
            return await reconcile_transient_media_purges(
                db,
                storage=failing_storage,
                now=at,
                limit=10,
                object_limit=1,
            )

    assert asyncio.run(purge(now)) == 0

    async def journal_state() -> tuple[str, int, datetime | None]:
        async with client.app_state["sessionmaker"]() as db:
            journal = await db.scalar(
                select(PurgeJournal).where(
                    PurgeJournal.meeting_id == meeting_id,
                    PurgeJournal.object_key == object_key,
                )
            )
            assert journal is not None
            return journal.state, journal.attempt_count, journal.next_retry_at

    assert asyncio.run(journal_state()) == (
        "terminal_unknown",
        MAX_PURGE_JOURNAL_ATTEMPTS,
        None,
    )

    async def operator_retry() -> dict[str, object]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            return await retry_orphan_purge_journals(
                db,
                meeting=meeting,
                storage=failing_storage,
            )

    assert asyncio.run(operator_retry()) == {"reset_count": 1, "converged": False}
    assert asyncio.run(purge(now + timedelta(hours=1))) == 1
    assert not client.app_state["storage"].object_exists(object_key)


def test_no_archive_purge_fences_new_attempt_and_recovers_after_delete_failure(
    client,
    tmp_path: Path,
) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Transient manual upload",
            "duration_seconds": "60",
            "local_recording_id": "transient-manual-upload",
            "archive_audio": "false",
        },
        files={"file": ("manual.wav", deterministic_wav_bytes(256), "audio/wav")},
    )
    assert response.status_code == 202
    payload = response.json()
    meeting_id = UUID(payload["meeting"]["meeting_id"])
    media_revision_id = UUID(payload["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(payload["meeting"]["workspace_id"])
    now = datetime.now(UTC)

    async def prepare() -> tuple[list[str], str, str]:
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            await run_normalization_job(
                db=db,
                storage=client.app_state["storage"],
                job_id=job.id,
                work_directory=tmp_path / "transient-normalization",
                pipeline=FakeManualNormalizationPipeline(),
            )
        async with client.app_state["sessionmaker"]() as db:
            workflows = list(
                await db.scalars(
                    select(ProcessingWorkflow)
                    .where(ProcessingWorkflow.meeting_id == meeting_id)
                    .order_by(ProcessingWorkflow.attempt_ordinal)
                )
            )
            assert len(workflows) == 1
            original = workflows[0]
            original.status = "failed_terminal"
            original.transient_state = "terminal"
            original.transient_terminal_at = now - timedelta(minutes=20)
            original.transient_purge_due_at = now - timedelta(minutes=5)
            second = ProcessingWorkflow(
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workspace_id=workspace_id,
                workflow_id=f"processing/{media_revision_id}/attempt/2",
                archive_audio=False,
                transient_state="processing",
                transient_admitted_at=original.transient_admitted_at,
                transient_hard_deadline=original.transient_hard_deadline,
                source_fingerprint=original.source_fingerprint,
                status="workflow_started",
                attempt_ordinal=2,
            )
            db.add(second)
            await db.commit()
            canonical = await db.scalar(
                select(TrackArtifact).where(
                    TrackArtifact.meeting_id == meeting_id,
                    TrackArtifact.track_role == "playback",
                    TrackArtifact.status == "stored",
                )
            )
            assert canonical is not None
            provider_job = await store.upsert_mediascribe_job(
                db,
                workflow=second,
                source_artifact=canonical,
                request_mode="single_track",
                source_fingerprint=second.source_fingerprint,
                diarize=True,
                summarize=False,
            )
            assert await store.claim_mediascribe_submission(db, job=provider_job) is not None
            artifacts = list(
                await db.scalars(
                    select(TrackArtifact).where(
                        TrackArtifact.meeting_id == meeting_id,
                        TrackArtifact.track_role.in_({"media", "playback"}),
                    )
                )
            )
            attempt = await db.scalar(
                select(PlaybackNormalizationAttempt).where(
                    PlaybackNormalizationAttempt.meeting_id == meeting_id
                )
            )
            assert attempt is not None
            return (
                sorted(
                    {
                        *(artifact.storage_object_key for artifact in artifacts),
                        attempt.storage_object_key,
                    }
                ),
                str(second.id),
                str(provider_job.id),
            )

    object_keys, second_workflow_id, provider_job_id = asyncio.run(prepare())
    assert object_keys
    assert all(client.app_state["storage"].object_exists(key) for key in object_keys)
    playback = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/playback",
        headers=auth_headers(),
    )
    assert playback.status_code == 409
    assert playback.json()["code"] == "playback_unavailable"

    async def purge(storage: object, at: datetime) -> int:
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="deletion_purge_reconciliation",
                    actor_id="transient-purge-test",
                    reason_category="transient_media",
                    feature_area="deletion",
                ),
            )
            return await reconcile_transient_media_purges(
                db,
                storage=storage,
                now=at,
                limit=10,
            )

    assert asyncio.run(purge(client.app_state["storage"], now)) == 0
    assert all(client.app_state["storage"].object_exists(key) for key in object_keys)

    async def make_second_attempt_terminal() -> None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.get(ProcessingWorkflow, UUID(second_workflow_id))
            assert workflow is not None
            workflow.status = "failed_terminal"
            workflow.transient_state = "terminal"
            workflow.transient_terminal_at = now - timedelta(minutes=20)
            workflow.transient_purge_due_at = now - timedelta(minutes=5)
            await db.commit()

    asyncio.run(make_second_attempt_terminal())
    assert asyncio.run(purge(client.app_state["storage"], now)) == 0

    async def expire_provider_claim() -> None:
        async with client.app_state["sessionmaker"]() as db:
            job = await db.get(MediaScribeJob, UUID(provider_job_id))
            assert job is not None
            job.submission_claimed_at = now - timedelta(minutes=3)
            await db.commit()

    asyncio.run(expire_provider_claim())
    failing_storage = FailOnceDeleteStorage(client.app_state["storage"])
    failing_storage.arm(object_keys[0])
    assert asyncio.run(purge(failing_storage, now)) == 0

    async def load_intermediate() -> tuple[list[str], list[str], list[str]]:
        async with client.app_state["sessionmaker"]() as db:
            artifacts = list(
                await db.scalars(
                    select(TrackArtifact).where(
                        TrackArtifact.meeting_id == meeting_id,
                        TrackArtifact.track_role.in_({"media", "playback"}),
                    )
                )
            )
            journals = list(
                await db.scalars(
                    select(PurgeJournal).where(
                        PurgeJournal.meeting_id == meeting_id,
                        PurgeJournal.artifact_class == "transient_audio",
                    )
                )
            )
            jobs = list(
                await db.scalars(
                    select(PlaybackNormalizationJob).where(
                        PlaybackNormalizationJob.meeting_id == meeting_id
                    )
                )
            )
            return (
                [artifact.status for artifact in artifacts],
                [journal.state for journal in journals],
                [job.state for job in jobs],
            )

    artifact_states, journal_states, job_states = asyncio.run(load_intermediate())
    assert set(artifact_states) == {"purge_pending"}
    assert "pending" in journal_states
    assert set(job_states) == {"cancelled"}
    assert client.app_state["storage"].object_exists(object_keys[0])

    assert asyncio.run(purge(failing_storage, now + timedelta(minutes=2))) == 1

    async def load_final() -> tuple[list[str], list[str], list[str], list[str]]:
        async with client.app_state["sessionmaker"]() as db:
            return (
                list(
                    await db.scalars(
                        select(TrackArtifact.status).where(
                            TrackArtifact.meeting_id == meeting_id,
                            TrackArtifact.track_role.in_({"media", "playback"}),
                        )
                    )
                ),
                list(
                    await db.scalars(
                        select(PlaybackNormalizationAttempt.state).where(
                            PlaybackNormalizationAttempt.meeting_id == meeting_id
                        )
                    )
                ),
                list(
                    await db.scalars(
                        select(ProcessingWorkflow.transient_state).where(
                            ProcessingWorkflow.meeting_id == meeting_id
                        )
                    )
                ),
                list(
                    await db.scalars(
                        select(PurgeJournal.state).where(
                            PurgeJournal.meeting_id == meeting_id,
                            PurgeJournal.artifact_class == "transient_audio",
                        )
                    )
                ),
            )

    artifact_states, attempt_states, transient_states, journal_states = asyncio.run(load_final())
    assert set(artifact_states) == {"purged"}
    assert set(attempt_states) == {"purged"}
    assert set(transient_states) == {"purged"}
    assert set(journal_states) == {"purged"}
    assert all(not client.app_state["storage"].object_exists(key) for key in object_keys)


def test_active_attempt_does_not_starve_an_eligible_transient_purge(client) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()

    def upload(local_recording_id: str) -> tuple[UUID, UUID, UUID]:
        response = client.post(
            "/api/v1/media-uploads",
            headers=auth_headers(),
            data={
                "title": local_recording_id,
                "duration_seconds": "60",
                "local_recording_id": local_recording_id,
                "archive_audio": "false",
            },
            files={"file": ("manual.wav", deterministic_wav_bytes(128), "audio/wav")},
        )
        assert response.status_code == 202
        payload = response.json()["meeting"]
        return (
            UUID(payload["workspace_id"]),
            UUID(payload["meeting_id"]),
            UUID(payload["media_revision"]["media_revision_id"]),
        )

    workspace_id, blocked_meeting_id, blocked_revision_id = upload("transient-starvation-blocked")
    _, locked_meeting_id, _locked_revision_id = upload("transient-starvation-locked")
    _, eligible_meeting_id, _eligible_revision_id = upload("transient-starvation-eligible")
    now = datetime.now(UTC)

    async def arrange() -> None:
        async with client.app_state["sessionmaker"]() as db:
            blocked = await db.scalar(
                select(ProcessingWorkflow).where(
                    ProcessingWorkflow.meeting_id == blocked_meeting_id
                )
            )
            eligible = await db.scalar(
                select(ProcessingWorkflow).where(
                    ProcessingWorkflow.meeting_id == eligible_meeting_id
                )
            )
            locked = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == locked_meeting_id)
            )
            assert blocked is not None and locked is not None and eligible is not None
            blocked.status = "failed_terminal"
            blocked.transient_state = "terminal"
            blocked.transient_terminal_at = now - timedelta(minutes=30)
            blocked.transient_purge_due_at = now - timedelta(minutes=10)
            db.add(
                ProcessingWorkflow(
                    meeting_id=blocked_meeting_id,
                    media_revision_id=blocked_revision_id,
                    workspace_id=workspace_id,
                    workflow_id=f"processing/{blocked_revision_id}/attempt/2",
                    archive_audio=False,
                    transient_state="processing",
                    transient_admitted_at=blocked.transient_admitted_at,
                    transient_hard_deadline=blocked.transient_hard_deadline,
                    source_fingerprint=blocked.source_fingerprint,
                    status="workflow_started",
                    attempt_ordinal=2,
                )
            )
            eligible.status = "failed_terminal"
            eligible.transient_state = "terminal"
            eligible.transient_terminal_at = now - timedelta(minutes=20)
            eligible.transient_purge_due_at = now - timedelta(minutes=5)
            locked.status = "failed_terminal"
            locked.transient_state = "terminal"
            locked.transient_terminal_at = now - timedelta(minutes=25)
            locked.transient_purge_due_at = now - timedelta(minutes=8)
            await db.commit()

    asyncio.run(arrange())

    async def purge_one() -> int:
        async with (
            client.app_state["sessionmaker"]() as lock_db,
            client.app_state["sessionmaker"]() as db,
        ):
            await apply_tenant_context(
                lock_db,
                MaintenanceTenantContext(
                    operation_name="deletion_purge_reconciliation",
                    actor_id="transient-lock-test",
                    reason_category="transient_media",
                    feature_area="deletion",
                ),
            )
            assert (
                await lock_db.scalar(
                    select(Meeting).where(Meeting.id == locked_meeting_id).with_for_update()
                )
                is not None
            )
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="deletion_purge_reconciliation",
                    actor_id="transient-starvation-test",
                    reason_category="transient_media",
                    feature_area="deletion",
                ),
            )
            return await reconcile_transient_media_purges(
                db,
                storage=client.app_state["storage"],
                now=now,
                limit=1,
            )

    assert asyncio.run(purge_one()) == 1

    async def states() -> tuple[set[str], set[str], set[str]]:
        async with client.app_state["sessionmaker"]() as db:
            return (
                set(
                    await db.scalars(
                        select(ProcessingWorkflow.transient_state).where(
                            ProcessingWorkflow.meeting_id == blocked_meeting_id
                        )
                    )
                ),
                set(
                    await db.scalars(
                        select(ProcessingWorkflow.transient_state).where(
                            ProcessingWorkflow.meeting_id == locked_meeting_id
                        )
                    )
                ),
                set(
                    await db.scalars(
                        select(ProcessingWorkflow.transient_state).where(
                            ProcessingWorkflow.meeting_id == eligible_meeting_id
                        )
                    )
                ),
            )

    blocked_states, locked_states, eligible_states = asyncio.run(states())
    assert blocked_states == {"terminal", "processing"}
    assert locked_states == {"terminal"}
    assert eligible_states == {"purged"}


def test_transient_purge_bounds_storage_operations_per_cycle(client) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Transient purge budget",
            "duration_seconds": "60",
            "local_recording_id": "transient-purge-budget",
            "archive_audio": "false",
        },
        files={"file": ("manual.wav", deterministic_wav_bytes(256), "audio/wav")},
    )
    assert response.status_code == 202
    payload = response.json()["meeting"]
    meeting_id = UUID(payload["meeting_id"])
    media_revision_id = UUID(payload["media_revision"]["media_revision_id"])
    workspace_id = UUID(payload["workspace_id"])
    now = datetime.now(UTC)
    extra_object_key = f"transient-budget/{media_revision_id}/extra.m4a"
    extra_bytes = b"bounded purge object"
    client.app_state["storage"].put_stream(
        extra_object_key,
        BytesIO(extra_bytes),
        len(extra_bytes),
    )

    async def arrange() -> set[str]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
            )
            source = await db.scalar(
                select(TrackArtifact).where(
                    TrackArtifact.meeting_id == meeting_id,
                    TrackArtifact.track_role == "media",
                )
            )
            assert workflow is not None and source is not None
            source_object_key = source.storage_object_key
            temporary_object_keys = set(
                await db.scalars(
                    select(TemporaryUploadObject.storage_object_key).where(
                        TemporaryUploadObject.media_revision_id == media_revision_id,
                        TemporaryUploadObject.object_role == "transient_source",
                    )
                )
            )
            workflow.status = "failed_terminal"
            workflow.transient_state = "terminal"
            workflow.transient_terminal_at = now - timedelta(minutes=10)
            workflow.transient_purge_due_at = now - timedelta(minutes=1)
            db.add(
                TrackArtifact(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    track_role="playback",
                    codec="aac",
                    sample_rate_hz=48_000,
                    channel_count=1,
                    duration_seconds=60,
                    byte_length=len(extra_bytes),
                    sha256="a" * 64,
                    storage_object_key=extra_object_key,
                    status="candidate",
                )
            )
            await db.commit()
            return {source_object_key, extra_object_key, *temporary_object_keys}

    object_keys = asyncio.run(arrange())
    assert len(object_keys) >= 2

    async def purge_once() -> int:
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="deletion_purge_reconciliation",
                    actor_id="transient-budget-test",
                    reason_category="transient_media",
                    feature_area="deletion",
                ),
            )
            return await reconcile_transient_media_purges(
                db,
                storage=client.app_state["storage"],
                now=now,
                limit=10,
                object_limit=1,
            )

    assert asyncio.run(purge_once()) == 0

    async def journal_states() -> list[str]:
        async with client.app_state["sessionmaker"]() as db:
            return list(
                await db.scalars(
                    select(PurgeJournal.state).where(
                        PurgeJournal.meeting_id == meeting_id,
                        PurgeJournal.artifact_class == "transient_audio",
                    )
                )
            )

    states = asyncio.run(journal_states())
    assert states.count("purged") == 1
    assert states.count("pending") == len(object_keys) - 1
    assert (
        sum(client.app_state["storage"].object_exists(key) for key in object_keys)
        == len(object_keys) - 1
    )
    results = [asyncio.run(purge_once()) for _ in range(len(object_keys) - 1)]
    assert results[-1] == 1
    assert all(result == 0 for result in results[:-1])
    assert all(not client.app_state["storage"].object_exists(key) for key in object_keys)


def test_hard_deadline_does_not_wait_for_inflight_upload_and_purges_after_settlement(
    client,
    tmp_path: Path,
) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Transient upload race",
            "duration_seconds": "60",
            "local_recording_id": "transient-upload-race",
            "archive_audio": "false",
        },
        files={"file": ("manual.wav", deterministic_wav_bytes(256), "audio/wav")},
    )
    assert response.status_code == 202
    meeting_id = UUID(response.json()["meeting"]["meeting_id"])
    now = datetime.now(UTC)

    async def scenario() -> None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
            )
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert workflow is not None and job is not None
            workflow.transient_hard_deadline = now - timedelta(seconds=1)
            await db.commit()
            job_id = job.id

        uploaded = asyncio.Event()
        release = asyncio.Event()
        storage = BlockingVerifiedUploadStorage(
            client.app_state["storage"],
            uploaded=uploaded,
            release=release,
        )

        async def normalize() -> None:
            async with client.app_state["sessionmaker"]() as db:
                job = await db.get(PlaybackNormalizationJob, job_id)
                assert job is not None
                await apply_job_worker_scope(db, job)
                await run_normalization_job(
                    db=db,
                    storage=storage,
                    job_id=job.id,
                    work_directory=tmp_path / "transient-upload-race",
                    pipeline=FakeManualNormalizationPipeline(),
                )

        task = asyncio.create_task(normalize())
        await asyncio.wait_for(uploaded.wait(), timeout=5)

        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="deletion_purge_reconciliation",
                    actor_id="transient-race-test",
                    reason_category="transient_media",
                    feature_area="deletion",
                ),
            )
            assert (
                await reconcile_transient_media_purges(
                    db,
                    storage=storage,
                    now=now,
                    limit=10,
                )
                == 0
            )

        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
            )
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            attempt = await db.scalar(
                select(PlaybackNormalizationAttempt).where(
                    PlaybackNormalizationAttempt.meeting_id == meeting_id
                )
            )
            assert workflow is not None and job is not None and attempt is not None
            assert workflow.status == "canceled"
            assert workflow.transient_state == "purge_due"
            assert job.state == "cancelled"
            assert attempt.state == "cleanup_pending"

        release.set()
        with pytest.raises(NormalizationExecutionDeferred):
            await task

        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="deletion_purge_reconciliation",
                    actor_id="transient-race-test",
                    reason_category="transient_media",
                    feature_area="deletion",
                ),
            )
            assert (
                await reconcile_transient_media_purges(
                    db,
                    storage=storage,
                    now=now,
                    limit=10,
                )
                == 1
            )
            assert (
                await reconcile_transient_media_purges(
                    db,
                    storage=storage,
                    now=now,
                    limit=10,
                )
                == 0
            )

        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
            )
            assert workflow is not None
            assert workflow.status == "canceled"
            assert workflow.transient_state == "purged"
            object_keys = list(
                await db.scalars(
                    select(PurgeJournal.object_key).where(
                        PurgeJournal.meeting_id == meeting_id,
                        PurgeJournal.artifact_class == "transient_audio",
                    )
                )
            )
        assert object_keys
        assert all(not client.app_state["storage"].object_exists(key) for key in object_keys)

    asyncio.run(scenario())
    status = client.get(
        f"/api/v1/meetings/{meeting_id}/processing",
        headers=auth_headers(),
    )
    assert status.status_code == 200
    assert status.json()["manual_action"] == "upload_another"


def test_transient_purge_keeps_local_attempt_tombstone_until_late_put_arrives(client) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Transient late PUT",
            "duration_seconds": "60",
            "local_recording_id": "transient-late-put",
            "archive_audio": "false",
        },
        files={"file": ("manual.wav", deterministic_wav_bytes(256), "audio/wav")},
    )
    assert response.status_code == 202
    meeting_id = UUID(response.json()["meeting"]["meeting_id"])
    now = datetime.now(UTC)

    async def arrange() -> tuple[UUID, str]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
            )
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert workflow is not None and job is not None
            workflow.status = "failed_terminal"
            workflow.retry_class = "terminal"
            workflow.transient_state = "terminal"
            workflow.transient_terminal_at = now - timedelta(minutes=10)
            workflow.transient_purge_due_at = now - timedelta(minutes=1)
            job.state = "running"
            job.attempt_count = 1
            job.cycle_attempt_count = 1
            attempt = PlaybackNormalizationAttempt(
                workspace_id=job.workspace_id,
                meeting_id=job.meeting_id,
                media_revision_id=job.media_revision_id,
                job_id=job.id,
                attempt_number=1,
                cycle_number=1,
                state="local_preparing",
                storage_object_key=f"transient/{job.id}/late-put.m4a",
                derivation_kind="single_source_transcode",
                selected_stream_index=None,
                source_stream_count=0,
                source_audio_stream_count=0,
            )
            db.add(attempt)
            await db.commit()
            return attempt.id, attempt.storage_object_key

    attempt_id, object_key = asyncio.run(arrange())

    async def purge(at: datetime) -> int:
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="deletion_purge_reconciliation",
                    actor_id="transient-late-put-test",
                    reason_category="transient_media",
                    feature_area="deletion",
                ),
            )
            return await reconcile_transient_media_purges(
                db,
                storage=client.app_state["storage"],
                now=at,
                limit=10,
            )

    assert asyncio.run(purge(now)) == 0
    client.app_state["storage"].put_stream(
        object_key,
        BytesIO(b"late canonical bytes"),
        len(b"late canonical bytes"),
    )
    assert asyncio.run(purge(now + timedelta(minutes=2))) == 1

    async def load_attempt() -> PlaybackNormalizationAttempt:
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(PlaybackNormalizationAttempt, attempt_id)
            assert attempt is not None
            return attempt

    attempt = asyncio.run(load_attempt())
    assert attempt.state == "purged"
    assert attempt.cleaned_at is not None
    assert not client.app_state["storage"].object_exists(object_key)


def test_successful_no_archive_result_stays_processed_after_audio_purge(
    client,
    tmp_path: Path,
) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Successful transient upload",
            "duration_seconds": "60",
            "local_recording_id": "successful-transient-upload",
            "archive_audio": "false",
        },
        files={"file": ("manual.wav", deterministic_wav_bytes(256), "audio/wav")},
    )
    assert response.status_code == 202
    payload = response.json()["meeting"]
    meeting_id = UUID(payload["meeting_id"])
    media_revision_id = UUID(payload["media_revision"]["media_revision_id"])
    workspace_id = UUID(payload["workspace_id"])
    now = datetime.now(UTC)

    async def prepare_and_purge() -> int:
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            await run_normalization_job(
                db=db,
                storage=client.app_state["storage"],
                job_id=job.id,
                work_directory=tmp_path / "successful-transient-upload",
                pipeline=FakeManualNormalizationPipeline(),
            )
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
            )
            assert workflow is not None
            workflow.status = "processed"
            workflow.transient_state = "terminal"
            workflow.transient_terminal_at = now - timedelta(minutes=20)
            workflow.transient_purge_due_at = now - timedelta(minutes=5)
            meeting = await store.load_meeting_for_workspace(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
            )
            assert meeting is not None
            meeting.processing_status = "processed"
            provider_job = MediaScribeJob(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                processing_workflow_id=workflow.id,
                external_job_id="job_successful_transient_upload",
                status="ready",
            )
            db.add(provider_job)
            await db.flush()
            db.add(
                ProcessingResult(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    processing_workflow_id=workflow.id,
                    mediascribe_job_id=provider_job.id,
                    result_version=1,
                    status="imported",
                    transcript_status="available",
                    diarization_status="available",
                    summary_status="not_requested",
                    segment_count=1,
                    diarization_segment_count=1,
                )
            )
            previous_revision = MediaRevision(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                local_media_revision_id="successful-transient-upload-previous",
                revision_number=2,
                source_kind="manual_upload",
                status="finalized",
                duration_seconds=60,
            )
            db.add(previous_revision)
            await db.flush()
            db.add(
                PurgeJournal(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=previous_revision.id,
                    artifact_class="transient_audio",
                    object_key="transient/previous-revision/terminal.m4a",
                    state="terminal_unknown",
                    attempt_count=MAX_PURGE_JOURNAL_ATTEMPTS,
                )
            )
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="deletion_purge_reconciliation",
                    actor_id="transient-success-test",
                    reason_category="transient_media",
                    feature_area="deletion",
                ),
            )
            return await reconcile_transient_media_purges(
                db,
                storage=client.app_state["storage"],
                now=now,
                limit=10,
            )

    assert asyncio.run(prepare_and_purge()) == 1
    status = client.get(
        f"/api/v1/meetings/{meeting_id}/processing",
        headers=auth_headers(),
    )
    assert status.status_code == 200
    projection = status.json()
    assert projection["state"] == "processed"
    assert projection["retry_class"] == "none"
    assert projection["manual_action"] == "none"
    assert projection["transcript_available"] is True

    async def retained_manifest_and_purged_audio() -> tuple[str, list[tuple[str, str]]]:
        async with client.app_state["sessionmaker"]() as db:
            artifacts = list(
                await db.scalars(
                    select(TrackArtifact)
                    .where(TrackArtifact.meeting_id == meeting_id)
                    .order_by(TrackArtifact.track_role)
                )
            )
            manifest = next(row for row in artifacts if row.track_role == "manifest")
            return manifest.storage_object_key, [
                (row.track_role, row.status)
                for row in artifacts
                if row.track_role in {"media", "playback"}
            ]

    manifest_key, audio_states = asyncio.run(retained_manifest_and_purged_audio())
    assert client.app_state["storage"].object_exists(manifest_key)
    assert all(state == "purged" for _role, state in audio_states)
