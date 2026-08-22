from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.exc import SQLAlchemyError
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
    apply_provider_link_auth_context,
    apply_provider_link_request_context,
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
from twobrain_rec_server.db.tenant_context import (
    AuthCallbackLookupContext,
    apply_tenant_context,
)
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
        "provider_link_invalid": "provider_link_invalid",
        "provider_link_reused": "provider_link_reused",
        "provider_link_unavailable": "provider_link_unavailable",
        "reauth_required": "reauth_required",
    }.get(result, "provider_link_denied")
    return f"{path}?provider_link={safe_result}"


def _account_settings_redirect(request: Request, *, result: str) -> RedirectResponse:
    return RedirectResponse(
        _account_settings_path(embedded=_is_embedded(request), result=result),
        status_code=303,
    )


def _provider_link_result(code: str) -> str:
    if code in {"provider_link_expired", "callback_state_expired"}:
        return "provider_link_expired"
    if code in {"provider_link_reused", "callback_state_reused"}:
        return "provider_link_reused"
    if code == "provider_link_session_required":
        return "reauth_required"
    if code in {
        "provider_link_not_found",
        "provider_link_candidate_missing",
        "provider_link_source_identity_missing",
        "provider_link_callback_mismatch",
        "callback_state_invalid",
        "callback_parse_error",
    }:
        return "provider_link_invalid"
    if code in {
        "billing_conflict",
        "calendar_ownership_conflict",
        "deletion_state_conflict",
        "export_in_progress",
        "fair_use_conflict",
        "meeting_owner_conflict",
        "referral_conflict",
        "settings_conflict",
        "upload_in_progress",
        "workspace_ownership_conflict",
        "workspace_role_conflict",
    }:
        return "merge_blocked"
    if code in {"provider_link_conflict", "workspace_scope_denied"}:
        return "provider_link_denied"
    return "provider_link_unavailable"


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


@router.get(
    "/settings/provider-links/{link_state_id}", response_class=HTMLResponse, include_in_schema=False
)
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
) -> Response:
    if db is None:
        return _account_settings_redirect(request, result="provider_link_unavailable")
    try:
        surface = await get_provider_link_settings_surface(
            db,
            tenant_scope,
            link_state_id=link_state_id,
        )
    except SQLAlchemyError:
        await db.rollback()
        return _account_settings_redirect(request, result="provider_link_unavailable")
    if surface is None:
        await db.rollback()
        return _account_settings_redirect(request, result="provider_link_invalid")
    if surface.status not in {"expired", "rejected"} and not surface.can_confirm:
        surface = replace(surface, provider=None)
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


@router.post(
    "/settings/provider-links/{provider}/start",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
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
        return _account_settings_redirect(request, result="provider_link_unavailable")
    try:
        _require_link_session(principal, tenant_scope)
    except ProblemDetail:
        return _account_settings_redirect(request, result="reauth_required")
    normalized_provider = provider.lower()
    try:
        adapter = get_provider_adapter(normalized_provider)
    except ValueError:
        return _account_settings_redirect(request, result="provider_link_unavailable")
    try:
        snapshot = await read_auth_providers(
            db,
            tenant_scope.workspace_id,
            adapters=build_provider_registry(),
            persist_defaults=True,
        )
    except SQLAlchemyError:
        await db.rollback()
        return _account_settings_redirect(request, result="provider_link_unavailable")
    provider_policy = next(
        (entry for entry in snapshot.providers if entry.provider == normalized_provider), None
    )
    if provider_policy is None or not provider_policy.enabled:
        await db.rollback()
        return _account_settings_redirect(request, result="provider_link_unavailable")
    try:
        await apply_provider_link_auth_context(
            db,
            principal=principal,
            workspace_id=tenant_scope.workspace_id,
        )
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
            raise ProviderLinkError("provider_link_unavailable")
        await apply_provider_link_request_context(
            db,
            principal=principal,
            workspace_id=tenant_scope.workspace_id,
        )
        link = await create_link_intent(
            db,
            principal=principal,
            workspace_id=tenant_scope.workspace_id,
            provider=normalized_provider,
            callback_state=callback_state,
        )
        callback_state.requested_redirect = _provider_link_path(
            link_state_id=link.id,
            embedded=_is_embedded(request),
        )
        await apply_tenant_context(
            db,
            AuthCallbackLookupContext(state_nonce=state.state_nonce),
        )
        await db.flush()
        callback_url = build_provider_callback_url(request, normalized_provider)
        credentials = _provider_credentials(
            request.app.state.settings,
            normalized_provider,
            callback_url,
        )
        authorization_url = adapter.build_authorization_url(
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            redirect_uri=callback_url,
            state=state.state_nonce,
            return_url=None,
            workspace_id=str(tenant_scope.workspace_id),
        )
        await db.commit()
    except ProviderLinkError as exc:
        await db.rollback()
        return _account_settings_redirect(request, result=_provider_link_result(exc.code))
    except (SQLAlchemyError, ValueError):
        await db.rollback()
        return _account_settings_redirect(request, result="provider_link_unavailable")
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
        return _account_settings_redirect(request, result="provider_link_unavailable")
    try:
        _require_link_session(principal, tenant_scope)
    except ProblemDetail:
        return _account_settings_redirect(request, result="reauth_required")
    try:
        confirmed = await confirm_provider_link(
            db, principal=principal, link_state_id=link_state_id
        )
    except ProviderLinkError as exc:
        response = _account_settings_redirect(request, result=_provider_link_result(exc.code))
        await db.commit()
        return response
    except SQLAlchemyError:
        await db.rollback()
        return _account_settings_redirect(request, result="provider_link_unavailable")
    try:
        prefix = "/desktop" if _is_embedded(request) else ""
        if (
            confirmed.status in {"merge_preview_ready", "merge_blocked"}
            and confirmed.merge_intent_id is not None
        ):
            response = RedirectResponse(
                f"{prefix}/settings/account/merge/{confirmed.merge_intent_id}", status_code=303
            )
        else:
            response = _account_settings_redirect(request, result="confirmed")
        await db.commit()
        return response
    except Exception:
        await db.rollback()
        raise
