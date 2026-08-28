from __future__ import annotations

import os
import shutil
import tempfile
from asyncio import CancelledError
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from anyio import to_thread
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.catalog import FREE_STORAGE_BYTES
from twobrain_rec_server.billing.entitlements import effective_plan_code
from twobrain_rec_server.billing.source_lifecycle import (
    clear_source_playback_verification,
    mark_source_playback_verified,
)
from twobrain_rec_server.billing.storage import (
    StorageAdmissionError,
    commit_storage_reservation,
    lock_storage_workspace,
    release_storage_reservation,
    reserve_storage,
)
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    MediaRevision,
    Meeting,
    PlaybackBackfillRun,
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    StorageReservation,
    TrackArtifact,
    Workspace,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.tenant_context import (
    rehydrate_tenant_context,
    require_database_context,
)
from twobrain_rec_server.domain.statuses import (
    DeletionState,
    MediaRevisionSourceKind,
    MediaRevisionStatus,
    TrackRole,
)
from twobrain_rec_server.ingest.media_revisions import (
    authoritative_track_roles,
    source_fingerprint_sha256,
)
from twobrain_rec_server.ingest.store import (
    archive_audio_for_revision,
    persist_orphan_cleanup_intents,
)
from twobrain_rec_server.normalization.audit import add_normalization_audit_event
from twobrain_rec_server.normalization.media import (
    MAX_DECODE_PROGRESS_BYTES,
    MAX_DURATION_SECONDS,
    MAX_GENERATED_DURATION_SECONDS,
    MAX_OUTPUT_BYTES,
    MAX_PROBE_STDOUT_BYTES,
    MAX_PROCESS_STDERR_BYTES,
    RECOVERED_TRANSCODE_MAX_DURATION_LOSS_RATIO,
    RECOVERED_TRANSCODE_MAX_DURATION_LOSS_SECONDS,
    TRANSCODE_MIX_DURATION_TOLERANCE_SECONDS,
    BMFFLayout,
    FileDigest,
    FullDecodeReceipt,
    MediaPolicyError,
    NormalizationAction,
    ProbeFacts,
    ProbeStream,
    ProcessExecutionError,
    ProcessResult,
    build_dual_mix_command,
    build_full_decode_command,
    build_lossless_remux_command,
    build_probe_command,
    build_transcode_command,
    copy_regular_file,
    hash_regular_file,
    inspect_bmff,
    inspected_container_family,
    parse_full_decode_progress,
    parse_probe_output,
    run_bounded_process,
    select_audio_stream,
    validate_canonical_profile,
    validate_duration_alignment,
    validate_probe_source_file,
    validate_tolerant_output_duration,
    validate_tolerant_source_duration,
)
from twobrain_rec_server.normalization.statuses import (
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
    AttemptState,
    BackfillState,
    DerivationKind,
    JobState,
    NormalizationReason,
    PlannedAction,
    PriorityClass,
    ReasonClass,
    TriggerKind,
    ensure_attempt_transition,
    ensure_backfill_transition,
    ensure_job_transition,
    reason_class,
    retry_failure_schedule,
)
from twobrain_rec_server.processing.fences import meeting_is_deleted_or_deleting
from twobrain_rec_server.storage.object_keys import build_playback_attempt_object_key
from twobrain_rec_server.workflows.temporal_client import (
    playback_normalization_workflow_id,
)


class CandidateRejected(ValueError):
    """An optional playback derivative is unusable; accepted source remains usable."""


class NormalizationExecutionFailure(RuntimeError):
    """A safe durable failure result that Temporal may retry without raw media output."""

    def __init__(
        self,
        *,
        reason_code: NormalizationReason,
        should_retry: bool,
        cycle_exhausted: bool,
    ) -> None:
        super().__init__(f"playback normalization failed: {reason_code.value}")
        self.reason_code = reason_code
        self.should_retry = should_retry
        self.cycle_exhausted = cycle_exhausted


class NormalizationExecutionDeferred(RuntimeError):
    """The durable job is already owned or is not due yet."""


@dataclass(frozen=True, slots=True)
class NormalizedOutput:
    derivation_kind: str
    selected_stream_index: int | None
    source_stream_count: int
    source_audio_stream_count: int
    source_duration_ms: int
    output_duration_ms: int
    output_byte_length: int
    output_sha256: str
    output_audio_bit_rate: int
    output_sample_rate_hz: int
    output_channel_count: int
    moov_before_mdat: bool
    fragmented: bool
    full_decode_passed: bool
    recovered_source: bool = False


@dataclass(frozen=True, slots=True)
class NormalizationExecutionResult:
    job_id: UUID
    canonical_track_artifact_id: UUID
    derivation_kind: str
    reused: bool


@dataclass(frozen=True, slots=True)
class NormalizationFailureResult:
    job_id: UUID
    state: JobState
    reason_code: NormalizationReason
    next_attempt_at: datetime | None
    retry_cycle_count: int
    should_temporal_retry: bool
    cycle_exhausted: bool


@dataclass(frozen=True, slots=True)
class NormalizationManualRetryResult:
    result: str
    job_id: UUID | None = None
    media_revision_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class BackfillInventoryPageResult:
    run_id: UUID
    state: str
    evaluated: int = 0
    inventory_completed: bool = False
    reused_completed: bool = False


@dataclass(frozen=True, slots=True)
class _BackfillArtifactFacts:
    id: UUID
    track_role: str
    status: str
    sha256: str
    normalization_profile_version: str | None
    validated_at: datetime | None
    derivation_kind: str | None
    source_fingerprint_sha256: str | None
    validation_version: str | None


@dataclass(frozen=True, slots=True)
class _BackfillDecision:
    planned_action: PlannedAction
    state: JobState
    reason_code: NormalizationReason | None = None
    canonical_track_artifact_id: UUID | None = None


class NormalizationPipeline(Protocol):
    async def derive_candidate(
        self,
        source_path: Path,
        output_path: Path,
    ) -> NormalizedOutput: ...

    async def derive_dual_source(
        self,
        microphone_path: Path,
        system_path: Path,
        output_path: Path,
    ) -> NormalizedOutput: ...

    async def derive_single_source(
        self,
        source_path: Path,
        output_path: Path,
        *,
        tolerant_first: bool = False,
        expected_duration_seconds: int | None = None,
    ) -> NormalizedOutput: ...


DEFAULT_NORMALIZATION_ACTIVITY_LEASE = timedelta(seconds=90)
DEFAULT_NORMALIZATION_WORK_BUDGET_BYTES = 6_442_450_944
DEFAULT_NORMALIZATION_WORK_RESERVE_BYTES = 268_435_456
_SINGLE_SOURCE_KINDS = frozenset(
    {
        MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value,
        MediaRevisionSourceKind.MANUAL_UPLOAD.value,
    }
)


def _require_normalization_work_capacity(
    work_directory: Path,
    *,
    source_bytes: int,
    sources_downloaded: bool,
    work_budget_bytes: int,
    output_max_bytes: int,
    reserve_bytes: int,
) -> None:
    if source_bytes < 0 or work_budget_bytes <= 0 or output_max_bytes <= 0 or reserve_bytes <= 0:
        raise MediaPolicyError("temporary_storage_unavailable")
    required_job_bytes = source_bytes + output_max_bytes + reserve_bytes
    if required_job_bytes > work_budget_bytes:
        raise MediaPolicyError("temporary_storage_unavailable")
    required_free_bytes = (
        output_max_bytes + reserve_bytes if sources_downloaded else required_job_bytes
    )
    try:
        free_bytes = shutil.disk_usage(work_directory).free
    except OSError as exc:
        raise MediaPolicyError("temporary_storage_unavailable") from exc
    if free_bytes < required_free_bytes:
        raise MediaPolicyError("temporary_storage_unavailable")


class FFmpegNormalizationPipeline:
    def __init__(
        self,
        *,
        ffmpeg_path: str | Path = "/usr/bin/ffmpeg",
        ffprobe_path: str | Path = "/usr/bin/ffprobe",
        probe_timeout_seconds: float = 60,
        process_timeout_seconds: float = 21_600,
        probe_stdout_limit_bytes: int = MAX_PROBE_STDOUT_BYTES,
        process_stderr_limit_bytes: int = MAX_PROCESS_STDERR_BYTES,
    ) -> None:
        self.ffmpeg_path = str(ffmpeg_path)
        self.ffprobe_path = str(ffprobe_path)
        self.probe_timeout_seconds = probe_timeout_seconds
        self.process_timeout_seconds = process_timeout_seconds
        self.probe_stdout_limit_bytes = probe_stdout_limit_bytes
        self.process_stderr_limit_bytes = process_stderr_limit_bytes
        self.allowed_executables = (self.ffmpeg_path, self.ffprobe_path)

    @classmethod
    def from_settings(cls, settings: Settings) -> FFmpegNormalizationPipeline:
        return cls(
            ffmpeg_path=settings.playback_normalization_ffmpeg_path,
            ffprobe_path=settings.playback_normalization_ffprobe_path,
            probe_timeout_seconds=settings.playback_normalization_probe_timeout_seconds,
            process_timeout_seconds=settings.playback_normalization_activity_timeout_seconds,
            probe_stdout_limit_bytes=settings.playback_normalization_probe_stdout_max_bytes,
            process_stderr_limit_bytes=settings.playback_normalization_process_stderr_max_bytes,
        )

    async def derive_candidate(
        self,
        source_path: Path,
        output_path: Path,
    ) -> NormalizedOutput:
        try:
            facts, stream = await self._probe_source(source_path)
            _reject_known_probe_duration_over_limit(facts, stream)
            recovered_source = False
            try:
                decode_receipt = await self._full_decode(
                    source_path,
                    stream_index=stream.index,
                    generated=False,
                )
                duration = decode_receipt.duration_seconds
            except MediaPolicyError as exc:
                if exc.reason_code != "corrupt_source":
                    raise
                duration = _known_probe_duration_seconds(facts, stream)
                if duration is None:
                    raise
                recovered_source = True
            ideal_layout = BMFFLayout(
                box_types=("ftyp", "moov", "mdat"),
                moov_before_mdat=True,
                fragmented=False,
                has_private_metadata=False,
            )
            try:
                if recovered_source:
                    raise MediaPolicyError("generated_output_invalid")
                validate_canonical_profile(
                    facts,
                    bmff_layout=ideal_layout,
                    byte_length=source_path.stat().st_size,
                    full_decode_passed=True,
                    enforce_reuse_bitrate=True,
                )
                actual_layout = await _inspect_bmff(source_path)
                validate_canonical_profile(
                    facts,
                    bmff_layout=actual_layout,
                    byte_length=source_path.stat().st_size,
                    full_decode_passed=True,
                    enforce_reuse_bitrate=True,
                )
            except MediaPolicyError as exc:
                if exc.reason_code == "duration_limit_exceeded":
                    raise
                if recovered_source:
                    action = NormalizationAction.RECOVERED_SINGLE_TRANSCODE
                    await self._run_ffmpeg(
                        build_transcode_command(
                            self.ffmpeg_path,
                            source_path,
                            output_path,
                            stream_index=stream.index,
                            tolerant=True,
                        ),
                        cwd=output_path.parent,
                    )
                    derivation_kind = DerivationKind.SINGLE_SOURCE_TRANSCODE.value
                    enforce_reuse_bitrate = False
                else:
                    action = NormalizationAction.FASTSTART_REMUX
                    await self._run_ffmpeg(
                        build_lossless_remux_command(
                            self.ffmpeg_path,
                            source_path,
                            output_path,
                            stream_index=stream.index,
                        ),
                        cwd=output_path.parent,
                    )
                    derivation_kind = DerivationKind.LOSSLESS_FASTSTART_REMUX.value
                    enforce_reuse_bitrate = True
            else:
                action = NormalizationAction.BYTE_COPY
                copy_regular_file(source_path, output_path)
                derivation_kind = DerivationKind.UPLOADED_CANDIDATE.value
                enforce_reuse_bitrate = True
            return await self._validated_output(
                output_path,
                action=action,
                derivation_kind=derivation_kind,
                source_durations=(duration,),
                source_stream_count=facts.stream_count,
                source_audio_stream_count=len(facts.audio_streams),
                source_duration_ms=_duration_milliseconds(duration),
                selected_stream_index=stream.index,
                enforce_reuse_bitrate=enforce_reuse_bitrate,
                recovered_source=recovered_source,
            )
        except MediaPolicyError as exc:
            if exc.reason_code in {
                "dependency_unavailable",
                "normalization_timeout",
                "temporary_storage_unavailable",
            }:
                raise
            raise CandidateRejected() from None
        except OSError as exc:
            raise MediaPolicyError("temporary_storage_unavailable") from exc

    async def derive_single_source(
        self,
        source_path: Path,
        output_path: Path,
        *,
        tolerant_first: bool = False,
        expected_duration_seconds: int | None = None,
    ) -> NormalizedOutput:
        try:
            facts, stream = await self._probe_source(source_path)
            _reject_known_probe_duration_over_limit(facts, stream)
            if tolerant_first:
                duration = validate_tolerant_source_duration(facts, stream)
                if expected_duration_seconds is not None:
                    _validate_authoritative_source_duration(
                        _duration_milliseconds(duration),
                        expected_duration_seconds=expected_duration_seconds,
                        manual_upload=True,
                    )
                await self._run_ffmpeg(
                    build_transcode_command(
                        self.ffmpeg_path,
                        source_path,
                        output_path,
                        stream_index=stream.index,
                        tolerant=True,
                    ),
                    cwd=output_path.parent,
                )
                return await self._validated_output(
                    output_path,
                    action=NormalizationAction.SINGLE_TRANSCODE,
                    derivation_kind=DerivationKind.SINGLE_SOURCE_TRANSCODE.value,
                    source_durations=(duration,),
                    source_stream_count=facts.stream_count,
                    source_audio_stream_count=len(facts.audio_streams),
                    source_duration_ms=_duration_milliseconds(duration),
                    selected_stream_index=stream.index,
                    enforce_reuse_bitrate=False,
                    recovered_source=False,
                    tolerant_first=True,
                )
            recovered_source = False
            try:
                decode_receipt = await self._full_decode(
                    source_path,
                    stream_index=stream.index,
                    generated=False,
                )
                duration = decode_receipt.duration_seconds
            except MediaPolicyError as exc:
                if exc.reason_code != "corrupt_source":
                    raise
                duration = _known_probe_duration_seconds(facts, stream)
                if duration is None:
                    raise
                recovered_source = True

            ideal_layout = BMFFLayout(
                box_types=("ftyp", "moov", "mdat"),
                moov_before_mdat=True,
                fragmented=False,
                has_private_metadata=False,
            )
            try:
                if recovered_source:
                    raise MediaPolicyError("generated_output_invalid")
                validate_canonical_profile(
                    facts,
                    bmff_layout=ideal_layout,
                    byte_length=source_path.stat().st_size,
                    full_decode_passed=True,
                    enforce_reuse_bitrate=True,
                )
            except MediaPolicyError as exc:
                if exc.reason_code == "duration_limit_exceeded":
                    raise
                action = (
                    NormalizationAction.RECOVERED_SINGLE_TRANSCODE
                    if recovered_source
                    else NormalizationAction.SINGLE_TRANSCODE
                )
                await self._run_ffmpeg(
                    build_transcode_command(
                        self.ffmpeg_path,
                        source_path,
                        output_path,
                        stream_index=stream.index,
                        tolerant=recovered_source,
                    ),
                    cwd=output_path.parent,
                )
                derivation_kind = DerivationKind.SINGLE_SOURCE_TRANSCODE.value
                enforce_reuse_bitrate = False
            else:
                actual_layout = await _inspect_bmff(source_path)
                try:
                    validate_canonical_profile(
                        facts,
                        bmff_layout=actual_layout,
                        byte_length=source_path.stat().st_size,
                        full_decode_passed=True,
                        enforce_reuse_bitrate=True,
                    )
                except MediaPolicyError:
                    action = NormalizationAction.FASTSTART_REMUX
                    await self._run_ffmpeg(
                        build_lossless_remux_command(
                            self.ffmpeg_path,
                            source_path,
                            output_path,
                            stream_index=stream.index,
                        ),
                        cwd=output_path.parent,
                    )
                    derivation_kind = DerivationKind.LOSSLESS_FASTSTART_REMUX.value
                else:
                    action = NormalizationAction.BYTE_COPY
                    copy_regular_file(source_path, output_path)
                    derivation_kind = DerivationKind.SOURCE_BYTE_COPY.value
                enforce_reuse_bitrate = True

            return await self._validated_output(
                output_path,
                action=action,
                derivation_kind=derivation_kind,
                source_durations=(duration,),
                source_stream_count=facts.stream_count,
                source_audio_stream_count=len(facts.audio_streams),
                source_duration_ms=_duration_milliseconds(duration),
                selected_stream_index=stream.index,
                enforce_reuse_bitrate=enforce_reuse_bitrate,
                recovered_source=recovered_source,
            )
        except OSError as exc:
            raise MediaPolicyError("temporary_storage_unavailable") from exc

    async def derive_dual_source(
        self,
        microphone_path: Path,
        system_path: Path,
        output_path: Path,
    ) -> NormalizedOutput:
        microphone_facts, microphone_stream = await self._probe_source(microphone_path)
        system_facts, system_stream = await self._probe_source(system_path)
        _reject_known_probe_duration_over_limit(microphone_facts, microphone_stream)
        _reject_known_probe_duration_over_limit(system_facts, system_stream)
        microphone_decode = await self._full_decode(
            microphone_path,
            stream_index=microphone_stream.index,
            generated=False,
        )
        system_decode = await self._full_decode(
            system_path,
            stream_index=system_stream.index,
            generated=False,
        )
        microphone_duration = microphone_decode.duration_seconds
        system_duration = system_decode.duration_seconds
        await self._run_ffmpeg(
            build_dual_mix_command(
                self.ffmpeg_path,
                microphone_path,
                system_path,
                output_path,
                microphone_stream_index=microphone_stream.index,
                system_stream_index=system_stream.index,
            ),
            cwd=output_path.parent,
        )
        return await self._validated_output(
            output_path,
            action=NormalizationAction.DUAL_MIX_TRANSCODE,
            derivation_kind=DerivationKind.DUAL_SOURCE_MIX_TRANSCODE.value,
            source_durations=(microphone_duration, system_duration),
            source_stream_count=microphone_facts.stream_count + system_facts.stream_count,
            source_audio_stream_count=(
                len(microphone_facts.audio_streams) + len(system_facts.audio_streams)
            ),
            source_duration_ms=_duration_milliseconds(max(microphone_duration, system_duration)),
            selected_stream_index=None,
            enforce_reuse_bitrate=False,
        )

    async def _probe_source(self, source_path: Path) -> tuple[ProbeFacts, ProbeStream]:
        validate_probe_source_file(source_path)
        try:
            result = await run_bounded_process(
                build_probe_command(self.ffprobe_path, source_path),
                timeout_seconds=self.probe_timeout_seconds,
                stdout_limit_bytes=self.probe_stdout_limit_bytes,
                stderr_limit_bytes=self.process_stderr_limit_bytes,
                allowed_executables=self.allowed_executables,
                cwd=source_path.parent,
            )
        except ProcessExecutionError as exc:
            if exc.return_code < 0:
                raise MediaPolicyError("dependency_unavailable") from exc
            raise MediaPolicyError("corrupt_source") from exc
        facts = parse_probe_output(result.stdout)
        return facts, select_audio_stream(
            facts,
            container_family=inspected_container_family(facts, source_path),
        )

    async def _full_decode(
        self,
        source_path: Path,
        *,
        stream_index: int,
        generated: bool,
    ) -> FullDecodeReceipt:
        try:
            result = await self._run_ffmpeg(
                build_full_decode_command(
                    self.ffmpeg_path,
                    source_path,
                    stream_index=stream_index,
                ),
                cwd=source_path.parent,
                stdout_limit_bytes=MAX_DECODE_PROGRESS_BYTES,
            )
        except ProcessExecutionError as exc:
            if exc.return_code < 0:
                raise MediaPolicyError("dependency_unavailable") from exc
            reason = "generated_output_invalid" if generated else "corrupt_source"
            raise MediaPolicyError(reason) from exc
        receipt = parse_full_decode_progress(result.stdout)
        duration_limit = MAX_GENERATED_DURATION_SECONDS if generated else MAX_DURATION_SECONDS
        if receipt.duration_seconds > duration_limit:
            reason = "generated_output_invalid" if generated else "duration_limit_exceeded"
            raise MediaPolicyError(reason)
        return receipt

    async def _run_ffmpeg(
        self,
        argv: list[str],
        *,
        cwd: Path,
        stdout_limit_bytes: int = 0,
    ) -> ProcessResult:
        return await run_bounded_process(
            argv,
            timeout_seconds=self.process_timeout_seconds,
            stdout_limit_bytes=stdout_limit_bytes,
            stderr_limit_bytes=self.process_stderr_limit_bytes,
            allowed_executables=self.allowed_executables,
            cwd=cwd,
        )

    async def _validated_output(
        self,
        output_path: Path,
        *,
        action: NormalizationAction,
        derivation_kind: str,
        source_durations: tuple[Decimal, ...],
        source_stream_count: int,
        source_audio_stream_count: int,
        source_duration_ms: int,
        selected_stream_index: int | None,
        enforce_reuse_bitrate: bool,
        recovered_source: bool = False,
        tolerant_first: bool = False,
    ) -> NormalizedOutput:
        try:
            output_facts, output_stream = await self._probe_source(output_path)
            decode_receipt = await self._full_decode(
                output_path,
                stream_index=output_stream.index,
                generated=True,
            )
            layout = await _inspect_bmff(output_path)
            digest = await _hash_regular_file(output_path, max_bytes=MAX_OUTPUT_BYTES)
            validate_canonical_profile(
                output_facts,
                bmff_layout=layout,
                byte_length=digest.byte_length,
                full_decode_passed=True,
                enforce_reuse_bitrate=enforce_reuse_bitrate,
            )
            output_duration = decode_receipt.duration_seconds
            if tolerant_first:
                validate_tolerant_output_duration(
                    source_duration_seconds=max(source_durations),
                    output_format_duration_seconds=output_facts.duration_seconds,
                    output_stream_duration_seconds=output_stream.duration_seconds,
                    output_decode_duration_seconds=output_duration,
                )
            else:
                validate_duration_alignment(
                    action=action,
                    source_durations_seconds=source_durations,
                    output_duration_seconds=output_duration,
                )
            output_bit_rate = output_stream.bit_rate or output_facts.bit_rate
            if output_bit_rate is None or output_bit_rate <= 0:
                raise MediaPolicyError("generated_output_invalid")
            return NormalizedOutput(
                derivation_kind=derivation_kind,
                selected_stream_index=selected_stream_index,
                source_stream_count=source_stream_count,
                source_audio_stream_count=source_audio_stream_count,
                source_duration_ms=source_duration_ms,
                output_duration_ms=_duration_milliseconds(output_duration),
                output_byte_length=digest.byte_length,
                output_sha256=digest.sha256_hex,
                output_audio_bit_rate=output_bit_rate,
                output_sample_rate_hz=output_stream.sample_rate_hz or 0,
                output_channel_count=output_stream.channels or 0,
                moov_before_mdat=layout.moov_before_mdat,
                fragmented=layout.fragmented,
                full_decode_passed=True,
                recovered_source=recovered_source,
            )
        except MediaPolicyError as exc:
            if exc.reason_code in {
                "dependency_unavailable",
                "normalization_timeout",
                "temporary_storage_unavailable",
            }:
                raise
            raise MediaPolicyError("generated_output_invalid") from exc


def _known_probe_duration_seconds(facts: ProbeFacts, stream: ProbeStream) -> Decimal | None:
    duration = stream.duration_seconds or facts.duration_seconds
    if duration is None or not duration.is_finite() or duration <= 0:
        return None
    return duration


def _reject_known_probe_duration_over_limit(facts: ProbeFacts, stream: ProbeStream) -> None:
    duration = _known_probe_duration_seconds(facts, stream)
    if duration is not None and duration > MAX_DURATION_SECONDS:
        raise MediaPolicyError("duration_limit_exceeded")


def _duration_milliseconds(duration: Decimal) -> int:
    milliseconds = int((duration * 1_000).to_integral_value())
    if milliseconds <= 0:
        raise MediaPolicyError("corrupt_source")
    return milliseconds


def _validate_authoritative_source_duration(
    source_duration_ms: int,
    *,
    expected_duration_seconds: int,
    manual_upload: bool = False,
) -> None:
    expected = Decimal(expected_duration_seconds)
    tolerance = (
        Decimal("1.25")
        if manual_upload
        else max(
            TRANSCODE_MIX_DURATION_TOLERANCE_SECONDS,
            min(
                RECOVERED_TRANSCODE_MAX_DURATION_LOSS_SECONDS,
                expected * RECOVERED_TRANSCODE_MAX_DURATION_LOSS_RATIO,
            ),
        )
    )
    if abs(Decimal(source_duration_ms) / Decimal("1000") - expected) > tolerance:
        raise MediaPolicyError("source_mismatch")


@dataclass(frozen=True, slots=True)
class _AttemptInputs:
    job: PlaybackNormalizationJob
    attempt: PlaybackNormalizationAttempt
    expected_duration_seconds: int
    candidate: TrackArtifact | None
    media: TrackArtifact | None
    microphone: TrackArtifact | None
    system: TrackArtifact | None
    source_error: str | None = None


async def upsert_playback_normalization_job(
    db: AsyncSession | None,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
) -> PlaybackNormalizationJob | None:
    if db is None or media_revision_id is None:
        return None
    require_database_context(
        db,
        allowed_context_kinds=frozenset({"request", "worker"}),
        workspace_id=workspace_id,
    )
    revision = await db.get(MediaRevision, media_revision_id)
    if (
        revision is None
        or revision.workspace_id != workspace_id
        or revision.meeting_id != meeting_id
    ):
        raise ValueError("accepted media revision is unavailable")
    if revision.status != MediaRevisionStatus.ACCEPTED.value or not revision.manifest_sha256:
        raise ValueError("normalization requires an accepted media revision")
    meeting = await db.get(Meeting, meeting_id)
    workspace = await db.get(Workspace, workspace_id)
    if meeting is None or workspace is None or meeting.workspace_id != workspace_id:
        raise ValueError("normalization tenant identity is unavailable")

    fingerprint = source_fingerprint_sha256(
        media_revision_id=revision.id,
        source_kind=revision.source_kind,
        manifest_sha256=revision.manifest_sha256,
        track_sha256_by_role=revision.track_sha256_by_role or {},
        duration_seconds=revision.duration_seconds,
    )
    existing = await db.scalar(
        select(PlaybackNormalizationJob).where(
            PlaybackNormalizationJob.workspace_id == workspace_id,
            PlaybackNormalizationJob.media_revision_id == revision.id,
            PlaybackNormalizationJob.profile_version == CANONICAL_PROFILE_VERSION,
        )
    )
    if existing is not None:
        immutable_identity = (
            existing.meeting_id,
            existing.source_kind,
            existing.source_fingerprint_sha256,
            existing.workflow_id,
            existing.organization_id,
            existing.requested_by_user_id,
            existing.source_device_id,
        )
        expected_identity = (
            meeting_id,
            revision.source_kind,
            fingerprint,
            playback_normalization_workflow_id(revision.id),
            workspace.organization_id,
            meeting.created_by_user_id,
            meeting.device_id,
        )
        if immutable_identity != expected_identity:
            raise ValueError("normalization job identity conflict")
        return existing

    candidate = await db.scalar(
        select(TrackArtifact.id).where(
            TrackArtifact.workspace_id == workspace_id,
            TrackArtifact.meeting_id == meeting_id,
            TrackArtifact.media_revision_id == revision.id,
            TrackArtifact.track_role == TrackRole.PLAYBACK.value,
            TrackArtifact.status == "candidate",
        )
    )
    job = PlaybackNormalizationJob(
        organization_id=workspace.organization_id,
        workspace_id=workspace_id,
        requested_by_user_id=meeting.created_by_user_id,
        source_device_id=meeting.device_id,
        meeting_id=meeting_id,
        media_revision_id=revision.id,
        profile_version=CANONICAL_PROFILE_VERSION,
        validation_version=VALIDATION_VERSION,
        trigger_kind=TriggerKind.FINALIZE.value,
        priority_class=PriorityClass.NEW_INGEST.value,
        source_kind=revision.source_kind,
        source_fingerprint_sha256=fingerprint,
        planned_action=(
            PlannedAction.VALIDATE_CANDIDATE.value
            if candidate is not None
            else PlannedAction.NORMALIZE_SOURCE.value
        ),
        state=JobState.QUEUED.value,
        workflow_id=playback_normalization_workflow_id(revision.id),
    )
    db.add(job)
    await db.flush()
    _add_job_audit_event(
        db,
        job=job,
        event_type="playback_normalization_requested",
        metadata={
            "profile_version": job.profile_version,
            "state": job.state,
            "trigger_kind": job.trigger_kind,
            "planned_action": job.planned_action,
        },
        created_at=datetime.now(UTC),
    )
    return job


def _eligible_legacy_revisions_statement(
    *,
    workspace_id: UUID,
    cursor_created_at: datetime | None,
    cursor_media_revision_id: UUID | None,
):
    existing_profile_job = exists().where(
        PlaybackNormalizationJob.workspace_id == workspace_id,
        PlaybackNormalizationJob.media_revision_id == MediaRevision.id,
        PlaybackNormalizationJob.profile_version == CANONICAL_PROFILE_VERSION,
    )
    statement = (
        select(
            MediaRevision.id.label("media_revision_id"),
            MediaRevision.meeting_id,
            MediaRevision.created_at,
            MediaRevision.source_kind,
            MediaRevision.manifest_sha256,
            MediaRevision.track_sha256_by_role,
            MediaRevision.duration_seconds,
            Meeting.created_by_user_id,
            Meeting.device_id,
        )
        .join(Meeting, Meeting.id == MediaRevision.meeting_id)
        .where(
            MediaRevision.workspace_id == workspace_id,
            MediaRevision.status == MediaRevisionStatus.ACCEPTED.value,
            MediaRevision.manifest_sha256.is_not(None),
            MediaRevision.source_kind.in_(
                (
                    MediaRevisionSourceKind.INITIAL_RECORDING.value,
                    MediaRevisionSourceKind.MANUAL_UPLOAD.value,
                )
            ),
            or_(
                Meeting.deletion_state.is_(None),
                Meeting.deletion_state == DeletionState.NONE.value,
            ),
            Meeting.deleted_at.is_(None),
            ~existing_profile_job,
        )
    )
    if cursor_created_at is not None and cursor_media_revision_id is not None:
        statement = statement.where(
            or_(
                MediaRevision.created_at > cursor_created_at,
                and_(
                    MediaRevision.created_at == cursor_created_at,
                    MediaRevision.id > cursor_media_revision_id,
                ),
            )
        )
    return statement.order_by(MediaRevision.created_at, MediaRevision.id)


async def _load_or_create_backfill_run(
    db: AsyncSession,
    *,
    workspace_id: UUID,
) -> PlaybackBackfillRun:
    run = await db.scalar(
        select(PlaybackBackfillRun)
        .where(
            PlaybackBackfillRun.workspace_id == workspace_id,
            PlaybackBackfillRun.profile_version == CANONICAL_PROFILE_VERSION,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if run is not None:
        return run
    candidate = PlaybackBackfillRun(
        workspace_id=workspace_id,
        profile_version=CANONICAL_PROFILE_VERSION,
        state=BackfillState.INVENTORY_PENDING.value,
    )
    try:
        async with db.begin_nested():
            db.add(candidate)
            await db.flush()
        return candidate
    except IntegrityError:
        run = await db.scalar(
            select(PlaybackBackfillRun)
            .where(
                PlaybackBackfillRun.workspace_id == workspace_id,
                PlaybackBackfillRun.profile_version == CANONICAL_PROFILE_VERSION,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if run is None:
            raise
        return run


async def _load_backfill_artifact_facts(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    media_revision_ids: list[UUID],
) -> dict[UUID, list[_BackfillArtifactFacts]]:
    if not media_revision_ids:
        return {}
    rows = (
        await db.execute(
            select(
                TrackArtifact.media_revision_id,
                TrackArtifact.id,
                TrackArtifact.track_role,
                TrackArtifact.status,
                TrackArtifact.sha256,
                TrackArtifact.normalization_profile_version,
                TrackArtifact.validated_at,
                TrackArtifact.derivation_kind,
                TrackArtifact.source_fingerprint_sha256,
                TrackArtifact.validation_version,
            ).where(
                TrackArtifact.workspace_id == workspace_id,
                TrackArtifact.media_revision_id.in_(media_revision_ids),
                TrackArtifact.track_role.in_(
                    (
                        TrackRole.PLAYBACK.value,
                        TrackRole.MEDIA.value,
                        TrackRole.MICROPHONE.value,
                        TrackRole.SYSTEM.value,
                    )
                ),
            )
        )
    ).all()
    by_revision: dict[UUID, list[_BackfillArtifactFacts]] = defaultdict(list)
    for row in rows:
        if row.media_revision_id is None:
            continue
        by_revision[row.media_revision_id].append(
            _BackfillArtifactFacts(
                id=row.id,
                track_role=row.track_role,
                status=row.status,
                sha256=row.sha256,
                normalization_profile_version=row.normalization_profile_version,
                validated_at=row.validated_at,
                derivation_kind=row.derivation_kind,
                source_fingerprint_sha256=row.source_fingerprint_sha256,
                validation_version=row.validation_version,
            )
        )
    return dict(by_revision)


def _backfill_source_reason(
    *,
    source_kind: str,
    expected_sha256_by_role: dict[str, str],
    artifacts: list[_BackfillArtifactFacts],
) -> NormalizationReason | None:
    for role in authoritative_track_roles(source_kind):
        role_artifacts = [
            artifact
            for artifact in artifacts
            if artifact.track_role == role and artifact.status == "stored"
        ]
        if not role_artifacts:
            return NormalizationReason.SOURCE_MISSING
        if (
            len(role_artifacts) != 1
            or expected_sha256_by_role.get(role) is None
            or role_artifacts[0].sha256 != expected_sha256_by_role[role]
        ):
            return NormalizationReason.SOURCE_MISMATCH
    return None


def _plan_backfill_decision(
    *,
    source_kind: str,
    source_fingerprint: str,
    expected_sha256_by_role: dict[str, str],
    artifacts: list[_BackfillArtifactFacts],
) -> _BackfillDecision:
    canonical = [
        artifact
        for artifact in artifacts
        if artifact.track_role == TrackRole.PLAYBACK.value
        and artifact.status == "stored"
        and artifact.normalization_profile_version == CANONICAL_PROFILE_VERSION
        and artifact.validated_at is not None
        and artifact.derivation_kind is not None
        and artifact.source_fingerprint_sha256 == source_fingerprint
        and artifact.validation_version == VALIDATION_VERSION
    ]
    if len(canonical) == 1:
        return _BackfillDecision(
            planned_action=PlannedAction.PRESERVE_VALID,
            state=JobState.READY,
            canonical_track_artifact_id=canonical[0].id,
        )

    legacy_candidates = [
        artifact
        for artifact in artifacts
        if artifact.track_role == TrackRole.PLAYBACK.value
        and artifact.status in {"candidate", "stored"}
        and artifact not in canonical
    ]
    if len(legacy_candidates) == 1:
        return _BackfillDecision(
            planned_action=PlannedAction.VALIDATE_CANDIDATE,
            state=JobState.QUEUED,
        )

    source_reason = _backfill_source_reason(
        source_kind=source_kind,
        expected_sha256_by_role=expected_sha256_by_role,
        artifacts=artifacts,
    )
    if source_reason is not None:
        return _BackfillDecision(
            planned_action=PlannedAction.UNAVAILABLE_SOURCE,
            state=JobState.TERMINAL,
            reason_code=source_reason,
        )
    return _BackfillDecision(
        planned_action=PlannedAction.NORMALIZE_SOURCE,
        state=JobState.QUEUED,
    )


def _add_job_audit_event(
    db: AsyncSession,
    *,
    job: PlaybackNormalizationJob,
    event_type: str,
    metadata: dict[str, object],
    created_at: datetime,
) -> None:
    add_normalization_audit_event(
        db,
        workspace_id=job.workspace_id,
        meeting_id=job.meeting_id,
        media_revision_id=job.media_revision_id,
        actor_user_id=job.requested_by_user_id,
        device_id=job.source_device_id,
        event_type=event_type,
        metadata=metadata,
        created_at=created_at,
    )


async def _refresh_backfill_run_outcomes(
    db: AsyncSession,
    *,
    run: PlaybackBackfillRun,
    now: datetime,
) -> None:
    state_counts = {
        state: int(count)
        for state, count in (
            await db.execute(
                select(PlaybackNormalizationJob.state, func.count())
                .where(PlaybackNormalizationJob.backfill_run_id == run.id)
                .group_by(PlaybackNormalizationJob.state)
            )
        ).all()
    }
    run.ready_count = max(run.ready_count, state_counts.get(JobState.READY.value, 0))
    run.terminal_count = max(run.terminal_count, state_counts.get(JobState.TERMINAL.value, 0))
    run.cancelled_count = max(run.cancelled_count, state_counts.get(JobState.CANCELLED.value, 0))
    unverified_ready = int(
        await db.scalar(
            select(func.count())
            .select_from(PlaybackNormalizationJob)
            .where(
                PlaybackNormalizationJob.backfill_run_id == run.id,
                PlaybackNormalizationJob.state == JobState.READY.value,
                PlaybackNormalizationJob.last_heartbeat_at.is_(None),
            )
        )
        or 0
    )
    outstanding = unverified_ready + sum(
        state_counts.get(state.value, 0)
        for state in (
            JobState.QUEUED,
            JobState.RUNNING,
            JobState.PUBLISHING,
            JobState.RETRY_WAIT,
        )
    )
    current = BackfillState(run.state)
    if current is BackfillState.INVENTORY_COMPLETE:
        ensure_backfill_transition(current, BackfillState.DISPATCHING)
        run.state = BackfillState.DISPATCHING.value
        current = BackfillState.DISPATCHING
    if current is BackfillState.DISPATCHING and outstanding == 0:
        ensure_backfill_transition(current, BackfillState.COMPLETE)
        run.state = BackfillState.COMPLETE.value
        run.completed_at = now
        add_normalization_audit_event(
            db,
            workspace_id=run.workspace_id,
            event_type="playback_backfill_completed",
            metadata={
                "profile_version": run.profile_version,
                "state": run.state,
                "evaluated_count": run.evaluated_count,
                "ready_count": run.ready_count,
                "terminal_count": run.terminal_count,
                "cancelled_count": run.cancelled_count,
                "completed_at": now,
            },
            created_at=now,
        )


async def inventory_playback_backfill_page(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    page_size: int,
    now: datetime | None = None,
) -> BackfillInventoryPageResult:
    """Plan one durable legacy page under an already-applied exact worker tenant scope."""

    require_database_context(
        db,
        allowed_context_kinds=frozenset({"worker"}),
        workspace_id=workspace_id,
    )

    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    context_settings = db.info.get("tenant_context", {})
    context_workspace_id = context_settings.get("app.workspace_id")
    if context_workspace_id is not None and UUID(str(context_workspace_id)) != workspace_id:
        raise ValueError("backfill workspace context mismatch")
    context_organization_id = context_settings.get("app.organization_id")
    if context_organization_id is not None:
        organization_id = UUID(str(context_organization_id))
    else:
        workspace = await db.get(Workspace, workspace_id)
        if workspace is None:
            raise ValueError("backfill workspace is unavailable")
        organization_id = workspace.organization_id
    run = await _load_or_create_backfill_run(db, workspace_id=workspace_id)
    await _refresh_backfill_run_outcomes(db, run=run, now=current_time)

    if run.state == BackfillState.COMPLETE.value:
        newer = await db.scalar(
            _eligible_legacy_revisions_statement(
                workspace_id=workspace_id,
                cursor_created_at=run.cursor_created_at,
                cursor_media_revision_id=run.cursor_media_revision_id,
            )
            .with_only_columns(MediaRevision.id)
            .limit(1)
        )
        if newer is None:
            await db.commit()
            return BackfillInventoryPageResult(
                run_id=run.id,
                state=run.state,
                reused_completed=True,
            )
        ensure_backfill_transition(
            BackfillState.COMPLETE,
            BackfillState.INVENTORY_RUNNING,
            newer_watermark=True,
        )
        run.state = BackfillState.INVENTORY_RUNNING.value
        run.inventory_started_at = current_time
        run.inventory_completed_at = None
        run.completed_at = None
        run.safe_block_reason = None
    elif run.state == BackfillState.BLOCKED.value:
        ensure_backfill_transition(BackfillState.BLOCKED, BackfillState.INVENTORY_PENDING)
        run.state = BackfillState.INVENTORY_PENDING.value
        run.safe_block_reason = None

    if run.state in {
        BackfillState.INVENTORY_COMPLETE.value,
        BackfillState.DISPATCHING.value,
    }:
        await db.commit()
        return BackfillInventoryPageResult(run_id=run.id, state=run.state)
    if run.state == BackfillState.INVENTORY_PENDING.value:
        ensure_backfill_transition(
            BackfillState.INVENTORY_PENDING,
            BackfillState.INVENTORY_RUNNING,
        )
        run.state = BackfillState.INVENTORY_RUNNING.value
        run.inventory_started_at = current_time

    rows = (
        await db.execute(
            _eligible_legacy_revisions_statement(
                workspace_id=workspace_id,
                cursor_created_at=run.cursor_created_at,
                cursor_media_revision_id=run.cursor_media_revision_id,
            ).limit(page_size + 1)
        )
    ).all()
    page = rows[:page_size]
    has_more = len(rows) > page_size
    artifact_facts = await _load_backfill_artifact_facts(
        db,
        workspace_id=workspace_id,
        media_revision_ids=[row.media_revision_id for row in page],
    )

    for row in page:
        locked_meeting = await db.scalar(
            select(Meeting)
            .where(Meeting.workspace_id == workspace_id, Meeting.id == row.meeting_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if locked_meeting is None or meeting_is_deleted_or_deleting(locked_meeting):
            continue
        locked_revision = await db.scalar(
            select(MediaRevision)
            .where(
                MediaRevision.workspace_id == workspace_id,
                MediaRevision.id == row.media_revision_id,
                MediaRevision.meeting_id == row.meeting_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if locked_revision is None or locked_revision.status != MediaRevisionStatus.ACCEPTED.value:
            continue
        existing_job = await db.scalar(
            select(PlaybackNormalizationJob)
            .where(
                PlaybackNormalizationJob.workspace_id == workspace_id,
                PlaybackNormalizationJob.media_revision_id == row.media_revision_id,
                PlaybackNormalizationJob.profile_version == CANONICAL_PROFILE_VERSION,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if existing_job is not None:
            # The page query is intentionally a cheap snapshot. A finalize or
            # another backfill worker may have created the unique profile job
            # before this row acquired its Meeting fence; treat that winner as
            # already inventoried instead of retrying the whole page.
            continue
        manifest_sha256 = str(row.manifest_sha256)
        expected_sha256_by_role = dict(row.track_sha256_by_role or {})
        fingerprint = source_fingerprint_sha256(
            media_revision_id=row.media_revision_id,
            source_kind=row.source_kind,
            manifest_sha256=manifest_sha256,
            track_sha256_by_role=expected_sha256_by_role,
            duration_seconds=row.duration_seconds,
        )
        decision = _plan_backfill_decision(
            source_kind=row.source_kind,
            source_fingerprint=fingerprint,
            expected_sha256_by_role=expected_sha256_by_role,
            artifacts=artifact_facts.get(row.media_revision_id, []),
        )
        job = PlaybackNormalizationJob(
            organization_id=organization_id,
            workspace_id=workspace_id,
            requested_by_user_id=row.created_by_user_id,
            source_device_id=row.device_id,
            meeting_id=row.meeting_id,
            media_revision_id=row.media_revision_id,
            profile_version=CANONICAL_PROFILE_VERSION,
            validation_version=VALIDATION_VERSION,
            trigger_kind=TriggerKind.LEGACY_BACKFILL.value,
            priority_class=PriorityClass.LEGACY_BACKFILL.value,
            source_kind=row.source_kind,
            source_fingerprint_sha256=fingerprint,
            backfill_run_id=run.id,
            planned_action=decision.planned_action.value,
            state=decision.state.value,
            reason_code=(decision.reason_code.value if decision.reason_code else None),
            workflow_id=playback_normalization_workflow_id(row.media_revision_id),
            canonical_track_artifact_id=decision.canonical_track_artifact_id,
            ready_at=current_time if decision.state is JobState.READY else None,
            terminal_at=current_time if decision.state is JobState.TERMINAL else None,
        )
        db.add(job)
        if decision.reason_code is not None:
            await db.flush()
            from twobrain_rec_server.support.incidents import (
                record_impossible_legacy_normalization_incident,
            )

            await record_impossible_legacy_normalization_incident(
                db=db,
                job=job,
                reason_code=decision.reason_code,
                recorded_at=current_time,
            )
        metadata: dict[str, object] = {
            "profile_version": CANONICAL_PROFILE_VERSION,
            "state": decision.state.value,
            "trigger_kind": TriggerKind.LEGACY_BACKFILL.value,
            "planned_action": decision.planned_action.value,
        }
        if decision.reason_code is not None:
            metadata["reason_code"] = decision.reason_code.value
        _add_job_audit_event(
            db,
            job=job,
            event_type="playback_backfill_inventory_planned",
            metadata=metadata,
            created_at=current_time,
        )
        _add_job_audit_event(
            db,
            job=job,
            event_type="playback_normalization_requested",
            metadata={
                "profile_version": job.profile_version,
                "state": job.state,
                "trigger_kind": job.trigger_kind,
                "planned_action": job.planned_action,
            },
            created_at=current_time,
        )
        if decision.state in {JobState.READY, JobState.TERMINAL}:
            skipped_metadata = {
                "profile_version": job.profile_version,
                "state": job.state,
                "trigger_kind": job.trigger_kind,
                "planned_action": job.planned_action,
            }
            if decision.reason_code is not None:
                skipped_metadata["reason_code"] = decision.reason_code.value
            _add_job_audit_event(
                db,
                job=job,
                event_type="playback_normalization_skipped",
                metadata=skipped_metadata,
                created_at=current_time,
            )
        if decision.reason_code is not None:
            _add_job_audit_event(
                db,
                job=job,
                event_type="playback_normalization_legacy_source_unavailable",
                metadata={
                    "reason_code": decision.reason_code.value,
                    "trigger_kind": job.trigger_kind,
                    "planned_action": job.planned_action,
                },
                created_at=current_time,
            )
        run.evaluated_count += 1
        setattr(
            run,
            f"{decision.planned_action.value}_count",
            getattr(run, f"{decision.planned_action.value}_count") + 1,
        )

    if page:
        run.cursor_created_at = page[-1].created_at
        run.cursor_media_revision_id = page[-1].media_revision_id
    inventory_completed = not has_more
    if inventory_completed:
        ensure_backfill_transition(
            BackfillState.INVENTORY_RUNNING,
            BackfillState.INVENTORY_COMPLETE,
        )
        run.state = BackfillState.INVENTORY_COMPLETE.value
        run.inventory_completed_at = current_time
        add_normalization_audit_event(
            db,
            workspace_id=workspace_id,
            event_type="playback_backfill_inventory_completed",
            metadata={
                "profile_version": run.profile_version,
                "state": run.state,
                "evaluated_count": run.evaluated_count,
                "preserve_valid_count": run.preserve_valid_count,
                "validate_candidate_count": run.validate_candidate_count,
                "normalize_source_count": run.normalize_source_count,
                "unavailable_source_count": run.unavailable_source_count,
                "inventory_started_at": _aware_utc(run.inventory_started_at),
                "inventory_completed_at": current_time,
            },
            created_at=current_time,
        )
        await db.flush()
        await _refresh_backfill_run_outcomes(db, run=run, now=current_time)
    await db.commit()
    return BackfillInventoryPageResult(
        run_id=run.id,
        state=run.state,
        evaluated=len(page),
        inventory_completed=inventory_completed,
    )


async def mark_playback_backfill_blocked(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    reason_code: NormalizationReason = NormalizationReason.DATABASE_UNAVAILABLE,
    now: datetime | None = None,
) -> UUID:
    """Persist a safe, automatically recoverable workspace inventory blocker."""

    require_database_context(
        db,
        allowed_context_kinds=frozenset({"worker"}),
        workspace_id=workspace_id,
    )

    current_time = now or datetime.now(UTC)
    run = await _load_or_create_backfill_run(db, workspace_id=workspace_id)
    current = BackfillState(run.state)
    if current is not BackfillState.COMPLETE and current is not BackfillState.BLOCKED:
        ensure_backfill_transition(current, BackfillState.BLOCKED)
        run.state = BackfillState.BLOCKED.value
        run.safe_block_reason = reason_code.value
        run.inventory_completed_at = None
        run.completed_at = None
        add_normalization_audit_event(
            db,
            workspace_id=workspace_id,
            event_type="playback_normalization_failed",
            metadata={"reason_code": reason_code.value},
            created_at=current_time,
        )
    await db.commit()
    return run.id


async def _download_verified_artifact(
    storage: object,
    artifact: TrackArtifact,
    destination_path: Path,
    *,
    max_bytes: int,
) -> None:
    if artifact.byte_length == 0:
        raise MediaPolicyError("empty_source")
    verified_async = getattr(storage, "download_verified_to_path_async", None)
    if verified_async is not None:
        await verified_async(
            artifact.storage_object_key,
            destination_path,
            expected_length=artifact.byte_length,
            expected_sha256=artifact.sha256,
            max_bytes=max_bytes,
        )
        return
    verified = getattr(storage, "download_verified_to_path", None)
    if verified is not None:
        await to_thread.run_sync(
            lambda: verified(
                artifact.storage_object_key,
                destination_path,
                expected_length=artifact.byte_length,
                expected_sha256=artifact.sha256,
                max_bytes=max_bytes,
            )
        )
        return
    download_async = getattr(storage, "download_to_path_async", None)
    if download_async is not None:
        try:
            await download_async(artifact.storage_object_key, destination_path)
        except KeyError as exc:
            raise RuntimeError("source_missing") from exc
    else:
        download = getattr(storage, "download_to_path", None)
        if download is None:
            raise RuntimeError("storage_unavailable")
        try:
            await to_thread.run_sync(
                lambda: download(artifact.storage_object_key, destination_path)
            )
        except KeyError as exc:
            raise RuntimeError("source_missing") from exc
    digest = await _hash_regular_file(destination_path, max_bytes=max_bytes)
    if digest.byte_length != artifact.byte_length or digest.sha256_hex != artifact.sha256:
        destination_path.unlink(missing_ok=True)
        raise RuntimeError("source_mismatch")


async def _upload_verified_output(
    storage: object,
    *,
    object_key: str,
    source_path: Path,
    output: NormalizedOutput,
) -> None:
    verified_async = getattr(storage, "upload_verified_path_async", None)
    if verified_async is not None:
        await verified_async(
            object_key,
            source_path,
            expected_length=output.output_byte_length,
            expected_sha256=output.output_sha256,
            max_bytes=MAX_OUTPUT_BYTES,
        )
        return
    verified = getattr(storage, "upload_verified_path", None)
    if verified is not None:
        await to_thread.run_sync(
            lambda: verified(
                object_key,
                source_path,
                expected_length=output.output_byte_length,
                expected_sha256=output.output_sha256,
                max_bytes=MAX_OUTPUT_BYTES,
            )
        )
        return
    put_stream_async = getattr(storage, "put_stream_async", None)
    if put_stream_async is not None:
        with source_path.open("rb") as stream:
            await put_stream_async(object_key, stream, output.output_byte_length)
        return
    put_stream = getattr(storage, "put_stream", None)
    if put_stream is None:
        raise RuntimeError("storage_unavailable")
    with source_path.open("rb") as stream:
        await to_thread.run_sync(lambda: put_stream(object_key, stream, output.output_byte_length))


async def _delete_storage_object(storage: object, object_key: str) -> None:
    delete_async = getattr(storage, "delete_object_async", None)
    if delete_async is not None:
        await delete_async(object_key)
        return
    delete = getattr(storage, "delete_object", None)
    if delete is not None:
        await to_thread.run_sync(lambda: delete(object_key))
        return
    raise RuntimeError("storage_unavailable")


async def _reserve_playback_storage(
    db: AsyncSession,
    *,
    job: PlaybackNormalizationJob,
    attempt: PlaybackNormalizationAttempt,
    declared_bytes: int,
    now: datetime,
) -> object | None:
    if not await archive_audio_for_revision(
        db,
        workspace_id=job.workspace_id,
        meeting_id=job.meeting_id,
        media_revision_id=job.media_revision_id,
    ):
        return None
    await lock_storage_workspace(db, job.workspace_id)
    subscription = await db.scalar(
        select(WorkspaceSubscription).where(
            WorkspaceSubscription.workspace_id == job.workspace_id
        )
    )
    effective_plan = (
        effective_plan_code(
            plan_code=subscription.plan_code,
            state=subscription.state,
            now=now,
            paid_through=subscription.paid_through,
            trial_ends_at=subscription.trial_ends_at,
        )
        if subscription is not None
        else "free"
    )
    return await reserve_storage(
        db,
        workspace_id=job.workspace_id,
        reservation_key=f"normalization:{attempt.id}",
        declared_bytes=declared_bytes,
        capacity_bytes=(
            subscription.capacity_bytes
            if subscription is not None and effective_plan in {"trial", "personal"}
            else FREE_STORAGE_BYTES
        ),
        now=now,
    )


async def _storage_object_exists(storage: object, object_key: str) -> bool | None:
    exists_async = getattr(storage, "object_exists_async", None)
    if exists_async is not None:
        return bool(await exists_async(object_key))
    exists = getattr(storage, "object_exists", None)
    if exists is not None:
        return bool(await to_thread.run_sync(lambda: exists(object_key)))
    return None


async def _ensure_normalized_output_matches_file(
    output_path: Path,
    output: NormalizedOutput,
) -> None:
    digest = await _hash_regular_file(output_path, max_bytes=MAX_OUTPUT_BYTES)
    if (
        digest.byte_length != output.output_byte_length
        or digest.sha256_hex != output.output_sha256
        or output.derivation_kind not in {kind.value for kind in DerivationKind}
        or output.source_stream_count <= 0
        or output.source_audio_stream_count <= 0
        or output.source_audio_stream_count > output.source_stream_count
        or output.source_duration_ms <= 0
        or output.output_duration_ms <= 0
        or output.output_audio_bit_rate <= 0
        or output.output_sample_rate_hz != 48_000
        or output.output_channel_count != 1
        or not output.moov_before_mdat
        or output.fragmented
        or not output.full_decode_passed
    ):
        raise RuntimeError("generated_output_invalid")


async def _inspect_bmff(path: Path) -> BMFFLayout:
    return await to_thread.run_sync(inspect_bmff, path)


async def _hash_regular_file(path: Path, *, max_bytes: int) -> FileDigest:
    return await to_thread.run_sync(lambda: hash_regular_file(path, max_bytes=max_bytes))


def _aware_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def normalization_reason_from_exception(exc: BaseException) -> NormalizationReason:
    if isinstance(exc, NormalizationExecutionFailure):
        return exc.reason_code
    reason_code = getattr(exc, "reason_code", None)
    if isinstance(reason_code, str):
        try:
            return NormalizationReason(reason_code)
        except ValueError:
            pass
    if isinstance(exc, CancelledError):
        return NormalizationReason.WORKER_INTERRUPTED
    if isinstance(exc, SQLAlchemyError):
        return NormalizationReason.DATABASE_UNAVAILABLE
    if isinstance(exc, StorageAdmissionError):
        if str(exc) == "storage capacity exceeded":
            return NormalizationReason.STORAGE_CAPACITY_EXCEEDED
        return NormalizationReason.DEPENDENCY_UNAVAILABLE
    if isinstance(exc, TimeoutError):
        return NormalizationReason.NORMALIZATION_TIMEOUT
    if isinstance(exc, OSError):
        return NormalizationReason.TEMPORARY_STORAGE_UNAVAILABLE
    if isinstance(exc, RuntimeError):
        try:
            return NormalizationReason(str(exc))
        except ValueError:
            pass
    return NormalizationReason.DEPENDENCY_UNAVAILABLE


async def record_normalization_failure(
    db: AsyncSession,
    *,
    job_id: UUID,
    reason_code: NormalizationReason,
    failed_at: datetime | None = None,
) -> NormalizationFailureResult:
    """Persist failure truth before Temporal decides whether to retry the activity."""

    require_database_context(db, allowed_context_kinds=frozenset({"worker"}))

    now = failed_at or datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("failed_at must be timezone-aware")
    job = await db.scalar(
        select(PlaybackNormalizationJob)
        .where(PlaybackNormalizationJob.id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if job is None:
        raise ValueError("normalization job not found")
    current_state = JobState(job.state)
    if current_state in {JobState.READY, JobState.TERMINAL, JobState.CANCELLED}:
        return NormalizationFailureResult(
            job_id=job.id,
            state=current_state,
            reason_code=reason_code,
            next_attempt_at=job.next_attempt_at,
            retry_cycle_count=job.retry_cycle_count,
            should_temporal_retry=False,
            cycle_exhausted=False,
        )

    attempt = await db.scalar(
        select(PlaybackNormalizationAttempt)
        .where(
            PlaybackNormalizationAttempt.job_id == job.id,
            PlaybackNormalizationAttempt.state.in_(
                [
                    AttemptState.LOCAL_PREPARING.value,
                    AttemptState.UPLOADED.value,
                ]
            ),
        )
        .order_by(PlaybackNormalizationAttempt.attempt_number.desc())
        .limit(1)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if attempt is not None:
        ensure_attempt_transition(AttemptState(attempt.state), AttemptState.CLEANUP_PENDING)
        attempt.state = AttemptState.CLEANUP_PENDING.value
        attempt.cleanup_reason = reason_code.value
        reservation = await db.scalar(
            select(StorageReservation)
            .where(
                StorageReservation.workspace_id == job.workspace_id,
                StorageReservation.idempotency_key == f"normalization:{attempt.id}",
            )
            .with_for_update()
        )
        if reservation is not None:
            await release_storage_reservation(db, reservation_id=reservation.id)
    elif (
        current_state is JobState.RETRY_WAIT
        and job.reason_code is not None
        and job.next_attempt_at is not None
    ):
        stored_reason = NormalizationReason(job.reason_code)
        return NormalizationFailureResult(
            job_id=job.id,
            state=JobState.RETRY_WAIT,
            reason_code=stored_reason,
            next_attempt_at=job.next_attempt_at,
            retry_cycle_count=job.retry_cycle_count,
            should_temporal_retry=job.cycle_attempt_count < 4,
            cycle_exhausted=job.cycle_attempt_count >= 4,
        )

    classification = reason_class(reason_code)
    next_attempt_at: datetime | None = None
    should_temporal_retry = False
    cycle_exhausted = False
    if classification in {
        ReasonClass.PERMANENT_SOURCE,
        ReasonClass.POLICY_BLOCK,
    }:
        ensure_job_transition(current_state, JobState.TERMINAL, reason_code=reason_code)
        job.state = JobState.TERMINAL.value
        job.reason_code = reason_code.value
        job.terminal_at = now
    elif classification is ReasonClass.LIFECYCLE:
        ensure_job_transition(current_state, JobState.CANCELLED, reason_code=reason_code)
        job.state = JobState.CANCELLED.value
        job.reason_code = reason_code.value
        job.cancelled_at = now
    else:
        failed_attempt_in_cycle = max(1, job.cycle_attempt_count)
        if failed_attempt_in_cycle > 4:
            raise RuntimeError("normalization retry counter is invalid")
        schedule = retry_failure_schedule(
            now,
            failed_attempt_in_cycle=failed_attempt_in_cycle,
            completed_cycle_count=job.retry_cycle_count,
        )
        ensure_job_transition(current_state, JobState.RETRY_WAIT, reason_code=reason_code)
        job.state = JobState.RETRY_WAIT.value
        job.reason_code = reason_code.value
        job.next_attempt_at = schedule.next_attempt_at
        job.priority_class = PriorityClass.DUE_RETRY.value
        job.retry_cycle_count = schedule.completed_cycle_count
        next_attempt_at = schedule.next_attempt_at
        should_temporal_retry = schedule.temporal_retry
        cycle_exhausted = schedule.cycle_exhausted
        if cycle_exhausted:
            job.workflow_run_id = None
            from twobrain_rec_server.support.incidents import (
                record_playback_normalization_incident,
            )

            await record_playback_normalization_incident(
                db=db,
                job=job,
                reason_code=reason_code,
                cooldown_cycle=job.retry_cycle_count,
                recorded_at=now,
            )
            _add_job_audit_event(
                db,
                job=job,
                event_type="playback_normalization_retry_cycle_exhausted",
                metadata={
                    "reason_code": reason_code.value,
                    "retry_cycle_count": job.retry_cycle_count,
                },
                created_at=now,
            )

    if classification is not ReasonClass.AUTOMATIC_RETRY:
        job.next_attempt_at = None
        job.workflow_run_id = None
    job.lease_owner_sha256 = None
    job.lease_expires_at = None
    job.last_heartbeat_at = now
    _add_job_audit_event(
        db,
        job=job,
        event_type=(
            "playback_normalization_cancelled"
            if classification is ReasonClass.LIFECYCLE
            else "playback_normalization_failed"
        ),
        metadata={"reason_code": reason_code.value, "state": job.state},
        created_at=now,
    )
    await db.commit()
    return NormalizationFailureResult(
        job_id=job.id,
        state=JobState(job.state),
        reason_code=reason_code,
        next_attempt_at=next_attempt_at,
        retry_cycle_count=job.retry_cycle_count,
        should_temporal_retry=should_temporal_retry,
        cycle_exhausted=cycle_exhausted,
    )


async def activate_due_normalization_retry(
    db: AsyncSession,
    *,
    job_id: UUID,
    now: datetime | None = None,
    recover_worker_interruption: bool = False,
) -> bool:
    require_database_context(
        db,
        allowed_context_kinds=frozenset({"request", "worker"}),
    )
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    job = await db.scalar(
        select(PlaybackNormalizationJob)
        .where(PlaybackNormalizationJob.id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if job is None or job.state != JobState.RETRY_WAIT.value or job.next_attempt_at is None:
        return False
    if _aware_utc(job.next_attempt_at) > current_time and not (
        recover_worker_interruption
        and job.reason_code == NormalizationReason.WORKER_INTERRUPTED.value
    ):
        return False
    if job.cycle_attempt_count >= 4:
        job.cycle_attempt_count = 0
        job.workflow_run_id = None
    ensure_job_transition(JobState.RETRY_WAIT, JobState.QUEUED)
    job.state = JobState.QUEUED.value
    job.reason_code = None
    job.next_attempt_at = None
    job.trigger_kind = TriggerKind.RECONCILE.value
    job.priority_class = PriorityClass.DUE_RETRY.value
    job.lease_owner_sha256 = None
    job.lease_expires_at = None
    _add_job_audit_event(
        db,
        job=job,
        event_type="playback_normalization_retried",
        metadata={
            "state": job.state,
            "attempt_count": job.attempt_count,
            "retry_cycle_count": job.retry_cycle_count,
        },
        created_at=current_time,
    )
    await db.commit()
    return True


async def request_normalization_retry_now(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
    now: datetime | None = None,
) -> NormalizationManualRetryResult:
    """Make one scheduled normalization retry due without creating parallel work."""

    if media_revision_id is None:
        return NormalizationManualRetryResult(result="not_available")
    require_database_context(
        db,
        allowed_context_kinds=frozenset({"request", "worker"}),
        workspace_id=workspace_id,
    )
    current_time = now or datetime.now(UTC)
    meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.id == meeting_id, Meeting.workspace_id == workspace_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        return NormalizationManualRetryResult(result="closed")
    current_revision_id = await db.scalar(
        select(MediaRevision.id)
        .where(
            MediaRevision.workspace_id == workspace_id,
            MediaRevision.meeting_id == meeting_id,
            MediaRevision.status == MediaRevisionStatus.ACCEPTED.value,
        )
        .order_by(MediaRevision.revision_number.desc())
    )
    if current_revision_id != media_revision_id:
        return NormalizationManualRetryResult(result="closed")
    job = await db.scalar(
        select(PlaybackNormalizationJob)
        .where(
            PlaybackNormalizationJob.workspace_id == workspace_id,
            PlaybackNormalizationJob.meeting_id == meeting_id,
            PlaybackNormalizationJob.media_revision_id == media_revision_id,
            PlaybackNormalizationJob.profile_version == CANONICAL_PROFILE_VERSION,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if job is None:
        return NormalizationManualRetryResult(result="not_available")
    if job.state in {
        JobState.QUEUED.value,
        JobState.RUNNING.value,
        JobState.PUBLISHING.value,
    }:
        return NormalizationManualRetryResult(
            result="already_in_flight",
            job_id=job.id,
            media_revision_id=job.media_revision_id,
        )
    if (
        job.state != JobState.RETRY_WAIT.value
        or job.next_attempt_at is None
        or job.reason_code is None
    ):
        return NormalizationManualRetryResult(
            result="not_retryable",
            job_id=job.id,
            media_revision_id=job.media_revision_id,
        )
    job.next_attempt_at = current_time
    job.priority_class = PriorityClass.DUE_RETRY.value
    job.trigger_kind = TriggerKind.RECONCILE.value
    _add_job_audit_event(
        db,
        job=job,
        event_type="playback_normalization_manual_retry_requested",
        metadata={
            "state": job.state,
            "reason_code": job.reason_code,
        },
        created_at=current_time,
    )
    await db.commit()
    return NormalizationManualRetryResult(
        result="accepted",
        job_id=job.id,
        media_revision_id=job.media_revision_id,
    )


async def cleanup_unpublished_normalization_attempts(
    db: AsyncSession,
    *,
    storage: object,
    job_id: UUID,
) -> int:
    require_database_context(db, allowed_context_kinds=frozenset({"worker"}))
    attempt_ids = list(
        await db.scalars(
            select(PlaybackNormalizationAttempt.id)
            .where(
                PlaybackNormalizationAttempt.job_id == job_id,
                PlaybackNormalizationAttempt.state.in_(
                    [
                        AttemptState.LOCAL_PREPARING.value,
                        AttemptState.UPLOADED.value,
                        AttemptState.CLEANUP_PENDING.value,
                        AttemptState.PURGED.value,
                    ]
                ),
                or_(
                    PlaybackNormalizationAttempt.state != AttemptState.PURGED.value,
                    PlaybackNormalizationAttempt.cleaned_at.is_(None),
                ),
            )
            .order_by(PlaybackNormalizationAttempt.updated_at, PlaybackNormalizationAttempt.id)
        )
    )
    cleaned = 0
    for attempt_id in attempt_ids:
        cleaned += int(
            await cleanup_normalization_attempt(
                db,
                storage=storage,
                attempt_id=attempt_id,
                cleanup_reason="automatic_recovery",
            )
        )
    return cleaned


async def cleanup_normalization_attempt(
    db: AsyncSession,
    *,
    storage: object,
    attempt_id: UUID,
    cleanup_reason: str,
    now: datetime | None = None,
    late_object_arrival: bool = False,
) -> bool:
    """Delete one immutable attempt object and persist only truthful cleanup."""

    require_database_context(db, allowed_context_kinds=frozenset({"worker"}))
    current_time = now or datetime.now(UTC)
    attempt = await db.scalar(
        select(PlaybackNormalizationAttempt)
        .where(PlaybackNormalizationAttempt.id == attempt_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if attempt is None or attempt.state == AttemptState.PUBLISHED.value:
        return False
    current_state = AttemptState(attempt.state)
    if current_state is AttemptState.CLEANED and not late_object_arrival:
        return False
    if current_state not in {
        AttemptState.LOCAL_PREPARING,
        AttemptState.UPLOADED,
        AttemptState.CLEANUP_PENDING,
        AttemptState.CLEANED,
        AttemptState.PURGED,
    }:
        return False
    entered_cleanup = current_state not in {
        AttemptState.CLEANUP_PENDING,
        AttemptState.PURGED,
    }
    if current_state is AttemptState.PURGED and late_object_arrival:
        attempt.cleaned_at = None
    if current_state not in {AttemptState.CLEANUP_PENDING, AttemptState.PURGED}:
        ensure_attempt_transition(current_state, AttemptState.CLEANUP_PENDING)
        attempt.state = AttemptState.CLEANUP_PENDING.value
    attempt.cleanup_reason = attempt.cleanup_reason or cleanup_reason
    object_key = attempt.storage_object_key
    workspace_id = attempt.workspace_id
    meeting_id = attempt.meeting_id
    await db.commit()

    try:
        object_existed = await _storage_object_exists(storage, object_key)
        await _delete_storage_object(storage, object_key)
    except Exception:
        await db.rollback()
        await persist_orphan_cleanup_intents(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            object_keys=(object_key,),
            reason="normalization_cleanup_failed",
        )
        pending = await db.scalar(
            select(PlaybackNormalizationAttempt)
            .where(PlaybackNormalizationAttempt.id == attempt_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if pending is not None and pending.state in {
            AttemptState.CLEANUP_PENDING.value,
            AttemptState.PURGED.value,
        }:
            pending.updated_at = current_time
            if entered_cleanup or late_object_arrival:
                add_normalization_audit_event(
                    db,
                    workspace_id=pending.workspace_id,
                    meeting_id=pending.meeting_id,
                    media_revision_id=pending.media_revision_id,
                    event_type="playback_normalization_temp_cleaned",
                    metadata={"cleanup_result": "deferred_retry"},
                    created_at=current_time,
                )
            await db.commit()
        return False

    refreshed = await db.scalar(
        select(PlaybackNormalizationAttempt)
        .where(PlaybackNormalizationAttempt.id == attempt_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if refreshed is None or refreshed.state == AttemptState.PUBLISHED.value:
        return False
    if refreshed.state == AttemptState.PURGED.value:
        if object_existed is False and refreshed.cleaned_at is None:
            # ponytail: keep one durable round-robin tombstone per ambiguous
            # deletion. If that queue becomes operationally material, replace
            # the polling row with an object-store conditional-write tombstone;
            # a time cutoff would reintroduce the late-PUT data-loss race.
            refreshed.updated_at = current_time
            await db.commit()
            return False
        refreshed.cleaned_at = refreshed.cleaned_at or current_time
    else:
        ensure_attempt_transition(AttemptState(refreshed.state), AttemptState.CLEANED)
        refreshed.state = AttemptState.CLEANED.value
        refreshed.cleaned_at = current_time
    refreshed.updated_at = current_time
    add_normalization_audit_event(
        db,
        workspace_id=refreshed.workspace_id,
        meeting_id=refreshed.meeting_id,
        media_revision_id=refreshed.media_revision_id,
        event_type="playback_normalization_temp_cleaned",
        metadata={
            "cleanup_result": "already_missing" if object_existed is False else "deleted"
        },
        created_at=current_time,
    )
    await db.commit()
    return True


async def recover_expired_normalization_job(
    db: AsyncSession,
    *,
    storage: object,
    job_id: UUID,
    now: datetime | None = None,
) -> NormalizationFailureResult | None:
    require_database_context(db, allowed_context_kinds=frozenset({"worker"}))
    current_time = now or datetime.now(UTC)
    job = await db.scalar(
        select(PlaybackNormalizationJob)
        .where(PlaybackNormalizationJob.id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        job is None
        or job.state not in {JobState.RUNNING.value, JobState.PUBLISHING.value}
        or job.lease_expires_at is None
        or _aware_utc(job.lease_expires_at) > current_time
    ):
        return None
    result = await record_normalization_failure(
        db,
        job_id=job.id,
        reason_code=NormalizationReason.WORKER_INTERRUPTED,
        failed_at=current_time,
    )
    await cleanup_unpublished_normalization_attempts(
        db,
        storage=storage,
        job_id=job.id,
    )
    return result


async def recover_missing_ready_normalization_job(
    db: AsyncSession,
    *,
    job_id: UUID,
    now: datetime | None = None,
) -> bool:
    """Demote a false ready pointer so retained accepted source can regenerate it."""

    require_database_context(db, allowed_context_kinds=frozenset({"worker"}))

    current_time = now or datetime.now(UTC)
    snapshot = await db.scalar(
        select(PlaybackNormalizationJob)
        .where(PlaybackNormalizationJob.id == job_id)
        .execution_options(populate_existing=True)
    )
    if snapshot is None:
        return False

    # Deletion and publication share Meeting as the lifecycle fence. Lock it
    # before the normalization job and its canonical artifact so a late ready
    # verifier cannot resurrect a purged derivative.
    meeting = await db.scalar(
        select(Meeting)
        .where(
            Meeting.workspace_id == snapshot.workspace_id,
            Meeting.id == snapshot.meeting_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        await db.rollback()
        return False
    job = await db.scalar(
        select(PlaybackNormalizationJob)
        .where(
            PlaybackNormalizationJob.workspace_id == snapshot.workspace_id,
            PlaybackNormalizationJob.id == job_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if job is None or job.state != JobState.READY.value:
        await db.rollback()
        return False
    canonical = None
    if job.canonical_track_artifact_id is not None:
        canonical = await db.scalar(
            select(TrackArtifact)
            .where(
                TrackArtifact.workspace_id == job.workspace_id,
                TrackArtifact.meeting_id == job.meeting_id,
                TrackArtifact.id == job.canonical_track_artifact_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    if canonical is not None and canonical.status not in {"purged", "deleted"}:
        _supersede_playback_artifact(canonical)
    ensure_job_transition(
        JobState.READY,
        JobState.RETRY_WAIT,
        reason_code=NormalizationReason.PUBLISH_INTERRUPTED,
    )
    job.state = JobState.RETRY_WAIT.value
    job.reason_code = NormalizationReason.PUBLISH_INTERRUPTED.value
    job.canonical_track_artifact_id = None
    job.ready_at = None
    job.next_attempt_at = current_time
    job.cycle_attempt_count = 0
    job.workflow_run_id = None
    job.priority_class = PriorityClass.DUE_RETRY.value
    job.trigger_kind = TriggerKind.RECONCILE.value
    job.lease_owner_sha256 = None
    job.lease_expires_at = None
    _add_job_audit_event(
        db,
        job=job,
        event_type="playback_normalization_failed",
        metadata={
            "reason_code": NormalizationReason.PUBLISH_INTERRUPTED.value,
            "state": job.state,
        },
        created_at=current_time,
    )
    await db.commit()
    return True


async def _prepare_attempt(
    db: AsyncSession,
    *,
    job_id: UUID,
    lease_owner: str,
    now: datetime | None = None,
    lease_duration: timedelta = DEFAULT_NORMALIZATION_ACTIVITY_LEASE,
) -> _AttemptInputs | NormalizationExecutionResult:
    current_time = now or datetime.now(UTC)
    job_meeting_id = await db.scalar(
        select(PlaybackNormalizationJob.meeting_id).where(PlaybackNormalizationJob.id == job_id)
    )
    if job_meeting_id is None:
        raise ValueError("normalization job not found")
    meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.id == job_meeting_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting is None:
        raise RuntimeError("source_missing")
    if meeting_is_deleted_or_deleting(meeting):
        raise NormalizationExecutionDeferred("meeting deletion blocks normalization")
    job = await db.scalar(
        select(PlaybackNormalizationJob)
        .where(PlaybackNormalizationJob.id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if job is None:
        raise ValueError("normalization job not found")
    if job.state == JobState.READY.value and job.canonical_track_artifact_id is not None:
        canonical = await db.get(TrackArtifact, job.canonical_track_artifact_id)
        if canonical is None:
            raise RuntimeError("canonical_artifact_missing")
        return NormalizationExecutionResult(
            job_id=job.id,
            canonical_track_artifact_id=canonical.id,
            derivation_kind=canonical.derivation_kind or DerivationKind.LEGACY_UNVALIDATED.value,
            reused=True,
        )
    if job.trigger_kind == TriggerKind.LEGACY_BACKFILL.value:
        backfill_run = (
            await db.get(PlaybackBackfillRun, job.backfill_run_id)
            if job.backfill_run_id is not None
            else None
        )
        if (
            backfill_run is None
            or backfill_run.inventory_completed_at is None
            or backfill_run.state
            not in {
                BackfillState.INVENTORY_COMPLETE.value,
                BackfillState.DISPATCHING.value,
                BackfillState.COMPLETE.value,
            }
        ):
            raise NormalizationExecutionDeferred(
                "legacy normalization waits for complete inventory"
            )
    if job.state == JobState.RETRY_WAIT.value:
        if (
            job.next_attempt_at is None
            or _aware_utc(job.next_attempt_at) > current_time
            or job.cycle_attempt_count >= 4
        ):
            raise NormalizationExecutionDeferred("normalization retry is not due")
        ensure_job_transition(JobState.RETRY_WAIT, JobState.QUEUED)
        job.state = JobState.QUEUED.value
        job.reason_code = None
        job.next_attempt_at = None
        _add_job_audit_event(
            db,
            job=job,
            event_type="playback_normalization_retried",
            metadata={
                "state": job.state,
                "attempt_count": job.attempt_count,
                "retry_cycle_count": job.retry_cycle_count,
            },
            created_at=current_time,
        )
    if job.state != JobState.QUEUED.value:
        raise NormalizationExecutionDeferred("normalization job is already owned")
    if job.cycle_attempt_count >= 4:
        raise NormalizationExecutionDeferred("normalization retry cycle is exhausted")

    artifacts = list(
        await db.scalars(
            select(TrackArtifact)
            .where(
                TrackArtifact.workspace_id == job.workspace_id,
                TrackArtifact.meeting_id == job.meeting_id,
                TrackArtifact.media_revision_id == job.media_revision_id,
                TrackArtifact.track_role.in_(
                    [
                        TrackRole.PLAYBACK.value,
                        TrackRole.MEDIA.value,
                        TrackRole.MICROPHONE.value,
                        TrackRole.SYSTEM.value,
                    ]
                ),
            )
            .order_by(TrackArtifact.created_at, TrackArtifact.id)
        )
    )
    candidate_rows = [
        artifact
        for artifact in artifacts
        if artifact.track_role == TrackRole.PLAYBACK.value
        and artifact.status in {"candidate", "stored"}
        and artifact.id != job.canonical_track_artifact_id
        and artifact.validated_at is None
    ]
    candidate = (
        candidate_rows[0]
        if job.planned_action == PlannedAction.VALIDATE_CANDIDATE.value and len(candidate_rows) == 1
        else None
    )
    media = next(
        (
            artifact
            for artifact in artifacts
            if artifact.track_role == TrackRole.MEDIA.value and artifact.status == "stored"
        ),
        None,
    )
    microphone = next(
        (
            artifact
            for artifact in artifacts
            if artifact.track_role == TrackRole.MICROPHONE.value and artifact.status == "stored"
        ),
        None,
    )
    system = next(
        (
            artifact
            for artifact in artifacts
            if artifact.track_role == TrackRole.SYSTEM.value and artifact.status == "stored"
        ),
        None,
    )
    revision = await db.get(MediaRevision, job.media_revision_id)
    if revision is None or revision.status != MediaRevisionStatus.ACCEPTED.value:
        raise RuntimeError("source_missing")
    expected_source_digests = revision.track_sha256_by_role or {}
    source_error: str | None = None
    if revision.source_kind in _SINGLE_SOURCE_KINDS:
        if media is None:
            source_error = "source_missing"
        elif expected_source_digests.get(TrackRole.MEDIA.value) != media.sha256:
            source_error = "source_mismatch"
    else:
        if microphone is None or system is None:
            source_error = "source_missing"
        elif (
            expected_source_digests.get(TrackRole.MICROPHONE.value) != microphone.sha256
            or expected_source_digests.get(TrackRole.SYSTEM.value) != system.sha256
        ):
            source_error = "source_mismatch"
    if candidate is None and source_error is not None:
        raise RuntimeError(source_error)

    attempt_id = uuid4()
    attempt = PlaybackNormalizationAttempt(
        id=attempt_id,
        workspace_id=job.workspace_id,
        meeting_id=job.meeting_id,
        media_revision_id=job.media_revision_id,
        job_id=job.id,
        attempt_number=job.attempt_count + 1,
        cycle_number=job.retry_cycle_count + 1,
        state=AttemptState.LOCAL_PREPARING.value,
        storage_object_key=build_playback_attempt_object_key(
            organization_id=job.organization_id,
            workspace_id=job.workspace_id,
            meeting_id=job.meeting_id,
            media_revision_id=job.media_revision_id,
            attempt_id=attempt_id,
        ),
        derivation_kind=(
            DerivationKind.UPLOADED_CANDIDATE.value
            if candidate is not None
            else DerivationKind.SINGLE_SOURCE_TRANSCODE.value
            if media is not None
            else DerivationKind.DUAL_SOURCE_MIX_TRANSCODE.value
        ),
        selected_stream_index=None,
        source_stream_count=0,
        source_audio_stream_count=0,
    )
    ensure_job_transition(JobState.QUEUED, JobState.RUNNING)
    job.state = JobState.RUNNING.value
    job.attempt_count += 1
    job.cycle_attempt_count += 1
    job.started_at = job.started_at or current_time
    job.last_heartbeat_at = current_time
    job.lease_owner_sha256 = sha256(lease_owner.encode("utf-8")).hexdigest()
    job.lease_expires_at = current_time + lease_duration
    db.add(attempt)
    _add_job_audit_event(
        db,
        job=job,
        event_type="playback_normalization_started",
        metadata={
            "state": job.state,
            "attempt_count": job.attempt_count,
            "retry_cycle_count": job.retry_cycle_count,
        },
        created_at=current_time,
    )
    await db.commit()
    return _AttemptInputs(
        job=job,
        attempt=attempt,
        expected_duration_seconds=revision.duration_seconds,
        candidate=candidate,
        media=media,
        microphone=microphone,
        system=system,
        source_error=source_error,
    )


async def run_normalization_job(
    *,
    db: AsyncSession,
    storage: object,
    job_id: UUID,
    work_directory: str | Path,
    pipeline: NormalizationPipeline,
    lease_duration: timedelta = DEFAULT_NORMALIZATION_ACTIVITY_LEASE,
    lease_owner: str | None = None,
    work_budget_bytes: int = DEFAULT_NORMALIZATION_WORK_BUDGET_BYTES,
    output_max_bytes: int = MAX_OUTPUT_BYTES,
    work_reserve_bytes: int = DEFAULT_NORMALIZATION_WORK_RESERVE_BYTES,
) -> NormalizationExecutionResult:
    require_database_context(db, allowed_context_kinds=frozenset({"worker"}))
    lease_owner_identity = lease_owner or f"direct:{job_id}"
    try:
        return await _execute_normalization_job(
            db=db,
            storage=storage,
            job_id=job_id,
            work_directory=work_directory,
            pipeline=pipeline,
            lease_duration=lease_duration,
            lease_owner=lease_owner_identity,
            work_budget_bytes=work_budget_bytes,
            output_max_bytes=output_max_bytes,
            work_reserve_bytes=work_reserve_bytes,
        )
    except NormalizationExecutionDeferred:
        raise
    except BaseException as exc:
        reason_code = normalization_reason_from_exception(exc)
        with suppress(Exception):
            await db.rollback()
        with suppress(Exception):
            await rehydrate_tenant_context(db)
        try:
            failure = await record_normalization_failure(
                db,
                job_id=job_id,
                reason_code=reason_code,
            )
        except Exception:
            raise NormalizationExecutionFailure(
                reason_code=NormalizationReason.DATABASE_UNAVAILABLE,
                should_retry=True,
                cycle_exhausted=False,
            ) from None
        with suppress(Exception):
            await cleanup_unpublished_normalization_attempts(
                db,
                storage=storage,
                job_id=job_id,
            )
        raise NormalizationExecutionFailure(
            reason_code=failure.reason_code,
            should_retry=failure.should_temporal_retry,
            cycle_exhausted=failure.cycle_exhausted,
        ) from None


async def _execute_normalization_job(
    *,
    db: AsyncSession,
    storage: object,
    job_id: UUID,
    work_directory: str | Path,
    pipeline: NormalizationPipeline,
    lease_duration: timedelta,
    lease_owner: str,
    work_budget_bytes: int,
    output_max_bytes: int,
    work_reserve_bytes: int,
) -> NormalizationExecutionResult:
    expected_lease_owner_sha256 = sha256(lease_owner.encode("utf-8")).hexdigest()
    prepared = await _prepare_attempt(
        db,
        job_id=job_id,
        lease_owner=lease_owner,
        lease_duration=lease_duration,
    )
    if isinstance(prepared, NormalizationExecutionResult):
        return prepared

    base_directory = Path(work_directory)
    base_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    work_path = Path(tempfile.mkdtemp(prefix=f"{job_id}-", dir=base_directory))
    os.chmod(work_path, 0o700)
    output_path = work_path / "output.m4a"
    try:
        output: NormalizedOutput
        if prepared.candidate is not None:
            candidate_path = work_path / "candidate.media"
            _require_normalization_work_capacity(
                work_path,
                source_bytes=prepared.candidate.byte_length,
                sources_downloaded=False,
                work_budget_bytes=work_budget_bytes,
                output_max_bytes=output_max_bytes,
                reserve_bytes=work_reserve_bytes,
            )
            await _download_verified_artifact(
                storage,
                prepared.candidate,
                candidate_path,
                max_bytes=MAX_OUTPUT_BYTES,
            )
            _require_normalization_work_capacity(
                work_path,
                source_bytes=prepared.candidate.byte_length,
                sources_downloaded=True,
                work_budget_bytes=work_budget_bytes,
                output_max_bytes=output_max_bytes,
                reserve_bytes=work_reserve_bytes,
            )
            try:
                output = await pipeline.derive_candidate(candidate_path, output_path)
            except CandidateRejected:
                output_path.unlink(missing_ok=True)
                candidate_path.unlink(missing_ok=True)
                if prepared.media is not None:
                    output = await _derive_from_single_source(
                        storage=storage,
                        prepared=prepared,
                        work_path=work_path,
                        output_path=output_path,
                        pipeline=pipeline,
                        work_budget_bytes=work_budget_bytes,
                        output_max_bytes=output_max_bytes,
                        work_reserve_bytes=work_reserve_bytes,
                    )
                else:
                    output = await _derive_from_first_party_sources(
                        storage=storage,
                        prepared=prepared,
                        work_path=work_path,
                        output_path=output_path,
                        pipeline=pipeline,
                        work_budget_bytes=work_budget_bytes,
                        output_max_bytes=output_max_bytes,
                        work_reserve_bytes=work_reserve_bytes,
                    )
        elif prepared.media is not None:
            output = await _derive_from_single_source(
                storage=storage,
                prepared=prepared,
                work_path=work_path,
                output_path=output_path,
                pipeline=pipeline,
                work_budget_bytes=work_budget_bytes,
                output_max_bytes=output_max_bytes,
                work_reserve_bytes=work_reserve_bytes,
            )
        else:
            output = await _derive_from_first_party_sources(
                storage=storage,
                prepared=prepared,
                work_path=work_path,
                output_path=output_path,
                pipeline=pipeline,
                work_budget_bytes=work_budget_bytes,
                output_max_bytes=output_max_bytes,
                work_reserve_bytes=work_reserve_bytes,
            )
        _validate_authoritative_source_duration(
            output.source_duration_ms,
            expected_duration_seconds=prepared.expected_duration_seconds,
            manual_upload=(
                prepared.job.source_kind == MediaRevisionSourceKind.MANUAL_UPLOAD.value
            ),
        )
        await _ensure_normalized_output_matches_file(output_path, output)

        # Fence ownership before storage I/O, then commit to release the
        # lifecycle locks. A deletion may race the upload; the post-upload
        # Meeting → Job → Attempt fence below deletes the late object instead
        # of holding a database lock across an unbounded storage call.
        meeting = await db.scalar(
            select(Meeting)
            .where(
                Meeting.id == prepared.job.meeting_id,
                Meeting.workspace_id == prepared.job.workspace_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        current_time = datetime.now(UTC)
        job = await db.scalar(
            select(PlaybackNormalizationJob)
            .where(PlaybackNormalizationJob.id == prepared.job.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        attempt = await db.scalar(
            select(PlaybackNormalizationAttempt)
            .where(PlaybackNormalizationAttempt.id == prepared.attempt.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            meeting is None
            or meeting_is_deleted_or_deleting(meeting)
            or attempt is None
            or job is None
            or attempt.state != AttemptState.LOCAL_PREPARING.value
            or job.state != JobState.RUNNING.value
            or attempt.attempt_number != job.attempt_count
            or job.lease_owner_sha256 != expected_lease_owner_sha256
            or job.lease_expires_at is None
            or _aware_utc(job.lease_expires_at) <= current_time
        ):
            await db.rollback()
            raise NormalizationExecutionDeferred(
                "normalization activity no longer owns the durable attempt"
            )
        await _reserve_playback_storage(
            db,
            job=job,
            attempt=attempt,
            declared_bytes=output.output_byte_length,
            now=current_time,
        )
        await db.commit()
        await _upload_verified_output(
            storage,
            object_key=prepared.attempt.storage_object_key,
            source_path=output_path,
            output=output,
        )
        current_time = datetime.now(UTC)
        meeting = await db.scalar(
            select(Meeting)
            .where(
                Meeting.id == prepared.job.meeting_id,
                Meeting.workspace_id == prepared.job.workspace_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        job = await db.scalar(
            select(PlaybackNormalizationJob)
            .where(PlaybackNormalizationJob.id == prepared.job.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        attempt = await db.scalar(
            select(PlaybackNormalizationAttempt)
            .where(PlaybackNormalizationAttempt.id == prepared.attempt.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            meeting is None
            or meeting_is_deleted_or_deleting(meeting)
            or attempt is None
            or job is None
        ):
            late_workspace_id = prepared.job.workspace_id
            late_meeting_id = prepared.job.meeting_id
            late_object_key = prepared.attempt.storage_object_key
            await db.rollback()
            try:
                await _delete_storage_object(storage, late_object_key)
            except Exception:
                await persist_orphan_cleanup_intents(
                    db,
                    workspace_id=late_workspace_id,
                    meeting_id=late_meeting_id,
                    object_keys=(late_object_key,),
                    reason="normalization_late_object_cleanup_failed",
                )
            raise NormalizationExecutionDeferred(
                "normalization activity no longer owns the durable attempt"
            )
        if (
            attempt.state != AttemptState.LOCAL_PREPARING.value
            or job.state != JobState.RUNNING.value
            or attempt.attempt_number != job.attempt_count
            or job.lease_owner_sha256 != expected_lease_owner_sha256
            or job.lease_expires_at is None
            or _aware_utc(job.lease_expires_at) <= current_time
        ):
            late_workspace_id = prepared.job.workspace_id
            late_meeting_id = prepared.job.meeting_id
            late_object_key = attempt.storage_object_key
            await db.rollback()
            try:
                await _delete_storage_object(storage, late_object_key)
            except Exception:
                await persist_orphan_cleanup_intents(
                    db,
                    workspace_id=late_workspace_id,
                    meeting_id=late_meeting_id,
                    object_keys=(late_object_key,),
                    reason="normalization_late_object_cleanup_failed",
                )
            raise NormalizationExecutionDeferred(
                "normalization activity no longer owns the durable attempt"
            )
        ensure_attempt_transition(AttemptState.LOCAL_PREPARING, AttemptState.UPLOADED)
        attempt.state = AttemptState.UPLOADED.value
        attempt.derivation_kind = output.derivation_kind
        attempt.selected_stream_index = output.selected_stream_index
        attempt.source_stream_count = output.source_stream_count
        attempt.source_audio_stream_count = output.source_audio_stream_count
        attempt.source_duration_ms = output.source_duration_ms
        attempt.output_duration_ms = output.output_duration_ms
        attempt.output_byte_length = output.output_byte_length
        attempt.output_sha256 = output.output_sha256
        attempt.output_audio_bit_rate = output.output_audio_bit_rate
        attempt.output_sample_rate_hz = output.output_sample_rate_hz
        attempt.output_channel_count = output.output_channel_count
        attempt.moov_before_mdat = output.moov_before_mdat
        attempt.fragmented = output.fragmented
        attempt.full_decode_passed = output.full_decode_passed
        attempt.uploaded_at = current_time
        ensure_job_transition(JobState.RUNNING, JobState.PUBLISHING)
        job.state = JobState.PUBLISHING.value
        job.last_heartbeat_at = current_time
        job.lease_expires_at = current_time + lease_duration
        _add_job_audit_event(
            db,
            job=job,
            event_type="playback_normalization_publishing",
            metadata={
                "state": job.state,
                "attempt_count": job.attempt_count,
                "stream_count": attempt.source_stream_count,
                "audio_stream_count": attempt.source_audio_stream_count,
                "full_decode_passed": bool(attempt.full_decode_passed),
                "moov_before_mdat": bool(attempt.moov_before_mdat),
                "recovered_source": bool(output.recovered_source),
            },
            created_at=current_time,
        )
        await db.commit()
        return await publish_uploaded_attempt(
            db=db,
            storage=storage,
            attempt_id=attempt.id,
        )
    finally:
        await to_thread.run_sync(lambda: shutil.rmtree(work_path, ignore_errors=True))


async def _derive_from_first_party_sources(
    *,
    storage: object,
    prepared: _AttemptInputs,
    work_path: Path,
    output_path: Path,
    pipeline: NormalizationPipeline,
    work_budget_bytes: int,
    output_max_bytes: int,
    work_reserve_bytes: int,
) -> NormalizedOutput:
    if prepared.source_error is not None:
        raise RuntimeError(prepared.source_error)
    if prepared.microphone is None or prepared.system is None:
        raise RuntimeError("source_missing")
    source_bytes = prepared.microphone.byte_length + prepared.system.byte_length
    _require_normalization_work_capacity(
        work_path,
        source_bytes=source_bytes,
        sources_downloaded=False,
        work_budget_bytes=work_budget_bytes,
        output_max_bytes=output_max_bytes,
        reserve_bytes=work_reserve_bytes,
    )
    microphone_path = work_path / "microphone.source"
    system_path = work_path / "system.source"
    await _download_verified_artifact(
        storage,
        prepared.microphone,
        microphone_path,
        max_bytes=prepared.microphone.byte_length,
    )
    await _download_verified_artifact(
        storage,
        prepared.system,
        system_path,
        max_bytes=prepared.system.byte_length,
    )
    _require_normalization_work_capacity(
        work_path,
        source_bytes=source_bytes,
        sources_downloaded=True,
        work_budget_bytes=work_budget_bytes,
        output_max_bytes=output_max_bytes,
        reserve_bytes=work_reserve_bytes,
    )
    return await pipeline.derive_dual_source(
        microphone_path,
        system_path,
        output_path,
    )


async def _derive_from_single_source(
    *,
    storage: object,
    prepared: _AttemptInputs,
    work_path: Path,
    output_path: Path,
    pipeline: NormalizationPipeline,
    work_budget_bytes: int,
    output_max_bytes: int,
    work_reserve_bytes: int,
) -> NormalizedOutput:
    if prepared.source_error is not None:
        raise RuntimeError(prepared.source_error)
    if prepared.media is None:
        raise RuntimeError("source_missing")
    _require_normalization_work_capacity(
        work_path,
        source_bytes=prepared.media.byte_length,
        sources_downloaded=False,
        work_budget_bytes=work_budget_bytes,
        output_max_bytes=output_max_bytes,
        reserve_bytes=work_reserve_bytes,
    )
    media_path = work_path / "media.source"
    await _download_verified_artifact(
        storage,
        prepared.media,
        media_path,
        max_bytes=prepared.media.byte_length,
    )
    _require_normalization_work_capacity(
        work_path,
        source_bytes=prepared.media.byte_length,
        sources_downloaded=True,
        work_budget_bytes=work_budget_bytes,
        output_max_bytes=output_max_bytes,
        reserve_bytes=work_reserve_bytes,
    )
    is_manual_upload = prepared.job.source_kind == MediaRevisionSourceKind.MANUAL_UPLOAD.value
    return await pipeline.derive_single_source(
        media_path,
        output_path,
        tolerant_first=is_manual_upload,
        expected_duration_seconds=(
            prepared.expected_duration_seconds if is_manual_upload else None
        ),
    )


def _attempt_is_publishable(attempt: PlaybackNormalizationAttempt) -> bool:
    return (
        attempt.state == AttemptState.UPLOADED.value
        and attempt.output_duration_ms is not None
        and attempt.output_duration_ms > 0
        and attempt.output_byte_length is not None
        and 0 < attempt.output_byte_length <= MAX_OUTPUT_BYTES
        and attempt.output_sha256 is not None
        and len(attempt.output_sha256) == 64
        and attempt.output_audio_bit_rate is not None
        and attempt.output_audio_bit_rate > 0
        and attempt.output_sample_rate_hz == 48_000
        and attempt.output_channel_count == 1
        and attempt.moov_before_mdat is True
        and attempt.fragmented is False
        and attempt.full_decode_passed is True
    )


async def _discard_unowned_attempt(
    *,
    db: AsyncSession,
    storage: object,
    attempt: PlaybackNormalizationAttempt,
    cleanup_reason: str,
) -> None:
    """Remove a late worker's immutable object without touching a published winner."""

    await cleanup_normalization_attempt(
        db,
        storage=storage,
        attempt_id=attempt.id,
        cleanup_reason=cleanup_reason,
        late_object_arrival=True,
    )


def _supersede_playback_artifact(artifact: TrackArtifact) -> None:
    artifact.status = "superseded"
    artifact.normalization_profile_version = None
    artifact.validated_at = None
    artifact.source_fingerprint_sha256 = None
    artifact.validation_version = None
    artifact.derivation_kind = None


async def publish_uploaded_attempt(
    *,
    db: AsyncSession,
    storage: object,
    attempt_id: UUID,
) -> NormalizationExecutionResult:
    require_database_context(db, allowed_context_kinds=frozenset({"worker"}))
    await rehydrate_tenant_context(db)
    attempt_job_id = await db.scalar(
        select(PlaybackNormalizationAttempt.job_id).where(
            PlaybackNormalizationAttempt.id == attempt_id
        )
    )
    if attempt_job_id is None:
        raise RuntimeError("generated_output_invalid")
    job_meeting_id = await db.scalar(
        select(PlaybackNormalizationJob.meeting_id).where(
            PlaybackNormalizationJob.id == attempt_job_id
        )
    )
    if job_meeting_id is None:
        raise RuntimeError("database_unavailable")
    meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.id == job_meeting_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting is None:
        raise RuntimeError("source_missing")
    job = await db.scalar(
        select(PlaybackNormalizationJob)
        .where(PlaybackNormalizationJob.id == attempt_job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if job is None:
        raise RuntimeError("database_unavailable")
    attempt = await db.scalar(
        select(PlaybackNormalizationAttempt)
        .where(PlaybackNormalizationAttempt.id == attempt_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting_is_deleted_or_deleting(meeting):
        if attempt is not None:
            await _discard_unowned_attempt(
                db=db,
                storage=storage,
                attempt=attempt,
                cleanup_reason=NormalizationReason.MEETING_DELETING.value,
            )
        raise RuntimeError("meeting_deleting")
    if attempt is None or not _attempt_is_publishable(attempt):
        raise RuntimeError("generated_output_invalid")
    if job.state == JobState.READY.value and job.canonical_track_artifact_id is not None:
        winner = await db.get(TrackArtifact, job.canonical_track_artifact_id)
        if winner is None:
            raise RuntimeError("canonical_artifact_missing")
        return await _clean_losing_attempt(
            db=db,
            storage=storage,
            attempt=attempt,
            winner=winner,
        )
    if (
        job.state != JobState.PUBLISHING.value
        or attempt.attempt_number != job.attempt_count
        or job.lease_expires_at is None
        or _aware_utc(job.lease_expires_at) <= datetime.now(UTC)
    ):
        await _discard_unowned_attempt(
            db=db,
            storage=storage,
            attempt=attempt,
            cleanup_reason="stale_publisher",
        )
        raise NormalizationExecutionDeferred("normalization activity no longer owns publication")

    revision = await db.scalar(
        select(MediaRevision)
        .where(MediaRevision.id == job.media_revision_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if revision is None:
        raise RuntimeError("source_missing")
    if revision.status != MediaRevisionStatus.ACCEPTED.value or not revision.manifest_sha256:
        raise RuntimeError("source_missing")
    current_fingerprint = source_fingerprint_sha256(
        media_revision_id=revision.id,
        source_kind=revision.source_kind,
        manifest_sha256=revision.manifest_sha256,
        track_sha256_by_role=revision.track_sha256_by_role or {},
        duration_seconds=revision.duration_seconds,
    )
    if current_fingerprint != job.source_fingerprint_sha256:
        raise RuntimeError("source_mismatch")

    prior_playback = list(
        await db.scalars(
            select(TrackArtifact).where(
                TrackArtifact.workspace_id == job.workspace_id,
                TrackArtifact.media_revision_id == job.media_revision_id,
                TrackArtifact.track_role == TrackRole.PLAYBACK.value,
                TrackArtifact.status.in_(["candidate", "stored"]),
            )
        )
    )
    if prior_playback:
        await clear_source_playback_verification(
            db,
            workspace_id=job.workspace_id,
            meeting_id=job.meeting_id,
            media_revision_id=job.media_revision_id,
        )
    for artifact in prior_playback:
        _supersede_playback_artifact(artifact)
    publication_time = datetime.now(UTC)
    storage_reservation = await _reserve_playback_storage(
        db,
        job=job,
        attempt=attempt,
        declared_bytes=int(attempt.output_byte_length or 0),
        now=publication_time,
    )
    canonical = TrackArtifact(
        meeting_id=job.meeting_id,
        media_revision_id=job.media_revision_id,
        workspace_id=job.workspace_id,
        track_role=TrackRole.PLAYBACK.value,
        codec="m4a-aac-lc",
        sample_rate_hz=attempt.output_sample_rate_hz or 48_000,
        channel_count=attempt.output_channel_count or 1,
        duration_seconds=max(1, round((attempt.output_duration_ms or 0) / 1_000)),
        byte_length=attempt.output_byte_length or 0,
        sha256=attempt.output_sha256 or "",
        storage_object_key=attempt.storage_object_key,
        status="stored",
        normalization_profile_version=job.profile_version,
        validated_at=datetime.now(UTC),
        derivation_kind=attempt.derivation_kind,
        source_fingerprint_sha256=job.source_fingerprint_sha256,
        validation_version=job.validation_version,
    )
    db.add(canonical)
    await db.flush()
    if storage_reservation is not None:
        await commit_storage_reservation(
            db,
            reservation_id=storage_reservation.id,
            artifact_id=canonical.id,
            actual_bytes=canonical.byte_length,
            now=publication_time,
        )
        await mark_source_playback_verified(
            db,
            workspace_id=job.workspace_id,
            meeting_id=job.meeting_id,
            media_revision_id=job.media_revision_id,
            verified_at=publication_time,
        )
    ensure_attempt_transition(AttemptState.UPLOADED, AttemptState.PUBLISHED)
    attempt.state = AttemptState.PUBLISHED.value
    attempt.published_track_artifact_id = canonical.id
    attempt.published_at = publication_time
    ensure_job_transition(JobState.PUBLISHING, JobState.READY)
    job.state = JobState.READY.value
    job.reason_code = None
    job.canonical_track_artifact_id = canonical.id
    job.ready_at = publication_time
    job.next_attempt_at = None
    job.lease_owner_sha256 = None
    job.lease_expires_at = None
    completed_metadata = {
        "profile_version": job.profile_version,
        "state": job.state,
        "attempt_count": job.attempt_count,
        "retry_cycle_count": job.retry_cycle_count,
        "stream_count": attempt.source_stream_count,
        "audio_stream_count": attempt.source_audio_stream_count,
        "full_decode_passed": bool(attempt.full_decode_passed),
        "moov_before_mdat": bool(attempt.moov_before_mdat),
        "output_byte_length": attempt.output_byte_length,
        "canonical_byte_length": canonical.byte_length,
    }
    _add_job_audit_event(
        db,
        job=job,
        event_type="playback_normalization_completed",
        metadata=completed_metadata,
        created_at=publication_time,
    )
    if job.trigger_kind == TriggerKind.LEGACY_BACKFILL.value:
        _add_job_audit_event(
            db,
            job=job,
            event_type="playback_normalization_backfilled",
            metadata={
                "profile_version": job.profile_version,
                "state": job.state,
                "trigger_kind": job.trigger_kind,
                "planned_action": job.planned_action,
                "attempt_count": job.attempt_count,
            },
            created_at=publication_time,
        )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        winner_job = await db.get(PlaybackNormalizationJob, job.id)
        if winner_job is None or winner_job.canonical_track_artifact_id is None:
            raise
        winner = await db.get(TrackArtifact, winner_job.canonical_track_artifact_id)
        loser = await db.get(PlaybackNormalizationAttempt, attempt.id)
        if winner is None or loser is None:
            raise RuntimeError("publish_interrupted") from None
        return await _clean_losing_attempt(
            db=db,
            storage=storage,
            attempt=loser,
            winner=winner,
        )
    return NormalizationExecutionResult(
        job_id=job.id,
        canonical_track_artifact_id=canonical.id,
        derivation_kind=canonical.derivation_kind or attempt.derivation_kind,
        reused=False,
    )


async def _clean_losing_attempt(
    *,
    db: AsyncSession,
    storage: object,
    attempt: PlaybackNormalizationAttempt,
    winner: TrackArtifact,
) -> NormalizationExecutionResult:
    cleaned = await cleanup_normalization_attempt(
        db,
        storage=storage,
        attempt_id=attempt.id,
        cleanup_reason="duplicate_publisher",
    )
    if cleaned:
        add_normalization_audit_event(
            db,
            workspace_id=attempt.workspace_id,
            meeting_id=attempt.meeting_id,
            media_revision_id=attempt.media_revision_id,
            event_type="playback_normalization_duplicate_reused",
            metadata={
                "profile_version": winner.normalization_profile_version
                or CANONICAL_PROFILE_VERSION,
                "state": JobState.READY.value,
                "cleanup_result": "deleted",
            },
            created_at=datetime.now(UTC),
        )
        await db.commit()
    return NormalizationExecutionResult(
        job_id=attempt.job_id,
        canonical_track_artifact_id=winner.id,
        derivation_kind=winner.derivation_kind or DerivationKind.LEGACY_UNVALIDATED.value,
        reused=True,
    )
