from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from twobrain_rec_server.billing.catalog import ADDON_CAPACITY_BYTES, storage_capacity_bytes


@dataclass(frozen=True, slots=True)
class StorageAddon:
    capacity_bytes: int
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True, slots=True)
class StorageAddonQuote:
    """Immutable quote for one total-capacity, co-termed selection."""

    capacity_bytes: int
    amount_minor: int
    starts_at: datetime
    ends_at: datetime
    deferred_to_renewal: bool = False


def _utc(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("storage add-on time must be timezone-aware")
    return moment.astimezone(UTC)


def choose_storage_addon(*, capacity_bytes: int, starts_at: datetime, ends_at: datetime) -> StorageAddon:
    if capacity_bytes not in ADDON_CAPACITY_BYTES:
        raise ValueError("unsupported storage add-on")
    if ends_at <= starts_at:
        raise ValueError("storage add-on period is invalid")
    return StorageAddon(capacity_bytes, _utc(starts_at), _utc(ends_at))


def quote_storage_addon_upgrade(
    *,
    current_capacity_bytes: int,
    target_capacity_bytes: int,
    current_period_price_minor: int,
    target_period_price_minor: int,
    paid_from: datetime,
    paid_through: datetime,
    now: datetime,
    provider_floor_minor: int,
    bonus_interval: bool = False,
) -> StorageAddonQuote:
    """Calculate the sole approved positive mid-cycle pro-rata upgrade.

    Downgrades/removals and upgrades during a zero-money bonus interval are
    intentionally deferred to the next paid renewal.  No rounding up and no
    second add-on is created here.
    """
    if target_capacity_bytes not in ADDON_CAPACITY_BYTES:
        raise ValueError("unsupported storage add-on")
    if current_capacity_bytes >= target_capacity_bytes:
        raise ValueError("storage add-on must increase total capacity")
    if current_period_price_minor < 0 or target_period_price_minor <= current_period_price_minor:
        raise ValueError("storage add-on price transition is invalid")
    if provider_floor_minor <= 0:
        raise ValueError("provider floor is invalid")
    start = _utc(paid_from)
    end = _utc(paid_through)
    current = _utc(now)
    if end <= start or current >= end:
        raise ValueError("paid interval is not active")
    if current < start:
        current = start
    if bonus_interval:
        return StorageAddonQuote(target_capacity_bytes, 0, end, end, deferred_to_renewal=True)
    full_microseconds = (end - start).days * 86_400_000_000 + (end - start).seconds * 1_000_000 + (end - start).microseconds
    remaining = end - current
    remaining_microseconds = remaining.days * 86_400_000_000 + remaining.seconds * 1_000_000 + remaining.microseconds
    amount = (target_period_price_minor - current_period_price_minor) * remaining_microseconds // full_microseconds
    if amount < provider_floor_minor:
        return StorageAddonQuote(target_capacity_bytes, 0, end, end, deferred_to_renewal=True)
    return StorageAddonQuote(target_capacity_bytes, amount, current, end)


def effective_storage_capacity(*, plan_code: str, addon: StorageAddon | None) -> int:
    return storage_capacity_bytes(plan_code, addon.capacity_bytes if addon else None)  # type: ignore[arg-type]
