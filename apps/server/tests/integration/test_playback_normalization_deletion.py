from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet_access import add_retained_playback_m4a
from tests.fixtures.processing import create_finalized_meeting
from tests.integration.test_playback_normalization_finalize import (
    _accept_first_party_recording,
)
from tests.integration.test_playback_normalization_workflow import FakeNormalizationPipeline
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import (
    IngestAuditEvent,
    PlaybackBackfillRun,
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    TrackArtifact,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.normalization.service import (
    NormalizationExecutionDeferred,
    NormalizationExecutionFailure,
    cleanup_normalization_attempt,
    run_normalization_job,
)
from twobrain_rec_server.normalization.statuses import CANONICAL_PROFILE_VERSION

BOUNDED_COPY = "Delete this meeting everywhere GRAF controls."


@pytest.mark.parametrize(
    ("job_state", "attempt_state"),
    [
        ("queued", None),
        ("running", "local_preparing"),
        ("publishing", "uploaded"),
        ("retry_wait", "cleanup_pending"),
    ],
)
def test_deletion_wins_at_every_normalization_boundary_and_purges_orphans(
    client,
    job_state: str,
    attempt_state: str | None,
) -> None:
    meeting_id, job_id, attempt_id, attempt_key = asyncio.run(
        _seed_normalization_boundary(
            client,
            suffix=f"{job_state}-{attempt_state or 'none'}",
            job_state=job_state,
            attempt_state=attempt_state,
        )
    )

    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )

    assert response.status_code == 202
    truth = asyncio.run(_load_normalization_lifecycle(client, job_id, attempt_id))
    assert truth["job"].state == "cancelled"
    assert truth["job"].reason_code == "meeting_deleting"
    assert truth["job"].cancelled_at is not None
    assert truth["job"].lease_owner_sha256 is None
    assert truth["job"].lease_expires_at is None
    event_types = [event.event_type for event in truth["events"]]
    assert event_types.count("playback_normalization_cancelled") == 1
    if attempt_id is not None:
        assert truth["attempt"].state == "purged"
        assert truth["attempt"].cleanup_reason == "meeting_deleting"
        if attempt_state == "local_preparing":
            assert truth["attempt"].cleaned_at is None
        else:
            assert truth["attempt"].cleaned_at is not None
        assert attempt_key not in client.app_state["storage"].objects
        cleanup_events = [
            event
            for event in truth["events"]
            if event.event_type == "playback_normalization_temp_cleaned"
        ]
        assert len(cleanup_events) == 1
        assert cleanup_events[0].metadata_json["cleanup_result"] == (
            "deleted"
            if attempt_state in {"uploaded", "cleanup_pending"}
            else "already_missing_pending_recheck"
        )

    report = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report",
        headers=auth_headers(),
    )
    assert report.status_code == 200
    rows = {row["artifact_class"]: row for row in report.json()["artifact_states"]}
    assert rows["normalization_job"]["state"] == "metadata_retained"
    expected_attempt_state = "purged" if attempt_id is not None else "not_applicable"
    assert rows["normalization_attempt_temp"]["state"] == expected_attempt_state
    assert "storage_object_key" not in report.text.lower()


def test_deletion_reports_candidate_and_canonical_separately(client) -> None:
    candidate_meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-deletion-candidate",
        include_playback=True,
    )
    assert result["status_code"] == 200
    candidate_id = UUID(str(candidate_meeting["meeting_id"]))
    asyncio.run(_seed_backfill_link(client, candidate_id))

    candidate_delete = client.post(
        f"/api/v1/cabinet/meetings/{candidate_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    candidate_report = client.get(
        f"/api/v1/cabinet/meetings/{candidate_id}/deletion-report",
        headers=auth_headers(),
    )

    assert candidate_delete.status_code == 202
    candidate_rows = {
        row["artifact_class"]: row for row in candidate_report.json()["artifact_states"]
    }
    assert candidate_rows["playback_candidate"]["state"] == "purged"
    assert candidate_rows["playback_canonical"]["state"] == "not_applicable"
    assert candidate_rows["normalization_backfill"]["state"] == "metadata_retained"

    finalized = create_finalized_meeting(client, "normalization-deletion-canonical")
    canonical_id = UUID(str(finalized["meeting"]["meeting_id"]))
    canonical_body = add_retained_playback_m4a(client, canonical_id)
    canonical_key, attempt_id = asyncio.run(
        _seed_published_attempt_for_canonical(client, canonical_id, canonical_body)
    )

    canonical_delete = client.post(
        f"/api/v1/cabinet/meetings/{canonical_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    canonical_report = client.get(
        f"/api/v1/cabinet/meetings/{canonical_id}/deletion-report",
        headers=auth_headers(),
    )

    assert canonical_delete.status_code == 202
    canonical_rows = {
        row["artifact_class"]: row for row in canonical_report.json()["artifact_states"]
    }
    assert canonical_rows["playback_candidate"]["state"] == "not_applicable"
    assert canonical_rows["playback_canonical"]["state"] == "purged"
    assert canonical_rows["normalization_attempt_temp"]["state"] == "purged"
    assert client.app_state["storage"].deleted_keys.count(canonical_key) == 1
    canonical_truth = asyncio.run(
        _load_normalization_lifecycle(client, None, attempt_id, meeting_id=canonical_id)
    )
    assert canonical_truth["job"].state == "cancelled"
    assert canonical_truth["job"].canonical_track_artifact_id is None
    assert canonical_truth["attempt"].state == "purged"


def test_deletion_waits_for_inflight_upload_and_removes_the_serialized_output(
    client,
    tmp_path: Path,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-deletion-late-worker",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    work_directory = tmp_path / "normalization-work"
    delegate_storage = client.app_state["storage"]

    async def delete_while_upload_holds_the_meeting_lock():
        upload_started = asyncio.Event()
        release_upload = asyncio.Event()

        class BlockingUploadStorage:
            async def put_stream_async(self, object_key, stream, length):
                upload_started.set()
                await release_upload.wait()
                delegate_storage.put_stream(object_key, stream, length)

            def __getattr__(self, name):
                return getattr(delegate_storage, name)

        storage = BlockingUploadStorage()

        async def run_late_worker() -> None:
            async with client.app_state["sessionmaker"]() as db:
                job = await db.scalar(
                    select(PlaybackNormalizationJob).where(
                        PlaybackNormalizationJob.meeting_id == meeting_id
                    )
                )
                assert job is not None
                with suppress(
                    NormalizationExecutionDeferred,
                    NormalizationExecutionFailure,
                ):
                    await run_normalization_job(
                        db=db,
                        storage=storage,
                        job_id=job.id,
                        work_directory=work_directory,
                        pipeline=FakeNormalizationPipeline("copy"),
                    )

        worker_task = asyncio.create_task(run_late_worker())
        await asyncio.wait_for(upload_started.wait(), timeout=5)
        async with client.app_state["sessionmaker"]() as db:
            active_attempt = await db.scalar(
                select(PlaybackNormalizationAttempt).where(
                    PlaybackNormalizationAttempt.meeting_id == meeting_id
                )
            )
            assert active_attempt is not None
            attempt_key = active_attempt.storage_object_key
        deletion_task = asyncio.create_task(
            asyncio.to_thread(
                client.post,
                f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
                headers=auth_headers(),
                json={"confirmation_boundary": BOUNDED_COPY},
            )
        )
        await asyncio.sleep(0.1)
        assert not deletion_task.done()
        release_upload.set()
        await asyncio.wait_for(worker_task, timeout=5)
        deletion = await asyncio.wait_for(deletion_task, timeout=5)

        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            attempts = list(
                await db.scalars(
                    select(PlaybackNormalizationAttempt).where(
                        PlaybackNormalizationAttempt.meeting_id == meeting_id
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
                            TrackArtifact.validated_at.is_not(None),
                        )
                    )
                )
            )
        return deletion, job, attempts, canonical_count, attempt_key

    deletion, job, attempts, canonical_count, attempt_key = asyncio.run(
        delete_while_upload_holds_the_meeting_lock()
    )
    assert deletion.status_code == 202
    assert job.state == "cancelled"
    assert job.reason_code == "meeting_deleting"
    assert len(attempts) == 1
    assert attempts[0].state == "purged"
    assert attempts[0].cleanup_reason == "meeting_deleting"
    assert attempts[0].storage_object_key not in client.app_state["storage"].objects
    assert attempts[0].cleaned_at is not None
    assert attempt_key in client.app_state["storage"].deleted_keys
    assert canonical_count == 0
    assert list(work_directory.iterdir()) == []


def test_deleted_local_attempt_rechecks_forever_and_removes_a_late_object(client) -> None:
    meeting_id, job_id, attempt_id, attempt_key = asyncio.run(
        _seed_normalization_boundary(
            client,
            suffix="late-object-after-process-loss",
            job_state="running",
            attempt_state="local_preparing",
        )
    )
    assert attempt_id is not None

    deletion = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert deletion.status_code == 202

    async def cleanup_once() -> bool:
        async with client.app_state["sessionmaker"]() as db:
            job = await db.get(PlaybackNormalizationJob, job_id)
            assert job is not None
            await apply_tenant_scope(
                db,
                TenantScope(
                    organization_id=job.organization_id,
                    workspace_id=job.workspace_id,
                    user_id=job.requested_by_user_id,
                    device_id=job.source_device_id,
                ),
                context_kind="worker",
            )
            return await cleanup_normalization_attempt(
                db,
                storage=client.app_state["storage"],
                attempt_id=attempt_id,
                cleanup_reason="automatic_recovery",
            )

    assert asyncio.run(cleanup_once()) is False
    before_late_arrival = asyncio.run(_load_normalization_lifecycle(client, job_id, attempt_id))
    assert before_late_arrival["attempt"].cleaned_at is None

    client.app_state["storage"].put_stream(
        attempt_key,
        BytesIO(b"late-object"),
        len(b"late-object"),
    )
    assert asyncio.run(cleanup_once()) is True

    after_cleanup = asyncio.run(_load_normalization_lifecycle(client, job_id, attempt_id))
    assert after_cleanup["attempt"].state == "purged"
    assert after_cleanup["attempt"].cleaned_at is not None
    assert attempt_key not in client.app_state["storage"].objects
    cleanup_results = [
        event.metadata_json["cleanup_result"]
        for event in after_cleanup["events"]
        if event.event_type == "playback_normalization_temp_cleaned"
    ]
    assert cleanup_results == ["already_missing_pending_recheck", "deleted"]


async def _seed_normalization_boundary(
    client,
    *,
    suffix: str,
    job_state: str,
    attempt_state: str | None,
) -> tuple[UUID, UUID, UUID | None, str | None]:
    finalized = create_finalized_meeting(client, f"normalization-deletion-{suffix}")
    meeting_id = UUID(str(finalized["meeting"]["meeting_id"]))
    now = datetime.now(UTC)
    async with client.app_state["sessionmaker"]() as db:
        job = await db.scalar(
            select(PlaybackNormalizationJob).where(
                PlaybackNormalizationJob.meeting_id == meeting_id
            )
        )
        assert job is not None
        job.state = job_state
        job.reason_code = "storage_unavailable" if job_state == "retry_wait" else None
        job.next_attempt_at = now + timedelta(minutes=5) if job_state == "retry_wait" else None
        if job_state in {"running", "publishing"}:
            job.started_at = now
            job.lease_owner_sha256 = sha256(b"deletion-boundary-worker").hexdigest()
            job.lease_expires_at = now + timedelta(minutes=5)

        attempt = None
        attempt_key = None
        if attempt_state is not None:
            job.attempt_count = 1
            job.cycle_attempt_count = 1
            attempt_key = f"tests/normalization/{meeting_id}/{attempt_state}.m4a"
            attempt = PlaybackNormalizationAttempt(
                workspace_id=job.workspace_id,
                meeting_id=job.meeting_id,
                media_revision_id=job.media_revision_id,
                job_id=job.id,
                attempt_number=1,
                cycle_number=1,
                state=attempt_state,
                storage_object_key=attempt_key,
                derivation_kind="dual_source_mix_transcode",
                selected_stream_index=None,
                source_stream_count=2,
                source_audio_stream_count=2,
            )
            if attempt_state in {"uploaded", "cleanup_pending"}:
                body = f"normalized-{suffix}".encode()
                client.app_state["storage"].put_bytes(attempt_key, body)
                attempt.output_duration_ms = 60_000
                attempt.output_byte_length = len(body)
                attempt.output_sha256 = sha256(body).hexdigest()
                attempt.output_audio_bit_rate = 64_000
                attempt.output_sample_rate_hz = 48_000
                attempt.output_channel_count = 1
                attempt.moov_before_mdat = True
                attempt.fragmented = False
                attempt.full_decode_passed = True
                attempt.uploaded_at = now
            db.add(attempt)
        await db.commit()
        return meeting_id, job.id, attempt.id if attempt is not None else None, attempt_key


async def _seed_backfill_link(client, meeting_id: UUID) -> None:
    now = datetime.now(UTC)
    async with client.app_state["sessionmaker"]() as db:
        job = await db.scalar(
            select(PlaybackNormalizationJob).where(
                PlaybackNormalizationJob.meeting_id == meeting_id
            )
        )
        assert job is not None
        run = PlaybackBackfillRun(
            workspace_id=job.workspace_id,
            profile_version=CANONICAL_PROFILE_VERSION,
            state="inventory_complete",
            inventory_started_at=now,
            inventory_completed_at=now,
        )
        db.add(run)
        await db.flush()
        job.trigger_kind = "legacy_backfill"
        job.priority_class = "legacy_backfill"
        job.backfill_run_id = run.id
        await db.commit()


async def _seed_published_attempt_for_canonical(
    client,
    meeting_id: UUID,
    body: bytes,
) -> tuple[str, UUID]:
    now = datetime.now(UTC)
    async with client.app_state["sessionmaker"]() as db:
        job = await db.scalar(
            select(PlaybackNormalizationJob).where(
                PlaybackNormalizationJob.meeting_id == meeting_id
            )
        )
        canonical = await db.scalar(
            select(TrackArtifact).where(
                TrackArtifact.meeting_id == meeting_id,
                TrackArtifact.track_role == "playback",
                TrackArtifact.status == "stored",
            )
        )
        assert job is not None and canonical is not None
        job.attempt_count = 1
        job.cycle_attempt_count = 1
        attempt = PlaybackNormalizationAttempt(
            workspace_id=job.workspace_id,
            meeting_id=job.meeting_id,
            media_revision_id=job.media_revision_id,
            job_id=job.id,
            attempt_number=1,
            cycle_number=1,
            state="published",
            storage_object_key=canonical.storage_object_key,
            published_track_artifact_id=canonical.id,
            derivation_kind=canonical.derivation_kind or "uploaded_candidate",
            selected_stream_index=0,
            source_stream_count=1,
            source_audio_stream_count=1,
            source_duration_ms=1_000,
            output_duration_ms=1_000,
            output_byte_length=len(body),
            output_sha256=sha256(body).hexdigest(),
            output_audio_bit_rate=64_000,
            output_sample_rate_hz=48_000,
            output_channel_count=1,
            moov_before_mdat=True,
            fragmented=False,
            full_decode_passed=True,
            uploaded_at=now,
            published_at=now,
        )
        db.add(attempt)
        await db.commit()
        return canonical.storage_object_key, attempt.id


async def _load_normalization_lifecycle(
    client,
    job_id: UUID | None,
    attempt_id: UUID | None,
    *,
    meeting_id: UUID | None = None,
) -> dict[str, object | None]:
    async with client.app_state["sessionmaker"]() as db:
        job = (
            await db.get(PlaybackNormalizationJob, job_id)
            if job_id is not None
            else await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
        )
        attempt = (
            await db.get(PlaybackNormalizationAttempt, attempt_id)
            if attempt_id is not None
            else None
        )
        events = list(
            await db.scalars(
                select(IngestAuditEvent).where(
                    IngestAuditEvent.meeting_id == job.meeting_id,
                    IngestAuditEvent.event_type.like("playback_normalization_%"),
                )
            )
        )
        return {"job": job, "attempt": attempt, "events": events}
