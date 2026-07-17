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
    TrackArtifact,
)
from twobrain_rec_server.normalization.pickup import reconcile_normalization_jobs
from twobrain_rec_server.normalization.service import (
    NormalizationExecutionDeferred,
    publish_uploaded_attempt,
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
            sessionmaker=client.app_state["sessionmaker"],
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
            sessionmaker=client.app_state["sessionmaker"],
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
            sessionmaker=client.app_state["sessionmaker"],
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
            sessionmaker=client.app_state["sessionmaker"],
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


def test_reconciler_recovers_lost_post_commit_dispatch_once(client) -> None:
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

    async def reconcile_twice():
        first = await reconcile_normalization_jobs(
            sessionmaker=client.app_state["sessionmaker"],
            settings=client.app.state.settings,
            storage=client.app_state["storage"],
            temporal_client=temporal,
            now=now,
            actor_id="restart-test",
        )
        second = await reconcile_normalization_jobs(
            sessionmaker=client.app_state["sessionmaker"],
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
            sessionmaker=client.app_state["sessionmaker"],
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
            sessionmaker=client.app_state["sessionmaker"],
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
            sessionmaker=client.app_state["sessionmaker"],
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
