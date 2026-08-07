from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.referrals import (
    ReferralReward,
    first_payment_reward,
    grantable_days,
)
from twobrain_rec_server.db.models import (
    ReferralAttribution,
    TimeCreditLedgerEntry,
    WorkspaceSubscription,
)


@dataclass(frozen=True, slots=True)
class TimeCredit:
    source_ref: str
    days: int
    state: str = "pending"


def mature_credit(*, reward: ReferralReward, source_ref: str, granted_rolling_days: int, now: datetime) -> TimeCredit | None:
    days = grantable_days(reward=reward, granted_rolling_days=granted_rolling_days, now=now)
    return TimeCredit(source_ref, days, "matured") if days else None


def payment_source_ref(provider_payment_id: str) -> str:
    if not provider_payment_id or len(provider_payment_id) > 160 or not all(
        char.isascii() and (char.isalnum() or char in "-_.") for char in provider_payment_id
    ):
        raise ValueError("provider payment id is invalid")
    return f"referral:payment:{provider_payment_id}"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("referral time must be timezone-aware")
    return value.astimezone(UTC)


async def create_pending_credit(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    invitee_user_id: UUID,
    provider_payment_id: str,
    paid_at: datetime,
    cycle: str,
) -> Literal["created", "duplicate", "ineligible"]:
    """Record the first paid referral reward; no service time is granted yet."""
    source_ref = payment_source_ref(provider_payment_id)
    attribution = await db.scalar(
        select(ReferralAttribution).where(
            ReferralAttribution.invitee_user_id == invitee_user_id,
            ReferralAttribution.state.in_(("bound", "registered", "attributed")),
        ).with_for_update()
    )
    if attribution is None or attribution.inviter_user_id == invitee_user_id:
        return "ineligible"
    reward_workspace_id = attribution.workspace_id
    existing = await db.scalar(
        select(TimeCreditLedgerEntry).where(
            TimeCreditLedgerEntry.workspace_id == reward_workspace_id,
            TimeCreditLedgerEntry.source_ref == source_ref,
        ).with_for_update()
    )
    if existing is not None:
        return "duplicate"
    reward = first_payment_reward(paid_at=_utc(paid_at), cycle=cycle)
    db.add(
        TimeCreditLedgerEntry(
            workspace_id=reward_workspace_id,
            source_ref=source_ref,
            days=reward.inviter_days,
            state="pending",
            maturity_at=reward.maturity_at,
            expires_at=reward.expires_at,
        )
    )
    attribution.state = "pending_maturity"
    await db.flush()
    return "created"


async def mature_pending_credits(db: AsyncSession, *, now: datetime, rolling_days: int = 0) -> int:
    """Apply matured credits contiguously after the current paid/bonus period."""
    current = _utc(now)
    rows = await db.scalars(
        select(TimeCreditLedgerEntry)
        .where(
            TimeCreditLedgerEntry.state == "pending",
            TimeCreditLedgerEntry.maturity_at <= current,
        )
        .order_by(TimeCreditLedgerEntry.maturity_at, TimeCreditLedgerEntry.created_at)
        .with_for_update()
    )
    total_applied = 0
    for row in rows:
        if current >= row.expires_at:
            row.state = "expired"
            continue
        window_start = current - timedelta(days=365)
        already_granted = await db.scalar(
            select(func.coalesce(func.sum(TimeCreditLedgerEntry.days), 0))
            .where(
                TimeCreditLedgerEntry.workspace_id == row.workspace_id,
                TimeCreditLedgerEntry.state == "applied",
                TimeCreditLedgerEntry.maturity_at >= window_start,
                TimeCreditLedgerEntry.maturity_at <= current,
            )
        )
        granted = int(already_granted or 0) + rolling_days
        days = min(max(0, row.days), max(0, 180 - granted))
        if days <= 0:
            row.state = "rejected"
            continue
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == row.workspace_id).with_for_update()
        )
        if subscription is None:
            row.state = "rejected"
            continue
        start = subscription.paid_through.astimezone(UTC) if subscription.paid_through and subscription.paid_through > current else current
        row.days = days
        row.state = "applied"
        row.applied_start = start
        row.applied_end = start + timedelta(days=days)
        subscription.paid_through = row.applied_end
        subscription.application_version = (subscription.application_version or 0) + 1
        total_applied += days
    await db.flush()
    return total_applied


async def reverse_credit_for_payment(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    provider_payment_id: str,
    now: datetime,
    invitee_user_id: UUID | None = None,
) -> Literal["reversed", "duplicate", "none"]:
    """Create a bounded append-only reversal from observed provider refund truth."""
    source_ref = payment_source_ref(provider_payment_id)
    ledger_workspace_id = workspace_id
    if invitee_user_id is not None:
        attribution = await db.scalar(
            select(ReferralAttribution).where(
                ReferralAttribution.invitee_user_id == invitee_user_id,
                ReferralAttribution.state.in_(("pending_maturity", "applied")),
            ).with_for_update()
        )
        if attribution is not None:
            ledger_workspace_id = attribution.workspace_id
    row = await db.scalar(
        select(TimeCreditLedgerEntry).where(
            TimeCreditLedgerEntry.workspace_id == ledger_workspace_id,
            TimeCreditLedgerEntry.source_ref == source_ref,
        ).with_for_update()
    )
    if row is None or row.state in {"reversed", "rejected", "expired"}:
        return "none"
    if row.state == "pending":
        row.state = "reversed"
        await db.flush()
        return "reversed"
    reversal_ref = f"{source_ref}:reversal"
    existing = await db.scalar(
        select(TimeCreditLedgerEntry).where(
            TimeCreditLedgerEntry.workspace_id == ledger_workspace_id,
            TimeCreditLedgerEntry.source_ref == reversal_ref,
        ).with_for_update()
    )
    if existing is not None:
        return "duplicate"
    reversal = TimeCreditLedgerEntry(
        workspace_id=ledger_workspace_id,
        source_ref=reversal_ref,
        days=-row.days,
        state="reversed",
        maturity_at=_utc(now),
        expires_at=_utc(now),
        applied_start=row.applied_start,
        applied_end=row.applied_end,
        reversal_of_id=row.id,
    )
    db.add(reversal)
    row.state = "reversed"
    # Never touch the paid base interval. Only remove an unconsumed tail that
    # still exactly ends at this credit's interval.
    subscription = await db.scalar(
        select(WorkspaceSubscription)
        .where(WorkspaceSubscription.workspace_id == ledger_workspace_id)
        .with_for_update()
    )
    if subscription is not None and row.applied_start and row.applied_end and subscription.paid_through == row.applied_end:
        subscription.paid_through = row.applied_start
        subscription.application_version = (subscription.application_version or 0) + 1
    await db.flush()
    return "reversed"
