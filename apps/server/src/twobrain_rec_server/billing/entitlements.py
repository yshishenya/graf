from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from twobrain_rec_server.billing.catalog import (
    FREE_PROCESSING_SECONDS,
    PlanCode,
    storage_capacity_bytes,
)


@dataclass(frozen=True, slots=True)
class EntitlementSnapshot:
    plan_code: PlanCode
    processing_unlimited: bool
    storage_capacity_bytes: int


def effective_plan_code(
    *,
    plan_code: PlanCode,
    state: str,
    now: datetime,
    paid_through: datetime | None,
    trial_ends_at: datetime | None,
) -> PlanCode:
    """Apply the authoritative cutoff before projecting paid capabilities."""
    current = now.astimezone(UTC)
    if plan_code == "trial":
        return "trial" if trial_ends_at is not None and trial_ends_at.astimezone(UTC) > current else "free"
    if plan_code == "personal":
        return "personal" if paid_through is not None and paid_through.astimezone(UTC) > current else "free"
    return "free" if state not in {"free", "trial", "personal"} else plan_code


def entitlement_for_plan(
    *,
    plan_code: PlanCode,
    storage_addon_bytes: int | None = None,
) -> EntitlementSnapshot:
    return EntitlementSnapshot(
        plan_code=plan_code,
        processing_unlimited=plan_code in {"trial", "personal"},
        storage_capacity_bytes=storage_capacity_bytes(plan_code, storage_addon_bytes),
    )


def processing_admission(
    *,
    entitlement: EntitlementSnapshot,
    committed_free_seconds: int,
    accepted_seconds: int,
    save_audio: bool,
) -> tuple[bool, str]:
    """Return a stable reason code; archive choice never blocks paid processing."""
    if accepted_seconds <= 0:
        raise ValueError("accepted seconds must be positive")
    if entitlement.processing_unlimited:
        return True, "paid_unlimited"
    if committed_free_seconds + accepted_seconds > FREE_PROCESSING_SECONDS:
        return (False, "free_processing_exhausted")
    if not save_audio:
        return True, "free_without_audio_archive"
    return True, "free_with_audio_archive"
