from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.ingest import get_request_db_session
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    MeetingListResponse,
    MeetingReviewResponse,
    MeetingReviewStatus,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_device_context,
    get_principal,
    get_tenant_scope,
)
from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review, list_cabinet_meetings

router = APIRouter(prefix="/api/v1", tags=["cabinet"])

TenantDependency = Depends(get_tenant_scope)
PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)
DbDependency = Depends(get_request_db_session)
CabinetSearchQuery = Query(default=None, max_length=120)
CabinetStatusQuery = Query(default=None)
CabinetSortQuery = Query(default="updated_desc")
CabinetLimitQuery = Query(default=50, ge=1, le=100)


@router.get(
    "/cabinet/meetings",
    response_model=MeetingListResponse,
    operation_id="listCabinetMeetings",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def list_cabinet_meetings_route(
    q: str | None = CabinetSearchQuery,
    status: MeetingReviewStatus | None = CabinetStatusQuery,
    sort: str = CabinetSortQuery,
    limit: int = CabinetLimitQuery,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingListResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    return await list_cabinet_meetings(
        db,
        workspace_id=tenant_scope.workspace_id,
        q=q,
        status=status,
        sort=sort,
        limit=limit,
    )


@router.get(
    "/cabinet/meetings/{meeting_id}",
    response_model=MeetingReviewResponse,
    operation_id="getCabinetMeetingReview",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_cabinet_meeting_review_route(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingReviewResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    response = await get_cabinet_meeting_review(db, workspace_id=tenant_scope.workspace_id, meeting_id=meeting_id)
    if response is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return response
