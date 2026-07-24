from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review
from twobrain_rec_server.cabinet.speakers import save_speaker_name
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    StorageDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _authorized_lifecycle_meeting,
)

router = APIRouter(tags=["cabinet-web"])


@router.post(
    "/meetings/{meeting_id}/speakers/{speaker_key}",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/meetings/{meeting_id}/speakers/{speaker_key}",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def update_speaker_name(
    request: Request,
    meeting_id: UUID,
    speaker_key: str,
    display_name: str = Form(default=""),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    await _authorized_lifecycle_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    review = await get_cabinet_meeting_review(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
        storage=storage,
        external_invitations_enabled=request.app.state.settings.share_external_invitations_enabled,
    )
    if review is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    await save_speaker_name(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        speaker_key=speaker_key,
        display_name=display_name,
        actor_user_id=principal.user_id,
        known_speaker_keys={speaker.speaker_key for speaker in review.speakers.speakers},
    )
    await db.commit()
    base = "/desktop/meetings" if request.url.path.startswith("/desktop/") else "/meetings"
    return RedirectResponse(f"{base}/{meeting_id}", status_code=303)
