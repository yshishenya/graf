from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PlanCode = Literal["free", "trial", "personal"]

FREE_PROCESSING_SECONDS = 18_000
FREE_STORAGE_BYTES = 250_000_000
TRIAL_STORAGE_BYTES = 500_000_000
PERSONAL_STORAGE_BYTES = 2_000_000_000
ADDON_CAPACITY_BYTES = (
    5_000_000_000,
    20_000_000_000,
    100_000_000_000,
    500_000_000_000,
)


@dataclass(frozen=True, slots=True)
class PlanDescriptor:
    code: PlanCode
    label: str
    storage_bytes: int
    processing_mode: Literal["quota", "unlimited"]
    monthly_amount_minor: int | None = None
    annual_amount_minor: int | None = None


def plan_descriptor(code: PlanCode) -> PlanDescriptor:
    if code == "free":
        return PlanDescriptor("free", "Free", FREE_STORAGE_BYTES, "quota")
    if code == "trial":
        return PlanDescriptor("trial", "Trial Личного", TRIAL_STORAGE_BYTES, "unlimited")
    if code != "personal":
        raise ValueError("unknown plan")
    return PlanDescriptor(
        "personal",
        "Личный",
        PERSONAL_STORAGE_BYTES,
        "unlimited",
        monthly_amount_minor=79_000,
        annual_amount_minor=790_000,
    )


def storage_capacity_bytes(plan: PlanCode, addon_capacity_bytes: int | None = None) -> int:
    """Return the effective capacity; add-ons are total-capacity selections."""
    if addon_capacity_bytes is not None:
        if plan != "personal" or addon_capacity_bytes not in ADDON_CAPACITY_BYTES:
            raise ValueError("storage add-on is available only for an approved personal plan")
        return addon_capacity_bytes
    return plan_descriptor(plan).storage_bytes


def classify_storage_threshold(*, used_bytes: int, capacity_bytes: int) -> str:
    if capacity_bytes <= 0:
        raise ValueError("capacity must be positive")
    ratio = used_bytes / capacity_bytes
    if ratio >= 1:
        return "full"
    if ratio >= 0.95:
        return "95%"
    if ratio >= 0.80:
        return "80%"
    return "normal"


def classify_free_processing(*, committed_seconds: int) -> str:
    if committed_seconds < 0:
        raise ValueError("committed seconds cannot be negative")
    if committed_seconds >= FREE_PROCESSING_SECONDS:
        return "exhausted"
    if committed_seconds >= int(FREE_PROCESSING_SECONDS * 0.8):
        return "approaching"
    return "normal"
