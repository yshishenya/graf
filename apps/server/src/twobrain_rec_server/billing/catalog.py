from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from twobrain_rec_server.db.models.billing import BillingPlanPrice, BillingPlanVersion

PlanCode = str
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
    plan_version_id: UUID | None = None
    price_id: UUID | None = None
    capabilities: dict[str, object] | None = None
    display_terms: dict[str, object] | None = None

    def as_dict(self) -> dict[str, object]:
        """Return the only catalog fields allowed in a financial snapshot."""

        result = {
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
        if self.plan_version_id is not None:
            result.update(
                plan_version_id=str(self.plan_version_id),
                price_id=str(self.price_id) if self.price_id else None,
                capability_schema_version=1,
                capabilities=dict(self.capabilities or {}),
                display_terms=dict(self.display_terms or {}),
            )
        return result


def validate_plan_version(
    row: BillingPlanVersion | None,
    *,
    now: datetime | None = None,
    price: BillingPlanPrice | None = None,
    for_checkout: bool = True,
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
    if (
        not isinstance(row.plan_code, str)
        or re.fullmatch(r"[a-z][a-z0-9_]{2,31}", row.plan_code) is None
    ):
        raise CatalogNotApproved("invalid plan code")
    managed = row.status not in (None, "legacy")
    if not managed and row.plan_code not in {"free", "trial", "personal"}:
        raise CatalogNotApproved("legacy plan has no supported capabilities")
    capabilities = validate_capabilities(row.capabilities) if managed else None
    terms = validate_display_terms(row.display_terms) if managed else None
    if managed and (row.capability_schema_version != 1 or row.plan_id is None or row.id is None):
        raise CatalogNotApproved("unsupported capability schema")
    if managed and row.status not in ({"published"} if for_checkout else {"published", "retired"}):
        raise CatalogNotApproved("catalog is not published")
    if price is not None and (price.version_id != row.id or not managed):
        raise CatalogNotApproved("price belongs to another catalog version")
    cycle = price.cycle if price is not None else row.cycle
    amount = price.amount_minor if price is not None else row.amount_minor
    currency = price.currency if price is not None else row.currency
    if managed and cycle != "none" and price is None:
        raise CatalogNotApproved("explicit price required")
    if cycle not in {"none", "month", "year"}:
        raise CatalogNotApproved("unknown billing cycle")
    if type(row.version) is not int or row.version <= 0 or (for_checkout and not row.enabled_for_checkout):
        raise CatalogNotApproved("catalog version is not enabled")
    for boundary_name, boundary in (
        ("effective_from", row.effective_from),
        ("effective_until", row.effective_until),
    ):
        if boundary is not None and boundary.tzinfo is None:
            raise CatalogNotApproved(f"catalog {boundary_name} must be timezone-aware")
    if (
        for_checkout
        and row.effective_from is not None
        and current < row.effective_from.astimezone(UTC)
    ):
        raise CatalogNotApproved("catalog version is not effective")
    if (
        for_checkout
        and row.effective_until is not None
        and current >= row.effective_until.astimezone(UTC)
    ):
        raise CatalogNotApproved("catalog version has expired")
    if currency != "RUB" or type(row.storage_bytes) is not int or row.storage_bytes <= 0:
        raise CatalogNotApproved("catalog money or storage fields are invalid")
    if row.processing_mode not in {"quota", "unlimited"}:
        raise CatalogNotApproved("catalog entitlement is invalid")
    if row.plan_code in {"free", "trial"} and (cycle != "none" or amount is not None):
        raise CatalogNotApproved("reserved plan cannot have a price")
    if cycle in {"month", "year"} and (type(amount) is not int or not 0 < amount <= 9_000_000_000_000_000):
        raise CatalogNotApproved("paid plan requires a positive price")
    if cycle == "none" and (amount is not None or row.plan_code == "personal"):
        raise CatalogNotApproved("invalid non-paid offer")
    if managed and (
        capabilities["storage_bytes"] != row.storage_bytes
        or capabilities["processing_unlimited"] != (row.processing_mode == "unlimited")
    ):
        raise CatalogNotApproved("catalog capability projection mismatch")
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
        cycle=cycle,  # type: ignore[arg-type]
        amount_minor=amount,
        currency=currency,
        storage_bytes=row.storage_bytes,
        processing_mode=row.processing_mode,  # type: ignore[arg-type]
        offer_version=offer_version.strip(),
        policy_snapshot=dict(policy),
        plan_version_id=row.id if managed else None,
        price_id=price.id if price is not None else None,
        capabilities=capabilities,
        display_terms=terms,
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


CAPABILITY_BOOLEANS = frozenset(
    {
        "processing_unlimited",
        "audio_archive",
        "audio_download",
        "content_export",
        "meeting_sharing",
        "ai_summary",
        "ai_outcomes",
    }
)
EXPORT_FORMATS = frozenset({"txt", "md", "csv", "xlsx", "json", "srt", "vtt"})


def validate_capabilities(value: object) -> dict[str, object]:
    """Only implemented capabilities; no expressions, feature names or quota sentinels."""
    keys = CAPABILITY_BOOLEANS | {
        "storage_bytes",
        "processing_seconds",
        "processing_window",
        "export_formats",
    }
    if not isinstance(value, dict) or value.keys() != keys:
        raise CatalogNotApproved("unsupported capability fields")
    if any(type(value[key]) is not bool for key in CAPABILITY_BOOLEANS):
        raise CatalogNotApproved("capability flags must be booleans")
    for key, minimum in (("storage_bytes", 1), ("processing_seconds", 0)):
        if type(value[key]) is not int or not minimum <= value[key] <= 9_000_000_000_000_000:
            raise CatalogNotApproved("invalid capability limit")
    if value["processing_window"] != "calendar_month_moscow":
        raise CatalogNotApproved("unsupported quota window")
    formats = value["export_formats"]
    if not isinstance(formats, list) or any(not isinstance(item, str) for item in formats):
        raise CatalogNotApproved("invalid export formats")
    if len(formats) != len(set(formats)) or not set(formats) <= EXPORT_FORMATS:
        raise CatalogNotApproved("unsupported export formats")
    if bool(formats) != value["content_export"]:
        raise CatalogNotApproved("export capability and formats disagree")
    return {**value, "export_formats": sorted(formats)}


def validate_display_terms(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or value.keys() != {
        "name",
        "description",
        "audience",
        "trial_days",
    }:
        raise CatalogNotApproved("invalid display terms")
    for key, minimum, maximum in (("name", 1, 80), ("description", 0, 500)):
        if not isinstance(value[key], str) or not minimum <= len(value[key].strip()) <= maximum:
            raise CatalogNotApproved("invalid offer text")
    if value["audience"] not in ("public", "invitation", "admin"):
        raise CatalogNotApproved("invalid offer audience")
    if type(value["trial_days"]) is not int or not 0 <= value["trial_days"] <= 365:
        raise CatalogNotApproved("invalid trial duration")
    return dict(value)
