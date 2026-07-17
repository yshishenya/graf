from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.auth.workspace_onboarding import (
    decide_workspace_join_offer,
    list_workspace_join_offers,
)
from twobrain_rec_server.cabinet.web_routes.support import (
    LoginDbDependency,
    PrincipalDependency,
    WebCSRFDependency,
)

router = APIRouter(tags=["cabinet-web"])


def _require_offer_session(principal: AuthenticatedPrincipal) -> UUID:
    if not principal.auth_via_session or principal.session_workspace_id is None:
        raise ProblemDetail(
            status=403,
            code="workspace_join_session_required",
            title="Workspace join session required",
        )
    return principal.session_workspace_id


@router.get("/settings/join-offers", include_in_schema=False)
async def list_workspace_offers(
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = LoginDbDependency,
) -> JSONResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    current_workspace_id = _require_offer_session(principal)
    offers = await list_workspace_join_offers(
        db,
        organization_id=principal.organization_id,
        current_workspace_id=current_workspace_id,
        user_id=principal.user_id,
    )
    await db.commit()
    return JSONResponse(
        {
            "offers": [
                {
                    "id": str(offer.id),
                    "workspace_name": offer.workspace_name,
                    "invited_role": offer.invited_role,
                    "expires_at": offer.expires_at.isoformat(),
                }
                for offer in offers
            ]
        }
    )


@router.post(
    "/settings/join-offers/{offer_id}/{action}",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
    response_model=None,
)
async def decide_workspace_offer(
    offer_id: UUID,
    action: Literal["accept", "reject"],
    return_to_settings: bool = Query(default=False),
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = LoginDbDependency,
) -> JSONResponse | RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    current_workspace_id = _require_offer_session(principal)
    try:
        offer, idempotent = await decide_workspace_join_offer(
            db,
            organization_id=principal.organization_id,
            current_workspace_id=current_workspace_id,
            user_id=principal.user_id,
            offer_id=offer_id,
            action=action,
        )
    except ProblemDetail:
        if not return_to_settings:
            raise
        await db.commit()
        return RedirectResponse("/settings?workspace_offer=unavailable", status_code=303)
    await db.commit()
    if return_to_settings:
        return RedirectResponse(f"/settings?workspace_offer={offer.status}", status_code=303)
    return JSONResponse({"status": offer.status, "idempotent": idempotent})
