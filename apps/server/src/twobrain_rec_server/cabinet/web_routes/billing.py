from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlencode, urlsplit
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.rate_limit import enforce_auth_rate_limits
from twobrain_rec_server.billing.catalog import (
    FREE_PROCESSING_SECONDS,
    FREE_STORAGE_BYTES,
    CatalogNotApproved,
    classify_free_processing,
    classify_storage_threshold,
    plan_descriptor,
    validate_plan_version,
)
from twobrain_rec_server.billing.checkout import build_checkout_intent, checkout_preview
from twobrain_rec_server.billing.entitlements import effective_plan_code
from twobrain_rec_server.billing.history import mask_payment_method
from twobrain_rec_server.billing.operations import (
    CHECKOUT_BLOCKING_STATES,
    BillingEmergencyStop,
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
from twobrain_rec_server.billing.receipts import ReceiptState, receipt_label
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
from twobrain_rec_server.billing.trial import activate_trial, require_trial_activation
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
from twobrain_rec_server.db.models import (
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
    AuthReferralLookupContext,
    AuthReferralUserLookupContext,
    apply_tenant_context,
    apply_tenant_scope,
)
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])

_CHECKOUT_PROMO_COOKIE = "graf_checkout_promo"
_CHECKOUT_PROMO_COOKIE_MAX_AGE = 5 * 60
_BILLING_OFFER_VERSION = "billing-personal-v1"


def _checkout_result_redirect(
    request: Request,
    result: str,
    *,
    promo_code: str | None = None,
) -> RedirectResponse:
    """Keep only the recoverable checkout field across a result redirect.

    The cookie is short-lived, HttpOnly and scoped to checkout routes. Promo
    codes are not financial identifiers, but they still must not enter a URL
    query string where browser history, referrer or analytics could capture
    them.
    """

    response = RedirectResponse(f"/billing/checkout?result={result}", status_code=303)
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
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise YooKassaConfigurationError("billing public callback URL is invalid")
    path = request.app.url_path_for("billing_checkout_return")
    if safe_invoice_number is not None:
        if re.fullmatch(r"INV-[A-Z0-9]+", safe_invoice_number) is None:
            raise YooKassaConfigurationError("billing invoice reference is invalid")
        path = f"{path}?{urlencode({'invoice': safe_invoice_number})}"
    return f"{str(configured).rstrip('/')}{path}"


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
    expired = raw_plan_code == "trial" and trial_ends_at <= now and effective_plan_code_value == "free"
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
    return f"{amount_minor / 100:,.2f} {currency}".replace(",", " ")


def _billing_price_label(amount_minor: int | None) -> str | None:
    if amount_minor is None:
        return None
    if amount_minor % 100 == 0:
        return f"{amount_minor // 100:,} ₽".replace(",", " ")
    return f"{amount_minor / 100:,.2f} ₽".replace(",", " ")


def _annual_saving_label(monthly_amount_minor: int | None, annual_amount_minor: int | None) -> str | None:
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
        "unknown": "Проверяем результат платежа",
        "pending_reconciliation": "Ожидаем сверку с ЮKassa",
        "reconciliation_gap": "Нужна ручная сверка платежа",
        "manual_resolution": "Нужна ручная сверка платежа",
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
    used = await db.scalar(select(TrialActivation.id).where(TrialActivation.user_id == principal.user_id))
    if used is not None:
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
        select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
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
        subscription.paid_through is not None and subscription.paid_through > datetime.now(UTC)
        or effective_plan_code(
            plan_code=subscription.plan_code,  # type: ignore[arg-type]
            state=subscription.state,
            now=datetime.now(UTC),
            paid_through=subscription.paid_through,
            trial_ends_at=subscription.trial_ends_at,
        ) != "free"
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


@router.get("/settings/billing", include_in_schema=False)
async def settings_billing_alias() -> RedirectResponse:
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
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
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
                select(func.coalesce(func.sum(StorageReservation.declared_bytes - StorageReservation.committed_bytes), 0)).where(
                    StorageReservation.workspace_id == tenant_scope.workspace_id,
                    StorageReservation.state == "active",
                    (StorageReservation.expires_at.is_(None) | (StorageReservation.expires_at > now)),
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
        if latest_invoice is not None:
            latest_operation = await db.scalar(
                select(BillingOperation).where(
                    BillingOperation.workspace_id == tenant_scope.workspace_id,
                    BillingOperation.id == latest_invoice.operation_id,
                )
            )
        else:
            latest_operation = await db.scalar(
                select(BillingOperation)
                .where(BillingOperation.workspace_id == tenant_scope.workspace_id)
                .order_by(BillingOperation.created_at.desc())
                .limit(1)
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
        subscription.paid_through if subscription is not None and plan_code == "personal" else subscription.trial_ends_at if subscription is not None and plan_code == "trial" else None
    )
    approved_catalog = await _approved_personal_catalog(db, now=now)
    recurring_next_charge_label = None
    recurring_next_charge_amount_label = None
    if subscription is not None and plan_code == "personal" and subscription.paid_through and subscription.paid_through > now:
        if subscription.recurring_allowed:
            recurring_next_charge_label = _billing_datetime_label(subscription.paid_through)
            snapshot = latest_invoice.plan_snapshot if latest_invoice and isinstance(latest_invoice.plan_snapshot, dict) else {}
            cycle = subscription.cycle if subscription.cycle in {"month", "year"} else snapshot.get("cycle")
            catalog_entry = approved_catalog.get(cycle)
            recurring_next_charge_amount_label = _billing_amount_label(
                catalog_entry.amount_minor if catalog_entry is not None else None
            )
        else:
            recurring_next_charge_label = "не запланировано"
    elif subscription is not None and subscription.renewal_resolution in {"unknown_pending", "pending", "unknown"}:
        recurring_next_charge_label = "проверяем результат предыдущего списания"
    content = _page_shell(
        "Тариф и оплата",
        embedded=False,
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
        storage_used=storage_used,
        storage_reserved=storage_reserved,
        storage_capacity=effective_capacity,
        storage_threshold=classify_storage_threshold(
            used_bytes=storage_used,
            capacity_bytes=effective_capacity,
        ),
        processing_used=processing_used,
        processing_reserved=processing_reserved,
        processing_used_label=format_duration(processing_used),
        processing_remaining_label=format_duration(
            max(0, FREE_PROCESSING_SECONDS - processing_used - processing_reserved)
        ),
        processing_reset_at_label=window_end.astimezone(MOSCOW).strftime("%d.%m.%Y, %H:%M (МСК)"),
        free_processing_limit_label="300 минут",
        processing_usage_freshness=window.freshness_state if window is not None else ("unavailable" if db is None else "fresh"),
        billing_data_available=db is not None,
        storage_capacity_label=f"{effective_capacity:,}".replace(",", " "),
        processing_threshold=classify_free_processing(committed_seconds=processing_used + processing_reserved),
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
        latest_invoice_status_label=(
            _invoice_status_label(latest_invoice.status) if latest_invoice is not None else None
        ),
        latest_operation_label=_operation_state_label(latest_operation.state if latest_operation is not None else None),
        latest_operation_state=latest_operation.state if latest_operation is not None else None,
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
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
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
    trial_state = (
        await _trial_eligibility_state(db, tenant_scope=tenant_scope, principal=principal)
        if current_code == "free" and billing_owner
        else "unavailable"
    )
    catalog = await _approved_personal_catalog(db, now=now)
    monthly_catalog = catalog.get("month")
    annual_catalog = catalog.get("year")
    catalog_ready = monthly_catalog is not None and annual_catalog is not None
    plans = []
    for code in ("free", "trial", "personal"):
        descriptor = plan_descriptor(code)  # type: ignore[arg-type]
        monthly_amount = (
            monthly_catalog.amount_minor if code == "personal" and monthly_catalog is not None else descriptor.monthly_amount_minor
        )
        annual_amount = (
            annual_catalog.amount_minor if code == "personal" and annual_catalog is not None else descriptor.annual_amount_minor
        )
        processing_label = format_duration(FREE_PROCESSING_SECONDS) if code == "free" else "Без лимита"
        plans.append(
            {
                "code": code,
                "label": descriptor.label,
                "processing_mode": descriptor.processing_mode,
                "processing_label": processing_label,
                "storage_label": _capacity_label(
                    monthly_catalog.storage_bytes if code == "personal" and monthly_catalog is not None else descriptor.storage_bytes
                ),
                "monthly_amount_label": _billing_price_label(monthly_amount) if catalog_ready or code != "personal" else None,
                "annual_amount_label": _billing_price_label(annual_amount) if catalog_ready or code != "personal" else None,
                "annual_saving_label": _annual_saving_label(
                    monthly_amount if catalog_ready or code != "personal" else None,
                    annual_amount if catalog_ready or code != "personal" else None,
                ),
                "is_current": code == current_code,
                "catalog_ready": catalog_ready if code == "personal" else True,
            }
        )
    content = _page_shell(
        "Тарифы",
        embedded=False,
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_plans", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_plans_content.html",
        plans=plans,
        current_plan_code=current_code,
        billing_owner=billing_owner,
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
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
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
                    "expiry_label": _billing_datetime_label(campaign.ends_at) if campaign.ends_at else "срок не ограничен",
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
        embedded=False,
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
    subscription = await db.scalar(
        select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
    ) if db is not None else None
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
    subscription = await db.scalar(
        select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
    ) if db is not None else None
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


@router.get("/billing/checkout/status/{safe_number}", response_class=HTMLResponse, include_in_schema=False)
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
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
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
    content = _page_shell(
        "Статус платежа",
        embedded=False,
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
        amount_label=_billing_amount_label(invoice.amount_minor, invoice.currency) or "Сумма недоступна",
        operation_state=operation_state,
        operation_state_label=_operation_state_label(operation_state),
        updated_at_label=_billing_datetime_label(operation.updated_at if operation is not None else None),
        status_result=request.query_params.get("result"),
    )
    return cabinet_html_response(content)


@router.post("/billing/checkout/status/{safe_number}/refresh", response_class=HTMLResponse, include_in_schema=False)
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
        return RedirectResponse(f"/billing/checkout/status/{quote(safe_number, safe='-')}?result=unavailable", status_code=303)
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
        select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
    )
    if not _can_manage_billing(
        role=await _billing_role(db, tenant_scope=tenant_scope, principal=principal),
        subscription=subscription,
        principal=principal,
    ) or invoice is None:
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    await reconcile_pending_initial_checkout_operations(
        db,
        request.app.state.settings,
        limit=1,
        operation_id=invoice.operation_id,
    )
    await db.commit()
    return RedirectResponse(f"/billing/checkout/status/{quote(safe_number, safe='-')}?result=refreshed", status_code=303)


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
    identity = await db.scalar(
        select(UserIdentity)
        .where(UserIdentity.id == principal.user_id)
        .with_for_update()
    )
    existing = await db.scalar(select(TrialActivation).where(TrialActivation.user_id == principal.user_id))
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == tenant_scope.workspace_id,
            WorkspaceMembership.user_id == principal.user_id,
            WorkspaceMembership.status == "active",
        )
    )
    workspace = await db.get(Workspace, tenant_scope.workspace_id)
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
            already_used=existing is not None,
        )
    except PermissionError:
        return RedirectResponse("/billing?trial=unavailable", status_code=303)
    except ValueError:
        return RedirectResponse("/billing?trial=already", status_code=303)
    if workspace is None or workspace.owner_user_id != principal.user_id:
        return RedirectResponse("/billing?trial=unavailable", status_code=303)
    if subscription is not None and subscription.billing_owner_id not in {None, principal.user_id}:
        return RedirectResponse("/billing?trial=unavailable", status_code=303)
    if subscription is not None and (
        subscription.paid_through is not None and subscription.paid_through > datetime.now(UTC)
        or effective_plan_code(
            plan_code=subscription.plan_code,  # type: ignore[arg-type]
            state=subscription.state,
            now=datetime.now(UTC),
            paid_through=subscription.paid_through,
            trial_ends_at=subscription.trial_ends_at,
        ) != "free"
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
        db.add(WorkspaceSubscription(workspace_id=tenant_scope.workspace_id, billing_owner_id=principal.user_id, state="trial", plan_code="trial", capacity_bytes=500_000_000, trial_ends_at=trial.ends_at))
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
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
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
            select(func.coalesce(func.sum(StorageReservation.declared_bytes - StorageReservation.committed_bytes), 0)).where(
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
            db, workspace_id=tenant_scope.workspace_id, capacity_bytes=capacity, reserved_bytes=reserved_bytes
        )
    content = _page_shell(
        "Использование и хранение",
        embedded=False,
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
        free_processing_limit_label="300 минут",
        processing_threshold=classify_free_processing(committed_seconds=processing_used + processing_reserved),
        processing_remaining=max(0, FREE_PROCESSING_SECONDS - processing_used - processing_reserved),
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
        storage_reserved=projection.reserved_bytes,
        storage_available=projection.available_bytes,
        storage_capacity=projection.capacity_bytes,
        storage_threshold=projection.threshold,
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
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
        )
    role = await _billing_role(db, tenant_scope=tenant_scope, principal=principal)
    if not _can_manage_billing(role=role, subscription=subscription, principal=principal):
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    now = datetime.now(UTC)
    active = subscription is not None and subscription.paid_through is not None and subscription.paid_through > now
    method_available = False
    next_charge_amount_label = None
    if db is not None and subscription is not None:
        method_available = await db.scalar(
            select(BillingPaymentMethod.id).where(
                BillingPaymentMethod.workspace_id == tenant_scope.workspace_id,
                BillingPaymentMethod.owner_user_id == principal.user_id,
                BillingPaymentMethod.is_default.is_(True),
                BillingPaymentMethod.state == "active",
                BillingPaymentMethod.verified_at.is_not(None),
            )
        ) is not None
        approved_catalog = await _approved_personal_catalog(db, now=now)
        cycle_catalog = approved_catalog.get(subscription.cycle)
        next_charge_amount_label = _billing_amount_label(
            cycle_catalog.amount_minor if cycle_catalog is not None else None
        )
    content = _page_shell(
        "Управление подпиской",
        embedded=False,
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_subscription", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_subscription_content.html",
        subscription=subscription,
        active=active,
        method_available=method_available,
        next_charge_amount_label=next_charge_amount_label,
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
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
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
        embedded=False,
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_payment_method", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_payment_method_content.html",
        method_label=method.masked_label if method is not None else None,
        method_kind=method.kind if method is not None else None,
        method_present=method is not None,
        renewal_allowed=bool(subscription is not None and subscription.recurring_allowed),
        paid_until_label=_billing_datetime_label(subscription.paid_through) if subscription is not None else None,
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
    subscription = await _billing_owner_subscription(db, tenant_scope=tenant_scope, principal=principal)
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
    subscription = None
    if db is not None:
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
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
        embedded=False,
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_storage_addons", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_storage_content.html",
        current_capacity=current_capacity,
        addon_options=(5_000_000_000, 20_000_000_000, 100_000_000_000, 500_000_000_000),
        eligible=effective_plan == "personal",
        billing_enabled=bool(request.app.state.settings.billing_checkout_enabled),
    )
    return cabinet_html_response(content)


async def _billing_owner_subscription(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
) -> WorkspaceSubscription | None:
    workspace = await db.get(Workspace, tenant_scope.workspace_id)
    if workspace is None or workspace.kind != "personal" or workspace.owner_user_id != principal.user_id:
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
    subscription = await _billing_owner_subscription(db, tenant_scope=tenant_scope, principal=principal)
    if (
        subscription is None
        or subscription.paid_through is None
        or subscription.paid_through <= datetime.now(UTC)
    ):
        return RedirectResponse("/billing/subscription?result=unavailable", status_code=303)
    if not subscription.recurring_allowed:
        return RedirectResponse("/billing/subscription?result=already_cancelled", status_code=303)
    if expected_authority_version is None or expected_authority_version != subscription.recurring_authority_version:
        await db.rollback()
        return RedirectResponse("/billing/subscription?result=conflict", status_code=303)
    try:
        changed = cancel_auto_renewal(
            SubscriptionControl(subscription.paid_through, subscription.recurring_allowed, subscription.recurring_authority_version),
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
                "next_charge_at": subscription.paid_through.isoformat() if subscription.paid_through else None,
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
    subscription = await _billing_owner_subscription(db, tenant_scope=tenant_scope, principal=principal)
    if subscription is None:
        return RedirectResponse("/billing/subscription?result=unavailable", status_code=303)
    if subscription.recurring_allowed:
        return RedirectResponse("/billing/subscription?result=already_active", status_code=303)
    if not resume_consent:
        return RedirectResponse("/billing/subscription?result=consent_required", status_code=303)
    if expected_authority_version is None or expected_authority_version != subscription.recurring_authority_version:
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
            SubscriptionControl(subscription.paid_through, subscription.recurring_allowed, subscription.recurring_authority_version),
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
    checkout_promo_code = request.cookies.get(_CHECKOUT_PROMO_COOKIE, "")
    descriptor = plan_descriptor("personal")
    catalog = await _approved_personal_catalog(db, now=datetime.now(UTC))
    monthly_catalog = catalog.get("month")
    annual_catalog = catalog.get("year")
    catalog_ready = monthly_catalog is not None and annual_catalog is not None
    monthly_amount = monthly_catalog.amount_minor if monthly_catalog is not None else None
    annual_amount = annual_catalog.amount_minor if annual_catalog is not None else None
    catalog_storage = monthly_catalog.storage_bytes if monthly_catalog is not None else descriptor.storage_bytes
    offer_version = monthly_catalog.offer_version if monthly_catalog is not None else _BILLING_OFFER_VERSION
    content = _page_shell(
        "Выбор тарифа",
        embedded=False,
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
        billing_enabled=bool(request.app.state.settings.billing_checkout_enabled),
        plan=descriptor,
        monthly_price_label=_billing_price_label(monthly_amount),
        annual_price_label=_billing_price_label(annual_amount),
        annual_saving_label=_annual_saving_label(
            monthly_amount, annual_amount
        ),
        catalog_ready=catalog_ready,
        catalog_storage_label=_capacity_label(catalog_storage),
        offer_version_label=offer_version,
        checkout_idempotency_key=f"web-{principal.user_id}-{uuid4().hex}",
        checkout_result=request.query_params.get("result"),
        checkout_promo_code=checkout_promo_code,
    )
    response = cabinet_html_response(content)
    if checkout_promo_code:
        response.delete_cookie(_CHECKOUT_PROMO_COOKIE, path="/billing/checkout")
    return response


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
    try:
        workspace = await db.scalar(
            select(Workspace).where(Workspace.id == tenant_scope.workspace_id).with_for_update()
        )
        if workspace is None or workspace.kind != "personal" or workspace.owner_user_id != principal.user_id:
            return RedirectResponse("/billing?result=personal_only", status_code=303)
        membership = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == tenant_scope.workspace_id,
                WorkspaceMembership.user_id == principal.user_id,
                WorkspaceMembership.status == "active",
            ).with_for_update()
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
            select(BillingOperation).where(
                BillingOperation.workspace_id == tenant_scope.workspace_id,
                BillingOperation.idempotency_key == key,
            ).with_for_update()
        )
        if existing is not None:
            confirmation_url = existing.request_snapshot.get("confirmation_url")
            if is_allowed_confirmation_url(confirmation_url):
                return RedirectResponse(confirmation_url, status_code=303)
            return RedirectResponse("/billing?result=pending", status_code=303)
        limited = await _billing_rate_limited_response(
            request,
            tenant_scope=tenant_scope,
            principal=principal,
            action="billing_checkout_start",
        )
        if limited is not None:
            return limited

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
            return RedirectResponse("/billing/checkout?result=catalog_not_approved", status_code=303)

        promo: PromoCode | None = None
        promo_campaign: PromotionCampaign | None = None
        if promo_code and promo_code.strip():
            try:
                promo_campaign = await db.scalar(
                    select(PromotionCampaign).where(
                        PromotionCampaign.code_hash == promo_code_hash(promo_code),
                        PromotionCampaign.enabled.is_(True),
                    ).with_for_update()
                )
                if promo_campaign is None:
                    raise PromoError("Промокод не распознан")
                used = await db.scalar(
                    select(func.count(PromotionRedemption.id)).where(
                        PromotionRedemption.workspace_id == tenant_scope.workspace_id,
                        PromotionRedemption.campaign_id == promo_campaign.id,
                        PromotionRedemption.state == "redeemed",
                    )
                )
                promo = PromoCode(
                    code=promo_code,
                    discount_percent=promo_campaign.discount_percent,
                    plan_code=promo_campaign.plan_code,
                    max_redemptions=promo_campaign.max_redemptions,
                    redeemed=promo_campaign.redeemed_count,
                    cycle=promo_campaign.cycle,
                    campaign_version=promo_campaign.campaign_version,
                    starts_at=promo_campaign.starts_at,
                    ends_at=promo_campaign.ends_at,
                )
                check_eligibility(
                    promo=promo,
                    plan_code="personal",
                    cycle=cycle,
                    now=datetime.now(UTC),
                    workspace_redemptions=int(used or 0),
                    active_reservations=promo_campaign.reserved_count,
                )
            except (PromoError, ValueError):
                return _checkout_result_redirect(request, "promo_invalid", promo_code=promo_code)
        # Referral attribution belongs to the inviter's workspace, while the
        # invitee is now paying from a different personal workspace. Use the
        # narrowly-scoped auth-public RLS lookup for this one read, then restore
        # the request tenant context before any billing mutation.
        referred = None
        try:
            referral_cookie = request.cookies.get("graf_referral_token")
            if referral_cookie:
                token_hash = referral_token_hash(validate_referral_token(referral_cookie))
                await apply_tenant_context(
                    db,
                    AuthReferralLookupContext(
                        workspace_id=tenant_scope.workspace_id,
                        user_id=principal.user_id,
                        token_hash=token_hash,
                    ),
                )
                referred = await db.scalar(
                    select(ReferralAttribution).where(
                        ReferralAttribution.token_hash == token_hash,
                        ReferralAttribution.invitee_user_id == principal.user_id,
                        ReferralAttribution.state == "bound",
                    )
                )
            if referred is None:
                await apply_tenant_context(
                    db,
                    AuthReferralUserLookupContext(user_id=principal.user_id),
                )
                referred = await db.scalar(
                    select(ReferralAttribution).where(
                        ReferralAttribution.invitee_user_id == principal.user_id,
                        ReferralAttribution.state == "bound",
                    )
                )
        except ValueError:
            referred = None
        finally:
            await apply_tenant_scope(db, tenant_scope)
        referral_candidate = (
            PromoCode("REFERRAL_INTRO", 10, "personal", 1, campaign_version="referral-v1")
            if referred is not None and referred.inviter_user_id != principal.user_id
            else None
        )
        # Exactly one discount may reach the immutable invoice.  Prefer the
        # lower payable amount and keep configured-promo first for deterministic
        # tie handling; the DB reservation is created only for the winner.
        candidates = tuple(candidate for candidate in (promo, referral_candidate) if candidate is not None)
        chosen, _ = choose_best_discount(
            amount_minor=catalog_snapshot.amount_minor or 0,
            plan_code="personal",
            cycle=cycle,
            provider_floor_minor=settings.billing_provider_floor_minor,
            candidates=candidates,
        )
        configured_promo = promo
        promo = chosen
        if configured_promo is not promo:
            # A referral winner has no PromotionCampaign row and must never
            # create a redemption against the entered campaign.
            promo_campaign = None
        referral_discount = promo is referral_candidate and referral_candidate is not None
        preview = checkout_preview(
            plan_code="personal",
            cycle=cycle,
            promo=promo,
            provider_floor_minor=settings.billing_provider_floor_minor,
            catalog_snapshot=catalog_snapshot,
        )
        unresolved_checkout = await db.scalar(
            select(BillingOperation)
            .where(
                BillingOperation.workspace_id == tenant_scope.workspace_id,
                BillingOperation.kind == "initial_checkout",
                BillingOperation.state.in_(CHECKOUT_BLOCKING_STATES),
            )
            .order_by(BillingOperation.created_at.desc())
            .with_for_update()
        )
        if unresolved_checkout is not None:
            confirmation_url = unresolved_checkout.request_snapshot.get("confirmation_url")
            if is_allowed_confirmation_url(confirmation_url):
                return RedirectResponse(confirmation_url, status_code=303)
            return RedirectResponse("/billing?result=pending", status_code=303)
        intent = build_checkout_intent(workspace_id=tenant_scope.workspace_id, idempotency_key=key, preview=preview)
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
                "discount_source": "referral" if referral_discount else ("promo" if promo is not None else None),
                "catalog_snapshot": catalog_snapshot.as_dict(),
                "offer_consent": True,
                "recurring_consent": True,
                "consent_at": consent_at,
                "billing_actor_user_id": str(principal.user_id),
                "offer_version": catalog_snapshot.offer_version,
            },
        )
        db.add(operation)
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
                "discount_source": "referral" if referral_discount else ("promo" if promo is not None else None),
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
            promo_campaign.reserved_count += 1
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
        async with YooKassaClient(settings) as provider:
            receipt = build_receipt_payload(
                receipt_contact=invoice.receipt_contact_snapshot,
                amount_minor=preview.payable_amount_minor,
                currency=invoice.currency,
                description=f"GRAF Личный, {preview.cycle}",
                tax_system_code=settings.billing_receipt_tax_system_code,
                vat_code=settings.billing_receipt_vat_code,
                payment_subject=settings.billing_receipt_payment_subject,
                payment_mode=settings.billing_receipt_payment_mode,
            )
            payment = await provider.create_payment(
                amount_minor=preview.payable_amount_minor,
                currency="RUB",
                description=f"GRAF Личный, {cycle}",
                idempotence_key=key,
                metadata={
                    "workspace_id": str(tenant_scope.workspace_id),
                    "operation_id": str(intent.operation_id),
                    "invoice_number": intent.invoice_number,
                    "return_url": return_url,
                },
                save_payment_method=True,
                receipt=receipt,
            )
        confirmation = payment.get("confirmation")
        confirmation_url = confirmation.get("confirmation_url") if isinstance(confirmation, dict) else None
        provider_id = validate_provider_identifier(payment.get("id"))
        operation.provider_id = provider_id
        operation.state = "provider_pending"
        if not is_allowed_confirmation_url(confirmation_url):
            # Preserve the provider reference before returning an error: the
            # payment may already exist and must be recovered by GET/list.
            operation.state = "unknown"
            await db.commit()
            return RedirectResponse("/billing/checkout?result=unavailable", status_code=303)
        if subscription is not None and subscription.billing_owner_id != principal.user_id:
            # An owner who replaced the designated billing owner must make a
            # fresh hosted payment before future renewals can use this account.
            subscription.billing_owner_id = principal.user_id
        operation.request_snapshot = {**operation.request_snapshot, "confirmation_url": confirmation_url}
        await db.commit()
        return RedirectResponse(confirmation_url, status_code=303)
    except IntegrityError:
        # A concurrent request may have won the unique workspace/key race.
        # Recover that operation by its logical idempotency key instead of
        # returning a second checkout attempt or mutating the winner.
        await db.rollback()
        winner = await db.scalar(
            select(BillingOperation)
            .where(
                BillingOperation.workspace_id == tenant_scope.workspace_id,
                BillingOperation.idempotency_key == key,
            )
            .with_for_update()
        ) if "key" in locals() else None
        if winner is not None:
            winner_url = winner.request_snapshot.get("confirmation_url")
            if is_allowed_confirmation_url(winner_url):
                return RedirectResponse(winner_url, status_code=303)
            return RedirectResponse("/billing?result=pending", status_code=303)
        return RedirectResponse("/billing/checkout?result=unavailable", status_code=303)
    except (BillingEmergencyStop, ValueError, YooKassaConfigurationError, YooKassaProviderError, httpx.HTTPError):
        await db.rollback()
        if "intent" in locals():
            unresolved = await db.scalar(
                select(BillingOperation).where(
                    BillingOperation.workspace_id == tenant_scope.workspace_id,
                    BillingOperation.id == intent.operation_id,
                ).with_for_update()
            )
            if unresolved is not None:
                if unresolved.state == "scheduled":
                    # A transport failure before provider_id persistence cannot
                    # be safely retried automatically; keep it in the same
                    # blocked, operator-owned state as other unresolved money
                    # mutations instead of pretending provider truth is known.
                    unresolved.state = "manual_resolution"
                    invoice = await db.scalar(
                        select(BillingInvoice)
                        .where(BillingInvoice.operation_id == unresolved.id)
                        .with_for_update()
                    )
                    if invoice is not None:
                        invoice.status = "manual_resolution"
                await db.commit()
        return RedirectResponse("/billing/checkout?result=unavailable", status_code=303)


@router.get("/billing/checkout/return", name="billing_checkout_return", include_in_schema=False)
async def billing_checkout_return(invoice: str | None = None) -> RedirectResponse:
    if invoice is not None and re.fullmatch(r"INV-[A-Z0-9]+", invoice):
        return RedirectResponse(f"/billing/checkout/status/{quote(invoice, safe='-')}", status_code=303)
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
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
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
            receipt_value = snapshot.get("receipt_registration")
            try:
                receipt_state = (
                    ReceiptState(receipt_value) if isinstance(receipt_value, str) else ReceiptState.UNKNOWN
                )
            except ValueError:
                receipt_state = ReceiptState.UNKNOWN
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
                    "created_at": invoice.created_at,
                    "amount_label": f"{invoice.amount_minor / 100:.2f} {invoice.currency}",
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
        embedded=False,
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
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
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
    receipt_value = snapshot.get("receipt_registration")
    try:
        receipt_state = ReceiptState(receipt_value) if isinstance(receipt_value, str) else ReceiptState.UNKNOWN
    except ValueError:
        receipt_state = ReceiptState.UNKNOWN
    receipt_url = snapshot.get("receipt_url")
    if not is_allowed_confirmation_url(receipt_url):
        receipt_url = None
    refund_mailto = None
    support_email = request.app.state.settings.billing_support_email
    if support_email:
        try:
            refund_mailto = build_refund_mailto(support_email=support_email, safe_invoice_number=invoice.safe_number)
        except ValueError:
            refund_mailto = None
    content = _page_shell(
        "Платёж",
        embedded=False,
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
            "amount_label": f"{invoice.amount_minor / 100:.2f} {invoice.currency}",
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
