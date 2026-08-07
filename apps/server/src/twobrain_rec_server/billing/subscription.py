from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class SubscriptionControl:
    paid_through: datetime
    recurring_allowed: bool
    authority_version: int


def cancel_auto_renewal(control: SubscriptionControl, *, expected_version: int) -> SubscriptionControl:
    if control.authority_version != expected_version:
        raise ValueError("subscription changed; reload and confirm again")
    return SubscriptionControl(control.paid_through, False, control.authority_version + 1)


def resume_auto_renewal(
    control: SubscriptionControl,
    *,
    expected_version: int,
    now: datetime | None = None,
) -> SubscriptionControl:
    if control.authority_version != expected_version:
        raise ValueError("subscription changed; reload and confirm again")
    effective_now = (now or datetime.now(UTC)).astimezone(UTC)
    if control.paid_through is None or control.paid_through.astimezone(UTC) <= effective_now:
        raise ValueError("subscription is no longer active")
    return SubscriptionControl(control.paid_through, True, control.authority_version + 1)


def project_plan(*, now: datetime, paid_through: datetime | None, recurring_allowed: bool) -> str:
    if paid_through is not None and now.astimezone(UTC) < paid_through:
        return "personal"
    return "free"
