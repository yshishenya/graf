from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.billing.catalog import (
    FREE_PROCESSING_SECONDS,
    FREE_STORAGE_BYTES,
    classify_free_processing,
    classify_storage_threshold,
    plan_descriptor,
)
from twobrain_rec_server.billing.checkout import build_checkout_intent, checkout_preview
from twobrain_rec_server.billing.entitlements import effective_plan_code
from twobrain_rec_server.billing.operations import BillingEmergencyStop, require_billing_enabled
from twobrain_rec_server.billing.promotions import (
    PromoCode,
    PromoError,
    check_eligibility,
    promo_code_hash,
)
from twobrain_rec_server.billing.refund_email import build_refund_mailto
from twobrain_rec_server.billing.storage import StorageProjection, project_active_playback_storage
from twobrain_rec_server.billing.subscription import (
    SubscriptionControl,
    cancel_auto_renewal,
    resume_auto_renewal,
)
from twobrain_rec_server.billing.trial import activate_trial
from twobrain_rec_server.billing.usage import format_duration, moscow_window_for
from twobrain_rec_server.billing.yookassa import (
    YooKassaClient,
    YooKassaConfigurationError,
    YooKassaProviderError,
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
    FreeUsageWindow,
    PromotionCampaign,
    PromotionRedemption,
    ReferralAttribution,
    StorageReservation,
    TrialActivation,
    WorkspaceMembership,
    WorkspaceSubscription,
)
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])


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
    effective_capacity = (
        subscription.capacity_bytes
        if subscription is not None and plan_code in {"trial", "personal"}
        else FREE_STORAGE_BYTES
    )
    storage_used = 0
    storage_reserved = 0
    processing_used = 0
    if db is not None:
        window_start, _ = moscow_window_for(now)
        window = await db.scalar(
            select(FreeUsageWindow).where(
                FreeUsageWindow.workspace_id == tenant_scope.workspace_id,
                FreeUsageWindow.window_start == window_start,
            )
        )
        processing_used = window.committed_seconds if window is not None else 0
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
        processing_used_label=format_duration(processing_used),
        free_processing_limit_label=format_duration(FREE_PROCESSING_SECONDS),
        storage_capacity_label=f"{effective_capacity:,}".replace(",", " "),
        processing_threshold=classify_free_processing(committed_seconds=processing_used),
        billing_enabled=bool(request.app.state.settings.billing_checkout_enabled),
        trial_result=trial_result,
    )
    return cabinet_html_response(content)


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
    existing = await db.scalar(select(TrialActivation).where(TrialActivation.user_id == principal.user_id))
    if existing is not None:
        return RedirectResponse("/billing?trial=already", status_code=303)
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
    subscription = await db.scalar(select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id).with_for_update())
    if subscription is None:
        db.add(WorkspaceSubscription(workspace_id=tenant_scope.workspace_id, billing_owner_id=principal.user_id, state="trial", plan_code="trial", capacity_bytes=500_000_000, trial_ends_at=trial.ends_at))
    else:
        subscription.state = "trial"
        subscription.plan_code = "trial"
        subscription.capacity_bytes = 500_000_000
        subscription.trial_ends_at = trial.ends_at
    await db.commit()
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
    if db is not None:
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == tenant_scope.workspace_id)
        )
        window_start, _ = moscow_window_for(now)
        window = await db.scalar(
            select(FreeUsageWindow).where(
                FreeUsageWindow.workspace_id == tenant_scope.workspace_id,
                FreeUsageWindow.window_start == window_start,
            )
        )
        processing_used = window.committed_seconds if window is not None else 0
        processing_reserved = window.reserved_seconds if window is not None else 0
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
        free_processing_limit_label=format_duration(FREE_PROCESSING_SECONDS),
        processing_threshold=classify_free_processing(committed_seconds=processing_used),
        processing_unlimited=plan_code in {"trial", "personal"},
        storage_used=projection.used_bytes,
        storage_reserved=projection.reserved_bytes,
        storage_available=projection.available_bytes,
        storage_capacity=projection.capacity_bytes,
        storage_threshold=projection.threshold,
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
    now = datetime.now(UTC)
    active = subscription is not None and subscription.paid_through is not None and subscription.paid_through > now
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
        billing_enabled=bool(request.app.state.settings.billing_checkout_enabled),
    )
    return cabinet_html_response(content)


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
    current_capacity = subscription.capacity_bytes if subscription is not None else FREE_STORAGE_BYTES
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
        eligible=subscription is not None and subscription.plan_code == "personal",
        billing_enabled=bool(request.app.state.settings.billing_checkout_enabled),
    )
    return cabinet_html_response(content)


async def _billing_owner_subscription(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
) -> WorkspaceSubscription | None:
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
    if subscription is None or subscription.billing_owner_id != principal.user_id:
        return None
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
            metadata_json={"authority_version": changed.authority_version},
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
) -> RedirectResponse:
    if db is None or not principal.auth_via_session:
        return RedirectResponse("/billing/subscription?result=unavailable", status_code=303)
    subscription = await _billing_owner_subscription(db, tenant_scope=tenant_scope, principal=principal)
    if subscription is None:
        return RedirectResponse("/billing/subscription?result=unavailable", status_code=303)
    if subscription.recurring_allowed:
        return RedirectResponse("/billing/subscription?result=already_active", status_code=303)
    if expected_authority_version is None or expected_authority_version != subscription.recurring_authority_version:
        await db.rollback()
        return RedirectResponse("/billing/subscription?result=conflict", status_code=303)
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
) -> HTMLResponse:
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
        plan=plan_descriptor("personal"),
        checkout_idempotency_key=f"web-{principal.user_id}-{uuid4().hex}",
        checkout_result=request.query_params.get("result"),
    )
    return cabinet_html_response(content)


@router.post("/billing/checkout/start", response_class=HTMLResponse, include_in_schema=False)
async def start_billing_checkout(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
    cycle: str = Form(default="month", max_length=16),
    idempotency_key: str = Form(default="", max_length=240),
    recurring_consent: bool = Form(default=False),
    promo_code: str | None = Form(default=None, max_length=48),
) -> RedirectResponse:
    settings = request.app.state.settings
    if db is None:
        return RedirectResponse("/billing/checkout?result=unavailable", status_code=303)
    try:
        membership = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == tenant_scope.workspace_id,
                WorkspaceMembership.user_id == principal.user_id,
                WorkspaceMembership.status == "active",
            )
        )
        if membership is None or membership.role != "owner":
            return RedirectResponse("/billing/checkout?result=owner_only", status_code=303)
        require_billing_enabled(
            checkout_enabled=bool(settings.billing_checkout_enabled),
            emergency_stop=bool(settings.billing_emergency_stop),
        )
        key = idempotency_key.strip()
        if not key:
            return RedirectResponse("/billing/checkout?result=invalid", status_code=303)
        if not recurring_consent:
            return RedirectResponse("/billing/checkout?result=consent_required", status_code=303)
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
                        PromotionRedemption.state.in_(("reserved", "redeemed")),
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
                )
            except (PromoError, ValueError):
                return RedirectResponse("/billing/checkout?result=promo_invalid", status_code=303)
        referral_discount = False
        if promo is None:
            referred = await db.scalar(
                select(ReferralAttribution).where(
                    # ponytail: do not broaden tenant reads until token-hash
                    # scoped auth-public RLS is available.
                    ReferralAttribution.workspace_id == tenant_scope.workspace_id,
                    ReferralAttribution.invitee_user_id == principal.user_id,
                    ReferralAttribution.state == "bound",
                ).with_for_update()
            )
            if referred is not None and referred.inviter_user_id != principal.user_id:
                # System benefit, not an operator campaign: it cannot stack with
                # a configured promo and is recorded only in the invoice snapshot.
                promo = PromoCode("REFERRAL_INTRO", 10, "personal", 1, campaign_version="referral-v1")
                referral_discount = True
        preview = checkout_preview(
            plan_code="personal",
            cycle=cycle,
            promo=promo,
            provider_floor_minor=settings.billing_provider_floor_minor,
        )
        existing = await db.scalar(
            select(BillingOperation).where(
                BillingOperation.workspace_id == tenant_scope.workspace_id,
                BillingOperation.idempotency_key == key,
            ).with_for_update()
        )
        if existing is not None:
            confirmation_url = existing.request_snapshot.get("confirmation_url")
            if isinstance(confirmation_url, str) and confirmation_url:
                return RedirectResponse(confirmation_url, status_code=303)
            return RedirectResponse("/billing?result=pending", status_code=303)
        intent = build_checkout_intent(workspace_id=tenant_scope.workspace_id, idempotency_key=key, preview=preview)
        operation = BillingOperation(
            id=intent.operation_id,
            workspace_id=tenant_scope.workspace_id,
            kind="initial_checkout",
            idempotency_key=intent.idempotency_key,
            state="scheduled",
            request_snapshot={
                "plan_code": preview.plan_code,
                "cycle": preview.cycle,
                "list_amount_minor": preview.list_amount_minor,
                "payable_amount_minor": preview.payable_amount_minor,
                "promo_code_hash": promo_code_hash(promo.code) if promo is not None else None,
                "referral_discount": referral_discount,
                "recurring_consent": True,
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
                "campaign_version": promo.campaign_version if promo is not None else None,
                "referral_discount": referral_discount,
                "recurring_consent": True,
            },
        )
        db.add(invoice)
        await db.flush()
        if promo is not None and promo_campaign is not None:
            db.add(
                PromotionRedemption(
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
            )
        await db.commit()
        return_url = str(request.url_for("billing_checkout_return"))
        async with YooKassaClient(settings) as provider:
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
            )
        confirmation = payment.get("confirmation")
        confirmation_url = confirmation.get("confirmation_url") if isinstance(confirmation, dict) else None
        provider_id = payment.get("id")
        if not isinstance(provider_id, str) or not provider_id or not isinstance(confirmation_url, str) or not confirmation_url:
            raise YooKassaProviderError("YooKassa confirmation is unavailable")
        operation.provider_id = provider_id
        operation.state = "provider_pending"
        operation.request_snapshot = {**operation.request_snapshot, "confirmation_url": confirmation_url}
        await db.commit()
        return RedirectResponse(confirmation_url, status_code=303)
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
                    unresolved.state = "unknown"
                invoice = await db.scalar(
                    select(BillingInvoice).where(BillingInvoice.operation_id == unresolved.id).with_for_update()
                )
                if invoice is not None:
                    redemption = await db.scalar(
                        select(PromotionRedemption)
                        .where(PromotionRedemption.invoice_id == invoice.id)
                        .with_for_update()
                    )
                    if redemption is not None and redemption.state == "reserved":
                        redemption.state = "released"
                        redemption.released_at = datetime.now(UTC)
                await db.commit()
        return RedirectResponse("/billing/checkout?result=unavailable", status_code=303)


@router.get("/billing/checkout/return", name="billing_checkout_return", include_in_schema=False)
async def billing_checkout_return() -> RedirectResponse:
    return RedirectResponse("/billing?result=returned", status_code=303)


@router.get("/billing/history", response_class=HTMLResponse, include_in_schema=False)
async def billing_history_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    invoices: list[dict[str, object]] = []
    if db is not None:
        rows = await db.scalars(
            select(BillingInvoice)
            .where(BillingInvoice.workspace_id == tenant_scope.workspace_id)
            .order_by(BillingInvoice.created_at.desc())
            .limit(100)
        )
        for invoice in rows:
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
