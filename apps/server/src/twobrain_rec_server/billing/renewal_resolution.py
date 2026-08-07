"""Deterministic renewal outcome projection at the paid-through boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class RenewalResolution(StrEnum):
    ACTIVE = "active"
    UNKNOWN_PENDING = "unknown_pending"
    FINAL_FAILURE = "final_failure"
    LATE_SUCCESS_RESTORED = "late_success_restored"
    LATE_SUCCESS_REFUSED = "late_success_refused"
    MANUAL_RESUME_REQUIRED = "manual_resume_required"


@dataclass(frozen=True, slots=True)
class RenewalDecision:
    resolution: RenewalResolution
    plan_code: str
    manual_resume_allowed: bool
    incident_required: bool
    support_notice_required: bool


def resolve_renewal_resolution(
    *,
    now: datetime,
    paid_through: datetime,
    provider_status: str | None,
    effective_refusal: bool = False,
    account_close: bool = False,
    provider_key_expired: bool = False,
) -> RenewalDecision:
    """Resolve renewal without grace, retry or a second provider mutation.

    ``unknown`` remains a blocked resolution while the key can still be
    observed. Once the key expires it becomes a final Free projection and the
    user may manually resume with fresh consent. A late success after refusal
    never restores access and is an internal incident only.
    """
    current = _utc(now)
    cutoff = _utc(paid_through)
    status = provider_status.strip().lower() if isinstance(provider_status, str) else None
    refused = effective_refusal or account_close
    if current < cutoff:
        return RenewalDecision(RenewalResolution.ACTIVE, "personal", False, False, False)
    if status in {"succeeded", "paid"}:
        if refused:
            return RenewalDecision(
                RenewalResolution.LATE_SUCCESS_REFUSED,
                "free",
                False,
                True,
                True,
            )
        return RenewalDecision(
            RenewalResolution.LATE_SUCCESS_RESTORED,
            "personal",
            False,
            False,
            False,
        )
    if status in {"unknown", None} and not provider_key_expired:
        return RenewalDecision(RenewalResolution.UNKNOWN_PENDING, "free", False, False, False)
    if status in {"canceled", "cancelled", "declined", "failed"} or provider_key_expired:
        return RenewalDecision(RenewalResolution.MANUAL_RESUME_REQUIRED, "free", True, False, False)
    return RenewalDecision(RenewalResolution.FINAL_FAILURE, "free", True, False, False)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
