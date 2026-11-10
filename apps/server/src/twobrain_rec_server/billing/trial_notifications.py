"""Queue and revalidate notices for the original personal trial."""

from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import String, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.events import BillingEvent, enqueue_billing_event, event_id_for
from twobrain_rec_server.billing.notifications import BillingNotification
from twobrain_rec_server.billing.storage import lock_storage_workspace
from twobrain_rec_server.db.models import (
    BillingNotificationDelivery,
    BillingNotificationPreference,
    ExternalIdentity,
    TrialActivation,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)

_PHASES = {
    "started": (BillingEvent.TRIAL_STARTED, BillingNotification.TRIAL_STARTED),
    "t72": (BillingEvent.TRIAL_ENDING, BillingNotification.TRIAL_ENDING),
    "t24": (BillingEvent.TRIAL_ENDING, BillingNotification.TRIAL_ENDING),
    "expired": (BillingEvent.TRIAL_EXPIRED, BillingNotification.TRIAL_EXPIRED),
}
TRIAL_NOTIFICATION_KINDS = frozenset(kind for _, kind in _PHASES.values())


def _trial_phase(now: datetime, *, include_start: bool = False):
    end = TrialActivation.ends_at
    start = TrialActivation.starts_at
    start_case = (
        (((start <= now) & (start > now - timedelta(days=1)) & (end > now), "started"),)
        if include_start else ()
    )
    return case(
        *start_case,
        ((end <= now) & (end > now - timedelta(days=1)), "expired"),
        ((end > now) & (end <= now + timedelta(days=1)), "t24"),
        ((end > now) & (end <= now + timedelta(days=3)), "t72"),
    )


def _verified_email():
    return (
        select(func.min(ExternalIdentity.email))
        .where(
            ExternalIdentity.user_id == TrialActivation.user_id,
            ExternalIdentity.is_active.is_(True),
            ExternalIdentity.is_verified.is_(True),
            ExternalIdentity.email != "",
        )
        .correlate(TrialActivation)
        .scalar_subquery()
    )


def _eligible_trials(now: datetime):
    return (
        select(TrialActivation)
        .join(Workspace, Workspace.id == TrialActivation.workspace_id)
        .join(WorkspaceSubscription, WorkspaceSubscription.workspace_id == Workspace.id)
        .join(UserIdentity, UserIdentity.id == TrialActivation.user_id)
        .join(
            WorkspaceMembership,
            (WorkspaceMembership.workspace_id == Workspace.id)
            & (WorkspaceMembership.user_id == TrialActivation.user_id),
        )
        .where(
            TrialActivation.starts_at <= now,
            TrialActivation.ends_at > now - timedelta(days=1),
            Workspace.kind == "personal",
            Workspace.owner_user_id == TrialActivation.user_id,
            WorkspaceMembership.role == "owner",
            WorkspaceMembership.status == "active",
            UserIdentity.status == "active",
            UserIdentity.merged_into_user_id.is_(None),
            WorkspaceSubscription.plan_code == "trial",
            WorkspaceSubscription.state == "trial",
            WorkspaceSubscription.trial_ends_at == TrialActivation.ends_at,
            or_(
                WorkspaceSubscription.billing_owner_id.is_(None),
                WorkspaceSubscription.billing_owner_id == TrialActivation.user_id,
            ),
            or_(
                WorkspaceSubscription.paid_through.is_(None),
                WorkspaceSubscription.paid_through <= now,
            ),
        )
    )


def _payload(trial: TrialActivation) -> dict[str, str]:
    zone = ZoneInfo("Europe/Moscow")
    return {
        "trial_starts_at": trial.starts_at.astimezone(zone).strftime("%d.%m.%Y %H:%M"),
        "trial_ends_at": trial.ends_at.astimezone(zone).strftime("%d.%m.%Y %H:%M"),
        "action_path": "/billing",
    }


async def _enqueue(db: AsyncSession, trial: TrialActivation, phase: str) -> bool:
    event, _ = _PHASES[phase]
    return await enqueue_billing_event(
        db,
        workspace_id=trial.workspace_id,
        recipient_id=trial.user_id,
        event_type=event,
        subject_ref=f"{trial.id.hex}:{phase}",
        payload=_payload(trial),
    )


async def enqueue_trial_started(db: AsyncSession, trial: TrialActivation, *, now: datetime) -> None:
    # The POST already holds the workspace lock and has verified the owner.
    await db.flush()
    if await db.scalar(
        _eligible_trials(now).where(TrialActivation.id == trial.id, _verified_email().is_not(None))
    ) is not None:
        await _enqueue(db, trial, "started")


async def enqueue_due_trial_notices(db: AsyncSession, *, now: datetime) -> None:
    phase = _trial_phase(now)
    event_prefix = case(
        (phase == "expired", f"{BillingEvent.TRIAL_EXPIRED.value}:"),
        else_=f"{BillingEvent.TRIAL_ENDING.value}:",
    )
    event_id = (
        event_prefix + func.replace(cast(TrialActivation.id, String), "-", "") + ":" + phase
    )
    queued = (
        select(BillingNotificationDelivery.id)
        .where(
            BillingNotificationDelivery.workspace_id == TrialActivation.workspace_id,
            BillingNotificationDelivery.recipient_id == TrialActivation.user_id,
            BillingNotificationDelivery.channel == "email",
            BillingNotificationDelivery.event_id == event_id,
        )
        .exists()
    )
    candidates = (
        await db.execute(
            _eligible_trials(now)
            .with_only_columns(TrialActivation.workspace_id, TrialActivation.id)
            .where(
                TrialActivation.ends_at <= now + timedelta(days=3),
                _verified_email().is_not(None),
                ~queued,
            )
            .order_by(TrialActivation.ends_at, TrialActivation.id)
            .limit(100)
        )
    ).all()
    for workspace_id, trial_id in sorted(candidates):
        await lock_storage_workspace(db, workspace_id)
        row = (
            await db.execute(
                _eligible_trials(now)
                .add_columns(phase)
                .where(
                    TrialActivation.id == trial_id,
                    phase.is_not(None),
                    _verified_email().is_not(None),
                    ~queued,
                )
            )
        ).one_or_none()
        if row is not None:
            await _enqueue(db, *row)


async def trial_notice_recipient(
    db: AsyncSession, delivery: BillingNotificationDelivery, *, now: datetime
) -> str | None:
    """Check the activation, window, current address and preference at claim time."""
    event_key, _, phase = delivery.event_id.rpartition(":")
    if phase not in _PHASES:
        return None
    event, kind = _PHASES[phase]
    if delivery.template_key != kind.value:
        return None
    try:
        trial_id = UUID(event_key.removeprefix(f"{event.value}:"))
    except ValueError:
        return None
    if delivery.event_id != event_id_for(event_type=event, subject_ref=f"{trial_id.hex}:{phase}"):
        return None
    optional_enabled = (
        select(BillingNotificationPreference.optional_email_enabled)
        .where(BillingNotificationPreference.user_id == TrialActivation.user_id)
        .correlate(TrialActivation)
        .scalar_subquery()
    )
    row = (
        await db.execute(
            _eligible_trials(now)
            .add_columns(_verified_email(), optional_enabled)
            .where(
                TrialActivation.id == trial_id,
                TrialActivation.workspace_id == delivery.workspace_id,
                TrialActivation.user_id == delivery.recipient_id,
                _trial_phase(now, include_start=True) == phase,
            )
        )
    ).one_or_none()
    if row is None:
        return None
    trial, address, optional_email_enabled = row
    if delivery.safe_payload != _payload(trial) or (
        phase != "expired" and optional_email_enabled is False
    ):
        return None
    return address
