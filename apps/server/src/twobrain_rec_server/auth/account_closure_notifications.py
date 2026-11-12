"""Historical close-request notices; the caller owns commit and rollback."""

from datetime import UTC, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.events import BillingEvent, enqueue_billing_event
from twobrain_rec_server.billing.notifications import BillingNotification, build_notification
from twobrain_rec_server.db.models import (
    AccountClosureRequest,
    BillingNotificationDelivery,
    ExternalIdentity,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)


def _payload(request: AccountClosureRequest, phase: str) -> dict[str, str]:
    payload = {
        "phase": phase,
        "account_close_request_id": request.id.hex,
        "account_close_requested_at": request.requested_at.astimezone(UTC).isoformat(),
        "account_close_finalize_at": request.finalize_at.astimezone(UTC).isoformat(),
        "action_path": "/settings/account",
    }
    if phase == "canceled" and request.canceled_at is not None:
        payload["account_close_canceled_at"] = request.canceled_at.astimezone(UTC).isoformat()
    return payload


async def _recipient(db: AsyncSession, request: AccountClosureRequest) -> str | None:
    # NOWAIT on every source row avoids inversion with closure and identity-first merge.
    workspace = await db.scalar(select(Workspace).where(
        Workspace.id == request.workspace_id,
    ).with_for_update(read=True, nowait=True))
    if (workspace is None or workspace.kind != "personal"
            or workspace.owner_user_id != request.requested_by_user_id):
        return None
    identity = await db.scalar(select(UserIdentity).where(
        UserIdentity.id == request.requested_by_user_id,
    ).with_for_update(read=True, nowait=True))
    if identity is None or identity.status != "active" or identity.merged_into_user_id is not None:
        return None
    membership = await db.scalar(select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == request.workspace_id,
        WorkspaceMembership.user_id == request.requested_by_user_id,
    ).with_for_update(read=True, nowait=True))
    if membership is None or membership.status != "active" or membership.role != "owner":
        return None
    addresses = list(await db.scalars(select(ExternalIdentity).where(
        ExternalIdentity.user_id == request.requested_by_user_id,
        ExternalIdentity.is_active.is_(True), ExternalIdentity.is_verified.is_(True),
        ExternalIdentity.email.is_not(None), ExternalIdentity.email != "",
    ).order_by(ExternalIdentity.email, ExternalIdentity.id).with_for_update(read=True, nowait=True)))
    return addresses[0].email if addresses else None


async def enqueue_account_close_notice(
    db: AsyncSession, request: AccountClosureRequest, *, phase: str,
) -> None:
    if await _recipient(db, request) is None:
        return
    await enqueue_billing_event(
        db, workspace_id=request.workspace_id, recipient_id=request.requested_by_user_id,
        event_type=BillingEvent.ACCOUNT_CLOSE, subject_ref=f"{request.id.hex}:{phase}",
        payload=_payload(request, phase),
    )


async def account_close_notice_recipient(
    db: AsyncSession, delivery: BillingNotificationDelivery,
) -> str | None:
    from twobrain_rec_server.auth.account_closure import (
        ACCOUNT_CLOSE_COOLING_DAYS,
        ACCOUNT_CLOSE_POLICY_VERSION,
    )

    if delivery.template_key != BillingNotification.ACCOUNT_CLOSE or delivery.channel != "email":
        return None
    event = build_notification(
        event_id=delivery.event_id, kind=BillingNotification.ACCOUNT_CLOSE,
        payload=delivery.safe_payload if isinstance(delivery.safe_payload, dict) else {},
    )
    snapshot = event.safe_payload
    if not snapshot:
        return None
    request_id = UUID(snapshot["account_close_request_id"])
    phase = snapshot["phase"]
    if delivery.event_id != f"account.close:{request_id.hex}:{phase}":
        return None
    request = await db.scalar(select(AccountClosureRequest).where(
        AccountClosureRequest.id == request_id,
    ).with_for_update(read=True, nowait=True))
    if (request is None or request.workspace_id != delivery.workspace_id
            or request.requested_by_user_id != delivery.recipient_id
            or request.policy_version != ACCOUNT_CLOSE_POLICY_VERSION
            or request.state not in {"scheduled", "canceled", "blocked"}
            or request.finalized_at is not None or not isinstance(request.metadata_json, dict)
            or any(key in request.metadata_json for key in ("content_workspace_ids", "finalization_started_at"))
            or request.requested_at.tzinfo is None or request.finalize_at.tzinfo is None
            or request.finalize_at - request.requested_at != timedelta(days=ACCOUNT_CLOSE_COOLING_DAYS)):
        return None
    if request.state == "canceled" and (
        request.canceled_at is None or request.canceled_at.tzinfo is None
        or not request.requested_at <= request.canceled_at < request.finalize_at
    ):
        return None
    if phase == "canceled" and request.state != "canceled":
        return None
    if snapshot != _payload(request, phase):
        return None
    return await _recipient(db, request)
