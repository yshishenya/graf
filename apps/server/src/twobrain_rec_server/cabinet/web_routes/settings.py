from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.auth import revoke_device
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth import email_delivery
from twobrain_rec_server.auth.account_closure import (
    cancel_account_close,
    schedule_account_close,
)
from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.dependencies import (
    auth_session_cookie_name,
    auth_session_cookie_secure,
    is_web_cookie_session,
)
from twobrain_rec_server.auth.provider_links import (
    RECOVERY_CAPABLE_PROVIDERS,
    recovery_safe_unlink_allowed,
)
from twobrain_rec_server.auth.rate_limit import enforce_auth_rate_limits
from twobrain_rec_server.auth.workspace_onboarding import (
    list_active_workspaces,
    list_workspace_join_offers,
)
from twobrain_rec_server.billing.notification_preferences import NotificationPreferences
from twobrain_rec_server.cabinet.auth_rendering import render_email_code_page
from twobrain_rec_server.cabinet.queries import (
    get_account_profile_view,
    get_account_settings_surface,
    get_provider_link_start_options,
)
from twobrain_rec_server.cabinet.rendering import render_settings_page
from twobrain_rec_server.cabinet.templates import cabinet_html_response
from twobrain_rec_server.cabinet.web_routes.auth_email_flow import (
    EMAIL_LINK_PROVIDER,
    _create_email_login_state,
    _finalize_email_callback,
    _issue_email_login_code,
    _normalize_email,
    _should_echo_email_code,
    consume_email_link_code,
)
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
)
from twobrain_rec_server.db.models import (
    AuthSession,
    AuthSessionDeviceBinding,
    BillingNotificationPreference,
    ExternalIdentity,
    RegisteredDevice,
    UserIdentity,
)
from twobrain_rec_server.db.tenant_context import (
    TenantDatabaseContext,
    apply_tenant_context,
    apply_tenant_scope,
)
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])

WorkspaceOfferResultQuery = Query(default=None, max_length=24, alias="workspace_offer")
WorkspaceSwitchResultQuery = Query(default=None, max_length=24, alias="space_switch")
ProviderLinkResultQuery = Query(default=None, max_length=48, alias="provider_link")
DeviceRevokeResultQuery = Query(default=None, max_length=24, alias="device_revoke")
SessionResultQuery = Query(default=None, max_length=24, alias="session")
NotificationResultQuery = Query(default=None, max_length=24, alias="notification")
AccountCloseResultQuery = Query(default=None, max_length=24, alias="account_close")
ProfileResultQuery = Query(default=None, max_length=24, alias="profile")
PreferencesResultQuery = Query(default=None, max_length=24, alias="preferences")
ProviderUnlinkResultQuery = Query(default=None, max_length=48, alias="provider_unlink")


def _settings_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


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
    session: str | None = None,
    notification: str | None = None,
    account_close: str | None = None,
    profile: str | None = None,
    preferences: str | None = None,
    provider_unlink: str | None = None,
) -> HTMLResponse:
    workspace_spaces = ()
    workspace_join_offers = ()
    provider_link_options = ()
    account_surface = None
    notification_preferences = NotificationPreferences()
    if category == "workspace" and db is not None:
        workspace_join_offers = await list_workspace_join_offers(
            db,
            organization_id=principal.organization_id,
            current_workspace_id=tenant_scope.workspace_id,
            internal_workspace_id=request.app.state.settings.web_login_workspace_id,
            user_id=principal.user_id,
        )
        workspace_spaces = await list_active_workspaces(
            db,
            organization_id=principal.organization_id,
            current_workspace_id=tenant_scope.workspace_id,
            internal_workspace_id=request.app.state.settings.web_login_workspace_id,
            user_id=principal.user_id,
        )
    elif category == "account" and db is not None:
        provider_link_options = await get_provider_link_start_options(db, tenant_scope)
        account_surface = await get_account_settings_surface(db, tenant_scope)
    elif category == "notifications" and db is not None:
        preference = await db.get(BillingNotificationPreference, principal.user_id)
        if preference is not None:
            notification_preferences = NotificationPreferences(
                optional_email_enabled=preference.optional_email_enabled,
                optional_in_app_enabled=preference.optional_in_app_enabled,
            )
    elif category in {"workspace", "account"}:
        from twobrain_rec_server.cabinet import view_models as cabinet_view_models

        account_surface = cabinet_view_models.AccountSettingsSurface(unavailable=True)
    profile_view = await get_account_profile_view(db, tenant_scope) if db is not None else None
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
            profile=profile_view,
            provider_link_result=provider_link,
            device_revoke_result=device_revoke,
            session_result=session,
            notification_result=notification,
            account_close_result=account_close,
            profile_result=profile,
            preferences_result=preferences,
            provider_unlink_result=provider_unlink,
            account_active=(
                "security" if request.url.path.endswith("/account/security") else "profile"
            ),
            notification_preferences=notification_preferences,
            show_account_navigation=request.url.path.startswith(("/account", "/desktop/account")),
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
    session: str | None = SessionResultQuery,
    profile: str | None = ProfileResultQuery,
    preferences: str | None = PreferencesResultQuery,
    provider_unlink: str | None = ProviderUnlinkResultQuery,
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
        session=session,
        profile=profile,
        preferences=preferences,
        provider_unlink=provider_unlink,
    )


async def _start_email_link(
    request: Request,
    *,
    principal: AuthenticatedPrincipal,
    tenant_scope: TenantScope,
    db: AsyncSession | None,
    embedded: bool,
) -> HTMLResponse | RedirectResponse:
    prefix = "/desktop" if embedded else ""
    if db is None:
        return RedirectResponse(
            f"{prefix}/settings/account?provider_link=provider_link_unavailable",
            status_code=303,
        )
    if not principal.auth_via_session or principal.session_id is None:
        return RedirectResponse(
            f"{prefix}/settings/account?provider_link=reauth_required",
            status_code=303,
        )
    form = await request.form()
    email = _normalize_email(str(form.get("email") or ""))
    next_path = "/desktop/settings/account" if embedded else "/settings/account"
    flow = "desktop_link" if embedded else "link"
    csrf_token = _csrf_token_for_principal(request, principal, tenant_scope=tenant_scope)
    if email is None:
        return HTMLResponse(
            render_email_code_page(
                email="",
                state_nonce="",
                next_path=next_path,
                error="email_invalid",
                flow=flow,
                csrf_token=csrf_token,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "settings"
                ),
            ),
            status_code=400,
        )
    retry_after = await enforce_auth_rate_limits(
        db,
        workspace_id=tenant_scope.workspace_id,
        scopes=(
            ("email_code_start_address", email),
            ("email_code_start_ip", _settings_client_ip(request)),
        ),
        sessionmaker=getattr(request.app.state, "db_sessionmaker", None),
        scope_secret=request.app.state.settings.share_identity_hash_secret,
    )
    if retry_after is not None:
        return HTMLResponse(
            render_email_code_page(
                email=email,
                state_nonce="",
                next_path=next_path,
                error="auth_rate_limited",
                flow=flow,
                csrf_token=csrf_token,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "settings"
                ),
            ),
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )
    code = _issue_email_login_code(request.app.state.settings)
    ttl_seconds = request.app.state.settings.auth_callback_state_ttl_seconds
    state = await _create_email_login_state(
        db,
        workspace_id=tenant_scope.workspace_id,
        next_path=next_path,
        email=email,
        code=code,
        ttl_seconds=ttl_seconds,
        provider=EMAIL_LINK_PROVIDER,
        secret=request.app.state.web_csrf_secret,
    )
    dev_code = code if _should_echo_email_code(request) else None
    if dev_code is None:
        try:
            await email_delivery.send_email_login_code(
                settings=request.app.state.settings,
                recipient_email=email,
                code=code,
                ttl_seconds=ttl_seconds,
            )
        except email_delivery.EmailLoginDeliveryError:
            await _finalize_email_callback(
                db,
                state=state,
                result="failed",
                now=datetime.now(UTC),
                error_code="email_delivery_unavailable",
            )
            await db.commit()
            return HTMLResponse(
                render_email_code_page(
                    email=email,
                    state_nonce=state.state_nonce,
                    next_path=next_path,
                    error="email_delivery_unavailable",
                    flow=flow,
                    csrf_token=csrf_token,
                    product_analytics_provider=build_request_browser_provider_context(
                        request, "settings"
                    ),
                ),
                status_code=503,
            )
    await db.commit()
    return HTMLResponse(
        render_email_code_page(
            email=email,
            state_nonce=state.state_nonce,
            next_path=next_path,
            dev_code=dev_code,
            flow=flow,
            csrf_token=csrf_token,
            product_analytics_provider=build_request_browser_provider_context(request, "settings"),
        )
    )


@router.post(
    "/settings/account/email-link/start",
    include_in_schema=False,
    response_model=None,
    dependencies=[WebCSRFDependency],
)
async def start_settings_account_email_link(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse | RedirectResponse:
    return await _start_email_link(
        request,
        principal=principal,
        tenant_scope=tenant_scope,
        db=db,
        embedded=False,
    )


@router.post(
    "/desktop/settings/account/email-link/start",
    include_in_schema=False,
    response_model=None,
    dependencies=[WebCSRFDependency],
)
async def start_embedded_settings_account_email_link(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse | RedirectResponse:
    return await _start_email_link(
        request,
        principal=principal,
        tenant_scope=tenant_scope,
        db=db,
        embedded=True,
    )


async def _verify_email_link(
    request: Request,
    *,
    principal: AuthenticatedPrincipal,
    tenant_scope: TenantScope,
    db: AsyncSession | None,
    embedded: bool,
) -> HTMLResponse | RedirectResponse:
    prefix = "/desktop" if embedded else ""
    if db is None:
        return RedirectResponse(
            f"{prefix}/settings/account?provider_link=provider_link_unavailable",
            status_code=303,
        )
    if not principal.auth_via_session or principal.session_id is None:
        return RedirectResponse(
            f"{prefix}/settings/account?provider_link=reauth_required",
            status_code=303,
        )
    form = await request.form()
    csrf_token = _csrf_token_for_principal(request, principal, tenant_scope=tenant_scope)
    email = _normalize_email(str(form.get("email") or ""))
    code = str(form.get("code") or "")
    state = str(form.get("state") or "")
    flow = "desktop_link" if embedded else "link"
    if email is None or not state or not code:
        return HTMLResponse(
            render_email_code_page(
                email=email or "",
                state_nonce=state,
                next_path="/desktop/settings/account" if embedded else "/settings/account",
                error="email_code_invalid",
                flow=flow,
                csrf_token=csrf_token,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "settings"
                ),
            ),
            status_code=400,
        )
    try:
        result = await consume_email_link_code(
            db,
            request=request,
            principal=principal,
            workspace_id=tenant_scope.workspace_id,
            email=email,
            code=code,
            state_nonce=state,
            csrf_token=csrf_token,
        )
        prefix = "/desktop" if embedded else ""
        if isinstance(result, HTMLResponse):
            response = result
        elif (
            result.status in {"merge_preview_ready", "merge_blocked"}
            and result.intent_id is not None
        ):
            response = RedirectResponse(
                f"{prefix}/settings/account/merge/{result.intent_id}", status_code=303
            )
        else:
            response = RedirectResponse(
                f"{prefix}/settings/account?provider_link=confirmed", status_code=303
            )
        await db.commit()
        return response
    except Exception:
        await db.rollback()
        raise


@router.post(
    "/settings/account/email-link/verify",
    include_in_schema=False,
    response_model=None,
    dependencies=[WebCSRFDependency],
)
async def verify_settings_account_email_link(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse | RedirectResponse:
    return await _verify_email_link(
        request,
        principal=principal,
        tenant_scope=tenant_scope,
        db=db,
        embedded=False,
    )


@router.post(
    "/desktop/settings/account/email-link/verify",
    include_in_schema=False,
    response_model=None,
    dependencies=[WebCSRFDependency],
)
async def verify_embedded_settings_account_email_link(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse | RedirectResponse:
    return await _verify_email_link(
        request,
        principal=principal,
        tenant_scope=tenant_scope,
        db=db,
        embedded=True,
    )


@router.get("/settings/notifications", response_class=HTMLResponse, include_in_schema=False)
async def settings_notifications_page(
    request: Request,
    notification: str | None = NotificationResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="notifications",
        embedded=False,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        notification=notification,
    )


def _form_checkbox(form: object, name: str) -> bool:
    value = getattr(form, "get", lambda _name: None)(name)
    return value in {"on", "true", "1", True}


async def _save_notification_preferences(
    db: AsyncSession,
    *,
    user_id: UUID,
    form: object,
) -> None:
    preference = await db.get(BillingNotificationPreference, user_id, with_for_update=True)
    if preference is None:
        preference = BillingNotificationPreference(user_id=user_id)
        db.add(preference)
    preference.optional_email_enabled = _form_checkbox(form, "optional_email_enabled")
    preference.optional_in_app_enabled = _form_checkbox(form, "optional_in_app_enabled")
    await db.commit()


@router.post(
    "/settings/notifications",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def save_settings_notifications(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    form = await request.form()
    await _save_notification_preferences(db, user_id=principal.user_id, form=form)
    return RedirectResponse("/settings/notifications?notification=saved", status_code=303)


async def _save_account_profile(
    db: AsyncSession,
    *,
    principal: AuthenticatedPrincipal,
    tenant_scope: TenantScope,
    request: Request,
) -> None:
    form = await request.form()
    display_name = " ".join(str(form.get("display_name") or "").split())
    if len(display_name) > 240:
        raise ProblemDetail(
            status=422, code="profile_display_name_too_long", title="Имя слишком длинное"
        )
    user = await db.get(UserIdentity, principal.user_id, with_for_update=True)
    if user is None:
        raise ProblemDetail(status=404, code="account_not_found", title="Аккаунт не найден")
    user.display_name = display_name or None
    await write_auth_audit_event(
        db,
        workspace_id=tenant_scope.workspace_id,
        actor_user_id=principal.user_id,
        user_id=principal.user_id,
        event_type="account_profile_updated",
        metadata={"fields": ["display_name"]},
    )
    await db.commit()


def _account_preference_value(form: object, name: str, allowed: frozenset[str]) -> str:
    value = str(getattr(form, "get", lambda _name: "")(name) or "")
    if value not in allowed:
        raise ProblemDetail(
            status=422,
            code=f"invalid_account_{name}",
            title="Недопустимое значение настройки аккаунта",
        )
    return value


async def _save_account_preferences(
    db: AsyncSession,
    *,
    principal: AuthenticatedPrincipal,
    tenant_scope: TenantScope,
    request: Request,
) -> None:
    form = await request.form()
    user = await db.get(UserIdentity, principal.user_id, with_for_update=True)
    if user is None or user.organization_id != tenant_scope.organization_id:
        raise ProblemDetail(status=404, code="account_not_found", title="Аккаунт не найден")
    user.locale = _account_preference_value(form, "locale", frozenset({"ru-RU", "en-US"}))
    user.timezone = _account_preference_value(form, "timezone", frozenset({"Europe/Moscow", "UTC"}))
    user.theme = _account_preference_value(form, "theme", frozenset({"system", "dark", "light"}))
    await write_auth_audit_event(
        db,
        workspace_id=tenant_scope.workspace_id,
        actor_user_id=principal.user_id,
        user_id=principal.user_id,
        event_type="account_preferences_updated",
        metadata={"fields": ["locale", "timezone", "theme"]},
    )
    await db.commit()


async def _unlink_account_provider(
    db: AsyncSession,
    *,
    identity_id: UUID,
    principal: AuthenticatedPrincipal,
    tenant_scope: TenantScope,
    internal_workspace_id: UUID,
) -> bool:
    identity = await db.scalar(
        select(ExternalIdentity)
        .where(
            ExternalIdentity.id == identity_id,
            ExternalIdentity.user_id == principal.user_id,
            ExternalIdentity.is_active.is_(True),
        )
        .with_for_update()
    )
    if identity is None:
        raise ProblemDetail(
            status=404, code="login_method_not_found", title="Способ входа не найден"
        )
    identities = list(
        await db.scalars(
            select(ExternalIdentity)
            .where(
                ExternalIdentity.user_id == principal.user_id,
                ExternalIdentity.is_active.is_(True),
            )
            .with_for_update()
        )
    )
    verified_count = sum(
        1 for item in identities if item.is_verified and item.provider in RECOVERY_CAPABLE_PROVIDERS
    )
    guarded_count = verified_count + int(
        identity.is_verified and identity.provider not in RECOVERY_CAPABLE_PROVIDERS
    )
    if not recovery_safe_unlink_allowed(
        verified_identity_count=guarded_count,
        target_is_verified=identity.is_verified,
    ):
        raise ProblemDetail(
            status=422,
            code="recovery_path_required",
            title="Сначала подключите другой подтверждённый способ восстановления",
        )
    revoked_count = 0
    current_session_revoked = False
    workspaces = await list_active_workspaces(
        db,
        organization_id=principal.organization_id,
        current_workspace_id=tenant_scope.workspace_id,
        internal_workspace_id=internal_workspace_id,
        user_id=principal.user_id,
    )
    workspace_ids = {tenant_scope.workspace_id} | {workspace.id for workspace in workspaces}
    for workspace_id in sorted(workspace_ids, key=str):
        await apply_tenant_context(
            db,
            TenantDatabaseContext(
                organization_id=principal.organization_id,
                workspace_id=workspace_id,
                user_id=principal.user_id,
            ),
        )
        sessions = list(
            await db.scalars(
                select(AuthSession)
                .where(
                    AuthSession.workspace_id == workspace_id,
                    AuthSession.user_id == principal.user_id,
                    AuthSession.provider == identity.provider,
                    AuthSession.status == "active",
                )
                .order_by(AuthSession.id)
                .with_for_update()
            )
        )
        session_ids = [session.id for session in sessions]
        bindings = (
            list(
                await db.scalars(
                    select(AuthSessionDeviceBinding)
                    .where(AuthSessionDeviceBinding.auth_session_id.in_(session_ids))
                    .order_by(AuthSessionDeviceBinding.id)
                    .with_for_update()
                )
            )
            if session_ids
            else []
        )
        for session in sessions:
            session.status = "revoked"
        for binding in bindings:
            binding.device_state = "blocked"
            binding.revocation_reason = "provider_unlinked"
        if sessions:
            current_session_revoked |= principal.session_id in set(session_ids)
            revoked_count += len(sessions)
            await db.flush()

    await apply_tenant_scope(db, tenant_scope)
    identity.is_active = False
    identity.is_verified = False
    await write_auth_audit_event(
        db,
        workspace_id=tenant_scope.workspace_id,
        actor_user_id=principal.user_id,
        user_id=principal.user_id,
        provider=identity.provider,
        event_type="provider_unlinked",
        metadata={"revoked_session_count": revoked_count, "provider": identity.provider},
    )
    await db.commit()
    return current_session_revoked


async def _revoke_account_session(
    db: AsyncSession,
    *,
    session_id: UUID,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
) -> None:
    if session_id == principal.session_id or session_id == tenant_scope.auth_session_id:
        raise ProblemDetail(
            status=422,
            code="current_session_revoke_forbidden",
            title="Текущую сессию нельзя отозвать этой кнопкой",
        )
    session = await db.scalar(
        select(AuthSession)
        .where(
            AuthSession.id == session_id,
            AuthSession.workspace_id == tenant_scope.workspace_id,
            AuthSession.user_id == principal.user_id,
        )
        .with_for_update()
    )
    if session is None:
        raise ProblemDetail(status=404, code="auth_session_not_found", title="Сессия не найдена")
    session.status = "revoked"
    await write_auth_audit_event(
        db,
        workspace_id=tenant_scope.workspace_id,
        actor_user_id=principal.user_id,
        user_id=principal.user_id,
        event_type="auth_session_revoked",
        provider=session.provider,
        metadata={"session_id": str(session.id)},
    )
    await db.commit()


async def _revoke_other_account_sessions(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
) -> int:
    sessions = list(
        await db.scalars(
            select(AuthSession)
            .where(
                AuthSession.workspace_id == tenant_scope.workspace_id,
                AuthSession.user_id == principal.user_id,
                AuthSession.status == "active",
                AuthSession.id != tenant_scope.auth_session_id,
            )
            .with_for_update()
        )
    )
    for session in sessions:
        session.status = "revoked"
    if sessions:
        await write_auth_audit_event(
            db,
            workspace_id=tenant_scope.workspace_id,
            actor_user_id=principal.user_id,
            user_id=principal.user_id,
            event_type="auth_sessions_revoked",
            metadata={"scope": "other_sessions", "count": len(sessions)},
        )
    await db.commit()
    return len(sessions)


async def _revoke_other_account_devices(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
) -> tuple[int, int]:
    devices = list(
        await db.scalars(
            select(RegisteredDevice)
            .where(
                RegisteredDevice.workspace_id == tenant_scope.workspace_id,
                RegisteredDevice.user_id == principal.user_id,
                RegisteredDevice.status == "active",
                RegisteredDevice.id != tenant_scope.device_id,
            )
            .with_for_update()
        )
    )
    device_ids = [device.id for device in devices]
    sessions = []
    bindings = []
    if device_ids:
        sessions = list(
            await db.scalars(
                select(AuthSession)
                .where(
                    AuthSession.workspace_id == tenant_scope.workspace_id,
                    AuthSession.user_id == principal.user_id,
                    AuthSession.status == "active",
                    AuthSession.device_id.in_(device_ids),
                )
                .with_for_update()
            )
        )
        bindings = list(
            await db.scalars(
                select(AuthSessionDeviceBinding)
                .where(AuthSessionDeviceBinding.registered_device_id.in_(device_ids))
                .with_for_update()
            )
        )
    for device in devices:
        device.status = "revoked"
        device.registration_state = "revoked"
        device.revoked_by = principal.user_id
    for session in sessions:
        session.status = "revoked"
    for binding in bindings:
        binding.device_state = "blocked"
        binding.revocation_reason = "device_revoked"
    if devices or sessions:
        await write_auth_audit_event(
            db,
            workspace_id=tenant_scope.workspace_id,
            actor_user_id=principal.user_id,
            user_id=principal.user_id,
            event_type="auth_devices_revoked",
            metadata={
                "scope": "other_devices",
                "device_count": len(devices),
                "session_count": len(sessions),
            },
        )
    await db.commit()
    return len(devices), len(sessions)


@router.post(
    "/settings/account/profile",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def save_settings_account_profile(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    await _save_account_profile(db, principal=principal, tenant_scope=tenant_scope, request=request)
    return RedirectResponse("/settings/account?profile=saved", status_code=303)


@router.post(
    "/desktop/settings/account/profile",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def save_embedded_settings_account_profile(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    await _save_account_profile(db, principal=principal, tenant_scope=tenant_scope, request=request)
    return RedirectResponse("/desktop/settings/account?profile=saved", status_code=303)


@router.post(
    "/settings/account/preferences",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def save_settings_account_preferences(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    await _save_account_preferences(
        db, principal=principal, tenant_scope=tenant_scope, request=request
    )
    return RedirectResponse("/settings/account?preferences=saved", status_code=303)


@router.post(
    "/desktop/settings/account/preferences",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def save_embedded_settings_account_preferences(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    await _save_account_preferences(
        db, principal=principal, tenant_scope=tenant_scope, request=request
    )
    return RedirectResponse("/desktop/settings/account?preferences=saved", status_code=303)


async def _unlink_provider_action(
    request: Request,
    *,
    identity_id: UUID,
    principal: AuthenticatedPrincipal,
    tenant_scope: TenantScope,
    db: AsyncSession | None,
    embedded: bool,
) -> RedirectResponse:
    result_path = f"{'/desktop' if embedded else ''}/settings/account?provider_unlink="
    if not principal.auth_via_session or not is_web_cookie_session(request):
        return RedirectResponse(
            result_path + "reauth_required",
            status_code=303,
        )
    if db is None:
        return RedirectResponse(
            result_path + "unavailable",
            status_code=303,
        )
    try:
        current_session_revoked = await _unlink_account_provider(
            db,
            identity_id=identity_id,
            principal=principal,
            tenant_scope=tenant_scope,
            internal_workspace_id=request.app.state.settings.web_login_workspace_id,
        )
    except ProblemDetail as exc:
        await db.rollback()
        result = {
            "recovery_path_required": "recovery_path_required",
            "login_method_not_found": "not_found",
        }.get(exc.code)
        if result is None:
            raise
        return RedirectResponse(result_path + result, status_code=303)
    except SQLAlchemyError:
        await db.rollback()
        return RedirectResponse(result_path + "unavailable", status_code=303)
    if current_session_revoked:
        response = RedirectResponse(
            "/login?next=/desktop/settings/account&error=auth_session_invalid"
            if embedded
            else "/login?next=/settings/account&error=auth_session_invalid",
            status_code=303,
        )
        response.delete_cookie(
            key=auth_session_cookie_name(request),
            path="/",
            secure=auth_session_cookie_secure(request),
            httponly=True,
            samesite="lax",
        )
        return response
    return RedirectResponse(
        result_path + "success",
        status_code=303,
    )


@router.post(
    "/settings/account/providers/{identity_id}/unlink",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def unlink_settings_account_provider(
    request: Request,
    identity_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    return await _unlink_provider_action(
        request,
        identity_id=identity_id,
        principal=principal,
        tenant_scope=tenant_scope,
        db=db,
        embedded=False,
    )


@router.post(
    "/desktop/settings/account/providers/{identity_id}/unlink",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def unlink_embedded_settings_account_provider(
    request: Request,
    identity_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    return await _unlink_provider_action(
        request,
        identity_id=identity_id,
        principal=principal,
        tenant_scope=tenant_scope,
        db=db,
        embedded=True,
    )


@router.post(
    "/settings/account/sessions/revoke-others",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def revoke_other_settings_sessions(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if not principal.auth_via_session or not is_web_cookie_session(request):
        return RedirectResponse("/settings/account?session=reauth_required", status_code=303)
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    await _revoke_other_account_sessions(db, tenant_scope=tenant_scope, principal=principal)
    return RedirectResponse("/settings/account?session=others_revoked", status_code=303)


@router.post(
    "/desktop/settings/account/sessions/revoke-others",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def revoke_other_embedded_settings_sessions(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if not principal.auth_via_session or not is_web_cookie_session(request):
        return RedirectResponse(
            "/desktop/settings/account?session=reauth_required", status_code=303
        )
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    await _revoke_other_account_sessions(db, tenant_scope=tenant_scope, principal=principal)
    return RedirectResponse("/desktop/settings/account?session=others_revoked", status_code=303)


@router.post(
    "/settings/account/sessions/{session_id}/revoke",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def revoke_settings_session(
    request: Request,
    session_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if not principal.auth_via_session or not is_web_cookie_session(request):
        return RedirectResponse("/settings/account?session=reauth_required", status_code=303)
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    await _revoke_account_session(
        db, session_id=session_id, tenant_scope=tenant_scope, principal=principal
    )
    return RedirectResponse("/settings/account?session=revoked", status_code=303)


@router.post(
    "/desktop/settings/account/sessions/{session_id}/revoke",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def revoke_embedded_settings_session(
    request: Request,
    session_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if not principal.auth_via_session or not is_web_cookie_session(request):
        return RedirectResponse(
            "/desktop/settings/account?session=reauth_required", status_code=303
        )
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    await _revoke_account_session(
        db, session_id=session_id, tenant_scope=tenant_scope, principal=principal
    )
    return RedirectResponse("/desktop/settings/account?session=revoked", status_code=303)


@router.get("/account", response_class=HTMLResponse, include_in_schema=False)
async def account_center_page(
    request: Request,
    provider_link: str | None = ProviderLinkResultQuery,
    device_revoke: str | None = DeviceRevokeResultQuery,
    session: str | None = SessionResultQuery,
    account_close: str | None = AccountCloseResultQuery,
    profile: str | None = ProfileResultQuery,
    preferences: str | None = PreferencesResultQuery,
    provider_unlink: str | None = ProviderUnlinkResultQuery,
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
        session=session,
        account_close=account_close,
        profile=profile,
        preferences=preferences,
        provider_unlink=provider_unlink,
    )


@router.get("/account/settings", include_in_schema=False)
async def account_settings_alias() -> RedirectResponse:
    """Keep the old account settings URL on the canonical settings surface."""
    return RedirectResponse("/settings/account", status_code=307)


@router.get("/account/profile", response_class=HTMLResponse, include_in_schema=False)
@router.get("/account/security", response_class=HTMLResponse, include_in_schema=False)
async def account_profile_security_alias_page(
    request: Request,
    provider_link: str | None = ProviderLinkResultQuery,
    device_revoke: str | None = DeviceRevokeResultQuery,
    session: str | None = SessionResultQuery,
    account_close: str | None = AccountCloseResultQuery,
    profile: str | None = ProfileResultQuery,
    preferences: str | None = PreferencesResultQuery,
    provider_unlink: str | None = ProviderUnlinkResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    """Stable account IA aliases; both views share the verified account surface."""
    return await _render_settings(
        request,
        category="account",
        embedded=False,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        provider_link=provider_link,
        device_revoke=device_revoke,
        session=session,
        account_close=account_close,
        profile=profile,
        preferences=preferences,
        provider_unlink=provider_unlink,
    )


@router.get("/account/notifications", response_class=HTMLResponse, include_in_schema=False)
async def account_notifications_alias_page(
    request: Request,
    notification: str | None = NotificationResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="notifications",
        embedded=False,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        notification=notification,
    )


async def _account_close_action(
    request: Request,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    db: AsyncSession | None,
    cancel: bool,
) -> RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    if not principal.auth_via_session or not is_web_cookie_session(request):
        return RedirectResponse(
            (
                "/desktop/settings/account"
                if request.url.path.startswith("/desktop/")
                else "/settings/account"
            )
            + "?account_close=reauth_required",
            status_code=303,
        )
    if not cancel:
        form = await request.form()
        if str(form.get("confirm_close") or "") != "Закрыть аккаунт":
            raise ProblemDetail(
                status=422,
                code="account_close_confirmation_required",
                title="Введите подтверждение закрытия аккаунта",
            )
    try:
        if cancel:
            await cancel_account_close(
                db,
                workspace_id=tenant_scope.workspace_id,
                user_id=principal.user_id,
                now=datetime.now(UTC),
            )
            result = "canceled"
        else:
            await schedule_account_close(
                db,
                workspace_id=tenant_scope.workspace_id,
                user_id=principal.user_id,
                now=datetime.now(UTC),
            )
            result = "scheduled"
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    prefix = "/desktop" if request.url.path.startswith("/desktop/") else ""
    return RedirectResponse(f"{prefix}/settings/account?account_close={result}", status_code=303)


@router.post(
    "/settings/account/close",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def schedule_account_close_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    return await _account_close_action(
        request,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        cancel=False,
    )


@router.post(
    "/desktop/settings/account/close",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def schedule_embedded_account_close_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    return await _account_close_action(
        request,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        cancel=False,
    )


@router.post(
    "/settings/account/close/cancel",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def cancel_account_close_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    return await _account_close_action(
        request,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        cancel=True,
    )


@router.post(
    "/desktop/settings/account/close/cancel",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def cancel_embedded_account_close_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    return await _account_close_action(
        request,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        cancel=True,
    )


@router.post(
    "/settings/account/devices/revoke-others",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def revoke_other_settings_devices(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if not principal.auth_via_session or not is_web_cookie_session(request):
        return RedirectResponse("/settings/account?device_revoke=reauth_required", status_code=303)
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    await _revoke_other_account_devices(db, tenant_scope=tenant_scope, principal=principal)
    return RedirectResponse("/settings/account?device_revoke=others_revoked", status_code=303)


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
    if not principal.auth_via_session or not is_web_cookie_session(request):
        return RedirectResponse("/settings/account?device_revoke=reauth_required", status_code=303)
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
    session: str | None = SessionResultQuery,
    account_close: str | None = AccountCloseResultQuery,
    preferences: str | None = PreferencesResultQuery,
    provider_unlink: str | None = ProviderUnlinkResultQuery,
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
        session=session,
        account_close=account_close,
        preferences=preferences,
        provider_unlink=provider_unlink,
    )


@router.get("/desktop/settings/notifications", response_class=HTMLResponse, include_in_schema=False)
async def embedded_settings_notifications_page(
    request: Request,
    notification: str | None = NotificationResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="notifications",
        embedded=True,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        notification=notification,
    )


@router.post(
    "/desktop/settings/notifications",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def save_embedded_settings_notifications(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    form = await request.form()
    await _save_notification_preferences(db, user_id=principal.user_id, form=form)
    return RedirectResponse("/desktop/settings/notifications?notification=saved", status_code=303)


@router.get("/desktop/account", response_class=HTMLResponse, include_in_schema=False)
async def embedded_account_center_page(
    request: Request,
    provider_link: str | None = ProviderLinkResultQuery,
    device_revoke: str | None = DeviceRevokeResultQuery,
    session: str | None = SessionResultQuery,
    profile: str | None = ProfileResultQuery,
    preferences: str | None = PreferencesResultQuery,
    provider_unlink: str | None = ProviderUnlinkResultQuery,
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
        session=session,
        profile=profile,
        preferences=preferences,
        provider_unlink=provider_unlink,
    )


@router.get("/desktop/account/profile", response_class=HTMLResponse, include_in_schema=False)
@router.get("/desktop/account/security", response_class=HTMLResponse, include_in_schema=False)
async def embedded_account_profile_security_alias_page(
    request: Request,
    provider_link: str | None = ProviderLinkResultQuery,
    device_revoke: str | None = DeviceRevokeResultQuery,
    session: str | None = SessionResultQuery,
    account_close: str | None = AccountCloseResultQuery,
    profile: str | None = ProfileResultQuery,
    preferences: str | None = PreferencesResultQuery,
    provider_unlink: str | None = ProviderUnlinkResultQuery,
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
        session=session,
        account_close=account_close,
        profile=profile,
        preferences=preferences,
        provider_unlink=provider_unlink,
    )


@router.get("/desktop/account/notifications", response_class=HTMLResponse, include_in_schema=False)
async def embedded_account_notifications_alias_page(
    request: Request,
    notification: str | None = NotificationResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_settings(
        request,
        category="notifications",
        embedded=True,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        notification=notification,
    )


@router.post(
    "/desktop/settings/account/devices/revoke-others",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def revoke_other_embedded_settings_devices(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if not principal.auth_via_session or not is_web_cookie_session(request):
        return RedirectResponse(
            "/desktop/settings/account?device_revoke=reauth_required", status_code=303
        )
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    await _revoke_other_account_devices(db, tenant_scope=tenant_scope, principal=principal)
    return RedirectResponse(
        "/desktop/settings/account?device_revoke=others_revoked", status_code=303
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
    if not principal.auth_via_session or not is_web_cookie_session(request):
        return RedirectResponse(
            "/desktop/settings/account?device_revoke=reauth_required", status_code=303
        )
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
