from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.cabinet.meeting_titles import (
    TITLE_ERRORS,
    meeting_title_version,
    save_meeting_title,
)
from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review
from twobrain_rec_server.cabinet.rendering import render_meeting_detail_page
from twobrain_rec_server.cabinet.templates import cabinet_html_response
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    StorageDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
)
from twobrain_rec_server.db.models import Meeting

router = APIRouter(tags=["cabinet-web"])


@router.post(
    "/meetings/{meeting_id}/title", include_in_schema=False, dependencies=[WebCSRFDependency]
)
@router.post(
    "/desktop/meetings/{meeting_id}/title",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def update_meeting_title(
    request: Request,
    meeting_id: UUID,
    title: str = Form(default=""),
    expected_version: str = Form(default=""),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    embedded = request.url.path.startswith("/desktop/")
    wants_json = "application/json" in request.headers.get("accept", "")
    try:
        meeting = await save_meeting_title(
            db,
            workspace_id=tenant_scope.workspace_id,
            meeting_id=meeting_id,
            user_id=principal.user_id,
            title=title,
            expected_version=expected_version,
        )
    except ProblemDetail as problem:
        if problem.code not in TITLE_ERRORS:
            raise
        # These errors are raised only after the locked owner/deletion checks.
        meeting = await db.get(Meeting, meeting_id)
        payload = {"code": problem.code, "message": TITLE_ERRORS[problem.code]}
        if problem.code == "meeting_title_conflict":
            payload.update(title=meeting.title or "", title_version=meeting_title_version(meeting))
        if wants_json:
            return JSONResponse(
                payload, status_code=problem.status, headers={"Cache-Control": "private, no-store"}
            )
        review = await get_cabinet_meeting_review(
            db,
            workspace_id=tenant_scope.workspace_id,
            meeting_id=meeting_id,
            viewer_user_id=principal.user_id,
            storage=storage,
        )
        if review is None or review.access is None or review.access.state != "owner":
            raise ProblemDetail(
                status=404, code="meeting_not_found", title="Встреча больше недоступна"
            ) from None
        return cabinet_html_response(
            render_meeting_detail_page(
                review,
                embedded=embedded,
                csrf_token=_csrf_token_for_principal(request, principal),
                title_edit={"draft": title, "error": TITLE_ERRORS[problem.code]},
            ),
            status_code=problem.status,
        )
    payload = {
        "meeting_id": str(meeting.id),
        "title": meeting.title,
        "title_version": meeting_title_version(meeting),
    }
    await db.commit()
    if wants_json:
        return JSONResponse(payload, headers={"Cache-Control": "private, no-store"})
    base = "/desktop/meetings" if embedded else "/meetings"
    return RedirectResponse(
        f"{base}/{meeting_id}", status_code=303, headers={"Cache-Control": "private, no-store"}
    )
