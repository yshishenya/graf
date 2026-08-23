from __future__ import annotations

from dataclasses import dataclass
from email.utils import parseaddr
from hashlib import sha256
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
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
from twobrain_rec_server.cabinet.rendering import (
    account_merge_provider_label,
    render_account_merge_page,
)
from twobrain_rec_server.cabinet.templates import cabinet_html_response
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
)
from twobrain_rec_server.db.models import AccountMergeIntent, ExternalIdentity
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])
ACCOUNT_MERGE_RESTART_ERRORS = frozenset(
    {
        "proof_required",
        "merge_preview_stale",
        "merge_intent_expired",
        "merge_restart_required",
    }
)


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


def _account_settings_path(*, embedded: bool, result: str) -> str:
    safe_result = {
        "confirmed",
        "merge_blocked",
        "merge_cancelled",
        "provider_link_denied",
        "provider_link_expired",
        "provider_link_invalid",
        "provider_link_reused",
        "provider_link_unavailable",
        "reauth_required",
    }
    outcome = result if result in safe_result else "provider_link_unavailable"
    return f"{'/desktop' if embedded else ''}/settings/account?provider_link={outcome}"


def _account_settings_redirect(*, embedded: bool, result: str) -> RedirectResponse:
    return RedirectResponse(
        _account_settings_path(embedded=embedded, result=result),
        status_code=303,
    )


def _merge_recovery_result(code: str) -> str:
    if code in {"merge_intent_expired", "expired"}:
        return "provider_link_expired"
    if code in {"merge_already_completed", "merge_idempotency_conflict"}:
        return "provider_link_reused"
    if code == "reauth_required":
        return "reauth_required"
    if code in {
        "merge_confirmation_invalid",
        "merge_intent_not_found",
        "merge_journal_missing",
        "proof_required",
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
    return "provider_link_unavailable"


def _error_copy(code: str, *, provider_label: str = "способ входа") -> str:
    sentence_label = {
        "email": "Email",
        "способ входа": "Способ входа",
    }.get(provider_label, provider_label)
    return {
        "merge_preview_stale": f"Состояние профилей изменилось. Данные не изменены; подключите {provider_label} заново.",
        "merge_intent_expired": f"Время подтверждения истекло. Данные не изменены; подключите {provider_label} заново.",
        "merge_restart_required": f"Причина остановки устранена. Данные не изменены; подключите {provider_label} заново.",
        "proof_required": f"Подтверждение больше не действует. Данные не изменены; подключите {provider_label} заново.",
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
        "merge_blocked": f"{sentence_label} не подключён. Данные не изменены.",
    }.get(code, f"{sentence_label} не подключён. Данные не изменены.")


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
    provider_label: str = "способ входа",
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
            f"Данные не изменены. Войдите во второй профиль, завершите активные операции в оплате, затем вернитесь в основной профиль и подключите {provider_label} заново.",
            "/billing",
        ),
        "calendar_ownership_conflict": (
            f"Данные не изменены. Войдите во второй профиль, отключите или повторно подтвердите календарь, затем вернитесь в основной профиль и подключите {provider_label} заново.",
            calendar_href,
        ),
        "deletion_state_conflict": (
            f"Данные не изменены. Войдите во второй профиль, дождитесь завершения или отмените закрытие профиля, затем вернитесь в основной профиль и подключите {provider_label} заново.",
            account_href,
        ),
        "settings_conflict": (
            f"Данные не изменены. Войдите во второй профиль, переименуйте или удалите один из совпадающих форматов, затем вернитесь в основной профиль и подключите {provider_label} заново.",
            summaries_href,
        ),
        "upload_in_progress": (
            f"Данные не изменены. Войдите во второй профиль, дождитесь завершения загрузки, затем вернитесь в основной профиль и подключите {provider_label} заново.",
            meetings_href,
        ),
        "export_in_progress": (
            f"Данные не изменены. Войдите во второй профиль, дождитесь завершения экспорта, затем вернитесь в основной профиль и подключите {provider_label} заново.",
            meetings_href,
        ),
        "fair_use_conflict": (
            f"Данные не изменены. Войдите во второй профиль, откройте проверку использования и при необходимости подайте апелляцию. После решения вернитесь в основной профиль и подключите {provider_label} заново.",
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
            _error_copy(code, provider_label=provider_label)
            if code in support_reasons
            else f"Текущее состояние профилей не позволяет безопасно подключить {provider_label} автоматически."
        )
        if configured_support is not None:
            reference = _support_reference(intent_id)
            query = urlencode({"subject": f"GRAF: подключение способа входа, номер {reference}"})
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
    if principal.session_id is None:
        raise ProblemDetail(
            status=404, code="merge_intent_not_found", title="Предпросмотр не найден"
        )
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


async def _intent_provider_id(
    db: AsyncSession,
    intent: AccountMergeIntent,
) -> str | None:
    if intent.provider_link_state_id is None:
        return "email_link"
    if intent.source_external_identity_id is None:
        return None
    identity = await db.get(ExternalIdentity, intent.source_external_identity_id)
    if identity is None or identity.user_id != intent.source_user_id:
        return None
    return identity.provider


def _relogin_result(provider_id: str | None) -> str:
    return {
        "email": "email_connected_relogin_required",
        "email_link": "email_connected_relogin_required",
        "email_magic_link": "email_connected_relogin_required",
        "yandex": "yandex_connected_relogin_required",
        "vk": "vk_connected_relogin_required",
    }.get(provider_id, "sign_in_method_connected_relogin_required")


@router.get(
    "/settings/account/merge/{intent_id}",
    response_class=HTMLResponse,
    response_model=None,
    include_in_schema=False,
)
@router.get(
    "/desktop/settings/account/merge/{intent_id}",
    response_class=HTMLResponse,
    response_model=None,
    include_in_schema=False,
)
async def account_merge_page(
    request: Request,
    intent_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    embedded = _embedded(request)
    if db is None:
        return _account_settings_redirect(embedded=embedded, result="provider_link_unavailable")
    try:
        intent = await _owned_intent(
            db, intent_id=intent_id, principal=principal, tenant_scope=tenant_scope
        )
        provider_id = await _intent_provider_id(db, intent)
    except ProblemDetail as exc:
        await db.rollback()
        return _account_settings_redirect(
            embedded=embedded, result=_merge_recovery_result(exc.code)
        )
    except SQLAlchemyError:
        await db.rollback()
        return _account_settings_redirect(embedded=embedded, result="provider_link_unavailable")
    if provider_id is None:
        await db.rollback()
        return _account_settings_redirect(embedded=embedded, result="provider_link_invalid")
    provider_label = account_merge_provider_label(provider_id)
    preview = None
    error_code = request.query_params.get("error", "")
    error_message = _error_copy(error_code, provider_label=provider_label) if error_code else None
    try:
        preview = await preview_merge_intent(db, intent_id=intent.id)
    except AccountMergeError as exc:
        if exc.durable:
            await db.commit()
        error_code = exc.code
        error_message = _error_copy(exc.code, provider_label=provider_label)
    except SQLAlchemyError:
        await db.rollback()
        return _account_settings_redirect(embedded=embedded, result="provider_link_unavailable")
    can_restart = error_code in ACCOUNT_MERGE_RESTART_ERRORS
    return cabinet_html_response(
        render_account_merge_page(
            preview,
            intent_id=intent.id,
            embedded=embedded,
            csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "settings",
                principal=principal,
                tenant_scope=tenant_scope,
                device_class="desktop_webview" if embedded else "browser",
            ),
            error_message=error_message,
            requires_reauth=error_code == "reauth_required",
            requires_restart=can_restart,
            provider_id=provider_id,
            blockers=(
                account_merge_blockers(
                    preview.blocker_codes,
                    intent_id=intent.id,
                    embedded=embedded,
                    support_email=request.app.state.settings.billing_support_email,
                    provider_label=provider_label,
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
        return _account_settings_redirect(embedded=embedded, result="reauth_required")
    if db is None:
        return _account_settings_redirect(embedded=embedded, result="provider_link_unavailable")
    try:
        intent = await _owned_intent(
            db, intent_id=intent_id, principal=principal, tenant_scope=tenant_scope
        )
        provider_id = await _intent_provider_id(db, intent)
    except ProblemDetail as exc:
        await db.rollback()
        return _account_settings_redirect(
            embedded=embedded,
            result=_merge_recovery_result(exc.code),
        )
    except SQLAlchemyError:
        await db.rollback()
        return _account_settings_redirect(embedded=embedded, result="provider_link_unavailable")
    if provider_id is None:
        await db.rollback()
        return _account_settings_redirect(embedded=embedded, result="provider_link_invalid")
    owned_intent_id = intent.id
    form = await request.form()
    fingerprint = str(form.get("preview_fingerprint") or "")
    idempotency_key = str(form.get("idempotency_key") or "")
    if not fingerprint or not idempotency_key:
        await db.rollback()
        return _account_settings_redirect(embedded=embedded, result="provider_link_invalid")
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
        if exc.code in {
            "merge_already_completed",
            "merge_idempotency_conflict",
            "merge_intent_not_found",
            "merge_journal_missing",
        }:
            return _account_settings_redirect(
                embedded=embedded,
                result=_merge_recovery_result(exc.code),
            )
        return RedirectResponse(
            f"{'/desktop' if embedded else ''}/settings/account/merge/{owned_intent_id}?error={exc.code}",
            status_code=303,
        )
    except SQLAlchemyError:
        await db.rollback()
        return _account_settings_redirect(embedded=embedded, result="provider_link_unavailable")
    await db.commit()
    response = RedirectResponse(
        f"/login?next=/desktop/settings/account&error={_relogin_result(provider_id)}"
        if embedded
        else f"/login?next=/settings/account&error={_relogin_result(provider_id)}",
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
    embedded = _embedded(request)
    if not principal.auth_via_session or not is_web_cookie_session(request):
        return _account_settings_redirect(embedded=embedded, result="reauth_required")
    if db is None:
        return _account_settings_redirect(embedded=embedded, result="provider_link_unavailable")
    try:
        intent = await _owned_intent(
            db, intent_id=intent_id, principal=principal, tenant_scope=tenant_scope
        )
        await cancel_merge_intent(db, intent_id=intent.id, actor_user_id=principal.user_id)
        await db.commit()
    except ProblemDetail as exc:
        await db.rollback()
        return _account_settings_redirect(
            embedded=embedded, result=_merge_recovery_result(exc.code)
        )
    except AccountMergeError as exc:
        await db.rollback()
        return _account_settings_redirect(
            embedded=embedded, result=_merge_recovery_result(exc.code)
        )
    except SQLAlchemyError:
        await db.rollback()
        return _account_settings_redirect(embedded=embedded, result="provider_link_unavailable")
    return _account_settings_redirect(embedded=embedded, result="merge_cancelled")
