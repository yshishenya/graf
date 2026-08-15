from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.workspace_onboarding import (
    activate_workspace_session,
    decide_workspace_join_offer,
    list_active_workspaces,
    list_workspace_join_offers,
)
from twobrain_rec_server.cabinet.web_routes.auth_email_flow import _set_browser_auth_cookie
from twobrain_rec_server.cabinet.web_routes.support import (
    LoginDbDependency,
    PrincipalDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
)

router = APIRouter(tags=["cabinet-web"])


def _workspace_settings_path(request: Request, *, result_key: str, result: str) -> str:
    prefix = "/desktop/settings/workspace" if request.url.path.startswith("/desktop/") else "/settings/workspace"
    return f"{prefix}?{result_key}={result}"


def _require_offer_session(principal: AuthenticatedPrincipal) -> UUID:
    if not principal.auth_via_session or principal.session_workspace_id is None:
        raise ProblemDetail(
            status=403,
            code="workspace_join_session_required",
            title="Workspace join session required",
        )
    return principal.session_workspace_id


@router.get("/settings/spaces", include_in_schema=False)
@router.get("/desktop/settings/spaces", include_in_schema=False)
async def list_accessible_spaces(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> JSONResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    spaces = await list_active_workspaces(
        db,
        organization_id=principal.organization_id,
        current_workspace_id=tenant_scope.workspace_id,
        internal_workspace_id=request.app.state.settings.web_login_workspace_id,
        user_id=principal.user_id,
    )
    return JSONResponse(
        {
            "spaces": [
                {
                    "id": str(space.id),
                    "name": space.name,
                    "kind": space.kind,
                    "role": space.role,
                    "active": space.active,
                }
                for space in spaces
            ]
        }
    )


@router.post(
    "/settings/spaces/{workspace_id}/activate",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
    response_model=None,
)
@router.post(
    "/desktop/settings/spaces/{workspace_id}/activate",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
    response_model=None,
)
async def activate_accessible_space(
    request: Request,
    workspace_id: UUID,
    return_to_settings: bool = Query(default=False),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> JSONResponse | RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    if not principal.auth_via_session or principal.session_id is None:
        raise ProblemDetail(
            status=403,
            code="workspace_activation_session_required",
            title="Workspace activation session required",
        )
    activated = await activate_workspace_session(
        db,
        organization_id=principal.organization_id,
        current_workspace_id=tenant_scope.workspace_id,
        internal_workspace_id=request.app.state.settings.web_login_workspace_id,
        user_id=principal.user_id,
        current_session_id=principal.session_id,
        target_workspace_id=workspace_id,
    )
    await db.commit()
    if return_to_settings:
        response = RedirectResponse(
            _workspace_settings_path(
                request,
                result_key="space_switch",
                result="activated",
            ),
            status_code=303,
        )
    else:
        response = JSONResponse(
            {
                "active_space": {
                    "id": str(activated.workspace.id),
                    "name": activated.workspace.name,
                    "kind": activated.workspace.kind,
                    "role": activated.workspace.role,
                    "active": True,
                }
            }
        )
    if activated.issued_session.token:
        _set_browser_auth_cookie(
            response,
            token=activated.issued_session.token,
            expires_at=activated.issued_session.expires_at,
        )
    return response


@router.get("/settings/join-offers", include_in_schema=False)
async def list_workspace_offers(
    request: Request,
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
        internal_workspace_id=request.app.state.settings.web_login_workspace_id,
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
@router.post(
    "/desktop/settings/join-offers/{offer_id}/{action}",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
    response_model=None,
)
async def decide_workspace_offer(
    request: Request,
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
            internal_workspace_id=request.app.state.settings.web_login_workspace_id,
            user_id=principal.user_id,
            offer_id=offer_id,
            action=action,
        )
    except ProblemDetail:
        if not return_to_settings:
            raise
        await db.commit()
        return RedirectResponse(
            _workspace_settings_path(
                request,
                result_key="workspace_offer",
                result="unavailable",
            ),
            status_code=303,
        )
    await db.commit()
    if return_to_settings:
        return RedirectResponse(
            _workspace_settings_path(
                request,
                result_key="workspace_offer",
                result=offer.status,
            ),
            status_code=303,
        )
    return JSONResponse({"status": offer.status, "idempotent": idempotent})
