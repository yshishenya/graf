from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.integration.test_playback_normalization_finalize import (
    _accept_first_party_recording,
)
from tests.integration.test_playback_normalization_retry import TransientFailurePipeline
from tests.integration.test_playback_normalization_workflow import FakeNormalizationPipeline
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import IngestAuditEvent, PlaybackNormalizationJob
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.normalization.service import (
    NormalizationExecutionFailure,
    activate_due_normalization_retry,
    run_normalization_job,
)


async def _apply_worker_context(db) -> None:
    await apply_tenant_scope(
        db,
        TenantScope(
            organization_id=ORG_ID,
            workspace_id=WORKSPACE_ID,
            user_id=USER_ID,
            device_id=DEVICE_ID,
        ),
        context_kind="worker",
    )


def test_worker_interruption_recovery_may_bypass_stale_activity_backoff(client) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-worker-interruption-backoff",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))

    async def exercise() -> bool:
        async with client.app_state["sessionmaker"]() as db:
            await _apply_worker_context(db)
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
            job.state = "retry_wait"
            job.reason_code = "worker_interrupted"
            job.next_attempt_at = now + timedelta(minutes=5)
            await db.commit()
            assert not await activate_due_normalization_retry(db, job_id=job.id, now=now)
            return await activate_due_normalization_retry(
                db,
                job_id=job.id,
                now=now,
                recover_worker_interruption=True,
            )

    assert asyncio.run(exercise()) is True


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
            await _apply_worker_context(db)
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
            await _apply_worker_context(db)
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
            await _apply_worker_context(db)
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
            await _apply_worker_context(db)
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
