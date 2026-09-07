from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.admin_grants import AccessResolution
from twobrain_rec_server.billing.catalog import FREE_PROCESSING_SECONDS, classify_free_processing
from twobrain_rec_server.billing.entitlements import resolve_entitlements
from twobrain_rec_server.db.models import (
    FreeUsageWindow,
    UsageLedgerEntry,
    UsageQuotaAllocation,
    Workspace,
)
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


async def reserve_processing_usage(
    db: AsyncSession, *, workspace_id: UUID, reservation_key: str,
    declared_seconds: int, now: datetime, expires_at: datetime | None = None,
    subject_user_id: UUID | None = None, hard_denies: frozenset[str] = frozenset(),
) -> UsageReservationRow:
    """Shared commercial admission; callers still enforce capture/security policy."""
    await db.scalar(select(Workspace.id).where(Workspace.id == workspace_id).with_for_update().execution_options(populate_existing=True))
    access = await resolve_entitlements(
        db, workspace_id=workspace_id, subject_user_id=subject_user_id, now=now,
        hard_denies=hard_denies,
    )
    if "processing_seconds" in access.denied_features:
        raise QuotaExceeded("processing is restricted")
    return await reserve_free_usage(
        db, workspace_id=workspace_id, reservation_key=reservation_key,
        declared_seconds=declared_seconds, now=now, expires_at=expires_at, _access=access,
    )


@dataclass(frozen=True, slots=True)
class QuotaBalance:
    source_id: UUID | None
    limit: int | None
    used: int
    reserved: int
    expires_at: datetime

    @property
    def available(self) -> int | None:
        return None if self.limit is None else max(0, self.limit-self.used-self.reserved)


@dataclass(frozen=True, slots=True)
class ProcessingUsageProjection:
    window_start: datetime
    window_end: datetime
    used: int
    reserved: int
    sources: tuple[QuotaBalance, ...]
    freshness_state: str

    @property
    def available(self) -> int | None:
        if any(source.limit is None for source in self.sources):
            return None
        return sum(source.available for source in self.sources)

    @property
    def limit(self) -> int | None:
        if any(source.limit is None for source in self.sources):
            return None
        return sum(source.limit for source in self.sources)


async def _quota_balances(
    db: AsyncSession, *, workspace_id: UUID, window: FreeUsageWindow | None,
    existing: UsageReservationRow | None, now: datetime,
    active_reserved: int, access: AccessResolution | None,
) -> tuple[QuotaBalance, ...]:
    allocation = UsageQuotaAllocation
    active = (
        (UsageReservationRow.state == "active")
        & (UsageReservationRow.expires_at.is_(None) | (UsageReservationRow.expires_at > now))
    )
    if existing is not None:
        active &= UsageReservationRow.id != existing.id
    held = case((active, allocation.allocated_seconds-allocation.committed_seconds), else_=0)
    window_id = window.id if window else None
    extras = [source for source in access.extra_quotas if source.feature_key == "processing_seconds"] if access else []
    stats = (await db.execute(
        select(
            allocation.adjustment_id, func.sum(allocation.committed_seconds), func.sum(held),
            func.sum(case((allocation.window_id == window_id, allocation.committed_seconds), else_=0)),
            func.sum(case((allocation.window_id == window_id, held), else_=0)),
        )
        .join(UsageReservationRow, UsageReservationRow.id == allocation.reservation_id)
        .where(
            allocation.workspace_id == workspace_id, allocation.adjustment_id.is_not(None),
            (allocation.window_id == window_id) | allocation.adjustment_id.in_([source.id for source in extras]),
        ).group_by(allocation.adjustment_id)
    )).all()
    used = {row[0]: (int(row[1]), int(row[2])) for row in stats}
    base_used = max(0, (window.committed_seconds if window else 0) - sum(int(row[3]) for row in stats))
    base_reserved = max(0, active_reserved - sum(int(row[4]) for row in stats))
    ceiling = access.capabilities["processing_seconds"] if access else (window.included_seconds if window else FREE_PROCESSING_SECONDS)
    if access and access.capabilities["processing_unlimited"]:
        ceiling = None
    sources = [QuotaBalance(None, ceiling, base_used, base_reserved, window.window_end if window else moscow_window_for(now)[1])]
    for source in extras:
        consumed, reserved = used.get(source.id, (0, 0))
        sources.append(QuotaBalance(source.id, source.value, consumed, reserved, source.expires_at))
    return tuple(sources)


async def processing_usage_projection(
    db: AsyncSession, *, workspace_id: UUID, now: datetime, access: AccessResolution,
) -> ProcessingUsageProjection:
    """Read balances without renewing or clearing holds.

    Hold the workspace row lock before resolving access for a coherent projection.
    """
    start, end = moscow_window_for(now)
    window = await db.scalar(select(FreeUsageWindow).where(
        FreeUsageWindow.workspace_id == workspace_id, FreeUsageWindow.window_start == start,
    ).execution_options(populate_existing=True))
    reserved = int(await db.scalar(select(func.coalesce(func.sum(
        UsageReservationRow.declared_seconds-UsageReservationRow.committed_seconds,
    ), 0)).where(
        UsageReservationRow.workspace_id == workspace_id,
        UsageReservationRow.window_id == (window.id if window else None),
        UsageReservationRow.state == "active",
        UsageReservationRow.expires_at.is_(None) | (UsageReservationRow.expires_at > now),
    )) or 0)
    sources = await _quota_balances(db, workspace_id=workspace_id, window=window,
        existing=None, now=now, active_reserved=reserved, access=access)
    return ProcessingUsageProjection(start, end, window.committed_seconds if window else 0,
        reserved, sources, window.freshness_state if window else "fresh")


async def _quota_allocation(
    db: AsyncSession, *, workspace_id: UUID, window: FreeUsageWindow,
    existing: UsageReservationRow | None, now: datetime, remaining: int,
    active_reserved: int, access: AccessResolution | None,
) -> list[tuple[UUID | None, int]]:
    sources = await _quota_balances(db, workspace_id=workspace_id, window=window,
        existing=existing, now=now, active_reserved=active_reserved, access=access)
    result = []
    for source in sources:
        amount = remaining if source.available is None else min(remaining, source.available)
        if amount:
            result.append((source.source_id, amount))
            remaining -= amount
    if remaining:
        raise QuotaExceeded("processing quota is exhausted")
    return result


async def _save_allocations(
    db: AsyncSession, reservation: UsageReservationRow, sources: list[tuple[UUID | None, int]],
) -> None:
    rows = list(await db.scalars(select(UsageQuotaAllocation).where(
        UsageQuotaAllocation.reservation_id == reservation.id,
    ).with_for_update().execution_options(populate_existing=True)))
    for row in rows:
        row.allocated_seconds = row.committed_seconds
    by_source = {(row.window_id,row.source_key): row for row in rows}
    for priority, (source, amount) in enumerate(sources):
        key = str(source) if source else "base"
        row = by_source.get((reservation.window_id,key))
        if row is None:
            row = UsageQuotaAllocation(
                workspace_id=reservation.workspace_id, reservation_id=reservation.id,
                window_id=reservation.window_id, source_key=key, adjustment_id=source,
                allocated_seconds=0, committed_seconds=0,
            )
            db.add(row)
        row.priority = priority
        row.allocated_seconds += amount
    await db.flush()


async def reserve_free_usage(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    reservation_key: str,
    declared_seconds: int,
    now: datetime,
    expires_at: datetime | None = None,
    _access: AccessResolution | None = None,
) -> UsageReservationRow:
    """Reserve exact seconds in the Moscow calendar window under a row lock."""
    if type(declared_seconds) is not int or not 0 < declared_seconds <= 9_000_000_000_000_000 or not reservation_key.strip():
        raise ValueError("usage reservation is invalid")
    # Serialize admission and first-window creation per workspace. The unique
    # keys alone would turn concurrent first use into an IntegrityError.
    await db.scalar(select(Workspace).where(Workspace.id == workspace_id).with_for_update().execution_options(populate_existing=True))
    existing = await db.scalar(
        select(UsageReservationRow).where(
            UsageReservationRow.workspace_id == workspace_id,
            UsageReservationRow.idempotency_key == reservation_key,
        ).with_for_update().execution_options(populate_existing=True)
    )
    if existing is not None and existing.declared_seconds != declared_seconds:
        raise ValueError("usage idempotency conflict")
    if existing is not None and existing.state == "committed":
        return existing
    if (
        _access is not None and existing is not None and existing.state == "active"
        and (existing.expires_at is None or _as_utc(existing.expires_at) > now)
    ):
        if expires_at is not None and existing.expires_at is not None and expires_at > existing.expires_at:
            existing.expires_at = expires_at
            await db.flush()
        return existing
    window_start, window_end = moscow_window_for(now)
    window = await db.scalar(
        select(FreeUsageWindow)
        .where(
            FreeUsageWindow.workspace_id == workspace_id,
            FreeUsageWindow.window_start == window_start,
        )
        .with_for_update().execution_options(populate_existing=True)
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
    if existing is not None:
        if (
            existing.window_id == window.id
            and existing.state == "active"
            and (existing.expires_at is None or _as_utc(existing.expires_at) > now)
        ):
            if (
                existing.state == "active"
                and expires_at is not None
                and existing.expires_at is not None
                and _as_utc(existing.expires_at) < _as_utc(expires_at)
            ):
                existing.expires_at = expires_at
                await db.flush()
            return existing
        remaining = max(0, existing.declared_seconds - existing.committed_seconds)
        if not remaining:
            return existing
    else:
        remaining = declared_seconds
    active_reserved = await db.scalar(
        select(func.coalesce(func.sum(UsageReservationRow.declared_seconds - UsageReservationRow.committed_seconds), 0)).where(
            UsageReservationRow.workspace_id == workspace_id,
            UsageReservationRow.window_id == window.id,
            UsageReservationRow.state == "active",
            (UsageReservationRow.expires_at.is_(None) | (UsageReservationRow.expires_at > now)),
            *((UsageReservationRow.id != existing.id,) if existing is not None else ()),
        )
    )
    sources = await _quota_allocation(
        db, workspace_id=workspace_id, window=window, existing=existing, now=now,
        remaining=remaining, active_reserved=int(active_reserved or 0), access=_access,
    )
    if _access is not None:
        window.included_seconds = _access.capabilities["processing_seconds"]
    # Reconcile only after admission succeeds, so a rejected reservation leaves
    # the caller's surrounding transaction and loaded lifecycle rows intact.
    window.reserved_seconds = int(active_reserved or 0)
    if existing is not None:
        if existing.window_id != window.id:
            previous_window = await db.scalar(
                select(FreeUsageWindow)
                .where(
                    FreeUsageWindow.id == existing.window_id,
                    FreeUsageWindow.workspace_id == workspace_id,
                )
                .with_for_update().execution_options(populate_existing=True)
            )
            if previous_window is not None:
                previous_reserved = await db.scalar(
                    select(
                        func.coalesce(
                            func.sum(
                                UsageReservationRow.declared_seconds
                                - UsageReservationRow.committed_seconds
                            ),
                            0,
                        )
                    ).where(
                        UsageReservationRow.workspace_id == workspace_id,
                        UsageReservationRow.window_id == previous_window.id,
                        UsageReservationRow.state == "active",
                        (
                            UsageReservationRow.expires_at.is_(None)
                            | (UsageReservationRow.expires_at > now)
                        ),
                        UsageReservationRow.id != existing.id,
                    )
                )
                previous_window.reserved_seconds = int(previous_reserved or 0)
            existing.window_id = window.id
        existing.state = "active"
        existing.expires_at = expires_at or now + timedelta(minutes=15)
        window.reserved_seconds += remaining
        await db.flush()
        await _save_allocations(db, existing, sources)
        return existing
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
    await _save_allocations(db, reservation, sources)
    return reservation


async def _lock_reservation_workspace(db: AsyncSession, reservation_id: UUID) -> None:
    workspace_id = await db.scalar(select(UsageReservationRow.workspace_id).where(
        UsageReservationRow.id == reservation_id,
    ))
    if workspace_id is not None:
        await db.scalar(select(Workspace.id).where(Workspace.id == workspace_id).with_for_update().execution_options(populate_existing=True))


async def _refresh_reserved_projection(db: AsyncSession, *, window_id: UUID, now: datetime) -> None:
    # Expired holds may already be excluded by a later admission. Subtracting them
    # again would erase another operation's live reservation from the projection.
    await db.flush()
    window = await db.scalar(select(FreeUsageWindow).where(FreeUsageWindow.id == window_id).with_for_update().execution_options(populate_existing=True))
    if window is not None:
        window.reserved_seconds = int(await db.scalar(select(func.coalesce(func.sum(
            UsageReservationRow.declared_seconds-UsageReservationRow.committed_seconds,
        ),0)).where(
            UsageReservationRow.window_id == window_id, UsageReservationRow.state == "active",
            UsageReservationRow.expires_at.is_(None) | (UsageReservationRow.expires_at > now),
        )) or 0)
        await db.flush()


async def release_expired_free_usage(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    now: datetime,
) -> int:
    """Release stale reservations and return the number of released rows."""
    await db.scalar(select(Workspace.id).where(Workspace.id == workspace_id).with_for_update().execution_options(populate_existing=True))
    rows = list(
        await db.scalars(
            select(UsageReservationRow)
            .where(
                UsageReservationRow.workspace_id == workspace_id,
                UsageReservationRow.state == "active",
                UsageReservationRow.expires_at.is_not(None),
                UsageReservationRow.expires_at <= now,
            )
            .with_for_update().execution_options(populate_existing=True)
        )
    )
    for reservation in rows:
        reservation.state = "released"
    for window_id in sorted({row.window_id for row in rows}):
        await _refresh_reserved_projection(db, window_id=window_id, now=now)
    return len(rows)


async def release_free_usage(
    db: AsyncSession,
    *,
    reservation_id: UUID,
) -> bool:
    """Release an active reservation without changing committed usage."""
    await _lock_reservation_workspace(db, reservation_id)
    reservation = await db.scalar(
        select(UsageReservationRow).where(UsageReservationRow.id == reservation_id).with_for_update().execution_options(populate_existing=True)
    )
    if reservation is None or reservation.state != "active":
        return False
    reservation.state = "released"
    await _refresh_reserved_projection(db, window_id=reservation.window_id, now=datetime.now(UTC))
    return True


async def find_free_usage_reservation(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    reservation_key: str,
) -> UsageReservationRow | None:
    """Find one processing reservation without exposing provider/content data."""
    await db.scalar(select(Workspace.id).where(Workspace.id == workspace_id).with_for_update().execution_options(populate_existing=True))
    return await db.scalar(
        select(UsageReservationRow)
        .where(
            UsageReservationRow.workspace_id == workspace_id,
            UsageReservationRow.idempotency_key == reservation_key,
        )
        .with_for_update().execution_options(populate_existing=True)
    )


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


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def commit_free_usage_ranges(
    db: AsyncSession,
    *,
    reservation_id: UUID,
    ranges: list[SourceRange],
) -> int:
    """Append only new source ranges and reject a reservation overrun."""
    await _lock_reservation_workspace(db, reservation_id)
    reservation = await db.scalar(select(UsageReservationRow).where(UsageReservationRow.id == reservation_id).with_for_update().execution_options(populate_existing=True))
    if reservation is None or reservation.state != "active":
        raise ValueError("usage reservation is not active")
    if reservation.expires_at is not None and _as_utc(reservation.expires_at) <= datetime.now(UTC):
        # A worker retry must not commit against an expired hold. Release the
        # remaining projection while the reservation row is already locked.
        reservation.state = "released"
        await _refresh_reserved_projection(db, window_id=reservation.window_id, now=datetime.now(UTC))
        raise ValueError("usage reservation has expired")
    window = await db.scalar(select(FreeUsageWindow).where(FreeUsageWindow.id == reservation.window_id).with_for_update().execution_options(populate_existing=True))
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
    allocations = list(await db.scalars(select(UsageQuotaAllocation).where(
        UsageQuotaAllocation.reservation_id == reservation.id,
        UsageQuotaAllocation.window_id == reservation.window_id,
    ).order_by(UsageQuotaAllocation.priority, UsageQuotaAllocation.id).with_for_update().execution_options(populate_existing=True)))
    # Legacy fixtures/rows may predate allocation backfill; their entire hold is base usage.
    if allocations:
        if sum(row.allocated_seconds-row.committed_seconds for row in allocations) < accepted:
            raise QuotaOverrun("usage allocation does not cover accepted ranges")
        remaining = accepted
        for allocation in allocations:
            amount = min(remaining, allocation.allocated_seconds-allocation.committed_seconds)
            allocation.committed_seconds += amount
            remaining -= amount
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
    await _refresh_reserved_projection(db, window_id=window.id, now=datetime.now(UTC))
    return accepted
