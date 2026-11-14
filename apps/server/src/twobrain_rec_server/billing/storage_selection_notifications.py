"""Historical no-money selection notices; the caller owns the transaction."""

import json
from datetime import UTC
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.events import enqueue_billing_notification
from twobrain_rec_server.billing.notifications import BillingNotification, build_notification
from twobrain_rec_server.db.models import (
    AccountClosureRequest,
    BillingInvoice,
    BillingNotificationDelivery,
    BillingOperation,
    BillingPurchaseQuote,
    ExternalIdentity,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)


def _integer(value: object, maximum: int = 9223372036854775807, *, minimum: int = 1) -> bool:
    return type(value) is int and minimum <= value <= maximum


async def _source(db: AsyncSession, operation_id: UUID):
    # NOWAIT on every source row avoids inversion with workspace-first financial writers.
    operation = await db.scalar(select(BillingOperation).where(
        BillingOperation.id == operation_id,
    ).with_for_update(read=True, nowait=True))
    if (operation is None or operation.state != "succeeded" or operation.provider_id is not None
            or operation.kind not in ("storage_schedule", "storage_selection_cancel")
            or not isinstance(operation.request_snapshot, dict)
            or operation.created_at.tzinfo is None):
        return None
    snapshot = operation.request_snapshot
    quote = await db.scalar(select(BillingPurchaseQuote).where(
        BillingPurchaseQuote.consumed_operation_id == operation.id,
    ).with_for_update(read=True, nowait=True))
    payload = {"storage_selection_operation_id": operation.id.hex,
               "storage_selection_saved_at": operation.created_at.astimezone(UTC).isoformat(),
               "action_path": "/billing/storage"}
    if operation.kind == "storage_schedule":
        if (quote is None or quote.purpose != "storage_schedule"
                or quote.workspace_id != operation.workspace_id
                or operation.idempotency_key != f"purchase:{quote.id}"
                or not isinstance(quote.snapshot, dict)
                or not _integer(quote.selection_version, 2147483646, minimum=0)
                or not _integer(snapshot.get("selection_version"), 2147483646, minimum=0)
                or snapshot["selection_version"] != quote.selection_version
                or quote.created_at.tzinfo is None or quote.expires_at.tzinfo is None
                or not quote.created_at <= operation.created_at < quote.expires_at):
            return None
        # JSON equality must not equate a boolean/float with an accepted integer.
        if json.dumps(snapshot, sort_keys=True, allow_nan=False) != json.dumps(quote.snapshot, sort_keys=True, allow_nan=False):
            return None
        cycle, target = snapshot.get("cycle"), snapshot.get("target_capacity_bytes")
        base, addon = snapshot.get("base_catalog_snapshot"), snapshot.get("next_storage_price")
        if (cycle not in ("month", "year") or snapshot.get("plan_code") != "personal"
                or not _integer(target, 500_000_000_000) or target < 5_000_000_000 or target % 5_000_000_000
                or not _integer(snapshot.get("current_capacity_bytes"))
                or not _integer(snapshot.get("next_amount_minor")) or not isinstance(base, dict)
                or base.get("plan_code") != "personal" or base.get("cycle") != cycle
                or base.get("currency") != "RUB" or not _integer(base.get("catalog_version"), 2147483647)
                or not _integer(base.get("amount_minor"))
                or type(base.get("storage_bytes")) is not int or base["storage_bytes"] != 5_000_000_000):
            return None
        if target == 5_000_000_000:
            if addon is not None:
                return None
            amount = base["amount_minor"]
        else:
            if (not isinstance(addon, dict) or addon.get("currency") != "RUB"
                    or addon.get("cycle") != cycle or not _integer(addon.get("capacity_bytes"))
                    or addon["capacity_bytes"] != target
                    or not _integer(addon.get("version"), 2147483647)
                    or not _integer(addon.get("amount_minor"))):
                return None
            try:
                if str(UUID(addon.get("id", ""))) != addon["id"]:
                    return None
            except (ValueError, TypeError, AttributeError):
                return None
            amount = base["amount_minor"] + addon["amount_minor"]
        if amount != snapshot["next_amount_minor"]:
            return None
        owner = quote.owner_user_id
        version = quote.selection_version + 1
        payload.update(storage_selection_phase="scheduled", storage_selection_version=str(version),
                       storage_target_capacity_bytes=str(target),
                       storage_current_capacity_bytes=str(snapshot["current_capacity_bytes"]),
                       storage_cycle=cycle, storage_next_amount_minor=str(amount),
                       storage_effective_at=snapshot.get("ends_at"))
    else:
        if (quote is not None or set(snapshot) != {
                "storage_selection_schema", "owner_user_id", "selection_version", "canceled_capacity_bytes"}
                or type(snapshot["storage_selection_schema"]) is not int or snapshot["storage_selection_schema"] != 1
                or not _integer(snapshot["selection_version"], 2147483647)
                or not _integer(snapshot["canceled_capacity_bytes"])):
            return None
        try:
            owner = UUID(snapshot["owner_user_id"])
            if owner.hex != snapshot["owner_user_id"]:
                return None
        except (ValueError, TypeError, AttributeError):
            return None
        version = snapshot["selection_version"]
        if operation.idempotency_key != f"storage-cancel:{operation.workspace_id.hex}:{version}":
            return None
        payload.update(storage_selection_phase="canceled", storage_selection_version=str(version),
                       storage_target_capacity_bytes=str(snapshot["canceled_capacity_bytes"]))
    if await db.scalar(select(BillingInvoice.id).where(BillingInvoice.operation_id == operation.id).limit(1)):
        return None
    event_id = f"storage:{operation.workspace_id}:selection:{version}"
    safe = build_notification(event_id=event_id, kind=BillingNotification.STORAGE_SELECTION_CHANGED,
                              payload=payload).safe_payload
    return (operation.workspace_id, owner, event_id, safe) if safe else None


async def _recipient(db: AsyncSession, workspace_id: UUID, owner: UUID) -> str | None:
    workspace = await db.scalar(select(Workspace).where(
        Workspace.id == workspace_id,
    ).with_for_update(read=True, nowait=True))
    if workspace is None or workspace.kind != "personal" or workspace.owner_user_id != owner:
        return None
    subscription = await db.scalar(select(WorkspaceSubscription).where(
        WorkspaceSubscription.workspace_id == workspace_id,
    ).with_for_update(read=True, nowait=True))
    if subscription is None or subscription.billing_owner_id != owner:
        return None
    identity = await db.scalar(select(UserIdentity).where(
        UserIdentity.id == owner,
    ).with_for_update(read=True, nowait=True))
    if identity is None or identity.status != "active" or identity.merged_into_user_id is not None:
        return None
    membership = await db.scalar(select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id, WorkspaceMembership.user_id == owner,
    ).with_for_update(read=True, nowait=True))
    if membership is None or membership.status != "active" or membership.role != "owner":
        return None
    addresses = list(await db.scalars(select(ExternalIdentity).where(
        ExternalIdentity.user_id == owner, ExternalIdentity.is_active.is_(True),
        ExternalIdentity.is_verified.is_(True), ExternalIdentity.email.is_not(None),
        func.trim(ExternalIdentity.email) != "",
    ).order_by(ExternalIdentity.email, ExternalIdentity.id).with_for_update(read=True, nowait=True)))
    if not addresses:
        return None
    closures = list(await db.scalars(select(AccountClosureRequest).where(
        AccountClosureRequest.requested_by_user_id == owner,
    ).order_by(AccountClosureRequest.id).with_for_update(read=True, nowait=True)))
    if any(row.finalized_at is not None or not isinstance(row.metadata_json, dict)
           or any(key in row.metadata_json for key in ("finalization_started_at", "content_workspace_ids"))
           for row in closures):
        return None
    return addresses[0].email


async def enqueue_storage_selection_notice(db: AsyncSession, operation: BillingOperation) -> None:
    source = await _source(db, operation.id)
    if source is None:
        raise ValueError("storage_selection_source_invalid")
    workspace, owner, event_id, payload = source
    if await _recipient(db, workspace, owner) is None:
        return
    await enqueue_billing_notification(db, workspace_id=workspace, recipient_id=owner,
                                       event_id=event_id, kind=BillingNotification.STORAGE_SELECTION_CHANGED,
                                       payload=payload, marketing_allowed=False)


async def storage_selection_notice_recipient(db: AsyncSession, delivery: BillingNotificationDelivery) -> str | None:
    if delivery.template_key != BillingNotification.STORAGE_SELECTION_CHANGED or delivery.channel != "email":
        return None
    safe = build_notification(event_id=delivery.event_id, kind=BillingNotification.STORAGE_SELECTION_CHANGED,
                              payload=delivery.safe_payload).safe_payload
    if not safe:
        return None
    source = await _source(db, UUID(safe["storage_selection_operation_id"]))
    if source != (delivery.workspace_id, delivery.recipient_id, delivery.event_id, safe):
        return None
    return await _recipient(db, delivery.workspace_id, delivery.recipient_id)
