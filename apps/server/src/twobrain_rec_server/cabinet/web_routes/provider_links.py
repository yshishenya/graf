from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.auth import (
    _provider_credentials,
    _set_browser_auth_state_cookie,
    build_provider_callback_url,
)
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.policy import read_auth_providers
from twobrain_rec_server.auth.provider_links import (
    ProviderLinkError,
    confirm_provider_link,
    create_link_intent,
)
from twobrain_rec_server.auth.providers import build_provider_registry, get_provider_adapter
from twobrain_rec_server.auth.sessions import create_callback_state, issue_callback_nonce
from twobrain_rec_server.cabinet.queries import get_provider_link_settings_surface
from twobrain_rec_server.cabinet.rendering import render_provider_link_settings_page
from twobrain_rec_server.cabinet.templates import cabinet_html_response
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
)
from twobrain_rec_server.db.models import AuthCallbackState
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])
ProviderLinkResultQuery = Query(default=None, max_length=48, alias="result")


def _provider_link_path(*, link_state_id: UUID, embedded: bool, result: str | None = None) -> str:
    path = "/desktop/settings/provider-links" if embedded else "/settings/provider-links"
    suffix = f"?result={result}" if result else ""
    return f"{path}/{link_state_id}{suffix}"


def _account_settings_path(*, embedded: bool, result: str) -> str:
    path = "/desktop/settings/account" if embedded else "/settings/account"
    safe_result = {
        "confirmed": "confirmed",
        "provider_link_conflict": "provider_link_conflict",
        "merge_blocked": "merge_blocked",
        "provider_link_denied": "provider_link_denied",
        "provider_link_expired": "provider_link_expired",
    }.get(result, "provider_link_denied")
    return f"{path}?provider_link={safe_result}"


def _is_embedded(request: Request) -> bool:
    return request.url.path.startswith("/desktop/")


def _require_link_session(principal: AuthenticatedPrincipal, tenant_scope: TenantScope) -> None:
    if (
        not principal.auth_via_session
        or principal.session_id is None
        or principal.session_workspace_id != tenant_scope.workspace_id
    ):
        raise ProblemDetail(
            status=403,
            code="provider_link_session_required",
            title="Provider link session required",
        )


@router.get("/settings/provider-links/{link_state_id}", response_class=HTMLResponse, include_in_schema=False)
@router.get(
    "/desktop/settings/provider-links/{link_state_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def provider_link_settings_page(
    request: Request,
    link_state_id: UUID,
    result: str | None = ProviderLinkResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    surface = await get_provider_link_settings_surface(
        db,
        tenant_scope,
        link_state_id=link_state_id,
    )
    if surface is None:
        raise ProblemDetail(status=404, code="provider_link_not_found", title="Provider link not found")
    return cabinet_html_response(
        render_provider_link_settings_page(
            surface,
            embedded=_is_embedded(request),
            csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "settings",
                principal=principal,
                tenant_scope=tenant_scope,
                device_class="desktop_webview" if _is_embedded(request) else "browser",
            ),
            result=result,
        )
    )


@router.post("/settings/provider-links/{provider}/start", include_in_schema=False, dependencies=[WebCSRFDependency])
@router.post(
    "/desktop/settings/provider-links/{provider}/start",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def start_provider_link_from_settings(
    provider: str,
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    _require_link_session(principal, tenant_scope)
    normalized_provider = provider.lower()
    try:
        adapter = get_provider_adapter(normalized_provider)
    except ValueError as exc:
        raise ProblemDetail(status=403, code="provider_missing", title="Provider is not configured") from exc
    snapshot = await read_auth_providers(
        db,
        tenant_scope.workspace_id,
        adapters=build_provider_registry(),
        persist_defaults=True,
    )
    provider_policy = next(
        (entry for entry in snapshot.providers if entry.provider == normalized_provider), None
    )
    if provider_policy is None or not provider_policy.enabled:
        raise ProblemDetail(status=403, code="provider_disabled", title="Provider disabled")
    browser_state_nonce = issue_callback_nonce()
    state = create_callback_state(
        db,
        provider=normalized_provider,
        workspace_id=tenant_scope.workspace_id,
        requested_redirect=None,
        browser_state_nonce=browser_state_nonce,
        ttl_seconds=request.app.state.settings.auth_callback_state_ttl_seconds,
    )
    await db.flush()
    callback_state = await db.get(AuthCallbackState, state.id)
    if callback_state is None:
        raise ProblemDetail(status=503, code="provider_link_unavailable", title="Provider link unavailable")
    try:
        link = await create_link_intent(
            db,
            principal=principal,
            workspace_id=tenant_scope.workspace_id,
            provider=normalized_provider,
            callback_state=callback_state,
        )
    except ProviderLinkError as exc:
        raise ProblemDetail(status=403, code=exc.code, title="Provider link denied") from exc
    callback_state.requested_redirect = _provider_link_path(
        link_state_id=link.id,
        embedded=_is_embedded(request),
    )
    callback_url = build_provider_callback_url(request, normalized_provider)
    credentials = _provider_credentials(request.app.state.settings, normalized_provider, callback_url)
    authorization_url = adapter.build_authorization_url(
        client_id=credentials.client_id,
        client_secret=credentials.client_secret,
        redirect_uri=callback_url,
        state=state.state_nonce,
        return_url=None,
        workspace_id=str(tenant_scope.workspace_id),
    )
    await db.commit()
    response = RedirectResponse(authorization_url, status_code=303)
    _set_browser_auth_state_cookie(
        response,
        nonce=browser_state_nonce,
        max_age=request.app.state.settings.auth_callback_state_ttl_seconds,
    )
    return response


@router.post(
    "/settings/provider-links/{link_state_id}/confirm",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/settings/provider-links/{link_state_id}/confirm",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def confirm_provider_link_from_settings(
    link_state_id: UUID,
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    _require_link_session(principal, tenant_scope)
    try:
        confirmed = await confirm_provider_link(
            db, principal=principal, link_state_id=link_state_id
        )
    except ProviderLinkError as exc:
        await db.commit()
        return RedirectResponse(
            _account_settings_path(embedded=_is_embedded(request), result=exc.code),
            status_code=303,
        )
    await db.commit()
    prefix = "/desktop" if _is_embedded(request) else ""
    if confirmed.status in {"merge_preview_ready", "merge_blocked"} and confirmed.merge_intent_id is not None:
        return RedirectResponse(
            f"{prefix}/settings/account/merge/{confirmed.merge_intent_id}", status_code=303
        )
    if confirmed.status == "merge_completed":
        response = RedirectResponse(
            f"/login?next={prefix}/settings/account&error=auth_session_invalid",
            status_code=303,
        )
        response.delete_cookie(
            key="__Host-twobrain_rec_owner_session",
            path="/",
            secure=True,
            httponly=True,
            samesite="lax",
        )
        return response
    return RedirectResponse(
        _account_settings_path(embedded=_is_embedded(request), result="confirmed"),
        status_code=303,
    )
