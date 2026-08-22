from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from twobrain_rec_server.db.models.billing import BillingPlanVersion

PlanCode = Literal["free", "trial", "personal"]
CatalogCycle = Literal["none", "month", "year"]

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


class CatalogNotApproved(ValueError):
    """The immutable server catalog cannot be used for a new checkout."""

    code = "catalog_not_approved"


@dataclass(frozen=True, slots=True)
class PlanDescriptor:
    code: PlanCode
    label: str
    storage_bytes: int
    processing_mode: Literal["quota", "unlimited"]
    monthly_amount_minor: int | None = None
    annual_amount_minor: int | None = None


@dataclass(frozen=True, slots=True)
class PlanCatalogSnapshot:
    """Validated, immutable catalog values copied into a checkout/invoice.

    ``BillingPlanVersion`` is the database authority.  This bounded value
    object prevents a provider request from consulting mutable catalog rows
    after an invoice has been created and keeps the raw ORM object out of
    request snapshots.
    """

    plan_code: PlanCode
    version: int
    cycle: CatalogCycle
    amount_minor: int | None
    currency: str
    storage_bytes: int
    processing_mode: Literal["quota", "unlimited"]
    offer_version: str
    policy_snapshot: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        """Return the only catalog fields allowed in a financial snapshot."""

        return {
            "plan_code": self.plan_code,
            "catalog_version": self.version,
            "cycle": self.cycle,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "storage_bytes": self.storage_bytes,
            "processing_mode": self.processing_mode,
            "offer_version": self.offer_version,
            "policy_snapshot": dict(self.policy_snapshot),
        }


def validate_plan_version(
    row: BillingPlanVersion | None,
    *,
    now: datetime | None = None,
) -> PlanCatalogSnapshot:
    """Validate one enabled, time-bounded catalog row for a new checkout.

    Missing, disabled, stale or malformed rows intentionally fail closed.  A
    caller must not silently fall back to ``plan_descriptor`` when the billing
    database is available, otherwise changing an approved price would not
    invalidate a stale checkout path.
    """

    if row is None:
        raise CatalogNotApproved("no approved catalog version")
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("catalog validation time must be timezone-aware")
    if row.plan_code not in {"free", "trial", "personal"}:
        raise CatalogNotApproved("unknown plan code")
    if row.cycle not in {"none", "month", "year"}:
        raise CatalogNotApproved("unknown billing cycle")
    if row.version <= 0 or not row.enabled_for_checkout:
        raise CatalogNotApproved("catalog version is not enabled")
    for boundary_name, boundary in (
        ("effective_from", row.effective_from),
        ("effective_until", row.effective_until),
    ):
        if boundary is not None and boundary.tzinfo is None:
            raise CatalogNotApproved(f"catalog {boundary_name} must be timezone-aware")
    if row.effective_from is not None and current < row.effective_from.astimezone(UTC):
        raise CatalogNotApproved("catalog version is not effective")
    if row.effective_until is not None and current >= row.effective_until.astimezone(UTC):
        raise CatalogNotApproved("catalog version has expired")
    if row.currency != "RUB" or row.storage_bytes <= 0:
        raise CatalogNotApproved("catalog money or storage fields are invalid")
    if row.processing_mode not in {"quota", "unlimited"}:
        raise CatalogNotApproved("catalog entitlement is invalid")
    if row.plan_code == "personal" and row.cycle not in {"month", "year"}:
        raise CatalogNotApproved("personal plan requires a payable cycle")
    if row.plan_code != "personal" and row.amount_minor is not None:
        raise CatalogNotApproved("non-paid plan cannot have a price")
    if row.plan_code == "personal" and (row.amount_minor is None or row.amount_minor <= 0):
        raise CatalogNotApproved("paid plan requires a positive price")
    policy = row.policy_snapshot if isinstance(row.policy_snapshot, dict) else {}
    for key, value in policy.items():
        if not isinstance(key, str) or not key or len(key) > 64:
            raise CatalogNotApproved("catalog policy snapshot is invalid")
        if not isinstance(value, (str, int, bool)) or (isinstance(value, str) and len(value) > 256):
            raise CatalogNotApproved("catalog policy snapshot is not bounded")
    offer_version = policy.get("offer_version")
    if not isinstance(offer_version, str) or not offer_version.strip() or len(offer_version) > 64:
        raise CatalogNotApproved("catalog offer version is missing")
    return PlanCatalogSnapshot(
        plan_code=row.plan_code,  # type: ignore[arg-type]
        version=row.version,
        cycle=row.cycle,  # type: ignore[arg-type]
        amount_minor=row.amount_minor,
        currency=row.currency,
        storage_bytes=row.storage_bytes,
        processing_mode=row.processing_mode,  # type: ignore[arg-type]
        offer_version=offer_version.strip(),
        policy_snapshot=dict(policy),
    )


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
        monthly_amount_minor=100_000,
        annual_amount_minor=1_000_000,
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
