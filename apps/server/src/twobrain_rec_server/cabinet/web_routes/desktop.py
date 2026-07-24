from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.dependencies import (
    set_desktop_calendar_auth_cookie,
)
from twobrain_rec_server.auth.workspace_onboarding import list_active_workspaces
from twobrain_rec_server.cabinet.deletion_rendering import (
    render_deletion_report_fragment,
    render_deletion_report_page,
)
from twobrain_rec_server.cabinet.queries import (
    get_cabinet_meeting_review,
    get_calendar_settings_surface,
    get_provider_link_start_options,
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
    render_meeting_unavailable_page,
    render_settings_page,
)
from twobrain_rec_server.cabinet.review_policy_rendering import render_meeting_share_fragment
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
    StorageDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _authorized_lifecycle_meeting,
    _csrf_token_for_principal,
    _is_hx_request,
    _normalize_web_meeting_status_filter,
    _request_path_with_query,
)
from twobrain_rec_server.deletion.service import deletion_report_response
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])
EmbeddedLogoutNextForm = Form(default="/login?next=/desktop/meetings", alias="next", max_length=512)


def _meeting_unavailable_response(
    request: Request,
    *,
    csrf_token: str | None,
) -> HTMLResponse:
    if _is_hx_request(request):
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return cabinet_html_response(
        render_meeting_unavailable_page(embedded=True, csrf_token=csrf_token),
        status_code=404,
    )


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
        unknown_sort_fallback="started_desc",
        normalize_response_sort=True,
        limit=limit,
    )
    raw_status = request.query_params.get("status")
    canonical_status = _normalize_web_meeting_status_filter(raw_status)
    status_was_normalized = (
        isinstance(raw_status, str)
        and raw_status != ""
        and canonical_status != raw_status
    )
    sort_was_normalized = sort != response.filters.sort
    needs_url_normalization = sort_was_normalized or status_was_normalized
    canonical_path = _request_path_with_query(
        request,
        sort_override=response.filters.sort if sort_was_normalized else None,
        status_override=status if status_was_normalized else None,
    ) if needs_url_normalization else _request_path_with_query(request)
    if needs_url_normalization and not _is_hx_request(request):
        return RedirectResponse(url=canonical_path, status_code=303)
    if _is_hx_request(request):
        result = cabinet_html_response(
            render_meeting_list_fragment(
                response, embedded=True, poll_url=canonical_path
            ),
            hx_request=True,
        )
        if needs_url_normalization:
            result.headers["HX-Replace-Url"] = canonical_path
        return result
    return cabinet_html_response(
        render_meeting_list_page(
            response,
            embedded=True,
            csrf_token=_csrf_token_for_principal(request, principal),
            poll_url=canonical_path,
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "embedded_desktop_webview",
                principal=principal,
                tenant_scope=tenant_scope,
                device_class="desktop_webview",
            ),
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
    meeting_id: str,
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
    try:
        parsed_meeting_id = UUID(meeting_id)
    except ValueError:
        return _meeting_unavailable_response(
            request,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    response = await get_cabinet_meeting_review(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=parsed_meeting_id,
        viewer_user_id=principal.user_id,
        storage=storage,
        include_calendar_correction_candidates=calendar_context_action == "change",
        external_invitations_enabled=request.app.state.settings.share_external_invitations_enabled,
        invitation_encryption_key=(
            request.app.state.settings.credential_encryption_key_file.read_bytes().strip()
            if request.app.state.settings.credential_encryption_key_file is not None
            else None
        ),
    )
    if response is None:
        return _meeting_unavailable_response(
            request,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    if response.access is not None and not response.access.can_view_full_meeting:
        return RedirectResponse(
            url=f"/api/v1/cabinet/meetings/{parsed_meeting_id}/shared-summary",
            status_code=302,
        )
    if _is_hx_request(request):
        return cabinet_html_response(
            render_meeting_detail_fragment(
                response,
                embedded=True,
                csrf_token=_csrf_token_for_principal(request, principal),
                poll_url=_request_path_with_query(request),
            ),
            hx_request=True,
        )
    return cabinet_html_response(
        render_meeting_detail_page(
            response,
            embedded=True,
            csrf_token=_csrf_token_for_principal(request, principal),
            poll_url=_request_path_with_query(request),
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "meeting_result_detail",
                principal=principal,
                tenant_scope=tenant_scope,
                device_class="desktop_webview",
            ),
        )
    )


@router.get(
    "/desktop/meetings/{meeting_id}/share",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def embedded_meeting_share_fragment(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    response = await get_cabinet_meeting_review(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
        storage=storage,
        external_invitations_enabled=request.app.state.settings.share_external_invitations_enabled,
        invitation_encryption_key=(
            request.app.state.settings.credential_encryption_key_file.read_bytes().strip()
            if request.app.state.settings.credential_encryption_key_file is not None
            else None
        ),
    )
    if response is None or response.access is None or not response.access.can_share:
        return _meeting_unavailable_response(
            request,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    return cabinet_html_response(render_meeting_share_fragment(response), hx_request=True)


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
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "settings",
                principal=principal,
                tenant_scope=tenant_scope,
                device_class="desktop_webview",
            ),
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
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    provider_link_options = await get_provider_link_start_options(db, tenant_scope)
    spaces = await list_active_workspaces(
        db,
        organization_id=principal.organization_id,
        current_workspace_id=tenant_scope.workspace_id,
        user_id=principal.user_id,
    )
    await db.commit()
    return cabinet_html_response(
        render_settings_page(
            embedded=True,
            csrf_token=_csrf_token_for_principal(request, principal),
            provider_link_options=provider_link_options,
            workspace_spaces=spaces,
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "settings",
                principal=principal,
                tenant_scope=tenant_scope,
                device_class="desktop_webview",
            ),
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
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "deletion",
                principal=principal,
                tenant_scope=tenant_scope,
                device_class="desktop_webview",
            ),
        )
    )
