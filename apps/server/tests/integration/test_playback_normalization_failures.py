from __future__ import annotations

import asyncio
from asyncio import CancelledError
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from tests.integration.test_playback_normalization_finalize import (
    _accept_first_party_recording,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.billing.storage import StorageAdmissionError
from twobrain_rec_server.db.models import (
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    StorageReservation,
    TrackArtifact,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.normalization import service as normalization_service
from twobrain_rec_server.normalization.media import (
    MediaPolicyError,
    ProcessOutputLimitError,
)
from twobrain_rec_server.normalization.service import (
    NormalizationExecutionFailure,
    NormalizedOutput,
    normalization_reason_from_exception,
    run_normalization_job,
)
from twobrain_rec_server.normalization.statuses import NormalizationReason


@pytest.mark.parametrize(
    ("failure", "expected_reason"),
    [
        (CancelledError(), NormalizationReason.WORKER_INTERRUPTED),
        (SQLAlchemyError("synthetic database failure"), NormalizationReason.DATABASE_UNAVAILABLE),
        (TimeoutError(), NormalizationReason.NORMALIZATION_TIMEOUT),
        (OSError(), NormalizationReason.TEMPORARY_STORAGE_UNAVAILABLE),
        (RuntimeError("publish_interrupted"), NormalizationReason.PUBLISH_INTERRUPTED),
    ],
)
def test_runtime_failure_types_have_safe_retryable_ownership(
    failure: BaseException,
    expected_reason: NormalizationReason,
) -> None:
    assert normalization_reason_from_exception(failure) is expected_reason


class FailingPipeline:
    def __init__(self, failure: BaseException, *, leave_partial_output: bool = False) -> None:
        self.failure = failure
        self.leave_partial_output = leave_partial_output

    async def derive_candidate(self, source_path: Path, output_path: Path):
        del source_path
        return self._fail(output_path)

    async def derive_dual_source(
        self,
        microphone_path: Path,
        system_path: Path,
        output_path: Path,
    ):
        del microphone_path, system_path
        return self._fail(output_path)

    async def derive_single_source(
        self,
        source_path: Path,
        output_path: Path,
        *,
        tolerant_first: bool = False,
        expected_duration_seconds: int | None = None,
    ):
        del tolerant_first, expected_duration_seconds
        del source_path
        return self._fail(output_path)

    def _fail(self, output_path: Path):
        if self.leave_partial_output:
            output_path.write_bytes(b"partial-unvalidated-output")
        raise self.failure


class InvalidReceiptPipeline:
    async def derive_candidate(self, source_path: Path, output_path: Path):
        del source_path
        return self._invalid(output_path)

    async def derive_dual_source(
        self,
        microphone_path: Path,
        system_path: Path,
        output_path: Path,
    ) -> NormalizedOutput:
        del microphone_path, system_path
        return self._invalid(output_path)

    async def derive_single_source(
        self,
        source_path: Path,
        output_path: Path,
        *,
        tolerant_first: bool = False,
        expected_duration_seconds: int | None = None,
    ) -> NormalizedOutput:
        del tolerant_first, expected_duration_seconds
        del source_path
        return self._invalid(output_path)

    @staticmethod
    def _invalid(output_path: Path) -> NormalizedOutput:
        body = b"complete-bytes-with-invalid-receipt"
        output_path.write_bytes(body)
        return NormalizedOutput(
            derivation_kind="single_source_transcode",
            selected_stream_index=0,
            source_stream_count=1,
            source_audio_stream_count=1,
            source_duration_ms=60_000,
            output_duration_ms=60_000,
            output_byte_length=len(body),
            output_sha256=sha256(body).hexdigest(),
            output_audio_bit_rate=64_000,
            output_sample_rate_hz=44_100,
            output_channel_count=1,
            moov_before_mdat=True,
            fragmented=False,
            full_decode_passed=True,
        )


class ValidReceiptPipeline:
    async def derive_candidate(self, source_path: Path, output_path: Path):
        del source_path
        return self._valid(output_path)

    async def derive_dual_source(
        self,
        microphone_path: Path,
        system_path: Path,
        output_path: Path,
    ) -> NormalizedOutput:
        del microphone_path, system_path
        return self._valid(output_path)

    async def derive_single_source(
        self,
        source_path: Path,
        output_path: Path,
        *,
        tolerant_first: bool = False,
        expected_duration_seconds: int | None = None,
    ) -> NormalizedOutput:
        del tolerant_first, expected_duration_seconds, source_path
        return self._valid(output_path)

    @staticmethod
    def _valid(output_path: Path) -> NormalizedOutput:
        body = b"complete-validated-canonical-output"
        output_path.write_bytes(body)
        return NormalizedOutput(
            derivation_kind="dual_source_mix_transcode",
            selected_stream_index=None,
            source_stream_count=2,
            source_audio_stream_count=2,
            source_duration_ms=60_000,
            output_duration_ms=60_000,
            output_byte_length=len(body),
            output_sha256=sha256(body).hexdigest(),
            output_audio_bit_rate=64_000,
            output_sample_rate_hz=48_000,
            output_channel_count=1,
            moov_before_mdat=True,
            fragmented=False,
            full_decode_passed=True,
        )


async def _apply_worker_scope(db, job: PlaybackNormalizationJob) -> None:
    """Match the production worker's exact database authority for direct calls."""

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


def test_storage_capacity_rejection_happens_before_canonical_put_and_does_not_retry(
    client,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-storage-capacity",
        include_playback=False,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    source_objects = set(client.app_state["storage"].objects)
    admission_calls = 0

    async def reject_capacity(*_args, **_kwargs):
        nonlocal admission_calls
        admission_calls += 1
        raise StorageAdmissionError("storage capacity exceeded")

    monkeypatch.setattr(normalization_service, "reserve_storage", reject_capacity)

    async def execute_failure():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await _apply_worker_scope(db, job)
            with pytest.raises(NormalizationExecutionFailure) as caught:
                await run_normalization_job(
                    db=db,
                    storage=client.app_state["storage"],
                    job_id=job.id,
                    work_directory=tmp_path / "storage-capacity",
                    pipeline=ValidReceiptPipeline(),
                )
            return caught.value, await db.get(PlaybackNormalizationJob, job.id)

    caught, job = asyncio.run(execute_failure())

    assert admission_calls == 1
    assert caught.reason_code is NormalizationReason.STORAGE_CAPACITY_EXCEEDED
    assert caught.should_retry is False
    assert job.state == "terminal"
    assert job.reason_code == NormalizationReason.STORAGE_CAPACITY_EXCEEDED.value
    assert set(client.app_state["storage"].objects) == source_objects


@pytest.mark.parametrize(
    ("case_name", "failure", "expected_reason"),
    [
        (
            "temporary-storage-pressure",
            MediaPolicyError("temporary_storage_unavailable"),
            NormalizationReason.TEMPORARY_STORAGE_UNAVAILABLE,
        ),
        (
            "dependency-unavailable",
            MediaPolicyError("dependency_unavailable"),
            NormalizationReason.DEPENDENCY_UNAVAILABLE,
        ),
        (
            "process-timeout",
            MediaPolicyError("normalization_timeout"),
            NormalizationReason.NORMALIZATION_TIMEOUT,
        ),
        (
            "bounded-process-output-cap",
            ProcessOutputLimitError(),
            NormalizationReason.DEPENDENCY_UNAVAILABLE,
        ),
        (
            "generated-output-invalid",
            MediaPolicyError("generated_output_invalid"),
            NormalizationReason.GENERATED_OUTPUT_INVALID,
        ),
    ],
)
def test_system_resource_and_output_failures_stay_in_automatic_recovery_and_clean_up(
    client,
    tmp_path: Path,
    case_name: str,
    failure: BaseException,
    expected_reason: NormalizationReason,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id=f"normalization-failure-{case_name}",
        include_playback=False,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    source_objects = set(client.app_state["storage"].objects)
    work_directory = tmp_path / case_name

    async def execute_failure():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await _apply_worker_scope(db, job)
            with pytest.raises(NormalizationExecutionFailure) as caught:
                await run_normalization_job(
                    db=db,
                    storage=client.app_state["storage"],
                    job_id=job.id,
                    work_directory=work_directory,
                    pipeline=FailingPipeline(failure, leave_partial_output=True),
                )
            refreshed = await db.get(PlaybackNormalizationJob, job.id)
            attempt = await db.scalar(
                select(PlaybackNormalizationAttempt).where(
                    PlaybackNormalizationAttempt.job_id == job.id
                )
            )
            canonical = list(
                await db.scalars(
                    select(TrackArtifact).where(
                        TrackArtifact.meeting_id == meeting_id,
                        TrackArtifact.track_role == "playback",
                        TrackArtifact.status == "stored",
                    )
                )
            )
            return caught.value, refreshed, attempt, canonical

    caught, job, attempt, canonical = asyncio.run(execute_failure())

    assert caught.reason_code is expected_reason
    assert caught.should_retry is True
    assert job.state == "retry_wait"
    assert job.reason_code == expected_reason.value
    assert job.next_attempt_at is not None
    assert attempt.state == "cleaned"
    assert attempt.cleaned_at is not None
    assert canonical == []
    assert set(client.app_state["storage"].objects) == source_objects
    assert list(work_directory.iterdir()) == []


@pytest.mark.parametrize(
    ("case_name", "free_bytes", "work_budget_bytes"),
    [
        ("insufficient-free-space", 0, 6_442_450_944),
        ("insufficient-job-budget", 10**15, 1),
    ],
)
def test_work_capacity_preflight_stops_before_download_and_retries_automatically(
    client,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case_name: str,
    free_bytes: int,
    work_budget_bytes: int,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id=f"normalization-capacity-{case_name}",
        include_playback=False,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    source_objects = set(client.app_state["storage"].objects)
    work_directory = tmp_path / case_name
    monkeypatch.setattr(
        normalization_service.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(free=free_bytes),
    )

    async def execute_failure():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await _apply_worker_scope(db, job)
            with pytest.raises(NormalizationExecutionFailure) as caught:
                await run_normalization_job(
                    db=db,
                    storage=client.app_state["storage"],
                    job_id=job.id,
                    work_directory=work_directory,
                    pipeline=FailingPipeline(AssertionError("pipeline must not run")),
                    work_budget_bytes=work_budget_bytes,
                )
            return (
                caught.value,
                await db.get(PlaybackNormalizationJob, job.id),
                await db.scalar(
                    select(PlaybackNormalizationAttempt).where(
                        PlaybackNormalizationAttempt.job_id == job.id
                    )
                ),
            )

    caught, job, attempt = asyncio.run(execute_failure())

    assert caught.reason_code is NormalizationReason.TEMPORARY_STORAGE_UNAVAILABLE
    assert caught.should_retry is True
    assert job.state == "retry_wait"
    assert job.reason_code == NormalizationReason.TEMPORARY_STORAGE_UNAVAILABLE.value
    assert attempt.state == "cleaned"
    assert attempt.cleaned_at is not None
    assert set(client.app_state["storage"].objects) == source_objects
    assert list(work_directory.iterdir()) == []


def test_invalid_output_receipt_cannot_publish_and_cleanup_remains_server_owned(
    client,
    tmp_path: Path,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-invalid-output-receipt",
        include_playback=False,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    source_objects = set(client.app_state["storage"].objects)
    work_directory = tmp_path / "invalid-output-receipt"

    async def execute_failure():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await _apply_worker_scope(db, job)
            with pytest.raises(NormalizationExecutionFailure) as caught:
                await run_normalization_job(
                    db=db,
                    storage=client.app_state["storage"],
                    job_id=job.id,
                    work_directory=work_directory,
                    pipeline=InvalidReceiptPipeline(),
                )
            return (
                caught.value,
                await db.get(PlaybackNormalizationJob, job.id),
                await db.scalar(
                    select(PlaybackNormalizationAttempt).where(
                        PlaybackNormalizationAttempt.job_id == job.id
                    )
                ),
            )

    caught, job, attempt = asyncio.run(execute_failure())

    assert caught.reason_code is NormalizationReason.GENERATED_OUTPUT_INVALID
    assert job.state == "retry_wait"
    assert attempt.state == "cleaned"
    assert attempt.cleaned_at is not None
    assert set(client.app_state["storage"].objects) == source_objects
    assert list(work_directory.iterdir()) == []


def test_failed_canonical_put_releases_pre_admitted_storage_reservation(
    client,
    tmp_path: Path,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-put-failure-reservation",
        include_playback=False,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    source_objects = set(client.app_state["storage"].objects)
    client.app_state["storage"].fail_put = True

    async def execute_failure():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await _apply_worker_scope(db, job)
            with pytest.raises(NormalizationExecutionFailure) as caught:
                await run_normalization_job(
                    db=db,
                    storage=client.app_state["storage"],
                    job_id=job.id,
                    work_directory=tmp_path / "put-failure-reservation",
                    pipeline=ValidReceiptPipeline(),
                )
            reservation = await db.scalar(
                select(StorageReservation).where(
                    StorageReservation.idempotency_key.like("normalization:%")
                )
            )
            attempt = await db.scalar(
                select(PlaybackNormalizationAttempt).where(
                    PlaybackNormalizationAttempt.job_id == job.id
                )
            )
            return caught.value, reservation, attempt

    try:
        caught, reservation, attempt = asyncio.run(execute_failure())
    finally:
        client.app_state["storage"].fail_put = False

    assert caught.reason_code is NormalizationReason.DEPENDENCY_UNAVAILABLE
    assert caught.should_retry is True
    assert reservation is not None
    assert reservation.state == "released"
    assert attempt.state == "cleaned"
    assert attempt.cleaned_at is not None
    assert set(client.app_state["storage"].objects) == source_objects
