"""Account-close policy and durable cooling-window operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.db.models import (
    AccountClosureRequest,
    AuthSession,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)

ACCOUNT_CLOSE_COOLING_DAYS = 7
ACCOUNT_CLOSE_POLICY_VERSION = "account-close-v1"
ACTIVE_CLOSURE_STATES = frozenset(("scheduled", "finalizing", "blocked"))


@dataclass(frozen=True, slots=True)
class AccountCloseView:
    state: str
    requested_at: datetime
    finalize_at: datetime
    policy_version: str
    can_cancel: bool


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def _owner_workspace(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
) -> Workspace:
    workspace = await db.scalar(
        select(Workspace)
        .where(Workspace.id == workspace_id)
        .with_for_update()
    )
    membership = await db.scalar(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.status == "active",
        )
    )
    if workspace is None or membership is None or membership.role != "owner":
        raise ProblemDetail(status=403, code="account_close_owner_required", title="Только владелец может закрыть аккаунт")
    active_members = await db.scalar(
        select(func.count())
        .select_from(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.status == "active",
        )
    )
    if int(active_members or 0) != 1:
        raise ProblemDetail(
            status=409,
            code="account_close_transfer_required",
            title="Перед закрытием передайте пространство участникам",
        )
    return workspace


def close_view(request: AccountClosureRequest, *, now: datetime) -> AccountCloseView:
    now_utc = _utc(now)
    return AccountCloseView(
        state=request.state,
        requested_at=_utc(request.requested_at),
        finalize_at=_utc(request.finalize_at),
        policy_version=request.policy_version,
        can_cancel=request.state in {"scheduled", "blocked"} and now_utc < _utc(request.finalize_at),
    )


async def schedule_account_close(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    now: datetime,
    request_key: str | None = None,
) -> AccountCloseView:
    """Schedule a seven-day cooling period and turn off future renewal."""

    workspace = await _owner_workspace(db, workspace_id=workspace_id, user_id=user_id)
    now_utc = _utc(now)
    existing = await db.scalar(
        select(AccountClosureRequest)
        .where(
            AccountClosureRequest.workspace_id == workspace_id,
            AccountClosureRequest.requested_by_user_id == user_id,
            AccountClosureRequest.state.in_(ACTIVE_CLOSURE_STATES),
        )
        .order_by(AccountClosureRequest.requested_at.desc())
        .with_for_update()
    )
    if existing is not None:
        return close_view(existing, now=now_utc)

    subscription = await db.scalar(
        select(WorkspaceSubscription)
        .where(WorkspaceSubscription.workspace_id == workspace_id)
        .with_for_update()
    )
    if subscription is not None and subscription.recurring_allowed:
        subscription.recurring_allowed = False
        subscription.recurring_authority_version += 1
    request = AccountClosureRequest(
        workspace_id=workspace.id,
        requested_by_user_id=user_id,
        request_key=request_key or f"account-close:{uuid4().hex}",
        state="scheduled",
        policy_version=ACCOUNT_CLOSE_POLICY_VERSION,
        requested_at=now_utc,
        finalize_at=now_utc + timedelta(days=ACCOUNT_CLOSE_COOLING_DAYS),
        metadata_json={"renewal_disabled": True, "cooling_days": ACCOUNT_CLOSE_COOLING_DAYS},
    )
    db.add(request)
    await db.flush()
    return close_view(request, now=now_utc)


async def cancel_account_close(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    now: datetime,
) -> AccountCloseView:
    request = await db.scalar(
        select(AccountClosureRequest)
        .where(
            AccountClosureRequest.workspace_id == workspace_id,
            AccountClosureRequest.requested_by_user_id == user_id,
            AccountClosureRequest.state.in_(("scheduled", "blocked")),
        )
        .order_by(AccountClosureRequest.requested_at.desc())
        .with_for_update()
    )
    if request is None:
        raise ProblemDetail(status=404, code="account_close_not_scheduled", title="Закрытие аккаунта не запланировано")
    now_utc = _utc(now)
    if now_utc >= _utc(request.finalize_at):
        raise ProblemDetail(status=409, code="account_close_cooling_expired", title="Период отмены уже завершён")
    request.state = "canceled"
    request.canceled_at = now_utc
    return close_view(request, now=now_utc)


async def finalize_account_close(
    db: AsyncSession,
    *,
    request_id: UUID,
    now: datetime,
) -> AccountCloseView:
    """Revoke access and paid entitlements after the cooling window.

    Meeting deletion fan-out is deliberately an explicit next stage owned by
    the deletion reconciler; this function never claims those external rows
    are erased.  It only applies the immediate account-access boundary.
    """

    request = await db.scalar(
        select(AccountClosureRequest)
        .where(AccountClosureRequest.id == request_id)
        .with_for_update()
    )
    if request is None:
        raise ProblemDetail(status=404, code="account_close_not_found", title="Запрос закрытия не найден")
    now_utc = _utc(now)
    if request.state == "canceled":
        return close_view(request, now=now_utc)
    if request.state == "completed":
        return close_view(request, now=now_utc)
    if now_utc < _utc(request.finalize_at):
        raise ProblemDetail(status=409, code="account_close_cooling_active", title="Период отмены ещё не завершён")
    request.state = "finalizing"
    await db.flush()
    subscription = await db.scalar(
        select(WorkspaceSubscription)
        .where(WorkspaceSubscription.workspace_id == request.workspace_id)
        .with_for_update()
    )
    if subscription is not None:
        subscription.state = "free"
        subscription.plan_code = "free"
        subscription.cycle = "none"
        subscription.capacity_bytes = 250_000_000
        subscription.paid_through = None
        subscription.trial_ends_at = None
        subscription.recurring_allowed = False
        subscription.recurring_authority_version += 1
    identity = await db.get(UserIdentity, request.requested_by_user_id, with_for_update=True)
    if identity is not None:
        identity.status = "closed"
    sessions = (
        await db.scalars(select(AuthSession).where(AuthSession.user_id == request.requested_by_user_id))
    ).all()
    for session in sessions:
        session.status = "revoked"
    devices = (
        await db.scalars(select(RegisteredDevice).where(RegisteredDevice.user_id == request.requested_by_user_id))
    ).all()
    for device in devices:
        device.status = "revoked"
        device.registration_state = "revoked"
    await db.execute(
        WorkspaceMembership.__table__.update()
        .where(
            WorkspaceMembership.workspace_id == request.workspace_id,
            WorkspaceMembership.user_id == request.requested_by_user_id,
        )
        .values(status="inactive")
    )
    request.state = "completed"
    request.finalized_at = now_utc
    request.metadata_json = {
        **(request.metadata_json or {}),
        "access_revoked_at": now_utc.isoformat(),
        "meeting_deletion_boundary": "delegated_to_deletion_reconciler",
    }
    await db.flush()
    return close_view(request, now=now_utc)


async def list_due_account_closures(
    db: AsyncSession,
    *,
    now: datetime,
    limit: int = 100,
) -> tuple[UUID, ...]:
    """Return due request IDs for a maintenance/Temporal finalizer."""

    rows = await db.scalars(
        select(AccountClosureRequest.id)
        .where(
            AccountClosureRequest.state.in_(("scheduled", "blocked")),
            AccountClosureRequest.finalize_at <= _utc(now),
        )
        .order_by(AccountClosureRequest.finalize_at, AccountClosureRequest.id)
        .limit(max(1, min(limit, 500)))
    )
    return tuple(rows)
