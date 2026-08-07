from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from twobrain_rec_server.billing.catalog import ADDON_CAPACITY_BYTES, storage_capacity_bytes


@dataclass(frozen=True, slots=True)
class StorageAddon:
    capacity_bytes: int
    starts_at: datetime
    ends_at: datetime


def choose_storage_addon(*, capacity_bytes: int, starts_at: datetime, ends_at: datetime) -> StorageAddon:
    if capacity_bytes not in ADDON_CAPACITY_BYTES:
        raise ValueError("unsupported storage add-on")
    if ends_at <= starts_at:
        raise ValueError("storage add-on period is invalid")
    return StorageAddon(capacity_bytes, starts_at, ends_at)


def effective_storage_capacity(*, plan_code: str, addon: StorageAddon | None) -> int:
    return storage_capacity_bytes(plan_code, addon.capacity_bytes if addon else None)  # type: ignore[arg-type]
