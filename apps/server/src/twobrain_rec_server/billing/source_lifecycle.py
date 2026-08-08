"""Lifecycle decisions for transcription sources and no-archive processing.

The cutoff rules stay small and pure so retries, Temporal replays and
maintenance scans use the same decision without duplicating wall-clock logic.
The gate writers use lazy database imports and never touch an object store.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

SOURCE_RETENTION_POLICY_UNCONFIGURED = "unconfigured"
SOURCE_TRACK_ROLES = frozenset({"media", "microphone", "system"})
SOURCE_TRACK_FILENAMES = frozenset({
    "meeting-transcription.wav",
    "mic.wav",
    "incoming.wav",
})

TRANSIENT_PURGE_AFTER = timedelta(minutes=15)
TRANSIENT_HARD_LIFETIME = timedelta(hours=24)


class SourceLifecycleError(ValueError):
    """The requested lifecycle transition is unsafe or incomplete."""


class TransientMediaState(StrEnum):
    ADMITTED = "admitted"
    PROCESSING = "processing"
    TERMINAL = "terminal"
    PURGE_DUE = "purge_due"
    PURGED = "purged"


class SourceLifecycleState(StrEnum):
    """Persisted state for current/legacy transcription source artifacts."""

    NOT_SOURCE = "not_source"
    RECOVERABLE = "recoverable"
    PURGE_DUE = "purge_due"
    PURGE_PENDING = "purge_pending"
    PURGED = "purged"


@dataclass(frozen=True, slots=True)
class TransientMediaAdmission:
    """Durable facts for an explicitly selected no-archive processing run."""

    admitted_at: datetime
    source_bytes: int
    state: TransientMediaState = TransientMediaState.ADMITTED
    terminal_at: datetime | None = None
    purged_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_aware(self.admitted_at)
        if self.source_bytes <= 0:
            raise SourceLifecycleError("transient source bytes must be positive")
        if self.terminal_at is not None:
            _require_aware(self.terminal_at)
            if self.terminal_at < self.admitted_at:
                raise SourceLifecycleError("terminal time cannot precede admission")
        if self.purged_at is not None:
            _require_aware(self.purged_at)

    @property
    def hard_deadline(self) -> datetime:
        return self.admitted_at + TRANSIENT_HARD_LIFETIME

    @property
    def terminal_deadline(self) -> datetime | None:
        if self.terminal_at is None:
            return None
        return self.terminal_at + TRANSIENT_PURGE_AFTER

    @property
    def purge_deadline(self) -> datetime:
        """The earliest terminal/hard cutoff; hard lifetime always wins."""
        return min(self.hard_deadline, self.terminal_deadline or self.hard_deadline)

    def is_purge_due(self, now: datetime) -> bool:
        _require_aware(now)
        return self.state is not TransientMediaState.PURGED and now >= self.purge_deadline

    def purge_reason(self, now: datetime) -> str | None:
        if not self.is_purge_due(now):
            return None
        if self.terminal_deadline is not None and now >= self.terminal_deadline:
            return "terminal_processing_plus_15_minutes"
        return "hard_lifetime_24_hours"

    def processing_started(self) -> TransientMediaAdmission:
        if self.state is not TransientMediaState.ADMITTED:
            raise SourceLifecycleError("transient admission is not waiting to start")
        return _replace(self, state=TransientMediaState.PROCESSING)

    def mark_terminal(self, now: datetime) -> TransientMediaAdmission:
        _require_aware(now)
        if self.state not in {
            TransientMediaState.ADMITTED,
            TransientMediaState.PROCESSING,
            TransientMediaState.TERMINAL,
        }:
            raise SourceLifecycleError("transient admission is already purged")
        if now < self.admitted_at:
            raise SourceLifecycleError("terminal time cannot precede admission")
        return _replace(self, state=TransientMediaState.TERMINAL, terminal_at=now)

    def mark_purged(self, now: datetime) -> TransientMediaAdmission:
        _require_aware(now)
        if self.state is TransientMediaState.PURGED:
            return self
        if now < self.admitted_at:
            raise SourceLifecycleError("purge time cannot precede admission")
        return _replace(self, state=TransientMediaState.PURGED, purged_at=now)


def admit_transient_media(
    *,
    now: datetime,
    source_bytes: int,
    archive_requested: bool,
) -> TransientMediaAdmission:
    """Admit only an explicit no-archive operation.

    A missing/false choice is not silently converted into transient mode by
    callers; the archival path remains a separate storage-bound operation.
    """

    _require_aware(now)
    if archive_requested:
        raise SourceLifecycleError("transient admission cannot archive audio")
    return TransientMediaAdmission(admitted_at=now, source_bytes=source_bytes)


def source_retention_deadline(
    *,
    transcript_imported_at: datetime | None,
    playback_verified_at: datetime | None,
    retention_period: timedelta,
) -> datetime | None:
    """Return a recoverable-source purge deadline only after both gates pass.

    The later gate starts the policy clock.  Passing a new policy period on a
    maintenance scan recomputes the deadline; if either gate disappears the
    function returns ``None`` and recovery remains open.
    """

    if retention_period <= timedelta(0):
        raise SourceLifecycleError("source retention period must be positive")
    if transcript_imported_at is None or playback_verified_at is None:
        return None
    _require_aware(transcript_imported_at)
    _require_aware(playback_verified_at)
    return max(transcript_imported_at, playback_verified_at) + retention_period


def source_retention_purge_due(
    *,
    now: datetime,
    transcript_imported_at: datetime | None,
    playback_verified_at: datetime | None,
    retention_period: timedelta,
) -> bool:
    _require_aware(now)
    deadline = source_retention_deadline(
        transcript_imported_at=transcript_imported_at,
        playback_verified_at=playback_verified_at,
        retention_period=retention_period,
    )
    return deadline is not None and now >= deadline


def source_lifecycle_state_for_gates(
    *,
    transcript_imported_at: datetime | None,
    playback_verified_at: datetime | None,
    now: datetime,
    retention_period: timedelta | None,
) -> tuple[SourceLifecycleState, datetime | None]:
    """Derive a fail-closed state and deadline from the two retention gates.

    ``None`` retention configuration intentionally keeps the source recoverable;
    normal source deletion is never enabled by an implicit default.
    """

    _require_aware(now)
    if transcript_imported_at is None or playback_verified_at is None:
        return SourceLifecycleState.RECOVERABLE, None
    if retention_period is None:
        return SourceLifecycleState.RECOVERABLE, None
    deadline = source_retention_deadline(
        transcript_imported_at=transcript_imported_at,
        playback_verified_at=playback_verified_at,
        retention_period=retention_period,
    )
    return (
        SourceLifecycleState.PURGE_DUE if now >= deadline else SourceLifecycleState.RECOVERABLE,
        deadline,
    )


def source_cogs_evidence(
    *,
    byte_length: int,
    policy_version: str,
    backup_expiry_days: int | None,
) -> dict[str, int | str | None]:
    """Return metadata-only accounting evidence; no estimated cost replaces bytes."""

    if byte_length <= 0:
        raise SourceLifecycleError("source byte length must be positive")
    if not policy_version.strip():
        raise SourceLifecycleError("source policy version is required")
    if backup_expiry_days is not None and backup_expiry_days < 0:
        raise SourceLifecycleError("backup expiry days cannot be negative")
    return {
        "actual_primary_bytes": byte_length,
        "customer_quota_bytes": 0,
        "backup_expiry_days": backup_expiry_days,
        "policy_version": policy_version,
        "cogs_status": "exact_bytes_recorded_cost_model_external",
    }


async def mark_source_transcript_imported(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
    imported_at: datetime,
) -> int:
    """Record the transcript gate for current or legacy source artifacts."""

    return await _mark_source_gate(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        imported_at=imported_at,
        field_name="source_transcript_imported_at",
    )


async def mark_source_playback_verified(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
    verified_at: datetime,
) -> int:
    """Record the verified canonical-playback gate for source artifacts."""

    return await _mark_source_gate(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        imported_at=verified_at,
        field_name="source_playback_verified_at",
    )


async def clear_source_playback_verification(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
) -> int:
    """Reopen source recovery when its verified playback is superseded/lost."""

    rows = await _source_rows(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
    )
    changed = 0
    for row in rows:
        if row.source_playback_verified_at is not None:
            row.source_playback_verified_at = None
            row.source_retention_purge_due_at = None
            row.source_retention_policy_version = None
            row.source_lifecycle_state = SourceLifecycleState.RECOVERABLE.value
            changed += 1
    return changed


async def _mark_source_gate(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
    imported_at: datetime,
    field_name: str,
) -> int:
    _require_aware(imported_at)
    rows = await _source_rows(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
    )
    changed = 0
    for row in rows:
        if row.source_lifecycle_state == SourceLifecycleState.PURGED.value:
            continue
        if getattr(row, field_name) != imported_at:
            setattr(row, field_name, imported_at)
            changed += 1
        if row.source_lifecycle_state == SourceLifecycleState.NOT_SOURCE.value:
            row.source_lifecycle_state = SourceLifecycleState.RECOVERABLE.value
    return changed


async def _source_rows(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
) -> list[object]:
    from sqlalchemy import select

    from twobrain_rec_server.db.models import TrackArtifact

    query = select(TrackArtifact).where(
        TrackArtifact.workspace_id == workspace_id,
        TrackArtifact.meeting_id == meeting_id,
        TrackArtifact.track_role.in_(tuple(SOURCE_TRACK_ROLES)),
        TrackArtifact.status.not_in({"purged", "deleted"}),
    )
    query = query.where(
        TrackArtifact.media_revision_id.is_(None)
        if media_revision_id is None
        else TrackArtifact.media_revision_id == media_revision_id
    )
    return list((await db.scalars(query.with_for_update())).all())


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SourceLifecycleError("lifecycle timestamps must be timezone-aware")


def _replace(value: TransientMediaAdmission, **changes: object) -> TransientMediaAdmission:
    return replace(value, **changes)


__all__ = [
    "TRANSIENT_HARD_LIFETIME",
    "TRANSIENT_PURGE_AFTER",
    "SOURCE_RETENTION_POLICY_UNCONFIGURED",
    "SOURCE_TRACK_FILENAMES",
    "SOURCE_TRACK_ROLES",
    "SourceLifecycleError",
    "SourceLifecycleState",
    "TransientMediaAdmission",
    "TransientMediaState",
    "admit_transient_media",
    "source_retention_deadline",
    "source_retention_purge_due",
    "source_lifecycle_state_for_gates",
    "source_cogs_evidence",
    "mark_source_transcript_imported",
    "mark_source_playback_verified",
    "clear_source_playback_verification",
]
