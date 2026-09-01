from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import quote, urlencode, urlsplit
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import case, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.browser_handoff import (
    DESKTOP_BILLING_HANDOFF_PROVIDER,
    open_desktop_billing_session,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.rate_limit import enforce_auth_rate_limits
from twobrain_rec_server.auth.sessions import hash_token
from twobrain_rec_server.billing.catalog import (
    FREE_PROCESSING_SECONDS,
    FREE_STORAGE_BYTES,
    CatalogNotApproved,
    classify_free_processing,
    classify_storage_threshold,
    plan_descriptor,
    validate_plan_version,
)
from twobrain_rec_server.billing.checkout import (
    CheckoutPreview,
    build_checkout_intent,
    checkout_preview,
)
from twobrain_rec_server.billing.entitlements import effective_plan_code
from twobrain_rec_server.billing.history import mask_payment_method
from twobrain_rec_server.billing.operations import (
    CHECKOUT_BLOCKING_STATES,
    BillingEmergencyStop,
    provider_key_is_expired,
    require_billing_enabled,
)
from twobrain_rec_server.billing.promotions import (
    PromoCode,
    PromoError,
    check_eligibility,
    choose_best_discount,
    normalize_promo,
    promo_code_hash,
)
from twobrain_rec_server.billing.provider_events import validate_provider_identifier
from twobrain_rec_server.billing.receipts import (
    ReceiptState,
    receipt_label,
    receipt_state_for_registration,
)
from twobrain_rec_server.billing.referrals import referral_token_hash, validate_referral_token
from twobrain_rec_server.billing.refund_email import build_refund_mailto
from twobrain_rec_server.billing.storage import (
    StorageProjection,
    lock_storage_workspace,
    project_active_playback_storage,
)
from twobrain_rec_server.billing.subscription import (
    SubscriptionControl,
    cancel_auto_renewal,
    resume_auto_renewal,
)
from twobrain_rec_server.billing.trial import (
    activate_trial,
    merged_user_lineage,
    require_trial_activation,
    trial_used_by_lineage,
)
from twobrain_rec_server.billing.usage import format_duration, moscow_window_for
from twobrain_rec_server.billing.webhook_reconciliation import (
    reconcile_pending_initial_checkout_operations,
)
from twobrain_rec_server.billing.yookassa import (
    YooKassaClient,
    YooKassaConfigurationError,
    YooKassaProviderError,
    build_receipt_payload,
    is_allowed_confirmation_url,
    provider_environment,
)
from twobrain_rec_server.cabinet.rendering_shared import _page_shell
from twobrain_rec_server.cabinet.templates import cabinet_html_response
from twobrain_rec_server.cabinet.web_routes.auth_email_flow import _set_browser_auth_cookie
from twobrain_rec_server.cabinet.web_routes.support import (
    LoginDbDependency,
    PrincipalDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
)
from twobrain_rec_server.db.models import (
    AuthCallbackState,
    AuthSession,
    BillingAuditEvent,
    BillingInvoice,
    BillingOperation,
    BillingPaymentMethod,
    BillingPlanVersion,
    ExternalIdentity,
    FreeUsageWindow,
    PromotionCampaign,
    PromotionRedemption,
    ReferralAttribution,
    StorageReservation,
    TimeCreditLedgerEntry,
    TrialActivation,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.tenant_context import (
    AuthCallbackLookupContext,
    AuthReferralLookupContext,
    AuthReferralUserLookupContext,
    AuthSessionLookupContext,
    apply_tenant_context,
    apply_tenant_scope,
)
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

if TYPE_CHECKING:
    from twobrain_rec_server.config import Settings

router = APIRouter(tags=["cabinet-web"])

_CHECKOUT_PROMO_COOKIE = "graf_checkout_promo"
_CHECKOUT_PROMO_COOKIE_MAX_AGE = 5 * 60
_BILLING_OFFER_VERSION = "billing-personal-v1"


def _is_embedded_request(request: Request) -> bool:
    """Presentation hint only; auth and tenant checks remain server-owned."""
    return request.headers.get("X-GRAF-Client", "").lower() == "desktop"


@router.get("/billing/handoff", include_in_schema=False)
async def billing_browser_handoff(
    request: Request,
    state: str = Query(min_length=16, max_length=128),
    db: AsyncSession | None = LoginDbDependency,
) -> RedirectResponse:
    """Exchange one native desktop handoff for the normal browser session cookie."""
    fallback = RedirectResponse(
        "/login?next=%2Fbilling&error=auth_handoff_invalid",
        status_code=303,
    )
    if db is None:
        return fallback
    key_file = getattr(request.app.state.settings, "credential_encryption_key_file", None)
    if key_file is None:
        return fallback
    key = key_file.read_bytes().strip()
    if not key:
        return fallback
    now = datetime.now(UTC)
    await apply_tenant_context(db, AuthCallbackLookupContext(state_nonce=state))
    callback_state = await db.scalar(
        select(AuthCallbackState)
        .where(
            AuthCallbackState.provider == DESKTOP_BILLING_HANDOFF_PROVIDER,
            AuthCallbackState.state_nonce == state,
        )
        .with_for_update()
    )
    if callback_state is None or callback_state.result != "pending":
        return fallback
    if callback_state.expires_at <= now:
        callback_state.used_at = now
        callback_state.result = "expired"
        callback_state.error_code = "auth_handoff_expired"
        await db.commit()
        return fallback

    session_token = open_desktop_billing_session(callback_state.expected_state, key=key)
    if session_token is None:
        callback_state.used_at = now
        callback_state.result = "failed"
        callback_state.error_code = "auth_handoff_invalid"
        await db.commit()
        return fallback

    await apply_tenant_context(
        db,
        AuthSessionLookupContext(session_token_hash=hash_token(session_token)),
    )
    auth_session = await db.scalar(
        select(AuthSession).where(AuthSession.session_token_hash == hash_token(session_token))
    )
    if auth_session is None or auth_session.status != "active" or auth_session.expires_at <= now:
        await apply_tenant_context(db, AuthCallbackLookupContext(state_nonce=state))
        callback_state.used_at = now
        callback_state.result = "failed"
        callback_state.error_code = "auth_handoff_session_invalid"
        await db.commit()
        return fallback

    await apply_tenant_context(db, AuthCallbackLookupContext(state_nonce=state))
    callback_state.used_at = now
    callback_state.result = "completed"
    callback_state.error_code = None
    await db.commit()
    redirect = RedirectResponse("/billing", status_code=303)
    _set_browser_auth_cookie(
        request,
        redirect,
        token=session_token,
        expires_at=auth_session.expires_at,
    )
    return redirect


def _checkout_result_redirect(
    request: Request,
    result: str,
    *,
    promo_code: str | None = None,
    cycle: str | None = None,
) -> RedirectResponse:
    """Keep only the recoverable checkout field across a result redirect.

    The cookie is short-lived, HttpOnly and scoped to checkout routes. Promo
    codes are not financial identifiers, but they still must not enter a URL
    query string where browser history, referrer or analytics could capture
    them.
    """

    query = {"result": result}
    if cycle in {"month", "year"}:
        query["cycle"] = cycle
    response = RedirectResponse(f"/billing/checkout?{urlencode(query)}", status_code=303)
    try:
        value = normalize_promo(promo_code) if promo_code else ""
    except PromoError:
        # Never put unvalidated form bytes into a response header. A malformed
        # code is cheap to re-enter; preserving a valid normalized value is
        # enough for recoverable expiry/capacity errors.
        value = ""
        response.delete_cookie(_CHECKOUT_PROMO_COOKIE, path="/billing/checkout")
    if value:
        response.set_cookie(
            _CHECKOUT_PROMO_COOKIE,
            value=value,
            max_age=_CHECKOUT_PROMO_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
            path="/billing/checkout",
        )
    else:
        response.delete_cookie(_CHECKOUT_PROMO_COOKIE, path="/billing/checkout")
    return response


MOSCOW = ZoneInfo("Europe/Moscow")


def billing_checkout_return_url(request: Request, *, safe_invoice_number: str | None = None) -> str:
    """Build a canonical HTTPS callback URL; never trust the inbound Host header."""
    configured = getattr(request.app.state.settings, "public_base_url", None)
    if configured is None:
        raise YooKassaConfigurationError("billing public callback URL is unavailable")
    try:
        parsed = urlsplit(str(configured))
    except ValueError as exc:
        raise YooKassaConfigurationError("billing public callback URL is invalid") from exc
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise YooKassaConfigurationError("billing public callback URL is invalid")
    path = request.app.url_path_for("billing_checkout_return")
    if safe_invoice_number is not None:
        if re.fullmatch(r"INV-[A-Z0-9]+", safe_invoice_number) is None:
            raise YooKassaConfigurationError("billing invoice reference is invalid")
        path = f"{path}?{urlencode({'invoice': safe_invoice_number})}"
    return f"{str(configured).rstrip('/')}{path}"


def _checkout_status_location(safe_number: str, *, result: str | None = None) -> str:
    location = f"/billing/checkout/status/{quote(safe_number, safe='-')}"
    return f"{location}?{urlencode({'result': result})}" if result else location


def _blocking_payment_operation_query(workspace_id: UUID):
    """Find unresolved charges before any new checkout or trial mutation."""
    return (
        select(BillingOperation)
        .where(
            BillingOperation.workspace_id == workspace_id,
            BillingOperation.kind.in_(("initial_checkout", "renewal")),
            BillingOperation.state.in_(CHECKOUT_BLOCKING_STATES),
        )
        .order_by(
            case(
                (
                    (BillingOperation.kind == "renewal") & (BillingOperation.state == "scheduled"),
                    1,
                ),
                else_=0,
            ),
            BillingOperation.created_at.desc(),
        )
    )


def _initial_checkout_can_continue(
    operation: BillingOperation,
    *,
    now: datetime | None = None,
) -> bool:
    return (
        operation.kind == "initial_checkout"
        and operation.provider_id is None
        and operation.state in {"scheduled", "manual_resolution"}
        and operation.provider_key_expires_at is not None
        and not provider_key_is_expired(
            expires_at=operation.provider_key_expires_at,
            now=now,
        )
    )


def _initial_checkout_failure_metadata(
    exc: BaseException,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    if isinstance(exc, YooKassaProviderError):
        failure_class = (
            "provider_rejected"
            if exc.status_code is not None and 400 <= exc.status_code < 500
            else "provider_unavailable"
        )
    elif isinstance(exc, YooKassaConfigurationError):
        failure_class = "configuration"
    elif isinstance(exc, httpx.TimeoutException):
        failure_class = "transport_timeout"
    elif isinstance(exc, httpx.HTTPError):
        failure_class = "transport_error"
    elif isinstance(exc, BillingEmergencyStop):
        failure_class = "checkout_disabled"
    elif isinstance(exc, ValueError):
        failure_class = "invalid_checkout_snapshot"
    else:
        failure_class = "unexpected"
    metadata: dict[str, object] = {
        "class": failure_class,
        "observed_at": (now or datetime.now(UTC)).astimezone(UTC).isoformat(),
    }
    if (
        isinstance(exc, YooKassaProviderError)
        and exc.status_code is not None
        and 400 <= exc.status_code <= 599
    ):
        metadata["http_status"] = exc.status_code
    return metadata


def _record_initial_checkout_failure(
    operation: BillingOperation,
    invoice: BillingInvoice,
    exc: BaseException,
    *,
    now: datetime | None = None,
) -> None:
    current = now or datetime.now(UTC)
    snapshot = (
        dict(operation.request_snapshot) if isinstance(operation.request_snapshot, dict) else {}
    )
    snapshot["provider_failure"] = _initial_checkout_failure_metadata(exc, now=current)
    operation.request_snapshot = snapshot
    if operation.provider_id is not None:
        operation.state = "unknown"
        invoice.status = "unknown"
    elif provider_key_is_expired(expires_at=operation.provider_key_expires_at, now=current):
        operation.state = "provider_key_expired"
        invoice.status = "manual_resolution"
    else:
        operation.state = "manual_resolution"
        invoice.status = "manual_resolution"


async def _create_initial_checkout_payment(
    *,
    settings: Settings,
    operation: BillingOperation,
    invoice: BillingInvoice,
    return_url: str,
) -> dict[str, object]:
    snapshot = operation.request_snapshot
    if (
        operation.kind != "initial_checkout"
        or invoice.operation_id != operation.id
        or invoice.workspace_id != operation.workspace_id
        or not isinstance(snapshot, Mapping)
        or snapshot.get("plan_code") != "personal"
        or snapshot.get("cycle") not in {"month", "year"}
        or snapshot.get("offer_consent") is not True
        or snapshot.get("recurring_consent") is not True
        or isinstance(snapshot.get("payable_amount_minor"), bool)
        or snapshot.get("payable_amount_minor") != invoice.amount_minor
        or invoice.currency != "RUB"
    ):
        raise ValueError("initial checkout snapshot is invalid")
    receipt_config = snapshot.get("receipt_config")
    if not isinstance(receipt_config, Mapping):
        receipt_config = {}
    cycle = str(snapshot["cycle"])
    description = f"GRAF Личный, {cycle}"
    receipt = build_receipt_payload(
        receipt_contact=invoice.receipt_contact_snapshot,
        amount_minor=invoice.amount_minor,
        currency=invoice.currency,
        description=description,
        tax_system_code=receipt_config.get(
            "tax_system_code", settings.billing_receipt_tax_system_code
        ),
        vat_code=receipt_config.get("vat_code", settings.billing_receipt_vat_code),
        payment_subject=str(
            receipt_config.get("payment_subject", settings.billing_receipt_payment_subject)
        ),
        payment_mode=str(receipt_config.get("payment_mode", settings.billing_receipt_payment_mode)),
    )
    async with YooKassaClient(settings) as provider:
        return await provider.create_payment(
            amount_minor=invoice.amount_minor,
            currency=invoice.currency,
            description=description,
            idempotence_key=operation.idempotency_key,
            metadata={
                "workspace_id": str(operation.workspace_id),
                "operation_id": str(operation.id),
                "invoice_number": invoice.safe_number,
                "return_url": return_url,
            },
            save_payment_method=True,
            receipt=receipt,
        )


def _bind_initial_checkout_payment(
    operation: BillingOperation,
    invoice: BillingInvoice,
    payment: Mapping[str, object],
) -> str | None:
    provider_id = validate_provider_identifier(payment.get("id"))
    confirmation = payment.get("confirmation")
    confirmation_url = (
        confirmation.get("confirmation_url") if isinstance(confirmation, Mapping) else None
    )
    operation.provider_id = provider_id
    snapshot = dict(operation.request_snapshot)
    if is_allowed_confirmation_url(confirmation_url):
        operation.state = "provider_pending"
        invoice.status = "pending"
        snapshot["confirmation_url"] = confirmation_url
    else:
        operation.state = "unknown"
        invoice.status = "unknown"
        confirmation_url = None
    operation.request_snapshot = snapshot
    return confirmation_url


def _status_refresh_result(counters: Mapping[str, int]) -> str:
    if counters.get("processed", 0) == 0:
        return "unchanged"
    if counters.get("failed", 0) > 0:
        return "unavailable"
    return "refreshed"


def trial_surface(
    *,
    raw_plan_code: str,
    effective_plan_code_value: str,
    trial_ends_at: datetime | None,
    now: datetime,
) -> tuple[int | None, str | None, bool]:
    """Return days-left, exact Moscow end label and the expired-trial state."""
    if trial_ends_at is None:
        return None, None, False
    end_label = trial_ends_at.astimezone(MOSCOW).strftime("%d.%m.%Y, %H:%M:%S (МСК)")
    expired = (
        raw_plan_code == "trial" and trial_ends_at <= now and effective_plan_code_value == "free"
    )
    days_left = (
        max(0, int((trial_ends_at.astimezone(UTC) - now.astimezone(UTC)).total_seconds() // 86_400))
        if effective_plan_code_value == "trial"
        else None
    )
    return days_left, end_label, expired


def trial_remaining_label(*, trial_ends_at: datetime | None, now: datetime) -> str | None:
    """Format the relative trial remainder without rounding up."""
    if trial_ends_at is None:
        return None
    remaining_seconds = int((trial_ends_at.astimezone(UTC) - now.astimezone(UTC)).total_seconds())
    if remaining_seconds <= 0:
        return None
    days, remainder = divmod(remaining_seconds, 86_400)
    hours = remainder // 3_600
    return f"{days} дн. {hours} ч."


def trial_phase(*, trial_ends_at: datetime | None, now: datetime) -> str | None:
    """Return the contextual countdown phase without flooring away the last day."""
    if trial_ends_at is None:
        return None
    remaining_seconds = int((trial_ends_at.astimezone(UTC) - now.astimezone(UTC)).total_seconds())
    if remaining_seconds <= 0:
        return None
    if remaining_seconds <= 86_400:
        return "t_minus_1"
    if remaining_seconds <= 3 * 86_400:
        return "t_minus_3"
    return None


def _billing_datetime_label(value: datetime | None) -> str | None:
    return value.astimezone(MOSCOW).strftime("%d.%m.%Y, %H:%M (МСК)") if value is not None else None


def _billing_amount_label(amount_minor: int | None, currency: str = "RUB") -> str | None:
    if amount_minor is None:
        return None
    if currency.upper() == "RUB":
        if amount_minor % 100 == 0:
            return f"{amount_minor // 100:,} ₽".replace(",", " ")
        return f"{amount_minor / 100:,.2f} ₽".replace(",", " ")
    return f"{amount_minor / 100:,.2f} {currency}".replace(",", " ")


def _billing_price_label(amount_minor: int | None) -> str | None:
    if amount_minor is None:
        return None
    if amount_minor % 100 == 0:
        return f"{amount_minor // 100:,} ₽".replace(",", " ")
    return f"{amount_minor / 100:,.2f} ₽".replace(",", " ")


def checkout_preview_labels(
    preview: CheckoutPreview,
    *,
    discount_percent: int | None = None,
    discount_source: str | None = None,
) -> dict[str, str]:
    """Build safe Russian labels for the server-calculated checkout summary."""
    discount_minor = preview.list_amount_minor - preview.payable_amount_minor
    discount_label = "Без скидки"
    if discount_minor > 0 and discount_percent is not None:
        source_label = "реферальная скидка, " if discount_source == "referral" else ""
        discount_label = (
            f"−{_billing_price_label(discount_minor)} ({source_label}{discount_percent}%)"
        )
    return {
        "cycle_label": "месяц" if preview.cycle == "month" else "год",
        "list_amount_label": _billing_price_label(preview.list_amount_minor) or "—",
        "discount_label": discount_label,
        "payable_amount_label": _billing_price_label(preview.payable_amount_minor) or "—",
        "next_amount_label": _billing_price_label(preview.list_amount_minor) or "—",
    }


def _choose_checkout_discount(
    *,
    amount_minor: int,
    cycle: str,
    provider_floor_minor: int,
    promo: PromoCode | None,
    referral_candidate: PromoCode | None,
) -> tuple[PromoCode | None, str | None]:
    candidates = tuple(
        candidate for candidate in (promo, referral_candidate) if candidate is not None
    )
    chosen, _ = choose_best_discount(
        amount_minor=amount_minor,
        plan_code="personal",
        cycle=cycle,
        provider_floor_minor=provider_floor_minor,
        candidates=candidates,
        strict_first=promo is not None,
    )
    discount_source = (
        "referral"
        if chosen is referral_candidate and referral_candidate is not None
        else "promo"
        if chosen is not None
        else None
    )
    return chosen, discount_source


def _annual_saving_label(
    monthly_amount_minor: int | None, annual_amount_minor: int | None
) -> str | None:
    if monthly_amount_minor is None or annual_amount_minor is None:
        return None
    saving = monthly_amount_minor * 12 - annual_amount_minor
    if saving <= 0:
        return None
    percent = round(saving / (monthly_amount_minor * 12) * 100)
    return f"Экономия {_billing_price_label(saving)} ({percent}%)"


def _operation_state_label(state: str | None) -> str:
    return {
        "scheduled": "Платёж подготовлен",
        "provider_pending": "Ожидаем подтверждение ЮKassa",
        "sent": "Платёж отправлен в ЮKassa",
        "processing": "ЮKassa обрабатывает платёж",
        "unknown": "Проверяем результат платежа",
        "pending_reconciliation": "Ожидаем сверку с ЮKassa",
        "reconciliation_gap": "Нужна ручная сверка платежа",
        "manual_resolution": "Нужна ручная сверка платежа",
        "provider_key_expired": "Срок безопасного продолжения оплаты истёк",
        "method_required": "Нужен способ оплаты",
        "succeeded": "Платёж подтверждён",
        "canceled": "Платёж отменён",
        "failed": "Платёж не выполнен",
    }.get(state or "", "Статус уточняется")


def _invoice_status_label(status: str) -> str:
    return {
        "pending": "Ожидает подтверждения",
        "succeeded": "Оплачен",
        "canceled": "Отменён",
        "failed": "Не выполнен",
        "unknown": "Проверяем результат",
    }.get(status, "Статус уточняется")


def _receipt_registration_state(value: object) -> ReceiptState:
    try:
        return receipt_state_for_registration(value if isinstance(value, str) else None)
    except ValueError:
        return ReceiptState.UNKNOWN


def _masked_receipt_contact(value: str | None) -> str | None:
    if not isinstance(value, str) or "@" not in value:
        return None
    local, domain = value.split("@", 1)
    if not local or not domain:
        return None
    return f"{local[0]}***@{domain}"


def _capacity_label(capacity_bytes: int) -> str:
    units = ((1_000_000_000, "GB"), (1_000_000, "MB"))
    for divisor, unit in units:
        if capacity_bytes % divisor == 0:
            return f"{capacity_bytes // divisor} {unit}"
    return f"{capacity_bytes:,} байт".replace(",", " ")


def _exact_bytes_label(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _storage_threshold_label(value: str) -> str:
    return {
        "normal": "В норме",
        "80%": "Заполнено на 80%",
        "95%": "Заполнено на 95%",
        "full": "Заполнено",
        "over_capacity": "Превышена ёмкость",
    }.get(value, "Состояние уточняется")


def _processing_threshold_label(value: str) -> str:
    return {
        "normal": "В норме",
        "approaching": "Приближается к лимиту",
        "exhausted": "Лимит исчерпан",
    }.get(value, "Состояние уточняется")


def _payment_method_kind_label(value: str | None) -> str | None:
    return {
        "bank_card": "Банковская карта",
        "sbp": "СБП",
    }.get(value, "Способ оплаты уточняется" if value else None)


def _promotion_state_label(state: str) -> str:
    return {
        "reserved": "Зарезервирован для оплаты",
        "redeemed": "Применён",
        "released": "Освобождён после отмены оплаты",
        "expired": "Истёк",
    }.get(state, "Статус уточняется")


async def _billing_rate_limited_response(
    request: Request,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    action: str,
    message: str = "Слишком много попыток. Попробуйте позже.",
) -> HTMLResponse | None:
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        return None
    retry_after = await enforce_auth_rate_limits(
        None,
        workspace_id=tenant_scope.workspace_id,
        scopes=((action, f"{principal.user_id}:{tenant_scope.workspace_id}"),),
        sessionmaker=sessionmaker,
        scope_secret=request.app.state.settings.share_identity_hash_secret,
    )
    if retry_after is None:
        return None
    response = HTMLResponse(message, status_code=429)
    response.headers["Retry-After"] = str(retry_after)
    response.headers["Cache-Control"] = "private, no-store"
    return response


async def _approved_personal_catalog(
    db: AsyncSession | None,
    *,
    now: datetime,
) -> dict[str, object]:
    """Read the same approved catalog authority used by checkout UI and POST."""
    if db is None:
        return {}
    rows = await db.scalars(
        select(BillingPlanVersion)
        .where(
            BillingPlanVersion.plan_code == "personal",
            BillingPlanVersion.cycle.in_(("month", "year")),
        )
        .order_by(BillingPlanVersion.version.desc())
    )
    approved: dict[str, object] = {}
    for row in rows:
        if row.cycle in approved:
            continue
        try:
            approved[row.cycle] = validate_plan_version(row, now=now)
        except (CatalogNotApproved, ValueError):
            continue
    return approved


async def _load_checkout_promo(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    raw_code: str,
    cycle: str,
    now: datetime,
    lock: bool = False,
) -> tuple[PromoCode, PromotionCampaign]:
    """Load and validate one campaign for preview or the final invoice."""
    normalized = normalize_promo(raw_code)
    query = select(PromotionCampaign).where(
        PromotionCampaign.code_hash == promo_code_hash(normalized),
        PromotionCampaign.enabled.is_(True),
    )
    if lock:
        query = query.with_for_update()
    campaign = await db.scalar(query)
    if campaign is None:
        raise PromoError("Промокод не распознан")
    used = await db.scalar(
        select(func.count(PromotionRedemption.id)).where(
            PromotionRedemption.workspace_id == workspace_id,
            PromotionRedemption.campaign_id == campaign.id,
            PromotionRedemption.state == "redeemed",
        )
    )
    promo = PromoCode(
        code=normalized,
        discount_percent=campaign.discount_percent,
        plan_code=campaign.plan_code,
        max_redemptions=campaign.max_redemptions,
        redeemed=campaign.redeemed_count,
        cycle=campaign.cycle,
        campaign_version=campaign.campaign_version,
        starts_at=campaign.starts_at,
        ends_at=campaign.ends_at,
    )
    check_eligibility(
        promo=promo,
        plan_code="personal",
        cycle=cycle,
        now=now,
        workspace_redemptions=int(used or 0),
        active_reservations=campaign.reserved_count,
    )
    return promo, campaign


async def _billing_role(
    db: AsyncSession | None,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
) -> str | None:
    if db is None:
        return None
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == tenant_scope.workspace_id,
            WorkspaceMembership.user_id == principal.user_id,
            WorkspaceMembership.status == "active",
        )
    )
    if membership is None:
        return None
    workspace = await db.get(Workspace, tenant_scope.workspace_id)
    if membership.role == "owner":
        # Corporate billing is sales-assisted/read-only. A personal owner is
        # valid only when the workspace's immutable owner marker agrees.
        if workspace is None or workspace.kind != "personal":
            return "corporate_owner"
        if workspace.owner_user_id != principal.user_id:
            return "member"
    return membership.role


def _can_manage_billing(
    *,
    role: str | None,
    subscription: WorkspaceSubscription | None,
    principal: AuthenticatedPrincipal,
) -> bool:
    return role == "owner" and (
        subscription is None or subscription.billing_owner_id in {None, principal.user_id}
    )


async def _trial_eligibility_state(
    db: AsyncSession | None,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
) -> str:
    """Return a user-safe trial state before rendering or mutating controls."""
    if db is None:
        return "unavailable"
    identity = await db.get(UserIdentity, principal.user_id)
    if await trial_used_by_lineage(db, user_id=principal.user_id):
        return "already"
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == tenant_scope.workspace_id,
            WorkspaceMembership.user_id == principal.user_id,
            WorkspaceMembership.status == "active",
        )
    )
    workspace = await db.get(Workspace, tenant_scope.workspace_id)
    subscription = await db.scalar(
        select(WorkspaceSubscription).where(
            WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
        )
    )
    if (
        identity is None
        or membership is None
        or membership.role != "owner"
        or workspace is None
        or workspace.kind != "personal"
        or workspace.owner_user_id != principal.user_id
    ):
        return "unavailable"
    if subscription is not None and (
        subscription.paid_through is not None
        and subscription.paid_through > datetime.now(UTC)
        or effective_plan_code(
            plan_code=subscription.plan_code,  # type: ignore[arg-type]
            state=subscription.state,
            now=datetime.now(UTC),
            paid_through=subscription.paid_through,
            trial_ends_at=subscription.trial_ends_at,
        )
        != "free"
    ):
        return "unavailable"
    verified_identity = await db.scalar(
        select(ExternalIdentity.id).where(
            ExternalIdentity.user_id == principal.user_id,
            ExternalIdentity.is_active.is_(True),
            ExternalIdentity.is_verified.is_(True),
        )
    )
    if identity.status != "active" or verified_identity is None:
        return "verification_required"
    return "eligible"


async def _referral_attribution_for_lineage(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    lineage_user_ids: tuple[UUID, ...],
    token_hash: str | None = None,
) -> ReferralAttribution | None:
    for lineage_user_id in lineage_user_ids:
        if token_hash is None:
            await apply_tenant_context(
                db,
                AuthReferralUserLookupContext(user_id=lineage_user_id),
            )
        else:
            await apply_tenant_context(
                db,
                AuthReferralLookupContext(
                    workspace_id=workspace_id,
                    user_id=lineage_user_id,
                    token_hash=token_hash,
                ),
            )
        query = select(ReferralAttribution).where(
            ReferralAttribution.invitee_user_id == lineage_user_id,
            ReferralAttribution.state.in_(("bound", "registered", "attributed")),
        )
        if token_hash is not None:
            query = query.where(ReferralAttribution.token_hash == token_hash)
        attribution = await db.scalar(query)
        if attribution is not None:
            return attribution
    return None


async def _checkout_referral_candidate(
    db: AsyncSession,
    *,
    request: Request,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
) -> tuple[PromoCode | None, ReferralAttribution | None, set[UUID]]:
    """Read the same optional referral discount used by final checkout."""
    lineage = merged_user_lineage(principal.user_id)
    lineage_ids = set(await db.scalars(select(lineage.c.user_id)))
    lineage_ids.add(principal.user_id)
    lineage_user_ids = (
        principal.user_id,
        *sorted(lineage_ids - {principal.user_id}, key=str),
    )
    referred = None
    try:
        referral_cookie = request.cookies.get("graf_referral_token")
        if referral_cookie:
            token_hash = referral_token_hash(validate_referral_token(referral_cookie))
            referred = await _referral_attribution_for_lineage(
                db,
                workspace_id=tenant_scope.workspace_id,
                lineage_user_ids=lineage_user_ids,
                token_hash=token_hash,
            )
        if referred is None:
            referred = await _referral_attribution_for_lineage(
                db,
                workspace_id=tenant_scope.workspace_id,
                lineage_user_ids=lineage_user_ids,
            )
    except ValueError:
        referred = None
    finally:
        await apply_tenant_scope(db, tenant_scope)
    referral_candidate = (
        PromoCode("REFERRAL_INTRO", 10, "personal", 1, campaign_version="referral-v1")
        if referred is not None and referred.inviter_user_id not in lineage_ids
        else None
    )
    return referral_candidate, referred, lineage_ids


@router.get("/settings/billing", include_in_schema=False)
async def settings_billing_alias() -> RedirectResponse:
    return RedirectResponse("/billing", status_code=307)


@router.get("/account/billing", include_in_schema=False)
async def account_billing_alias() -> RedirectResponse:
    """Keep the legacy account link in the canonical billing surface."""
    return RedirectResponse("/billing", status_code=307)


@router.get("/billing", response_class=HTMLResponse, include_in_schema=False)
async def billing_overview_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    now = datetime.now(UTC)
    subscription = None
    trial_result = request.query_params.get("trial")
    billing_result = request.query_params.get("result")
    if db is not None:
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
    raw_plan_code = subscription.plan_code if subscription is not None else "free"
    plan_code = effective_plan_code(
        plan_code=raw_plan_code,  # type: ignore[arg-type]
        state=subscription.state if subscription is not None else "free",
        now=now,
        paid_through=subscription.paid_through if subscription is not None else None,
        trial_ends_at=subscription.trial_ends_at if subscription is not None else None,
    )
    plan = plan_descriptor(plan_code)  # type: ignore[arg-type]
    role = await _billing_role(db, tenant_scope=tenant_scope, principal=principal)
    billing_owner = _can_manage_billing(role=role, subscription=subscription, principal=principal)
    trial_state = (
        await _trial_eligibility_state(db, tenant_scope=tenant_scope, principal=principal)
        if plan_code == "free" and billing_owner
        else "unavailable"
    )
    trial_eligible = trial_state == "eligible"
    trial_days_left, trial_ends_at_label, trial_expired = trial_surface(
        raw_plan_code=raw_plan_code,
        effective_plan_code_value=plan_code,
        trial_ends_at=subscription.trial_ends_at if subscription is not None else None,
        now=now,
    )
    trial_remaining = trial_remaining_label(
        trial_ends_at=subscription.trial_ends_at if subscription is not None else None,
        now=now,
    )
    current_trial_phase = trial_phase(
        trial_ends_at=subscription.trial_ends_at if subscription is not None else None,
        now=now,
    )
    renewal_failed = (
        raw_plan_code == "personal"
        and plan_code == "free"
        and subscription is not None
        and subscription.renewal_resolution
        in {
            "canceled",
            "provider_key_expired",
            "manual_resume_required",
            "final_failure",
            "authority_refused",
            "late_success_refused",
        }
    )
    effective_capacity = (
        subscription.capacity_bytes
        if subscription is not None and plan_code in {"trial", "personal"}
        else FREE_STORAGE_BYTES
    )
    storage_used = 0
    storage_reserved = 0
    processing_used = 0
    processing_reserved = 0
    latest_invoice = None
    latest_operation = None
    pending_invoice = None
    payment_method = None
    bonus_until = None
    window = None
    window_start, window_end = moscow_window_for(now)
    if db is not None:
        window = await db.scalar(
            select(FreeUsageWindow).where(
                FreeUsageWindow.workspace_id == tenant_scope.workspace_id,
                FreeUsageWindow.window_start == window_start,
            )
        )
        processing_used = window.committed_seconds if window is not None else 0
        processing_reserved = window.reserved_seconds if window is not None else 0
        storage_reserved = int(
            await db.scalar(
                select(
                    func.coalesce(
                        func.sum(
                            StorageReservation.declared_bytes - StorageReservation.committed_bytes
                        ),
                        0,
                    )
                ).where(
                    StorageReservation.workspace_id == tenant_scope.workspace_id,
                    StorageReservation.state == "active",
                    (
                        StorageReservation.expires_at.is_(None)
                        | (StorageReservation.expires_at > now)
                    ),
                )
            )
            or 0
        )
        projection = await project_active_playback_storage(
            db,
            workspace_id=tenant_scope.workspace_id,
            capacity_bytes=effective_capacity,
            reserved_bytes=storage_reserved,
        )
        storage_used = projection.used_bytes
        latest_invoice = await db.scalar(
            select(BillingInvoice)
            .where(BillingInvoice.workspace_id == tenant_scope.workspace_id)
            .order_by(BillingInvoice.created_at.desc())
            .limit(1)
        )
        latest_operation = await db.scalar(
            _blocking_payment_operation_query(tenant_scope.workspace_id).limit(1)
        )
        if latest_operation is not None:
            pending_invoice = await db.scalar(
                select(BillingInvoice).where(
                    BillingInvoice.workspace_id == tenant_scope.workspace_id,
                    BillingInvoice.operation_id == latest_operation.id,
                )
            )
        bonus_until = await db.scalar(
            select(func.max(TimeCreditLedgerEntry.applied_end)).where(
                TimeCreditLedgerEntry.workspace_id == tenant_scope.workspace_id,
                TimeCreditLedgerEntry.state == "applied",
                TimeCreditLedgerEntry.applied_end.is_not(None),
                TimeCreditLedgerEntry.applied_end > now,
            )
        )
        if billing_owner:
            payment_method = await db.scalar(
                select(BillingPaymentMethod).where(
                    BillingPaymentMethod.workspace_id == tenant_scope.workspace_id,
                    BillingPaymentMethod.owner_user_id == principal.user_id,
                    BillingPaymentMethod.is_default.is_(True),
                    BillingPaymentMethod.state == "active",
                )
            )
    paid_through_label = _billing_datetime_label(
        subscription.paid_through
        if subscription is not None and plan_code == "personal"
        else subscription.trial_ends_at
        if subscription is not None and plan_code == "trial"
        else None
    )
    approved_catalog = await _approved_personal_catalog(db, now=now)
    latest_invoice_summary = None
    pending_invoice_summary = None
    latest_snapshot = (
        latest_invoice.plan_snapshot
        if latest_invoice is not None and isinstance(latest_invoice.plan_snapshot, dict)
        else {}
    )
    if billing_owner and latest_invoice is not None:
        latest_invoice_summary = {
            "safe_number": latest_invoice.safe_number,
            "amount_label": _billing_amount_label(
                latest_invoice.amount_minor, latest_invoice.currency
            )
            or "Сумма недоступна",
            "created_at_label": _billing_datetime_label(latest_invoice.created_at),
            "status_label": _invoice_status_label(latest_invoice.status),
            "payment_method_label": mask_payment_method(
                latest_snapshot.get("payment_method_label")
                if isinstance(latest_snapshot.get("payment_method_label"), str)
                else None
            ),
        }
    if billing_owner and pending_invoice is not None:
        pending_invoice_summary = {"safe_number": pending_invoice.safe_number}
    # The query parameter is only a one-time notice; persisted operations are
    # the sole source of truth for whether a new checkout is blocked.
    blocking_operations = []
    if db is not None:
        scalars = getattr(db, "scalars", None)
        if callable(scalars):
            blocking_operations = list(
                await scalars(_blocking_payment_operation_query(tenant_scope.workspace_id))
            )
        elif latest_operation is not None:
            # Keep lightweight test doubles and read-only adapters compatible;
            # production AsyncSession always takes the complete-query branch.
            blocking_operations = [latest_operation]
    operation_pending = any(
        not (
            operation.kind == "renewal"
            and operation.state == "scheduled"
            and plan_code == "personal"
        )
        for operation in blocking_operations
    )
    current_cycle = (
        subscription.cycle
        if subscription is not None and subscription.cycle in {"month", "year"}
        else latest_snapshot.get("cycle")
    )
    if current_cycle not in {"month", "year"}:
        current_cycle = None
    current_catalog = approved_catalog.get(current_cycle) if current_cycle is not None else None
    current_price_label = (
        "0 ₽"
        if plan_code in {"free", "trial"}
        else _billing_amount_label(
            current_catalog.amount_minor if current_catalog is not None else None
        )
        or "Сумма уточняется"
    )
    current_cycle_label = (
        "без оплаты"
        if plan_code == "free"
        else "7 дней"
        if plan_code == "trial"
        else "в год"
        if current_cycle == "year"
        else "в месяц"
        if current_cycle == "month"
        else "период уточняется"
    )
    recurring_next_charge_label = None
    recurring_next_charge_amount_label = None
    if (
        subscription is not None
        and plan_code == "personal"
        and subscription.paid_through
        and subscription.paid_through > now
    ):
        if subscription.recurring_allowed:
            recurring_next_charge_label = _billing_datetime_label(subscription.paid_through)
            snapshot = (
                latest_invoice.plan_snapshot
                if latest_invoice and isinstance(latest_invoice.plan_snapshot, dict)
                else {}
            )
            cycle = (
                subscription.cycle
                if subscription.cycle in {"month", "year"}
                else snapshot.get("cycle")
            )
            scheduled_renewal_invoice = (
                pending_invoice
                if latest_operation is not None
                and latest_operation.kind == "renewal"
                and latest_operation.state == "scheduled"
                else None
            )
            recurring_next_charge_amount_label = _billing_amount_label(
                scheduled_renewal_invoice.amount_minor
                if scheduled_renewal_invoice is not None
                else approved_catalog[cycle].amount_minor
                if cycle in approved_catalog
                else None,
                scheduled_renewal_invoice.currency
                if scheduled_renewal_invoice is not None
                else "RUB",
            )
        else:
            recurring_next_charge_label = "не запланировано"
    elif subscription is not None and subscription.renewal_resolution in {
        "unknown_pending",
        "pending",
        "unknown",
    }:
        recurring_next_charge_label = "проверяем результат предыдущего списания"
    content = _page_shell(
        "Тариф и оплата",
        embedded=_is_embedded_request(request),
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request,
            "billing_overview",
            principal=principal,
            tenant_scope=tenant_scope,
        ),
        content_template="cabinet/pages/billing_overview_content.html",
        plan=plan,
        plan_code=plan_code,
        current_price_label=current_price_label,
        current_cycle_label=current_cycle_label,
        storage_used=storage_used,
        storage_used_label=_capacity_label(storage_used),
        storage_used_exact_label=_exact_bytes_label(storage_used),
        storage_reserved=storage_reserved,
        storage_reserved_label=_capacity_label(storage_reserved),
        storage_reserved_exact_label=_exact_bytes_label(storage_reserved),
        storage_capacity=effective_capacity,
        storage_threshold=classify_storage_threshold(
            used_bytes=storage_used,
            capacity_bytes=effective_capacity,
        ),
        storage_threshold_label=_storage_threshold_label(
            classify_storage_threshold(used_bytes=storage_used, capacity_bytes=effective_capacity)
        ),
        processing_used=processing_used,
        processing_reserved=processing_reserved,
        processing_used_label=format_duration(processing_used),
        processing_reserved_label=format_duration(processing_reserved),
        processing_remaining_label=format_duration(
            max(0, FREE_PROCESSING_SECONDS - processing_used - processing_reserved)
        ),
        processing_reset_at_label=window_end.astimezone(MOSCOW).strftime("%d.%m.%Y, %H:%M (МСК)"),
        free_processing_limit_label="300 минут",
        processing_usage_freshness=window.freshness_state
        if window is not None
        else ("unavailable" if db is None else "fresh"),
        billing_data_available=db is not None,
        storage_capacity_label=_capacity_label(effective_capacity),
        storage_capacity_exact_label=_exact_bytes_label(effective_capacity),
        processing_threshold=classify_free_processing(
            committed_seconds=processing_used + processing_reserved
        ),
        processing_threshold_label=_processing_threshold_label(
            classify_free_processing(committed_seconds=processing_used + processing_reserved)
        ),
        billing_enabled=bool(request.app.state.settings.billing_checkout_enabled),
        catalog_ready=("month" in approved_catalog and "year" in approved_catalog),
        trial_result=trial_result,
        trial_days_left=trial_days_left,
        trial_ends_at_label=trial_ends_at_label,
        trial_remaining_label=trial_remaining,
        trial_phase=current_trial_phase,
        renewal_failed=renewal_failed,
        trial_expired=trial_expired,
        trial_eligible=trial_eligible,
        trial_state=trial_state,
        billing_owner=billing_owner,
        billing_role=role,
        billing_result=billing_result,
        paid_through_label=paid_through_label,
        bonus_until_label=_billing_datetime_label(bonus_until),
        next_charge_label=recurring_next_charge_label,
        next_charge_amount_label=recurring_next_charge_amount_label,
        payment_method_label=payment_method.masked_label if payment_method is not None else None,
        latest_invoice=latest_invoice,
        latest_invoice_summary=latest_invoice_summary,
        pending_invoice_summary=pending_invoice_summary,
        latest_invoice_status_label=(
            _invoice_status_label(latest_invoice.status) if latest_invoice is not None else None
        ),
        latest_operation_label=_operation_state_label(
            latest_operation.state if latest_operation is not None else None
        ),
        operation_pending=operation_pending,
    )
    return cabinet_html_response(content)


@router.get("/billing/plans", response_class=HTMLResponse, include_in_schema=False)
async def billing_plans_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    """Show the server-owned plan catalog without inventing checkout prices."""
    subscription = None
    if db is not None:
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
    now = datetime.now(UTC)
    current_code = effective_plan_code(
        plan_code=subscription.plan_code if subscription is not None else "free",  # type: ignore[arg-type]
        state=subscription.state if subscription is not None else "free",
        now=now,
        paid_through=subscription.paid_through if subscription is not None else None,
        trial_ends_at=subscription.trial_ends_at if subscription is not None else None,
    )
    role = await _billing_role(db, tenant_scope=tenant_scope, principal=principal)
    billing_owner = _can_manage_billing(role=role, subscription=subscription, principal=principal)
    if role != "owner":
        return RedirectResponse("/billing?result=personal_only", status_code=303)
    operation_pending = False
    if db is not None:
        operation_pending = (
            await db.scalar(_blocking_payment_operation_query(tenant_scope.workspace_id).limit(1))
            is not None
        )
    trial_state = (
        await _trial_eligibility_state(db, tenant_scope=tenant_scope, principal=principal)
        if current_code == "free" and billing_owner
        else "unavailable"
    )
    catalog = await _approved_personal_catalog(db, now=now)
    current_cycle = (
        subscription.cycle
        if subscription is not None and subscription.cycle in {"month", "year"}
        else None
    )
    requested_cycle = request.query_params.get("cycle")
    selected_cycle = (
        requested_cycle if requested_cycle in {"month", "year"} else current_cycle or "year"
    )
    monthly_catalog = catalog.get("month")
    annual_catalog = catalog.get("year")
    catalog_ready = monthly_catalog is not None and annual_catalog is not None
    plans = []
    for code in ("free", "trial", "personal"):
        descriptor = plan_descriptor(code)  # type: ignore[arg-type]
        monthly_amount = (
            monthly_catalog.amount_minor
            if code == "personal" and monthly_catalog is not None
            else descriptor.monthly_amount_minor
        )
        annual_amount = (
            annual_catalog.amount_minor
            if code == "personal" and annual_catalog is not None
            else descriptor.annual_amount_minor
        )
        processing_label = (
            format_duration(FREE_PROCESSING_SECONDS) if code == "free" else "Без лимита"
        )
        plans.append(
            {
                "code": code,
                "label": descriptor.label,
                "processing_mode": descriptor.processing_mode,
                "processing_label": processing_label,
                "storage_label": _capacity_label(
                    monthly_catalog.storage_bytes
                    if code == "personal" and monthly_catalog is not None
                    else descriptor.storage_bytes
                ),
                "monthly_amount_label": _billing_price_label(monthly_amount)
                if catalog_ready or code != "personal"
                else None,
                "annual_amount_label": _billing_price_label(annual_amount)
                if catalog_ready or code != "personal"
                else None,
                "annual_saving_label": _annual_saving_label(
                    monthly_amount if catalog_ready or code != "personal" else None,
                    annual_amount if catalog_ready or code != "personal" else None,
                ),
                "is_current": code == current_code
                and (code != "personal" or selected_cycle == current_cycle),
                "catalog_ready": catalog_ready if code == "personal" else True,
            }
        )
    content = _page_shell(
        "Тарифы",
        embedded=_is_embedded_request(request),
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_plans", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_plans_content.html",
        plans=plans,
        selected_cycle=selected_cycle,
        current_plan_code=current_code,
        billing_role=role,
        billing_owner=billing_owner,
        operation_pending=operation_pending,
        trial_state=trial_state,
        billing_enabled=bool(request.app.state.settings.billing_checkout_enabled),
        catalog_ready=catalog_ready,
        support_email=request.app.state.settings.billing_support_email,
    )
    return cabinet_html_response(content)


@router.get("/billing/discounts", response_class=HTMLResponse, include_in_schema=False)
async def billing_discounts_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    """Show discount terms and safe redemption history; raw promo codes stay out of UI."""
    subscription = None
    if db is not None:
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
    billing_owner = _can_manage_billing(
        role=await _billing_role(db, tenant_scope=tenant_scope, principal=principal),
        subscription=subscription,
        principal=principal,
    )
    if not billing_owner:
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    now = datetime.now(UTC)
    active_promotions: list[dict[str, str]] = []
    redemptions: list[dict[str, str]] = []
    if db is not None:
        campaigns = await db.scalars(
            select(PromotionCampaign)
            .where(PromotionCampaign.enabled.is_(True))
            .order_by(PromotionCampaign.created_at.desc())
            .limit(20)
        )
        for campaign in campaigns:
            if campaign.starts_at is not None and campaign.starts_at > now:
                continue
            if campaign.ends_at is not None and campaign.ends_at <= now:
                continue
            active_promotions.append(
                {
                    "discount_label": f"Скидка {campaign.discount_percent}% на «Личный»",
                    "expiry_label": _billing_datetime_label(campaign.ends_at)
                    if campaign.ends_at
                    else "срок не ограничен",
                }
            )
        rows = await db.execute(
            select(PromotionRedemption, PromotionCampaign)
            .join(PromotionCampaign, PromotionCampaign.id == PromotionRedemption.campaign_id)
            .where(PromotionRedemption.workspace_id == tenant_scope.workspace_id)
            .order_by(PromotionRedemption.reserved_at.desc())
            .limit(100)
        )
        for redemption, campaign in rows:
            redemptions.append(
                {
                    "discount_label": f"Скидка {redemption.discount_percent}%",
                    "state_label": _promotion_state_label(redemption.state),
                    "cycle_label": "Год" if campaign.cycle == "year" else "Месяц",
                }
            )
    content = _page_shell(
        "Скидки",
        embedded=_is_embedded_request(request),
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_discounts", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_discounts_content.html",
        active_promotions=active_promotions,
        redemptions=redemptions,
        billing_owner=billing_owner,
        billing_enabled=bool(request.app.state.settings.billing_checkout_enabled),
        checkout_promo_active=bool(request.cookies.get(_CHECKOUT_PROMO_COOKIE)),
        result=request.query_params.get("result"),
    )
    return cabinet_html_response(content)


@router.post("/billing/discounts/apply", response_class=HTMLResponse, include_in_schema=False)
async def apply_billing_discount(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
    promo_code: str | None = Form(default=None, max_length=48),
) -> RedirectResponse:
    """Validate a code without reserving it; reservation belongs to checkout."""
    subscription = (
        await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
        if db is not None
        else None
    )
    if db is None or not _can_manage_billing(
        role=await _billing_role(db, tenant_scope=tenant_scope, principal=principal),
        subscription=subscription,
        principal=principal,
    ):
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    limited = await _billing_rate_limited_response(
        request,
        tenant_scope=tenant_scope,
        principal=principal,
        action="billing_promo_action",
    )
    if limited is not None:
        return limited
    try:
        normalized = normalize_promo(promo_code or "")
    except PromoError:
        return RedirectResponse("/billing/discounts?result=invalid", status_code=303)
    campaign = await db.scalar(
        select(PromotionCampaign).where(
            PromotionCampaign.code_hash == promo_code_hash(normalized),
            PromotionCampaign.enabled.is_(True),
        )
    )
    if campaign is None:
        return RedirectResponse("/billing/discounts?result=invalid", status_code=303)
    now = datetime.now(UTC)
    if (campaign.starts_at is not None and campaign.starts_at > now) or (
        campaign.ends_at is not None and campaign.ends_at <= now
    ):
        return RedirectResponse("/billing/discounts?result=invalid", status_code=303)
    return _checkout_result_redirect(request, "promo_applied", promo_code=normalized)


@router.post("/billing/discounts/remove", response_class=HTMLResponse, include_in_schema=False)
async def remove_billing_discount(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    subscription = (
        await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
        if db is not None
        else None
    )
    if db is None or not _can_manage_billing(
        role=await _billing_role(db, tenant_scope=tenant_scope, principal=principal),
        subscription=subscription,
        principal=principal,
    ):
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    limited = await _billing_rate_limited_response(
        request,
        tenant_scope=tenant_scope,
        principal=principal,
        action="billing_promo_action",
    )
    if limited is not None:
        return limited
    response = RedirectResponse("/billing/discounts?result=removed", status_code=303)
    response.delete_cookie(_CHECKOUT_PROMO_COOKIE, path="/billing/checkout")
    return response


@router.get(
    "/billing/checkout/status/{safe_number}", response_class=HTMLResponse, include_in_schema=False
)
async def billing_checkout_status_page(
    safe_number: str,
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    """Render a workspace-scoped payment timeline without calling YooKassa from the browser."""
    subscription = None
    invoice = None
    operation = None
    if db is not None:
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
        invoice = await db.scalar(
            select(BillingInvoice).where(
                BillingInvoice.workspace_id == tenant_scope.workspace_id,
                BillingInvoice.safe_number == safe_number,
            )
        )
        if invoice is not None:
            operation = await db.scalar(
                select(BillingOperation).where(
                    BillingOperation.workspace_id == tenant_scope.workspace_id,
                    BillingOperation.id == invoice.operation_id,
                )
            )
    if not _can_manage_billing(
        role=await _billing_role(db, tenant_scope=tenant_scope, principal=principal),
        subscription=subscription,
        principal=principal,
    ):
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    if invoice is None:
        return RedirectResponse("/billing/history?result=not_found", status_code=303)
    operation_state = operation.state if operation is not None else None
    settings = request.app.state.settings
    operation_actor = (
        operation.request_snapshot.get("billing_actor_user_id")
        if operation is not None
        else None
    )
    actor_matches = operation_actor in {None, str(principal.user_id)}
    can_continue_payment = bool(
        operation is not None
        and settings.billing_checkout_enabled
        and not settings.billing_emergency_stop
        and actor_matches
        and _initial_checkout_can_continue(operation)
    )
    can_refresh_payment = bool(
        operation is not None
        and operation.provider_id is not None
        and operation.kind == "initial_checkout"
        and operation.state in {"provider_pending", "unknown"}
    )
    content = _page_shell(
        "Статус платежа",
        embedded=_is_embedded_request(request),
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_checkout_status", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_operation_status_content.html",
        invoice={
            "safe_number": invoice.safe_number,
            "created_at_label": _billing_datetime_label(invoice.created_at),
        },
        amount_label=_billing_amount_label(invoice.amount_minor, invoice.currency)
        or "Сумма недоступна",
        operation_state=operation_state,
        operation_state_label=_operation_state_label(operation_state),
        billing_enabled=bool(settings.billing_checkout_enabled),
        can_continue_payment=can_continue_payment,
        can_refresh_payment=can_refresh_payment,
        updated_at_label=_billing_datetime_label(
            operation.updated_at if operation is not None else None
        ),
        status_result=request.query_params.get("result"),
    )
    return cabinet_html_response(content)


@router.post(
    "/billing/checkout/status/{safe_number}/refresh",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def refresh_billing_checkout_status(
    safe_number: str,
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    """Refresh one hosted checkout from provider truth without opening a new payment."""
    if db is None:
        return RedirectResponse(
            f"/billing/checkout/status/{quote(safe_number, safe='-')}?result=unavailable",
            status_code=303,
        )
    limited = await _billing_rate_limited_response(
        request,
        tenant_scope=tenant_scope,
        principal=principal,
        action="billing_status_refresh",
    )
    if limited is not None:
        return limited
    invoice = await db.scalar(
        select(BillingInvoice).where(
            BillingInvoice.workspace_id == tenant_scope.workspace_id,
            BillingInvoice.safe_number == safe_number,
        )
    )
    subscription = await db.scalar(
        select(WorkspaceSubscription).where(
            WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
        )
    )
    if (
        not _can_manage_billing(
            role=await _billing_role(db, tenant_scope=tenant_scope, principal=principal),
            subscription=subscription,
            principal=principal,
        )
        or invoice is None
    ):
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    counters = await reconcile_pending_initial_checkout_operations(
        db,
        request.app.state.settings,
        limit=1,
        operation_id=invoice.operation_id,
        defer_referral_reward=True,
    )
    await db.commit()
    return RedirectResponse(
        _checkout_status_location(safe_number, result=_status_refresh_result(counters)),
        status_code=303,
    )


@router.post(
    "/billing/checkout/status/{safe_number}/continue",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def continue_billing_checkout(
    safe_number: str,
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    """Continue the existing provider request identity; never create a second invoice."""
    if db is None:
        return RedirectResponse(
            _checkout_status_location(safe_number, result="unavailable"),
            status_code=303,
        )
    limited = await _billing_rate_limited_response(
        request,
        tenant_scope=tenant_scope,
        principal=principal,
        action="billing_checkout_continue",
    )
    if limited is not None:
        return limited
    invoice = await db.scalar(
        select(BillingInvoice)
        .where(
            BillingInvoice.workspace_id == tenant_scope.workspace_id,
            BillingInvoice.safe_number == safe_number,
        )
        .with_for_update()
    )
    subscription = await db.scalar(
        select(WorkspaceSubscription)
        .where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
        .with_for_update()
    )
    if (
        not _can_manage_billing(
            role=await _billing_role(db, tenant_scope=tenant_scope, principal=principal),
            subscription=subscription,
            principal=principal,
        )
        or invoice is None
    ):
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    operation = await db.scalar(
        select(BillingOperation)
        .where(
            BillingOperation.workspace_id == tenant_scope.workspace_id,
            BillingOperation.id == invoice.operation_id,
        )
        .with_for_update()
    )
    if operation is None or operation.kind != "initial_checkout":
        return RedirectResponse(
            _checkout_status_location(safe_number, result="unavailable"),
            status_code=303,
        )
    billing_actor_user_id = operation.request_snapshot.get("billing_actor_user_id")
    if billing_actor_user_id is not None and billing_actor_user_id != str(principal.user_id):
        return RedirectResponse(
            _checkout_status_location(safe_number, result="unavailable"),
            status_code=303,
        )
    settings = request.app.state.settings
    try:
        require_billing_enabled(
            checkout_enabled=bool(settings.billing_checkout_enabled),
            emergency_stop=bool(settings.billing_emergency_stop),
        )
    except BillingEmergencyStop:
        return RedirectResponse(
            _checkout_status_location(safe_number, result="unavailable"),
            status_code=303,
        )
    if billing_actor_user_id is None:
        operation.request_snapshot = {
            **operation.request_snapshot,
            "billing_actor_user_id": str(principal.user_id),
        }
        billing_actor_user_id = str(principal.user_id)
        await db.commit()
    if operation.provider_id is not None:
        confirmation_url = operation.request_snapshot.get("confirmation_url")
        return RedirectResponse(
            confirmation_url
            if is_allowed_confirmation_url(confirmation_url)
            else _checkout_status_location(safe_number, result="unchanged"),
            status_code=303,
        )
    if provider_key_is_expired(expires_at=operation.provider_key_expires_at):
        operation.state = "provider_key_expired"
        invoice.status = "manual_resolution"
        await db.commit()
        return RedirectResponse(
            _checkout_status_location(safe_number, result="continuation_expired"),
            status_code=303,
        )
    if not _initial_checkout_can_continue(operation):
        return RedirectResponse(
            _checkout_status_location(safe_number, result="unchanged"),
            status_code=303,
        )
    operation.state = "scheduled"
    invoice.status = "pending"
    await db.commit()
    try:
        return_url = billing_checkout_return_url(request, safe_invoice_number=invoice.safe_number)
        payment = await _create_initial_checkout_payment(
            settings=settings,
            operation=operation,
            invoice=invoice,
            return_url=return_url,
        )
        confirmation_url = _bind_initial_checkout_payment(operation, invoice, payment)
        if subscription is not None and subscription.billing_owner_id != principal.user_id:
            subscription.billing_owner_id = principal.user_id
        await db.commit()
        return RedirectResponse(
            confirmation_url
            if confirmation_url is not None
            else _checkout_status_location(safe_number, result="provider_unavailable"),
            status_code=303,
        )
    except (
        ValueError,
        YooKassaConfigurationError,
        YooKassaProviderError,
        httpx.HTTPError,
    ) as exc:
        await db.rollback()
        operation = await db.scalar(
            select(BillingOperation)
            .where(
                BillingOperation.workspace_id == tenant_scope.workspace_id,
                BillingOperation.id == invoice.operation_id,
            )
            .with_for_update()
        )
        invoice = await db.scalar(
            select(BillingInvoice)
            .where(
                BillingInvoice.workspace_id == tenant_scope.workspace_id,
                BillingInvoice.safe_number == safe_number,
            )
            .with_for_update()
        )
        if operation is not None and invoice is not None:
            _record_initial_checkout_failure(operation, invoice, exc)
            await db.commit()
        return RedirectResponse(
            _checkout_status_location(safe_number, result="provider_unavailable"),
            status_code=303,
        )


@router.post("/billing/trial/activate", response_class=HTMLResponse, include_in_schema=False)
async def activate_billing_trial(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
    confirmation: str | None = Form(default=None, max_length=32),
) -> RedirectResponse:
    if db is None or not principal.auth_via_session:
        return RedirectResponse("/billing?trial=unavailable", status_code=303)
    if confirmation != "start_trial":
        return RedirectResponse("/billing?trial=confirmation_required", status_code=303)
    identity = await db.scalar(
        select(UserIdentity).where(UserIdentity.id == principal.user_id).with_for_update()
    )
    await lock_storage_workspace(db, tenant_scope.workspace_id)
    eligibility_state = await _trial_eligibility_state(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
    )
    if eligibility_state == "verification_required":
        return RedirectResponse("/billing?trial=verification_required", status_code=303)
    if eligibility_state == "already":
        return RedirectResponse("/billing?trial=already", status_code=303)
    if eligibility_state != "eligible":
        return RedirectResponse("/billing?trial=unavailable", status_code=303)
    workspace = await db.scalar(
        select(Workspace).where(Workspace.id == tenant_scope.workspace_id).with_for_update()
    )
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == tenant_scope.workspace_id,
            WorkspaceMembership.user_id == principal.user_id,
            WorkspaceMembership.status == "active",
        )
    )
    if (
        workspace is None
        or workspace.kind != "personal"
        or workspace.owner_user_id != principal.user_id
        or membership is None
        or membership.role != "owner"
    ):
        return RedirectResponse("/billing?trial=unavailable", status_code=303)
    blocking_checkout = await db.scalar(
        _blocking_payment_operation_query(tenant_scope.workspace_id).limit(1)
    )
    if blocking_checkout is not None:
        return RedirectResponse("/billing?trial=pending", status_code=303)
    already_used = await trial_used_by_lineage(db, user_id=principal.user_id)
    subscription = await db.scalar(
        select(WorkspaceSubscription)
        .where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
        .with_for_update()
    )
    try:
        require_trial_activation(
            identity_status=identity.status if identity is not None else "",
            membership_role=membership.role if membership is not None else "",
            workspace_kind=workspace.kind if workspace is not None else "",
            already_used=already_used,
        )
    except PermissionError:
        return RedirectResponse("/billing?trial=unavailable", status_code=303)
    except ValueError:
        return RedirectResponse("/billing?trial=already", status_code=303)
    if subscription is not None and subscription.billing_owner_id not in {None, principal.user_id}:
        return RedirectResponse("/billing?trial=unavailable", status_code=303)
    if subscription is not None and (
        subscription.paid_through is not None
        and subscription.paid_through > datetime.now(UTC)
        or effective_plan_code(
            plan_code=subscription.plan_code,  # type: ignore[arg-type]
            state=subscription.state,
            now=datetime.now(UTC),
            paid_through=subscription.paid_through,
            trial_ends_at=subscription.trial_ends_at,
        )
        != "free"
    ):
        return RedirectResponse("/billing?trial=unavailable", status_code=303)
    now = datetime.now(UTC)
    trial = activate_trial(
        user_id=principal.user_id,
        now=now,
        policy_version="trial-v1",
        verified=True,
        eligible=True,
    )
    db.add(
        TrialActivation(
            user_id=principal.user_id,
            workspace_id=tenant_scope.workspace_id,
            starts_at=trial.starts_at,
            ends_at=trial.ends_at,
            policy_version=trial.policy_version,
        )
    )
    if subscription is None:
        db.add(
            WorkspaceSubscription(
                workspace_id=tenant_scope.workspace_id,
                billing_owner_id=principal.user_id,
                state="trial",
                plan_code="trial",
                capacity_bytes=500_000_000,
                trial_ends_at=trial.ends_at,
            )
        )
    else:
        subscription.state = "trial"
        subscription.plan_code = "trial"
        subscription.capacity_bytes = 500_000_000
        subscription.trial_ends_at = trial.ends_at
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return RedirectResponse("/billing?trial=already", status_code=303)
    return RedirectResponse("/billing?trial=activated", status_code=303)


@router.get("/billing/usage", response_class=HTMLResponse, include_in_schema=False)
async def billing_usage_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    now = datetime.now(UTC)
    subscription = None
    processing_used = 0
    processing_reserved = 0
    reserved_bytes = 0
    usage_projection_state = "unavailable" if db is None else "fresh"
    window_start, window_end = moscow_window_for(now)
    if db is not None:
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
        window = await db.scalar(
            select(FreeUsageWindow).where(
                FreeUsageWindow.workspace_id == tenant_scope.workspace_id,
                FreeUsageWindow.window_start == window_start,
            )
        )
        processing_used = window.committed_seconds if window is not None else 0
        processing_reserved = window.reserved_seconds if window is not None else 0
        usage_projection_state = window.freshness_state if window is not None else "fresh"
        reserved = await db.scalar(
            select(
                func.coalesce(
                    func.sum(
                        StorageReservation.declared_bytes - StorageReservation.committed_bytes
                    ),
                    0,
                )
            ).where(
                StorageReservation.workspace_id == tenant_scope.workspace_id,
                StorageReservation.state == "active",
                (StorageReservation.expires_at.is_(None) | (StorageReservation.expires_at > now)),
            )
        )
        reserved_bytes = int(reserved or 0)
    capacity = FREE_STORAGE_BYTES
    projection = StorageProjection(0, reserved_bytes, capacity)
    raw_plan_code = subscription.plan_code if subscription is not None else "free"
    plan_code = effective_plan_code(
        plan_code=raw_plan_code,  # type: ignore[arg-type]
        state=subscription.state if subscription is not None else "free",
        now=now,
        paid_through=subscription.paid_through if subscription is not None else None,
        trial_ends_at=subscription.trial_ends_at if subscription is not None else None,
    )
    role = await _billing_role(db, tenant_scope=tenant_scope, principal=principal)
    billing_owner = _can_manage_billing(role=role, subscription=subscription, principal=principal)
    trial_state = (
        await _trial_eligibility_state(db, tenant_scope=tenant_scope, principal=principal)
        if plan_code == "free" and billing_owner
        else "unavailable"
    )
    trial_eligible = trial_state == "eligible"
    if subscription is not None and plan_code in {"trial", "personal"}:
        capacity = subscription.capacity_bytes
    if db is not None:
        projection = await project_active_playback_storage(
            db,
            workspace_id=tenant_scope.workspace_id,
            capacity_bytes=capacity,
            reserved_bytes=reserved_bytes,
        )
    content = _page_shell(
        "Использование и хранение",
        embedded=_is_embedded_request(request),
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_usage", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_usage_content.html",
        plan_code=plan_code,
        processing_used=processing_used,
        processing_reserved=processing_reserved,
        processing_used_label=format_duration(processing_used),
        processing_reserved_label=format_duration(processing_reserved),
        free_processing_limit_label="300 минут",
        processing_threshold=classify_free_processing(
            committed_seconds=processing_used + processing_reserved
        ),
        processing_threshold_label=_processing_threshold_label(
            classify_free_processing(committed_seconds=processing_used + processing_reserved)
        ),
        processing_remaining=max(
            0, FREE_PROCESSING_SECONDS - processing_used - processing_reserved
        ),
        processing_remaining_label=format_duration(
            max(0, FREE_PROCESSING_SECONDS - processing_used - processing_reserved)
        ),
        processing_reset_at_label=window_end.astimezone(MOSCOW).strftime("%d.%m.%Y, %H:%M (МСК)"),
        trial_eligible=trial_eligible,
        billing_owner=billing_owner,
        billing_role=role,
        billing_enabled=bool(request.app.state.settings.billing_checkout_enabled),
        processing_unlimited=plan_code in {"trial", "personal"},
        storage_used=projection.used_bytes,
        storage_used_label=_capacity_label(projection.used_bytes),
        storage_reserved=projection.reserved_bytes,
        storage_reserved_label=_capacity_label(projection.reserved_bytes),
        storage_reserved_exact_label=_exact_bytes_label(projection.reserved_bytes),
        storage_available=projection.available_bytes,
        storage_available_label=_capacity_label(projection.available_bytes),
        storage_available_exact_label=_exact_bytes_label(projection.available_bytes),
        storage_capacity=projection.capacity_bytes,
        storage_capacity_label=_capacity_label(projection.capacity_bytes),
        storage_capacity_exact_label=_exact_bytes_label(projection.capacity_bytes),
        storage_used_exact_label=_exact_bytes_label(projection.used_bytes),
        storage_threshold=projection.threshold,
        storage_threshold_label=_storage_threshold_label(projection.threshold),
        usage_projection_state=usage_projection_state,
    )
    return cabinet_html_response(content)


@router.get("/billing/subscription", response_class=HTMLResponse, include_in_schema=False)
async def billing_subscription_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    subscription = None
    if db is not None:
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
    role = await _billing_role(db, tenant_scope=tenant_scope, principal=principal)
    if not _can_manage_billing(role=role, subscription=subscription, principal=principal):
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    now = datetime.now(UTC)
    active = (
        subscription is not None
        and subscription.paid_through is not None
        and subscription.paid_through > now
    )
    method_available = False
    next_charge_amount_label = None
    if db is not None and subscription is not None:
        method_available = (
            await db.scalar(
                select(BillingPaymentMethod.id).where(
                    BillingPaymentMethod.workspace_id == tenant_scope.workspace_id,
                    BillingPaymentMethod.owner_user_id == principal.user_id,
                    BillingPaymentMethod.is_default.is_(True),
                    BillingPaymentMethod.state == "active",
                    BillingPaymentMethod.verified_at.is_not(None),
                )
            )
            is not None
        )
        approved_catalog = await _approved_personal_catalog(db, now=now)
        cycle_catalog = approved_catalog.get(subscription.cycle)
        next_charge_amount_label = _billing_amount_label(
            cycle_catalog.amount_minor if cycle_catalog is not None else None
        )
    content = _page_shell(
        "Управление подпиской",
        embedded=_is_embedded_request(request),
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_subscription", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_subscription_content.html",
        subscription=subscription,
        active=active,
        paid_through_label=_billing_datetime_label(subscription.paid_through)
        if active and subscription is not None
        else None,
        method_available=method_available,
        next_charge_amount_label=next_charge_amount_label,
        billing_enabled=bool(request.app.state.settings.billing_checkout_enabled),
        subscription_plan_label=(
            plan_descriptor(
                effective_plan_code(
                    plan_code=subscription.plan_code,
                    state=subscription.state,
                    now=now,
                    paid_through=subscription.paid_through,
                    trial_ends_at=subscription.trial_ends_at,
                )
            ).label
            if subscription is not None
            else "Бесплатный"
        ),
        result=request.query_params.get("result"),
    )
    return cabinet_html_response(content)


@router.get("/billing/payment-method", response_class=HTMLResponse, include_in_schema=False)
async def billing_payment_method_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    subscription = None
    if db is not None:
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
    role = await _billing_role(db, tenant_scope=tenant_scope, principal=principal)
    if not _can_manage_billing(role=role, subscription=subscription, principal=principal):
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    method = None
    if db is not None:
        method = await db.scalar(
            select(BillingPaymentMethod).where(
                BillingPaymentMethod.workspace_id == tenant_scope.workspace_id,
                BillingPaymentMethod.owner_user_id == principal.user_id,
                BillingPaymentMethod.is_default.is_(True),
                BillingPaymentMethod.state == "active",
            )
        )
    content = _page_shell(
        "Способ оплаты",
        embedded=_is_embedded_request(request),
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_payment_method", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_payment_method_content.html",
        method_label=method.masked_label if method is not None else None,
        method_kind=method.kind if method is not None else None,
        method_kind_label=_payment_method_kind_label(method.kind if method is not None else None),
        method_present=method is not None,
        renewal_allowed=bool(subscription is not None and subscription.recurring_allowed),
        paid_until_label=_billing_datetime_label(subscription.paid_through)
        if subscription is not None
        else None,
        billing_enabled=bool(request.app.state.settings.billing_checkout_enabled),
        result=request.query_params.get("result"),
    )
    return cabinet_html_response(content)


@router.post("/billing/payment-method/delete", response_class=HTMLResponse, include_in_schema=False)
async def delete_billing_payment_method(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    """Revoke GRAF's saved-method authority; YooKassa remains merchant-owned."""
    if db is None or not principal.auth_via_session:
        return RedirectResponse("/billing/payment-method?result=unavailable", status_code=303)
    subscription = await _billing_owner_subscription(
        db, tenant_scope=tenant_scope, principal=principal
    )
    if subscription is None:
        return RedirectResponse("/billing/payment-method?result=owner_only", status_code=303)
    if subscription.recurring_allowed:
        return RedirectResponse("/billing/payment-method?result=renewal_on", status_code=303)
    method = await db.scalar(
        select(BillingPaymentMethod)
        .where(
            BillingPaymentMethod.workspace_id == tenant_scope.workspace_id,
            BillingPaymentMethod.owner_user_id == principal.user_id,
            BillingPaymentMethod.is_default.is_(True),
            BillingPaymentMethod.state == "active",
        )
        .with_for_update()
    )
    if method is None:
        return RedirectResponse("/billing/payment-method?result=none", status_code=303)
    method.state = "revoked"
    method.is_default = False
    subscription.recurring_authority_version += 1
    subscription.application_version += 1
    db.add(
        BillingAuditEvent(
            workspace_id=tenant_scope.workspace_id,
            actor_user_id=principal.user_id,
            action="payment_method.revoke_authority",
            target_kind="billing_payment_method",
            target_ref=str(method.id),
            outcome="success",
            reason_code="owner_confirmed",
            metadata_json={"authority_version": subscription.recurring_authority_version},
        )
    )
    await db.commit()
    return RedirectResponse("/billing/payment-method?result=removed", status_code=303)


@router.get("/billing/storage", response_class=HTMLResponse, include_in_schema=False)
async def billing_storage_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        content = _page_shell(
            "Увеличение хранилища",
            embedded=_is_embedded_request(request),
            active_nav="settings",
            settings_active="billing",
            csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
            product_analytics_provider=build_request_browser_provider_context(
                request, "billing_storage_addons", principal=principal, tenant_scope=tenant_scope
            ),
            content_template="cabinet/pages/billing_storage_content.html",
            current_capacity=None,
            current_capacity_label=None,
            addon_options=(),
            capacity_labels=(),
            eligible=False,
            billing_enabled=False,
            result="unavailable",
        )
        return cabinet_html_response(content)
    subscription = None
    if db is not None:
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
    role = await _billing_role(db, tenant_scope=tenant_scope, principal=principal)
    if not _can_manage_billing(role=role, subscription=subscription, principal=principal):
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    now = datetime.now(UTC)
    effective_plan = (
        effective_plan_code(
            plan_code=subscription.plan_code,
            state=subscription.state,
            now=now,
            paid_through=subscription.paid_through,
            trial_ends_at=subscription.trial_ends_at,
        )
        if subscription is not None
        else "free"
    )
    current_capacity = (
        subscription.capacity_bytes
        if subscription is not None and effective_plan in {"trial", "personal"}
        else FREE_STORAGE_BYTES
    )
    content = _page_shell(
        "Увеличение хранилища",
        embedded=_is_embedded_request(request),
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_storage_addons", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_storage_content.html",
        current_capacity=current_capacity,
        current_capacity_label=_capacity_label(current_capacity),
        addon_options=(5_000_000_000, 20_000_000_000, 100_000_000_000, 500_000_000_000),
        capacity_labels=tuple(
            _capacity_label(value)
            for value in (5_000_000_000, 20_000_000_000, 100_000_000_000, 500_000_000_000)
        ),
        eligible=effective_plan == "personal",
        billing_enabled=bool(request.app.state.settings.billing_checkout_enabled),
        result=request.query_params.get("result"),
    )
    return cabinet_html_response(content)


async def _billing_owner_subscription(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
) -> WorkspaceSubscription | None:
    workspace = await db.get(Workspace, tenant_scope.workspace_id)
    if (
        workspace is None
        or workspace.kind != "personal"
        or workspace.owner_user_id != principal.user_id
    ):
        return None
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == tenant_scope.workspace_id,
            WorkspaceMembership.user_id == principal.user_id,
            WorkspaceMembership.status == "active",
        )
    )
    if membership is None or membership.role != "owner":
        return None
    subscription = await db.scalar(
        select(WorkspaceSubscription)
        .where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
        .with_for_update()
    )
    if subscription is None or subscription.billing_owner_id not in {None, principal.user_id}:
        return None
    if subscription.billing_owner_id is None:
        subscription.billing_owner_id = principal.user_id
    return subscription


@router.post("/billing/subscription/cancel", response_class=HTMLResponse, include_in_schema=False)
async def cancel_billing_subscription(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
    expected_authority_version: int | None = Form(default=None, ge=0),
) -> RedirectResponse:
    if db is None or not principal.auth_via_session:
        return RedirectResponse("/billing/subscription?result=unavailable", status_code=303)
    subscription = await _billing_owner_subscription(
        db, tenant_scope=tenant_scope, principal=principal
    )
    if (
        subscription is None
        or subscription.paid_through is None
        or subscription.paid_through <= datetime.now(UTC)
    ):
        return RedirectResponse("/billing/subscription?result=unavailable", status_code=303)
    if not subscription.recurring_allowed:
        return RedirectResponse("/billing/subscription?result=already_cancelled", status_code=303)
    if (
        expected_authority_version is None
        or expected_authority_version != subscription.recurring_authority_version
    ):
        await db.rollback()
        return RedirectResponse("/billing/subscription?result=conflict", status_code=303)
    try:
        changed = cancel_auto_renewal(
            SubscriptionControl(
                subscription.paid_through,
                subscription.recurring_allowed,
                subscription.recurring_authority_version,
            ),
            expected_version=expected_authority_version,
        )
    except ValueError:
        await db.rollback()
        return RedirectResponse("/billing/subscription?result=conflict", status_code=303)
    subscription.recurring_allowed = changed.recurring_allowed
    subscription.recurring_authority_version = changed.authority_version
    subscription.application_version += 1
    db.add(
        BillingAuditEvent(
            workspace_id=tenant_scope.workspace_id,
            actor_user_id=principal.user_id,
            action="subscription.cancel_auto_renewal",
            target_kind="workspace_subscription",
            target_ref=str(tenant_scope.workspace_id),
            outcome="success",
            reason_code="owner_confirmed",
            metadata_json={
                "authority_version": changed.authority_version,
                "consent_at": datetime.now(UTC).isoformat(),
                "next_charge_at": subscription.paid_through.isoformat()
                if subscription.paid_through
                else None,
            },
        )
    )
    await db.commit()
    return RedirectResponse("/billing/subscription?result=cancelled", status_code=303)


@router.post("/billing/subscription/resume", response_class=HTMLResponse, include_in_schema=False)
async def resume_billing_subscription(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
    expected_authority_version: int | None = Form(default=None, ge=0),
    resume_consent: bool = Form(default=False),
) -> RedirectResponse:
    if db is None or not principal.auth_via_session:
        return RedirectResponse("/billing/subscription?result=unavailable", status_code=303)
    subscription = await _billing_owner_subscription(
        db, tenant_scope=tenant_scope, principal=principal
    )
    if subscription is None:
        return RedirectResponse("/billing/subscription?result=unavailable", status_code=303)
    if subscription.recurring_allowed:
        return RedirectResponse("/billing/subscription?result=already_active", status_code=303)
    if not resume_consent:
        return RedirectResponse("/billing/subscription?result=consent_required", status_code=303)
    if (
        expected_authority_version is None
        or expected_authority_version != subscription.recurring_authority_version
    ):
        await db.rollback()
        return RedirectResponse("/billing/subscription?result=conflict", status_code=303)
    method_exists = await db.scalar(
        select(BillingPaymentMethod.id).where(
            BillingPaymentMethod.workspace_id == tenant_scope.workspace_id,
            BillingPaymentMethod.owner_user_id == principal.user_id,
            BillingPaymentMethod.is_default.is_(True),
            BillingPaymentMethod.state == "active",
            BillingPaymentMethod.verified_at.is_not(None),
        )
    )
    if method_exists is None:
        await db.rollback()
        return RedirectResponse("/billing/subscription?result=method_required", status_code=303)
    try:
        changed = resume_auto_renewal(
            SubscriptionControl(
                subscription.paid_through,
                subscription.recurring_allowed,
                subscription.recurring_authority_version,
            ),
            expected_version=expected_authority_version,
            now=datetime.now(UTC),
        )
    except ValueError:
        await db.rollback()
        return RedirectResponse("/billing/subscription?result=unavailable", status_code=303)
    subscription.recurring_allowed = changed.recurring_allowed
    subscription.recurring_authority_version = changed.authority_version
    subscription.application_version += 1
    db.add(
        BillingAuditEvent(
            workspace_id=tenant_scope.workspace_id,
            actor_user_id=principal.user_id,
            action="subscription.resume_auto_renewal",
            target_kind="workspace_subscription",
            target_ref=str(tenant_scope.workspace_id),
            outcome="success",
            reason_code="owner_confirmed",
            metadata_json={"authority_version": changed.authority_version},
        )
    )
    await db.commit()
    return RedirectResponse("/billing/subscription?result=resumed", status_code=303)


@router.get("/billing/checkout", response_class=HTMLResponse, include_in_schema=False)
async def billing_checkout_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if await _billing_role(db, tenant_scope=tenant_scope, principal=principal) != "owner":
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    settings = request.app.state.settings
    checkout_result = request.query_params.get("result")
    blocking_operation = (
        await db.scalar(_blocking_payment_operation_query(tenant_scope.workspace_id).limit(1))
        if db is not None
        else None
    )
    if blocking_operation is not None:
        checkout_result = "pending"
    checkout_blocked = checkout_result == "pending"
    continuation_candidate = (
        blocking_operation.request_snapshot.get("confirmation_url")
        if blocking_operation is not None
        and blocking_operation.kind == "initial_checkout"
        and blocking_operation.state == "provider_pending"
        and blocking_operation.request_snapshot.get("billing_actor_user_id")
        in {None, str(principal.user_id)}
        and settings.billing_checkout_enabled
        and not settings.billing_emergency_stop
        else None
    )
    checkout_continuation_url = (
        continuation_candidate if is_allowed_confirmation_url(continuation_candidate) else None
    )
    checkout_promo_code = request.cookies.get(_CHECKOUT_PROMO_COOKIE, "")
    checkout_cycle = request.query_params.get("cycle", "month")
    if checkout_cycle not in {"month", "year"}:
        checkout_cycle = "month"
    descriptor = plan_descriptor("personal")
    receipt_contact = (
        await db.scalar(
            select(ExternalIdentity.email)
            .where(
                ExternalIdentity.user_id == principal.user_id,
                ExternalIdentity.is_active.is_(True),
                ExternalIdentity.is_verified.is_(True),
                ExternalIdentity.email.is_not(None),
            )
            .order_by(ExternalIdentity.created_at.asc())
        )
        if db is not None
        else None
    )
    catalog = await _approved_personal_catalog(db, now=datetime.now(UTC))
    monthly_catalog = catalog.get("month")
    annual_catalog = catalog.get("year")
    catalog_ready = monthly_catalog is not None and annual_catalog is not None
    monthly_amount = monthly_catalog.amount_minor if monthly_catalog is not None else None
    annual_amount = annual_catalog.amount_minor if annual_catalog is not None else None
    catalog_storage = (
        monthly_catalog.storage_bytes if monthly_catalog is not None else descriptor.storage_bytes
    )
    offer_version = (
        monthly_catalog.offer_version if monthly_catalog is not None else _BILLING_OFFER_VERSION
    )
    checkout_preview_data: dict[str, str] | None = None
    promo_preview_error: str | None = None
    selected_catalog = catalog.get(checkout_cycle)
    if (
        not checkout_blocked
        and bool(settings.billing_checkout_enabled)
        and selected_catalog is not None
    ):
        try:
            promo = None
            if checkout_promo_code:
                promo, _ = await _load_checkout_promo(
                    db,
                    workspace_id=tenant_scope.workspace_id,
                    raw_code=checkout_promo_code,
                    cycle=checkout_cycle,
                    now=datetime.now(UTC),
                )
            referral_candidate, _, _ = await _checkout_referral_candidate(
                db,
                request=request,
                tenant_scope=tenant_scope,
                principal=principal,
            )
            chosen, discount_source = _choose_checkout_discount(
                amount_minor=selected_catalog.amount_minor or 0,
                cycle=checkout_cycle,
                provider_floor_minor=settings.billing_provider_floor_minor,
                promo=promo,
                referral_candidate=referral_candidate,
            )
            checkout_preview_data = checkout_preview_labels(
                checkout_preview(
                    plan_code="personal",
                    cycle=checkout_cycle,
                    promo=chosen,
                    provider_floor_minor=settings.billing_provider_floor_minor,
                    catalog_snapshot=selected_catalog,
                ),
                discount_percent=chosen.discount_percent if chosen is not None else None,
                discount_source=discount_source,
            )
        except PromoError as exc:
            promo_preview_error = str(exc)
        except ValueError:
            promo_preview_error = "Промокод временно недоступен. Проверьте код позже."
    content = _page_shell(
        "Выбор тарифа",
        embedded=_is_embedded_request(request),
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request,
            "billing_checkout",
            principal=principal,
            tenant_scope=tenant_scope,
        ),
        content_template="cabinet/pages/billing_checkout_content.html",
        billing_enabled=bool(settings.billing_checkout_enabled),
        plan=descriptor,
        monthly_price_label=_billing_price_label(monthly_amount),
        annual_price_label=_billing_price_label(annual_amount),
        annual_saving_label=_annual_saving_label(monthly_amount, annual_amount),
        catalog_ready=catalog_ready,
        catalog_storage_label=_capacity_label(catalog_storage),
        offer_version_label=offer_version,
        checkout_idempotency_key=f"web-{principal.user_id}-{uuid4().hex}",
        checkout_result=checkout_result,
        checkout_blocked=checkout_blocked,
        checkout_continuation_url=checkout_continuation_url,
        checkout_promo_code=checkout_promo_code,
        checkout_cycle=checkout_cycle,
        checkout_preview=checkout_preview_data,
        promo_preview_error=promo_preview_error,
        receipt_contact_label=_masked_receipt_contact(receipt_contact),
    )
    response = cabinet_html_response(content)
    if checkout_promo_code:
        response.delete_cookie(_CHECKOUT_PROMO_COOKIE, path="/billing/checkout")
    return response


@router.post("/billing/checkout/preview", response_class=HTMLResponse, include_in_schema=False)
async def preview_billing_checkout(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
    cycle: str = Form(default="month", max_length=16),
    promo_code: str | None = Form(default=None, max_length=48),
) -> RedirectResponse:
    """Validate a promo and show its price without reserving or charging."""
    settings = request.app.state.settings
    if db is None or not settings.billing_checkout_enabled or settings.billing_emergency_stop:
        return RedirectResponse("/billing/checkout?result=unavailable", status_code=303)
    if await _billing_role(db, tenant_scope=tenant_scope, principal=principal) != "owner":
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    limited = await _billing_rate_limited_response(
        request,
        tenant_scope=tenant_scope,
        principal=principal,
        action="billing_checkout_preview",
    )
    if limited is not None:
        return limited
    if cycle not in {"month", "year"}:
        return _checkout_result_redirect(request, "promo_invalid", promo_code=promo_code)
    try:
        catalog = await _approved_personal_catalog(db, now=datetime.now(UTC))
        catalog_snapshot = catalog.get(cycle)
        if catalog_snapshot is None:
            return _checkout_result_redirect(request, "catalog_not_approved", cycle=cycle)
        if not (promo_code or "").strip():
            return _checkout_result_redirect(request, "promo_applied", cycle=cycle)
        entered_promo, _ = await _load_checkout_promo(
            db,
            workspace_id=tenant_scope.workspace_id,
            raw_code=promo_code or "",
            cycle=cycle,
            now=datetime.now(UTC),
        )
        referral_candidate, _, _ = await _checkout_referral_candidate(
            db,
            request=request,
            tenant_scope=tenant_scope,
            principal=principal,
        )
        promo, _ = _choose_checkout_discount(
            amount_minor=catalog_snapshot.amount_minor or 0,
            cycle=cycle,
            provider_floor_minor=settings.billing_provider_floor_minor,
            promo=entered_promo,
            referral_candidate=referral_candidate,
        )
        checkout_preview(
            plan_code="personal",
            cycle=cycle,
            promo=promo,
            provider_floor_minor=settings.billing_provider_floor_minor,
            catalog_snapshot=catalog_snapshot,
        )
    except (PromoError, ValueError):
        return _checkout_result_redirect(
            request,
            "promo_invalid",
            promo_code=promo_code,
            cycle=cycle,
        )
    return _checkout_result_redirect(
        request,
        "promo_applied",
        promo_code=entered_promo.code,
        cycle=cycle,
    )


@router.post("/billing/checkout/start", response_class=HTMLResponse, include_in_schema=False)
async def start_billing_checkout(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
    cycle: str = Form(default="month", max_length=16),
    idempotency_key: str = Form(default="", max_length=240),
    offer_consent: bool = Form(default=False),
    recurring_consent: bool = Form(default=False),
    promo_code: str | None = Form(default=None, max_length=48),
) -> RedirectResponse:
    settings = request.app.state.settings
    if db is None:
        return RedirectResponse("/billing/checkout?result=unavailable", status_code=303)
    # Keep the narrow rate-limit transaction ahead of workspace row locks.
    # Otherwise its FK insert can wait on this transaction's FOR UPDATE lock
    # and deadlock the checkout request against itself.
    limited = await _billing_rate_limited_response(
        request,
        tenant_scope=tenant_scope,
        principal=principal,
        action="billing_checkout_start",
    )
    if limited is not None:
        return limited
    try:
        workspace = await db.scalar(
            select(Workspace).where(Workspace.id == tenant_scope.workspace_id).with_for_update()
        )
        if (
            workspace is None
            or workspace.kind != "personal"
            or workspace.owner_user_id != principal.user_id
        ):
            return RedirectResponse("/billing?result=personal_only", status_code=303)
        membership = await db.scalar(
            select(WorkspaceMembership)
            .where(
                WorkspaceMembership.workspace_id == tenant_scope.workspace_id,
                WorkspaceMembership.user_id == principal.user_id,
                WorkspaceMembership.status == "active",
            )
            .with_for_update()
        )
        subscription = await db.scalar(
            select(WorkspaceSubscription)
            .where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
            .with_for_update()
        )
        if membership is None or membership.role != "owner":
            return RedirectResponse("/billing/checkout?result=owner_only", status_code=303)
        receipt_contact = await db.scalar(
            select(ExternalIdentity.email)
            .where(
                ExternalIdentity.user_id == principal.user_id,
                ExternalIdentity.is_active.is_(True),
                ExternalIdentity.is_verified.is_(True),
                ExternalIdentity.email.is_not(None),
            )
            .order_by(ExternalIdentity.created_at.asc())
        )
        require_billing_enabled(
            checkout_enabled=bool(settings.billing_checkout_enabled),
            emergency_stop=bool(settings.billing_emergency_stop),
        )
        key = idempotency_key.strip()
        if not key:
            return RedirectResponse("/billing/checkout?result=invalid", status_code=303)
        if not offer_consent:
            return RedirectResponse("/billing/checkout?result=offer_required", status_code=303)
        if not recurring_consent:
            return RedirectResponse("/billing/checkout?result=consent_required", status_code=303)

        # Idempotency recovery must not re-run mutable promo/referral checks.
        # A retried request can carry the same reservation and should recover
        # the original hosted URL even after the campaign window changed.
        existing = await db.scalar(
            select(BillingOperation)
            .where(
                BillingOperation.workspace_id == tenant_scope.workspace_id,
                BillingOperation.idempotency_key == key,
            )
            .with_for_update()
        )
        if existing is not None:
            confirmation_url = existing.request_snapshot.get("confirmation_url")
            if is_allowed_confirmation_url(confirmation_url):
                return RedirectResponse(confirmation_url, status_code=303)
            existing_invoice = await db.scalar(
                select(BillingInvoice).where(BillingInvoice.operation_id == existing.id)
            )
            if existing_invoice is not None:
                return RedirectResponse(
                    _checkout_status_location(existing_invoice.safe_number),
                    status_code=303,
                )
            return RedirectResponse("/billing?result=pending", status_code=303)
        now = datetime.now(UTC)
        if (
            subscription is not None
            and subscription.plan_code == "personal"
            and subscription.paid_through is not None
            and subscription.paid_through.astimezone(UTC) > now
        ):
            return RedirectResponse("/billing?result=already_active", status_code=303)

        # New money mutation must use an enabled, effective database catalog
        # row.  Static descriptors remain useful for read-only copy and unit
        # tests, but are never a checkout authority once the billing DB is
        # available.  An absent/stale/disabled row therefore fails closed.
        catalog_rows = await db.scalars(
            select(BillingPlanVersion)
            .where(
                BillingPlanVersion.plan_code == "personal",
                BillingPlanVersion.cycle == cycle,
            )
            .order_by(BillingPlanVersion.version.desc())
        )
        catalog_snapshot = None
        for catalog_row in catalog_rows:
            try:
                catalog_snapshot = validate_plan_version(catalog_row, now=now)
                break
            except (CatalogNotApproved, ValueError):
                continue
        if catalog_snapshot is None:
            return RedirectResponse(
                "/billing/checkout?result=catalog_not_approved", status_code=303
            )

        promo: PromoCode | None = None
        promo_campaign: PromotionCampaign | None = None
        if promo_code and promo_code.strip():
            try:
                promo, promo_campaign = await _load_checkout_promo(
                    db,
                    workspace_id=tenant_scope.workspace_id,
                    raw_code=promo_code,
                    cycle=cycle,
                    now=datetime.now(UTC),
                    lock=True,
                )
            except (PromoError, ValueError):
                return _checkout_result_redirect(
                    request,
                    "promo_invalid",
                    promo_code=promo_code,
                    cycle=cycle,
                )
        # Referral attribution belongs to the inviter's workspace, while the
        # invitee is now paying from a different personal workspace. The
        # helper restores the request tenant context before any mutation.
        referral_candidate, referred, lineage_ids = await _checkout_referral_candidate(
            db,
            request=request,
            tenant_scope=tenant_scope,
            principal=principal,
        )
        # Exactly one discount may reach the immutable invoice.  Prefer the
        # lower payable amount and keep configured-promo first for deterministic
        # tie handling; the DB reservation is created only for the winner.
        try:
            chosen, _ = _choose_checkout_discount(
                amount_minor=catalog_snapshot.amount_minor or 0,
                cycle=cycle,
                provider_floor_minor=settings.billing_provider_floor_minor,
                promo=promo,
                referral_candidate=referral_candidate,
            )
        except PromoError:
            await db.rollback()
            return _checkout_result_redirect(
                request,
                "promo_invalid",
                promo_code=promo_code,
                cycle=cycle,
            )
        configured_promo = promo
        promo = chosen
        if configured_promo is not promo:
            # A referral winner has no PromotionCampaign row and must never
            # create a redemption against the entered campaign.
            promo_campaign = None
        referral_discount = promo is referral_candidate and referral_candidate is not None
        if (
            referral_discount
            and referred is not None
            and referred.invitee_user_id in lineage_ids
            and referred.state in {"bound", "registered"}
        ):
            # The invitee owns this transition; the reward itself is created
            # later by maintenance in the inviter workspace.
            await apply_tenant_context(
                db,
                AuthReferralUserLookupContext(user_id=referred.invitee_user_id),
            )
            try:
                await db.execute(
                    update(ReferralAttribution)
                    .where(
                        ReferralAttribution.id == referred.id,
                        ReferralAttribution.invitee_user_id == referred.invitee_user_id,
                        ReferralAttribution.state.in_(("bound", "registered")),
                    )
                    .values(state="attributed")
                )
            finally:
                await apply_tenant_scope(db, tenant_scope)
        preview = checkout_preview(
            plan_code="personal",
            cycle=cycle,
            promo=promo,
            provider_floor_minor=settings.billing_provider_floor_minor,
            catalog_snapshot=catalog_snapshot,
        )
        unresolved_payment = await db.scalar(
            _blocking_payment_operation_query(tenant_scope.workspace_id).with_for_update()
        )
        if unresolved_payment is not None:
            confirmation_url = unresolved_payment.request_snapshot.get("confirmation_url")
            if is_allowed_confirmation_url(confirmation_url):
                return RedirectResponse(confirmation_url, status_code=303)
            unresolved_invoice = await db.scalar(
                select(BillingInvoice).where(BillingInvoice.operation_id == unresolved_payment.id)
            )
            if unresolved_invoice is not None:
                return RedirectResponse(
                    _checkout_status_location(unresolved_invoice.safe_number),
                    status_code=303,
                )
            return RedirectResponse("/billing?result=pending", status_code=303)
        provider_environment(settings.billing_yookassa_environment)
        intent = build_checkout_intent(
            workspace_id=tenant_scope.workspace_id, idempotency_key=key, preview=preview
        )
        consent_at = datetime.now(UTC).isoformat()
        operation = BillingOperation(
            id=intent.operation_id,
            workspace_id=tenant_scope.workspace_id,
            kind="initial_checkout",
            idempotency_key=intent.idempotency_key,
            state="scheduled",
            provider_key_expires_at=datetime.now(UTC) + timedelta(hours=24),
            request_snapshot={
                "plan_code": preview.plan_code,
                "cycle": preview.cycle,
                "list_amount_minor": preview.list_amount_minor,
                "payable_amount_minor": preview.payable_amount_minor,
                "promo_code_hash": promo_code_hash(promo.code) if promo is not None else None,
                "discount_percent": promo.discount_percent if promo is not None else None,
                "referral_discount": referral_discount,
                "discount_source": "referral"
                if referral_discount
                else ("promo" if promo is not None else None),
                "catalog_snapshot": catalog_snapshot.as_dict(),
                "offer_consent": True,
                "recurring_consent": True,
                "consent_at": consent_at,
                "billing_actor_user_id": str(principal.user_id),
                "offer_version": catalog_snapshot.offer_version,
                "receipt_config": {
                    "tax_system_code": settings.billing_receipt_tax_system_code,
                    "vat_code": settings.billing_receipt_vat_code,
                    "payment_subject": settings.billing_receipt_payment_subject,
                    "payment_mode": settings.billing_receipt_payment_mode,
                },
            },
        )
        db.add(operation)
        await db.flush()
        invoice = BillingInvoice(
            workspace_id=tenant_scope.workspace_id,
            operation_id=intent.operation_id,
            safe_number=intent.invoice_number,
            amount_minor=preview.payable_amount_minor,
            plan_snapshot={
                "plan_code": preview.plan_code,
                "cycle": preview.cycle,
                "list_amount_minor": preview.list_amount_minor,
                "payable_amount_minor": preview.payable_amount_minor,
                "promo_code_hash": promo_code_hash(promo.code) if promo is not None else None,
                "discount_percent": promo.discount_percent if promo is not None else None,
                "campaign_version": promo.campaign_version if promo is not None else None,
                "referral_discount": referral_discount,
                "discount_source": "referral"
                if referral_discount
                else ("promo" if promo is not None else None),
                "catalog_snapshot": catalog_snapshot.as_dict(),
                "offer_consent": True,
                "recurring_consent": True,
                "consent_at": consent_at,
                "billing_actor_user_id": str(principal.user_id),
                "offer_version": catalog_snapshot.offer_version,
            },
            receipt_contact_snapshot=receipt_contact if isinstance(receipt_contact, str) else None,
        )
        db.add(invoice)
        await db.flush()
        if promo is not None and promo_campaign is not None:
            redemption = await db.scalar(
                select(PromotionRedemption)
                .where(
                    PromotionRedemption.workspace_id == tenant_scope.workspace_id,
                    PromotionRedemption.campaign_id == promo_campaign.id,
                )
                .with_for_update()
            )
            if redemption is not None and redemption.state not in {"released", "expired"}:
                await db.rollback()
                return _checkout_result_redirect(request, "promo_invalid", promo_code=promo_code)
            if redemption is None:
                redemption = PromotionRedemption(
                    campaign_id=promo_campaign.id,
                    workspace_id=tenant_scope.workspace_id,
                    invoice_id=invoice.id,
                    reservation_key=key,
                    code_hash=promo_code_hash(promo.code),
                    list_amount_minor=preview.list_amount_minor,
                    payable_amount_minor=preview.payable_amount_minor,
                    discount_percent=promo.discount_percent,
                    state="reserved",
                    expires_at=datetime.now(UTC) + timedelta(minutes=15),
                )
                db.add(redemption)
            else:
                redemption.invoice_id = invoice.id
                redemption.reservation_key = key
                redemption.code_hash = promo_code_hash(promo.code)
                redemption.list_amount_minor = preview.list_amount_minor
                redemption.payable_amount_minor = preview.payable_amount_minor
                redemption.discount_percent = promo.discount_percent
                redemption.state = "reserved"
                redemption.expires_at = datetime.now(UTC) + timedelta(minutes=15)
                redemption.released_at = None
                redemption.redeemed_at = None
        await db.commit()
        return_url = billing_checkout_return_url(request, safe_invoice_number=intent.invoice_number)
        payment = await _create_initial_checkout_payment(
            settings=settings,
            operation=operation,
            invoice=invoice,
            return_url=return_url,
        )
        confirmation_url = _bind_initial_checkout_payment(operation, invoice, payment)
        if subscription is not None and subscription.billing_owner_id != principal.user_id:
            # An owner who replaced the designated billing owner must make a
            # fresh hosted payment before future renewals can use this account.
            subscription.billing_owner_id = principal.user_id
        await db.commit()
        return RedirectResponse(
            confirmation_url
            if confirmation_url is not None
            else _checkout_status_location(intent.invoice_number, result="provider_unavailable"),
            status_code=303,
        )
    except IntegrityError:
        # A concurrent request may have won the unique workspace/key race.
        # Recover that operation by its logical idempotency key instead of
        # returning a second checkout attempt or mutating the winner.
        await db.rollback()
        winner = (
            await db.scalar(
                select(BillingOperation)
                .where(
                    BillingOperation.workspace_id == tenant_scope.workspace_id,
                    BillingOperation.idempotency_key == key,
                )
                .with_for_update()
            )
            if "key" in locals()
            else None
        )
        if winner is not None:
            winner_url = winner.request_snapshot.get("confirmation_url")
            if is_allowed_confirmation_url(winner_url):
                return RedirectResponse(winner_url, status_code=303)
            winner_invoice = await db.scalar(
                select(BillingInvoice).where(BillingInvoice.operation_id == winner.id)
            )
            if winner_invoice is not None:
                return RedirectResponse(
                    _checkout_status_location(winner_invoice.safe_number),
                    status_code=303,
                )
            return RedirectResponse("/billing?result=pending", status_code=303)
        return RedirectResponse("/billing/checkout?result=unavailable", status_code=303)
    except (
        BillingEmergencyStop,
        ValueError,
        YooKassaConfigurationError,
        YooKassaProviderError,
        httpx.HTTPError,
    ) as exc:
        await db.rollback()
        if "intent" in locals():
            unresolved = await db.scalar(
                select(BillingOperation)
                .where(
                    BillingOperation.workspace_id == tenant_scope.workspace_id,
                    BillingOperation.id == intent.operation_id,
                )
                .with_for_update()
            )
            if unresolved is not None:
                invoice = await db.scalar(
                    select(BillingInvoice)
                    .where(BillingInvoice.operation_id == unresolved.id)
                    .with_for_update()
                )
                if invoice is not None:
                    _record_initial_checkout_failure(unresolved, invoice, exc)
                    await db.commit()
                    return RedirectResponse(
                        _checkout_status_location(
                            invoice.safe_number,
                            result="provider_unavailable",
                        ),
                        status_code=303,
                    )
        return RedirectResponse("/billing/checkout?result=unavailable", status_code=303)


@router.get("/billing/checkout/return", name="billing_checkout_return", include_in_schema=False)
async def billing_checkout_return(invoice: str | None = None) -> RedirectResponse:
    if invoice is not None and re.fullmatch(r"INV-[A-Z0-9]+", invoice):
        return RedirectResponse(
            f"/billing/checkout/status/{quote(invoice, safe='-')}", status_code=303
        )
    return RedirectResponse("/billing?result=returned", status_code=303)


@router.get("/billing/history", response_class=HTMLResponse, include_in_schema=False)
async def billing_history_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    subscription = None
    if db is not None:
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
    if not _can_manage_billing(
        role=await _billing_role(db, tenant_scope=tenant_scope, principal=principal),
        subscription=subscription,
        principal=principal,
    ):
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    invoices: list[dict[str, object]] = []
    if db is not None:
        rows = await db.scalars(
            select(BillingInvoice)
            .where(BillingInvoice.workspace_id == tenant_scope.workspace_id)
            .order_by(BillingInvoice.created_at.desc())
            .limit(100)
        )
        for invoice in rows:
            snapshot = invoice.plan_snapshot if isinstance(invoice.plan_snapshot, dict) else {}
            receipt_state = _receipt_registration_state(snapshot.get("receipt_registration"))
            refund_mailto = None
            if request.app.state.settings.billing_support_email:
                try:
                    refund_mailto = build_refund_mailto(
                        support_email=request.app.state.settings.billing_support_email,
                        safe_invoice_number=invoice.safe_number,
                    )
                except ValueError:
                    refund_mailto = None
            invoices.append(
                {
                    "safe_number": invoice.safe_number,
                    "created_at_label": _billing_datetime_label(invoice.created_at),
                    "amount_label": _billing_amount_label(invoice.amount_minor, invoice.currency)
                    or "Сумма недоступна",
                    "status": invoice.status,
                    "status_label": _invoice_status_label(invoice.status),
                    "cycle_label": "Год" if snapshot.get("cycle") == "year" else "Месяц",
                    "discount_label": (
                        f"Скидка {snapshot.get('discount_percent')}%"
                        if isinstance(snapshot.get("discount_percent"), int)
                        else ("Реферальная скидка" if snapshot.get("referral_discount") else None)
                    ),
                    "payment_method_label": mask_payment_method(
                        snapshot.get("payment_method_label")
                        if isinstance(snapshot.get("payment_method_label"), str)
                        else None
                    ),
                    "receipt_label": receipt_label(receipt_state),
                    "detail_url": f"/billing/invoices/{invoice.safe_number}",
                    "refund_mailto": refund_mailto,
                }
            )
    content = _page_shell(
        "История платежей",
        embedded=_is_embedded_request(request),
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request,
            "billing_history",
            principal=principal,
            tenant_scope=tenant_scope,
        ),
        content_template="cabinet/pages/billing_history_content.html",
        invoices=invoices,
        support_email=request.app.state.settings.billing_support_email,
    )
    return cabinet_html_response(content)


@router.get("/billing/invoices/{safe_number}", response_class=HTMLResponse, include_in_schema=False)
async def billing_invoice_detail_page(
    safe_number: str,
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    subscription = None
    if db is not None:
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
    if not _can_manage_billing(
        role=await _billing_role(db, tenant_scope=tenant_scope, principal=principal),
        subscription=subscription,
        principal=principal,
    ):
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    invoice = None
    if db is not None:
        invoice = await db.scalar(
            select(BillingInvoice).where(
                BillingInvoice.workspace_id == tenant_scope.workspace_id,
                BillingInvoice.safe_number == safe_number,
            )
        )
    if invoice is None:
        return RedirectResponse("/billing/history?result=not_found", status_code=303)
    snapshot = invoice.plan_snapshot if isinstance(invoice.plan_snapshot, dict) else {}
    receipt_state = _receipt_registration_state(snapshot.get("receipt_registration"))
    receipt_url = snapshot.get("receipt_url") if receipt_state is ReceiptState.AVAILABLE else None
    if not is_allowed_confirmation_url(receipt_url):
        receipt_url = None
    refund_mailto = None
    support_email = request.app.state.settings.billing_support_email
    if support_email:
        try:
            refund_mailto = build_refund_mailto(
                support_email=support_email, safe_invoice_number=invoice.safe_number
            )
        except ValueError:
            refund_mailto = None
    content = _page_shell(
        "Платёж",
        embedded=_is_embedded_request(request),
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_invoice", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_invoice_content.html",
        invoice={
            "safe_number": invoice.safe_number,
            "created_at": invoice.created_at,
            "amount_label": _billing_amount_label(invoice.amount_minor, invoice.currency)
            or "Сумма недоступна",
            "status": invoice.status,
            "cycle_label": "Год" if snapshot.get("cycle") == "year" else "Месяц",
            "status_label": _invoice_status_label(invoice.status),
            "discount_label": (
                f"Скидка {snapshot.get('discount_percent')}%"
                if isinstance(snapshot.get("discount_percent"), int)
                else ("Реферальная скидка" if snapshot.get("referral_discount") else None)
            ),
            "payment_method_label": mask_payment_method(
                snapshot.get("payment_method_label")
                if isinstance(snapshot.get("payment_method_label"), str)
                else None
            ),
            "receipt_contact_label": _masked_receipt_contact(invoice.receipt_contact_snapshot),
            "receipt_label": receipt_label(receipt_state),
            "receipt_url": receipt_url,
            "refund_mailto": refund_mailto,
        },
        support_email=support_email,
    )
    return cabinet_html_response(content)
