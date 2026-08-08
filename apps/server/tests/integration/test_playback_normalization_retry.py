from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.fixtures.processing import apply_job_worker_scope
from tests.integration.test_playback_normalization_finalize import (
    _accept_first_party_recording,
)
from twobrain_rec_server.db.models import (
    IngestAuditEvent,
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    SupportIncident,
)
from twobrain_rec_server.normalization.service import (
    NormalizationExecutionFailure,
    activate_due_normalization_retry,
    record_normalization_failure,
    run_normalization_job,
)
from twobrain_rec_server.normalization.statuses import NormalizationReason


class TransientFailurePipeline:
    async def derive_candidate(self, _source_path: Path, _output_path: Path):
        raise RuntimeError("storage_unavailable")

    async def derive_dual_source(
        self,
        _microphone_path: Path,
        _system_path: Path,
        _output_path: Path,
    ):
        raise AssertionError("candidate failure must not switch to source fallback")


def test_retryable_failures_persist_four_attempt_cycle_and_continue_daily(client) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-retry-cycles",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    source_keys_before = set(client.app_state["storage"].objects)

    async def exercise_cycles():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
            short_delays: list[timedelta] = []
            long_delays: list[timedelta] = []
            total_attempts = 0
            for _cycle in range(1, 7):
                for attempt in range(1, 5):
                    total_attempts += 1
                    job = await db.get(PlaybackNormalizationJob, job.id)
                    assert job is not None
                    job.state = "running"
                    job.attempt_count = total_attempts
                    job.cycle_attempt_count = attempt
                    await db.commit()
                    failure = await record_normalization_failure(
                        db,
                        job_id=job.id,
                        reason_code=NormalizationReason.STORAGE_UNAVAILABLE,
                        failed_at=now,
                    )
                    assert failure.next_attempt_at is not None
                    delay = failure.next_attempt_at - now
                    if attempt < 4:
                        short_delays.append(delay)
                        assert failure.should_temporal_retry is True
                        assert failure.cycle_exhausted is False
                    else:
                        long_delays.append(delay)
                        assert failure.should_temporal_retry is False
                        assert failure.cycle_exhausted is True
                    now = failure.next_attempt_at
                    assert await activate_due_normalization_retry(
                        db,
                        job_id=job.id,
                        now=now,
                    )
            refreshed = await db.get(PlaybackNormalizationJob, job.id)
            incidents = list(
                await db.scalars(
                    select(SupportIncident).where(
                        SupportIncident.workspace_id == refreshed.workspace_id,
                        SupportIncident.problem_code
                        == "playback_normalization.retry_cycle_exhausted",
                    )
                )
            )
            audit_events = list(
                await db.scalars(
                    select(IngestAuditEvent).where(
                        IngestAuditEvent.meeting_id == meeting_id,
                        IngestAuditEvent.event_type.like("playback_normalization_%"),
                    )
                )
            )
            return refreshed, short_delays, long_delays, incidents, audit_events

    job, short_delays, long_delays, incidents, audit_events = asyncio.run(exercise_cycles())
    assert short_delays[:3] == [
        timedelta(seconds=30),
        timedelta(seconds=60),
        timedelta(seconds=120),
    ]
    assert long_delays == [
        timedelta(minutes=15),
        timedelta(hours=1),
        timedelta(hours=6),
        timedelta(hours=24),
        timedelta(hours=24),
        timedelta(hours=24),
    ]
    assert job.state == "queued"
    assert job.retry_cycle_count == 6
    assert job.cycle_attempt_count == 0
    assert len(incidents) == 6
    assert all(incident.redaction_result == "accepted" for incident in incidents)
    event_types = [event.event_type for event in audit_events]
    assert event_types.count("playback_normalization_requested") == 1
    assert event_types.count("playback_normalization_failed") == 24
    assert event_types.count("playback_normalization_retried") == 24
    assert event_types.count("playback_normalization_retry_cycle_exhausted") == 6
    assert event_types.count("playback_normalization_incident_recorded") == 6
    assert set(client.app_state["storage"].objects) == source_keys_before


def test_permanent_source_failure_stops_automatic_retry_without_reupload(client) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-permanent-stop",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    source_keys_before = set(client.app_state["storage"].objects)

    async def mark_permanent():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            job.state = "running"
            job.attempt_count = 1
            job.cycle_attempt_count = 1
            await db.commit()
            failure = await record_normalization_failure(
                db,
                job_id=job.id,
                reason_code=NormalizationReason.NO_AUDIO,
                failed_at=datetime(2026, 7, 14, 12, 0, tzinfo=UTC),
            )
            return failure, await db.get(PlaybackNormalizationJob, job.id)

    failure, job = asyncio.run(mark_permanent())
    assert failure.state.value == "terminal"
    assert failure.should_temporal_retry is False
    assert failure.next_attempt_at is None
    assert job.state == "terminal"
    assert job.reason_code == "no_audio"
    assert set(client.app_state["storage"].objects) == source_keys_before


def test_real_attempt_failure_is_durable_cleaned_and_keeps_accepted_source(
    client,
    tmp_path: Path,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-real-transient-attempt",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    source_keys_before = set(client.app_state["storage"].objects)
    work_directory = tmp_path / "normalization-retry-work"

    async def execute_failure():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            with pytest.raises(NormalizationExecutionFailure) as caught:
                await run_normalization_job(
                    db=db,
                    storage=client.app_state["storage"],
                    job_id=job.id,
                    work_directory=work_directory,
                    pipeline=TransientFailurePipeline(),
                )
            assert caught.value.reason_code is NormalizationReason.STORAGE_UNAVAILABLE
            assert caught.value.should_retry is True
            refreshed = await db.get(PlaybackNormalizationJob, job.id)
            attempt = await db.scalar(
                select(PlaybackNormalizationAttempt).where(
                    PlaybackNormalizationAttempt.job_id == job.id
                )
            )
            return refreshed, attempt

    job, attempt = asyncio.run(execute_failure())
    assert job.state == "retry_wait"
    assert job.reason_code == "storage_unavailable"
    assert job.attempt_count == 1
    assert job.cycle_attempt_count == 1
    assert attempt.state == "cleaned"
    assert attempt.cleaned_at is not None
    assert set(client.app_state["storage"].objects) == source_keys_before
    assert list(work_directory.iterdir()) == []
