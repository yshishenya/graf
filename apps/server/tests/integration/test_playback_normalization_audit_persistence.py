from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.integration.test_playback_normalization_finalize import (
    _accept_first_party_recording,
)
from tests.integration.test_playback_normalization_retry import TransientFailurePipeline
from tests.integration.test_playback_normalization_workflow import FakeNormalizationPipeline
from twobrain_rec_server.db.models import IngestAuditEvent, PlaybackNormalizationJob
from twobrain_rec_server.normalization.service import (
    NormalizationExecutionFailure,
    activate_due_normalization_retry,
    run_normalization_job,
)


def test_success_lifecycle_audit_is_persisted_once_and_ready_reuse_is_silent(
    client,
    tmp_path: Path,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-audit-success",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))

    async def exercise():
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
            reused = await run_normalization_job(
                db=db,
                storage=client.app_state["storage"],
                job_id=job.id,
                work_directory=tmp_path,
                pipeline=FakeNormalizationPipeline("invalid"),
            )
            assert reused.reused is True
        async with client.app_state["sessionmaker"]() as db:
            return list(
                await db.scalars(
                    select(IngestAuditEvent).where(
                        IngestAuditEvent.meeting_id == meeting_id,
                        IngestAuditEvent.event_type.like("playback_normalization_%"),
                    )
                )
            )

    events = asyncio.run(exercise())
    event_types = [event.event_type for event in events]
    assert event_types.count("playback_normalization_requested") == 1
    assert event_types.count("playback_normalization_started") == 1
    assert event_types.count("playback_normalization_publishing") == 1
    assert event_types.count("playback_normalization_completed") == 1
    assert len(events) == 4
    completed = next(
        event for event in events if event.event_type == "playback_normalization_completed"
    )
    assert completed.metadata_json["state"] == "ready"
    assert completed.metadata_json["full_decode_passed"] is True
    assert completed.metadata_json["moov_before_mdat"] is True
    serialized = json.dumps([event.metadata_json for event in events], sort_keys=True)
    assert "normalization-audit-success" not in serialized
    assert "storage_object_key" not in serialized


def test_failed_attempt_cleanup_and_due_retry_each_emit_one_durable_event(
    client,
    tmp_path: Path,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-audit-retry",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            with pytest.raises(NormalizationExecutionFailure):
                await run_normalization_job(
                    db=db,
                    storage=client.app_state["storage"],
                    job_id=job.id,
                    work_directory=tmp_path,
                    pipeline=TransientFailurePipeline(),
                )
            job = await db.get(PlaybackNormalizationJob, job.id)
            assert job is not None and job.next_attempt_at is not None
            due_at = job.next_attempt_at
            assert await activate_due_normalization_retry(db, job_id=job.id, now=due_at)
            assert not await activate_due_normalization_retry(
                db,
                job_id=job.id,
                now=datetime.now(UTC),
            )
        async with client.app_state["sessionmaker"]() as db:
            return list(
                await db.scalars(
                    select(IngestAuditEvent).where(
                        IngestAuditEvent.meeting_id == meeting_id,
                        IngestAuditEvent.event_type.like("playback_normalization_%"),
                    )
                )
            )

    events = asyncio.run(exercise())
    event_types = [event.event_type for event in events]
    assert event_types.count("playback_normalization_requested") == 1
    assert event_types.count("playback_normalization_started") == 1
    assert event_types.count("playback_normalization_failed") == 1
    assert event_types.count("playback_normalization_temp_cleaned") == 1
    assert event_types.count("playback_normalization_retried") == 1
    assert len(events) == 5
    assert next(
        event.metadata_json["reason_code"]
        for event in events
        if event.event_type == "playback_normalization_failed"
    ) == "storage_unavailable"
    assert next(
        event.metadata_json["cleanup_result"]
        for event in events
        if event.event_type == "playback_normalization_temp_cleaned"
    ) == "already_missing"
