from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.auth import revoke_device
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.workspace_onboarding import (
    list_active_workspaces,
    list_workspace_join_offers,
)
from twobrain_rec_server.cabinet.queries import (
    get_account_settings_surface,
    get_provider_link_start_options,
)
from twobrain_rec_server.cabinet.rendering import render_settings_page
from twobrain_rec_server.cabinet.templates import cabinet_html_response
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
)
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])

WorkspaceOfferResultQuery = Query(default=None, max_length=24, alias="workspace_offer")
WorkspaceSwitchResultQuery = Query(default=None, max_length=24, alias="space_switch")
ProviderLinkResultQuery = Query(default=None, max_length=48, alias="provider_link")
DeviceRevokeResultQuery = Query(default=None, max_length=24, alias="device_revoke")


async def _render_settings(
    request: Request,
    *,
    category: str,
    embedded: bool,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    db: AsyncSession | None,
    workspace_offer: str | None = None,
    space_switch: str | None = None,
    provider_link: str | None = None,
    device_revoke: str | None = None,
) -> HTMLResponse:
    workspace_spaces = ()
    workspace_join_offers = ()
    provider_link_options = ()
    account_surface = None
    if category == "workspace" and db is not None:
        workspace_join_offers = await list_workspace_join_offers(
            db,
            organization_id=principal.organization_id,
            current_workspace_id=tenant_scope.workspace_id,
            user_id=principal.user_id,
        )
        workspace_spaces = await list_active_workspaces(
            db,
            organization_id=principal.organization_id,
            current_workspace_id=tenant_scope.workspace_id,
            user_id=principal.user_id,
        )
    elif category == "account" and db is not None:
        provider_link_options = await get_provider_link_start_options(db, tenant_scope)
        account_surface = await get_account_settings_surface(db, tenant_scope)
    elif category in {"workspace", "account"}:
        from twobrain_rec_server.cabinet import view_models as cabinet_view_models

        account_surface = cabinet_view_models.AccountSettingsSurface(unavailable=True)
    if db is not None:
        await db.commit()
    return cabinet_html_response(
        render_settings_page(
            embedded=embedded,
            category=category,
            csrf_token=_csrf_token_for_principal(
                request,
                principal,
                tenant_scope=tenant_scope,
            ),
            provider_link_options=provider_link_options,
            workspace_spaces=workspace_spaces,
            workspace_join_offers=workspace_join_offers,
            workspace_offer_result=workspace_offer,
            workspace_switch_result=space_switch,
            account_surface=account_surface,
            provider_link_result=provider_link,
            device_revoke_result=device_revoke,
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "settings",
                principal=principal,
                tenant_scope=tenant_scope,
                device_class="desktop_webview" if embedded else "browser",
            ),
        )
    )


@router.get("/settings", response_class=HTMLResponse, include_in_schema=False)
async def settings_overview_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="overview",
        embedded=False,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
    )


@router.get("/settings/recording", response_class=HTMLResponse, include_in_schema=False)
async def settings_recording_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="recording",
        embedded=False,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
    )


@router.get("/settings/summaries", response_class=HTMLResponse, include_in_schema=False)
async def settings_summaries_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="summaries",
        embedded=False,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
    )


@router.get("/settings/workspace", response_class=HTMLResponse, include_in_schema=False)
async def settings_workspace_page(
    request: Request,
    workspace_offer: str | None = WorkspaceOfferResultQuery,
    space_switch: str | None = WorkspaceSwitchResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="workspace",
        embedded=False,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        workspace_offer=workspace_offer,
        space_switch=space_switch,
    )


@router.get("/settings/account", response_class=HTMLResponse, include_in_schema=False)
async def settings_account_page(
    request: Request,
    provider_link: str | None = ProviderLinkResultQuery,
    device_revoke: str | None = DeviceRevokeResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="account",
        embedded=False,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        provider_link=provider_link,
        device_revoke=device_revoke,
    )


@router.get("/account", response_class=HTMLResponse, include_in_schema=False)
async def account_center_page(
    request: Request,
    provider_link: str | None = ProviderLinkResultQuery,
    device_revoke: str | None = DeviceRevokeResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    """Stable account-center entry point used by the cabinet navigation."""
    return await _render_settings(
        request,
        category="account",
        embedded=False,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        provider_link=provider_link,
        device_revoke=device_revoke,
    )


@router.post(
    "/settings/account/devices/{device_id}/revoke",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def revoke_settings_device(
    request: Request,
    device_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503,
            code="cabinet_store_unavailable",
            title="Cabinet store unavailable",
        )
    await revoke_device(
        request=request,
        device_id=device_id,
        principal=principal,
        x_workspace_id=str(tenant_scope.workspace_id),
        db=db,
    )
    return RedirectResponse("/settings/account?device_revoke=revoked", status_code=303)


@router.get("/desktop/settings", response_class=HTMLResponse, include_in_schema=False)
async def embedded_settings_overview_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="overview",
        embedded=True,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
    )


@router.get("/desktop/settings/recording", response_class=HTMLResponse, include_in_schema=False)
async def embedded_settings_recording_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="recording",
        embedded=True,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
    )


@router.get("/desktop/settings/summaries", response_class=HTMLResponse, include_in_schema=False)
async def embedded_settings_summaries_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="summaries",
        embedded=True,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
    )


@router.get("/desktop/settings/workspace", response_class=HTMLResponse, include_in_schema=False)
async def embedded_settings_workspace_page(
    request: Request,
    workspace_offer: str | None = WorkspaceOfferResultQuery,
    space_switch: str | None = WorkspaceSwitchResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="workspace",
        embedded=True,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        workspace_offer=workspace_offer,
        space_switch=space_switch,
    )


@router.get("/desktop/settings/account", response_class=HTMLResponse, include_in_schema=False)
async def embedded_settings_account_page(
    request: Request,
    provider_link: str | None = ProviderLinkResultQuery,
    device_revoke: str | None = DeviceRevokeResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="account",
        embedded=True,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        provider_link=provider_link,
        device_revoke=device_revoke,
    )


@router.get("/desktop/account", response_class=HTMLResponse, include_in_schema=False)
async def embedded_account_center_page(
    request: Request,
    provider_link: str | None = ProviderLinkResultQuery,
    device_revoke: str | None = DeviceRevokeResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="account",
        embedded=True,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        provider_link=provider_link,
        device_revoke=device_revoke,
    )


@router.post(
    "/desktop/settings/account/devices/{device_id}/revoke",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def revoke_embedded_settings_device(
    request: Request,
    device_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503,
            code="cabinet_store_unavailable",
            title="Cabinet store unavailable",
        )
    await revoke_device(
        request=request,
        device_id=device_id,
        principal=principal,
        x_workspace_id=str(tenant_scope.workspace_id),
        db=db,
    )
    return RedirectResponse("/desktop/settings/account?device_revoke=revoked", status_code=303)
