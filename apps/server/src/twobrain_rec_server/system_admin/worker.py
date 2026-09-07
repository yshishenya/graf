"""Maintenance dispatcher: atomically admit a domain effect, then observe it.

Only the maintenance login runs this module. The web console never receives
product-table DML or storage writer credentials. Existing Temporal/start and deletion
reconcilers recover the committed domain effect; this loop never resubmits it.
"""

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.billing.admin_grants import create_adjustment, revoke_adjustment
from twobrain_rec_server.db.models import Meeting, MeetingDeletionRequest, ProcessingWorkflow
from twobrain_rec_server.db.models.billing import (
    BillingAccessAdjustment,
    BillingAccessRevocation,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
from twobrain_rec_server.deletion.service import BOUNDED_DELETE_COPY, request_meeting_deletion
from twobrain_rec_server.domain.statuses import DeletionRequestSource
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.dispatch import dispatch_created_processing_attempt
from twobrain_rec_server.processing.pickup import _processing_tenant_scope
from twobrain_rec_server.storage.minio_client import get_storage
from twobrain_rec_server.system_admin.operations import decode_command

logger = logging.getLogger(__name__)


async def _result(db: AsyncSession, claim: dict, state: str, *, error: str | None = None) -> None:
    function = "record_system_operation_failure" if error else "record_system_operation_result"
    accepted = await db.scalar(text(
        f"select system_control.{function}(:id,:target,:fence,:ref,:state)"
    ), {"id": UUID(claim["operation_id"]), "target": UUID(claim["target_id"]),
        "fence": claim["attempt_fence"], "ref": UUID(claim["domain_ref"]), "state": error or state})
    if not accepted:
        raise RuntimeError("system operation result fence rejected")
    await db.commit()


async def _observe(db: AsyncSession, claim: dict) -> None:
    command = decode_command(claim["command"])
    domain_id = UUID(claim["domain_ref"])
    state = "awaiting_reconciliation"
    if command.kind == "meeting.reprocess":
        row = await db.get(ProcessingWorkflow, domain_id)
        if row is not None:
            if row.status == "processed":
                state = "succeeded"
            elif row.status in {"failed_terminal", "blocked", "canceled"}:
                state = "failed"
    else:
        row = await db.get(MeetingDeletionRequest, domain_id)
        if row is not None:
            if row.state == "complete":
                state = "succeeded"
            elif row.state in {"terminal_failed", "policy_blocked"}:
                state = "failed"
    # A missing domain reference is not permission to create another effect.
    await _result(db, claim, state, error=("processing_failed" if command.kind == "meeting.reprocess"
                                         else "deletion_failed") if state == "failed" else None)


async def execute_operation(
    db: AsyncSession, *, operation_id: UUID, target_id: UUID,
    settings, temporal_client, storage,
) -> None:
    parameters = {"id": operation_id, "target": target_id}
    # Route billing commands through their dedicated claim first. The generic
    # meeting claim intentionally rejects unknown kinds and would otherwise
    # cancel a valid subscription command as ``authority_revoked``.
    claim = await db.scalar(text("select system_control.claim_subscription_operation(:id,:target)"), parameters)
    if claim is None:
        claim = await db.scalar(text("select system_control.claim_system_operation(:id,:target)"), parameters)
    if claim is None:
        claim = await db.scalar(text("select system_control.resume_system_operation(:id,:target)"), parameters)
        if claim is None:
            await db.commit()  # Includes any cancellation/version-conflict decision.
            return
    raw_command = claim["command"]
    if isinstance(raw_command, str):
        import json
        raw_command = json.loads(raw_command)
    if raw_command.get("kind") in {"subscription.adjust", "subscription.adjustment.revoke"}:
        if claim["mode"] != "start":
            await _observe_subscription_operation(db, claim, raw_command)
            return
        await _execute_subscription_operation(db, claim)
        return
    command = decode_command(raw_command)
    await apply_tenant_context(db, MaintenanceTenantContext(
        operation_name=("processing_recovery_reconciliation" if command.kind == "meeting.reprocess"
                        else "deletion_purge_reconciliation"),
        actor_id="graf-system-operation-worker", reason_category="durable_system_operation",
        feature_area="system_admin",
    ))
    if claim["mode"] != "start":
        await _observe(db, claim)
        return
    meeting = await db.get(Meeting, target_id)
    if meeting is None:
        await _result(db, claim, "failed", error="meeting_not_found")
        return
    if command.kind == "meeting.reprocess":
        # Keep the authority claim outside the domain savepoint. Rejected quota
        # admission rolls back all domain writes, while recording a terminal result.
        try:
            async with db.begin_nested():
                scope = await _processing_tenant_scope(db, meeting=meeting, tenant_scope=None)
                revision = await store.latest_media_revision_for_meeting(
                    db, workspace_id=meeting.workspace_id, meeting_id=meeting.id,
                )
                predecessor = await db.scalar(select(ProcessingWorkflow).where(
                    ProcessingWorkflow.meeting_id == meeting.id,
                    ProcessingWorkflow.media_revision_id == revision.id,
                    ProcessingWorkflow.purpose == "transcription",
                ).order_by(ProcessingWorkflow.attempt_ordinal.desc(), ProcessingWorkflow.created_at.desc()).limit(1)) if revision else None
                creation = await store.create_processing_attempt(
                    db, workspace_id=meeting.workspace_id, meeting_id=meeting.id,
                    expected_media_revision_id=revision.id if revision else None,
                    expected_workflow_id=predecessor.workflow_id if predecessor else None,
                    allow_processed=predecessor is not None and predecessor.status == "processed",
                    system_operation_id=operation_id,
                    workflow_row_id=UUID(claim["domain_ref"]),
                )
                if creation.workflow is None or creation.result != "created":
                    raise ProblemDetail(status=409, code="system_processing_admission_rejected",
                                        title="Повторная обработка недоступна")
        except ProblemDetail:
            await _result(db, claim, "failed", error=creation.result)
            return
        # This shared helper commits the claim + workflow before contacting Temporal.
        # The tenant scope is the original recording owner/device execution context;
        # immutable system_operation_id identifies the actual initiating admin.
        try:
            await dispatch_created_processing_attempt(
                settings=settings, temporal_client=temporal_client, db=db, tenant_scope=scope,
                meeting_id=target_id, creation=creation, reason_code="system_admin_reprocess",
            )
        except ProblemDetail:
            await db.rollback()
        await _observe(db, claim)
    else:
        # The deletion service commits the claim, tombstone, request and report
        # together before storage I/O. Its existing purge loop owns subsequent retries.
        await request_meeting_deletion(
            db, meeting=meeting, actor_user_id=None, device_id=None,
            confirmation_boundary=BOUNDED_DELETE_COPY, request_source=DeletionRequestSource.ADMIN,
            storage=storage, temporal_client=temporal_client,
            system_operation_id=operation_id, system_request_id=UUID(claim["domain_ref"]),
        )
        await _observe(db, claim)


async def run_system_operation_reconciler(settings, temporal_client) -> None:
    engine = create_engine(settings)
    sessions = create_sessionmaker(engine)
    storage = get_storage(settings)
    try:
        while True:
            try:
                async with sessions() as db:
                    await db.execute(text("select system_control.expire_media_tickets()"))
                    await db.commit()
                    pending = (await db.execute(text(
                        "select * from system_control.pending_system_operations()"
                    ))).all()
                    pending += (await db.execute(text(
                        "select * from system_control.pending_subscription_operations()"
                    ))).all()
                for operation_id, target_id in pending:
                    try:
                        async with sessions() as db:
                            await execute_operation(db, operation_id=operation_id, target_id=target_id,
                                settings=settings, temporal_client=temporal_client, storage=storage)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        # No exception text: driver errors may contain private SQL values.
                        logger.error("system operation deferred", extra={"operation_id": str(operation_id)})
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.error("system operation reconciliation unavailable")
            await asyncio.sleep(15)
    finally:
        await engine.dispose()
        close = getattr(storage, "close", None)
        if close is not None:
            result = close()
            if asyncio.iscoroutine(result):
                await result


async def _execute_subscription_operation(db: AsyncSession, claim: dict) -> None:
    """Apply one immutable access ledger change after the maintenance claim."""
    import json

    raw = claim["command"]
    if isinstance(raw, str):
        raw = json.loads(raw)
    parameters = raw.get("parameters") or {}
    operation_id = UUID(claim["operation_id"])
    workspace_id = UUID(claim["target_id"])
    domain_ref = UUID(claim["domain_ref"])
    await apply_tenant_context(db, MaintenanceTenantContext(
        operation_name="system_billing_adjustment", actor_id="graf-system-billing-worker",
        reason_category="durable_system_operation", feature_area="system_admin",
    ))
    try:
        async with db.begin_nested():
            if raw.get("kind") == "subscription.adjust":
                await create_adjustment(
                    db,
                    workspace_id=workspace_id,
                    subject_user_id=UUID(parameters["subject_user_id"]) if parameters.get("subject_user_id") else None,
                    kind=parameters["adjustment_kind"], feature_key=parameters.get("feature_key"),
                    value=parameters.get("value"), unit=parameters.get("unit"),
                    plan_version_id=UUID(parameters["plan_version_id"]) if parameters.get("plan_version_id") else None,
                    plan_mode=parameters.get("plan_mode"),
                    starts_at=datetime.fromisoformat(parameters["starts_at"]),
                    ends_at=datetime.fromisoformat(parameters["ends_at"]), timezone=parameters["timezone"],
                    source_kind="admin", source_ref=parameters["source_ref"], reason=raw["reason"],
                    admin_operation_id=operation_id, adjustment_id=domain_ref,
                )
            else:
                await revoke_adjustment(
                    db, workspace_id=workspace_id, adjustment_id=UUID(parameters["adjustment_id"]),
                    source_kind="admin", source_ref=parameters["source_ref"], reason=raw["reason"],
                    admin_operation_id=operation_id, revocation_id=domain_ref,
                )
            subscription = await db.get(WorkspaceSubscription, workspace_id, populate_existing=True)
            if subscription is not None:
                subscription.application_version = max(1, subscription.application_version + 1)
            await db.flush()
    except Exception:
        # The maintenance role may mutate the domain ledger only through its
        # guarded helper. Record a terminal, fenced result through the
        # system-control function instead of writing operation tables directly.
        await _result(db, claim, "failed", error="processing_failed")
        return
    await _result(db, claim, "succeeded")


async def _observe_subscription_operation(db: AsyncSession, claim: dict, command: dict) -> None:
    """Resolve a crash after the claim without issuing a second ledger row."""
    domain_ref = UUID(claim["domain_ref"])
    model = BillingAccessAdjustment if command.get("kind") == "subscription.adjust" else BillingAccessRevocation
    row = await db.get(model, domain_ref)
    await _result(db, claim, "succeeded" if row is not None else "awaiting_reconciliation")
