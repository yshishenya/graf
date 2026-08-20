from __future__ import annotations

from dataclasses import dataclass
from email.utils import parseaddr
from hashlib import sha256
from urllib.parse import urlencode
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


@dataclass(frozen=True, slots=True)
class AccountMergeBlocker:
    title: str
    detail: str
    action_label: str
    action_href: str
    action_next: str | None = None
    support_reference: str | None = None


def _embedded(request: Request) -> bool:
    return request.url.path.startswith("/desktop/")


def _error_copy(code: str) -> str:
    return {
        "merge_preview_stale": "Состояние профилей изменилось. Данные не изменены; подключите email заново.",
        "merge_intent_expired": "Время подтверждения истекло. Данные не изменены; подключите email заново.",
        "proof_required": "Нужно повторно подтвердить оба способа входа.",
        "reauth_required": "Для этого действия войдите через подтверждённую веб-сессию и повторите попытку. Данные не изменены.",
        "workspace_role_conflict": "Роли профилей нельзя безопасно совместить автоматически.",
        "workspace_ownership_conflict": "Для пространств нельзя безопасно выбрать основного владельца автоматически.",
        "billing_conflict": "На втором профиле есть активная оплата.",
        "calendar_ownership_conflict": "Ко второму профилю подключён календарь.",
        "deletion_state_conflict": "Сейчас идёт закрытие профиля или удаление встречи.",
        "meeting_owner_conflict": "Найдена конфликтующая локальная запись встречи.",
        "referral_conflict": "На втором профиле есть активное приглашение или ожидающее начисление.",
        "fair_use_conflict": "На втором профиле действует ограничение добросовестного использования.",
        "settings_conflict": "В профилях есть одинаковые пользовательские форматы итогов.",
        "upload_in_progress": "Сейчас загружается запись.",
        "export_in_progress": "Сейчас готовится экспорт.",
        "merge_blocked": "Email не подключён. Данные не изменены.",
    }.get(code, "Email не подключён. Данные не изменены.")


def _support_reference(intent_id: UUID) -> str:
    digest = sha256(f"account-linking:{intent_id}".encode()).hexdigest()[:12].upper()
    return f"AM-{digest}"


def _configured_support_email(value: str | None) -> str | None:
    normalized = (value or "").strip()
    _display_name, parsed = parseaddr(normalized)
    if (
        not normalized
        or parsed != normalized
        or parsed.count("@") != 1
        or any(char in normalized for char in "\r\n")
    ):
        return None
    return normalized


def account_merge_blockers(
    blocker_codes: tuple[str, ...],
    *,
    intent_id: UUID,
    embedded: bool,
    support_email: str | None,
) -> tuple[AccountMergeBlocker, ...]:
    account_href = "/desktop/settings/account" if embedded else "/settings/account"
    summaries_href = "/desktop/settings/summaries" if embedded else "/settings/summaries"
    meetings_href = "/desktop/meetings" if embedded else "/meetings"
    fair_use_href = "/desktop/account/fair-use" if embedded else "/account/fair-use"
    calendar_href = (
        "/desktop/settings/integrations/calendar" if embedded else "/settings/integrations/calendar"
    )
    logout_href = "/desktop/meetings" if embedded else "/logout"
    self_service = {
        "billing_conflict": (
            "Данные не изменены. Войдите во второй профиль, завершите активные операции в оплате, затем вернитесь в основной профиль и подключите email заново.",
            "/billing",
        ),
        "calendar_ownership_conflict": (
            "Данные не изменены. Войдите во второй профиль, отключите или повторно подтвердите календарь, затем вернитесь в основной профиль и подключите email заново.",
            calendar_href,
        ),
        "deletion_state_conflict": (
            "Данные не изменены. Войдите во второй профиль, дождитесь завершения или отмените закрытие профиля, затем вернитесь в основной профиль и подключите email заново.",
            account_href,
        ),
        "settings_conflict": (
            "Данные не изменены. Войдите во второй профиль, переименуйте или удалите один из совпадающих форматов, затем вернитесь в основной профиль и подключите email заново.",
            summaries_href,
        ),
        "upload_in_progress": (
            "Данные не изменены. Войдите во второй профиль, дождитесь завершения загрузки, затем вернитесь в основной профиль и подключите email заново.",
            meetings_href,
        ),
        "export_in_progress": (
            "Данные не изменены. Войдите во второй профиль, дождитесь завершения экспорта, затем вернитесь в основной профиль и подключите email заново.",
            meetings_href,
        ),
        "fair_use_conflict": (
            "Данные не изменены. Войдите во второй профиль, откройте проверку использования и при необходимости подайте апелляцию. После решения вернитесь в основной профиль и подключите email заново.",
            fair_use_href,
        ),
    }
    support_reasons = {
        "workspace_role_conflict",
        "workspace_ownership_conflict",
        "meeting_owner_conflict",
        "referral_conflict",
    }
    configured_support = _configured_support_email(support_email)
    result: list[AccountMergeBlocker] = []
    for code in blocker_codes:
        action = self_service.get(code)
        if action is not None:
            detail, target_href = action
            login_href = f"/login?{urlencode({'next': target_href, 'error': 'account_linking_other_profile_required'})}"
            result.append(
                AccountMergeBlocker(
                    title=_error_copy(code).removesuffix("."),
                    detail=detail,
                    action_label="Войти во второй профиль",
                    action_href=logout_href,
                    action_next=login_href,
                )
            )
            continue
        reason = (
            _error_copy(code)
            if code in support_reasons
            else "Текущее состояние профилей не позволяет безопасно подключить email автоматически."
        )
        if configured_support is not None:
            reference = _support_reference(intent_id)
            query = urlencode({"subject": f"GRAF: подключение email, номер {reference}"})
            result.append(
                AccountMergeBlocker(
                    title=reason.removesuffix("."),
                    detail=(
                        "Данные не изменены. Передайте поддержке только номер ниже — "
                        "email, внутренние идентификаторы и содержимое встреч не нужны."
                    ),
                    action_label="Получить помощь",
                    action_href=f"mailto:{configured_support}?{query}",
                    support_reference=reference,
                )
            )
            continue
        result.append(
            AccountMergeBlocker(
                title=reason.removesuffix("."),
                detail=(
                    "Данные не изменены. Поддержка на этом сервере не настроена; "
                    "вернитесь в настройки и не повторяйте действие, пока причина не устранена."
                ),
                action_label="Вернуться в настройки",
                action_href=account_href,
            )
        )
    return tuple(result)


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
            AccountMergeIntent.initiating_auth_session_id == principal.session_id,
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
    error_code = request.query_params.get("error", "")
    error_message = _error_copy(error_code) if error_code else None
    try:
        preview = await preview_merge_intent(db, intent_id=intent.id)
    except AccountMergeError as exc:
        if exc.durable:
            await db.commit()
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
            requires_reauth=error_code == "reauth_required",
            blockers=(
                account_merge_blockers(
                    preview.blocker_codes,
                    intent_id=intent.id,
                    embedded=_embedded(request),
                    support_email=request.app.state.settings.billing_support_email,
                )
                if preview is not None
                else ()
            ),
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
    owned_intent_id = intent.id
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
        if exc.durable:
            await db.commit()
        else:
            await db.rollback()
        return RedirectResponse(
            f"{'/desktop' if embedded else ''}/settings/account/merge/{owned_intent_id}?error={exc.code}",
            status_code=303,
        )
    await db.commit()
    response = RedirectResponse(
        "/login?next=/desktop/settings/account&error=email_connected_relogin_required"
        if embedded
        else "/login?next=/settings/account&error=email_connected_relogin_required",
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
