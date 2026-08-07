from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.catalog import FREE_PROCESSING_SECONDS, classify_free_processing
from twobrain_rec_server.db.models import FreeUsageWindow, UsageLedgerEntry
from twobrain_rec_server.db.models import UsageReservation as UsageReservationRow

MOSCOW = ZoneInfo("Europe/Moscow")


def format_duration(seconds: int) -> str:
    if seconds < 0:
        raise ValueError("duration cannot be negative")
    return f"{seconds // 60} мин {seconds % 60} сек"


def moscow_window_for(moment: datetime) -> tuple[datetime, datetime]:
    local = moment.astimezone(MOSCOW)
    start_local = datetime(local.year, local.month, 1, tzinfo=MOSCOW)
    if local.month == 12:
        next_local = datetime(local.year + 1, 1, 1, tzinfo=MOSCOW)
    else:
        next_local = datetime(local.year, local.month + 1, 1, tzinfo=MOSCOW)
    return start_local.astimezone(UTC), next_local.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class SourceRange:
    source_id: str
    start_second: int
    end_second: int

    def __post_init__(self) -> None:
        if not self.source_id.strip() or self.start_second < 0 or self.end_second <= self.start_second:
            raise ValueError("source range must be a non-empty positive interval")

    @property
    def seconds(self) -> int:
        return self.end_second - self.start_second


@dataclass(slots=True)
class UsageReservation:
    reservation_id: str
    window_start: datetime
    declared_seconds: int
    state: str = "active"
    committed_seconds: int = 0

    @property
    def remaining_seconds(self) -> int:
        return max(0, self.declared_seconds - self.committed_seconds)


@dataclass(slots=True)
class FreeUsageLedger:
    """Exact-second ledger with source-range de-duplication.

    The caller must serialize this object per workspace/window transaction.
    """

    window_start: datetime
    window_end: datetime
    committed_seconds: int = 0
    _accepted_ranges: set[SourceRange] = field(default_factory=set)
    _reservations: dict[str, UsageReservation] = field(default_factory=dict)

    @classmethod
    def for_moment(cls, moment: datetime) -> FreeUsageLedger:
        start, end = moscow_window_for(moment)
        return cls(start, end)

    def reserve(self, reservation_id: str, declared_seconds: int) -> UsageReservation:
        if declared_seconds <= 0:
            raise ValueError("declared duration must be positive")
        if reservation_id in self._reservations:
            return self._reservations[reservation_id]
        reserved = sum(r.remaining_seconds for r in self._reservations.values() if r.state == "active")
        if self.committed_seconds + reserved + declared_seconds > FREE_PROCESSING_SECONDS:
            raise QuotaExceeded("free processing quota is exhausted")
        reservation = UsageReservation(reservation_id, self.window_start, declared_seconds)
        self._reservations[reservation_id] = reservation
        return reservation

    def commit(self, reservation_id: str, ranges: list[SourceRange]) -> int:
        reservation = self._reservations.get(reservation_id)
        if reservation is None or reservation.state != "active":
            raise ValueError("reservation is not active")
        unique: list[SourceRange] = []
        intervals: dict[str, list[tuple[int, int]]] = {}
        for item in self._accepted_ranges:
            intervals.setdefault(item.source_id, []).append((item.start_second, item.end_second))
        for item in ranges:
            portions = _subtract_source_range(item, intervals.get(item.source_id, []))
            unique.extend(portions)
            intervals.setdefault(item.source_id, []).extend(
                (part.start_second, part.end_second) for part in portions
            )
        accepted_seconds = sum(item.seconds for item in unique)
        if accepted_seconds > reservation.remaining_seconds:
            raise QuotaOverrun("accepted source range exceeds its reservation")
        self._accepted_ranges.update(unique)
        reservation.committed_seconds += accepted_seconds
        self.committed_seconds += accepted_seconds
        if reservation.remaining_seconds == 0:
            reservation.state = "committed"
        return accepted_seconds

    def release(self, reservation_id: str) -> None:
        reservation = self._reservations.get(reservation_id)
        if reservation is None:
            return
        if reservation.state == "active":
            reservation.state = "released"

    @property
    def remaining_seconds(self) -> int:
        return max(0, FREE_PROCESSING_SECONDS - self.committed_seconds)

    @property
    def threshold(self) -> str:
        return classify_free_processing(committed_seconds=self.committed_seconds)


class QuotaExceeded(RuntimeError):
    pass


class QuotaOverrun(RuntimeError):
    pass


async def reserve_free_usage(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    reservation_key: str,
    declared_seconds: int,
    now: datetime,
    expires_at: datetime | None = None,
) -> UsageReservationRow:
    """Reserve exact seconds in the Moscow calendar window under a row lock."""
    if declared_seconds <= 0 or not reservation_key.strip():
        raise ValueError("usage reservation is invalid")
    window_start, window_end = moscow_window_for(now)
    window = await db.scalar(
        select(FreeUsageWindow)
        .where(FreeUsageWindow.workspace_id == workspace_id, FreeUsageWindow.window_start == window_start)
        .with_for_update()
    )
    if window is None:
        window = FreeUsageWindow(
            id=uuid4(),
            workspace_id=workspace_id,
            window_start=window_start,
            window_end=window_end,
            included_seconds=FREE_PROCESSING_SECONDS,
        )
        db.add(window)
        await db.flush()
    existing = await db.scalar(
        select(UsageReservationRow).where(
            UsageReservationRow.workspace_id == workspace_id,
            UsageReservationRow.idempotency_key == reservation_key,
        ).with_for_update()
    )
    if existing is not None:
        return existing
    active_reserved = await db.scalar(
        select(func.coalesce(func.sum(UsageReservationRow.declared_seconds - UsageReservationRow.committed_seconds), 0)).where(
            UsageReservationRow.workspace_id == workspace_id,
            UsageReservationRow.window_id == window.id,
            UsageReservationRow.state == "active",
            (UsageReservationRow.expires_at.is_(None) | (UsageReservationRow.expires_at > now)),
        )
    )
    # Reconcile the projection while the window row is locked; expired rows
    # are excluded from admission and must not keep the UI showing stale hold.
    window.reserved_seconds = int(active_reserved or 0)
    if window.committed_seconds + int(active_reserved or 0) + declared_seconds > window.included_seconds:
        raise QuotaExceeded("free processing quota is exhausted")
    reservation = UsageReservationRow(
        id=uuid4(),
        workspace_id=workspace_id,
        window_id=window.id,
        idempotency_key=reservation_key,
        declared_seconds=declared_seconds,
        expires_at=expires_at or now + timedelta(minutes=15),
    )
    db.add(reservation)
    window.reserved_seconds += declared_seconds
    await db.flush()
    return reservation


async def release_expired_free_usage(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    now: datetime,
) -> int:
    """Release stale reservations and return the number of released rows."""
    rows = list(
        await db.scalars(
            select(UsageReservationRow)
            .where(
                UsageReservationRow.workspace_id == workspace_id,
                UsageReservationRow.state == "active",
                UsageReservationRow.expires_at.is_not(None),
                UsageReservationRow.expires_at <= now,
            )
            .with_for_update()
        )
    )
    for reservation in rows:
        reservation.state = "released"
        window = await db.scalar(
            select(FreeUsageWindow).where(FreeUsageWindow.id == reservation.window_id).with_for_update()
        )
        if window is not None:
            window.reserved_seconds = max(
                0,
                window.reserved_seconds
                - max(0, reservation.declared_seconds - reservation.committed_seconds),
            )
    await db.flush()
    return len(rows)


async def release_free_usage(
    db: AsyncSession,
    *,
    reservation_id: UUID,
) -> bool:
    """Release an active reservation without changing committed usage."""
    reservation = await db.scalar(
        select(UsageReservationRow).where(UsageReservationRow.id == reservation_id).with_for_update()
    )
    if reservation is None or reservation.state != "active":
        return False
    reservation.state = "released"
    window = await db.scalar(
        select(FreeUsageWindow).where(FreeUsageWindow.id == reservation.window_id).with_for_update()
    )
    if window is not None:
        window.reserved_seconds = max(
            0,
            window.reserved_seconds
            - max(0, reservation.declared_seconds - reservation.committed_seconds),
        )
    await db.flush()
    return True


def _subtract_source_range(
    candidate: SourceRange,
    existing: list[tuple[int, int]],
) -> list[SourceRange]:
    """Return candidate portions not already committed for the same source."""
    cursor = candidate.start_second
    segments: list[SourceRange] = []
    for start, end in sorted(existing):
        if end <= cursor:
            continue
        if start >= candidate.end_second:
            break
        if start > cursor:
            segments.append(SourceRange(candidate.source_id, cursor, min(start, candidate.end_second)))
        cursor = max(cursor, end)
        if cursor >= candidate.end_second:
            break
    if cursor < candidate.end_second:
        segments.append(SourceRange(candidate.source_id, cursor, candidate.end_second))
    return segments


async def commit_free_usage_ranges(
    db: AsyncSession,
    *,
    reservation_id: UUID,
    ranges: list[SourceRange],
) -> int:
    """Append only new source ranges and reject a reservation overrun."""
    reservation = await db.scalar(select(UsageReservationRow).where(UsageReservationRow.id == reservation_id).with_for_update())
    if reservation is None or reservation.state != "active":
        raise ValueError("usage reservation is not active")
    window = await db.scalar(select(FreeUsageWindow).where(FreeUsageWindow.id == reservation.window_id).with_for_update())
    if window is None:
        raise ValueError("usage window is missing")
    existing_rows = await db.scalars(
        select(UsageLedgerEntry).where(
            UsageLedgerEntry.workspace_id == reservation.workspace_id,
            UsageLedgerEntry.source_id.in_([item.source_id for item in ranges]),
        )
    )
    intervals: dict[str, list[tuple[int, int]]] = {}
    for row in existing_rows:
        intervals.setdefault(row.source_id, []).append((row.start_second, row.end_second))
    unique: list[SourceRange] = []
    for item in ranges:
        portions = _subtract_source_range(item, intervals.get(item.source_id, []))
        unique.extend(portions)
        intervals.setdefault(item.source_id, []).extend((part.start_second, part.end_second) for part in portions)
    accepted = sum(item.seconds for item in unique)
    if accepted > reservation.declared_seconds - reservation.committed_seconds:
        raise QuotaOverrun("accepted source range exceeds its reservation")
    for item in unique:
        db.add(
            UsageLedgerEntry(
                id=uuid4(),
                workspace_id=reservation.workspace_id,
                reservation_id=reservation.id,
                source_id=item.source_id,
                start_second=item.start_second,
                end_second=item.end_second,
                committed_seconds=item.seconds,
            )
        )
    reservation.committed_seconds += accepted
    window.committed_seconds += accepted
    if reservation.committed_seconds == reservation.declared_seconds:
        reservation.state = "committed"
    window.reserved_seconds = max(
        0,
        window.reserved_seconds - accepted,
    )
    await db.flush()
    return accepted
