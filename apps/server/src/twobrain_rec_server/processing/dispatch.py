"""Shared dispatch for an already admitted attempt; commit before Temporal."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing import store
from twobrain_rec_server.workflows.temporal_client import start_processing_workflow


async def dispatch_created_processing_attempt(
    *,
    settings: Settings,
    temporal_client: object | None,
    db: AsyncSession,
    tenant_scope: TenantScope,
    meeting_id: UUID,
    creation: store.ProcessingAttemptCreation,
    reason_code: str,
) -> tuple[object, str | None]:
    assert creation.workflow is not None
    assert creation.media_revision_id is not None
    assert creation.attempt_ordinal is not None
    if temporal_client is None:
        await db.commit()
        await store.fail_processing_attempt_dispatch(db, workflow_id=creation.workflow.id)
        raise ProblemDetail(
            status=503,
            code="processing_temporal_unavailable",
            title="Новая попытка временно недоступна",
            detail="Запуск временно недоступен. Данные записи сохранены; повторите действие позже.",
        )
    workflow = await store.set_workflow_status(
        db,
        creation.workflow,
        ProcessingStatus.WORKFLOW_STARTED,
        reason_code=reason_code,
    )
    try:
        started = await start_processing_workflow(
            temporal_client=temporal_client,
            settings=settings,
            processing_workflow_row_id=workflow.id,
            meeting_id=meeting_id,
            media_revision_id=creation.media_revision_id,
            workspace_id=tenant_scope.workspace_id,
            tenant_scope=tenant_scope,
            archive_audio=workflow.archive_audio,
            attempt_ordinal=creation.attempt_ordinal,
        )
    except Exception as exc:
        await store.fail_processing_attempt_dispatch(db, workflow_id=workflow.id)
        raise ProblemDetail(
            status=503,
            code="processing_attempt_dispatch_unavailable",
            title="Не удалось запустить новую попытку",
            detail="Запуск временно недоступен. Данные записи сохранены; повторите действие позже.",
        ) from exc

    dispatch = None
    if not started.ambiguous:
        dispatch = "reused" if started.reused else "started"
        if started.run_id is not None:
            try:
                run_persisted = await store.record_processing_attempt_run(
                    db,
                    workflow_id=workflow.id,
                    workflow_run_id=started.run_id,
                )
            except Exception:
                run_persisted = False
            if not run_persisted:
                await db.rollback()
    return workflow, dispatch
