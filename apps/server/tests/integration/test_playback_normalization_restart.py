from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from tests.fakes.fake_minio import FailOnceDeleteStorage
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import apply_job_worker_scope
from tests.integration.test_playback_normalization_finalize import (
    _accept_first_party_recording,
)
from tests.integration.test_playback_normalization_workflow import (
    FakeNormalizationPipeline,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import (
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    StorageReservation,
    TrackArtifact,
)
from twobrain_rec_server.normalization import pickup as pickup_module
from twobrain_rec_server.normalization import service as normalization_service
from twobrain_rec_server.normalization.pickup import reconcile_normalization_jobs
from twobrain_rec_server.normalization.service import (
    FFmpegNormalizationPipeline,
    NormalizationExecutionDeferred,
    NormalizationExecutionFailure,
    _prepare_attempt,
    _reserve_playback_storage,
    cleanup_normalization_attempt,
    cleanup_unpublished_normalization_attempts,
    publish_uploaded_attempt,
    record_normalization_failure,
    recover_expired_normalization_job,
    run_normalization_job,
)
from twobrain_rec_server.normalization.statuses import NormalizationReason
from twobrain_rec_server.normalization.worker import renew_normalization_activity_lease


class BlockingNormalizationPipeline(FakeNormalizationPipeline):
    def __init__(self, started: asyncio.Event, release: asyncio.Event) -> None:
        super().__init__("copy")
        self.started = started
        self.release = release

    async def derive_candidate(self, source_path: Path, output_path: Path):
        self.started.set()
        await self.release.wait()
        return await super().derive_candidate(source_path, output_path)


def test_duplicate_loser_cleanup_retries_while_winner_remains_ready(
    client,
    tmp_path: Path,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-duplicate-cleanup-retry",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    flaky_storage = FailOnceDeleteStorage(client.app_state["storage"])

    async def publish_loser_then_reconcile():
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
                work_directory=tmp_path,
                pipeline=FakeNormalizationPipeline("copy"),
            )
            job = await db.get(PlaybackNormalizationJob, job.id)
            assert job is not None and job.state == "ready"
            loser_body = b"validated-duplicate-loser"
            loser_key = f"tests/normalization/{job.id}/duplicate-loser.m4a"
            loser = PlaybackNormalizationAttempt(
                workspace_id=job.workspace_id,
                meeting_id=job.meeting_id,
                media_revision_id=job.media_revision_id,
                job_id=job.id,
                attempt_number=job.attempt_count + 1,
                cycle_number=job.retry_cycle_count + 1,
                state="uploaded",
                storage_object_key=loser_key,
                derivation_kind="uploaded_candidate",
                selected_stream_index=0,
                source_stream_count=1,
                source_audio_stream_count=1,
                source_duration_ms=60_000,
                output_duration_ms=60_000,
                output_byte_length=len(loser_body),
                output_sha256=sha256(loser_body).hexdigest(),
                output_audio_bit_rate=64_000,
                output_sample_rate_hz=48_000,
                output_channel_count=1,
                moov_before_mdat=True,
                fragmented=False,
                full_decode_passed=True,
                uploaded_at=datetime.now(UTC),
            )
            db.add(loser)
            await db.commit()
            flaky_storage.put_bytes(loser_key, loser_body)
            flaky_storage.arm(loser_key)
            reused = await publish_uploaded_attempt(
                db=db,
                storage=flaky_storage,
                attempt_id=loser.id,
            )
            first_truth = await db.get(PlaybackNormalizationAttempt, loser.id)
            assert reused.reused is True
            assert first_truth is not None
            assert first_truth.state == "cleanup_pending"
            assert first_truth.cleaned_at is None
            assert loser_key in flaky_storage.objects

        client.app.state.settings.playback_normalization_enabled = True
        receipt = await reconcile_normalization_jobs(
            sessionmaker=client.app_state["media_sessionmaker"],
            settings=client.app.state.settings,
            storage=flaky_storage,
            temporal_client=FakeTemporalClient(),
            now=datetime.now(UTC) + timedelta(seconds=1),
            actor_id="duplicate-cleanup-test",
        )
        async with client.app_state["sessionmaker"]() as db:
            final_job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            final_loser = await db.get(PlaybackNormalizationAttempt, loser.id)
            return receipt, final_job, final_loser, loser_key

    receipt, job, loser, loser_key = asyncio.run(publish_loser_then_reconcile())
    assert receipt.cleaned >= 1
    assert job.state == "ready"
    assert loser.state == "cleaned"
    assert loser.cleaned_at is not None
    assert loser_key not in flaky_storage.objects
    assert loser_key in flaky_storage.failed_keys


def test_activity_heartbeat_renews_only_the_active_tenant_job(client) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-heartbeat-lease",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    owner_sha256 = sha256(b"heartbeat-owner").hexdigest()

    async def exercise_renewal():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            job.state = "running"
            job.lease_owner_sha256 = owner_sha256
            job.lease_expires_at = now - timedelta(seconds=1)
            tenant_scope = TenantScope(
                organization_id=job.organization_id,
                workspace_id=job.workspace_id,
                user_id=job.requested_by_user_id,
                device_id=job.source_device_id,
            )
            job_id = job.id
            await db.commit()
        renewed = await renew_normalization_activity_lease(
            sessionmaker=client.app_state["media_sessionmaker"],
            tenant_scope=tenant_scope,
            job_id=job_id,
            lease_owner_sha256=owner_sha256,
            lease_duration=timedelta(seconds=90),
            now=now,
        )
        async with client.app_state["sessionmaker"]() as db:
            job = await db.get(PlaybackNormalizationJob, job_id)
            assert job is not None
            renewed_until = job.lease_expires_at
            job.lease_owner_sha256 = sha256(b"replacement-owner").hexdigest()
            await db.commit()
        stale_owner_refused = await renew_normalization_activity_lease(
            sessionmaker=client.app_state["media_sessionmaker"],
            tenant_scope=tenant_scope,
            job_id=job_id,
            lease_owner_sha256=owner_sha256,
            lease_duration=timedelta(seconds=90),
            now=now + timedelta(seconds=30),
        )
        async with client.app_state["sessionmaker"]() as db:
            job = await db.get(PlaybackNormalizationJob, job_id)
            assert job is not None
            job.state = "queued"
            job.lease_owner_sha256 = None
            job.lease_expires_at = None
            await db.commit()
        refused = await renew_normalization_activity_lease(
            sessionmaker=client.app_state["media_sessionmaker"],
            tenant_scope=tenant_scope,
            job_id=job_id,
            lease_owner_sha256=owner_sha256,
            lease_duration=timedelta(seconds=90),
            now=now + timedelta(seconds=30),
        )
        return renewed, renewed_until, stale_owner_refused, refused

    renewed, renewed_until, stale_owner_refused, refused = asyncio.run(exercise_renewal())
    assert renewed is True
    assert renewed_until.replace(tzinfo=UTC) == now + timedelta(seconds=90)
    assert stale_owner_refused is False
    assert refused is False


def test_late_worker_cannot_publish_after_expired_lease_recovery(
    client,
    tmp_path: Path,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-late-worker",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    source_keys = set(client.app_state["storage"].objects)
    recovery_time = datetime.now(UTC) + timedelta(minutes=5)

    async def expire_while_worker_is_finishing():
        started = asyncio.Event()
        release = asyncio.Event()
        pipeline = BlockingNormalizationPipeline(started, release)

        async def run_late_worker() -> None:
            async with client.app_state["sessionmaker"]() as db:
                job = await db.scalar(
                    select(PlaybackNormalizationJob).where(
                        PlaybackNormalizationJob.meeting_id == meeting_id
                    )
                )
                assert job is not None
                await apply_job_worker_scope(db, job)
                with pytest.raises(NormalizationExecutionDeferred):
                    await run_normalization_job(
                        db=db,
                        storage=client.app_state["storage"],
                        job_id=job.id,
                        work_directory=tmp_path,
                        pipeline=pipeline,
                    )

        worker_task = asyncio.create_task(run_late_worker())
        await asyncio.wait_for(started.wait(), timeout=5)
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            job.lease_expires_at = recovery_time - timedelta(seconds=1)
            await db.commit()
            recovery = await recover_expired_normalization_job(
                db,
                storage=client.app_state["storage"],
                job_id=job.id,
                now=recovery_time,
            )
            assert recovery is not None
            job_id = job.id
        release.set()
        await worker_task
        async with client.app_state["sessionmaker"]() as db:
            job = await db.get(PlaybackNormalizationJob, job_id)
            attempts = list(
                await db.scalars(
                    select(PlaybackNormalizationAttempt).where(
                        PlaybackNormalizationAttempt.job_id == job_id
                    )
                )
            )
            canonical_count = len(
                list(
                    await db.scalars(
                        select(TrackArtifact).where(
                            TrackArtifact.meeting_id == meeting_id,
                            TrackArtifact.track_role == "playback",
                            TrackArtifact.status == "stored",
                        )
                    )
                )
            )
            return job, attempts, canonical_count

    job, attempts, canonical_count = asyncio.run(expire_while_worker_is_finishing())
    assert job.state == "retry_wait"
    assert job.reason_code == "worker_interrupted"
    assert len(attempts) == 1
    assert attempts[0].state == "cleaned"
    assert attempts[0].cleanup_reason == "worker_interrupted"
    assert canonical_count == 0
    assert set(client.app_state["storage"].objects) == source_keys


def test_reconciler_recovers_lost_post_commit_dispatch_before_legacy_inventory(
    client,
    monkeypatch,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-lost-dispatch",
        include_playback=True,
    )
    assert result["status_code"] == 200
    revision_id = UUID(str(meeting["media_revision"]["media_revision_id"]))
    temporal = FakeTemporalClient()
    client.app.state.settings.playback_normalization_enabled = True
    now = datetime(2026, 7, 14, 13, 0, tzinfo=UTC)
    events: list[str] = []
    dispatch = pickup_module.dispatch_normalization_after_accepted_commit

    async def record_dispatch(**kwargs):
        events.append("dispatch")
        return await dispatch(**kwargs)

    async def record_inventory(**_kwargs):
        events.append("inventory")
        return 0, 0, 0, 0

    monkeypatch.setattr(
        pickup_module,
        "dispatch_normalization_after_accepted_commit",
        record_dispatch,
    )
    monkeypatch.setattr(pickup_module, "_inventory_legacy_workspaces", record_inventory)

    async def reconcile_twice():
        first = await reconcile_normalization_jobs(
            sessionmaker=client.app_state["media_sessionmaker"],
            settings=client.app.state.settings,
            storage=client.app_state["storage"],
            temporal_client=temporal,
            now=now,
            actor_id="restart-test",
        )
        second = await reconcile_normalization_jobs(
            sessionmaker=client.app_state["media_sessionmaker"],
            settings=client.app.state.settings,
            storage=client.app_state["storage"],
            temporal_client=temporal,
            now=now + timedelta(seconds=1),
            actor_id="restart-test",
        )
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.media_revision_id == revision_id
                )
            )
            return first, second, job

    first, second, job = asyncio.run(reconcile_twice())
    workflow_id = f"playback-normalization/{revision_id}/v1"
    assert first.dispatched == 1
    assert second.dispatched == 0
    assert events[:2] == ["dispatch", "inventory"]
    assert list(temporal.starts) == [workflow_id]
    assert job.workflow_run_id == temporal.starts[workflow_id]["run_id"]
    assert job.lease_owner_sha256 == sha256(
        f"restart-test:{job.id}".encode()
    ).hexdigest()


def test_reconciler_cleans_expired_worker_attempt_and_schedules_automatic_retry(client) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-expired-worker",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    client.app.state.settings.playback_normalization_enabled = True
    temporal = FakeTemporalClient()
    now = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
    orphan_body = b"unpublished-normalization-attempt"

    async def seed_and_reconcile():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            attempt_id = uuid4()
            object_key = f"tests/normalization-attempts/{attempt_id}"
            client.app_state["storage"].put_bytes(object_key, orphan_body)
            job.state = "running"
            job.attempt_count = 1
            job.cycle_attempt_count = 1
            job.lease_owner_sha256 = sha256(b"stale-worker").hexdigest()
            job.lease_expires_at = now - timedelta(seconds=1)
            db.add(
                PlaybackNormalizationAttempt(
                    id=attempt_id,
                    workspace_id=job.workspace_id,
                    meeting_id=job.meeting_id,
                    media_revision_id=job.media_revision_id,
                    job_id=job.id,
                    attempt_number=1,
                    cycle_number=1,
                    state="local_preparing",
                    storage_object_key=object_key,
                    derivation_kind="uploaded_candidate",
                    selected_stream_index=None,
                    source_stream_count=0,
                    source_audio_stream_count=0,
                )
            )
            await db.commit()
        receipt = await reconcile_normalization_jobs(
            sessionmaker=client.app_state["media_sessionmaker"],
            settings=client.app.state.settings,
            storage=client.app_state["storage"],
            temporal_client=temporal,
            now=now,
            actor_id="expired-worker-test",
        )
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            attempt = await db.scalar(
                select(PlaybackNormalizationAttempt).where(
                    PlaybackNormalizationAttempt.job_id == job.id
                )
            )
            return receipt, job, attempt, object_key

    receipt, job, attempt, object_key = asyncio.run(seed_and_reconcile())
    assert receipt.recovered == 1
    assert receipt.cleaned == 1
    assert job.state == "retry_wait"
    assert job.reason_code == "worker_interrupted"
    assert job.next_attempt_at.replace(tzinfo=UTC) == now + timedelta(seconds=30)
    assert job.lease_owner_sha256 is None
    assert attempt.state == "cleaned"
    assert attempt.cleaned_at is not None
    assert object_key not in client.app_state["storage"].objects
    assert temporal.starts == {}


def test_reconciler_keeps_attempt_owned_by_an_active_worker(client) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-active-worker-cleanup",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    client.app.state.settings.playback_normalization_enabled = True
    now = datetime.now(UTC)
    attempt_body = b"active-normalization-attempt"

    async def seed_and_reconcile():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            attempt_id = uuid4()
            object_key = f"tests/normalization-attempts/{attempt_id}"
            client.app_state["storage"].put_bytes(object_key, attempt_body)
            job.state = "running"
            job.attempt_count = 1
            job.cycle_attempt_count = 1
            job.lease_owner_sha256 = sha256(b"active-worker").hexdigest()
            job.lease_expires_at = now + timedelta(minutes=5)
            db.add(
                PlaybackNormalizationAttempt(
                    id=attempt_id,
                    workspace_id=job.workspace_id,
                    meeting_id=job.meeting_id,
                    media_revision_id=job.media_revision_id,
                    job_id=job.id,
                    attempt_number=1,
                    cycle_number=1,
                    state="local_preparing",
                    storage_object_key=object_key,
                    derivation_kind="uploaded_candidate",
                    selected_stream_index=None,
                    source_stream_count=0,
                    source_audio_stream_count=0,
                )
            )
            await db.commit()
        await reconcile_normalization_jobs(
            sessionmaker=client.app_state["media_sessionmaker"],
            settings=client.app.state.settings,
            storage=client.app_state["storage"],
            temporal_client=FakeTemporalClient(),
            now=now,
            actor_id="active-worker-test",
        )
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(PlaybackNormalizationAttempt, attempt_id)
        return attempt, object_key

    attempt, object_key = asyncio.run(seed_and_reconcile())
    assert attempt is not None and attempt.state == "local_preparing"
    assert object_key in client.app_state["storage"].objects


def test_startup_reconciler_immediately_dispatches_only_worker_interrupted_retry(client) -> None:
    interrupted_meeting, interrupted_result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-startup-worker-interrupted",
        include_playback=True,
    )
    deferred_meeting, deferred_result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-startup-other-retry",
        include_playback=True,
    )
    assert interrupted_result["status_code"] == 200
    assert deferred_result["status_code"] == 200
    interrupted_meeting_id = UUID(str(interrupted_meeting["meeting_id"]))
    deferred_meeting_id = UUID(str(deferred_meeting["meeting_id"]))
    client.app.state.settings.playback_normalization_enabled = True
    temporal = FakeTemporalClient()
    now = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)

    async def seed_and_start_worker_reconciliation():
        async with client.app_state["sessionmaker"]() as db:
            interrupted_job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == interrupted_meeting_id
                )
            )
            deferred_job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == deferred_meeting_id
                )
            )
            assert interrupted_job is not None
            assert deferred_job is not None
            for job, reason_code in (
                (interrupted_job, NormalizationReason.WORKER_INTERRUPTED.value),
                (deferred_job, NormalizationReason.STORAGE_UNAVAILABLE.value),
            ):
                job.state = "retry_wait"
                job.reason_code = reason_code
                job.next_attempt_at = now + timedelta(hours=24)
                job.attempt_count = 16
                job.cycle_attempt_count = 4
                job.retry_cycle_count = 4
                job.lease_owner_sha256 = None
                job.lease_expires_at = None
            interrupted_job_id = interrupted_job.id
            deferred_job_id = deferred_job.id
            await db.commit()
        receipt = await reconcile_normalization_jobs(
            sessionmaker=client.app_state["media_sessionmaker"],
            settings=client.app.state.settings,
            storage=client.app_state["storage"],
            temporal_client=temporal,
            now=now,
            actor_id="startup-worker-test",
            recover_worker_interrupted=True,
        )
        async with client.app_state["sessionmaker"]() as db:
            return (
                receipt,
                await db.get(PlaybackNormalizationJob, interrupted_job_id),
                await db.get(PlaybackNormalizationJob, deferred_job_id),
            )

    receipt, interrupted_job, deferred_job = asyncio.run(seed_and_start_worker_reconciliation())
    assert receipt.dispatched == 1
    assert interrupted_job is not None
    assert interrupted_job.state == "queued"
    assert interrupted_job.reason_code is None
    assert interrupted_job.next_attempt_at is None
    assert interrupted_job.cycle_attempt_count == 0
    assert interrupted_job.workflow_run_id is not None
    assert len(temporal.starts) == 1
    assert deferred_job is not None
    assert deferred_job.state == "retry_wait"
    assert deferred_job.reason_code == NormalizationReason.STORAGE_UNAVAILABLE.value
    assert deferred_job.next_attempt_at.replace(tzinfo=UTC) == now + timedelta(hours=24)
    assert len(temporal.starts) == 1


def test_reconciler_demotes_missing_ready_object_and_automatically_dispatches_regeneration(
    client,
    tmp_path,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-missing-ready-object",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    temporal = FakeTemporalClient()
    client.app.state.settings.playback_normalization_enabled = True
    now = datetime(2026, 7, 14, 16, 0, tzinfo=UTC)

    async def publish_remove_and_reconcile():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            execution = await run_normalization_job(
                db=db,
                storage=client.app_state["storage"],
                job_id=job.id,
                work_directory=tmp_path,
                pipeline=FakeNormalizationPipeline("copy"),
            )
            canonical = await db.get(TrackArtifact, execution.canonical_track_artifact_id)
            assert canonical is not None
            source_keys = set(client.app_state["storage"].objects) - {
                canonical.storage_object_key
            }
            client.app_state["storage"].delete_object(canonical.storage_object_key)
            job_id = job.id
            canonical_id = canonical.id
        receipt = await reconcile_normalization_jobs(
            sessionmaker=client.app_state["media_sessionmaker"],
            settings=client.app.state.settings,
            storage=client.app_state["storage"],
            temporal_client=temporal,
            now=now,
            actor_id="missing-ready-test",
        )
        async with client.app_state["sessionmaker"]() as db:
            job = await db.get(PlaybackNormalizationJob, job_id)
            canonical = await db.get(TrackArtifact, canonical_id)
            return receipt, job, canonical, source_keys

    receipt, job, old_canonical, source_keys = asyncio.run(publish_remove_and_reconcile())
    assert receipt.recovered == 1
    assert receipt.dispatched == 1
    assert job.state == "queued"
    assert job.canonical_track_artifact_id is None
    assert job.reason_code is None
    assert job.workflow_run_id is not None
    assert old_canonical.status == "superseded"
    assert source_keys <= set(client.app_state["storage"].objects)
    assert list(temporal.starts) == [job.workflow_id]


async def _ownership_job(db, meeting_id):
    job = await db.scalar(
        select(PlaybackNormalizationJob).where(PlaybackNormalizationJob.meeting_id == meeting_id)
    )
    assert job is not None
    await apply_job_worker_scope(db, job)
    return job


def _job_ownership_snapshot(job):
    return (
        job.state,
        job.reason_code,
        job.next_attempt_at,
        job.attempt_count,
        job.cycle_attempt_count,
        job.retry_cycle_count,
        job.lease_owner_sha256,
        job.lease_expires_at,
        job.last_heartbeat_at,
        job.canonical_track_artifact_id,
    )


async def _seed_next_owned_attempt(db, storage, job, *, owner, uploaded):
    failure = await record_normalization_failure(
        db,
        job_id=job.id,
        reason_code=NormalizationReason.WORKER_INTERRUPTED,
    )
    assert failure.next_attempt_at is not None
    prepared = await _prepare_attempt(
        db,
        job_id=job.id,
        lease_owner=owner,
        now=failure.next_attempt_at + timedelta(seconds=1),
    )
    if uploaded:
        await _reserve_playback_storage(
            db,
            job=job,
            attempt=prepared.attempt,
            declared_bytes=32,
            now=datetime.now(UTC),
        )
        prepared.attempt.state = "uploaded"
        prepared.attempt.output_byte_length = len(b"synthetic-next-attempt")
        prepared.attempt.output_sha256 = sha256(b"synthetic-next-attempt").hexdigest()
        prepared.attempt.uploaded_at = datetime.now(UTC)
        job.state = "publishing"
        await db.commit()
    storage.put_bytes(prepared.attempt.storage_object_key, b"synthetic-next-attempt")
    return prepared.attempt


@pytest.mark.parametrize(
    ("uploaded", "same_owner", "lock_old_attempt"),
    [
        (False, False, False),
        (False, True, False),
        (True, False, False),
        (True, True, False),
        (True, True, True),
    ],
)
def test_late_failure_preserves_next_attempt_and_removes_only_old_object(
    client,
    tmp_path,
    monkeypatch,
    uploaded,
    same_owner,
    lock_old_attempt,
):
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-late-failure-fence",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    storage = client.app_state["storage"]
    source = dict(storage.objects)

    async def exercise():
        started, release, discarding = asyncio.Event(), asyncio.Event(), asyncio.Event()

        class LateFailurePipeline(BlockingNormalizationPipeline):
            async def derive_candidate(self, source_path, output_path):
                self.started.set()
                await asyncio.wait_for(self.release.wait(), timeout=10)
                raise OSError("synthetic late failure of attempt A")

        discard = normalization_service._discard_unowned_attempt

        async def observe_discard(**kwargs):
            discarding.set()
            return await discard(**kwargs)

        monkeypatch.setattr(normalization_service, "_discard_unowned_attempt", observe_discard)

        async def old_worker():
            async with client.app_state["sessionmaker"]() as db:
                job = await _ownership_job(db, meeting_id)
                with pytest.raises(NormalizationExecutionDeferred):
                    await run_normalization_job(
                        db=db,
                        storage=storage,
                        job_id=job.id,
                        work_directory=tmp_path,
                        pipeline=LateFailurePipeline(started, release),
                        lease_owner="worker-A",
                    )

        worker = asyncio.create_task(old_worker())
        try:
            await asyncio.wait_for(started.wait(), timeout=5)
            async with client.app_state["sessionmaker"]() as db:
                job = await _ownership_job(db, meeting_id)
                old = await db.scalar(
                    select(PlaybackNormalizationAttempt).where(
                        PlaybackNormalizationAttempt.job_id == job.id,
                    )
                )
                old_id, old_key = old.id, old.storage_object_key
                job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
                await db.commit()
                assert (
                    await recover_expired_normalization_job(
                        db,
                        storage=storage,
                        job_id=job.id,
                    )
                    is not None
                )
                newer = await _seed_next_owned_attempt(
                    db,
                    storage,
                    job,
                    owner="worker-A" if same_owner else "worker-B",
                    uploaded=uploaded,
                )
                job_id, new_id, new_key = job.id, newer.id, newer.storage_object_key
                expected_job = _job_ownership_snapshot(job)
                reservation = await db.scalar(
                    select(StorageReservation).where(
                        StorageReservation.idempotency_key == f"normalization:{new_id}",
                    )
                )
                expected_reservation = (reservation.id, reservation.state) if reservation else None
            # A late PUT after recovery has already marked A CLEANED must still be removed.
            storage.put_bytes(old_key, b"synthetic-late-old-object")
            async with client.app_state["sessionmaker"]() as locker:
                if lock_old_attempt:
                    if locker.bind.dialect.name != "postgresql":
                        pytest.skip("row lock ownership requires PostgreSQL")
                    await _ownership_job(locker, meeting_id)
                    await locker.scalar(
                        select(PlaybackNormalizationAttempt)
                        .where(
                            PlaybackNormalizationAttempt.id == old_id,
                        )
                        .with_for_update()
                    )
                release.set()
                if lock_old_attempt:
                    await asyncio.wait_for(discarding.wait(), timeout=5)
                    # Failure's Job lock must be released before waiting for old Attempt.
                    assert (
                        await locker.scalar(
                            select(PlaybackNormalizationJob.id)
                            .where(
                                PlaybackNormalizationJob.id == job_id,
                            )
                            .with_for_update(nowait=True)
                        )
                        == job_id
                    )
                    await locker.rollback()
                await asyncio.wait_for(worker, timeout=5)
            async with client.app_state["sessionmaker"]() as db:
                job = await _ownership_job(db, meeting_id)
                newer = await db.get(PlaybackNormalizationAttempt, new_id)
                reservation = await db.scalar(
                    select(StorageReservation).where(
                        StorageReservation.idempotency_key == f"normalization:{new_id}",
                    )
                )
                assert _job_ownership_snapshot(job) == expected_job
                assert newer.state == ("uploaded" if uploaded else "local_preparing")
                assert (
                    (reservation.id, reservation.state) if reservation else None
                ) == expected_reservation
            assert storage.objects == {**source, new_key: b"synthetic-next-attempt"}
        finally:
            release.set()
            if not worker.done():
                worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)

    asyncio.run(exercise())
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("uploaded", [False, True])
@pytest.mark.parametrize("job_wide", [False, True])
def test_delayed_cleanup_preserves_latest_leased_attempt(client, uploaded, job_wide):
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-direct-cleanup-fence",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    storage = client.app_state["storage"]
    source = dict(storage.objects)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            job = await _ownership_job(db, meeting_id)
            old = await _prepare_attempt(db, job_id=job.id, lease_owner="worker-A")
            old_id = old.attempt.id
            newer = await _seed_next_owned_attempt(
                db,
                storage,
                job,
                owner="worker-B",
                uploaded=uploaded,
            )
            new_id, new_key = newer.id, newer.storage_object_key
            expected_job = _job_ownership_snapshot(job)
            if job_wide:
                assert (
                    await cleanup_unpublished_normalization_attempts(
                        db,
                        storage=storage,
                        job_id=job.id,
                    )
                    == 1
                )
            else:
                assert not await cleanup_normalization_attempt(
                    db,
                    storage=storage,
                    attempt_id=new_id,
                    cleanup_reason="late_A",
                )
                assert await cleanup_normalization_attempt(
                    db,
                    storage=storage,
                    attempt_id=old_id,
                    cleanup_reason="late_A",
                )
            await db.refresh(job)
            await db.refresh(newer)
            assert _job_ownership_snapshot(job) == expected_job
            assert newer.state == ("uploaded" if uploaded else "local_preparing")
            reservation = await db.scalar(
                select(StorageReservation).where(
                    StorageReservation.idempotency_key == f"normalization:{new_id}",
                )
            )
            if uploaded:
                assert reservation is not None and reservation.state == "active"
            # Expiry restores ordinary cleanup eligibility.
            job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()
            assert await cleanup_normalization_attempt(
                db,
                storage=storage,
                attempt_id=new_id,
                cleanup_reason="expired",
            )
            assert new_key not in storage.objects
        assert storage.objects == source

    asyncio.run(exercise())


@pytest.mark.parametrize("uploaded", [False, True])
@pytest.mark.parametrize("created_after_snapshot", [False, True])
def test_prepare_failure_does_not_blame_an_owned_attempt(
    client,
    tmp_path,
    monkeypatch,
    uploaded,
    created_after_snapshot,
):
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-before-prepare-fence",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    storage = client.app_state["storage"]

    async def exercise():
        async def create_owned():
            async with client.app_state["sessionmaker"]() as db:
                job = await _ownership_job(db, meeting_id)
                await _prepare_attempt(db, job_id=job.id, lease_owner="worker-A")
                await _seed_next_owned_attempt(
                    db, storage, job, owner="worker-B", uploaded=uploaded
                )
                return _job_ownership_snapshot(job), dict(storage.objects)

        expected = None if created_after_snapshot else await create_owned()

        async def fail_prepare(*args, **kwargs):
            nonlocal expected
            if created_after_snapshot:
                expected = await create_owned()
            raise OSError("synthetic preparation failure before ownership check")

        monkeypatch.setattr(normalization_service, "_prepare_attempt", fail_prepare)
        async with client.app_state["sessionmaker"]() as db:
            job = await _ownership_job(db, meeting_id)
            with pytest.raises(NormalizationExecutionDeferred):
                await run_normalization_job(
                    db=db,
                    storage=storage,
                    job_id=job.id,
                    work_directory=tmp_path,
                    pipeline=FakeNormalizationPipeline("copy"),
                )
        async with client.app_state["sessionmaker"]() as db:
            job = await _ownership_job(db, meeting_id)
            assert (_job_ownership_snapshot(job), storage.objects) == expected

    asyncio.run(exercise())


@pytest.mark.parametrize("locked_model", [PlaybackNormalizationAttempt, PlaybackNormalizationJob])
def test_cleanup_skips_contended_rows_releases_job_lock_and_retries(client, locked_model):
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-cleanup-lock-order",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    storage = client.app_state["storage"]

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            if db.bind.dialect.name != "postgresql":
                pytest.skip("SKIP LOCKED/savepoint requires PostgreSQL")
            job = await _ownership_job(db, meeting_id)
            prepared = await _prepare_attempt(db, job_id=job.id, lease_owner="worker-A")
            attempt_id, job_id = prepared.attempt.id, job.id
            object_key = prepared.attempt.storage_object_key
            job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()
            storage.put_bytes(object_key, b"synthetic-expired-output")
            before = dict(storage.objects)
            async with client.app_state["sessionmaker"]() as locker:
                await _ownership_job(locker, meeting_id)
                locked_id = attempt_id if locked_model is PlaybackNormalizationAttempt else job_id
                await locker.scalar(
                    select(locked_model)
                    .where(
                        locked_model.id == locked_id,
                    )
                    .with_for_update()
                )
                assert not await asyncio.wait_for(
                    cleanup_normalization_attempt(
                        db,
                        storage=storage,
                        attempt_id=attempt_id,
                        cleanup_reason="contended",
                    ),
                    timeout=3,
                )
                assert storage.objects == before
                # SAVEPOINT rollback must release a Job lock acquired before skipped Attempt.
                assert (
                    await locker.scalar(
                        select(PlaybackNormalizationJob.id)
                        .where(
                            PlaybackNormalizationJob.id == job_id,
                        )
                        .with_for_update(nowait=True)
                    )
                    == job_id
                )
                await locker.rollback()
            assert await cleanup_normalization_attempt(
                db,
                storage=storage,
                attempt_id=attempt_id,
                cleanup_reason="retry",
            )
            assert object_key not in storage.objects

    asyncio.run(exercise())


def test_unread_ownership_snapshot_never_records_job_wide_failure(client, tmp_path, monkeypatch):
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-unread-ownership",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            job = await _ownership_job(db, meeting_id)
            job_id = job.id
            expected = _job_ownership_snapshot(job)
            scalar = db.scalar
            failed = False

            async def fail_count(statement, *args, **kwargs):
                nonlocal failed
                if not failed and statement.column_descriptions[0]["name"] == "attempt_count":
                    failed = True
                    raise OSError("synthetic database snapshot failure")
                return await scalar(statement, *args, **kwargs)

            monkeypatch.setattr(db, "scalar", fail_count)
            with pytest.raises(NormalizationExecutionFailure) as caught:
                await run_normalization_job(
                    db=db,
                    storage=client.app_state["storage"],
                    job_id=job_id,
                    work_directory=tmp_path,
                    pipeline=FakeNormalizationPipeline("copy"),
                )
            assert failed
            assert caught.value.reason_code is NormalizationReason.DATABASE_UNAVAILABLE
            assert caught.value.should_retry
        async with client.app_state["sessionmaker"]() as db:
            job = await _ownership_job(db, meeting_id)
            assert _job_ownership_snapshot(job) == expected
            assert not list(
                await db.scalars(
                    select(PlaybackNormalizationAttempt).where(
                        PlaybackNormalizationAttempt.job_id == job_id,
                    )
                )
            )

    asyncio.run(exercise())


@pytest.mark.parametrize("boundary", ["owner", "expired", "state", "preparing"])
def test_failure_fence_checks_lease_and_preparation_boundary(client, boundary):
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-failure-lease-fence",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            job = await _ownership_job(db, meeting_id)
            prepared = await _prepare_attempt(db, job_id=job.id, lease_owner="worker-A")
            if boundary == "owner":
                job.lease_owner_sha256 = sha256(b"another-owner").hexdigest()
            elif boundary == "expired":
                job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            else:
                job.state = "queued"
            await db.commit()
            expected = _job_ownership_snapshot(job)
            with pytest.raises(NormalizationExecutionDeferred):
                await record_normalization_failure(
                    db,
                    job_id=job.id,
                    reason_code=NormalizationReason.STORAGE_UNAVAILABLE,
                    expected_attempt_count=job.attempt_count,
                    expected_lease_owner_sha256=(
                        None if boundary == "preparing" else sha256(b"worker-A").hexdigest()
                    ),
                )
            assert _job_ownership_snapshot(job) == expected
            assert prepared.attempt.state == "local_preparing"

    asyncio.run(exercise())


def test_real_directory_failure_keeps_durable_retry_and_source(client, tmp_path):
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-real-directory-failure",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    storage = client.app_state["storage"]
    source = dict(storage.objects)
    blocked = tmp_path / "owned-file"
    blocked.write_text("synthetic obstruction")

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            job = await _ownership_job(db, meeting_id)
            job_id = job.id
            with pytest.raises(NormalizationExecutionFailure) as caught:
                await run_normalization_job(
                    db=db,
                    storage=storage,
                    job_id=job_id,
                    work_directory=blocked,
                    pipeline=FFmpegNormalizationPipeline(),
                )
            assert caught.value.reason_code is NormalizationReason.TEMPORARY_STORAGE_UNAVAILABLE
            await db.refresh(job)
            assert job.state == "retry_wait" and job.next_attempt_at is not None
            assert job.lease_owner_sha256 is None
            attempt = await db.scalar(
                select(PlaybackNormalizationAttempt).where(
                    PlaybackNormalizationAttempt.job_id == job_id,
                )
            )
            assert attempt.state == "cleaned" and attempt.cleaned_at is not None

    asyncio.run(exercise())
    assert storage.objects == source
    assert list(tmp_path.iterdir()) == [blocked]
