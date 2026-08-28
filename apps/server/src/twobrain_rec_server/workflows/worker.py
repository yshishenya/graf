from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import func, select

from twobrain_rec_server.auth.account_closure import (
    begin_account_close_finalization,
    finalize_account_close,
    list_due_account_closures,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.email_delivery import (
    EmailLoginDeliveryError,
    send_account_created_email,
    send_billing_notification,
    send_meeting_invitation,
)
from twobrain_rec_server.billing.entitlements import grant_confirmed_renewal
from twobrain_rec_server.billing.maintenance import reconcile_billing_maintenance
from twobrain_rec_server.billing.notifications import (
    MANDATORY_NOTIFICATION_KINDS,
    BillingNotification,
    NotificationEvent,
    notification_copy,
)
from twobrain_rec_server.billing.operations import provider_key_is_expired
from twobrain_rec_server.billing.renewal_charge import (
    charge_renewal_operation,
    pending_renewal_charge_candidates,
    plan_due_renewals,
    project_renewal_cutoffs,
)
from twobrain_rec_server.billing.webhook_reconciliation import (
    reconcile_pending_initial_checkout_operations,
    reconcile_pending_webhook_events,
)
from twobrain_rec_server.billing.yookassa import YooKassaClient
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.models import (
    AccountClosureRequest,
    BillingAuditEvent,
    BillingInvoice,
    BillingNotificationDelivery,
    BillingNotificationPreference,
    BillingOperation,
    ExternalIdentity,
    Meeting,
    MeetingShareInvitation,
    ProcessingWorkflow,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context,
    apply_tenant_scope,
)
from twobrain_rec_server.deletion.local_purge import reconcile_expired_local_purge_tasks
from twobrain_rec_server.deletion.service import (
    fanout_account_close_deletions,
    reconcile_deletion_purges,
    reconcile_source_retention_purges,
    reconcile_transient_media_purges,
)
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus, ProcessingStatus
from twobrain_rec_server.mediascribe.client import MediaScribeClient, MediaScribeClientError
from twobrain_rec_server.outcomes.ai_service import (
    OutcomeGenerationTerminalError,
    execute_candidate_generation,
    finalize_candidate_generation_failure,
    mark_candidate_generation_terminal_failure,
    publish_candidate_generation_calls,
    resolve_candidate_prompt,
    snapshot_candidate_transcript,
)
from twobrain_rec_server.outcomes.dispatch import (
    list_due_dispatch_intents,
    reconcile_dispatch_intent,
)
from twobrain_rec_server.processing import reasons, store
from twobrain_rec_server.processing.pickup import pick_up_processing
from twobrain_rec_server.processing.recovery import schedule_retry, schedule_retry_with_settings
from twobrain_rec_server.processing.store import ProcessingLifecycleBlocked
from twobrain_rec_server.processing.submit import (
    ManualUploadNormalizationPending,
    ManualUploadNormalizationTerminal,
    ProcessingUsageUnavailable,
    poll_and_import_mediascribe_result,
    submit_to_mediascribe,
)
from twobrain_rec_server.storage.minio_client import get_storage
from twobrain_rec_server.workflows.billing_reconciliation_workflow import (
    BILLING_RECONCILIATION_ACTIVITY_NAME,
    BillingReconciliationWorkflow,
    billing_reconciliation_task_queue,
    start_billing_reconciliation_workflow,
    validate_billing_reconciliation_payload,
)
from twobrain_rec_server.workflows.billing_renewal_workflow import (
    BILLING_RENEWAL_ACTIVITY_NAME,
    BillingRenewalWorkflow,
    billing_renewal_task_queue,
    start_billing_renewal_workflow,
    validate_billing_renewal_payload,
)
from twobrain_rec_server.workflows.invitation_delivery_workflow import (
    AccountCreatedEmailWorkflow,
    InvitationDeliveryWorkflow,
)
from twobrain_rec_server.workflows.outcome_generation_workflow import (
    OutcomeGenerationWorkflow,
    OutcomeObservabilityReconcilerWorkflow,
    TranscriptSnapshotError,
)
from twobrain_rec_server.workflows.processing_workflow import (
    PROCESSING_ACTIVITY_MAX_ATTEMPTS,
    MediaScribeProcessingWorkflow,
)
from twobrain_rec_server.workflows.temporal_client import (
    connect_temporal_client,
    outcome_generation_task_queue,
    processing_worker_identity,
)

logger = logging.getLogger(__name__)

BILLING_RENEWAL_RECONCILE_STATES = frozenset(
    {"scheduled", "sent", "processing", "unknown", "provider_key_expired"}
)
BILLING_RENEWAL_TERMINAL_STATES = frozenset({"succeeded", "canceled", "succeeded_refused"})
PROCESSING_ACTIVITY_HEARTBEAT_INTERVAL_SECONDS = 15


def _processing_activity_is_cancelled(activity_context: Any) -> bool:
    is_cancelled = getattr(activity_context, "is_cancelled", None)
    if is_cancelled is None:
        return False
    try:
        return bool(is_cancelled())
    except RuntimeError:
        # Direct unit callers do not have a Temporal activity context.
        return False


def _heartbeat_processing_activity(activity_context: Any, **details: Any) -> None:
    activity_context.heartbeat(details)
    if _processing_activity_is_cancelled(activity_context):
        raise asyncio.CancelledError


async def _await_processing_operation(
    operation: Any,
    *,
    activity_context: Any,
    state: str,
    meeting_id: str,
    heartbeat_interval_seconds: float = PROCESSING_ACTIVITY_HEARTBEAT_INTERVAL_SECONDS,
) -> Any:
    """Keep long provider/storage awaits heartbeating and cancellation-aware."""

    task = asyncio.ensure_future(operation)
    try:
        while not task.done():
            done, _ = await asyncio.wait(
                (task,),
                timeout=heartbeat_interval_seconds,
            )
            if task in done:
                break
            _heartbeat_processing_activity(
                activity_context,
                state=state,
                meeting_id=meeting_id,
            )
        return await task
    except asyncio.CancelledError:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        raise


def _provider_job_field(provider_job: Any, field_name: str) -> Any:
    """Read a bounded provider job field from DTOs and test doubles."""

    if isinstance(provider_job, dict):
        return provider_job.get(field_name)
    value = getattr(provider_job, field_name, None)
    if value is not None:
        return value
    extras = getattr(provider_job, "model_extra", None)
    return extras.get(field_name) if isinstance(extras, dict) else None


_PROVIDER_REQUEST_FINGERPRINT_FIELDS = (
    "request_fingerprint",
    "request_hash",
    "payload_fingerprint",
    "payload_hash",
    "fingerprint",
)


def _provider_request_fingerprint(provider_job: Any) -> tuple[bool, str | None]:
    """Read only an explicitly allowlisted, bounded provider fingerprint."""

    for field_name in _PROVIDER_REQUEST_FINGERPRINT_FIELDS:
        raw = _provider_job_field(provider_job, field_name)
        if raw is None:
            continue
        if not isinstance(raw, str):
            return True, None
        value = raw.strip()
        if (
            not value
            or len(value) > 128
            or any(ord(char) < 0x21 or ord(char) > 0x7E for char in value)
        ):
            return True, None
        return True, value
    return False, None


def _provider_request_matches_job(*, provider_job: Any, job: Any) -> bool:
    present, provider_fingerprint = _provider_request_fingerprint(provider_job)
    if not present:
        return True
    expected = getattr(job, "request_fingerprint", None)
    return isinstance(expected, str) and provider_fingerprint == expected


def _provider_job_status(provider_job: Any) -> MediaScribeJobStatus:
    raw_status = _provider_job_field(provider_job, "status")
    raw_status = getattr(raw_status, "value", raw_status)
    try:
        status = MediaScribeJobStatus(raw_status)
    except (TypeError, ValueError):
        # A future provider status must not make a recovered provider ID look
        # like a fresh upload. Polling will establish the next known state.
        return MediaScribeJobStatus.SUBMITTED
    if status in {
        MediaScribeJobStatus.NOT_SUBMITTED,
        MediaScribeJobStatus.SUBMITTING,
        MediaScribeJobStatus.BLOCKED,
    }:
        return MediaScribeJobStatus.SUBMITTED
    return status


def _is_unknown_mediascribe_upload(*, workflow: Any, job: Any) -> bool:
    if getattr(workflow, "status", None) == ProcessingStatus.BLOCKED_UNKNOWN.value:
        return True
    return (
        getattr(job, "last_error_code", None)
        == reasons.BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN
    )


async def _restore_unknown_processing_state(
    db: Any,
    *,
    workflow: Any,
    retry_after_seconds: int | None = None,
    schedule_next_retry: bool = False,
    settings: Any | None = None,
) -> Any | None:
    """Keep an unknown upload recoverable on its durable idempotency key."""

    current = await store.get_processing_workflow(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
        media_revision_id=workflow.media_revision_id,
        purpose=getattr(workflow, "purpose", "transcription"),
        active_only=False,
    )
    if current is None:
        return None
    current.status = ProcessingStatus.BLOCKED_UNKNOWN.value
    current.stage = "reconcile"
    current.retry_class = "unknown_outcome"
    current.last_reason_code = reasons.BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN
    if schedule_next_retry:
        retry_after = (
            timedelta(seconds=max(0, int(retry_after_seconds)))
            if retry_after_seconds is not None
            else None
        )
        scheduler = schedule_retry_with_settings if settings is not None else schedule_retry
        retry_schedule = (
            scheduler(
                settings,
                now=datetime.now(UTC),
                retry_count=int(current.retry_count or 0),
                generation=int(current.schedule_generation or 0),
                retry_after=retry_after,
                deadline_at=current.deadline_at,
                source="provider_retry_after" if retry_after is not None else None,
            )
            if settings is not None
            else scheduler(
                now=datetime.now(UTC),
                retry_count=int(current.retry_count or 0),
                generation=int(current.schedule_generation or 0),
                retry_after=retry_after,
                deadline_at=current.deadline_at,
                source="provider_retry_after" if retry_after is not None else None,
            )
        )
        current.next_attempt_at = retry_schedule.next_attempt_at
        current.next_attempt_source = retry_schedule.source
        current.schedule_generation = retry_schedule.generation
        current.retry_count = retry_schedule.retry_count
    else:
        current.next_attempt_at = None
        current.next_attempt_source = None
    current.ended_at = None
    if getattr(current, "archive_audio", True) is False:
        current.transient_state = "processing"
        current.transient_terminal_at = None
        current.transient_purge_due_at = None
    await db.commit()
    return current


def _next_poll_seconds(workflow: Any) -> str | None:
    next_attempt_at = getattr(workflow, "next_attempt_at", None)
    if next_attempt_at is None:
        return None
    if next_attempt_at.tzinfo is None:
        next_attempt_at = next_attempt_at.replace(tzinfo=UTC)
    return str(min(900, max(5, int((next_attempt_at - datetime.now(UTC)).total_seconds()))))


async def _reconcile_unknown_mediascribe_upload(
    db: Any,
    *,
    workflow: Any,
    job: Any | None,
    mediascribe_client: Any,
    settings: Any | None = None,
) -> Any | None:
    """Reconcile an uncertain POST when the provider job id is already known."""

    if job is None:
        await _restore_unknown_processing_state(db, workflow=workflow, settings=settings)
        return None

    external_job_id = getattr(job, "external_job_id", None)
    if not external_job_id:
        # A POST can time out after the provider accepted it.  The only
        # contract-backed reconciliation is replaying the exact request with
        # the same durable Idempotency-Key; submit_to_mediascribe owns that
        # replay on the next Temporal/manual cycle.
        return job

    provider_job: Any | None = None
    get_job = getattr(mediascribe_client, "get_job", None)
    if callable(get_job):
        try:
            provider_job = await get_job(external_job_id)
        except MediaScribeClientError as exc:
            await _restore_unknown_processing_state(
                db,
                workflow=workflow,
                retry_after_seconds=exc.retry_after_seconds,
                schedule_next_retry=exc.retryable,
                settings=settings,
            )
            return None
        if not _provider_request_matches_job(provider_job=provider_job, job=job):
            await _restore_unknown_processing_state(db, workflow=workflow, settings=settings)
            return None

    status = (
        _provider_job_status(provider_job)
        if provider_job is not None
        else MediaScribeJobStatus.SUBMITTED
    )
    # The fallback path already retained the opaque provider ID. Clear the
    # blocked projection so the normal poll/import path can advance it.
    job.status = status.value
    job.failed_at = None
    job.last_error_code = None
    job.last_error_message = None
    await db.commit()
    await _restore_unknown_processing_state(db, workflow=workflow, settings=settings)
    return job


def _provider_amount_minor(payment: dict[str, Any]) -> tuple[int, str]:
    amount = payment.get("amount")
    if not isinstance(amount, dict):
        raise ValueError("provider payment amount is missing")
    currency = amount.get("currency")
    if not isinstance(currency, str) or not currency:
        raise ValueError("provider payment currency is missing")
    try:
        decimal_value = Decimal(str(amount["value"]))
    except (InvalidOperation, KeyError, TypeError, ValueError) as exc:
        raise ValueError("provider payment amount is invalid") from exc
    minor_value = decimal_value * 100
    if (
        not decimal_value.is_finite()
        or decimal_value < 0
        or minor_value != minor_value.to_integral_value()
    ):
        raise ValueError("provider payment amount precision is invalid")
    return int(minor_value), currency


def _validate_authoritative_renewal_payment(
    payment: dict[str, Any],
    *,
    operation: BillingOperation,
    invoice: BillingInvoice,
) -> str:
    if payment.get("id") != operation.provider_id:
        raise ValueError("provider payment reference does not match")
    metadata = payment.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("provider payment metadata is missing")
    if metadata.get("workspace_id") != str(operation.workspace_id):
        raise ValueError("provider payment workspace does not match")
    if metadata.get("operation_id") != str(operation.id):
        raise ValueError("provider payment operation does not match")
    amount_minor, currency = _provider_amount_minor(payment)
    if amount_minor != invoice.amount_minor or currency != invoice.currency:
        raise ValueError("provider payment amount does not match")
    status = payment.get("status")
    if not isinstance(status, str) or not status:
        raise ValueError("provider payment status is missing")
    return status


async def run_billing_renewal_reconciler(settings: Any, temporal_client: object) -> None:
    """Plan one renewal, charge it once, then reconcile provider truth."""
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    context = MaintenanceTenantContext(
        operation_name="billing_reconciliation",
        actor_id="graf-maintenance",
        reason_category="renewal_provider_truth_recovery",
        feature_area="billing",
    )
    try:
        while True:
            try:
                async with sessionmaker() as db:
                    await apply_tenant_context(db, context)
                    now = datetime.now(UTC)
                    await project_renewal_cutoffs(db, now=now)
                    await plan_due_renewals(
                        db,
                        now=now,
                        provider_floor_minor=settings.billing_provider_floor_minor,
                    )
                    await db.commit()
                async with sessionmaker() as db:
                    await apply_tenant_context(db, context)
                    charge_candidates = await pending_renewal_charge_candidates(
                        db,
                        now=datetime.now(UTC),
                    )
                for operation_id, workspace_id in charge_candidates:
                    try:
                        async with sessionmaker() as db:
                            await apply_tenant_context(db, context)
                            await charge_renewal_operation(
                                db,
                                settings,
                                operation_id=operation_id,
                                workspace_id=workspace_id,
                            )
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        logger.exception("billing renewal charge attempt failed")
                async with sessionmaker() as db:
                    await apply_tenant_context(db, context)
                    rows = (
                        await db.execute(
                            select(BillingOperation.id, BillingOperation.workspace_id)
                            .join(Workspace, Workspace.id == BillingOperation.workspace_id)
                            .join(
                                WorkspaceSubscription,
                                WorkspaceSubscription.workspace_id == BillingOperation.workspace_id,
                            )
                            .join(
                                WorkspaceMembership,
                                WorkspaceMembership.workspace_id == BillingOperation.workspace_id,
                            )
                            .where(
                                Workspace.kind == "personal",
                                Workspace.owner_user_id == WorkspaceSubscription.billing_owner_id,
                                WorkspaceMembership.user_id
                                == WorkspaceSubscription.billing_owner_id,
                                WorkspaceMembership.role == "owner",
                                WorkspaceMembership.status == "active",
                                BillingOperation.kind == "renewal",
                                BillingOperation.provider_id.is_not(None),
                                BillingOperation.state.in_(BILLING_RENEWAL_RECONCILE_STATES),
                            )
                            .order_by(BillingOperation.updated_at, BillingOperation.id)
                            .limit(100)
                        )
                    ).all()
                for operation_id, workspace_id in rows:
                    await start_billing_renewal_workflow(
                        temporal_client=temporal_client,
                        settings=settings,
                        operation_id=operation_id,
                        workspace_id=workspace_id,
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("billing renewal reconciliation cycle failed")
            await asyncio.sleep(60)
    finally:
        await engine.dispose()


async def run_billing_reconciliation_reconciler(settings: Any, temporal_client: object) -> None:
    """Schedule one bounded maintenance workflow per five-minute UTC bucket."""
    try:
        while True:
            bucket = datetime.now(UTC).replace(second=0, microsecond=0)
            bucket = bucket.replace(minute=(bucket.minute // 5) * 5)
            run_id = uuid5(NAMESPACE_URL, f"graf-billing-reconciliation:{bucket.isoformat()}")
            try:
                await start_billing_reconciliation_workflow(
                    temporal_client=temporal_client,
                    settings=settings,
                    run_id=run_id,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("billing maintenance workflow scheduling failed")
            await asyncio.sleep(300)
    except asyncio.CancelledError:
        raise


async def run_billing_notification_reconciler(settings: Any) -> None:
    """Deliver bounded transactional notices exactly once per outbox row."""
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    context = MaintenanceTenantContext(
        # Reuse the existing narrowly-approved billing maintenance operation;
        # the observer is read-only and must not widen the RLS allowlist.
        operation_name="billing_reconciliation",
        actor_id="graf-maintenance",
        reason_category="durable_notification_backlog",
        feature_area="billing",
    )
    try:
        while True:
            try:
                async with sessionmaker() as db:
                    await apply_tenant_context(db, context)
                    verified_email = (
                        select(
                            ExternalIdentity.user_id,
                            func.min(ExternalIdentity.email).label("email"),
                        )
                        .where(
                            ExternalIdentity.email.is_not(None),
                            ExternalIdentity.is_active.is_(True),
                            ExternalIdentity.is_verified.is_(True),
                        )
                        .group_by(ExternalIdentity.user_id)
                        .subquery()
                    )
                    rows = (
                        await db.execute(
                            select(
                                BillingNotificationDelivery,
                                verified_email.c.email,
                                BillingNotificationPreference.optional_email_enabled,
                            )
                            .join(
                                verified_email,
                                verified_email.c.user_id
                                == BillingNotificationDelivery.recipient_id,
                            )
                            .outerjoin(
                                BillingNotificationPreference,
                                BillingNotificationPreference.user_id
                                == BillingNotificationDelivery.recipient_id,
                            )
                            .where(
                                BillingNotificationDelivery.channel == "email",
                                BillingNotificationDelivery.state.in_(("pending", "retry")),
                            )
                            .order_by(
                                BillingNotificationDelivery.created_at,
                                BillingNotificationDelivery.id,
                            )
                            .limit(50)
                        )
                    ).all()
                for row, recipient_email, optional_email_enabled in rows:
                    try:
                        kind = BillingNotification(row.template_key)
                        if (
                            kind not in MANDATORY_NOTIFICATION_KINDS
                            and optional_email_enabled is False
                        ):
                            async with sessionmaker() as db:
                                await apply_tenant_context(db, context)
                                suppressed = await db.scalar(
                                    select(BillingNotificationDelivery)
                                    .where(BillingNotificationDelivery.id == row.id)
                                    .with_for_update()
                                )
                                if suppressed is not None and suppressed.state in {
                                    "pending",
                                    "retry",
                                }:
                                    suppressed.state = "suppressed"
                                await db.commit()
                            continue
                        title, body = notification_copy(
                            NotificationEvent(
                                event_id=row.event_id,
                                kind=kind,
                                safe_payload=row.safe_payload or {},
                            ),
                            support_email=settings.billing_support_email,
                        )
                        action_path = (row.safe_payload or {}).get("action_path")
                        base_url = str(getattr(settings, "public_base_url", "")).rstrip("/")
                        action_url = (
                            f"{base_url}{action_path}"
                            if base_url and isinstance(action_path, str)
                            else None
                        )
                        plain = (
                            body
                            if action_url is None
                            else f"{body}\n\nОткрыть кабинет: {action_url}"
                        )
                        html = (
                            f"<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;"
                            f'max-width:560px;line-height:1.5"><h1>{escape(title)}</h1><p>{escape(body)}</p>'
                            + (
                                f'<p><a href="{escape(action_url, quote=True)}">Открыть кабинет</a></p>'
                                if action_url
                                else ""
                            )
                            + "</div>"
                        )
                        await send_billing_notification(
                            settings=settings,
                            recipient_email=str(recipient_email),
                            subject=title,
                            plain_body=plain,
                            html_body=html,
                            delivery_key=f"billing:{row.id}",
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        async with sessionmaker() as db:
                            await apply_tenant_context(db, context)
                            failed = await db.scalar(
                                select(BillingNotificationDelivery)
                                .where(BillingNotificationDelivery.id == row.id)
                                .with_for_update()
                            )
                            if failed is not None and failed.state in {"pending", "retry"}:
                                failed.attempts += 1
                                failed.last_error_code = type(exc).__name__[:64]
                                failed.state = "retry" if failed.attempts < 5 else "failed"
                            await db.commit()
                        logger.warning("billing notification delivery failed", exc_info=True)
                    else:
                        async with sessionmaker() as db:
                            await apply_tenant_context(db, context)
                            delivered = await db.scalar(
                                select(BillingNotificationDelivery)
                                .where(BillingNotificationDelivery.id == row.id)
                                .with_for_update()
                            )
                            if delivered is not None and delivered.state in {"pending", "retry"}:
                                delivered.state = "delivered"
                                delivered.delivered_at = datetime.now(UTC)
                            await db.commit()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("billing notification reconciliation cycle failed")
            await asyncio.sleep(60)
    finally:
        await engine.dispose()


async def run_account_closure_reconciler(
    settings: Any, temporal_client: object | None = None
) -> None:
    """Finalize due account-close cooling windows durably.

    The row is the source of truth and the loop is restart-safe.  A future
    Temporal workflow may claim the same IDs; row locks make duplicate claims
    harmless and no meeting deletion is falsely reported as complete here.
    """
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    storage = get_storage(settings)
    context = MaintenanceTenantContext(
        operation_name="billing_reconciliation",
        actor_id="graf-maintenance",
        reason_category="account_close_finalization",
        feature_area="account",
    )
    try:
        while True:
            try:
                async with sessionmaker() as db:
                    await apply_tenant_context(db, context)
                    request_ids = await list_due_account_closures(
                        db, now=datetime.now(UTC), limit=100
                    )
                for request_id in request_ids:
                    try:
                        async with sessionmaker() as db:
                            await apply_tenant_context(db, context)
                            request = await db.scalar(
                                select(AccountClosureRequest)
                                .where(AccountClosureRequest.id == request_id)
                                .with_for_update()
                            )
                            if request is None or request.state not in {
                                "scheduled",
                                "finalizing",
                                "blocked",
                            }:
                                continue
                            # Account closure reuses the already-audited meeting
                            # deletion path.  If storage or one purge is
                            # unavailable, keep the close blocked and retry only
                            # after an operator-visible reconciliation action.
                            _, workspace_ids = await begin_account_close_finalization(
                                db, request_id=request.id, now=datetime.now(UTC)
                            )
                            await db.commit()
                            for workspace_id in workspace_ids:
                                await fanout_account_close_deletions(
                                    db,
                                    workspace_id=workspace_id,
                                    storage=storage,
                                    temporal_client=temporal_client,
                                )
                            await finalize_account_close(
                                db, request_id=request_id, now=datetime.now(UTC)
                            )
                            await db.commit()
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        logger.exception("account close finalization blocked")
                        async with sessionmaker() as db:
                            await apply_tenant_context(db, context)
                            blocked = await db.scalar(
                                select(AccountClosureRequest)
                                .where(AccountClosureRequest.id == request_id)
                                .with_for_update()
                            )
                            if blocked is not None and blocked.state in {
                                "scheduled",
                                "finalizing",
                                "blocked",
                            }:
                                blocked.state = "blocked"
                                blocked.failure_reason = type(exc).__name__[:240]
                                blocked.metadata_json = {
                                    **(blocked.metadata_json or {}),
                                    "blocked_reason": "meeting_deletion_fanout_failed",
                                }
                                await db.commit()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("account close reconciliation cycle failed")
            await asyncio.sleep(30)
    finally:
        close_storage = getattr(storage, "close", None)
        if close_storage is not None:
            close_storage()
        await engine.dispose()


async def run_billing_reconciliation_activity(payload: dict[str, str]) -> dict[str, int | str]:
    """Run one bounded billing maintenance pass; provider mutations are out of scope."""
    from temporalio.exceptions import ApplicationError

    try:
        safe_payload = validate_billing_reconciliation_payload(payload)
    except ValueError as exc:
        raise ApplicationError(
            "billing_reconciliation_payload_invalid",
            type="BillingReconciliationInvalidPayload",
            non_retryable=True,
        ) from exc
    settings = get_settings()
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    context = MaintenanceTenantContext(
        operation_name="billing_reconciliation",
        actor_id="graf-workflow-worker",
        reason_category="billing_maintenance",
        feature_area="billing",
    )
    try:
        async with sessionmaker() as db:
            await apply_tenant_context(db, context)
            counters = await reconcile_billing_maintenance(db)
            webhook_counters = await reconcile_pending_webhook_events(db, settings)
            initial_checkout_counters = await reconcile_pending_initial_checkout_operations(
                db, settings
            )
            await db.commit()
        return {
            "run_id": safe_payload["run_id"],
            **counters,
            **{f"webhook_{k}": v for k, v in webhook_counters.items()},
            **{f"initial_checkout_{k}": v for k, v in initial_checkout_counters.items()},
        }
    finally:
        await engine.dispose()


async def run_billing_renewal_activity(payload: dict[str, str]) -> dict[str, str]:
    """Observe provider truth for one persisted renewal operation.

    This activity is deliberately observation-only at the provider boundary.
    A retry repeats GET for the same operation and can never create another
    payment or idempotency key.
    """
    from temporalio.exceptions import ApplicationError

    try:
        safe_payload = validate_billing_renewal_payload(payload)
    except ValueError as exc:
        raise ApplicationError(
            "billing_renewal_payload_invalid",
            type="BillingRenewalInvalidPayload",
            non_retryable=True,
        ) from exc

    operation_id = UUID(safe_payload["operation_id"])
    workspace_id = UUID(safe_payload["workspace_id"])
    settings = get_settings()
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    context = MaintenanceTenantContext(
        operation_name="billing_reconciliation",
        actor_id="graf-workflow-worker",
        reason_category="renewal_provider_truth_recovery",
        feature_area="billing",
    )
    try:
        async with sessionmaker() as db:
            await apply_tenant_context(db, context)
            operation = await db.scalar(
                select(BillingOperation)
                .where(
                    BillingOperation.id == operation_id,
                    BillingOperation.workspace_id == workspace_id,
                )
                .with_for_update()
            )
            if operation is None or operation.kind != "renewal":
                raise ApplicationError(
                    "billing_renewal_operation_invalid",
                    type="BillingRenewalInvalidPayload",
                    non_retryable=True,
                )
            if operation.state in BILLING_RENEWAL_TERMINAL_STATES:
                return {"operation_id": str(operation_id), "status": operation.state}
            if operation.provider_id is None:
                raise ApplicationError(
                    "billing_renewal_provider_reference_missing",
                    type="BillingRenewalProviderMismatch",
                    non_retryable=True,
                )
            invoice = await db.scalar(
                select(BillingInvoice)
                .where(
                    BillingInvoice.operation_id == operation_id,
                    BillingInvoice.workspace_id == workspace_id,
                )
                .with_for_update()
            )
            if invoice is None:
                raise ApplicationError(
                    "billing_renewal_invoice_missing",
                    type="BillingRenewalProviderMismatch",
                    non_retryable=True,
                )
            workspace = await db.get(Workspace, workspace_id)
            subscription = await db.scalar(
                select(WorkspaceSubscription)
                .where(WorkspaceSubscription.workspace_id == workspace_id)
                .with_for_update()
            )
            owner = None
            if (
                workspace is not None
                and workspace.kind == "personal"
                and workspace.owner_user_id is not None
            ):
                owner = await db.scalar(
                    select(WorkspaceMembership)
                    .where(
                        WorkspaceMembership.workspace_id == workspace_id,
                        WorkspaceMembership.user_id == workspace.owner_user_id,
                        WorkspaceMembership.role == "owner",
                        WorkspaceMembership.status == "active",
                    )
                    .with_for_update()
                )
            if (
                owner is None
                or subscription is None
                or subscription.billing_owner_id != owner.user_id
            ):
                operation.state = "manual_resolution"
                invoice.status = "manual_resolution"
                if subscription is not None:
                    if subscription.recurring_allowed:
                        subscription.recurring_allowed = False
                        subscription.recurring_authority_version = (
                            subscription.recurring_authority_version or 0
                        ) + 1
                    subscription.renewal_resolution = "workspace_scope_invalid"
                await db.commit()
                return {"operation_id": str(operation_id), "status": "manual_resolution"}
            provider_id = operation.provider_id

        try:
            async with YooKassaClient(settings) as provider:
                payment = await provider.get_payment(provider_id)
        except Exception as exc:
            raise ApplicationError(
                "billing_provider_observation_unavailable",
                type="BillingProviderObservationUnavailable",
            ) from exc

        async with sessionmaker() as db:
            await apply_tenant_context(db, context)
            operation = await db.scalar(
                select(BillingOperation)
                .where(
                    BillingOperation.id == operation_id,
                    BillingOperation.workspace_id == workspace_id,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if operation is None or operation.kind != "renewal":
                raise ApplicationError(
                    "billing_renewal_operation_invalid",
                    type="BillingRenewalInvalidPayload",
                    non_retryable=True,
                )
            if operation.state in BILLING_RENEWAL_TERMINAL_STATES:
                return {"operation_id": str(operation_id), "status": operation.state}
            invoice = await db.scalar(
                select(BillingInvoice).where(
                    BillingInvoice.operation_id == operation_id,
                    BillingInvoice.workspace_id == workspace_id,
                )
            )
            if invoice is None or operation.provider_id != provider_id:
                raise ApplicationError(
                    "billing_renewal_provider_binding_changed",
                    type="BillingRenewalProviderMismatch",
                    non_retryable=True,
                )
            try:
                provider_status = _validate_authoritative_renewal_payment(
                    payment,
                    operation=operation,
                    invoice=invoice,
                )
            except ValueError as exc:
                raise ApplicationError(
                    "billing_renewal_provider_truth_mismatch",
                    type="BillingRenewalProviderMismatch",
                    non_retryable=True,
                ) from exc

            subscription = await db.scalar(
                select(WorkspaceSubscription)
                .where(WorkspaceSubscription.workspace_id == workspace_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            now = datetime.now(UTC)
            key_expired = provider_key_is_expired(
                expires_at=operation.provider_key_expires_at,
                now=now,
            )
            previous_state = operation.state

            if provider_status == "succeeded":
                grant_starts_at = now
                if (
                    not key_expired
                    and subscription is not None
                    and subscription.paid_through is not None
                ):
                    grant_starts_at = max(
                        grant_starts_at, subscription.paid_through.astimezone(UTC)
                    )
                grant_status = await grant_confirmed_renewal(
                    db,
                    workspace_id=workspace_id,
                    provider_payment_id=provider_id,
                    amount_minor=invoice.amount_minor,
                    currency=invoice.currency,
                    grant_starts_at=grant_starts_at,
                )
                if grant_status not in {"granted", "duplicate", "refused"}:
                    raise ApplicationError(
                        "billing_renewal_entitlement_projection_failed",
                        type="BillingRenewalProviderMismatch",
                        non_retryable=True,
                    )
                if grant_status != "refused":
                    operation.state = "succeeded"
                    if subscription is not None:
                        subscription.renewal_resolution = (
                            "late_success" if key_expired else "succeeded"
                        )
                    if key_expired and grant_status == "granted":
                        db.add(
                            BillingAuditEvent(
                                workspace_id=workspace_id,
                                action="renewal_late_success_observed",
                                target_kind="billing_operation",
                                target_ref=str(operation_id),
                                outcome="observed",
                                reason_code="provider_success_after_key_expiry",
                                metadata_json={},
                            )
                        )
            elif provider_status in {"canceled", "cancelled"}:
                operation.state = "canceled"
                invoice.status = "canceled"
                if subscription is not None:
                    subscription.renewal_resolution = "canceled"
            else:
                operation.state = "provider_key_expired" if key_expired else "unknown"
                if subscription is not None:
                    subscription.renewal_resolution = (
                        "provider_key_expired" if key_expired else "pending"
                    )
                if key_expired and previous_state != "provider_key_expired":
                    db.add(
                        BillingAuditEvent(
                            workspace_id=workspace_id,
                            action="renewal_resolution_gap",
                            target_kind="billing_operation",
                            target_ref=str(operation_id),
                            outcome="unknown",
                            reason_code="provider_key_expired",
                            metadata_json={},
                        )
                    )
            result_state = operation.state
            await db.commit()

            if result_state == "unknown":
                raise ApplicationError(
                    "billing_provider_outcome_unknown",
                    type="BillingProviderOutcomeUnknown",
                )
            return {"operation_id": str(operation_id), "status": result_state}
    finally:
        await engine.dispose()


async def run_dispatch_reconciler(settings: Any, temporal_client: object) -> None:
    """Retry durable candidate dispatches without relying on a user request."""
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    try:
        while True:
            try:
                async with sessionmaker() as db:
                    await apply_tenant_context(
                        db,
                        MaintenanceTenantContext(
                            operation_name="outcome_dispatch_reconciliation",
                            actor_id="graf-workflow-worker",
                            reason_category="durable_dispatch_retry",
                            feature_area="content_regeneration",
                        ),
                    )
                    intents = await list_due_dispatch_intents(db, limit=100)
                    # list_due_dispatch_intents may project expired leases on
                    # intent rows. Flush that projection before the first
                    # Meeting fence so autoflush cannot invert locks.
                    await db.commit()
                    for intent in intents:
                        await reconcile_dispatch_intent(
                            db,
                            intent=intent,
                            settings=settings,
                            temporal_client=temporal_client,
                        )
            except Exception:
                logger.exception("outcome dispatch reconciliation cycle failed")
            await asyncio.sleep(5)
    finally:
        await engine.dispose()


async def run_deletion_purge_reconciler(settings: Any, temporal_client: object) -> None:
    """Converge committed deletion tombstones after process/storage failures."""
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    storage = get_storage(settings)
    context = MaintenanceTenantContext(
        operation_name="deletion_purge_reconciliation",
        actor_id="graf-workflow-worker",
        reason_category="durable_deletion_retry",
        feature_area="content_regeneration",
    )
    try:
        while True:
            try:
                async with sessionmaker() as db:
                    await apply_tenant_context(db, context)
                    await reconcile_expired_local_purge_tasks(db, limit=500)
                    await db.commit()
                    await reconcile_deletion_purges(
                        db,
                        storage=storage,
                        temporal_client=temporal_client,
                        limit=20,
                    )
                    await reconcile_transient_media_purges(
                        db,
                        storage=storage,
                        limit=20,
                    )
                    if settings.retention_source_audio_days is not None:
                        await reconcile_source_retention_purges(
                            db,
                            storage=storage,
                            retention_period=timedelta(days=settings.retention_source_audio_days),
                            policy_version=settings.retention_source_audio_policy_version,
                            backup_expiry_days=settings.retention_backup_expiry_days,
                            limit=20,
                        )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("deletion purge reconciliation cycle failed")
            await asyncio.sleep(15)
    finally:
        close_storage = getattr(storage, "close", None)
        if close_storage is not None:
            close_storage()
        await engine.dispose()


async def reconcile_stale_processing_starts(
    db: Any,
    *,
    settings: Any,
    temporal_client: object,
    now: datetime | None = None,
    limit: int = 25,
) -> int:
    if limit <= 0:
        return 0
    missing_limit = 1 if settings.processing_enabled else 0
    missing = (
        await store.claim_missing_processing_start_intents(
            db,
            now=now,
            limit=missing_limit,
        )
        if missing_limit
        else []
    )
    stale_limit = limit - len(missing)
    intents = (
        await store.claim_stale_processing_start_intents(
            db,
            now=now,
            limit=stale_limit,
        )
        if stale_limit
        else []
    )
    # Candidate enumeration is advisory; canonical pickup owns the row locks
    # and idempotency fences.
    await db.rollback()
    reconciled = 0
    for intent in intents:
        result = await pick_up_processing(
            db=db,
            settings=settings,
            workspace_id=intent.workspace_id,
            meeting_id=intent.meeting_id,
            limit=1,
            temporal_client=temporal_client,
        )
        if result.started_count or result.reused_count or result.blocked_count:
            reconciled += 1
    for intent in missing:
        result = await pick_up_processing(
            db=db,
            settings=settings,
            workspace_id=intent.workspace_id,
            meeting_id=intent.meeting_id,
            limit=1,
            temporal_client=temporal_client,
            archive_audio=intent.archive_audio,
            expected_media_revision_id=intent.media_revision_id,
            processing_intent_session_id=intent.upload_session_id,
        )
        if result.started_count or result.reused_count or result.blocked_count:
            reconciled += 1
    return reconciled


async def run_processing_start_reconciler(settings: Any, temporal_client: object) -> None:
    """Recover committed Temporal start intents without another user request."""

    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    try:
        while True:
            try:
                async with sessionmaker() as db:
                    await apply_tenant_context(
                        db,
                        MaintenanceTenantContext(
                            operation_name="processing_recovery_reconciliation",
                            actor_id="graf-maintenance",
                            reason_category="durable_start_recovery",
                            feature_area="content_regeneration",
                        ),
                    )
                    await reconcile_stale_processing_starts(
                        db,
                        settings=settings,
                        temporal_client=temporal_client,
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("processing start reconciliation cycle failed")
            await asyncio.sleep(15)
    finally:
        await engine.dispose()


def invitation_delivery_failure_state(
    error: EmailLoginDeliveryError,
) -> tuple[str, str]:
    """Keep pre-egress failures distinct from an unknown provider outcome."""
    return (
        "outcome_unknown" if error.outcome_unknown else "failed",
        error.reason_code,
    )


async def run_processing_pipeline_activity(
    payload: dict[str, str],
    *,
    settings: Any | None = None,
    sessionmaker: Any | None = None,
    storage: object | None = None,
    mediascribe_client: MediaScribeClient | None = None,
) -> dict[str, str]:
    from temporalio import activity

    meeting_ref = payload.get("meeting_id", "unknown")
    media_revision_id: UUID | None = None
    _heartbeat_processing_activity(activity, state="starting", meeting_id=meeting_ref)
    try:
        tenant_scope = tenant_scope_from_processing_payload(payload)
        meeting_id = UUID(payload["meeting_id"])
        if payload.get("media_revision_id"):
            media_revision_id = UUID(payload["media_revision_id"])
        workspace_id = UUID(payload["workspace_id"])
    except (KeyError, ValueError):
        return {
            "meeting_id": meeting_ref,
            "processing_status": ProcessingStatus.BLOCKED.value,
            "reason_code": reasons.BLOCKED_UNAUTHORIZED,
        }
    settings = settings or get_settings()
    single_step = payload.get("single_step") == "true"
    owned_engine = None
    if sessionmaker is None:
        owned_engine = create_engine(settings)
        sessionmaker = create_sessionmaker(owned_engine)
    try:
        mediascribe_client = mediascribe_client or MediaScribeClient.from_settings(settings)
        storage = storage or get_storage(settings)
        async with sessionmaker() as db:
            await apply_tenant_scope(db, tenant_scope, context_kind="worker")
            workflow = await store.get_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                active_only=True,
            )
            if media_revision_id is None:
                latest_revision = await store.latest_media_revision_for_meeting(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                )
                if latest_revision is not None:
                    raise ProcessingLifecycleBlocked("processing_source_revision_stale")
            if workflow is None:
                raise ProcessingLifecycleBlocked("processing_workflow_missing")
            job = await store.get_mediascribe_job(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=workflow.media_revision_id,
                processing_workflow_id=workflow.id,
                active_only=False,
            )
            if _is_unknown_mediascribe_upload(workflow=workflow, job=job):
                job = await _reconcile_unknown_mediascribe_upload(
                    db,
                    workflow=workflow,
                    job=job,
                    mediascribe_client=mediascribe_client,
                    settings=settings,
                )
                if job is None:
                    return {
                        "meeting_id": payload.get("meeting_id", meeting_ref),
                        "processing_status": ProcessingStatus.BLOCKED_UNKNOWN.value,
                        "reason_code": reasons.BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
                        **(
                            {"next_poll_seconds": _next_poll_seconds(workflow)}
                            if _next_poll_seconds(workflow)
                            else {}
                        ),
                    }
            _heartbeat_processing_activity(
                activity,
                state="submitting",
                meeting_id=meeting_ref,
            )
            try:
                submit_result = await _await_processing_operation(
                    submit_to_mediascribe(
                        db=db,
                        settings=settings,
                        storage=storage,
                        mediascribe_client=mediascribe_client,
                        workflow=workflow,
                    ),
                    activity_context=activity,
                    state="submitting",
                    meeting_id=meeting_ref,
                )
                job = submit_result.job
            except ManualUploadNormalizationPending as exc:
                now = datetime.now(UTC)
                next_attempt_at = exc.next_attempt_at
                if next_attempt_at is not None and next_attempt_at.tzinfo is None:
                    next_attempt_at = next_attempt_at.replace(tzinfo=UTC)
                delay = (
                    max(5, min(int((next_attempt_at - now).total_seconds()), 900))
                    if next_attempt_at is not None
                    else 900
                )
                return {
                    "meeting_id": payload.get("meeting_id", meeting_ref),
                    "processing_status": "normalization_pending",
                    "reason_code": exc.reason_code,
                    "next_poll_seconds": str(delay),
                    **(
                        {"next_attempt_at": next_attempt_at.isoformat()}
                        if next_attempt_at is not None
                        else {}
                    ),
                }
            except ManualUploadNormalizationTerminal as exc:
                return {
                    "meeting_id": payload.get("meeting_id", meeting_ref),
                    "processing_status": (
                        ProcessingStatus.CANCELED.value
                        if exc.cancelled
                        else ProcessingStatus.FAILED_TERMINAL.value
                    ),
                    "reason_code": exc.reason_code,
                }
            except ProcessingUsageUnavailable as exc:
                return {
                    "meeting_id": payload.get("meeting_id", meeting_ref),
                    "processing_status": ProcessingStatus.BLOCKED.value,
                    "reason_code": str(exc),
                }
            except MediaScribeClientError as exc:
                if exc.reason_code != reasons.BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN:
                    raise
                # The ambiguous attempt is durably recorded. Replaying the
                # exact same POST belongs to the next workflow/manual cycle;
                # never poll a job whose opaque provider id is unknown.
                workflow = (
                    await _restore_unknown_processing_state(
                        db,
                        workflow=workflow,
                        retry_after_seconds=exc.retry_after_seconds,
                        schedule_next_retry=True,
                        settings=settings,
                    )
                    or workflow
                )
                return {
                    "meeting_id": payload.get("meeting_id", meeting_ref),
                    "processing_status": ProcessingStatus.BLOCKED_UNKNOWN.value,
                    "reason_code": reasons.BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
                    **(
                        {"next_poll_seconds": _next_poll_seconds(workflow)}
                        if _next_poll_seconds(workflow)
                        else {}
                    ),
                }
            _heartbeat_processing_activity(
                activity,
                state="submitted",
                meeting_id=meeting_ref,
            )
            if single_step and workflow.status == ProcessingStatus.WAITING_RETRY.value:
                return {
                    "meeting_id": payload["meeting_id"],
                    "processing_status": ProcessingStatus.WAITING_RETRY.value,
                    "next_poll_seconds": _next_poll_seconds(workflow) or "30",
                }
            deadline_at = workflow.deadline_at
            if deadline_at is not None and workflow.manual_claimed_at is None:
                if deadline_at.tzinfo is None:
                    deadline_at = deadline_at.replace(tzinfo=UTC)
                if deadline_at <= datetime.now(UTC):
                    workflow.retry_class = "retryable"
                    workflow.next_attempt_at = None
                    workflow.next_attempt_source = None
                    await store.set_workflow_status(
                        db,
                        workflow,
                        ProcessingStatus.FAILED_RETRYABLE,
                        reason_code="processing_retry_deadline_exceeded",
                    )
                    return {
                        "meeting_id": payload["meeting_id"],
                        "processing_status": ProcessingStatus.FAILED_RETRYABLE.value,
                        "reason_code": "processing_retry_deadline_exceeded",
                    }
            poll_attempts = 1 if single_step else settings.processing_max_poll_attempts
            for poll_attempt in range(poll_attempts):
                _heartbeat_processing_activity(
                    activity,
                    state="polling",
                    meeting_id=meeting_ref,
                    poll_attempt=poll_attempt + 1,
                )
                import_result = await _await_processing_operation(
                    poll_and_import_mediascribe_result(
                        db=db,
                        workflow=workflow,
                        job=job,
                        mediascribe_client=mediascribe_client,
                        outcome_generation_enabled=settings.outcome_generation_enabled,
                    ),
                    activity_context=activity,
                    state="polling",
                    meeting_id=meeting_ref,
                )
                _heartbeat_processing_activity(
                    activity,
                    state="poll_complete",
                    meeting_id=meeting_ref,
                    poll_attempt=poll_attempt + 1,
                )
                if import_result.status == ProcessingStatus.PROCESSED:
                    return {"meeting_id": payload["meeting_id"], "processing_status": "processed"}
                if import_result.status in {
                    ProcessingStatus.BLOCKED,
                    ProcessingStatus.BLOCKED_UNKNOWN,
                    ProcessingStatus.CANCELED,
                    ProcessingStatus.FAILED_TERMINAL,
                }:
                    return {
                        "meeting_id": payload["meeting_id"],
                        "processing_status": import_result.status.value,
                    }
                if single_step:
                    schedule = schedule_retry_with_settings(
                        settings,
                        respect_max_attempts=False,
                        now=datetime.now(UTC),
                        retry_count=int(workflow.retry_count or 0),
                        generation=int(workflow.schedule_generation or 0),
                        retry_after=timedelta(
                            seconds=max(0, int(getattr(job, "retry_after_seconds", 0) or 0))
                        )
                        if getattr(job, "retry_after_seconds", None) is not None
                        else None,
                        provider_next_attempt_at=getattr(job, "provider_next_retry_at", None),
                        deadline_at=workflow.deadline_at,
                        source=(
                            "provider_retry_after"
                            if getattr(job, "retry_after_seconds", None) is not None
                            else None
                        ),
                    )
                    if schedule.next_attempt_at is None:
                        deadline_exceeded = schedule.stop_reason == "deadline_exceeded"
                        reason_code = (
                            "processing_retry_deadline_exceeded"
                            if deadline_exceeded
                            else "processing_recovery_attempt_limit_exceeded"
                        )
                        workflow.retry_class = "retryable" if deadline_exceeded else "terminal"
                        workflow.next_attempt_at = None
                        workflow.next_attempt_source = None
                        await store.set_workflow_status(
                            db,
                            workflow,
                            ProcessingStatus.FAILED_RETRYABLE
                            if deadline_exceeded
                            else ProcessingStatus.FAILED_TERMINAL,
                            reason_code=reason_code,
                            terminal=not deadline_exceeded,
                        )
                        return {
                            "meeting_id": payload["meeting_id"],
                            "processing_status": (
                                ProcessingStatus.FAILED_RETRYABLE
                                if deadline_exceeded
                                else ProcessingStatus.FAILED_TERMINAL
                            ).value,
                            "reason_code": reason_code,
                        }
                    workflow.retry_class = "retryable"
                    workflow.retry_count = schedule.retry_count
                    workflow.schedule_generation = schedule.generation
                    workflow.next_attempt_at = schedule.next_attempt_at
                    workflow.next_attempt_source = schedule.source
                    await store.set_workflow_status(
                        db,
                        workflow,
                        ProcessingStatus.WAITING_RETRY,
                        reason_code=workflow.last_reason_code or "provider_result_not_ready",
                    )
                    seconds = (
                        max(5, int((schedule.next_attempt_at - datetime.now(UTC)).total_seconds()))
                        if schedule.next_attempt_at is not None
                        else 30
                    )
                    return {
                        "meeting_id": payload["meeting_id"],
                        "processing_status": ProcessingStatus.WAITING_RETRY.value,
                        "next_poll_seconds": str(min(seconds, 900)),
                    }
                await _await_processing_operation(
                    asyncio.sleep(settings.processing_poll_interval_seconds),
                    activity_context=activity,
                    state="poll_wait",
                    meeting_id=meeting_ref,
                )
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.FAILED_RETRYABLE,
                reason_code="mediascribe_poll_limit_exceeded",
                terminal=False,
            )
            return {
                "meeting_id": payload["meeting_id"],
                "processing_status": ProcessingStatus.FAILED_RETRYABLE.value,
                "reason_code": "mediascribe_poll_limit_exceeded",
            }
    except ProcessingLifecycleBlocked as exc:
        if str(exc) == "processing_source_revision_stale":
            # A stale callback can omit its revision id after a newer source
            # is accepted. Terminalize only older active workflows; never let
            # that callback leave a stale row visible to reconciliation.
            try:
                async with sessionmaker() as stale_db:
                    await apply_tenant_scope(stale_db, tenant_scope, context_kind="worker")
                    await store.cancel_stale_revision_workflows(
                        stale_db,
                        workspace_id=workspace_id,
                        meeting_id=meeting_id,
                        reason_code=str(exc),
                    )
            except Exception:
                logger.exception("failed to cancel stale processing workflow")
        # Do not reopen or retry a canceled workflow through the provider-error
        # path. The stale-source helper above commits its terminal transition.
        return {
            "meeting_id": payload.get("meeting_id", meeting_ref),
            "processing_status": ProcessingStatus.CANCELED.value,
            "reason_code": str(exc),
        }
    except MediaScribeClientError as exc:
        if exc.reason_code == reasons.BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN:
            await _restore_unknown_processing_state(
                db,
                workflow=workflow,
                retry_after_seconds=exc.retry_after_seconds,
                schedule_next_retry=True,
                settings=settings,
            )
            return {
                "meeting_id": payload.get("meeting_id", meeting_ref),
                "processing_status": ProcessingStatus.BLOCKED_UNKNOWN.value,
                "reason_code": reasons.BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
            }
        status = _processing_status_for_client_error(exc)
        try:
            activity_attempt = activity.info().attempt
        except RuntimeError:
            activity_attempt = 1
        exhausted = exc.retryable and activity_attempt >= PROCESSING_ACTIVITY_MAX_ATTEMPTS
        if exhausted:
            status = ProcessingStatus.FAILED_TERMINAL
            reason_code = "processing_recovery_attempt_limit_exceeded"
        else:
            reason_code = exc.reason_code
        try:
            persisted = await _persist_activity_client_error(
                sessionmaker,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                tenant_scope=tenant_scope,
                status=status,
                reason_code=reason_code,
                retry_after_seconds=exc.retry_after_seconds,
                settings=settings,
            )
        except ProcessingLifecycleBlocked as blocked:
            return {
                "meeting_id": payload.get("meeting_id", meeting_ref),
                "processing_status": ProcessingStatus.CANCELED.value,
                "reason_code": str(blocked),
            }
        status = ProcessingStatus(persisted.status)
        reason_code = persisted.last_reason_code or reason_code
        next_poll_seconds = _next_poll_seconds(persisted)
        return {
            "meeting_id": payload["meeting_id"],
            "processing_status": (
                ProcessingStatus.WAITING_RETRY.value
                if status == ProcessingStatus.FAILED_RETRYABLE and next_poll_seconds is not None
                else status.value
            ),
            **(
                {"reason_code": reason_code}
                if status in {ProcessingStatus.BLOCKED, ProcessingStatus.FAILED_TERMINAL}
                or exhausted
                or (status == ProcessingStatus.FAILED_RETRYABLE and next_poll_seconds is None)
                else {}
            ),
            **({"next_poll_seconds": next_poll_seconds} if next_poll_seconds is not None else {}),
        }
    except RuntimeError as exc:
        classified = _processing_status_for_runtime_error(exc)
        if classified is None:
            raise
        status, retryable = classified
        try:
            activity_attempt = activity.info().attempt
        except RuntimeError:
            activity_attempt = 1
        exhausted = retryable and activity_attempt >= PROCESSING_ACTIVITY_MAX_ATTEMPTS
        if exhausted:
            status = ProcessingStatus.FAILED_TERMINAL
        reason_code = str(exc)
        try:
            persisted = await _persist_activity_client_error(
                sessionmaker,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                tenant_scope=tenant_scope,
                status=status,
                reason_code=reason_code,
                settings=settings,
            )
        except ProcessingLifecycleBlocked as blocked:
            return {
                "meeting_id": payload.get("meeting_id", meeting_ref),
                "processing_status": ProcessingStatus.CANCELED.value,
                "reason_code": str(blocked),
            }
        status = ProcessingStatus(persisted.status)
        reason_code = persisted.last_reason_code or reason_code
        next_poll_seconds = _next_poll_seconds(persisted)
        return {
            "meeting_id": payload["meeting_id"],
            "processing_status": (
                ProcessingStatus.WAITING_RETRY.value
                if status == ProcessingStatus.FAILED_RETRYABLE and next_poll_seconds is not None
                else status.value
            ),
            "reason_code": reason_code,
            **({"next_poll_seconds": next_poll_seconds} if next_poll_seconds is not None else {}),
        }
    finally:
        if owned_engine is not None:
            await owned_engine.dispose()


async def resolve_outcome_prompt_config_activity(payload: dict[str, str]) -> dict[str, Any]:
    settings = get_settings()
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    try:
        try:
            return await resolve_candidate_prompt(
                sessionmaker,
                settings=settings,
                workspace_id=UUID(payload["workspace_id"]),
                candidate_id=UUID(payload["candidate_id"]),
            )
        except OutcomeGenerationTerminalError as exc:
            await mark_candidate_generation_terminal_failure(
                sessionmaker,
                workspace_id=UUID(payload["workspace_id"]),
                candidate_id=UUID(payload["candidate_id"]),
                failure_code=str(exc),
            )
            raise
    finally:
        await engine.dispose()


async def snapshot_outcome_transcript_metadata_activity(
    payload: dict[str, str],
) -> dict[str, Any]:
    settings = get_settings()
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    try:
        try:
            metadata, _ = await snapshot_candidate_transcript(
                sessionmaker,
                workspace_id=UUID(payload["workspace_id"]),
                candidate_id=UUID(payload["candidate_id"]),
                settings=settings,
            )
        except (OutcomeGenerationTerminalError, TranscriptSnapshotError) as exc:
            await mark_candidate_generation_terminal_failure(
                sessionmaker,
                workspace_id=UUID(payload["workspace_id"]),
                candidate_id=UUID(payload["candidate_id"]),
                failure_code=str(exc),
            )
            raise
        return metadata
    finally:
        await engine.dispose()


async def snapshot_outcome_transcript_chunk_activity(
    payload: dict[str, Any],
) -> dict[str, Any]:
    settings = get_settings()
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    try:
        try:
            _, chunks = await snapshot_candidate_transcript(
                sessionmaker,
                workspace_id=UUID(str(payload["workspace_id"])),
                candidate_id=UUID(str(payload["candidate_id"])),
                settings=settings,
            )
        except (OutcomeGenerationTerminalError, TranscriptSnapshotError) as exc:
            await mark_candidate_generation_terminal_failure(
                sessionmaker,
                workspace_id=UUID(str(payload["workspace_id"])),
                candidate_id=UUID(str(payload["candidate_id"])),
                failure_code=str(exc),
            )
            raise
        index = int(payload["chunk_index"])
        if index < 0 or index >= len(chunks):
            raise ValueError("outcome transcript chunk index is invalid")
        return chunks[index]
    finally:
        await engine.dispose()


async def execute_outcome_generation_activity(payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    try:
        try:
            return await execute_candidate_generation(
                sessionmaker,
                workspace_id=UUID(str(payload["workspace_id"])),
                candidate_id=UUID(str(payload["candidate_id"])),
                expected_snapshot_hash=str(payload["snapshot_hash"]),
                settings=settings,
            )
        except OutcomeGenerationTerminalError as exc:
            await mark_candidate_generation_terminal_failure(
                sessionmaker,
                workspace_id=UUID(str(payload["workspace_id"])),
                candidate_id=UUID(str(payload["candidate_id"])),
                failure_code=str(exc),
            )
            raise
    finally:
        await engine.dispose()


async def finalize_outcome_generation_failure_activity(
    payload: dict[str, Any],
) -> dict[str, str]:
    settings = get_settings()
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    try:
        await finalize_candidate_generation_failure(
            sessionmaker,
            workspace_id=UUID(str(payload["workspace_id"])),
            candidate_id=UUID(str(payload["candidate_id"])),
            failure_code=str(payload.get("failure_code") or "summary_generation_retries_exhausted")[
                :120
            ],
            failure_reason=(
                str(payload["failure_reason"]) if payload.get("failure_reason") else None
            ),
        )
        return {"candidate_id": str(payload["candidate_id"]), "status": "failed"}
    finally:
        await engine.dispose()


async def publish_outcome_observability_activity(payload: dict[str, Any]) -> dict[str, Any]:
    from temporalio import activity

    settings = get_settings()
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    try:
        info = activity.info()
        result = await publish_candidate_generation_calls(
            sessionmaker,
            workspace_id=UUID(str(payload["workspace_id"])),
            candidate_id=UUID(str(payload["candidate_id"])),
            settings=settings,
            activity_attempt=info.attempt,
            temporal_workflow_id=str(payload.get("generation_workflow_id") or info.workflow_id),
            temporal_run_id=str(payload.get("generation_workflow_run_id") or info.workflow_run_id),
            temporal_activity_id=info.activity_id,
        )
        return {"candidate_id": str(payload["candidate_id"]), **result}
    finally:
        await engine.dispose()


async def deliver_meeting_invitation_activity(payload: dict[str, str]) -> dict[str, str]:
    from temporalio.exceptions import ApplicationError

    from twobrain_rec_server.api.problems import ProblemDetail
    from twobrain_rec_server.cabinet.access import (
        lock_shareable_meeting,
        open_invitation_delivery,
    )
    from twobrain_rec_server.cabinet.egress import record_egress_audit_event
    from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context

    settings = get_settings()
    invitation_id = UUID(payload["invitation_id"])
    workspace_id = UUID(payload["workspace_id"])
    if settings.credential_encryption_key_file is None:
        raise ApplicationError("invitation_key_unavailable", non_retryable=True)
    key = settings.credential_encryption_key_file.read_bytes().strip()
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    tenant_context = TenantDatabaseContext(
        organization_id=UUID(int=0),
        workspace_id=workspace_id,
        user_id=UUID(int=0),
        context_kind="worker",
    )
    try:
        async with sessionmaker() as db:
            await apply_tenant_context(db, tenant_context)

            async def cancel_invitation(reserved: MeetingShareInvitation, reason: str) -> None:
                reserved.status = "cancelled"
                reserved.failure_code = reason
                reserved.encrypted_delivery_address = ""
                reserved.encrypted_recipient_address = None
                await record_egress_audit_event(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=reserved.meeting_id,
                    actor_user_id=reserved.invited_by_user_id,
                    device_id=None,
                    event_type="share_invitation_cancelled",
                    outcome="failed",
                    policy_reason=reason,
                )
                await db.commit()

            invitation = await db.get(MeetingShareInvitation, invitation_id)
            if invitation is None:
                raise ApplicationError("invitation_not_committed", non_retryable=False)
            if invitation.workspace_id != workspace_id:
                return {"invitation_id": str(invitation_id), "status": "not_found"}
            if invitation.status == "sending":
                # Join the canonical meeting -> invitation lock order and
                # re-read the state. A late Temporal attempt must never replace
                # a newer sent, accepted, or revoked state with `outcome_unknown`.
                try:
                    await lock_shareable_meeting(
                        db,
                        workspace_id=workspace_id,
                        meeting_id=invitation.meeting_id,
                    )
                except ProblemDetail:
                    await cancel_invitation(invitation, "meeting_unavailable_before_delivery")
                    return {
                        "invitation_id": str(invitation_id),
                        "status": "meeting_unavailable",
                    }
                invitation = await db.scalar(
                    select(MeetingShareInvitation)
                    .where(
                        MeetingShareInvitation.id == invitation_id,
                        MeetingShareInvitation.workspace_id == workspace_id,
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                if invitation is None:
                    return {"invitation_id": str(invitation_id), "status": "not_found"}
                if invitation.status != "sending":
                    return {
                        "invitation_id": str(invitation_id),
                        "status": invitation.status,
                    }
                invitation.status = "outcome_unknown"
                invitation.failure_code = "postal_delivery_outcome_unknown"
                invitation.encrypted_delivery_address = ""
                invitation.encrypted_recipient_address = None
                await record_egress_audit_event(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=invitation.meeting_id,
                    actor_user_id=invitation.invited_by_user_id,
                    device_id=None,
                    event_type="share_invitation_outcome_unknown",
                    outcome="failed",
                    policy_reason="postal_delivery_outcome_unknown",
                )
                await db.commit()
                return {"invitation_id": str(invitation_id), "status": "outcome_unknown"}
            if invitation.status != "pending":
                return {"invitation_id": str(invitation_id), "status": invitation.status}
            try:
                await lock_shareable_meeting(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=invitation.meeting_id,
                )
            except ProblemDetail:
                await cancel_invitation(invitation, "meeting_unavailable_before_delivery")
                return {"invitation_id": str(invitation_id), "status": "meeting_unavailable"}
            invitation = await db.scalar(
                select(MeetingShareInvitation)
                .where(
                    MeetingShareInvitation.id == invitation_id,
                    MeetingShareInvitation.workspace_id == workspace_id,
                    MeetingShareInvitation.status == "pending",
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if invitation is None:
                return {"invitation_id": str(invitation_id), "status": "cancelled"}
            if invitation.expires_at <= datetime.now(UTC):
                invitation.status = "expired"
                invitation.encrypted_delivery_address = ""
                invitation.encrypted_recipient_address = None
                await db.commit()
                return {"invitation_id": str(invitation_id), "status": "expired"}
            try:
                address, raw_token = open_invitation_delivery(
                    invitation.encrypted_delivery_address,
                    key=key,
                )
            except ProblemDetail as exc:
                invitation.status = "failed"
                invitation.failure_code = exc.code
                invitation.encrypted_delivery_address = ""
                invitation.encrypted_recipient_address = None
                await record_egress_audit_event(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=invitation.meeting_id,
                    actor_user_id=invitation.invited_by_user_id,
                    device_id=None,
                    event_type="share_invitation_failed",
                    outcome="failed",
                    policy_reason=exc.code,
                )
                await db.commit()
                raise ApplicationError(exc.code, non_retryable=True) from exc
            acceptance_url = (
                f"{str(settings.public_base_url).rstrip('/')}/share-invitations/{raw_token}"
                f"?workspace_id={workspace_id}"
            )
            invitation.status = "sending"
            invitation.failure_code = None
            await record_egress_audit_event(
                db,
                workspace_id=workspace_id,
                meeting_id=invitation.meeting_id,
                actor_user_id=invitation.invited_by_user_id,
                device_id=None,
                event_type="share_invitation_delivery_started",
                outcome="prepared",
                policy_reason="postal_delivery_attempt_reserved",
            )
            await db.commit()

            # A committed `sending` state is the at-most-once fence. Reacquire the
            # canonical meeting -> invitation locks before network egress so a
            # concurrent revoke either wins before send or waits for its outcome.
            await apply_tenant_context(db, tenant_context)
            try:
                await lock_shareable_meeting(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=invitation.meeting_id,
                )
            except ProblemDetail:
                await cancel_invitation(invitation, "meeting_unavailable_after_reservation")
                return {"invitation_id": str(invitation_id), "status": "meeting_unavailable"}
            invitation = await db.scalar(
                select(MeetingShareInvitation)
                .where(
                    MeetingShareInvitation.id == invitation_id,
                    MeetingShareInvitation.workspace_id == workspace_id,
                    MeetingShareInvitation.status == "sending",
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if invitation is None:
                return {"invitation_id": str(invitation_id), "status": "cancelled"}
            meeting = await db.get(Meeting, invitation.meeting_id)
            if meeting is None:
                await cancel_invitation(invitation, "meeting_unavailable_after_reservation")
                return {"invitation_id": str(invitation_id), "status": "meeting_unavailable"}
            inviter = await db.get(UserIdentity, invitation.invited_by_user_id)
            try:
                await send_meeting_invitation(
                    settings=settings,
                    recipient_email=address,
                    acceptance_url=acceptance_url,
                    delivery_key=str(invitation.id),
                    content_scope=invitation.content_scope,
                    inviter_name=inviter.display_name if inviter is not None else None,
                    meeting_title=meeting.title,
                    occurred_at=meeting.started_at or meeting.created_at,
                    duration_seconds=meeting.duration_seconds,
                    expires_at=invitation.expires_at,
                )
            except EmailLoginDeliveryError as exc:
                invitation.status, invitation.failure_code = invitation_delivery_failure_state(exc)
                invitation.encrypted_delivery_address = ""
                invitation.encrypted_recipient_address = None
                await record_egress_audit_event(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=invitation.meeting_id,
                    actor_user_id=invitation.invited_by_user_id,
                    device_id=None,
                    event_type=(
                        "share_invitation_outcome_unknown"
                        if exc.outcome_unknown
                        else "share_invitation_failed"
                    ),
                    outcome="failed",
                    policy_reason=exc.reason_code,
                )
                await db.commit()
                raise ApplicationError(exc.reason_code, non_retryable=True) from exc
            invitation.status = "sent"
            invitation.sent_at = datetime.now(UTC)
            invitation.failure_code = None
            invitation.encrypted_delivery_address = ""
            await record_egress_audit_event(
                db,
                workspace_id=workspace_id,
                meeting_id=invitation.meeting_id,
                actor_user_id=invitation.invited_by_user_id,
                device_id=None,
                event_type="share_invitation_sent",
                outcome="allowed",
                policy_reason="postal_delivery_accepted",
            )
            await db.commit()
            return {"invitation_id": str(invitation_id), "status": "sent"}
    finally:
        await engine.dispose()


async def send_account_created_email_activity(payload: dict[str, str]) -> dict[str, str]:
    from temporalio.exceptions import ApplicationError

    from twobrain_rec_server.api.problems import ProblemDetail
    from twobrain_rec_server.cabinet.access import lock_shareable_meeting
    from twobrain_rec_server.cabinet.egress import record_egress_audit_event
    from twobrain_rec_server.db.tenant_context import (
        TenantDatabaseContext,
        WorkspaceAuthContext,
        apply_tenant_context,
    )

    settings = get_settings()
    invitation_id = UUID(payload["invitation_id"])
    workspace_id = UUID(payload["workspace_id"])
    organization_id = UUID(payload["organization_id"])
    user_id = UUID(payload["user_id"])
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    tenant_context = TenantDatabaseContext(
        organization_id=organization_id,
        workspace_id=workspace_id,
        user_id=UUID(int=0),
        context_kind="worker",
    )

    async def set_delivery_state(
        db,
        invitation: MeetingShareInvitation,
        *,
        status: str,
        failure_code: str | None = None,
        event_type: str,
        outcome: str,
    ) -> None:
        invitation.account_created_email_status = status
        invitation.account_created_email_failure_code = failure_code
        await record_egress_audit_event(
            db,
            workspace_id=workspace_id,
            meeting_id=invitation.meeting_id,
            actor_user_id=user_id,
            device_id=None,
            event_type=event_type,
            outcome=outcome,
            policy_reason=failure_code or "postal_delivery_accepted",
        )
        await db.commit()

    try:
        async with sessionmaker() as db:
            await apply_tenant_context(db, tenant_context)
            invitation = await db.get(MeetingShareInvitation, invitation_id)
            if invitation is None or invitation.workspace_id != workspace_id:
                raise ApplicationError("invitation_not_committed", non_retryable=False)
            if invitation.account_created_email_status == "sending":
                try:
                    await lock_shareable_meeting(
                        db,
                        workspace_id=workspace_id,
                        meeting_id=invitation.meeting_id,
                    )
                except ProblemDetail:
                    return {"invitation_id": str(invitation_id), "status": "meeting_unavailable"}
                invitation = await db.scalar(
                    select(MeetingShareInvitation)
                    .where(
                        MeetingShareInvitation.id == invitation_id,
                        MeetingShareInvitation.workspace_id == workspace_id,
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                if invitation is None:
                    raise ApplicationError("invitation_not_committed", non_retryable=False)
                if invitation.account_created_email_status != "sending":
                    return {
                        "invitation_id": str(invitation_id),
                        "status": invitation.account_created_email_status,
                    }
                await set_delivery_state(
                    db,
                    invitation,
                    status="outcome_unknown",
                    failure_code="postal_delivery_outcome_unknown",
                    event_type="share_account_created_email_outcome_unknown",
                    outcome="failed",
                )
                return {"invitation_id": str(invitation_id), "status": "outcome_unknown"}
            if invitation.account_created_email_status != "pending":
                return {
                    "invitation_id": str(invitation_id),
                    "status": invitation.account_created_email_status,
                }
            try:
                await lock_shareable_meeting(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=invitation.meeting_id,
                )
            except ProblemDetail:
                await set_delivery_state(
                    db,
                    invitation,
                    status="failed",
                    failure_code="meeting_unavailable_before_delivery",
                    event_type="share_account_created_email_failed",
                    outcome="failed",
                )
                return {"invitation_id": str(invitation_id), "status": "failed"}
            invitation = await db.scalar(
                select(MeetingShareInvitation)
                .where(
                    MeetingShareInvitation.id == invitation_id,
                    MeetingShareInvitation.workspace_id == workspace_id,
                    MeetingShareInvitation.account_created_email_status == "pending",
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if invitation is None:
                return {"invitation_id": str(invitation_id), "status": "not_found"}
            meeting = await db.get(Meeting, invitation.meeting_id)
            await apply_tenant_context(
                db,
                WorkspaceAuthContext(
                    workspace_id=workspace_id,
                    organization_id=organization_id,
                    context_kind="auth_bootstrap",
                ),
            )
            identity = await db.scalar(
                select(ExternalIdentity).where(
                    ExternalIdentity.user_id == user_id,
                    ExternalIdentity.is_active.is_(True),
                    ExternalIdentity.is_verified.is_(True),
                    ExternalIdentity.email.is_not(None),
                )
            )
            await apply_tenant_context(db, tenant_context)
            if meeting is None or identity is None or not identity.email:
                await set_delivery_state(
                    db,
                    invitation,
                    status="failed",
                    failure_code="account_email_identity_missing",
                    event_type="share_account_created_email_failed",
                    outcome="failed",
                )
                return {"invitation_id": str(invitation_id), "status": "failed"}
            invitation.account_created_email_status = "sending"
            invitation.account_created_email_failure_code = None
            await record_egress_audit_event(
                db,
                workspace_id=workspace_id,
                meeting_id=invitation.meeting_id,
                actor_user_id=user_id,
                device_id=None,
                event_type="share_account_created_email_delivery_started",
                outcome="prepared",
                policy_reason="postal_delivery_attempt_reserved",
            )
            await db.commit()

            await apply_tenant_context(db, tenant_context)
            try:
                await lock_shareable_meeting(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=invitation.meeting_id,
                )
            except ProblemDetail:
                invitation = await db.get(MeetingShareInvitation, invitation_id)
                if invitation is not None:
                    await set_delivery_state(
                        db,
                        invitation,
                        status="failed",
                        failure_code="meeting_unavailable_after_reservation",
                        event_type="share_account_created_email_failed",
                        outcome="failed",
                    )
                return {"invitation_id": str(invitation_id), "status": "failed"}
            invitation = await db.scalar(
                select(MeetingShareInvitation)
                .where(
                    MeetingShareInvitation.id == invitation_id,
                    MeetingShareInvitation.workspace_id == workspace_id,
                    MeetingShareInvitation.account_created_email_status == "sending",
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            meeting = await db.get(Meeting, invitation.meeting_id) if invitation else None
            if invitation is None or meeting is None:
                return {"invitation_id": str(invitation_id), "status": "not_found"}
            try:
                base_url = str(settings.public_base_url).rstrip("/")
                await send_account_created_email(
                    settings=settings,
                    recipient_email=str(identity.email),
                    meeting_title=meeting.title,
                    content_scope=invitation.content_scope,
                    graf_url=f"{base_url}/meetings",
                    settings_url=f"{base_url}/settings",
                    delivery_key=f"account-created:{invitation.id}",
                )
            except EmailLoginDeliveryError as exc:
                await set_delivery_state(
                    db,
                    invitation,
                    status="outcome_unknown" if exc.outcome_unknown else "failed",
                    failure_code=exc.reason_code,
                    event_type=(
                        "share_account_created_email_outcome_unknown"
                        if exc.outcome_unknown
                        else "share_account_created_email_failed"
                    ),
                    outcome="failed",
                )
                raise ApplicationError(exc.reason_code, non_retryable=True) from exc
            invitation.account_created_email_status = "sent"
            invitation.account_created_email_sent_at = datetime.now(UTC)
            invitation.account_created_email_failure_code = None
            await record_egress_audit_event(
                db,
                workspace_id=workspace_id,
                meeting_id=invitation.meeting_id,
                actor_user_id=user_id,
                device_id=None,
                event_type="share_account_created_email_sent",
                outcome="allowed",
                policy_reason="postal_delivery_accepted",
            )
            await db.commit()
            return {"invitation_id": str(invitation_id), "status": "sent"}
    finally:
        await engine.dispose()


def _processing_status_for_client_error(exc: MediaScribeClientError) -> ProcessingStatus:
    if exc.reason_code in {
        reasons.BLOCKED_CONFIG,
    }:
        return ProcessingStatus.BLOCKED
    if exc.reason_code == reasons.BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN:
        return ProcessingStatus.BLOCKED_UNKNOWN
    if exc.reason_code == reasons.MEDIASCRIBE_MALFORMED_RESPONSE:
        return ProcessingStatus.FAILED_TERMINAL
    return ProcessingStatus.FAILED_RETRYABLE if exc.retryable else ProcessingStatus.FAILED_TERMINAL


def _processing_status_for_runtime_error(
    exc: RuntimeError,
) -> tuple[ProcessingStatus, bool] | None:
    reason_code = str(exc)
    if reason_code == reasons.BLOCKED_MISSING_ARTIFACTS:
        return ProcessingStatus.BLOCKED, False
    if reason_code == reasons.PROCESSING_TEMP_STORAGE_UNAVAILABLE:
        return ProcessingStatus.FAILED_RETRYABLE, True
    return None


def _required_uuid_from_payload(payload: dict[str, str], field_name: str) -> UUID:
    value = payload.get(field_name)
    if not value:
        raise ValueError(f"missing tenant scope field: {field_name}")
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError(f"invalid tenant scope field: {field_name}") from exc


def tenant_scope_from_processing_payload(payload: dict[str, str]) -> TenantScope:
    required = {"organization_id", "workspace_id", "user_id", "device_id"}
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"missing tenant scope fields: {', '.join(missing)}")
    auth_session_id = payload.get("auth_session_id")
    return TenantScope(
        organization_id=_required_uuid_from_payload(payload, "organization_id"),
        workspace_id=_required_uuid_from_payload(payload, "workspace_id"),
        user_id=_required_uuid_from_payload(payload, "user_id"),
        device_id=_required_uuid_from_payload(payload, "device_id"),
        auth_session_id=UUID(auth_session_id) if auth_session_id else None,
    )


async def _persist_activity_client_error(
    sessionmaker,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
    tenant_scope: TenantScope | None = None,
    status: ProcessingStatus,
    reason_code: str,
    retry_after_seconds: int | None = None,
    settings: Any | None = None,
) -> ProcessingWorkflow:
    async with sessionmaker() as db:
        if tenant_scope is not None:
            await apply_tenant_scope(db, tenant_scope, context_kind="worker")
        workflow = await store.get_processing_workflow(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
        if media_revision_id is None:
            latest_revision = await store.latest_media_revision_for_meeting(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
            )
            if latest_revision is not None:
                raise ProcessingLifecycleBlocked("processing_source_revision_stale")
        if workflow is None:
            raise ProcessingLifecycleBlocked("processing_workflow_missing")
        if status == ProcessingStatus.BLOCKED_UNKNOWN:
            restored = await _restore_unknown_processing_state(
                db,
                workflow=workflow,
                settings=settings,
            )
            if restored is None:
                raise ProcessingLifecycleBlocked("processing_workflow_missing")
            return restored
        terminal = status in {ProcessingStatus.BLOCKED, ProcessingStatus.FAILED_TERMINAL}
        already_persisted = (
            workflow.status == status.value
            and workflow.last_reason_code == reason_code
            and (not terminal or workflow.ended_at is not None)
        )
        if already_persisted and (
            status != ProcessingStatus.FAILED_RETRYABLE or workflow.next_attempt_at is not None
        ):
            return workflow
        if status == ProcessingStatus.FAILED_RETRYABLE:
            scheduler = schedule_retry_with_settings if settings is not None else schedule_retry
            schedule_kwargs = {
                "now": datetime.now(UTC),
                "retry_count": int(workflow.retry_count or 0),
                "generation": int(workflow.schedule_generation or 0),
                "retry_after": (
                    timedelta(seconds=max(0, int(retry_after_seconds)))
                    if retry_after_seconds is not None
                    else None
                ),
                "deadline_at": workflow.deadline_at,
                "source": "provider_retry_after" if retry_after_seconds is not None else None,
            }
            schedule = (
                scheduler(settings, respect_max_attempts=False, **schedule_kwargs)
                if settings is not None
                else scheduler(**schedule_kwargs)
            )
            workflow.next_attempt_at = schedule.next_attempt_at
            workflow.next_attempt_source = schedule.source
            workflow.schedule_generation = schedule.generation
            workflow.retry_count = schedule.retry_count
            workflow.retry_class = "retryable"
            if schedule.next_attempt_at is None:
                if schedule.stop_reason == "deadline_exceeded":
                    reason_code = "processing_retry_deadline_exceeded"
                else:
                    status = ProcessingStatus.FAILED_TERMINAL
                    reason_code = "processing_recovery_attempt_limit_exceeded"
                    terminal = True
                    workflow.retry_class = "terminal"
        return await store.set_workflow_status(
            db,
            workflow,
            status,
            reason_code=reason_code,
            terminal=terminal,
        )


async def _run_temporal_workers(workers: list[Any]) -> None:
    worker_tasks = [asyncio.create_task(worker.run()) for worker in workers]
    try:
        await asyncio.gather(*worker_tasks)
    finally:
        for task in worker_tasks:
            task.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)


async def run_worker() -> None:
    from temporalio import activity
    from temporalio.worker import Worker

    settings = get_settings()
    if settings.prompt_optimization_enabled:
        raise RuntimeError("prompt optimization must run in the operations-only worker")
    processing_client = await connect_temporal_client(settings)
    processing_engine = create_engine(settings)
    processing_sessionmaker = create_sessionmaker(processing_engine)
    processing_storage = get_storage(settings)
    processing_mediascribe_client = (
        MediaScribeClient.from_settings(settings, reuse_connections=True)
        if settings.processing_enabled
        else None
    )

    async def processing_activity_impl(payload: dict[str, str]) -> dict[str, str]:
        return await run_processing_pipeline_activity(
            payload,
            settings=settings,
            sessionmaker=processing_sessionmaker,
            storage=processing_storage,
            mediascribe_client=processing_mediascribe_client,
        )

    processing_activity = activity.defn(name="run_processing_pipeline_activity")(
        processing_activity_impl
    )
    billing_renewal_activity = activity.defn(name=BILLING_RENEWAL_ACTIVITY_NAME)(
        run_billing_renewal_activity
    )
    billing_reconciliation_activity = activity.defn(name=BILLING_RECONCILIATION_ACTIVITY_NAME)(
        run_billing_reconciliation_activity
    )
    outcome_activities = [
        activity.defn(name="resolve_outcome_prompt_config_activity")(
            resolve_outcome_prompt_config_activity
        ),
        activity.defn(name="snapshot_outcome_transcript_metadata_activity")(
            snapshot_outcome_transcript_metadata_activity
        ),
        activity.defn(name="snapshot_outcome_transcript_chunk_activity")(
            snapshot_outcome_transcript_chunk_activity
        ),
        activity.defn(name="execute_outcome_generation_activity")(
            execute_outcome_generation_activity
        ),
        activity.defn(name="finalize_outcome_generation_failure_activity")(
            finalize_outcome_generation_failure_activity
        ),
        activity.defn(name="publish_outcome_observability_activity")(
            publish_outcome_observability_activity
        ),
    ]
    invitation_activity = activity.defn(name="deliver_meeting_invitation_activity")(
        deliver_meeting_invitation_activity
    )
    account_created_email_activity = activity.defn(name="send_account_created_email_activity")(
        send_account_created_email_activity
    )
    processing_worker = Worker(
        processing_client,
        task_queue=settings.temporal_task_queue,
        workflows=[
            MediaScribeProcessingWorkflow,
            InvitationDeliveryWorkflow,
            AccountCreatedEmailWorkflow,
        ],
        activities=[processing_activity, invitation_activity, account_created_email_activity],
        identity=processing_worker_identity(),
    )
    billing_renewal_worker = Worker(
        processing_client,
        task_queue=billing_renewal_task_queue(settings),
        workflows=[BillingRenewalWorkflow],
        activities=[billing_renewal_activity],
        identity=f"{processing_worker_identity()}:billing-renewal",
    )
    billing_reconciliation_worker = Worker(
        processing_client,
        task_queue=billing_reconciliation_task_queue(settings),
        workflows=[BillingReconciliationWorkflow],
        activities=[billing_reconciliation_activity],
        identity=f"{processing_worker_identity()}:billing-reconciliation",
    )
    workers = [processing_worker, billing_renewal_worker, billing_reconciliation_worker]
    if settings.outcome_generation_enabled:
        traced_client = await connect_temporal_client(
            settings,
            identity=f"{processing_worker_identity()}:ai",
            outcome_tracing=True,
        )
        if settings.outcome_generation_enabled:
            outcome_worker = Worker(
                traced_client,
                task_queue=outcome_generation_task_queue(settings),
                workflows=[
                    OutcomeGenerationWorkflow,
                    OutcomeObservabilityReconcilerWorkflow,
                ],
                activities=outcome_activities,
                identity=f"{processing_worker_identity()}:outcomes",
            )
            workers.append(outcome_worker)
    try:
        await _run_temporal_workers(workers)
    finally:
        if processing_mediascribe_client is not None:
            await processing_mediascribe_client.aclose()
        close_storage = getattr(processing_storage, "close", None)
        if close_storage is not None:
            close_storage()
        await processing_engine.dispose()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
