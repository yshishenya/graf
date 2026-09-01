from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
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
    ProcessingReprocessRequest,
    ProcessingReprocessResponse,
    ProcessingStatusResponse,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_device_context,
    get_principal,
    get_tenant_scope,
    require_web_csrf,
)
from twobrain_rec_server.cabinet.access import decide_meeting_access
from twobrain_rec_server.db.models import Meeting
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.normalization.pickup import dispatch_normalization_after_accepted_commit
from twobrain_rec_server.normalization.service import request_normalization_retry_now
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.pickup import pick_up_processing
from twobrain_rec_server.processing.status import get_content_safe_processing_status
from twobrain_rec_server.workflows.temporal_client import (
    connect_temporal_client,
    request_processing_manual_check,
    start_processing_workflow,
)

router = APIRouter(prefix="/api/v1", tags=["processing"])

TenantDependency = Depends(get_tenant_scope)
PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)
DbDependency = Depends(get_request_db_session)
WebCSRFDependency = Depends(require_web_csrf)


async def _load_processing_meeting(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> Meeting | None:
    return await db.scalar(
        select(Meeting).where(
            Meeting.id == meeting_id,
            Meeting.workspace_id == workspace_id,
        )
    )


async def _get_temporal_client(request: Request) -> object | None:
    """Reuse a process client while allowing recovery after a late startup."""

    temporal_client = getattr(request.app.state, "temporal_client", None)
    if temporal_client is not None:
        return temporal_client
    lock = getattr(request.app.state, "temporal_client_connect_lock", None)
    if lock is None:
        lock = asyncio.Lock()
        request.app.state.temporal_client_connect_lock = lock
    async with lock:
        temporal_client = getattr(request.app.state, "temporal_client", None)
        if temporal_client is not None:
            return temporal_client
        try:
            temporal_client = await connect_temporal_client(request.app.state.settings)
        except Exception:
            return None
        request.app.state.temporal_client = temporal_client
        return temporal_client


async def _dispatch_created_processing_attempt(
    *,
    request: Request,
    db: AsyncSession,
    tenant_scope: TenantScope,
    meeting_id: UUID,
    creation: store.ProcessingAttemptCreation,
    reason_code: str,
) -> tuple[object, str | None]:
    assert creation.workflow is not None
    assert creation.media_revision_id is not None
    assert creation.attempt_ordinal is not None
    temporal_client = await _get_temporal_client(request)
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
            settings=request.app.state.settings,
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
        raise ProblemDetail(
            status=503, code="processing_store_unavailable", title="Processing store unavailable"
        )
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
    http_response: Response,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> ProcessingStatusResponse:
    http_response.headers["Cache-Control"] = "private, no-store"
    http_response.headers["Pragma"] = "no-cache"
    if db is None:
        raise ProblemDetail(
            status=503, code="processing_store_unavailable", title="Processing store unavailable"
        )
    meeting = await _load_processing_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    access = await decide_meeting_access(
        db,
        meeting,
        workspace_id=tenant_scope.workspace_id,
        viewer_user_id=principal.user_id,
    )
    if not access.can_view:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    status = await get_content_safe_processing_status(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    )
    if status is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if status.meeting_id != meeting_id:
        raise ProblemDetail(
            status=500,
            code="processing_status_identity_mismatch",
            title="Processing status unavailable",
        )
    if meeting.created_by_user_id != principal.user_id:
        status = status.model_copy(
            update={
                "workflow_id": None,
                "next_attempt_at": None,
                "next_attempt_source": None,
                "schedule_generation": 0,
                "manual_action": "none",
            }
        )
    return status


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
        latest = (
            await get_content_safe_processing_status(
                db,
                workspace_id=tenant_scope.workspace_id,
                meeting_id=meeting_id,
            )
            or current
        )
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
            "source_expired": (
                409,
                "processing_source_expired",
                "Срок временного хранения записи истёк. Загрузите файл заново.",
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

    workflow, dispatch = await _dispatch_created_processing_attempt(
        request=request,
        db=db,
        tenant_scope=tenant_scope,
        meeting_id=meeting_id,
        creation=creation,
        reason_code="user_new_attempt",
    )

    latest = (
        await get_content_safe_processing_status(
            db,
            workspace_id=tenant_scope.workspace_id,
            meeting_id=meeting_id,
        )
        or current
    )
    return ProcessingAttemptResponse.model_validate(
        {
            **latest.model_dump(mode="python"),
            "attempt_result": "created",
            "attempt_ordinal": creation.attempt_ordinal,
            "workflow_id": workflow.workflow_id,
            "dispatch": dispatch,
        }
    )


@router.post(
    "/meetings/{meeting_id}/processing/reprocess",
    response_model=ProcessingReprocessResponse,
    status_code=202,
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def reprocess_meeting(
    meeting_id: UUID,
    payload: ProcessingReprocessRequest,
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> ProcessingReprocessResponse:
    if db is None:
        raise ProblemDetail(
            status=503,
            code="processing_store_unavailable",
            title="Processing store unavailable",
        )
    meeting = await _load_processing_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    )
    if meeting is None or meeting.created_by_user_id != principal.user_id:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
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
        owner_user_id=principal.user_id,
        expected_media_revision_id=payload.expected_media_revision_id,
        expected_workflow_id=payload.expected_workflow_id,
        allow_processed=True,
    )
    if creation.result in {"replayed", "already_in_flight"}:
        await db.rollback()
        latest = (
            await get_content_safe_processing_status(
                db,
                workspace_id=tenant_scope.workspace_id,
                meeting_id=meeting_id,
            )
            or current
        )
        return ProcessingReprocessResponse.model_validate(
            {
                **latest.model_dump(mode="python"),
                "request_result": creation.result,
                "attempt_ordinal": creation.attempt_ordinal or latest.attempt_ordinal,
                "workflow_id": (
                    creation.workflow.workflow_id
                    if creation.workflow is not None
                    else latest.workflow_id
                ),
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
            "meeting_not_found": (404, "meeting_not_found", "Meeting not found"),
            "stale_meeting_view": (
                409,
                "stale_meeting_view",
                "Встреча уже изменилась. Обновите страницу и повторите действие.",
            ),
            "deletion_closed": (
                409,
                "processing_meeting_deleting",
                "Встреча уже закрыта для дальнейшей обработки.",
            ),
            "source_unavailable": (
                409,
                "processing_source_unavailable",
                "Исходная запись для повторной обработки недоступна.",
            ),
            "source_expired": (
                409,
                "processing_source_expired",
                "Срок хранения исходной записи истёк. Загрузите файл заново.",
            ),
            "quota_exceeded": (
                409,
                "processing_quota_exceeded",
                "Не удалось подтвердить доступный лимит обработки.",
            ),
        }
        status, code, detail = problems.get(
            creation.result,
            (
                409,
                "processing_reprocess_not_eligible",
                "Эту запись сейчас нельзя обработать повторно.",
            ),
        )
        raise ProblemDetail(status=status, code=code, title=detail, detail=detail)

    workflow, dispatch = await _dispatch_created_processing_attempt(
        request=request,
        db=db,
        tenant_scope=tenant_scope,
        meeting_id=meeting_id,
        creation=creation,
        reason_code="user_reprocess",
    )
    latest = (
        await get_content_safe_processing_status(
            db,
            workspace_id=tenant_scope.workspace_id,
            meeting_id=meeting_id,
        )
        or current
    )
    return ProcessingReprocessResponse.model_validate(
        {
            **latest.model_dump(mode="python"),
            "request_result": "created",
            "attempt_ordinal": creation.attempt_ordinal,
            "workflow_id": workflow.workflow_id,
            "dispatch": dispatch,
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
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> ProcessingCheckResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="processing_store_unavailable", title="Processing store unavailable"
        )
    current = await get_content_safe_processing_status(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    )
    if current is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if (
        current.attempt_ordinal > 1
    ):
        meeting = await _load_processing_meeting(
            db,
            workspace_id=tenant_scope.workspace_id,
            meeting_id=meeting_id,
        )
        if meeting is None or meeting.created_by_user_id != principal.user_id:
            raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    check = payload or ProcessingCheckRequest()
    claim = await store.claim_processing_manual_check(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        media_revision_id=current.media_revision_id,
        owner_user_id=principal.user_id,
        command_key=check.command_id,
        expected_schedule_generation=check.schedule_generation,
    )
    workflow_id = claim.workflow.id if claim.workflow is not None else None
    manual_command_version = (
        int(claim.workflow.manual_command_version or 0) if claim.workflow is not None else 0
    )

    async def release_claim() -> None:
        if claim.claimed and workflow_id is not None:
            await db.rollback()
            await store.release_processing_manual_check_claim(
                db,
                workflow_id=workflow_id,
                manual_command_version=manual_command_version,
                settings=getattr(request.app.state, "settings", None),
            )

    if current.manual_action == "retry_preparation":
        if claim.request_result == "stale_schedule":
            await db.commit()
            latest = (
                await get_content_safe_processing_status(
                    db,
                    workspace_id=tenant_scope.workspace_id,
                    meeting_id=meeting_id,
                )
                or current
            )
            return _processing_check_response(
                latest,
                request_result="stale_schedule",
                command_id=claim.command_id,
                same_job_check=False,
            )
        try:
            retry = await request_normalization_retry_now(
                db,
                workspace_id=tenant_scope.workspace_id,
                meeting_id=meeting_id,
                media_revision_id=current.media_revision_id,
            )
        except asyncio.CancelledError:
            await asyncio.shield(release_claim())
            raise
        except Exception as exc:
            await release_claim()
            raise ProblemDetail(
                status=503,
                code="processing_manual_check_unavailable",
                title="Не удалось запустить повторную подготовку",
                detail="Попробуйте ещё раз позже.",
            ) from exc
        if retry.result not in {"accepted", "already_in_flight"}:
            await db.rollback()
            await release_claim()
            latest = (
                await get_content_safe_processing_status(
                    db,
                    workspace_id=tenant_scope.workspace_id,
                    meeting_id=meeting_id,
                )
                or current
            )
            return _processing_check_response(
                latest,
                request_result="not_safe",
                command_id=claim.command_id,
                same_job_check=False,
            )
        try:
            temporal_client = await _get_temporal_client(request)
            normalization_dispatch = await dispatch_normalization_after_accepted_commit(
                db=db,
                settings=request.app.state.settings,
                tenant_scope=tenant_scope,
                media_revision_id=current.media_revision_id,
                temporal_client=temporal_client,
                lease_owner=f"manual-retry:{claim.command_id}",
            )
            # The normalization worker wakes processing after publication.
            # Do not spend an extra processing cycle while the M4A is pending.
            if not (normalization_dispatch.started or normalization_dispatch.reused):
                await release_claim()
        except asyncio.CancelledError:
            await asyncio.shield(release_claim())
            raise
        except Exception as exc:
            await release_claim()
            raise ProblemDetail(
                status=503,
                code="processing_manual_check_unavailable",
                title="Не удалось запустить повторную подготовку",
                detail="Попробуйте ещё раз позже.",
            ) from exc
        latest = (
            await get_content_safe_processing_status(
                db,
                workspace_id=tenant_scope.workspace_id,
                meeting_id=meeting_id,
            )
            or current
        )
        return _processing_check_response(
            latest,
            request_result=(
                "already_in_flight" if retry.result == "already_in_flight" else "accepted"
            ),
            command_id=claim.command_id,
            same_job_check=False,
        )
    await db.commit()
    if claim.request_result != "accepted" or not claim.claimed or claim.workflow is None:
        latest = (
            await get_content_safe_processing_status(
                db,
                workspace_id=tenant_scope.workspace_id,
                meeting_id=meeting_id,
            )
            or current
        )
        return _processing_check_response(
            latest,
            request_result=claim.request_result,
            command_id=claim.command_id,
            same_job_check=claim.same_job_check,
        )

    try:
        temporal_client = await _get_temporal_client(request)
    except asyncio.CancelledError:
        await asyncio.shield(release_claim())
        raise
    if temporal_client is None:
        await release_claim()
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
    except asyncio.CancelledError:
        await asyncio.shield(release_claim())
        raise
    except Exception as exc:
        await release_claim()
        raise ProblemDetail(
            status=503,
            code="processing_manual_check_unavailable",
            title="Не удалось запустить проверку обработки",
            detail="Попробуйте ещё раз позже.",
        ) from exc
    latest = (
        await get_content_safe_processing_status(
            db,
            workspace_id=tenant_scope.workspace_id,
            meeting_id=meeting_id,
        )
        or current
    )
    return _processing_check_response(
        latest,
        request_result="accepted",
        command_id=claim.command_id,
        same_job_check=True,
        dispatch=dispatched.dispatch,
    )
