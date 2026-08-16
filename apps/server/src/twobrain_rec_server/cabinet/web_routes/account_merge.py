from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.account_merge import (
    AccountMergeError,
    cancel_merge_intent,
    confirm_merge_intent,
    preview_merge_intent,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.dependencies import is_web_cookie_session
from twobrain_rec_server.cabinet.rendering import render_account_merge_page
from twobrain_rec_server.cabinet.templates import cabinet_html_response
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
)
from twobrain_rec_server.db.models import AccountMergeIntent
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])


def _embedded(request: Request) -> bool:
    return request.url.path.startswith("/desktop/")


def _error_copy(code: str) -> str:
    return {
        "merge_preview_stale": "Предпросмотр устарел. Данные не изменены; начните объединение заново.",
        "merge_intent_expired": "Срок подтверждения истёк. Данные не изменены; начните заново.",
        "proof_required": "Нужно повторно подтвердить оба способа входа.",
        "reauth_required": "Для этого действия войдите через подтверждённую веб-сессию и повторите попытку. Данные не изменены.",
        "workspace_role_conflict": "У аккаунтов несовместимые роли в одном рабочем пространстве.",
        "workspace_ownership_conflict": "Нельзя безопасно определить владельца рабочих пространств.",
        "billing_conflict": "Сначала нужно отдельно решить активный платёжный статус.",
        "calendar_ownership_conflict": "Сначала отключите или повторно подтвердите календарь.",
        "deletion_state_conflict": "На аккаунте или встрече уже идёт закрытие/удаление.",
        "meeting_owner_conflict": "Нашлись одинаковые локальные записи. Объединение остановлено, чтобы не потерять данные.",
    }.get(code, "Объединение не выполнено. Данные не изменены.")


async def _owned_intent(
    db: AsyncSession,
    *,
    intent_id: UUID,
    principal: AuthenticatedPrincipal,
    tenant_scope: TenantScope,
) -> AccountMergeIntent:
    intent = await db.scalar(
        select(AccountMergeIntent).where(
            AccountMergeIntent.id == intent_id,
            AccountMergeIntent.workspace_id == tenant_scope.workspace_id,
            AccountMergeIntent.survivor_user_id == principal.user_id,
        )
    )
    if intent is None:
        raise ProblemDetail(
            status=404, code="merge_intent_not_found", title="Предпросмотр не найден"
        )
    return intent


@router.get(
    "/settings/account/merge/{intent_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
@router.get(
    "/desktop/settings/account/merge/{intent_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def account_merge_page(
    request: Request,
    intent_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    intent = await _owned_intent(
        db, intent_id=intent_id, principal=principal, tenant_scope=tenant_scope
    )
    preview = None
    error_message = _error_copy(request.query_params.get("error", "")) if request.query_params.get("error") else None
    try:
        preview = await preview_merge_intent(db, intent_id=intent.id)
    except AccountMergeError as exc:
        error_message = _error_copy(exc.code)
    return cabinet_html_response(
        render_account_merge_page(
            preview,
            intent_id=intent.id,
            embedded=_embedded(request),
            csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "settings",
                principal=principal,
                tenant_scope=tenant_scope,
                device_class="desktop_webview" if _embedded(request) else "browser",
            ),
            error_message=error_message,
        )
    )


async def _confirm(
    request: Request,
    *,
    intent_id: UUID,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    db: AsyncSession | None,
    embedded: bool,
) -> RedirectResponse:
    if not principal.auth_via_session or not is_web_cookie_session(request):
        return RedirectResponse(
            f"{'/desktop' if embedded else ''}/settings/account/merge/{intent_id}?error=reauth_required",
            status_code=303,
        )
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    intent = await _owned_intent(
        db, intent_id=intent_id, principal=principal, tenant_scope=tenant_scope
    )
    form = await request.form()
    fingerprint = str(form.get("preview_fingerprint") or "")
    idempotency_key = str(form.get("idempotency_key") or "")
    if not fingerprint or not idempotency_key:
        raise ProblemDetail(
            status=422, code="merge_confirmation_invalid", title="Не хватает подтверждения"
        )
    try:
        await confirm_merge_intent(
            db,
            intent_id=intent.id,
            preview_fingerprint=fingerprint,
            idempotency_key=idempotency_key,
        )
    except AccountMergeError as exc:
        await db.rollback()
        return RedirectResponse(
            f"{'/desktop' if embedded else ''}/settings/account/merge/{intent.id}?error={exc.code}",
            status_code=303,
        )
    await db.commit()
    response = RedirectResponse(
        "/login?next=/desktop/settings/account&error=auth_session_invalid"
        if embedded
        else "/login?next=/settings/account&error=auth_session_invalid",
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


@router.post(
    "/settings/account/merge/{intent_id}/confirm",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/settings/account/merge/{intent_id}/confirm",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def confirm_account_merge(
    request: Request,
    intent_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    return await _confirm(
        request,
        intent_id=intent_id,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        embedded=_embedded(request),
    )


@router.post(
    "/settings/account/merge/{intent_id}/cancel",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/settings/account/merge/{intent_id}/cancel",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def cancel_account_merge(
    request: Request,
    intent_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if not principal.auth_via_session or not is_web_cookie_session(request):
        return RedirectResponse(
            f"{'/desktop' if _embedded(request) else ''}/settings/account?provider_link=reauth_required",
            status_code=303,
        )
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    try:
        intent = await _owned_intent(
            db, intent_id=intent_id, principal=principal, tenant_scope=tenant_scope
        )
        await cancel_merge_intent(db, intent_id=intent.id, actor_user_id=principal.user_id)
        await db.commit()
    except AccountMergeError as exc:
        await db.rollback()
        return RedirectResponse(
            f"{'/desktop' if _embedded(request) else ''}/settings/account?provider_link={exc.code}",
            status_code=303,
        )
    return RedirectResponse(
        f"{'/desktop' if _embedded(request) else ''}/settings/account?provider_link=merge_cancelled",
        status_code=303,
    )
