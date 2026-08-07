from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

TRIAL_DAYS = 7


@dataclass(frozen=True, slots=True)
class TrialWindow:
    user_id: UUID
    starts_at: datetime
    ends_at: datetime
    policy_version: str

    @property
    def active(self) -> bool:
        return datetime.now(UTC) < self.ends_at


def activate_trial(*, user_id: UUID, now: datetime, policy_version: str, verified: bool, eligible: bool) -> TrialWindow:
    if not verified:
        raise PermissionError("verified identity is required")
    if not eligible:
        raise ValueError("trial is already used")
    start = now.astimezone(UTC)
    return TrialWindow(user_id, start, start + timedelta(days=TRIAL_DAYS), policy_version)


def trial_plan_at(*, now: datetime, trial: TrialWindow | None) -> str:
    return "trial" if trial is not None and trial.starts_at <= now.astimezone(UTC) < trial.ends_at else "free"
