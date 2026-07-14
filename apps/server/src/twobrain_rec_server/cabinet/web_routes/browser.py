from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.cabinet.queries import (
    get_cabinet_meeting_review,
    list_cabinet_meetings,
)
from twobrain_rec_server.cabinet.rendering import (
    render_meeting_detail_fragment,
    render_meeting_detail_page,
    render_meeting_list_fragment,
    render_meeting_list_page,
    render_settings_page,
)
from twobrain_rec_server.cabinet.templates import (
    cabinet_html_response,
)
from twobrain_rec_server.cabinet.web_routes.support import (
    CabinetAccessFilter,
    CabinetLimitQuery,
    CabinetSearchQuery,
    CabinetSortQuery,
    CabinetStatusFilter,
    PrincipalDependency,
    StorageDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
    _is_hx_request,
    _request_path_with_query,
)

router = APIRouter(tags=["cabinet-web"])


@router.get("/meetings", response_class=HTMLResponse, include_in_schema=False)
async def meeting_list_page(
    request: Request,
    q: str | None = CabinetSearchQuery,
    status: CabinetStatusFilter = None,
    access: CabinetAccessFilter = None,
    sort: str = CabinetSortQuery,
    limit: int = CabinetLimitQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    response = await list_cabinet_meetings(
        db,
        workspace_id=tenant_scope.workspace_id,
        viewer_user_id=principal.user_id,
        storage=storage,
        q=q,
        status=status,
        group_status_filter=True,
        visible_title_search=True,
        access=access,
        sort=sort,
        limit=limit,
    )
    if _is_hx_request(request):
        return cabinet_html_response(
            render_meeting_list_fragment(response, poll_url=_request_path_with_query(request)),
            hx_request=True,
        )
    return cabinet_html_response(
        render_meeting_list_page(
            response,
            csrf_token=_csrf_token_for_principal(request, principal),
            poll_url=_request_path_with_query(request),
        )
    )


@router.get("/meetings/{meeting_id}", response_class=HTMLResponse, include_in_schema=False)
async def meeting_detail_page(
    request: Request,
    meeting_id: UUID,
    calendar_context_action: str | None = Query(default=None, pattern="^change$"),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    response = await get_cabinet_meeting_review(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
        storage=storage,
        include_calendar_correction_candidates=calendar_context_action == "change",
    )
    if response is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if _is_hx_request(request):
        return cabinet_html_response(
            render_meeting_detail_fragment(
                response,
                poll_url=_request_path_with_query(request),
            ),
            hx_request=True,
        )
    return cabinet_html_response(
        render_meeting_detail_page(
            response,
            csrf_token=_csrf_token_for_principal(request, principal),
            poll_url=_request_path_with_query(request),
        )
    )


@router.get("/settings", response_class=HTMLResponse, include_in_schema=False)
async def settings_page(
    request: Request,
    _tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
) -> HTMLResponse:
    return cabinet_html_response(
        render_settings_page(
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    )
