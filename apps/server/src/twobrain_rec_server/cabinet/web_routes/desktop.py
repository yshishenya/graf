from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.dependencies import (
    set_desktop_calendar_auth_cookie,
)
from twobrain_rec_server.cabinet.deletion_rendering import (
    render_deletion_report_fragment,
    render_deletion_report_page,
)
from twobrain_rec_server.cabinet.queries import (
    get_cabinet_meeting_review,
    get_calendar_settings_surface,
    list_cabinet_meetings,
)
from twobrain_rec_server.cabinet.rendering import (
    calendar_settings_notice_codes,
    render_calendar_settings_fragment,
    render_calendar_settings_page,
    render_meeting_detail_fragment,
    render_meeting_detail_page,
    render_meeting_list_fragment,
    render_meeting_list_page,
    render_settings_page,
)
from twobrain_rec_server.cabinet.templates import (
    cabinet_html_response,
)
from twobrain_rec_server.cabinet.web_routes.auth import (
    logout_current_browser_session,
)
from twobrain_rec_server.cabinet.web_routes.support import (
    CabinetAccessFilter,
    CabinetLimitQuery,
    CabinetSearchQuery,
    CabinetSortQuery,
    CabinetStatusFilter,
    CalendarConnectResultQuery,
    CalendarDisconnectResultQuery,
    CalendarPolicyLimitedQuery,
    CalendarPreferencesResultQuery,
    CalendarSelectionResultQuery,
    CalendarSyncResultQuery,
    LoginDbDependency,
    PrincipalDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _authorized_lifecycle_meeting,
    _csrf_token_for_principal,
    _is_hx_request,
    _request_path_with_query,
)
from twobrain_rec_server.deletion.service import deletion_report_response

router = APIRouter(tags=["cabinet-web"])
EmbeddedLogoutNextForm = Form(default="/login?next=/desktop/meetings", alias="next", max_length=512)


@router.get("/desktop/meetings", response_class=HTMLResponse, include_in_schema=False)
async def embedded_meeting_list_page(
    request: Request,
    q: str | None = CabinetSearchQuery,
    status: CabinetStatusFilter = None,
    access: CabinetAccessFilter = None,
    sort: str = CabinetSortQuery,
    limit: int = CabinetLimitQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
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
            render_meeting_list_fragment(
                response, embedded=True, poll_url=_request_path_with_query(request)
            ),
            hx_request=True,
        )
    return cabinet_html_response(
        render_meeting_list_page(
            response,
            embedded=True,
            csrf_token=_csrf_token_for_principal(request, principal),
            poll_url=_request_path_with_query(request),
        )
    )


# Compatibility path for already-installed macOS clients: their embedded
# cabinet allowlist permits POST navigation to /desktop/meetings, but blocks
# /logout until a future app release explicitly allows a desktop logout route.
@router.post("/desktop/meetings", include_in_schema=False, response_model=None)
async def embedded_logout_from_meetings_route(
    request: Request,
    next_path: str = EmbeddedLogoutNextForm,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    _csrf: None = WebCSRFDependency,
    db: AsyncSession | None = LoginDbDependency,
):
    return await logout_current_browser_session(
        request,
        next_path=next_path,
        principal=principal,
        db=db,
    )


@router.get("/desktop/meetings/{meeting_id}", response_class=HTMLResponse, include_in_schema=False)
async def embedded_meeting_detail_page(
    request: Request,
    meeting_id: UUID,
    calendar_context_action: str | None = Query(default=None, pattern="^change$"),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
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
        include_calendar_correction_candidates=calendar_context_action == "change",
    )
    if response is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if _is_hx_request(request):
        return cabinet_html_response(
            render_meeting_detail_fragment(response, embedded=True),
            hx_request=True,
        )
    return cabinet_html_response(
        render_meeting_detail_page(
            response,
            embedded=True,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    )


@router.get(
    "/desktop/settings/integrations/calendar", response_class=HTMLResponse, include_in_schema=False
)
async def embedded_calendar_settings_page(
    request: Request,
    connect_result: str | None = CalendarConnectResultQuery,
    policy_limited: str | None = CalendarPolicyLimitedQuery,
    selection_result: str | None = CalendarSelectionResultQuery,
    preferences_result: str | None = CalendarPreferencesResultQuery,
    sync_result: str | None = CalendarSyncResultQuery,
    disconnect_result: str | None = CalendarDisconnectResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    surface = await get_calendar_settings_surface(
        db,
        tenant_scope,
        notice_codes=calendar_settings_notice_codes(
            connect_result=connect_result,
            policy_limited=policy_limited,
            selection_result=selection_result,
            preferences_result=preferences_result,
            sync_result=sync_result,
            disconnect_result=disconnect_result,
        ),
    )
    if _is_hx_request(request):
        response = cabinet_html_response(
            render_calendar_settings_fragment(
                surface,
                embedded=True,
                csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
            ),
            hx_request=True,
        )
        set_desktop_calendar_auth_cookie(
            response,
            request=request,
            principal=principal,
            tenant_scope=tenant_scope,
        )
        return response
    response = cabinet_html_response(
        render_calendar_settings_page(
            surface,
            embedded=True,
            csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        )
    )
    set_desktop_calendar_auth_cookie(
        response,
        request=request,
        principal=principal,
        tenant_scope=tenant_scope,
    )
    return response


@router.get("/desktop/settings", response_class=HTMLResponse, include_in_schema=False)
async def embedded_settings_page(
    request: Request,
    _tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
) -> HTMLResponse:
    return cabinet_html_response(
        render_settings_page(
            embedded=True,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    )


@router.get(
    "/desktop/meetings/{meeting_id}/deletion-report",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def embedded_meeting_deletion_report_page(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting = await _authorized_lifecycle_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    report = await deletion_report_response(db, meeting=meeting)
    meeting_title = meeting.title or "Deleted meeting"
    if _is_hx_request(request):
        return cabinet_html_response(
            render_deletion_report_fragment(meeting_title, report, embedded=True),
            hx_request=True,
        )
    return cabinet_html_response(
        render_deletion_report_page(
            meeting_title,
            report,
            embedded=True,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    )
