"""Lifecycle decisions for transcription sources and no-archive processing.

This module is deliberately storage-provider agnostic.  The database/object-store
workers persist the returned timestamps and states; keeping the cutoff rules in a
small pure module makes retries, Temporal replays and maintenance scans use the
same decision without relying on wall-clock arithmetic in individual workers.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum

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


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SourceLifecycleError("lifecycle timestamps must be timezone-aware")


def _replace(value: TransientMediaAdmission, **changes: object) -> TransientMediaAdmission:
    return replace(value, **changes)


__all__ = [
    "TRANSIENT_HARD_LIFETIME",
    "TRANSIENT_PURGE_AFTER",
    "SourceLifecycleError",
    "TransientMediaAdmission",
    "TransientMediaState",
    "admit_transient_media",
    "source_retention_deadline",
    "source_retention_purge_due",
]
