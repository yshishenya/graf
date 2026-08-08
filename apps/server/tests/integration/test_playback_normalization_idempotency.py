from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
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
    TrackArtifact,
    Workspace,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.normalization.pickup import (
    dispatch_normalization_after_accepted_commit,
)
from twobrain_rec_server.normalization.service import (
    publish_uploaded_attempt,
    run_normalization_job,
    upsert_playback_normalization_job,
)
from twobrain_rec_server.storage.object_keys import build_playback_attempt_object_key


class WorkflowAlreadyStartedError(RuntimeError):
    pass


class SingleWorkflowTemporalClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def start_workflow(
        self,
        _workflow,
        _payload,
        *,
        id: str,
        task_queue: str,
        **_options: object,
    ):
        assert task_queue
        self.calls.append(id)
        if len(self.calls) > 1:
            raise WorkflowAlreadyStartedError(id)
        return {"workflow_id": id, "run_id": "single-active-run"}


def test_duplicate_finalize_job_and_expired_pickup_reuse_one_workflow(client) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-duplicate-pickup",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    revision_id = UUID(str(meeting["media_revision"]["media_revision_id"]))
    temporal = SingleWorkflowTemporalClient()
    client.app.state.settings.playback_normalization_enabled = True
    tenant_scope = TenantScope(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        user_id=USER_ID,
        device_id=DEVICE_ID,
    )
    now = datetime(2026, 7, 14, 17, 0, tzinfo=UTC)

    async def duplicate_upsert_and_dispatch():
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_scope(db, tenant_scope)
            first_job = await upsert_playback_normalization_job(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                media_revision_id=revision_id,
            )
            second_job = await upsert_playback_normalization_job(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                media_revision_id=revision_id,
            )
            await db.commit()
            assert first_job is not None and second_job is not None
            assert first_job.id == second_job.id
            first = await dispatch_normalization_after_accepted_commit(
                db=db,
                settings=client.app.state.settings,
                tenant_scope=tenant_scope,
                media_revision_id=revision_id,
                temporal_client=temporal,
                lease_owner="first-pickup",
                now=now,
            )
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_scope(db, tenant_scope)
            job = await db.get(PlaybackNormalizationJob, first_job.id)
            assert job is not None
            job.lease_expires_at = now - timedelta(seconds=1)
            await db.commit()
            second = await dispatch_normalization_after_accepted_commit(
                db=db,
                settings=client.app.state.settings,
                tenant_scope=tenant_scope,
                media_revision_id=revision_id,
                temporal_client=temporal,
                lease_owner="second-pickup",
                now=now,
            )
            job_count = await db.scalar(
                select(func.count())
                .select_from(PlaybackNormalizationJob)
                .where(PlaybackNormalizationJob.media_revision_id == revision_id)
            )
            job = await db.get(PlaybackNormalizationJob, first_job.id)
            return first, second, job_count, job

    first, second, job_count, job = asyncio.run(duplicate_upsert_and_dispatch())
    expected_id = f"playback-normalization/{revision_id}/v1"
    assert first.started is True
    assert second.reused is True
    assert job_count == 1
    assert job.workflow_id == expected_id
    assert job.workflow_run_id == "single-active-run"
    assert temporal.calls == [expected_id, expected_id]


@pytest.mark.parametrize(
    ("delete_fails", "expected_state", "object_remains"),
    ((False, "cleaned", False), (True, "cleanup_pending", True)),
)
def test_late_duplicate_publisher_preserves_cleanup_truth_and_reuses_one_canonical(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
    delete_fails: bool,
    expected_state: str,
    object_remains: bool,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-duplicate-publisher",
        include_playback=True,
    )
    assert result["status_code"] == 200
    storage = client.app_state["storage"]
    loser_body = b"late-valid-canonical-output"

    def fail_delete(_object_key: str) -> None:
        raise RuntimeError("configured delete failure")

    async def execute_and_publish_loser():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == UUID(str(meeting["meeting_id"]))
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            winner = await run_normalization_job(
                db=db,
                storage=storage,
                job_id=job.id,
                work_directory=tmp_path,
                pipeline=FakeNormalizationPipeline("copy"),
            )
            workspace = await db.get(Workspace, job.workspace_id)
            assert workspace is not None
            loser_id = uuid4()
            loser_key = build_playback_attempt_object_key(
                organization_id=workspace.organization_id,
                workspace_id=job.workspace_id,
                meeting_id=job.meeting_id,
                media_revision_id=job.media_revision_id,
                attempt_id=loser_id,
            )
            storage.put_bytes(loser_key, loser_body)
            if delete_fails:
                monkeypatch.setattr(storage, "delete_object", fail_delete)
            loser = PlaybackNormalizationAttempt(
                id=loser_id,
                workspace_id=job.workspace_id,
                meeting_id=job.meeting_id,
                media_revision_id=job.media_revision_id,
                job_id=job.id,
                attempt_number=2,
                cycle_number=1,
                state="uploaded",
                storage_object_key=loser_key,
                derivation_kind="dual_source_mix_transcode",
                selected_stream_index=None,
                source_stream_count=2,
                source_audio_stream_count=2,
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
            reused = await publish_uploaded_attempt(
                db=db,
                storage=storage,
                attempt_id=loser.id,
            )
            canonical_count = await db.scalar(
                select(func.count())
                .select_from(TrackArtifact)
                .where(
                    TrackArtifact.media_revision_id == job.media_revision_id,
                    TrackArtifact.track_role == "playback",
                    TrackArtifact.status == "stored",
                    TrackArtifact.validated_at.is_not(None),
                )
            )
            refreshed_loser = await db.get(PlaybackNormalizationAttempt, loser.id)
            return winner, reused, canonical_count, refreshed_loser, loser_key

    winner, reused, canonical_count, loser, loser_key = asyncio.run(execute_and_publish_loser())
    assert reused.reused is True
    assert reused.canonical_track_artifact_id == winner.canonical_track_artifact_id
    assert canonical_count == 1
    assert loser.state == expected_state
    assert (loser.cleaned_at is None) is object_remains
    assert (loser_key in storage.objects) is object_remains
