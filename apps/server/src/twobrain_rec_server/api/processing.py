from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.queries import load_admin_workspace_context
from twobrain_rec_server.api.ingest import get_request_db_session
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
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
from twobrain_rec_server.processing.pickup import pick_up_processing
from twobrain_rec_server.processing.status import get_content_safe_processing_status

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
    )
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
