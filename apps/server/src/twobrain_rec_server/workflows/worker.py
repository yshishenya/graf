from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.email_delivery import EmailLoginDeliveryError, PostalEmailLoginClient
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.models import Meeting, MeetingShareInvitation, UserIdentity
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.domain.statuses import ProcessingStatus
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
from twobrain_rec_server.processing import reasons, store
from twobrain_rec_server.processing.submit import (
    poll_and_import_mediascribe_result,
    submit_to_mediascribe,
)
from twobrain_rec_server.storage.minio_client import get_storage
from twobrain_rec_server.workflows.invitation_delivery_workflow import InvitationDeliveryWorkflow
from twobrain_rec_server.workflows.outcome_generation_workflow import (
    OutcomeGenerationWorkflow,
    OutcomeObservabilityReconcilerWorkflow,
    TranscriptSnapshotError,
)
from twobrain_rec_server.workflows.processing_workflow import MediaScribeProcessingWorkflow
from twobrain_rec_server.workflows.temporal_client import (
    connect_temporal_client,
    outcome_generation_task_queue,
    processing_worker_identity,
)


def invitation_delivery_failure_state(
    error: EmailLoginDeliveryError,
) -> tuple[str, str]:
    """Keep pre-egress failures distinct from an unknown provider outcome."""
    return (
        "outcome_unknown" if error.outcome_unknown else "failed",
        error.reason_code,
    )


async def run_processing_pipeline_activity(payload: dict[str, str]) -> dict[str, str]:
    from temporalio import activity

    meeting_ref = payload.get("meeting_id", "unknown")
    media_revision_id: UUID | None = None
    activity.heartbeat({"state": "starting", "meeting_id": meeting_ref})
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
    settings = get_settings()
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    try:
        mediascribe_client = MediaScribeClient.from_settings(settings)
        storage = get_storage(settings)
        async with sessionmaker() as db:
            await apply_tenant_scope(db, tenant_scope, context_kind="worker")
            workflow = await store.get_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            if workflow is None:
                workflow = await store.upsert_processing_workflow(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    workflow_id=f"processing/{payload.get('media_revision_id') or payload['meeting_id']}",
                    status=ProcessingStatus.WORKFLOW_STARTED,
                )
            submit_result = await submit_to_mediascribe(
                db=db,
                settings=settings,
                storage=storage,
                mediascribe_client=mediascribe_client,
                workflow=workflow,
            )
            job = submit_result.job
            for poll_attempt in range(settings.processing_max_poll_attempts):
                activity.heartbeat({"state": "polling", "poll_attempt": poll_attempt + 1})
                import_result = await poll_and_import_mediascribe_result(
                    db=db,
                    workflow=workflow,
                    job=job,
                    mediascribe_client=mediascribe_client,
                )
                if import_result.status == ProcessingStatus.PROCESSED:
                    return {"meeting_id": payload["meeting_id"], "processing_status": "processed"}
                if import_result.status == ProcessingStatus.FAILED_TERMINAL:
                    return {
                        "meeting_id": payload["meeting_id"],
                        "processing_status": "failed_terminal",
                    }
                await asyncio.sleep(settings.processing_poll_interval_seconds)
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.FAILED_TERMINAL,
                reason_code="mediascribe_poll_limit_exceeded",
                terminal=True,
            )
            return {"meeting_id": payload["meeting_id"], "processing_status": "failed_terminal"}
    except MediaScribeClientError as exc:
        status = _processing_status_for_client_error(exc)
        await _persist_activity_client_error(
            sessionmaker,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            tenant_scope=tenant_scope,
            status=status,
            reason_code=exc.reason_code,
        )
        return {"meeting_id": payload["meeting_id"], "processing_status": status.value}
    finally:
        await engine.dispose()


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
            failure_code=str(payload.get("failure_code") or "summary_generation_retries_exhausted")[:120],
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
            temporal_workflow_id=str(
                payload.get("generation_workflow_id") or info.workflow_id
            ),
            temporal_run_id=str(
                payload.get("generation_workflow_run_id") or info.workflow_run_id
            ),
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
                await PostalEmailLoginClient.from_settings(settings).send_meeting_invitation(
                    recipient_email=address,
                    acceptance_url=acceptance_url,
                    delivery_key=str(invitation.id),
                    inviter_name=inviter.display_name if inviter is not None else None,
                    meeting_title=meeting.title,
                    occurred_at=meeting.started_at or meeting.created_at,
                    duration_seconds=meeting.duration_seconds,
                    expires_at=invitation.expires_at,
                )
            except EmailLoginDeliveryError as exc:
                invitation.status, invitation.failure_code = invitation_delivery_failure_state(exc)
                invitation.encrypted_delivery_address = ""
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


def _processing_status_for_client_error(exc: MediaScribeClientError) -> ProcessingStatus:
    if exc.reason_code in {
        reasons.BLOCKED_CONFIG,
        reasons.BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
    }:
        return ProcessingStatus.BLOCKED
    return ProcessingStatus.FAILED_RETRYABLE if exc.retryable else ProcessingStatus.FAILED_TERMINAL


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
) -> None:
    async with sessionmaker() as db:
        if tenant_scope is not None:
            await apply_tenant_scope(db, tenant_scope, context_kind="worker")
        workflow = await store.get_processing_workflow(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
        if workflow is None:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id or meeting_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
        terminal = status in {ProcessingStatus.BLOCKED, ProcessingStatus.FAILED_TERMINAL}
        if (
            workflow.status == status.value
            and workflow.last_reason_code == reason_code
            and (not terminal or workflow.ended_at is not None)
        ):
            return
        await store.set_workflow_status(
            db,
            workflow,
            status,
            reason_code=reason_code,
            terminal=terminal,
        )


async def run_worker() -> None:
    from temporalio import activity
    from temporalio.worker import Worker

    settings = get_settings()
    if settings.prompt_optimization_enabled:
        raise RuntimeError(
            "prompt optimization must run in the operations-only worker"
        )
    processing_client = await connect_temporal_client(settings)
    processing_activity = activity.defn(name="run_processing_pipeline_activity")(
        run_processing_pipeline_activity
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
    processing_worker = Worker(
        processing_client,
        task_queue=settings.temporal_task_queue,
        workflows=[
            MediaScribeProcessingWorkflow,
            InvitationDeliveryWorkflow,
        ],
        activities=[processing_activity, invitation_activity],
        identity=processing_worker_identity(),
    )
    workers = [processing_worker]
    if settings.outcome_generation_enabled:
        traced_client = await connect_temporal_client(
            settings,
            identity=f"{processing_worker_identity()}:ai",
            outcome_tracing=True,
        )
        if settings.outcome_generation_enabled:
            workers.append(
                Worker(
                    traced_client,
                    task_queue=outcome_generation_task_queue(settings),
                    workflows=[
                        OutcomeGenerationWorkflow,
                        OutcomeObservabilityReconcilerWorkflow,
                    ],
                    activities=outcome_activities,
                    identity=f"{processing_worker_identity()}:outcomes",
                )
            )
    await asyncio.gather(*(worker.run() for worker in workers))


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
