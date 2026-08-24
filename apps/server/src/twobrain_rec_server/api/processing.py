from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.queries import load_admin_workspace_context
from twobrain_rec_server.api.ingest import get_request_db_session
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    ProcessingAttemptResponse,
    ProcessingCheckRequest,
    ProcessingCheckResponse,
    ProcessingPickupRequest,
    ProcessingPickupResponse,
    ProcessingStatusResponse,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_device_context,
    get_principal,
    get_tenant_scope,
    require_web_csrf,
)
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.pickup import pick_up_processing
from twobrain_rec_server.processing.status import get_content_safe_processing_status
from twobrain_rec_server.workflows.temporal_client import (
    cancel_workflow_best_effort,
    request_processing_manual_check,
    start_processing_workflow,
)

router = APIRouter(prefix="/api/v1", tags=["processing"])

TenantDependency = Depends(get_tenant_scope)
PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)
DbDependency = Depends(get_request_db_session)
WebCSRFDependency = Depends(require_web_csrf)


@router.post(
    "/internal/processing/pickup",
    response_model=ProcessingPickupResponse,
    status_code=202,
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def trigger_processing_pickup(
    payload: ProcessingPickupRequest,
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> ProcessingPickupResponse:
    if db is None:
        raise ProblemDetail(status=503, code="processing_store_unavailable", title="Processing store unavailable")
    await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    result = await pick_up_processing(
        db=db,
        settings=request.app.state.settings,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=payload.meeting_id,
        limit=payload.limit,
        temporal_client=getattr(request.app.state, "temporal_client", None),
        tenant_scope=tenant_scope,
        archive_audio=payload.archive_audio,
    )
    await db.commit()
    return ProcessingPickupResponse(
        accepted=result.accepted,
        started_count=result.started_count,
        reused_count=result.reused_count,
        blocked_count=result.blocked_count,
        meeting_ids=result.meeting_ids,
    )


@router.get(
    "/meetings/{meeting_id}/processing",
    response_model=ProcessingStatusResponse,
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_processing_status(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> ProcessingStatusResponse:
    if db is None:
        raise ProblemDetail(status=503, code="processing_store_unavailable", title="Processing store unavailable")
    response = await get_content_safe_processing_status(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    )
    if response is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return response


@router.post(
    "/meetings/{meeting_id}/processing/attempt",
    response_model=ProcessingAttemptResponse,
    status_code=202,
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def start_new_processing_attempt(
    meeting_id: UUID,
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> ProcessingAttemptResponse:
    """Create and dispatch one fresh attempt after a confirmed terminal failure."""

    if db is None:
        raise ProblemDetail(
            status=503,
            code="processing_store_unavailable",
            title="Processing store unavailable",
        )
    current = await get_content_safe_processing_status(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    )
    if current is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")

    creation = await store.create_processing_attempt(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    )
    if creation.result == "already_in_flight":
        await db.rollback()
        latest = await get_content_safe_processing_status(
            db,
            workspace_id=tenant_scope.workspace_id,
            meeting_id=meeting_id,
        ) or current
        return ProcessingAttemptResponse.model_validate(
            {
                **latest.model_dump(mode="python"),
                "attempt_result": "already_in_flight",
                "attempt_ordinal": creation.attempt_ordinal or latest.attempt_ordinal,
            }
        )
    if (
        creation.result != "created"
        or creation.workflow is None
        or creation.media_revision_id is None
        or creation.attempt_ordinal is None
    ):
        await db.rollback()
        problems = {
            "unknown_outcome": (
                409,
                "processing_unknown_outcome",
                "Сначала нужно проверить уже отправленную обработку.",
            ),
            "configuration_failure": (
                409,
                "processing_configuration_failure",
                "Эту обработку нельзя безопасно перезапустить без исправления настройки.",
            ),
            "deletion_closed": (
                409,
                "processing_deletion_closed",
                "Встреча уже закрыта для дальнейшей обработки.",
            ),
            "source_unavailable": (
                409,
                "processing_source_unavailable",
                "Не удалось подтвердить исходную запись для новой попытки.",
            ),
            "quota_exceeded": (
                409,
                "processing_quota_exceeded",
                "Недостаточно доступного лимита обработки для новой попытки.",
            ),
            "not_terminal": (
                409,
                "processing_attempt_not_allowed",
                "Новую попытку можно начать только после подтверждённого окончательного сбоя.",
            ),
            "meeting_not_found": (404, "meeting_not_found", "Meeting not found"),
        }
        status, code, detail = problems.get(
            creation.result,
            (409, "processing_attempt_not_allowed", "Новая попытка сейчас недоступна."),
        )
        raise ProblemDetail(status=status, code=code, title=detail, detail=detail)

    temporal_client = getattr(request.app.state, "temporal_client", None)
    if temporal_client is None:
        await db.commit()
        await store.fail_processing_attempt_dispatch(
            db,
            workflow_id=creation.workflow.id,
        )
        raise ProblemDetail(
            status=503,
            code="processing_temporal_unavailable",
            title="Новая попытка временно недоступна",
            detail="Попытка сохранена. После восстановления сервиса запустите обработку заново.",
        )
    workflow = creation.workflow
    # The activity must see this row before Temporal can start it.  The
    # compensating status below prevents an unavailable dispatch from leaving
    # a durable attempt stuck in ``starting``.
    await db.commit()
    try:
        started = await start_processing_workflow(
            temporal_client=temporal_client,
            settings=request.app.state.settings,
            meeting_id=meeting_id,
            media_revision_id=creation.media_revision_id,
            workspace_id=tenant_scope.workspace_id,
            tenant_scope=tenant_scope,
            archive_audio=workflow.archive_audio,
            attempt_ordinal=creation.attempt_ordinal,
        )
        await store.record_processing_attempt_run(
            db,
            workflow_id=workflow.id,
            workflow_run_id=started.run_id,
        )
    except Exception as exc:
        await cancel_workflow_best_effort(temporal_client, workflow.workflow_id)
        await store.fail_processing_attempt_dispatch(
            db,
            workflow_id=workflow.id,
        )
        raise ProblemDetail(
            status=503,
            code="processing_attempt_dispatch_unavailable",
            title="Не удалось запустить новую попытку",
            detail="Попытка сохранена, но запуск временно недоступен. Попробуйте начать её заново позже.",
        ) from exc

    latest = await get_content_safe_processing_status(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    ) or current
    return ProcessingAttemptResponse.model_validate(
        {
            **latest.model_dump(mode="python"),
            "attempt_result": "created",
            "attempt_ordinal": creation.attempt_ordinal,
            "workflow_id": workflow.workflow_id,
            "dispatch": "reused" if started.reused else "started",
        }
    )


def _processing_check_response(
    status: ProcessingStatusResponse,
    *,
    request_result: str,
    command_id: str,
    same_job_check: bool,
    dispatch: str | None = None,
) -> ProcessingCheckResponse:
    return ProcessingCheckResponse.model_validate(
        {
            **status.model_dump(mode="python"),
            "request_result": request_result,
            "command_id": command_id,
            "same_job_check": same_job_check,
            "dispatch": dispatch,
        }
    )


@router.post(
    "/meetings/{meeting_id}/processing/check",
    response_model=ProcessingCheckResponse,
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def check_processing(
    meeting_id: UUID,
    request: Request,
    payload: ProcessingCheckRequest | None = None,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> ProcessingCheckResponse:
    if db is None:
        raise ProblemDetail(status=503, code="processing_store_unavailable", title="Processing store unavailable")
    current = await get_content_safe_processing_status(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    )
    if current is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    check = payload or ProcessingCheckRequest()
    claim = await store.claim_processing_manual_check(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        media_revision_id=current.media_revision_id,
        command_key=check.command_id,
        expected_schedule_generation=check.schedule_generation,
    )
    await db.commit()
    if claim.request_result != "accepted" or not claim.claimed or claim.workflow is None:
        latest = await get_content_safe_processing_status(
            db,
            workspace_id=tenant_scope.workspace_id,
            meeting_id=meeting_id,
        ) or current
        return _processing_check_response(
            latest,
            request_result=claim.request_result,
            command_id=claim.command_id,
            same_job_check=claim.same_job_check,
        )

    temporal_client = getattr(request.app.state, "temporal_client", None)
    if temporal_client is None:
        await store.release_processing_manual_check_claim(
            db,
            workflow_id=claim.workflow.id,
            manual_command_version=int(claim.workflow.manual_command_version or 0),
        )
        raise ProblemDetail(
            status=503,
            code="processing_temporal_unavailable",
            title="Проверка обработки временно недоступна",
            detail="Попробуйте ещё раз позже.",
        )
    try:
        dispatched = await request_processing_manual_check(
            temporal_client=temporal_client,
            workflow_id=claim.workflow.workflow_id,
            command_id=claim.command_id,
        )
    except Exception as exc:
        await store.release_processing_manual_check_claim(
            db,
            workflow_id=claim.workflow.id,
            manual_command_version=int(claim.workflow.manual_command_version or 0),
        )
        raise ProblemDetail(
            status=503,
            code="processing_manual_check_unavailable",
            title="Не удалось запустить проверку обработки",
            detail="Попробуйте ещё раз позже.",
        ) from exc
    latest = await get_content_safe_processing_status(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    ) or current
    return _processing_check_response(
        latest,
        request_result="accepted",
        command_id=claim.command_id,
        same_job_check=True,
        dispatch=dispatched.dispatch,
    )
