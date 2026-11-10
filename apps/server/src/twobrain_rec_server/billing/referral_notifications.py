"""Referral notices share the credit transaction and recheck the original recipient before sending."""
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.events import BillingEvent, enqueue_billing_event
from twobrain_rec_server.db.models import (
    BillingNotificationPreference,
    ExternalIdentity,
    ReferralAttribution,
    TimeCreditLedgerEntry,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)


async def referral_notice_recipient(
    db: AsyncSession, *, credit_id: UUID, workspace_id: UUID, expected_recipient: UUID | None = None,
) -> tuple[UUID, str] | None:
    stmt = (
        select(UserIdentity.id, func.min(ExternalIdentity.email))
        .select_from(TimeCreditLedgerEntry)
        .join(ReferralAttribution, ReferralAttribution.id == TimeCreditLedgerEntry.referral_attribution_id)
        .join(Workspace, Workspace.id == TimeCreditLedgerEntry.workspace_id)
        .join(UserIdentity, UserIdentity.id == ReferralAttribution.inviter_user_id)
        .join(WorkspaceMembership, and_(
            WorkspaceMembership.workspace_id == Workspace.id,
            WorkspaceMembership.user_id == UserIdentity.id,
        ))
        .join(ExternalIdentity, ExternalIdentity.user_id == UserIdentity.id)
        .outerjoin(BillingNotificationPreference, BillingNotificationPreference.user_id == UserIdentity.id)
        .where(
            TimeCreditLedgerEntry.id == credit_id,
            Workspace.id == workspace_id,
            ReferralAttribution.workspace_id == workspace_id,
            Workspace.kind == "personal",
            Workspace.owner_user_id == UserIdentity.id,
            WorkspaceMembership.role == "owner",
            WorkspaceMembership.status == "active",
            UserIdentity.status == "active",
            UserIdentity.merged_into_user_id.is_(None),
            ExternalIdentity.is_verified.is_(True),
            ExternalIdentity.is_active.is_(True),
            ExternalIdentity.email.is_not(None),
            ExternalIdentity.email != "",
            BillingNotificationPreference.optional_email_enabled.is_not(False),
        )
        .group_by(UserIdentity.id)
    )
    if expected_recipient is not None:
        stmt = stmt.where(UserIdentity.id == expected_recipient)
    row = (await db.execute(stmt)).one_or_none()
    return (row[0], row[1]) if row is not None else None


async def enqueue_referral_notice(
    db: AsyncSession, *, credit: TimeCreditLedgerEntry, kind: BillingEvent, at: datetime,
) -> None:
    if credit.referral_attribution_id is None:
        return
    recipient = await referral_notice_recipient(db, credit_id=credit.id, workspace_id=credit.workspace_id)
    if recipient is None:
        return

    def moscow_date(value: datetime) -> str:
        return value.astimezone(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y %H:%M")

    if kind == BillingEvent.REFERRAL_AVAILABLE:
        payload = {"referral_expiry": moscow_date(credit.expires_at)}
    elif kind == BillingEvent.REFERRAL_APPLIED:
        if credit.applied_start is None or credit.applied_end is None:
            raise ValueError("applied referral notice requires a recorded interval")
        payload = {
            "referral_days": str(credit.days),
            "referral_start": moscow_date(credit.applied_start),
            "referral_end": moscow_date(credit.applied_end),
        }
    elif kind == BillingEvent.REFERRAL_REVERSED:
        payload = {"referral_reversed": moscow_date(at)}
    else:
        raise ValueError("invalid referral notice transition")
    await enqueue_billing_event(
        db, workspace_id=credit.workspace_id, recipient_id=recipient[0],
        event_type=kind, subject_ref=str(credit.id), payload=payload,
    )
