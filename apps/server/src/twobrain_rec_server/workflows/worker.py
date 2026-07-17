from __future__ import annotations

import asyncio
from uuid import UUID

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.mediascribe.client import MediaScribeClient, MediaScribeClientError
from twobrain_rec_server.processing import reasons, store
from twobrain_rec_server.processing.submit import (
    poll_and_import_mediascribe_result,
    submit_to_mediascribe,
)
from twobrain_rec_server.storage.minio_client import get_storage
from twobrain_rec_server.workflows.processing_workflow import MediaScribeProcessingWorkflow
from twobrain_rec_server.workflows.temporal_client import (
    connect_temporal_client,
    processing_worker_identity,
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
    client = await connect_temporal_client(settings)
    processing_activity = activity.defn(name="run_processing_pipeline_activity")(
        run_processing_pipeline_activity
    )
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[MediaScribeProcessingWorkflow],
        activities=[processing_activity],
        identity=processing_worker_identity(),
    )
    await worker.run()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
