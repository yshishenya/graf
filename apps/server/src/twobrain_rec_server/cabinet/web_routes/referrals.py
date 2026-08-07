from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.billing.referrals import create_referral_token, referral_token_hash
from twobrain_rec_server.cabinet.rendering_shared import _page_shell
from twobrain_rec_server.cabinet.templates import cabinet_html_response
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
)
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])


@router.get("/referrals", response_class=HTMLResponse, include_in_schema=False)
async def referrals_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
) -> HTMLResponse:
    secret = str(getattr(request.app.state.settings, "billing_referral_secret", None) or request.app.state.settings.web_csrf_secret)
    token = create_referral_token(user_id=principal.user_id, secret=secret)
    link = f"{str(request.base_url).rstrip('/')}/referral/{token}"
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
        referral_token_hash=referral_token_hash(token),
    )
    return cabinet_html_response(content)


@router.get("/referral/{token}", include_in_schema=False)
async def referral_landing(token: str) -> RedirectResponse:
    if not token.startswith("r1_") or len(token) != 67:
        return RedirectResponse("/sign-up?error=referral_invalid", status_code=303)
    response = RedirectResponse("/sign-up?next=/meetings", status_code=303)
    response.set_cookie("graf_referral_token", token, max_age=60 * 60 * 24 * 30, httponly=True, samesite="lax", secure=True)
    return response
