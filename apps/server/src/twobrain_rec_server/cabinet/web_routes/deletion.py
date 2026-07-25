from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.cabinet.deletion_rendering import (
    render_deletion_report_fragment,
    render_deletion_report_page,
)
from twobrain_rec_server.cabinet.rendering import _base_path
from twobrain_rec_server.cabinet.templates import (
    cabinet_html_response,
)
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    StorageDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _authorized_lifecycle_meeting,
    _authorized_meeting,
    _csrf_token_for_principal,
    _ensure_lifecycle_manager,
    _is_hx_request,
)
from twobrain_rec_server.deletion.service import deletion_report_response, request_meeting_deletion
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])


@router.get(
    "/meetings/{meeting_id}/deletion-report",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def meeting_deletion_report_page(
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
            render_deletion_report_fragment(meeting_title, report),
            hx_request=True,
        )
    return cabinet_html_response(
        render_deletion_report_page(
            meeting_title,
            report,
            csrf_token=_csrf_token_for_principal(request, principal),
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "deletion",
                principal=principal,
                tenant_scope=tenant_scope,
            ),
        )
    )


@router.post(
    "/meetings/{meeting_id}/deletion-requests",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/meetings/{meeting_id}/deletion-requests",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def meeting_deletion_request_page(
    request: Request,
    meeting_id: UUID,
    confirmation_boundary: str = Form(...),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    _ensure_lifecycle_manager(decision)
    await request_meeting_deletion(
        db,
        meeting=meeting,
        actor_user_id=principal.user_id,
        device_id=principal.session_device_id,
        confirmation_boundary=confirmation_boundary,
        local_buffer_expiry_days=request.app.state.settings.retention_local_buffer_expiry_days,
        storage=storage,
        temporal_client=getattr(request.app.state, "temporal_client", None),
    )
    await db.commit()
    embedded = request.url.path.startswith("/desktop/")
    if _is_hx_request(request):
        return cabinet_html_response(
            "",
            status_code=202,
            hx_request=True,
        )
    return RedirectResponse(_base_path(embedded), status_code=303)
