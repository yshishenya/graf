from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.selectable import CTE

from twobrain_rec_server.db.models import TrialActivation, UserIdentity

TRIAL_DAYS = 7


def merged_user_lineage(user_id: UUID) -> CTE:
    """Return the current user and every historical source merged into it."""

    lineage = (
        select(UserIdentity.id.label("user_id"))
        .where(UserIdentity.id == user_id)
        .cte("merged_user_lineage", recursive=True)
    )
    source = aliased(UserIdentity)
    return lineage.union_all(
        select(source.id.label("user_id")).where(
            source.merged_into_user_id == lineage.c.user_id
        )
    )


async def trial_used_by_lineage(db: AsyncSession, *, user_id: UUID) -> bool:
    lineage = merged_user_lineage(user_id)
    used = await db.scalar(
        select(TrialActivation.id)
        .where(TrialActivation.user_id.in_(select(lineage.c.user_id)))
        .limit(1)
    )
    return used is not None


def require_trial_activation(
    *,
    identity_status: str,
    membership_role: str,
    workspace_kind: str,
    already_used: bool,
) -> None:
    """Fail closed before trial state is created or a subscription is changed."""
    if identity_status != "active":
        raise PermissionError("verified identity is required")
    if membership_role != "owner" or workspace_kind != "personal":
        raise PermissionError("personal workspace owner is required")
    if already_used:
        raise ValueError("trial is already used")


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
