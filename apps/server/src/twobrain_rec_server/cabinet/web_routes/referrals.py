from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.rate_limit import enforce_auth_rate_limits
from twobrain_rec_server.billing.referrals import (
    create_referral_token,
    referral_token_hash,
    validate_referral_token,
)
from twobrain_rec_server.cabinet.rendering_shared import _page_shell
from twobrain_rec_server.cabinet.templates import cabinet_html_response
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
)
from twobrain_rec_server.db.models import ReferralLink, Workspace
from twobrain_rec_server.db.tenant_context import (
    WorkspaceAuthContext,
    apply_tenant_context,
    apply_tenant_scope,
)
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])


@router.get("/referrals", response_class=HTMLResponse, include_in_schema=False)
@router.get("/account/referrals", response_class=HTMLResponse, include_in_schema=False)
async def referrals_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    secret_path = getattr(request.app.state.settings, "billing_referral_secret_file", None)
    try:
        secret = secret_path.read_text(encoding="utf-8").strip() if secret_path is not None and secret_path.is_file() else ""
    except OSError:
        secret = ""
    workspace = await db.scalar(select(Workspace).where(Workspace.id == tenant_scope.workspace_id)) if db is not None else None
    can_invite = workspace is not None and workspace.kind == "personal" and workspace.owner_user_id == principal.user_id
    token = (
        create_referral_token(user_id=principal.user_id, workspace_id=tenant_scope.workspace_id, secret=secret)
        if secret and can_invite
        else ""
    )
    token_hash = referral_token_hash(token) if token else None
    link_record = None
    if db is not None and token_hash is not None:
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(workspace_id=tenant_scope.workspace_id, user_id=principal.user_id),
        )
        try:
            link_record = await db.scalar(
                select(ReferralLink).where(
                    ReferralLink.token_hash == token_hash,
                    ReferralLink.workspace_id == tenant_scope.workspace_id,
                    ReferralLink.inviter_user_id == principal.user_id,
                    ReferralLink.state == "active",
                )
            )
        finally:
            await apply_tenant_scope(db, tenant_scope)
    public_base_url = getattr(request.app.state.settings, "public_base_url", None)
    link = (
        f"{str(public_base_url).rstrip('/')}/r/{token}"
        if token and public_base_url is not None and getattr(public_base_url, "scheme", None) == "https"
        else ""
    )
    content = _page_shell(
        "Пригласить друзей",
        embedded=False,
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request,
            "billing_referrals",
            principal=principal,
            tenant_scope=tenant_scope,
        ),
        content_template="cabinet/pages/referrals_content.html",
        referral_link=link,
        referral_token_hash=token_hash,
        referral_issued=link_record is not None,
        referral_issue_result=request.query_params.get("result"),
    )
    return cabinet_html_response(content)


@router.post("/referrals/issue", response_class=HTMLResponse, include_in_schema=False)
async def issue_referral_link(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    """Persist referral attribution only after an explicit user action."""
    if db is None:
        return RedirectResponse("/referrals?result=unavailable", status_code=303)
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        return RedirectResponse("/referrals?result=unavailable", status_code=303)
    retry_after = await enforce_auth_rate_limits(
        None,
        workspace_id=tenant_scope.workspace_id,
        scopes=(("billing_referral_issue", f"{principal.user_id}:{tenant_scope.workspace_id}"),),
        sessionmaker=sessionmaker,
        scope_secret=request.app.state.settings.share_identity_hash_secret,
    )
    if retry_after is not None:
        response = HTMLResponse("Слишком много попыток. Попробуйте позже.", status_code=429)
        response.headers["Retry-After"] = str(retry_after)
        response.headers["Cache-Control"] = "private, no-store"
        return response
    secret_path = getattr(request.app.state.settings, "billing_referral_secret_file", None)
    try:
        secret = secret_path.read_text(encoding="utf-8").strip() if secret_path is not None and secret_path.is_file() else ""
    except OSError:
        secret = ""
    workspace = await db.scalar(select(Workspace).where(Workspace.id == tenant_scope.workspace_id))
    if not secret or workspace is None or workspace.kind != "personal" or workspace.owner_user_id != principal.user_id:
        return RedirectResponse("/referrals?result=unavailable", status_code=303)
    token_hash = referral_token_hash(
        create_referral_token(user_id=principal.user_id, workspace_id=tenant_scope.workspace_id, secret=secret)
    )
    await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=tenant_scope.workspace_id, user_id=principal.user_id))
    try:
        link_record = await db.scalar(
            select(ReferralLink)
            .where(
                ReferralLink.token_hash == token_hash,
                ReferralLink.workspace_id == tenant_scope.workspace_id,
                ReferralLink.inviter_user_id == principal.user_id,
            )
            .with_for_update()
        )
        if link_record is None:
            db.add(
                ReferralLink(
                    id=uuid4(),
                    workspace_id=tenant_scope.workspace_id,
                    inviter_user_id=principal.user_id,
                    token_hash=token_hash,
                    campaign_version="referral-v1",
                    state="active",
                )
            )
            await db.commit()
    finally:
        await apply_tenant_scope(db, tenant_scope)
    return RedirectResponse("/referrals?result=issued", status_code=303)


@router.get("/referral/{token}", include_in_schema=False)
async def referral_landing(request: Request, token: str) -> RedirectResponse:
    try:
        validate_referral_token(token)
    except ValueError:
        return RedirectResponse("/sign-up?error=referral_invalid", status_code=303)
    response = RedirectResponse("/sign-up?next=/meetings", status_code=303)
    if not request.cookies.get("graf_referral_token"):
        response.set_cookie(
            "graf_referral_token",
            token,
            max_age=60 * 60 * 24 * 30,
            httponly=True,
            samesite="lax",
            secure=True,
        )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@router.get("/r/{token}", include_in_schema=False)
async def referral_landing_short(request: Request, token: str) -> RedirectResponse:
    """Canonical contract alias kept alongside the legacy readable route."""
    return await referral_landing(request, token)
