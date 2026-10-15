"""Durable dispatch and at-most-once transport reservation; content stays in DB."""

import secrets
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from temporalio import activity
from temporalio.client import WorkflowExecutionStatus
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.email_delivery import EmailLoginDeliveryError, PostalEmailLoginClient
from twobrain_rec_server.cabinet.access import (
    decide_meeting_access,
    hash_share_token,
    lock_shareable_meeting,
    seal_invitation_delivery,
)
from twobrain_rec_server.cabinet.summary_sharing import (
    active_sender,
    encryption_key,
    open_sealed,
    seal,
)
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.models import (
    DispatchIntent,
    ExternalIdentity,
    Meeting,
    MeetingShareInvitation,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.db.models.summary_sharing import (
    PublishedMeetingSummary,
    SummaryDeliveryBatch,
    SummaryEmailSuppression,
    SummaryRecipientDelivery,
)
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    TenantDatabaseContext,
    apply_tenant_context,
)
from twobrain_rec_server.workflows.summary_delivery_workflow import SummaryDeliveryWorkflow


async def tenant(db, workspace_id, user_id):
    # Organization is metadata required for the existing worker context. Runtime
    # queries remain scoped to the payload workspace and saved batch owner.
    role = (
        await db.scalar(text("SELECT session_user"))
        if db.get_bind().dialect.name == "postgresql"
        else None
    )
    if role == "twobrain_rec_maintenance":
        await apply_tenant_context(
            db,
            MaintenanceTenantContext(
                operation_name="summary_delivery_reconciliation",
                actor_id="summary-delivery",
                reason_category="delivery_attempt",
                feature_area="sharing",
            ),
        )
        return await db.get(Workspace, workspace_id) is not None
    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=UUID(int=0),
            workspace_id=workspace_id,
            user_id=user_id,
            context_kind="request",
        ),
    )
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        return False
    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=workspace.organization_id,
            workspace_id=workspace_id,
            user_id=user_id,
            context_kind="request",
        ),
    )
    return True


async def refresh_batch_state(db, batch):
    states = set(
        await db.scalars(
            select(SummaryRecipientDelivery.state).where(
                SummaryRecipientDelivery.workspace_id == batch.workspace_id,
                SummaryRecipientDelivery.batch_id == batch.id,
            )
        )
    )
    if batch.state in ("cancelled", "requires_review"):
        return
    batch.state = (
        "pending" if "pending" in states else "sending" if "sending" in states else "completed"
    )


async def reserve_recipient(sessionmaker, *, settings, workspace_id, batch_id, recipient_id):
    now = datetime.now(UTC)
    async with sessionmaker() as db:
        await tenant(db, workspace_id, UUID(int=0))
        batch = await db.scalar(
            select(SummaryDeliveryBatch).where(
                SummaryDeliveryBatch.workspace_id == workspace_id,
                SummaryDeliveryBatch.id == batch_id,
            )
        )
        if batch is None:
            return None
        try:
            meeting = await lock_shareable_meeting(
                db, workspace_id=workspace_id, meeting_id=batch.meeting_id
            )
        except ProblemDetail:
            return None
        await tenant(db, workspace_id, batch.owner_user_id)
        decision = await decide_meeting_access(
            db, meeting, workspace_id=workspace_id, viewer_user_id=batch.owner_user_id
        )
        guard = None
        if batch.automatic:
            from twobrain_rec_server.cabinet.summary_autosend import guard_auto_batch

            guard = await guard_auto_batch(db, batch=batch, now=now, settings=settings)
        # Global lock order: meeting -> preference -> rule -> batch -> recipient.
        batch = await db.scalar(
            select(SummaryDeliveryBatch)
            .where(
                SummaryDeliveryBatch.id == batch_id,
                SummaryDeliveryBatch.workspace_id == workspace_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        row = await db.scalar(
            select(SummaryRecipientDelivery)
            .where(
                SummaryRecipientDelivery.workspace_id == workspace_id,
                SummaryRecipientDelivery.batch_id == batch_id,
                SummaryRecipientDelivery.id == recipient_id,
            )
            .with_for_update()
        )
        if row is None:
            return None
        if row.state == "sending":
            if row.reserved_at and row.reserved_at + timedelta(minutes=2) <= now:
                row.state, row.failure_code = "unknown", "summary_attempt_interrupted"
                await refresh_batch_state(db, batch)
                await db.commit()
            return None
        if row.state != "pending":
            return None
        if batch.scheduled_at > now:
            return None
        reason = None
        review = False
        if guard and not guard.allowed:
            reason, review = guard.reason_code, guard.requires_review
        if (
            not decision.can_share
            or meeting.created_by_user_id != batch.owner_user_id
            or not await active_sender(
                db, workspace_id=workspace_id, actor_user_id=batch.owner_user_id
            )
        ):
            reason = "summary_owner_authority_lost"
        if batch.state in ("cancelled", "requires_review") or batch.deadline_at <= now:
            reason = reason or "summary_batch_cancelled_or_expired"
        if reason:
            row.state, row.failure_code = "cancelled", reason
            if review:
                batch.state, batch.failure_code = "requires_review", reason
            await refresh_batch_state(db, batch)
            await db.commit()
            return None
        snapshot = await db.scalar(
            select(PublishedMeetingSummary).where(
                PublishedMeetingSummary.id == batch.published_summary_id,
                PublishedMeetingSummary.workspace_id == workspace_id,
                PublishedMeetingSummary.meeting_id == meeting.id,
            )
        )
        if snapshot is None or snapshot.schema_version != 1:
            row.state, row.failure_code = "cancelled", "summary_publication_missing"
            await refresh_batch_state(db, batch)
            await db.commit()
            return None
        key = encryption_key(settings)
        suppression = None
        if batch.automatic:
            suppression = await db.scalar(
                select(SummaryEmailSuppression)
                .where(
                    SummaryEmailSuppression.workspace_id == workspace_id,
                    SummaryEmailSuppression.sender_user_id == batch.owner_user_id,
                    SummaryEmailSuppression.normalized_address_hash == row.normalized_address_hash,
                )
                .with_for_update()
            )
            if suppression and suppression.opted_out_at:
                row.state = "suppressed"
                await refresh_batch_state(db, batch)
                await db.commit()
                return None
            if suppression is None:
                token = secrets.token_urlsafe(32)
                suppression = SummaryEmailSuppression(
                    id=uuid4(),
                    workspace_id=workspace_id,
                    sender_user_id=batch.owner_user_id,
                    normalized_address_hash=row.normalized_address_hash,
                    token_hash=hash_share_token(token),
                    token_ciphertext=seal(token, key),
                )
                db.add(suppression)
        email = open_sealed(row.encrypted_address, key)
        identity = await db.scalar(
            select(ExternalIdentity)
            .join(WorkspaceMembership, WorkspaceMembership.user_id == ExternalIdentity.user_id)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.status == "active",
                func.lower(ExternalIdentity.email) == email,
                ExternalIdentity.is_active.is_(True),
                ExternalIdentity.is_verified.is_(True),
            )
        )
        existing_access = None
        if identity:
            existing_access = await decide_meeting_access(
                db, meeting, workspace_id=workspace_id, viewer_user_id=identity.user_id
            )
        base = str(settings.public_base_url).rstrip("/")
        if identity and existing_access.can_view:
            row.user_id = identity.user_id
            # This notification references its own frozen document; no ACL mutation.
            read_url = f"{base}/api/v1/cabinet/summary-sharing/received/{row.id}?workspace_id={workspace_id}"
        else:
            if not settings.share_external_invitations_enabled:
                row.state, row.failure_code = "cancelled", "summary_external_delivery_disabled"
                await refresh_batch_state(db, batch)
                await db.commit()
                return None
            token = secrets.token_urlsafe(32)
            invitation = MeetingShareInvitation(
                id=uuid4(),
                workspace_id=workspace_id,
                meeting_id=meeting.id,
                invited_by_user_id=batch.owner_user_id,
                normalized_address_hash=row.normalized_address_hash,
                encrypted_delivery_address=seal_invitation_delivery(
                    address=email, raw_token=token, key=key
                ),
                encrypted_recipient_address=seal_invitation_delivery(
                    address=email, raw_token=token, key=key
                ),
                token_hash=hash_share_token(token),
                content_scope="summary_only",
                can_download=False,
                can_export=False,
                can_comment=False,
                can_edit=False,
                status="sent",
                published_summary_id=snapshot.id,
                expires_at=now + timedelta(days=7),
                read_expires_at=now + timedelta(days=30),
                sent_at=now,
            )
            db.add(invitation)
            await db.flush()
            row.invitation_id = invitation.id
            read_url = f"{base}/share-invitations/{token}?workspace_id={workspace_id}"
        opt_out = (
            f"{base}/api/v1/cabinet/summary-sharing/opt-out/{open_sealed(suppression.token_ciphertext, key)}?workspace_id={workspace_id}"
            if suppression
            else None
        )
        row.state, row.reserved_at = "sending", now
        row.read_expires_at = row.read_expires_at or now + timedelta(days=30)
        row.attempt_count += 1
        batch.state = "sending"
        payload = {
            "recipient_email": email,
            "read_url": read_url,
            "delivery_key": f"summary:{row.id}:{row.attempt_count}",
            "meeting_title": snapshot.projection_json["meeting_label"],
            "automatic": batch.automatic,
            "opt_out_url": opt_out,
        }
        await db.commit()
        return payload


async def deliver_summary_batch(
    sessionmaker, *, settings, workspace_id, batch_id, mail_client=None
):
    async with sessionmaker() as db:
        await tenant(db, workspace_id, UUID(int=0))
        ids = list(
            await db.scalars(
                select(SummaryRecipientDelivery.id)
                .where(
                    SummaryRecipientDelivery.workspace_id == workspace_id,
                    SummaryRecipientDelivery.batch_id == batch_id,
                )
                .order_by(SummaryRecipientDelivery.id)
            )
        )
    for recipient_id in ids:
        payload = await reserve_recipient(
            sessionmaker,
            settings=settings,
            workspace_id=workspace_id,
            batch_id=batch_id,
            recipient_id=recipient_id,
        )
        if payload is None:
            continue
        state, code, provider_id = "accepted", None, None
        try:
            if mail_client is None and not settings.email_login_delivery_enabled:
                raise EmailLoginDeliveryError("postal_delivery_disabled", retryable=False)
            sender = mail_client or PostalEmailLoginClient.from_settings(settings)
            # Database session and reservation locks have ended before network I/O.
            provider_id = await sender.send_summary_delivery(**payload)
        except EmailLoginDeliveryError as exc:
            state = "unknown" if exc.outcome_unknown else "failed"
            code = exc.reason_code
        except Exception:
            # Crash/transport ambiguity can never enter an automatic resend path.
            state, code = "unknown", "summary_delivery_outcome_unknown"
        async with sessionmaker() as db:
            await tenant(db, workspace_id, UUID(int=0))
            current_batch = await db.scalar(
                select(SummaryDeliveryBatch).where(
                    SummaryDeliveryBatch.id == batch_id,
                    SummaryDeliveryBatch.workspace_id == workspace_id,
                )
            )
            if current_batch is None:
                continue
            await db.scalar(
                select(Meeting)
                .where(Meeting.id == current_batch.meeting_id, Meeting.workspace_id == workspace_id)
                .with_for_update()
            )
            batch = await db.scalar(
                select(SummaryDeliveryBatch)
                .where(
                    SummaryDeliveryBatch.id == batch_id,
                    SummaryDeliveryBatch.workspace_id == workspace_id,
                )
                .with_for_update()
            )
            row = await db.scalar(
                select(SummaryRecipientDelivery)
                .where(
                    SummaryRecipientDelivery.id == recipient_id,
                    SummaryRecipientDelivery.workspace_id == workspace_id,
                )
                .with_for_update()
            )
            if row is not None and row.state == "sending":
                row.state, row.failure_code, row.provider_message_id, row.completed_at = (
                    state,
                    code,
                    provider_id,
                    datetime.now(UTC),
                )
                if batch:
                    await refresh_batch_state(db, batch)
                await db.commit()
    return {"batch_id": str(batch_id), "state": "processed"}


@activity.defn(name="deliver_summary_batch_activity")
async def deliver_summary_batch_activity(payload: dict[str, str]):
    settings = get_settings()
    engine = create_engine(settings)
    try:
        return await deliver_summary_batch(
            create_sessionmaker(engine),
            settings=settings,
            workspace_id=UUID(payload["workspace_id"]),
            batch_id=UUID(payload["batch_id"]),
        )
    finally:
        await engine.dispose()


async def finalize_expired_batches(sessionmaker, *, now, limit):
    """Deadline closes only attempts that have never been reserved."""
    context = MaintenanceTenantContext(
        operation_name="summary_delivery_reconciliation",
        actor_id="summary-delivery",
        reason_category="dispatch_recovery",
        feature_area="sharing",
    )
    async with sessionmaker() as db:
        await apply_tenant_context(db, context)
        ids = list(
            await db.scalars(
                select(SummaryDeliveryBatch.id)
                .join(
                    SummaryRecipientDelivery,
                    SummaryRecipientDelivery.batch_id == SummaryDeliveryBatch.id,
                )
                .where(
                    SummaryDeliveryBatch.deadline_at <= now,
                    SummaryRecipientDelivery.state == "pending",
                )
                .distinct()
                .limit(limit)
            )
        )
        await db.commit()
    for batch_id in ids:
        async with sessionmaker() as db:
            await apply_tenant_context(db, context)
            batch = await db.get(SummaryDeliveryBatch, batch_id)
            if batch is None:
                continue
            await db.scalar(
                select(Meeting)
                .where(Meeting.id == batch.meeting_id, Meeting.workspace_id == batch.workspace_id)
                .with_for_update()
            )
            batch = await db.scalar(
                select(SummaryDeliveryBatch)
                .where(SummaryDeliveryBatch.id == batch_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if batch is None or batch.deadline_at > now:
                continue
            pending = list(
                await db.scalars(
                    select(SummaryRecipientDelivery)
                    .where(
                        SummaryRecipientDelivery.batch_id == batch_id,
                        SummaryRecipientDelivery.workspace_id == batch.workspace_id,
                        SummaryRecipientDelivery.state == "pending",
                    )
                    .with_for_update()
                )
            )
            for row in pending:
                row.state, row.failure_code = "cancelled", "summary_delivery_deadline_expired"
            batch.failure_code = "summary_delivery_deadline_expired"
            await refresh_batch_state(db, batch)
            await db.commit()


async def recover_finished_dispatches(sessionmaker, *, temporal_client, now, limit):
    """A terminal workflow may have stopped before reserving every address."""
    context = MaintenanceTenantContext(
        operation_name="summary_delivery_reconciliation",
        actor_id="summary-delivery",
        reason_category="dispatch_recovery",
        feature_area="sharing",
    )
    async with sessionmaker() as db:
        await apply_tenant_context(db, context)
        rows = (
            await db.scalars(
                select(DispatchIntent)
                .where(
                    DispatchIntent.intent_kind == "summary_delivery",
                    DispatchIntent.state == "started",
                    DispatchIntent.next_attempt_at <= now,
                    DispatchIntent.lease_expires_at.is_(None)
                    | (DispatchIntent.lease_expires_at <= now),
                )
                .order_by(DispatchIntent.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
        jobs = []
        for row in rows:
            if row.external_workflow_id:
                row.lease_expires_at = now + timedelta(minutes=2)
                jobs.append((row.id, row.external_workflow_id))
        await db.commit()
    terminal = {
        WorkflowExecutionStatus.COMPLETED,
        WorkflowExecutionStatus.FAILED,
        WorkflowExecutionStatus.CANCELED,
        WorkflowExecutionStatus.TERMINATED,
        WorkflowExecutionStatus.TIMED_OUT,
    }
    for intent_id, workflow_id in jobs:
        status = None
        with suppress(Exception):
            status = (await temporal_client.get_workflow_handle(workflow_id).describe()).status
        async with sessionmaker() as db:
            await apply_tenant_context(db, context)
            row = await db.scalar(
                select(DispatchIntent).where(DispatchIntent.id == intent_id).with_for_update()
            )
            if row is None or row.state != "started" or row.external_workflow_id != workflow_id:
                continue
            row.lease_expires_at = None
            row.next_attempt_at = now + timedelta(seconds=30)
            if status not in terminal:
                await db.commit()
                continue
            batch = await db.get(SummaryDeliveryBatch, UUID(row.payload_json["batch_id"]))
            pending = list(
                await db.scalars(
                    select(SummaryRecipientDelivery).where(
                        SummaryRecipientDelivery.batch_id == UUID(row.payload_json["batch_id"]),
                        SummaryRecipientDelivery.workspace_id == row.workspace_id,
                        SummaryRecipientDelivery.state == "pending",
                    )
                )
            )
            if not pending or batch is None or batch.state in ("cancelled", "requires_review"):
                row.state, row.completed_at = "completed", now
                row.reconciliation_state = "completed"
            elif batch.deadline_at <= now:
                row.state = "cancelled"
            else:
                generation = int(row.payload_json.get("recovery_generation", 0)) + 1
                row.payload_json = {**row.payload_json, "recovery_generation": generation}
                row.state, row.reconciliation_state = "created", "pending"
                row.next_attempt_at = now + timedelta(seconds=min(300, 30 * generation))
                row.external_workflow_id = None
            await db.commit()


async def reconcile_summary_delivery_once(
    sessionmaker, *, settings, temporal_client, now=None, limit=50
):
    """Commit/start gap recovery uses deterministic per-intent workflow identities."""
    now = now or datetime.now(UTC)
    await finalize_expired_batches(sessionmaker, now=now, limit=limit)
    await recover_finished_dispatches(
        sessionmaker, temporal_client=temporal_client, now=now, limit=limit
    )
    async with sessionmaker() as db:
        await apply_tenant_context(
            db,
            MaintenanceTenantContext(
                operation_name="summary_delivery_reconciliation",
                actor_id="summary-delivery",
                reason_category="reservation_recovery",
                feature_area="sharing",
            ),
        )
        stale_batches = list(
            await db.scalars(
                select(SummaryRecipientDelivery.batch_id)
                .where(
                    SummaryRecipientDelivery.state == "sending",
                    SummaryRecipientDelivery.reserved_at <= now - timedelta(minutes=2),
                )
                .distinct()
                .limit(limit)
            )
        )
        await db.commit()
    for stale_id in stale_batches:
        async with sessionmaker() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="summary_delivery_reconciliation",
                    actor_id="summary-delivery",
                    reason_category="reservation_recovery",
                    feature_area="sharing",
                ),
            )
            batch = await db.get(SummaryDeliveryBatch, stale_id)
            if batch is None:
                continue
            await db.scalar(
                select(Meeting)
                .where(Meeting.id == batch.meeting_id, Meeting.workspace_id == batch.workspace_id)
                .with_for_update()
            )
            batch = await db.scalar(
                select(SummaryDeliveryBatch)
                .where(SummaryDeliveryBatch.id == stale_id)
                .with_for_update()
            )
            stale = (
                await db.scalars(
                    select(SummaryRecipientDelivery)
                    .where(
                        SummaryRecipientDelivery.batch_id == stale_id,
                        SummaryRecipientDelivery.state == "sending",
                        SummaryRecipientDelivery.reserved_at <= now - timedelta(minutes=2),
                    )
                    .with_for_update()
                )
            ).all()
            for recipient in stale:
                recipient.state, recipient.failure_code = "unknown", "summary_attempt_interrupted"
            await refresh_batch_state(db, batch)
            await db.commit()
    async with sessionmaker() as db:
        await apply_tenant_context(
            db,
            MaintenanceTenantContext(
                operation_name="summary_delivery_reconciliation",
                actor_id="summary-delivery",
                reason_category="dispatch_recovery",
                feature_area="sharing",
            ),
        )
        rows = (
            await db.scalars(
                select(DispatchIntent)
                .where(
                    DispatchIntent.intent_kind == "summary_delivery",
                    DispatchIntent.state.in_(("created", "start_unknown")),
                    DispatchIntent.next_attempt_at <= now,
                    (
                        DispatchIntent.lease_expires_at.is_(None)
                        | (DispatchIntent.lease_expires_at <= now)
                    ),
                )
                .order_by(DispatchIntent.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
        jobs = []
        for row in rows:
            batch = await db.scalar(
                select(SummaryDeliveryBatch).where(
                    SummaryDeliveryBatch.workspace_id == row.workspace_id,
                    SummaryDeliveryBatch.id == UUID(row.payload_json["batch_id"]),
                )
            )
            if (
                batch is None
                or batch.state in ("cancelled", "requires_review")
                or batch.deadline_at <= now
            ):
                row.state = "cancelled"
                continue
            row.lease_expires_at = now + timedelta(minutes=2)
            row.attempt_count += 1
            generation = int(row.payload_json.get("recovery_generation", 0))
            row.external_workflow_id = row.external_workflow_id or (
                f"summary-delivery:{row.id}:recovery:{generation}"
                if generation
                else f"summary-delivery:{row.id}"
            )
            jobs.append(
                (
                    row.id,
                    row.external_workflow_id,
                    {"workspace_id": str(row.workspace_id), "batch_id": str(batch.id)},
                )
            )
        await db.commit()
    for intent_id, workflow_id, payload in jobs:
        accepted = False
        try:
            await temporal_client.start_workflow(
                SummaryDeliveryWorkflow.run,
                payload,
                id=workflow_id,
                task_queue=settings.temporal_task_queue,
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
            )
            accepted = True
        except WorkflowAlreadyStartedError:
            accepted = True
        except Exception:
            pass
        async with sessionmaker() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="summary_delivery_reconciliation",
                    actor_id="summary-delivery",
                    reason_category="dispatch_recovery",
                    feature_area="sharing",
                ),
            )
            row = await db.get(DispatchIntent, intent_id)
            if row:
                row.state = "started" if accepted else "start_unknown"
                row.reconciliation_state = "started" if accepted else "pending"
                row.started_at = now if accepted else None
                row.lease_expires_at = None
                row.next_attempt_at = now + timedelta(
                    seconds=min(300, 5 * 2 ** min(row.attempt_count, 6))
                )
                await db.commit()
    return len(jobs)
