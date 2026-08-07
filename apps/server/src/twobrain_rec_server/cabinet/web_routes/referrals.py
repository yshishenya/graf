from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.billing.referrals import create_referral_token, referral_token_hash
from twobrain_rec_server.cabinet.rendering_shared import _page_shell
from twobrain_rec_server.cabinet.templates import cabinet_html_response
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
)
from twobrain_rec_server.db.models import ReferralAttribution
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])


@router.get("/referrals", response_class=HTMLResponse, include_in_schema=False)
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
    token = create_referral_token(user_id=principal.user_id, secret=secret) if secret else ""
    token_hash = referral_token_hash(token) if token else None
    if db is not None and token_hash is not None:
        attribution = await db.scalar(select(ReferralAttribution).where(ReferralAttribution.token_hash == token_hash))
        if attribution is None:
            db.add(
                ReferralAttribution(
                    workspace_id=tenant_scope.workspace_id,
                    inviter_user_id=principal.user_id,
                    token_hash=token_hash,
                    campaign_version="referral-v1",
                    first_touched_at=datetime.now(UTC),
                    state="issued",
                )
            )
            await db.commit()
    link = f"{str(request.base_url).rstrip('/')}/referral/{token}" if token else ""
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
    )
    return cabinet_html_response(content)


@router.get("/referral/{token}", include_in_schema=False)
async def referral_landing(token: str) -> RedirectResponse:
    if not token.startswith("r1_") or len(token) != 67:
        return RedirectResponse("/sign-up?error=referral_invalid", status_code=303)
    response = RedirectResponse("/sign-up?next=/meetings", status_code=303)
    response.set_cookie("graf_referral_token", token, max_age=60 * 60 * 24 * 30, httponly=True, samesite="lax", secure=True)
    return response
