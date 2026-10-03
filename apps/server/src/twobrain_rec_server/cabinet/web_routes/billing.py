from __future__ import annotations

import base64
import binascii
import hmac
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import TYPE_CHECKING
from urllib.parse import quote, urlencode, urlsplit
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.browser_handoff import (
    DESKTOP_BILLING_HANDOFF_PROVIDER,
    open_desktop_billing_session,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.rate_limit import enforce_auth_rate_limits
from twobrain_rec_server.auth.sessions import (
    create_login_device,
    hash_token,
    issue_auth_session,
    resolve_session_device,
)
from twobrain_rec_server.billing.catalog import (
    ADDON_CAPACITY_BYTES,
    FREE_PROCESSING_SECONDS,
    FREE_STORAGE_BYTES,
    PERSONAL_STORAGE_BYTES,
    CatalogNotApproved,
    classify_free_processing,
    classify_storage_threshold,
    plan_descriptor,
    storage_package_capacity,
    storage_package_count,
    validate_plan_version,
)
from twobrain_rec_server.billing.checkout import (
    CheckoutPreview,
    build_checkout_intent,
    checkout_preview,
)
from twobrain_rec_server.billing.entitlements import _add_paid_interval, effective_plan_code
from twobrain_rec_server.billing.events import enqueue_billing_notification
from twobrain_rec_server.billing.history import mask_payment_method, purchase_purpose_label
from twobrain_rec_server.billing.notifications import BillingNotification
from twobrain_rec_server.billing.operations import (
    CHECKOUT_BLOCKING_STATES,
    INITIAL_CHECKOUT_OBSERVATION_EXPIRED,
    BillingCheckoutDisabled,
    billing_checkout_allowed,
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
    release_invoice_promo,
)
from twobrain_rec_server.billing.provider_events import validate_provider_identifier
from twobrain_rec_server.billing.purchases import (
    AcceptanceBudgetUnavailable,
    PurchaseError,
    accept_base_price,
    accept_storage_price,
    calculate_storage_purchase,
    checkout_quote_snapshot,
    compose_personal_catalog,
    create_purchase_quote,
    effective_paid_storage,
    reserve_acceptance_budget,
    settle_acceptance_budget,
    storage_catalog,
    storage_period_timeline,
    storage_price_snapshot,
    utc,
    validate_acceptance_campaign,
    validate_purchase_quote,
)
from twobrain_rec_server.billing.receipts import (
    ReceiptState,
    receipt_label,
    receipt_state_for_registration,
)
from twobrain_rec_server.billing.referrals import referral_token_hash, validate_referral_token
from twobrain_rec_server.billing.refund_email import build_refund_mailto
from twobrain_rec_server.billing.renewal_charge import (
    cancel_unsent_renewals,
    next_renewal_attempt,
    renewal_attempt_of,
    renewal_canceled_without_payment,
)
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
    TRIAL_DAYS,
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
from twobrain_rec_server.cabinet.queries import get_account_profile_view
from twobrain_rec_server.cabinet.rendering_shared import _page_shell
from twobrain_rec_server.cabinet.templates import cabinet_html_response
from twobrain_rec_server.cabinet.user_time import format_user_datetime
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
    AuthSessionDeviceBinding,
    BillingAuditEvent,
    BillingEntitlementGrant,
    BillingInvoice,
    BillingOperation,
    BillingPaymentMethod,
    BillingPlanVersion,
    BillingPurchaseQuote,
    BillingStorageEntitlementGrant,
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
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context,
    apply_tenant_scope,
)
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)
from twobrain_rec_server.public.offers import (
    PUBLIC_APPROVED_OFFER_VERSION,
    matches_approved_public_catalog,
)

if TYPE_CHECKING:
    from twobrain_rec_server.config import Settings

router = APIRouter(tags=["cabinet-web"])

_CHECKOUT_PROMO_COOKIE = "graf_checkout_promo"
_CHECKOUT_PROMO_DRAFT_COOKIE = "graf_checkout_promo_draft"
_CHECKOUT_PROMO_COOKIE_MAX_AGE = 5 * 60
_CHECKOUT_PROMO_DRAFT_PURPOSE = "billing-promo:v1:"


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
        select(AuthSession)
        .where(AuthSession.session_token_hash == hash_token(session_token))
        .with_for_update()
    )
    if auth_session is None or auth_session.status != "active" or auth_session.expires_at <= now:
        await apply_tenant_context(db, AuthCallbackLookupContext(state_nonce=state))
        callback_state.used_at = now
        callback_state.result = "failed"
        callback_state.error_code = "auth_handoff_session_invalid"
        await db.commit()
        return fallback

    user = await db.get(UserIdentity, auth_session.user_id)
    valid_owner = user is not None and user.status == "active"
    if valid_owner:
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                organization_id=user.organization_id,
                workspace_id=auth_session.workspace_id,
                user_id=user.id,
                context_kind="auth_bootstrap",
            ),
        )
        workspace = await db.get(Workspace, auth_session.workspace_id)
        membership = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == auth_session.workspace_id,
                WorkspaceMembership.user_id == user.id,
            )
        )
        valid_owner = (
            workspace is not None
            and workspace.organization_id == user.organization_id
            and workspace.id != request.app.state.settings.web_login_workspace_id
            and membership is not None
            and membership.status == "active"
            and (
                workspace.kind != "personal"
                or (workspace.owner_user_id == user.id and membership.role == "owner")
            )
        )
    if valid_owner:
        await apply_tenant_context(
            db,
            TenantDatabaseContext(
                organization_id=user.organization_id,
                workspace_id=auth_session.workspace_id,
                user_id=user.id,
                auth_session_id=auth_session.id,
                device_id=auth_session.device_id,
            ),
        )
        valid_owner, source_device = await resolve_session_device(db, auth_session)
        valid_owner = valid_owner and source_device is not None
    if not valid_owner:
        await apply_tenant_context(db, AuthCallbackLookupContext(state_nonce=state))
        callback_state.used_at = now
        callback_state.result = "failed"
        callback_state.error_code = "auth_handoff_session_invalid"
        await db.commit()
        return fallback
    device = await create_login_device(
        db,
        user_id=user.id,
        workspace_id=auth_session.workspace_id,
        user_agent=request.headers.get("user-agent"),
        browser_only=True,
        now=now,
    )
    issued = await issue_auth_session(
        db,
        user_id=user.id,
        workspace_id=auth_session.workspace_id,
        device_id=device.id,
        provider=auth_session.provider,
        claims_fingerprint=auth_session.claims_fingerprint,
        now=now,
        expires_at=auth_session.expires_at,
    )
    db.add(
        AuthSessionDeviceBinding(
            auth_session_id=issued.id,
            registered_device_id=device.id,
            device_state="trusted",
            last_heartbeat_at=now,
        )
    )
    await db.flush()
    await apply_tenant_context(db, AuthCallbackLookupContext(state_nonce=state))
    callback_state.used_at = now
    callback_state.result = "completed"
    callback_state.error_code = None
    await db.commit()
    redirect = RedirectResponse("/billing", status_code=303)
    _set_browser_auth_cookie(
        request,
        redirect,
        token=issued.token,
        expires_at=issued.expires_at,
    )
    return redirect


def _promo_draft_now() -> int:
    return int(datetime.now(UTC).timestamp())


def _checkout_promo_draft(
    request: Request,
    *,
    principal: AuthenticatedPrincipal,
    tenant_scope: TenantScope,
) -> dict | None:
    """Read bounded input only for its verified browser session and workspace."""
    secret = getattr(request.app.state, "web_csrf_secret", None)
    token = request.cookies.get(_CHECKOUT_PROMO_DRAFT_COOKIE, "")
    if not principal.auth_via_session or principal.session_id is None or not secret or not token:
        return None
    try:
        if len(token) > 2048:
            return None
        encoded, signature = token.rsplit(".", 1)
        expected = hmac.new(
            str(secret).encode(),
            (_CHECKOUT_PROMO_DRAFT_PURPOSE + encoded).encode(),
            sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        draft = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if (
            not isinstance(draft, dict)
            or set(draft) != {"code", "cycle", "expiry", "user", "workspace", "session"}
            or not isinstance(draft["code"], str)
            or not 0 < len(draft["code"]) <= 48
            or draft["cycle"] not in ("month", "year")
            or type(draft["expiry"]) is not int
            or not _promo_draft_now() < draft["expiry"]
            or draft["user"] != str(principal.user_id)
            or draft["workspace"] != str(tenant_scope.workspace_id)
            or draft["session"] != str(principal.session_id)
        ):
            return None
        return draft
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        return None


def _clear_checkout_promo_draft(response: Response) -> None:
    response.delete_cookie(_CHECKOUT_PROMO_DRAFT_COOKIE, path="/billing/checkout")
    response.delete_cookie(_CHECKOUT_PROMO_COOKIE, path="/billing/checkout")


def _checkout_operation_redirect(url: str, *, status_code: int = 303) -> RedirectResponse:
    """An authoritative operation owns the selection from this point onward."""
    response = RedirectResponse(url, status_code=status_code)
    _clear_checkout_promo_draft(response)
    return response


def _checkout_result_redirect(
    request: Request,
    result: str,
    *,
    principal: AuthenticatedPrincipal,
    tenant_scope: TenantScope,
    promo_code: str | None = None,
    cycle: str | None = None,
    replace_promo: bool = False,
) -> RedirectResponse:
    """Carry signed input, never a price, quote, consent or payment authority."""
    previous = _checkout_promo_draft(request, principal=principal, tenant_scope=tenant_scope)
    value = promo_code if promo_code is not None else previous["code"] if previous and not replace_promo else ""
    if not replace_promo:
        if previous is not None:
            # An unchanged/stale form or failed start cannot replace newer input.
            value = previous["code"]
        else:
            if value and result == "promo_applied":
                result = "promo_expired"
            value = ""
    selected_cycle = previous["cycle"] if previous and request.url.path == "/billing/checkout/start" else (
        cycle if cycle in ("month", "year") else previous["cycle"] if previous else "month"
    )
    query = {"result": result}
    if cycle in ("month", "year") or previous:
        query["cycle"] = selected_cycle
    response = RedirectResponse(f"/billing/checkout?{urlencode(query)}", status_code=303)
    secret = getattr(request.app.state, "web_csrf_secret", None)
    now = _promo_draft_now()
    expiry = now + _CHECKOUT_PROMO_COOKIE_MAX_AGE if replace_promo else (
        previous["expiry"] if previous else None
    )
    if (
        principal.auth_via_session and principal.session_id is not None and secret
        and isinstance(value, str) and value.strip() and len(value) <= 48
        and expiry is not None and now < expiry
    ):
        draft = {
            "code": value,
            "cycle": selected_cycle,
            "expiry": expiry,
            "user": str(principal.user_id),
            "workspace": str(tenant_scope.workspace_id),
            "session": str(principal.session_id),
        }
        encoded = base64.urlsafe_b64encode(
            json.dumps(draft, separators=(",", ":"), sort_keys=True).encode()
        ).decode().rstrip("=")
        signature = hmac.new(
            str(secret).encode(), (_CHECKOUT_PROMO_DRAFT_PURPOSE + encoded).encode(), sha256
        ).hexdigest()
        response.set_cookie(
            _CHECKOUT_PROMO_DRAFT_COOKIE,
            value=f"{encoded}.{signature}",
            max_age=expiry - now,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
            path="/billing/checkout",
        )
        response.delete_cookie(_CHECKOUT_PROMO_COOKIE, path="/billing/checkout")
    else:
        _clear_checkout_promo_draft(response)
    return response


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
            BillingOperation.kind.in_(("initial_checkout", "storage_upgrade", "early_renewal", "renewal")),
            ~((BillingOperation.kind == "renewal") & (BillingOperation.state == "scheduled") & BillingOperation.provider_id.is_(None)),
            BillingOperation.state.in_(CHECKOUT_BLOCKING_STATES),
        )
        .order_by(BillingOperation.created_at.desc(), BillingOperation.id.desc())
    )


def _initial_checkout_can_continue(
    operation: BillingOperation,
    *,
    now: datetime | None = None,
) -> bool:
    return (
        operation.kind == "initial_checkout"
        and operation.request_snapshot.get("purchase_schema") != 2
        and operation.provider_id is None
        and operation.state in {"scheduled", "manual_resolution", "unknown"}
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
    elif isinstance(exc, BillingCheckoutDisabled):
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
    if isinstance(exc, YooKassaProviderError) and exc.reason == "recurring_not_available":
        metadata["reason"] = "recurring_not_available"
    return metadata


def _record_initial_checkout_failure(
    operation: BillingOperation,
    invoice: BillingInvoice,
    exc: BaseException,
    *,
    now: datetime | None = None,
    dispatch_started: bool = True,
) -> None:
    if invoice.status == "succeeded" or operation.state in {
        "succeeded",
        "succeeded_refused",
        "canceled",
        "reconciliation_gap",
    }:
        return
    current = now or datetime.now(UTC)
    snapshot = (
        dict(operation.request_snapshot) if isinstance(operation.request_snapshot, dict) else {}
    )
    snapshot["provider_failure"] = _initial_checkout_failure_metadata(exc, now=current)
    operation.request_snapshot = snapshot
    if operation.provider_id is not None:
        operation.state = "unknown"
        invoice.status = "unknown"
    elif (
        snapshot.get("purchase_schema") == 2
        and (
            not dispatch_started
            or (isinstance(exc, YooKassaProviderError)
                and exc.status_code in {400, 401, 403, 404, 405, 415, 429})
        )
    ):
        # These documented responses reject creation. A timeout, 5xx or
        # unrecognized status has no such proof and must remain unresolved.
        operation.state = "canceled"
        invoice.status = "canceled"
    elif snapshot.get("purchase_schema") != 2 and provider_key_is_expired(
        expires_at=operation.provider_key_expires_at, now=current
    ):
        operation.state = "canceled"
        invoice.status = "canceled"
    else:
        operation.state = "manual_resolution"
        invoice.status = "manual_resolution"


async def _persist_initial_checkout_failure(
    db, operation, invoice, exc, *, dispatch_started: bool = True
) -> None:
    _record_initial_checkout_failure(
        operation, invoice, exc, dispatch_started=dispatch_started
    )
    if (
        operation.state == invoice.status == "canceled"
        and operation.request_snapshot.get("purchase_schema") == 2
        and operation.provider_id is None
        and (
            not dispatch_started
            or (isinstance(exc, YooKassaProviderError)
                and exc.status_code in {400, 401, 403, 404, 405, 415, 429})
        )
    ):
        await release_invoice_promo(db, invoice_id=invoice.id, now=datetime.now(UTC))
        await settle_acceptance_budget(
            db, workspace_id=operation.workspace_id, operation_id=operation.id, succeeded=False
        )


async def _create_initial_checkout_payment(
    *,
    settings: Settings,
    operation: BillingOperation,
    invoice: BillingInvoice,
    return_url: str,
    dispatch_state: dict[str, bool] | None = None,
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
        or type(snapshot.get("recurring_consent")) is not bool
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
        if dispatch_state is not None:
            dispatch_state["started"] = True
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
            save_payment_method=snapshot["recurring_consent"],
            receipt=receipt,
        )


def _bind_initial_checkout_payment(
    operation: BillingOperation,
    invoice: BillingInvoice,
    payment: Mapping[str, object],
) -> str | None:
    provider_id = validate_provider_identifier(payment.get("id"))
    if operation.provider_id not in {None, provider_id}:
        raise ValueError("provider payment binding changed")
    # A webhook can win the race while the original POST is still in flight.
    if invoice.status == "succeeded" or operation.state in {
        "succeeded",
        "succeeded_refused",
        "canceled",
        "reconciliation_gap",
    }:
        return None
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
    """Return days-left, exact viewer-local end label and the expired-trial state."""
    if trial_ends_at is None:
        return None, None, False
    end_label = _billing_datetime_label(trial_ends_at)
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
    return format_user_datetime(value, show_zone=True) if value is not None else None


def _legacy_storage_period_label(snapshot: Mapping[str, object]) -> str | None:
    """Read the period validated by the legacy storage projector, without current quota."""
    target = snapshot.get("addon_capacity_bytes", snapshot.get("capacity_bytes"))
    if (
        snapshot.get("purchase_schema") not in (None, 1)
        or type(target) is not int
        or target not in (PERSONAL_STORAGE_BYTES, *ADDON_CAPACITY_BYTES)
        or snapshot.get("cycle") not in ("month", "year")
    ):
        return None
    period = []
    for key in ("effective_at", "ends_at"):
        value = snapshot.get(key)
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        period.append(parsed.astimezone(UTC))
    starts_at, ends_at = period
    if starts_at >= ends_at:
        return None
    return f"{_billing_datetime_label(starts_at)} — {_billing_datetime_label(ends_at)}"


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
        "scheduled": "Платеж подготовлен",
        "provider_pending": "Ожидаем подтверждение ЮKassa",
        "sent": "Платеж отправлен в ЮKassa",
        "processing": "ЮKassa обрабатывает платеж",
        "unknown": "Проверяем результат платежа",
        "pending_reconciliation": "Проверяем результат оплаты",
        "reconciliation_gap": "Проверяем результат оплаты",
        "manual_resolution": "Проверяем результат оплаты",
        "provider_key_expired": "Продолжить эту оплату уже нельзя",
        "observation_expired": "Срок проверки платежа истек",
        "method_required": "Нужен способ оплаты",
        "succeeded": "Платеж подтвержден",
        "succeeded_refused": "Оплата получена. Проверяем доступ",
        "canceled": "Платеж отменен",
        "failed": "Платеж не выполнен",
    }.get(state or "", "Статус уточняется")


def _invoice_status_label(status: str) -> str:
    return {
        "pending": "Ожидает подтверждения",
        "succeeded": "Оплачен",
        "canceled": "Отменен",
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


async def _verified_receipt_contact(db, user_id):
    if db is None:
        return None
    return await db.scalar(
        select(ExternalIdentity.email)
        .where(
            ExternalIdentity.user_id == user_id,
            ExternalIdentity.is_active.is_(True),
            ExternalIdentity.is_verified.is_(True),
            ExternalIdentity.email.is_not(None),
        )
        .order_by(ExternalIdentity.created_at.asc())
        .limit(1)
    )


def _receipt_contact_action_url(request, *, next_path):
    account_path = "/desktop/settings/account" if _is_embedded_request(request) else "/settings/account"
    return f"{account_path}?{urlencode({'next': next_path})}#account-providers-title"


def _renewal_notice(subscription):
    """Explain existing renewal blockers without changing their resolution."""
    resolution = subscription.renewal_resolution if subscription else None
    cycle = "year" if subscription and subscription.cycle == "year" else "month"
    return {
        "method_required": (
            "Автопродление приостановлено. Проверьте способ оплаты.",
            "/billing/payment-method", "Проверить способ оплаты",
        ),
        "receipt_contact_required": (
            "Автопродление приостановлено: нужен адрес для чека из подтвержденной оплаты. "
            "Оплатите следующий период вручную; оплаченный остаток сохранится.",
            f"/billing/checkout?cycle={cycle}", "Оплатить следующий период вручную",
        ),
        "price_changed": (
            "Цена подписки или хранения изменилась. Автопродление приостановлено до подтверждения новых условий.",
            "/billing/storage", "Проверить новую цену",
        ),
    }.get(resolution, (None, None, None))


def _capacity_label(capacity_bytes: int) -> str:
    value = float(capacity_bytes)
    for unit in ("байт", "KB", "MB", "GB", "TB"):
        if round(value, 2) < 1000 or unit == "TB":
            break
        value /= 1000
    label = f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{label} {unit}"


def _exact_bytes_label(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _storage_threshold_label(value: str) -> str:
    return {
        "normal": "В норме",
        "80%": "Заполнено на 80%",
        "95%": "Заполнено на 95%",
        "full": "Заполнено",
        "over_capacity": "Превышена емкость",
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
        "redeemed": "Применен",
        "released": "Освобожден после отмены оплаты",
        "expired": "Истек",
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
    """Read the same approved catalog authority used by checkout UI and POST.

    The public page only claims a sale for the published offer revision, so the
    cabinet must apply the same bar. Otherwise an exact-price row carrying some
    other revision would open checkout while the landing page stays silent.
    """
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
            snapshot = validate_plan_version(row, now=now)
        except (CatalogNotApproved, ValueError):
            continue
        if snapshot.offer_version != PUBLIC_APPROVED_OFFER_VERSION:
            continue
        approved[row.cycle] = snapshot
    if not matches_approved_public_catalog(approved.get("month"), approved.get("year")):
        return {}
    return approved


async def _load_checkout_promo(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    raw_code: str,
    cycle: str,
    now: datetime,
    lock: bool = False,
    purpose: str = "initial_checkout",
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
    policy = campaign.policy_snapshot or {}
    # Legacy public promotions apply only to the original tariff checkout.
    purposes = policy.get("purposes", ["initial_checkout"])
    if not isinstance(purposes, list) or purpose not in purposes:
        raise PromoError("Промокод не подходит для этой покупки")
    if policy.get("workspace_id") not in {None, str(workspace_id)}:
        raise PromoError("Промокод недоступен для этого пространства")
    try:
        await validate_acceptance_campaign(db, policy=policy, workspace_id=workspace_id, now=now)
    except PurchaseError as exc:
        raise PromoError(str(exc)) from exc
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
        await effective_paid_storage(db, subscription=subscription, now=now)
        if db is not None and subscription is not None and plan_code in {"trial", "personal"}
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
    renewal_notice, renewal_action_url, renewal_action_label = _renewal_notice(subscription)
    if (
        subscription is not None
        and plan_code == "personal"
        and subscription.paid_through
        and subscription.paid_through > now
    ):
        if subscription.recurring_allowed:
            recurring_next_charge_label = await _next_renewal_label(db, subscription, now=now)
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
            next_catalog = approved_catalog.get(cycle)
            if next_catalog is not None:
                try:
                    next_catalog, _ = await compose_personal_catalog(
                        db, base=next_catalog, subscription=subscription, now=now
                    )
                except PurchaseError:
                    next_catalog = None
            recurring_next_charge_amount_label = _billing_amount_label(
                scheduled_renewal_invoice.amount_minor
                if scheduled_renewal_invoice is not None
                else next_catalog.amount_minor
                if next_catalog is not None
                else None,
                scheduled_renewal_invoice.currency
                if scheduled_renewal_invoice is not None
                else "RUB",
            )
        else:
            recurring_next_charge_label = "не запланировано"
            next_catalog = approved_catalog.get(current_cycle)
            if next_catalog is not None:
                try:
                    next_catalog, _ = await compose_personal_catalog(
                        db, base=next_catalog, subscription=subscription, now=now
                    )
                except PurchaseError:
                    next_catalog = None
            recurring_next_charge_amount_label = _billing_amount_label(
                next_catalog.amount_minor if next_catalog is not None else None
            )
    elif subscription is not None and subscription.renewal_resolution in {
        "unknown_pending",
        "pending",
        "unknown",
    }:
        recurring_next_charge_label = "проверяем результат предыдущего списания"
    trial_activation = None
    if db is not None and subscription is not None and billing_owner and plan_code == "trial":
        trial_activation = await db.scalar(
            select(TrialActivation)
            .where(
                TrialActivation.workspace_id == tenant_scope.workspace_id,
                TrialActivation.ends_at == subscription.trial_ends_at,
            )
            .order_by(TrialActivation.starts_at.desc())
            .limit(1)
        )
    content = _page_shell(
        "Тариф и оплата",
        embedded=_is_embedded_request(request),
        profile=await get_account_profile_view(db, tenant_scope) if db is not None else None,
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
        processing_reset_at_label=format_user_datetime(window_end, show_zone=True),
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
        billing_enabled=billing_checkout_allowed(request.app.state.settings, tenant_scope.workspace_id),
        catalog_ready=("month" in approved_catalog and "year" in approved_catalog),
        trial_result=trial_result,
        trial_preview_starts_at_label=_billing_datetime_label(now),
        trial_preview_ends_at_label=_billing_datetime_label(now + timedelta(days=TRIAL_DAYS)),
        trial_starts_at_label=_billing_datetime_label(
            trial_activation.starts_at if trial_activation is not None else None
        ),
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
        renewal_allowed=bool(subscription and subscription.recurring_allowed),
        renewal_notice=renewal_notice,
        renewal_action_url=renewal_action_url,
        renewal_action_label=renewal_action_label,
        manual_checkout_url=f"/billing/checkout?cycle={current_cycle or 'month'}",
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
        profile=await get_account_profile_view(db, tenant_scope) if db is not None else None,
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
        billing_enabled=billing_checkout_allowed(request.app.state.settings, tenant_scope.workspace_id),
        trial_preview_starts_at_label=_billing_datetime_label(now),
        trial_preview_ends_at_label=_billing_datetime_label(now + timedelta(days=TRIAL_DAYS)),
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
    """Show discount terms and history without disclosing campaign codes."""
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
    redemptions: list[dict[str, str]] = []
    if db is not None:
        rows = await db.execute(
            select(PromotionRedemption, BillingInvoice)
            .outerjoin(
                BillingInvoice,
                (BillingInvoice.id == PromotionRedemption.invoice_id)
                & (BillingInvoice.workspace_id == tenant_scope.workspace_id),
            )
            .where(PromotionRedemption.workspace_id == tenant_scope.workspace_id)
            .order_by(PromotionRedemption.reserved_at.desc())
            .limit(100)
        )
        for redemption, invoice in rows:
            snapshot = invoice.plan_snapshot if invoice is not None else None
            cycle = snapshot.get("cycle") if isinstance(snapshot, dict) else None
            redemptions.append(
                {
                    "discount_label": f"Скидка {redemption.discount_percent}%",
                    "state_label": _promotion_state_label(redemption.state),
                    "cycle_label": "Год" if cycle == "year" else "Месяц" if cycle == "month" else "",
                }
            )
    content = _page_shell(
        "Скидки",
        embedded=_is_embedded_request(request),
        profile=await get_account_profile_view(db, tenant_scope) if db is not None else None,
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_discounts", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_discounts_content.html",
        redemptions=redemptions,
        billing_owner=billing_owner,
        billing_enabled=billing_checkout_allowed(request.app.state.settings, tenant_scope.workspace_id),
        discount_promo_code=getattr(request.state, "discount_promo_code", ""),
        result=getattr(request.state, "discount_result", request.query_params.get("result")),
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
) -> HTMLResponse:
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
        normalized = None
    campaign = await db.scalar(
        select(PromotionCampaign).where(
            PromotionCampaign.code_hash == promo_code_hash(normalized),
            PromotionCampaign.enabled.is_(True),
        )
    ) if normalized else None
    cycle = subscription.cycle if subscription and subscription.cycle in {"month", "year"} else None
    now = datetime.now(UTC)
    if campaign is None or (campaign.starts_at is not None and campaign.starts_at > now) or (
        campaign.ends_at is not None and campaign.ends_at <= now
    ):
        return _checkout_result_redirect(
            request, "promo_invalid", promo_code=promo_code, cycle=cycle,
            principal=principal, tenant_scope=tenant_scope, replace_promo=True,
        )
    return _checkout_result_redirect(
        request, "promo_applied", promo_code=normalized, cycle=cycle,
        principal=principal, tenant_scope=tenant_scope, replace_promo=True,
    )


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
    _clear_checkout_promo_draft(response)
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
    service_period_label = None
    service_gap = bool(
        operation_state == "succeeded_refused"
        or (operation and operation.request_snapshot.get("reconciliation_detail"))
        or (invoice.plan_snapshot or {}).get("service_resolution")
    )
    if operation_state in {"succeeded", "succeeded_projected"} and not service_gap:
        if invoice.status != "succeeded":
            service_gap = True
        elif operation_state == "succeeded_projected":
            if operation.kind == "storage_upgrade":
                service_period_label = _legacy_storage_period_label(operation.request_snapshot)
            service_gap = service_period_label is None
        elif operation.kind in {"initial_checkout", "renewal", "early_renewal"}:
            grant = await db.scalar(select(BillingEntitlementGrant).where(
                BillingEntitlementGrant.workspace_id == tenant_scope.workspace_id,
                BillingEntitlementGrant.invoice_id == invoice.id,
            ))
            service_gap = grant is None
            if grant is not None:
                service_period_label = (
                    f"{_billing_datetime_label(grant.starts_at)} — "
                    f"{_billing_datetime_label(grant.ends_at)}"
                )
        elif operation.kind == "storage_upgrade":
            grants = list(await db.scalars(select(BillingStorageEntitlementGrant).where(
                BillingStorageEntitlementGrant.workspace_id == tenant_scope.workspace_id,
                BillingStorageEntitlementGrant.invoice_id == invoice.id,
            ).order_by(
                BillingStorageEntitlementGrant.starts_at,
                BillingStorageEntitlementGrant.ends_at,
                BillingStorageEntitlementGrant.id,
            )))
            service_gap = not grants
            if grants:
                service_period_label = "; ".join(
                    f"{_billing_datetime_label(grant.starts_at)} — "
                    f"{_billing_datetime_label(grant.ends_at)}"
                    for grant in grants
                )
        else:
            service_gap = True
    payment_applied = operation_state in {"succeeded", "succeeded_projected"} and not service_gap
    provider_failure = operation.request_snapshot.get("provider_failure") if operation else None
    if not isinstance(provider_failure, dict):
        provider_failure = {}
    creation_rejected = bool(
        operation
        and operation.request_snapshot.get("purchase_schema") == 2
        and operation_state == invoice.status == "canceled"
        and operation.provider_id is None
        and provider_failure.get("class") == "provider_rejected"
        and type(provider_failure.get("http_status")) is int
        and provider_failure["http_status"] in {400, 401, 403, 404, 405, 415, 429}
    )
    recurring_not_available = bool(
        creation_rejected
        and operation.kind == "initial_checkout"
        and operation.request_snapshot.get("recurring_consent") is True
        and provider_failure.get("http_status") == 403
        and provider_failure.get("reason") == "recurring_not_available"
    )
    retry_payment_url = f"/billing/checkout?cycle={'year' if invoice.plan_snapshot.get('cycle') == 'year' else 'month'}"
    if operation and operation.kind == "storage_upgrade":
        retry_payment_url = "/billing/storage"
        try:
            package_count = storage_package_count(operation.request_snapshot.get("target_capacity_bytes"))
        except ValueError:
            pass
        else:
            retry_payment_url += f"?package_count={package_count}"
    elif operation and operation.kind == "early_renewal":
        retry_payment_url = "/billing/subscription"
    settings = request.app.state.settings
    operation_actor = (
        operation.request_snapshot.get("billing_actor_user_id") if operation is not None else None
    )
    actor_matches = operation_actor == str(principal.user_id) or (
        operation_actor is None and operation is not None and operation.kind == "initial_checkout"
    )
    can_continue_payment = bool(
        operation is not None
        and invoice.status == "pending"
        and billing_checkout_allowed(settings, tenant_scope.workspace_id)
        and actor_matches
        and (
            _initial_checkout_can_continue(operation)
            or (
                operation.kind in {"initial_checkout", "storage_upgrade"}
                and operation.state == "provider_pending"
                and is_allowed_confirmation_url(operation.request_snapshot.get("confirmation_url"))
            )
        )
    )
    can_refresh_payment = bool(
        operation is not None
        and (
            operation.provider_id is not None
            or operation.request_snapshot.get("purchase_schema") == 2
        )
        and operation.kind in {"initial_checkout", "storage_upgrade", "early_renewal", "renewal"}
        and operation.state
        in {
            "processing",
            "sent",
            "provider_pending",
            "unknown",
            "manual_resolution",
            "reconciliation_gap",
            "provider_key_expired",
            INITIAL_CHECKOUT_OBSERVATION_EXPIRED,
        }
    )
    content = _page_shell(
        "Статус платежа",
        embedded=_is_embedded_request(request),
        profile=await get_account_profile_view(db, tenant_scope) if db is not None else None,
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
        creation_rejected=creation_rejected,
        recurring_not_available=recurring_not_available,
        retry_payment_url=retry_payment_url,
        support_email=settings.billing_support_email,
        purchase_purpose_label=purchase_purpose_label(invoice.plan_snapshot or {}),
        payment_applied=payment_applied,
        service_gap=service_gap,
        service_period_label=service_period_label,
        return_to_work_url="/desktop/meetings" if _is_embedded_request(request) else "/meetings",
        operation_state_label=_operation_state_label(operation_state),
        billing_enabled=billing_checkout_allowed(settings, tenant_scope.workspace_id),
        can_continue_payment=can_continue_payment and request.query_params.get("view") != "local",
        can_refresh_payment=can_refresh_payment,
        read_only_recovery=request.query_params.get("view") == "local",
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
    if invoice.status != "pending" or (
        operation is not None and operation.state in {"succeeded", "succeeded_refused", "canceled", "failed"}
    ):
        return RedirectResponse(_checkout_status_location(safe_number), status_code=303)
    if operation is not None and operation.kind == "storage_upgrade":
        if (
            operation.request_snapshot.get("billing_actor_user_id") != str(principal.user_id)
            or not billing_checkout_allowed(request.app.state.settings, tenant_scope.workspace_id)
        ):
            return RedirectResponse(
                _checkout_status_location(invoice.safe_number, result="unavailable"),
                status_code=303,
            )
        url = operation.request_snapshot.get("confirmation_url")
        if operation.state == "provider_pending" and is_allowed_confirmation_url(url):
            return _checkout_operation_redirect(url, status_code=303)
        return RedirectResponse(_checkout_status_location(invoice.safe_number), status_code=303)
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
            checkout_enabled=billing_checkout_allowed(settings, tenant_scope.workspace_id),
        )
    except BillingCheckoutDisabled:
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
        if operation.state == "provider_pending" and is_allowed_confirmation_url(confirmation_url):
            return _checkout_operation_redirect(confirmation_url, status_code=303)
        return RedirectResponse(
            _checkout_status_location(safe_number, result="unchanged"), status_code=303
        )
    if operation.request_snapshot.get("purchase_schema") == 2:
        return RedirectResponse(
            _checkout_status_location(safe_number, result="unchanged"), status_code=303
        )
    if provider_key_is_expired(expires_at=operation.provider_key_expires_at):
        operation.state = "canceled"
        invoice.status = "canceled"
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
        await lock_storage_workspace(db, tenant_scope.workspace_id)
        await db.refresh(operation, with_for_update=True)
        await db.refresh(invoice, with_for_update=True)
        confirmation_url = _bind_initial_checkout_payment(operation, invoice, payment)
        if subscription is not None and subscription.billing_owner_id != principal.user_id:
            subscription.billing_owner_id = principal.user_id
        await db.commit()
        return _checkout_operation_redirect(
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
        capacity = await effective_paid_storage(db, subscription=subscription, now=now)
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
        profile=await get_account_profile_view(db, tenant_scope) if db is not None else None,
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
        processing_reset_at_label=format_user_datetime(window_end, show_zone=True),
        trial_eligible=trial_eligible,
        billing_owner=billing_owner,
        billing_role=role,
        billing_enabled=billing_checkout_allowed(request.app.state.settings, tenant_scope.workspace_id),
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
    next_charge_label = (
        await _next_renewal_label(db, subscription, now=now) if active and db is not None else None
    )
    resume_charge_label = (
        await _next_renewal_label(db, subscription, now=now, for_resume=True)
        if active and db is not None
        else None
    )
    method_available = False
    payment_method_label = None
    resume_quote_id = None
    pending_charge_amount_label = None
    prepared_charge_amount_label = None
    next_charge_amount_label = None
    pending_invoice = None
    receipt_contact = await _verified_receipt_contact(db, principal.user_id) if db is not None else None
    renewal_notice, renewal_action_url, renewal_action_label = _renewal_notice(subscription)
    if db is not None and subscription is not None:
        payment_method_label = await db.scalar(
            select(BillingPaymentMethod.masked_label).where(
                BillingPaymentMethod.workspace_id == tenant_scope.workspace_id,
                BillingPaymentMethod.owner_user_id == principal.user_id,
                BillingPaymentMethod.is_default.is_(True),
                BillingPaymentMethod.state == "active",
                BillingPaymentMethod.verified_at.is_not(None),
            )
        )
        method_available = payment_method_label is not None
        approved_catalog = await _approved_personal_catalog(db, now=now)
        cycle_catalog = approved_catalog.get(subscription.cycle)
        if cycle_catalog is not None:
            try:
                cycle_catalog, _ = await compose_personal_catalog(
                    db, base=cycle_catalog, subscription=subscription, now=now
                )
            except PurchaseError:
                cycle_catalog = None
        next_charge_amount_label = _billing_amount_label(
            cycle_catalog.amount_minor if cycle_catalog is not None else None
        )
        awaiting_invoices = await db.execute(
            select(BillingInvoice, BillingOperation)
            .join(BillingOperation, BillingOperation.id == BillingInvoice.operation_id)
            .where(
                BillingInvoice.workspace_id == tenant_scope.workspace_id,
                BillingOperation.kind.in_(("renewal", "early_renewal")),
                BillingOperation.state.in_(CHECKOUT_BLOCKING_STATES),
            )
            .order_by(BillingInvoice.created_at.desc())
        )
        for invoice, operation in awaiting_invoices:
            if operation.kind == "renewal" and operation.state == "scheduled" and operation.provider_id is None:
                if prepared_charge_amount_label is None:
                    prepared_charge_amount_label = _billing_amount_label(invoice.amount_minor, invoice.currency)
            elif pending_invoice is None:
                pending_invoice = invoice
                pending_charge_amount_label = _billing_amount_label(invoice.amount_minor, invoice.currency)

    if (
        db is not None
        and active
        and subscription is not None
        and not subscription.recurring_allowed
        and billing_checkout_allowed(request.app.state.settings, tenant_scope.workspace_id)
        and method_available
        and subscription.renewal_resolution != "receipt_contact_required"
    ):
        try:
            resume_snapshot = await _resume_renewal_snapshot(db, subscription=subscription, now=now)
            bound = await create_purchase_quote(
                db,
                workspace_id=tenant_scope.workspace_id,
                owner_user_id=principal.user_id,
                purpose="resume_renewal",
                subscription=subscription,
                snapshot=resume_snapshot,
                now=now,
            )
            resume_quote_id = str(bound.id)
            await db.commit()
        except PurchaseError:
            # No mutation has happened when quote preparation is unavailable.
            # Rolling back here would expire the subscription used by the view.
            pass
    content = _page_shell(
        "Управление подпиской",
        embedded=_is_embedded_request(request),
        profile=await get_account_profile_view(db, tenant_scope) if db is not None else None,
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
        next_charge_label=next_charge_label,
        resume_charge_label=resume_charge_label,
        resume_quote_id=resume_quote_id,
        method_available=method_available,
        receipt_contact_ready=bool(receipt_contact),
        receipt_contact_action_url=_receipt_contact_action_url(
            request, next_path="/billing/subscription",
        ),
        early_preview_error=getattr(request.state, "early_preview_error", None),
        early_promo_code=getattr(request.state, "early_promo_code", ""),
        payment_method_label=mask_payment_method(payment_method_label),
        next_charge_amount_label=next_charge_amount_label,
        pending_charge_amount_label=pending_charge_amount_label,
        prepared_charge_amount_label=prepared_charge_amount_label,
        pending_payment_url=_checkout_status_location(pending_invoice.safe_number)
        if pending_invoice else None,
        renewal_notice=renewal_notice,
        renewal_action_url=renewal_action_url,
        renewal_action_label=renewal_action_label,
        manual_checkout_url=f"/billing/checkout?cycle={'year' if subscription and subscription.cycle == 'year' else 'month'}",
        subscription_cycle_label="год"
        if subscription and subscription.cycle == "year"
        else "месяц",
        next_capacity_label=_capacity_label(subscription.next_capacity_bytes)
        if subscription and subscription.next_capacity_bytes
        else None,
        billing_enabled=billing_checkout_allowed(request.app.state.settings, tenant_scope.workspace_id),
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
        profile=await get_account_profile_view(db, tenant_scope) if db is not None else None,
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_payment_method", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_payment_method_content.html",
        manual_checkout_url=f"/billing/checkout?cycle={'year' if subscription and subscription.cycle == 'year' else 'month'}",
        method_label=method.masked_label if method is not None else None,
        method_kind=method.kind if method is not None else None,
        method_kind_label=_payment_method_kind_label(method.kind if method is not None else None),
        method_present=method is not None,
        renewal_allowed=bool(subscription is not None and subscription.recurring_allowed),
        paid_until_label=_billing_datetime_label(subscription.paid_through)
        if subscription is not None
        else None,
        billing_enabled=billing_checkout_allowed(request.app.state.settings, tenant_scope.workspace_id),
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
            profile=await get_account_profile_view(db, tenant_scope) if db is not None else None,
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
        await effective_paid_storage(db, subscription=subscription, now=now)
        if subscription is not None and effective_plan in {"trial", "personal"}
        else FREE_STORAGE_BYTES
    )
    storage_prices = await storage_catalog(db, now=now)
    base = (await _approved_personal_catalog(db, now=now)).get(
        subscription.cycle if subscription else "month"
    )
    options = []
    if base is not None:
        for capacity in (PERSONAL_STORAGE_BYTES, *ADDON_CAPACITY_BYTES):
            price = storage_prices.get((capacity, subscription.cycle if subscription else "month"))
            if capacity != PERSONAL_STORAGE_BYTES and price is None:
                continue
            options.append(
                {
                    "capacity": capacity,
                    "package_count": storage_package_count(capacity),
                    "label": _capacity_label(capacity),
                    "addon_label": _billing_price_label(price.amount_minor if price else 0),
                    "total_label": _billing_price_label(
                        base.amount_minor + (price.amount_minor if price else 0)
                    ),
                    "cycle_label": "месяц" if base.cycle == "month" else "год",
                }
            )
    selected_package_count = storage_package_count(
        max(PERSONAL_STORAGE_BYTES, subscription.next_capacity_bytes or current_capacity)
    ) if subscription else 0
    selected_package_count = next(
        (option["package_count"] for option in options
         if str(option["package_count"]) == str(getattr(
             request.state, "storage_package_count", request.query_params.get("package_count"),
         ))),
        selected_package_count,
    )
    receipt_contact = await _verified_receipt_contact(db, principal.user_id)
    content = _page_shell(
        "Увеличение хранилища",
        embedded=_is_embedded_request(request),
        profile=await get_account_profile_view(db, tenant_scope) if db is not None else None,
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request, "billing_storage_addons", principal=principal, tenant_scope=tenant_scope
        ),
        content_template="cabinet/pages/billing_storage_content.html",
        current_capacity=current_capacity,
        current_capacity_label=_capacity_label(current_capacity),
        storage_options=options,
        selected_package_count=selected_package_count,
        storage_preview_error=getattr(request.state, "storage_preview_error", None),
        storage_promo_code=getattr(request.state, "storage_promo_code", ""),
        receipt_contact_ready=bool(receipt_contact),
        receipt_contact_action_url=_receipt_contact_action_url(
            request, next_path=f"/billing/storage?package_count={selected_package_count}",
        ),
        receipt_contact_message="Подтвердите email для чека в аккаунте, затем вернитесь к выбору места.",
        storage_timeline=[
            {
                "start": _billing_datetime_label(item["starts_at"]),
                "end": _billing_datetime_label(item["ends_at"]),
                "capacity": _capacity_label(item["capacity_bytes"]),
                "bonus": item["bonus"],
            }
            for item in await storage_period_timeline(db, subscription=subscription, now=now)
        ]
        if subscription and effective_plan == "personal"
        else [],
        next_capacity_label=_capacity_label(subscription.next_capacity_bytes)
        if subscription and subscription.next_capacity_bytes
        else None,
        selection_version=subscription.next_capacity_version if subscription else 0,
        paid_through_label=_billing_datetime_label(subscription.paid_through)
        if subscription
        else None,
        eligible=effective_plan == "personal",
        billing_enabled=billing_checkout_allowed(request.app.state.settings, tenant_scope.workspace_id),
        result=request.query_params.get("result"),
    )
    return cabinet_html_response(content)


async def _billing_owner_subscription(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
) -> WorkspaceSubscription | None:
    await lock_storage_workspace(db, tenant_scope.workspace_id)
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
    if subscription is None or subscription.paid_through is None:
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
    await cancel_unsent_renewals(
        db, workspace_id=tenant_scope.workspace_id, reason="authority_cancelled"
    )
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
    await enqueue_billing_notification(
        db,
        workspace_id=tenant_scope.workspace_id,
        recipient_id=principal.user_id,
        event_id=f"subscription:{tenant_scope.workspace_id}:authority:{changed.authority_version}",
        kind=BillingNotification.AUTORENEWAL_DISABLED,
        payload={"action_path": "/billing/subscription"},
        marketing_allowed=False,
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
    resume_quote_id: str = Form(default="", max_length=64),
) -> RedirectResponse:
    if db is None or not principal.auth_via_session:
        return RedirectResponse("/billing/subscription?result=unavailable", status_code=303)
    if not billing_checkout_allowed(request.app.state.settings, tenant_scope.workspace_id):
        return RedirectResponse("/billing/subscription?result=unavailable", status_code=303)
    await lock_storage_workspace(db, tenant_scope.workspace_id)
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
        now = datetime.now(UTC)
        resume_quote = await validate_purchase_quote(
            db,
            quote_id=UUID(resume_quote_id),
            workspace_id=tenant_scope.workspace_id,
            owner_user_id=principal.user_id,
            purpose="resume_renewal",
            subscription=subscription,
            now=now,
            expected_snapshot=await _resume_renewal_snapshot(
                db, subscription=subscription, now=now
            ),
        )
    except ValueError:
        await db.rollback()
        return RedirectResponse("/billing/subscription?result=conflict", status_code=303)
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
    accept_base_price(subscription, resume_quote.snapshot["catalog_snapshot"], resume_quote.snapshot.get("storage_price_snapshot"))
    accept_storage_price(subscription, resume_quote.snapshot.get("storage_price_snapshot"))
    subscription.renewal_resolution = None
    subscription.recurring_allowed = changed.recurring_allowed
    subscription.recurring_authority_version = changed.authority_version
    subscription.application_version += 1
    consent_operation = BillingOperation(
        workspace_id=tenant_scope.workspace_id, kind="resume_renewal",
        idempotency_key=f"resume:{resume_quote.id}", state="succeeded",
        request_snapshot=resume_quote.snapshot,
    )
    db.add(consent_operation)
    await db.flush()
    resume_quote.consumed_operation_id = consent_operation.id
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
    await enqueue_billing_notification(
        db,
        workspace_id=tenant_scope.workspace_id,
        recipient_id=principal.user_id,
        event_id=f"subscription:{tenant_scope.workspace_id}:authority:{changed.authority_version}",
        kind=BillingNotification.AUTORENEWAL_ENABLED,
        payload={"action_path": "/billing/subscription"},
        marketing_allowed=False,
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
    checkout_result = getattr(
        request.state, "billing_checkout_result", request.query_params.get("result")
    )
    blocking_operation = (
        await db.scalar(_blocking_payment_operation_query(tenant_scope.workspace_id).limit(1))
        if db is not None
        else None
    )
    if blocking_operation is not None:
        checkout_result = "pending"
    blocking_invoice = (
        await db.scalar(select(BillingInvoice).where(
            BillingInvoice.workspace_id == tenant_scope.workspace_id,
            BillingInvoice.operation_id == blocking_operation.id,
        ))
        if db is not None and blocking_operation is not None else None
    )
    checkout_blocked = checkout_result == "pending"
    continuation_candidate = (
        blocking_operation.request_snapshot.get("confirmation_url")
        if blocking_operation is not None
        and blocking_operation.kind == "initial_checkout"
        and blocking_operation.state == "provider_pending"
        and blocking_operation.request_snapshot.get("billing_actor_user_id")
        in {None, str(principal.user_id)}
        and billing_checkout_allowed(settings, tenant_scope.workspace_id)
        else None
    )
    checkout_continuation_url = (
        continuation_candidate if is_allowed_confirmation_url(continuation_candidate) else None
    )
    saved_draft = _checkout_promo_draft(request, principal=principal, tenant_scope=tenant_scope)
    checkout_promo_code = saved_draft["code"] if saved_draft else ""
    # Direct POST rejection must not replay stale form input into the preview.
    checkout_cycle = (
        saved_draft["cycle"] if saved_draft else getattr(request.state, "billing_checkout_cycle", None)
    ) if request.method == "POST" else request.query_params.get("cycle")
    descriptor = plan_descriptor("personal")
    receipt_contact = await _verified_receipt_contact(db, principal.user_id)
    now = datetime.now(UTC)
    subscription = (
        await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id
            )
        )
        if db is not None
        else None
    )
    if checkout_cycle not in {"month", "year"}:
        checkout_cycle = saved_draft["cycle"] if saved_draft else (
            subscription.cycle
            if subscription and subscription.cycle in {"month", "year"}
            else "month"
        )
    catalog = await _approved_personal_catalog(db, now=now)
    base_catalog = dict(catalog)
    storage_prices = {}
    composition_error = None
    if db is not None:
        try:
            for catalog_cycle, base in base_catalog.items():
                (
                    catalog[catalog_cycle],
                    storage_prices[catalog_cycle],
                ) = await compose_personal_catalog(
                    db,
                    base=base,
                    subscription=subscription,
                    now=now,
                )
        except PurchaseError as exc:
            catalog = {}
            composition_error = str(exc)
    quote_id = None
    period_label = None
    next_attempt_label = None
    monthly_catalog = catalog.get("month")
    annual_catalog = catalog.get("year")
    catalog_ready = monthly_catalog is not None and annual_catalog is not None
    monthly_amount = monthly_catalog.amount_minor if monthly_catalog is not None else None
    annual_amount = annual_catalog.amount_minor if annual_catalog is not None else None
    catalog_storage = (
        monthly_catalog.storage_bytes if monthly_catalog is not None else descriptor.storage_bytes
    )
    offer_version = (
        monthly_catalog.offer_version
        if monthly_catalog is not None
        else PUBLIC_APPROVED_OFFER_VERSION
    )
    checkout_preview_data: dict[str, str] | None = None
    checkout_has_discount = False
    promo_preview_error: str | None = composition_error
    selected_catalog = catalog.get(checkout_cycle)
    if (
        not checkout_blocked
        and billing_checkout_allowed(settings, tenant_scope.workspace_id)
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
            preview = checkout_preview(
                plan_code="personal",
                cycle=checkout_cycle,
                promo=chosen,
                provider_floor_minor=settings.billing_provider_floor_minor,
                catalog_snapshot=selected_catalog,
            )
            bound_quote = await create_purchase_quote(
                db,
                workspace_id=tenant_scope.workspace_id,
                owner_user_id=principal.user_id,
                purpose="initial_checkout",
                subscription=subscription,
                now=now,
                snapshot=checkout_quote_snapshot(
                    catalog=selected_catalog,
                    storage_price=storage_prices.get(checkout_cycle),
                    preview=preview,
                    promo=chosen,
                    discount_source=discount_source,
                ),
            )
            quote_id = str(bound_quote.id)
            await db.commit()
            period_start = (
                max(now, subscription.paid_through)
                if subscription and subscription.paid_through
                else now
            )
            period_end = _add_paid_interval(period_start, checkout_cycle)
            period_label = (
                f"{format_user_datetime(period_start, show_zone=True)} — {format_user_datetime(period_end, show_zone=True)}"
                if period_start > now
                else "Месяц после подтверждения оплаты"
                if checkout_cycle == "month"
                else "Год после подтверждения оплаты"
            )
            next_attempt_label = (
                format_user_datetime(period_end - timedelta(hours=72), show_zone=True)
                if period_start > now
                else "За 3 дня до конца оплаченного периода; точная дата появится после оплаты"
            )
            checkout_preview_data = checkout_preview_labels(
                preview,
                discount_percent=chosen.discount_percent if chosen is not None else None,
                discount_source=discount_source,
            )
            checkout_has_discount = preview.payable_amount_minor < preview.list_amount_minor
        except (PromoError, PurchaseError) as exc:
            promo_preview_error = str(exc)
        except ValueError:
            promo_preview_error = "Промокод временно недоступен. Проверьте код позже."
    content = _page_shell(
        "Выбор тарифа",
        embedded=_is_embedded_request(request),
        profile=await get_account_profile_view(db, tenant_scope) if db is not None else None,
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
        billing_enabled=billing_checkout_allowed(settings, tenant_scope.workspace_id),
        plan=descriptor,
        monthly_price_label=_billing_price_label(monthly_amount),
        annual_price_label=_billing_price_label(annual_amount),
        annual_saving_label=_annual_saving_label(monthly_amount, annual_amount),
        catalog_ready=catalog_ready,
        catalog_storage_label=_capacity_label(catalog_storage),
        offer_version_label=offer_version,
        checkout_quote_id=quote_id,
        checkout_base_price_label=_billing_price_label(base_catalog[checkout_cycle].amount_minor)
        if checkout_cycle in base_catalog
        else None,
        checkout_storage_price_label=_billing_price_label(
            storage_prices[checkout_cycle].amount_minor
        )
        if storage_prices.get(checkout_cycle)
        else None,
        checkout_period_label=period_label,
        checkout_next_attempt_label=next_attempt_label,
        checkout_idempotency_key=f"web-{principal.user_id}-{uuid4().hex}",
        checkout_result=checkout_result,
        checkout_blocked=checkout_blocked,
        checkout_status_url=_checkout_status_location(blocking_invoice.safe_number)
        if blocking_invoice else None,
        checkout_continuation_url=checkout_continuation_url,
        checkout_promo_code=checkout_promo_code,
        checkout_cycle=checkout_cycle,
        checkout_preview=checkout_preview_data,
        checkout_has_discount=checkout_has_discount,
        promo_preview_error=promo_preview_error,
        receipt_contact_ready=bool(receipt_contact),
        receipt_contact_action_url=_receipt_contact_action_url(
            request, next_path=f"/billing/checkout?cycle={checkout_cycle}",
        ),
        receipt_contact_message="Подтвердите email для чека в аккаунте, затем вернитесь к оформлению.",
        receipt_contact_label=_masked_receipt_contact(receipt_contact),
    )
    response = cabinet_html_response(content)
    if blocking_operation is not None or (
        request.cookies.get(_CHECKOUT_PROMO_DRAFT_COOKIE) and saved_draft is None
    ):
        _clear_checkout_promo_draft(response)
    elif (
        request.method == "GET" and saved_draft
        and request.query_params.get("cycle") in {"month", "year"}
        and checkout_cycle != saved_draft["cycle"]
    ):
        updated_choice = _checkout_result_redirect(
            request, "promo_applied", cycle=checkout_cycle,
            principal=principal, tenant_scope=tenant_scope,
        )
        for header in updated_choice.headers.getlist("set-cookie"):
            response.headers.append("set-cookie", header)
    elif request.cookies.get(_CHECKOUT_PROMO_COOKIE):
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
    preview_action: str = Form(default="apply", max_length=16),
    previous_promo_code: str = Form(default="", max_length=48),
) -> RedirectResponse:
    """Validate a promo and show its price without reserving or charging."""
    settings = request.app.state.settings
    if preview_action in {"month", "year"}:
        cycle = preview_action
    # A presentation hint detects an edit; it never authorizes a discount.
    # Same input on an expired page must not restart the original five minutes.
    replace_promo = preview_action == "apply" or (
        bool((promo_code or "").strip())
        and promo_code != previous_promo_code
    )
    if not replace_promo:
        saved_draft = _checkout_promo_draft(
            request, principal=principal, tenant_scope=tenant_scope
        )
        if saved_draft is not None:
            promo_code = saved_draft["code"]
    if db is None or not billing_checkout_allowed(settings, tenant_scope.workspace_id):
        return _checkout_result_redirect(
            request, "unavailable", cycle=cycle, promo_code=promo_code,
            principal=principal, tenant_scope=tenant_scope, replace_promo=replace_promo,
        )
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
        return _checkout_result_redirect(request, "promo_invalid", promo_code=promo_code, principal=principal, tenant_scope=tenant_scope)
    try:
        catalog = await _approved_personal_catalog(db, now=datetime.now(UTC))
        catalog_snapshot = catalog.get(cycle)
        if catalog_snapshot is None:
            return _checkout_result_redirect(
                request, "catalog_not_approved", cycle=cycle, promo_code=promo_code,
                principal=principal, tenant_scope=tenant_scope, replace_promo=replace_promo,
            )
        if (
            preview_action in {"month", "year"} and not replace_promo
            and saved_draft is None and (promo_code or "").strip()
        ):
            return _checkout_result_redirect(
                request, "promo_expired", cycle=cycle,
                principal=principal, tenant_scope=tenant_scope,
            )
        if not (promo_code or "").strip():
            return _checkout_result_redirect(
                request, "promo_applied", cycle=cycle, promo_code="",
                principal=principal, tenant_scope=tenant_scope, replace_promo=replace_promo,
            )
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
            principal=principal,
            tenant_scope=tenant_scope,
            replace_promo=replace_promo,
        )
    return _checkout_result_redirect(
        request,
        "promo_applied",
        promo_code=promo_code,
        cycle=cycle,
        principal=principal,
        tenant_scope=tenant_scope,
        replace_promo=replace_promo,
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
    quote_id: str = Form(default="", max_length=64),
    offer_consent: bool = Form(default=False),
    recurring_consent: bool = Form(default=False),
    offer_version: str = Form(default="", max_length=64),
    promo_code: str | None = Form(default=None, max_length=48),
) -> HTMLResponse:
    settings = request.app.state.settings
    if db is None:
        return _checkout_result_redirect(request, "unavailable", cycle=cycle, promo_code=promo_code, principal=principal, tenant_scope=tenant_scope)
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
    dispatch_state = {"started": False}
    try:
        await lock_storage_workspace(db, tenant_scope.workspace_id)
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
            return _checkout_result_redirect(request, "owner_only", cycle=cycle, promo_code=promo_code, principal=principal, tenant_scope=tenant_scope)
        receipt_contact = await _verified_receipt_contact(db, principal.user_id)
        require_billing_enabled(
            checkout_enabled=billing_checkout_allowed(settings, tenant_scope.workspace_id),
        )
        key = idempotency_key.strip()
        if not key:
            return _checkout_result_redirect(request, "invalid", cycle=cycle, promo_code=promo_code, principal=principal, tenant_scope=tenant_scope)
        if not offer_consent:
            return _checkout_result_redirect(request, "offer_required", cycle=cycle, promo_code=promo_code, principal=principal, tenant_scope=tenant_scope)

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
                return _checkout_operation_redirect(confirmation_url, status_code=303)
            existing_invoice = await db.scalar(
                select(BillingInvoice).where(BillingInvoice.operation_id == existing.id)
            )
            if existing_invoice is not None:
                return _checkout_operation_redirect(
                    _checkout_status_location(existing_invoice.safe_number),
                    status_code=303,
                )
            return _checkout_operation_redirect("/billing?result=pending", status_code=303)
        if not receipt_contact:
            blocker = await db.scalar(
                _blocking_payment_operation_query(tenant_scope.workspace_id).limit(1)
            )
            if blocker is not None:
                blocked_invoice = await db.scalar(select(BillingInvoice).where(
                    BillingInvoice.workspace_id == tenant_scope.workspace_id,
                    BillingInvoice.operation_id == blocker.id,
                ))
                return _checkout_operation_redirect(
                    _checkout_status_location(blocked_invoice.safe_number)
                    if blocked_invoice else "/billing?result=pending",
                    status_code=303,
                )
            return _checkout_result_redirect(
                request, "receipt_contact_required", cycle=cycle, promo_code=promo_code,
                principal=principal,
                tenant_scope=tenant_scope,
            )
        now = datetime.now(UTC)
        # An active paid period must never block a new payment: a person who
        # wants to pay early can pay at any moment, and the granted period is
        # added to the paid remainder instead of replacing it.

        # New money mutation must use an enabled, effective database catalog
        # row.  Static descriptors remain useful for read-only copy and unit
        # tests, but are never a checkout authority once the billing DB is
        # available.  An absent/stale/disabled row therefore fails closed.
        catalog_snapshot = (await _approved_personal_catalog(db, now=now)).get(cycle)
        if catalog_snapshot is None:
            return _checkout_result_redirect(request, "catalog_not_approved", cycle=cycle, promo_code=promo_code, principal=principal, tenant_scope=tenant_scope)
        if offer_version != catalog_snapshot.offer_version:
            request.state.billing_checkout_result = "offer_changed"
            request.state.billing_checkout_cycle = cycle
            response = await billing_checkout_page(
                request,
                tenant_scope=tenant_scope,
                principal=principal,
                db=db,
            )
            response.status_code = 409
            return response

        catalog_snapshot, storage_price = await compose_personal_catalog(
            db,
            base=catalog_snapshot,
            subscription=subscription,
            now=now,
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
                    principal=principal,
                    tenant_scope=tenant_scope,
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
            chosen, discount_source = _choose_checkout_discount(
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
                principal=principal,
                tenant_scope=tenant_scope,
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
        try:
            bound_quote = await validate_purchase_quote(
                db,
                quote_id=UUID(quote_id),
                workspace_id=tenant_scope.workspace_id,
                owner_user_id=principal.user_id,
                purpose="initial_checkout",
                subscription=subscription,
                now=now,
                expected_snapshot=checkout_quote_snapshot(
                    catalog=catalog_snapshot,
                    storage_price=storage_price,
                    preview=preview,
                    promo=promo,
                    discount_source=discount_source,
                ),
            )
        except (PurchaseError, ValueError):
            await db.rollback()
            request.state.billing_checkout_result = "quote_changed"
            request.state.billing_checkout_cycle = cycle
            response = await billing_checkout_page(
                request,
                tenant_scope=tenant_scope,
                principal=principal,
                db=db,
            )
            response.status_code = 409
            return response
        await cancel_unsent_renewals(
            db, workspace_id=tenant_scope.workspace_id, reason="checkout_selected"
        )
        unresolved_payment = await db.scalar(
            _blocking_payment_operation_query(tenant_scope.workspace_id).with_for_update()
        )
        if unresolved_payment is not None:
            confirmation_url = unresolved_payment.request_snapshot.get("confirmation_url")
            if is_allowed_confirmation_url(confirmation_url):
                return _checkout_operation_redirect(confirmation_url, status_code=303)
            unresolved_invoice = await db.scalar(
                select(BillingInvoice).where(BillingInvoice.operation_id == unresolved_payment.id)
            )
            if unresolved_invoice is not None:
                return _checkout_operation_redirect(
                    _checkout_status_location(unresolved_invoice.safe_number),
                    status_code=303,
                )
            return _checkout_operation_redirect("/billing?result=pending", status_code=303)
        provider_environment(settings.billing_yookassa_environment)
        intent = build_checkout_intent(
            workspace_id=tenant_scope.workspace_id, idempotency_key=key, preview=preview
        )
        if subscription is None:
            subscription = WorkspaceSubscription(workspace_id=tenant_scope.workspace_id, billing_owner_id=principal.user_id)
            db.add(subscription)
            await db.flush()
        accept_base_price(subscription, catalog_snapshot.as_dict(), storage_price_snapshot(storage_price))
        accept_storage_price(subscription, storage_price_snapshot(storage_price))
        consent_at = datetime.now(UTC).isoformat()
        operation = BillingOperation(
            id=intent.operation_id,
            workspace_id=tenant_scope.workspace_id,
            kind="initial_checkout",
            idempotency_key=intent.idempotency_key,
            state="processing",
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
                "storage_price_snapshot": storage_price_snapshot(storage_price),
                "quote_id": str(bound_quote.id),
                "purchase_schema": 2,
                "purchase_purpose": "initial_checkout",
                "provider_shop_id": settings.billing_yookassa_shop_id,
                "provider_environment": settings.billing_yookassa_environment,
                "recurring_authority_version": subscription.recurring_authority_version
                if subscription
                else 0,
                "selection_version": subscription.next_capacity_version if subscription else 0,
                "offer_consent": True,
                "recurring_consent": recurring_consent,
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
                "storage_price_snapshot": storage_price_snapshot(storage_price),
                "quote_id": str(bound_quote.id),
                "purchase_schema": 2,
                "purchase_purpose": "initial_checkout",
                "provider_shop_id": settings.billing_yookassa_shop_id,
                "provider_environment": settings.billing_yookassa_environment,
                "recurring_authority_version": subscription.recurring_authority_version
                if subscription
                else 0,
                "selection_version": subscription.next_capacity_version if subscription else 0,
                "offer_consent": True,
                "recurring_consent": recurring_consent,
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
                return _checkout_result_redirect(request, "promo_invalid", promo_code=promo_code, cycle=cycle, principal=principal, tenant_scope=tenant_scope)
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
        if subscription is not None and subscription.billing_owner_id != principal.user_id:
            # An owner who replaced the designated billing owner must make a
            # fresh hosted payment before future renewals can use this account.
            subscription.billing_owner_id = principal.user_id
        bound_quote.consumed_operation_id = operation.id
        await reserve_acceptance_budget(
            db,
            workspace_id=tenant_scope.workspace_id,
            operation_id=operation.id,
            amount_minor=invoice.amount_minor,
            now=now,
        )
        await db.commit()
        return_url = billing_checkout_return_url(request, safe_invoice_number=intent.invoice_number)
        payment = await _create_initial_checkout_payment(
            settings=settings,
            operation=operation,
            invoice=invoice,
            return_url=return_url,
            dispatch_state=dispatch_state,
        )
        await lock_storage_workspace(db, tenant_scope.workspace_id)
        await db.refresh(operation, with_for_update=True)
        await db.refresh(invoice, with_for_update=True)
        confirmation_url = _bind_initial_checkout_payment(operation, invoice, payment)
        await db.commit()
        return _checkout_operation_redirect(
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
                return _checkout_operation_redirect(winner_url, status_code=303)
            winner_invoice = await db.scalar(
                select(BillingInvoice).where(BillingInvoice.operation_id == winner.id)
            )
            if winner_invoice is not None:
                return _checkout_operation_redirect(
                    _checkout_status_location(winner_invoice.safe_number),
                    status_code=303,
                )
            return _checkout_operation_redirect("/billing?result=pending", status_code=303)
        return _checkout_result_redirect(request, "unavailable", cycle=cycle, promo_code=promo_code, principal=principal, tenant_scope=tenant_scope)
    except (
        BillingCheckoutDisabled,
        ValueError,
        YooKassaConfigurationError,
        YooKassaProviderError,
        httpx.HTTPError,
        OSError,
    ) as exc:
        await db.rollback()
        if isinstance(exc, AcceptanceBudgetUnavailable):
            return _checkout_result_redirect(
                request, "account_unavailable", cycle=cycle, promo_code=promo_code,
                principal=principal, tenant_scope=tenant_scope,
            )
        if "intent" in locals():
            await lock_storage_workspace(db, tenant_scope.workspace_id)
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
                    await _persist_initial_checkout_failure(
                        db, unresolved, invoice, exc,
                        dispatch_started=dispatch_state["started"],
                    )
                    await db.commit()
                    return _checkout_operation_redirect(
                        _checkout_status_location(
                            invoice.safe_number,
                            result="provider_unavailable",
                        ),
                        status_code=303,
                    )
        return _checkout_result_redirect(request, "unavailable", cycle=cycle, promo_code=promo_code, principal=principal, tenant_scope=tenant_scope)


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
    role = await _billing_role(db, tenant_scope=tenant_scope, principal=principal)
    can_manage = _can_manage_billing(role=role, subscription=subscription, principal=principal)
    if role != "owner":
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    invoices: list[dict[str, object]] = []
    if db is not None:
        query = select(BillingInvoice).where(
            BillingInvoice.workspace_id == tenant_scope.workspace_id
        )
        if not can_manage:
            query = query.where(
                BillingInvoice.plan_snapshot["service_resolution"].as_string().in_(
                    ("owner_changed", "workspace_scope_invalid")
                )
            )
        rows = await db.scalars(query.order_by(BillingInvoice.created_at.desc()).limit(100))
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
                    "purpose_label": purchase_purpose_label(snapshot),
                    "service_label": "Оплата подтверждена; услуга требует сверки"
                    if snapshot.get("service_resolution")
                    else None,
                    "service_period_label": (
                        _billing_datetime_label(snapshot.get("service_starts_at"))
                        + " — "
                        + _billing_datetime_label(snapshot.get("service_ends_at"))
                    )
                    if snapshot.get("service_starts_at") and snapshot.get("service_ends_at")
                    else None,
                    "discount_label": (
                        f"Скидка {snapshot.get('discount_percent')}%"
                        if isinstance(snapshot.get("discount_percent"), int)
                        else ("Реферальная скидка" if snapshot.get("referral_discount") else None)
                    ),
                    "payment_method_label": mask_payment_method(
                        snapshot.get("payment_method_label")
                        if can_manage and isinstance(snapshot.get("payment_method_label"), str)
                        else None
                    ),
                    "receipt_label": receipt_label(receipt_state) if can_manage else "Чек доступен плательщику",
                    "detail_url": f"/billing/invoices/{invoice.safe_number}",
                    "status_url": _checkout_status_location(invoice.safe_number)
                    if can_manage and invoice.status in {"pending", "unknown", "manual_resolution", "failed", "canceled"} else None,
                    "status_action_label": "Открыть статус платежа",
                    "refund_mailto": refund_mailto,
                }
            )
    content = _page_shell(
        "История платежей",
        embedded=_is_embedded_request(request),
        profile=await get_account_profile_view(db, tenant_scope) if db is not None else None,
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


def _invoice_capacity_label(snapshot: Mapping[str, object]) -> str | None:
    storage = snapshot.get("storage_price_snapshot")
    catalog = snapshot.get("catalog_snapshot")
    for value in (
        snapshot.get("target_capacity_bytes"),
        snapshot.get("storage_capacity_bytes"),
        storage.get("capacity_bytes") if isinstance(storage, Mapping) else None,
        catalog.get("storage_bytes") if isinstance(catalog, Mapping) else None,
    ):
        if type(value) is int and value > 0:
            return _capacity_label(value)
    return None


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
    role = await _billing_role(db, tenant_scope=tenant_scope, principal=principal)
    can_manage = _can_manage_billing(role=role, subscription=subscription, principal=principal)
    if role != "owner":
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
    if not can_manage and snapshot.get("service_resolution") not in {
        "owner_changed", "workspace_scope_invalid"
    }:
        return RedirectResponse("/billing/history?result=not_found", status_code=303)
    # The current owner receives service-gap notices even when the payer's
    # mandate belongs to the previous owner. This view grants no payment
    # authority and never exposes the previous payer's receipt or card.
    receipt_state = _receipt_registration_state(snapshot.get("receipt_registration"))
    receipt_url = snapshot.get("receipt_url") if receipt_state is ReceiptState.AVAILABLE else None
    if not can_manage or not is_allowed_confirmation_url(receipt_url):
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
        "Платеж",
        embedded=_is_embedded_request(request),
        profile=await get_account_profile_view(db, tenant_scope) if db is not None else None,
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
            "status_url": _checkout_status_location(invoice.safe_number)
            if can_manage and invoice.status in {"pending", "unknown", "manual_resolution", "failed", "canceled"} else None,
            "status_action_label": "Открыть статус платежа",
            "cycle_label": "Год" if snapshot.get("cycle") == "year" else "Месяц",
            "purpose_label": purchase_purpose_label(snapshot),
            "capacity_label": _invoice_capacity_label(snapshot),
            "storage_intervals": [
                {
                    "start": _billing_datetime_label(item["starts_at"]),
                    "end": _billing_datetime_label(item["ends_at"]),
                    "capacity": _capacity_label(item["capacity_bytes"]),
                }
                for item in snapshot.get("storage_segments", [])
                if isinstance(item, dict)
                and item.get("starts_at") and item.get("ends_at")
                and isinstance(item.get("capacity_bytes"), int)
            ],
            "service_label": "Оплата подтверждена; услуга требует сверки"
            if snapshot.get("service_resolution")
            else None,
            "service_period_label": (
                _billing_datetime_label(snapshot.get("service_starts_at"))
                + " — "
                + _billing_datetime_label(snapshot.get("service_ends_at"))
            )
            if snapshot.get("service_starts_at") and snapshot.get("service_ends_at")
            else None,
            "status_label": _invoice_status_label(invoice.status),
            "discount_label": (
                f"Скидка {snapshot.get('discount_percent')}%"
                if isinstance(snapshot.get("discount_percent"), int)
                else ("Реферальная скидка" if snapshot.get("referral_discount") else None)
            ),
            "payment_method_label": mask_payment_method(
                snapshot.get("payment_method_label")
                if can_manage and isinstance(snapshot.get("payment_method_label"), str)
                else None
            ),
            "receipt_contact_label": _masked_receipt_contact(invoice.receipt_contact_snapshot) if can_manage else None,
            "receipt_label": receipt_label(receipt_state) if can_manage else "Чек доступен плательщику",
            "receipt_url": receipt_url,
            "refund_mailto": refund_mailto,
        },
        support_email=support_email,
    )
    return cabinet_html_response(content)


async def _purchase_error_page(
    request, tenant_scope, principal, db, message, *, status_code=409,
    action_url=None, action_label=None,
):
    content = _page_shell(
        "Подтверждение покупки",
        embedded=_is_embedded_request(request),
        profile=await get_account_profile_view(db, tenant_scope) if db is not None else None,
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        content_template="cabinet/pages/billing_purchase_content.html",
        support_email=request.app.state.settings.billing_support_email,
        purchase=None,
        purchase_error=message,
        purchase_error_action_url=action_url,
        purchase_error_action_label=action_label,
    )
    return cabinet_html_response(content, status_code=status_code)


async def _render_purchase_quote(request, tenant_scope, principal, db, bound_quote):
    value = bound_quote.snapshot
    receipt_contact = await _verified_receipt_contact(db, principal.user_id)
    next_storage_price = (
        value.get("next_storage_price") or value.get("storage_price_snapshot") or {}
    )
    next_storage_amount = next_storage_price.get("amount_minor", 0)
    content = _page_shell(
        "Подтверждение покупки",
        embedded=_is_embedded_request(request),
        profile=await get_account_profile_view(db, tenant_scope),
        active_nav="settings",
        settings_active="billing",
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        content_template="cabinet/pages/billing_purchase_content.html",
        support_email=request.app.state.settings.billing_support_email,
        purchase_error=None,
        receipt_contact_ready=bound_quote.purpose == "storage_schedule" or bool(receipt_contact),
        receipt_contact_action_url=_receipt_contact_action_url(
            request, next_path="/billing/subscription" if bound_quote.purpose == "early_renewal"
            else f"/billing/storage?package_count={storage_package_count(value['target_capacity_bytes'])}",
        ),
        receipt_contact_message="Подтвердите email для чека в аккаунте, затем вернитесь к покупке.",
        purchase={
            "quote_id": str(bound_quote.id),
            "purpose": bound_quote.purpose,
            "title": "Изменение объёма хранения"
            if bound_quote.purpose != "early_renewal"
            else "Досрочное продление",
            "capacity_label": _capacity_label(value["target_capacity_bytes"]),
            "package_count": storage_package_count(value["target_capacity_bytes"]),
            "list_label": _billing_price_label(value["list_amount_minor"]),
            "payable_label": _billing_price_label(value["payable_amount_minor"]),
            "discount_label": _billing_price_label(
                value["list_amount_minor"] - value["payable_amount_minor"]
            ),
            "has_discount": value["payable_amount_minor"] < value["list_amount_minor"],
            "next_label": _billing_price_label(value["next_amount_minor"]),
            "base_label": _billing_price_label(value["next_amount_minor"] - next_storage_amount),
            "storage_label": _billing_price_label(next_storage_amount),
            "current_capacity_label": _capacity_label(value["current_capacity_bytes"])
            if value.get("current_capacity_bytes")
            else None,
            "cycle_label": "месяц" if value["cycle"] == "month" else "год",
            "period_label": value["period_label"],
            "next_attempt_label": value.get("next_attempt_label"),
            "timeline": [
                {
                    "start": _billing_datetime_label(item["starts_at"]),
                    "end": _billing_datetime_label(item["ends_at"]),
                    "capacity": _capacity_label(item["capacity_bytes"]),
                    "bonus": item["bonus"],
                }
                for item in value.get("capacity_timeline", [])
            ],
            "recurring_allowed": value["recurring_allowed"],
            "method_label": value.get("payment_method_label"),
            "deferred": bound_quote.purpose == "storage_schedule",
        },
    )
    return cabinet_html_response(content)


@router.post("/billing/storage/preview", response_class=HTMLResponse, include_in_schema=False)
async def preview_storage_purchase(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
    package_count: int = Form(ge=0, le=99),
    promo_code: str = Form(default="", max_length=48),
):
    capacity_bytes = storage_package_capacity(package_count)
    if db is None:
        return await _purchase_error_page(
            request, tenant_scope, principal, db, "Оплата временно недоступна"
        )
    try:
        require_billing_enabled(
            checkout_enabled=billing_checkout_allowed(request.app.state.settings, tenant_scope.workspace_id)
        )
        if await _billing_role(db, tenant_scope=tenant_scope, principal=principal) != "owner":
            return RedirectResponse("/billing?result=owner_only", status_code=303)
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id,
            )
        )
        if subscription is None:
            raise PurchaseError("Сначала подключите тариф «Личный»")
        now = datetime.now(UTC)
        promo, campaign = None, None
        if promo_code.strip():
            promo, campaign = await _load_checkout_promo(
                db,
                workspace_id=tenant_scope.workspace_id,
                raw_code=promo_code,
                cycle=subscription.cycle,
                now=now,
                purpose="storage_upgrade",
            )
        calculation = await calculate_storage_purchase(
            db,
            subscription=subscription,
            target_capacity_bytes=capacity_bytes,
            now=now,
            discount_percent=promo.discount_percent if promo else 0,
            provider_floor_minor=request.app.state.settings.billing_provider_floor_minor,
        )
        if promo and promo.cycle is not None and any(
            item.cycle != promo.cycle for item in calculation.segments
        ):
            raise PromoError("Промокод не подходит ко всем оплачиваемым периодам")
        prices = await storage_catalog(db, now=now)
        price = prices.get((capacity_bytes, subscription.cycle))
        base = (await _approved_personal_catalog(db, now=now)).get(subscription.cycle)
        if base is None or (capacity_bytes != PERSONAL_STORAGE_BYTES and price is None):
            raise PurchaseError("Цена временно недоступна")
        purpose = "storage_schedule" if calculation.deferred_to_renewal else "storage_upgrade"
        snapshot = {
            "plan_code": "personal",
            "cycle": subscription.cycle,
            "list_amount_minor": calculation.list_amount_minor,
            "payable_amount_minor": calculation.payable_amount_minor,
            "target_capacity_bytes": capacity_bytes,
            "current_capacity_bytes": await effective_paid_storage(
                db, subscription=subscription, now=now
            ),
            "storage_segments": [item.as_dict() for item in calculation.segments],
            "capacity_timeline": await storage_period_timeline(
                db, subscription=subscription, now=now, upgraded_segments=calculation.segments
            ),
            "next_amount_minor": base.amount_minor + (price.amount_minor if price else 0),
            "next_storage_price": storage_price_snapshot(price),
            "base_catalog_snapshot": base.as_dict(),
            "selection_version": subscription.next_capacity_version,
            "period_label": (
                "Со следующего неоплаченного периода: "
                if purpose == "storage_schedule"
                else "С подтверждения оплаты до "
            )
            + format_user_datetime(subscription.paid_through, show_zone=True),
            "ends_at": utc(subscription.paid_through).isoformat(),
            "next_attempt_label": await _next_renewal_label(
                db, subscription, now=now, after_price_confirmation=purpose == "storage_schedule",
            ),
            "recurring_allowed": bool(subscription.recurring_allowed),
            "promo_code_hash": promo_code_hash(promo.code) if promo else None,
            "campaign_id": str(campaign.id) if campaign else None,
            "campaign_version": promo.campaign_version if promo else None,
            "discount_percent": promo.discount_percent if promo else None,
        }
        bound = await create_purchase_quote(
            db,
            workspace_id=tenant_scope.workspace_id,
            owner_user_id=principal.user_id,
            purpose=purpose,
            subscription=subscription,
            snapshot=snapshot,
            now=now,
        )
        await db.commit()
        return await _render_purchase_quote(request, tenant_scope, principal, db, bound)
    except (PurchaseError, PromoError, BillingCheckoutDisabled) as exc:
        await db.rollback()
        request.state.storage_preview_error = str(exc)
        request.state.storage_promo_code = promo_code
        request.state.storage_package_count = package_count
        response = await billing_storage_page(request, tenant_scope, principal, db)
        response.status_code = 409
        return response


@router.post(
    "/billing/subscription/early-preview", response_class=HTMLResponse, include_in_schema=False
)
async def preview_early_renewal(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
    promo_code: str = Form(default="", max_length=48),
):
    if db is None:
        return await _purchase_error_page(
            request, tenant_scope, principal, db, "Оплата временно недоступна"
        )
    try:
        require_billing_enabled(
            checkout_enabled=billing_checkout_allowed(request.app.state.settings, tenant_scope.workspace_id)
        )
        if await _billing_role(db, tenant_scope=tenant_scope, principal=principal) != "owner":
            return RedirectResponse("/billing?result=owner_only", status_code=303)
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == tenant_scope.workspace_id,
            )
        )
        now = datetime.now(UTC)
        if (
            subscription is None
            or subscription.plan_code != "personal"
            or not subscription.paid_through
            or subscription.paid_through <= now
        ):
            raise PurchaseError("Для досрочного продления нужна действующая подписка")
        method = await db.scalar(
            select(BillingPaymentMethod).where(
                BillingPaymentMethod.workspace_id == tenant_scope.workspace_id,
                BillingPaymentMethod.owner_user_id == principal.user_id,
                BillingPaymentMethod.state == "active",
                BillingPaymentMethod.is_default.is_(True),
                BillingPaymentMethod.verified_at.is_not(None),
            )
        )
        if method is None:
            raise PurchaseError("Сохранённая карта недоступна. Откройте обычную оплату тарифа")
        base = (await _approved_personal_catalog(db, now=now)).get(subscription.cycle)
        if base is None:
            raise PurchaseError("Цена временно недоступна")
        catalog, price = await compose_personal_catalog(
            db, base=base, subscription=subscription, now=now
        )
        promo, campaign = None, None
        if promo_code.strip():
            promo, campaign = await _load_checkout_promo(
                db,
                workspace_id=tenant_scope.workspace_id,
                raw_code=promo_code,
                cycle=subscription.cycle,
                now=now,
                purpose="early_renewal",
            )
        preview = checkout_preview(
            plan_code="personal",
            cycle=subscription.cycle,
            promo=promo,
            provider_floor_minor=request.app.state.settings.billing_provider_floor_minor,
            catalog_snapshot=catalog,
        )
        snapshot = checkout_quote_snapshot(
            catalog=catalog,
            storage_price=price,
            preview=preview,
            promo=promo,
            discount_source="promo" if promo else None,
        )
        snapshot.update(
            {
                "plan_code": "personal",
                "target_capacity_bytes": catalog.storage_bytes,
                "next_amount_minor": catalog.amount_minor,
                "period_label": format_user_datetime(subscription.paid_through, show_zone=True)
                + " — "
                + format_user_datetime(
                    _add_paid_interval(subscription.paid_through, subscription.cycle),
                    show_zone=True,
                ),
                "ends_at": utc(subscription.paid_through).isoformat(),
                "next_attempt_label": _billing_datetime_label(
                    _add_paid_interval(subscription.paid_through, subscription.cycle)
                    - timedelta(hours=72)
                )
                if subscription.recurring_allowed
                else "не запланирована",
                "recurring_allowed": bool(subscription.recurring_allowed),
                "recurring_authority_version": subscription.recurring_authority_version,
                "selection_version": subscription.next_capacity_version,
                "payment_method_id": str(method.id),
                "payment_method_label": method.masked_label,
                "campaign_id": str(campaign.id) if campaign else None,
            }
        )
        bound = await create_purchase_quote(
            db,
            workspace_id=tenant_scope.workspace_id,
            owner_user_id=principal.user_id,
            purpose="early_renewal",
            subscription=subscription,
            snapshot=snapshot,
            now=now,
        )
        await db.commit()
        return await _render_purchase_quote(request, tenant_scope, principal, db, bound)
    except (PurchaseError, PromoError, BillingCheckoutDisabled) as exc:
        await db.rollback()
        request.state.early_preview_error = str(exc)
        request.state.early_promo_code = promo_code
        response = await billing_subscription_page(request, tenant_scope, principal, db)
        response.status_code = 409
        return response


async def _reserve_purchase_promo(db, *, quote_snapshot, workspace_id, invoice, operation, now):
    campaign_id = quote_snapshot.get("campaign_id")
    if not campaign_id:
        return
    campaign = await db.scalar(
        select(PromotionCampaign).where(PromotionCampaign.id == UUID(campaign_id)).with_for_update()
    )
    if (
        campaign is None
        or not campaign.enabled
        or campaign.code_hash != quote_snapshot.get("promo_code_hash")
        or campaign.campaign_version != quote_snapshot.get("campaign_version")
        or campaign.discount_percent != quote_snapshot.get("discount_percent")
    ):
        raise PurchaseError("Промокод изменился. Проверьте расчёт заново")
    policy = campaign.policy_snapshot or {}
    if operation.kind not in policy.get("purposes", ["initial_checkout"]) or policy.get(
        "workspace_id"
    ) not in {None, str(workspace_id)}:
        raise PurchaseError("Промокод недоступен для этой покупки")
    await validate_acceptance_campaign(db, policy=policy, workspace_id=workspace_id, now=now)
    if (
        campaign.plan_code != "personal"
        or campaign.cycle not in {None, quote_snapshot["cycle"]}
        or (campaign.starts_at and campaign.starts_at > now)
        or (campaign.ends_at and campaign.ends_at <= now)
        or campaign.redeemed_count + campaign.reserved_count >= campaign.max_redemptions
    ):
        raise PurchaseError("Промокод больше недоступен")
    if campaign.cycle is not None and any(
        item.get("cycle") != campaign.cycle
        for item in quote_snapshot.get("storage_segments", [])
    ):
        raise PurchaseError("Промокод не подходит ко всем оплачиваемым периодам")
    redemption = await db.scalar(
        select(PromotionRedemption)
        .where(
            PromotionRedemption.workspace_id == workspace_id,
            PromotionRedemption.campaign_id == campaign.id,
        )
        .with_for_update()
    )
    if redemption is not None and redemption.state not in {"released", "expired"}:
        raise PurchaseError("Промокод уже использован или ожидает результата платежа")
    if redemption is None:
        redemption = PromotionRedemption(workspace_id=workspace_id, campaign_id=campaign.id)
        db.add(redemption)
    redemption.invoice_id = invoice.id
    redemption.reservation_key = operation.idempotency_key
    redemption.code_hash = campaign.code_hash
    redemption.list_amount_minor = quote_snapshot["list_amount_minor"]
    redemption.payable_amount_minor = invoice.amount_minor
    redemption.discount_percent = campaign.discount_percent
    redemption.state = "reserved"
    redemption.expires_at = now + timedelta(minutes=15)
    redemption.released_at = redemption.redeemed_at = None


@router.post("/billing/purchases/confirm", response_class=HTMLResponse, include_in_schema=False)
async def confirm_billing_purchase(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
    quote_id: str = Form(max_length=64),
    purchase_consent: bool = Form(default=False),
):
    if db is None:
        return await _purchase_error_page(
            request, tenant_scope, principal, db, "Оплата временно недоступна"
        )
    limited = await _billing_rate_limited_response(
        request, tenant_scope=tenant_scope, principal=principal, action="billing_checkout_start"
    )
    if limited is not None:
        return limited
    settings = request.app.state.settings
    operation, invoice = None, None
    dispatched = False
    persisted = False
    recovery_url = "/billing"
    try:
        require_billing_enabled(checkout_enabled=billing_checkout_allowed(settings, tenant_scope.workspace_id))
        await lock_storage_workspace(db, tenant_scope.workspace_id)
        subscription = await _billing_owner_subscription(
            db, tenant_scope=tenant_scope, principal=principal
        )
        if subscription is None:
            raise PurchaseError("Изменять подписку может только владелец")
        if not purchase_consent:
            raise PurchaseError("Подтвердите сумму и условия покупки")
        bound = await db.scalar(
            select(BillingPurchaseQuote)
            .where(
                BillingPurchaseQuote.id == UUID(quote_id),
                BillingPurchaseQuote.workspace_id == tenant_scope.workspace_id,
                BillingPurchaseQuote.owner_user_id == principal.user_id,
            )
            .with_for_update()
        )
        if bound is None or bound.purpose not in {
            "storage_upgrade",
            "storage_schedule",
            "early_renewal",
        }:
            raise PurchaseError("Расчёт недоступен. Откройте новую покупку")
        if bound.purpose == "early_renewal":
            recovery_url = "/billing/subscription"
        else:
            recovery_url = "/billing/storage"
            try:
                package_count = storage_package_count(bound.snapshot.get("target_capacity_bytes"))
            except ValueError:
                pass
            else:
                recovery_url += f"?package_count={package_count}"
        if bound.consumed_operation_id:
            previous_invoice = await db.scalar(
                select(BillingInvoice).where(
                    BillingInvoice.operation_id == bound.consumed_operation_id
                )
            )
            return RedirectResponse(
                _checkout_status_location(previous_invoice.safe_number)
                if previous_invoice
                else "/billing/storage?result=scheduled",
                status_code=303,
            )
        now = datetime.now(UTC)
        bound = await validate_purchase_quote(
            db,
            quote_id=bound.id,
            workspace_id=tenant_scope.workspace_id,
            owner_user_id=principal.user_id,
            purpose=bound.purpose,
            subscription=subscription,
            now=now,
        )
        value = bound.snapshot
        if utc(datetime.fromisoformat(value["ends_at"])) <= now:
            raise PurchaseError("Оплаченный период закончился. Откройте новый расчёт")
        base = (await _approved_personal_catalog(db, now=now)).get(value["cycle"])
        if base is None:
            raise PurchaseError("Цена временно недоступна")
        prices = await storage_catalog(db, now=now)
        if bound.purpose == "early_renewal":
            catalog, price = await compose_personal_catalog(
                db, base=base, subscription=subscription, now=now
            )
            if value.get("catalog_snapshot") != catalog.as_dict() or value.get(
                "storage_price_snapshot"
            ) != storage_price_snapshot(price):
                raise PurchaseError("Цена изменилась. Проверьте расчёт заново")
        else:
            price = prices.get((value["target_capacity_bytes"], value["cycle"]))
            if (
                value["next_storage_price"] != storage_price_snapshot(price)
                or value["base_catalog_snapshot"] != base.as_dict()
            ):
                raise PurchaseError("Цена изменилась. Проверьте расчёт заново")
            for segment in value["storage_segments"]:
                current_price = prices.get((segment["capacity_bytes"], segment["cycle"]))
                if current_price is None or str(current_price.id) != segment["catalog_version_id"]:
                    raise PurchaseError("Цена изменилась. Проверьте расчёт заново")
        if bound.purpose == "early_renewal":
            await cancel_unsent_renewals(
                db, workspace_id=tenant_scope.workspace_id, reason="early_renewal_selected"
            )
        blocker = await db.scalar(
            select(BillingOperation)
            .where(
                BillingOperation.workspace_id == tenant_scope.workspace_id,
                BillingOperation.state.in_(CHECKOUT_BLOCKING_STATES),
            )
            .limit(1)
            .with_for_update()
        )
        if blocker is not None:
            blocked_invoice = await db.scalar(select(BillingInvoice).where(
                BillingInvoice.workspace_id == tenant_scope.workspace_id,
                BillingInvoice.operation_id == blocker.id,
            ))
            if blocked_invoice is not None:
                return RedirectResponse(_checkout_status_location(blocked_invoice.safe_number), status_code=303)
            return await _purchase_error_page(
                request, tenant_scope, principal, db,
                "Проверяем предыдущую оплату. Повторно платить не нужно.",
                action_url="/billing/history#billing-help", action_label="Уточнить результат",
            )
        accept_base_price(subscription, base.as_dict())
        accept_storage_price(
            subscription, value.get("next_storage_price") or value.get("storage_price_snapshot")
        )
        if bound.purpose == "storage_schedule":
            subscription.renewal_resolution = None
            subscription.next_capacity_bytes = value["target_capacity_bytes"]
            subscription.next_capacity_version = (subscription.next_capacity_version or 0) + 1
            subscription.application_version = (subscription.application_version or 0) + 1
            # Immutable no-money audit operation also consumes this quote exactly once.
            operation = BillingOperation(
                workspace_id=tenant_scope.workspace_id,
                kind="storage_schedule",
                idempotency_key=f"purchase:{bound.id}",
                state="succeeded",
                request_snapshot=value,
            )
            db.add(operation)
            await db.flush()
            bound.consumed_operation_id = operation.id
            await _notify_storage_selection(db, subscription=subscription)
            await db.commit()
            return RedirectResponse("/billing/storage?result=scheduled", status_code=303)
        receipt_contact = await _verified_receipt_contact(db, principal.user_id)
        if not receipt_contact:
            next_path = (
                "/billing/subscription" if bound.purpose == "early_renewal"
                else f"/billing/storage?package_count={storage_package_count(value['target_capacity_bytes'])}"
            )
            await db.rollback()
            return await _purchase_error_page(
                request, tenant_scope, principal, db,
                "Подтвердите email для чека в аккаунте, затем вернитесь к покупке.",
                action_url=_receipt_contact_action_url(request, next_path=next_path),
                action_label="Подтвердить email",
            )
        provider_ref = None
        if bound.purpose == "early_renewal":
            from twobrain_rec_server.billing.payment_methods import (
                open_provider_reference,
                read_billing_encryption_key,
            )

            method = await db.scalar(
                select(BillingPaymentMethod)
                .where(
                    BillingPaymentMethod.id == UUID(value["payment_method_id"]),
                    BillingPaymentMethod.workspace_id == tenant_scope.workspace_id,
                    BillingPaymentMethod.owner_user_id == principal.user_id,
                    BillingPaymentMethod.is_default.is_(True),
                    BillingPaymentMethod.state == "active",
                    BillingPaymentMethod.verified_at.is_not(None),
                )
                .with_for_update()
            )
            key = read_billing_encryption_key(settings.credential_encryption_key_file)
            if method is None or key is None or method.key_version != "billing-v1":
                raise PurchaseError("Сохранённая карта недоступна")
            provider_ref = open_provider_reference(method.encrypted_provider_ref, key)
        snapshot = {
            **value,
            "purchase_schema": 2,
            "purchase_purpose": bound.purpose,
            "billing_actor_user_id": str(principal.user_id),
            "provider_shop_id": settings.billing_yookassa_shop_id,
            "provider_environment": provider_environment(settings.billing_yookassa_environment),
            "one_time_consent_at": now.isoformat(),
            "quote_id": str(bound.id),
        }
        operation = BillingOperation(
            workspace_id=tenant_scope.workspace_id,
            kind=bound.purpose,
            idempotency_key=f"purchase:{bound.id}",
            state="processing",
            provider_key_expires_at=now + timedelta(hours=24),
            request_snapshot=snapshot,
        )
        db.add(operation)
        await db.flush()
        invoice = BillingInvoice(
            workspace_id=tenant_scope.workspace_id,
            operation_id=operation.id,
            safe_number=f"INV-{uuid4().hex.upper()}",
            amount_minor=value["payable_amount_minor"],
            currency="RUB",
            status="pending",
            plan_snapshot=snapshot,
            receipt_contact_snapshot=receipt_contact,
        )
        db.add(invoice)
        await db.flush()
        await _reserve_purchase_promo(
            db,
            quote_snapshot=value,
            workspace_id=tenant_scope.workspace_id,
            invoice=invoice,
            operation=operation,
            now=now,
        )
        await reserve_acceptance_budget(
            db,
            workspace_id=tenant_scope.workspace_id,
            operation_id=operation.id,
            amount_minor=invoice.amount_minor,
            now=now,
        )
        description = (
            "GRAF: хранение, всего "
            if bound.purpose == "storage_upgrade"
            else "GRAF Личный и хранение, всего "
        ) + _capacity_label(value["target_capacity_bytes"])
        receipt = build_receipt_payload(
            receipt_contact=receipt_contact,
            amount_minor=invoice.amount_minor,
            currency="RUB",
            description=description,
            tax_system_code=settings.billing_receipt_tax_system_code,
            vat_code=settings.billing_receipt_vat_code,
            payment_subject=settings.billing_receipt_payment_subject,
            payment_mode=settings.billing_receipt_payment_mode,
        )
        return_url = billing_checkout_return_url(request, safe_invoice_number=invoice.safe_number)
        bound.consumed_operation_id = operation.id
        await db.commit()  # Budget, promo, invoice and consent precede the only POST.
        persisted = True
        async with YooKassaClient(settings) as provider:
            dispatched = True
            payment = await provider.create_payment(
                amount_minor=invoice.amount_minor,
                currency="RUB",
                description=description,
                idempotence_key=operation.idempotency_key,
                metadata={
                    "workspace_id": str(tenant_scope.workspace_id),
                    "operation_id": str(operation.id),
                    "invoice_number": invoice.safe_number,
                    **({"return_url": return_url} if provider_ref is None else {}),
                },
                payment_method_id=provider_ref,
                save_payment_method=False,
                receipt=receipt,
            )
        await lock_storage_workspace(db, tenant_scope.workspace_id)
        await db.refresh(operation, with_for_update=True)
        await db.refresh(invoice, with_for_update=True)
        url = _bind_initial_checkout_payment(operation, invoice, payment)
        await db.commit()
        return RedirectResponse(
            url or _checkout_status_location(invoice.safe_number), status_code=303
        )
    except (
        ValueError,
        BillingCheckoutDisabled,
        YooKassaConfigurationError,
        YooKassaProviderError,
        httpx.HTTPError,
        OSError,
        IntegrityError,
    ) as exc:
        await db.rollback()
        if persisted:
            await lock_storage_workspace(db, tenant_scope.workspace_id)
            # Never repeat POST after an ambiguous response. GET/webhook resolves it.
            bound = await db.scalar(
                select(BillingPurchaseQuote).where(
                    BillingPurchaseQuote.id == UUID(quote_id),
                    BillingPurchaseQuote.workspace_id == tenant_scope.workspace_id,
                )
            )
            if bound and bound.consumed_operation_id:
                saved = await db.scalar(
                    select(BillingOperation)
                    .where(BillingOperation.id == bound.consumed_operation_id)
                    .with_for_update()
                )
                saved_invoice = await db.scalar(
                    select(BillingInvoice)
                    .where(BillingInvoice.operation_id == bound.consumed_operation_id)
                    .with_for_update()
                )
                if saved and saved_invoice:
                    await _persist_initial_checkout_failure(
                        db, saved, saved_invoice, exc, dispatch_started=dispatched
                    )
                    await db.commit()
                    return RedirectResponse(
                        _checkout_status_location(saved_invoice.safe_number), status_code=303
                    )
            return await _purchase_error_page(
                request, tenant_scope, principal, db,
                "Результат оплаты уточняется. Не начинайте новый платеж.",
                action_url="/billing/history#billing-help", action_label="Уточнить результат",
            )
        message = (
            str(exc)
            if isinstance(exc, (PurchaseError, PromoError))
            else "Покупка не создана. Проверьте условия и повторите расчёт"
        )
        return await _purchase_error_page(
            request, tenant_scope, principal, db, message,
            action_url=recovery_url,
            action_label="К тарифу и оплате" if recovery_url == "/billing" else "Проверить сумму заново",
        )


@router.post("/billing/storage/cancel-selection", include_in_schema=False)
async def cancel_storage_selection(
    request: Request,
    _csrf: None = WebCSRFDependency,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
    selection_version: int = Form(ge=0),
):
    if db is None:
        return await _purchase_error_page(
            request, tenant_scope, principal, db, "Управление временно недоступно"
        )
    await lock_storage_workspace(db, tenant_scope.workspace_id)
    subscription = await _billing_owner_subscription(
        db, tenant_scope=tenant_scope, principal=principal
    )
    if subscription is None:
        return RedirectResponse("/billing?result=owner_only", status_code=303)
    blocker = await db.scalar(
        select(BillingOperation.id)
        .where(
            BillingOperation.workspace_id == tenant_scope.workspace_id,
            BillingOperation.state.in_(CHECKOUT_BLOCKING_STATES),
        )
        .limit(1)
    )
    if blocker is not None:
        await db.rollback()
        return await _purchase_error_page(
            request,
            tenant_scope,
            principal,
            db,
            "Сначала дождитесь результата предыдущего платежа в истории",
        )
    if subscription.next_capacity_version != selection_version:
        await db.rollback()
        return await _purchase_error_page(
            request, tenant_scope, principal, db, "Объём уже изменился. Проверьте текущий выбор"
        )
    subscription.next_capacity_bytes = None
    subscription.next_capacity_version += 1
    subscription.application_version += 1
    await _notify_storage_selection(db, subscription=subscription)
    await db.commit()
    return RedirectResponse("/billing/storage?result=schedule_canceled", status_code=303)


async def _next_renewal_label(db, subscription, *, now, for_resume=False, after_price_confirmation=False):
    if subscription is None or subscription.paid_through is None:
        return "не запланировано"
    if not subscription.recurring_allowed and not for_resume:
        return "не запланировано"
    if subscription.renewal_resolution == "price_changed" and not (for_resume or after_price_confirmation):
        return "приостановлено: подтвердите новую цену подписки и хранения"
    if subscription.renewal_resolution == "method_required" and not for_resume:
        return "приостановлено: проверьте способ оплаты"
    if subscription.renewal_resolution == "receipt_contact_required":
        return "приостановлено: нужен адрес для чека из подтвержденной оплаты"
    if subscription.renewal_resolution in {
        "acceptance_budget", "provider_unavailable", "catalog_not_approved", "provider_floor"
    } and not for_resume:
        return "приостановлено: оплата временно недоступна"
    operations = list(
        await db.scalars(
            select(BillingOperation).where(
                BillingOperation.workspace_id == subscription.workspace_id,
                BillingOperation.kind == "renewal",
                BillingOperation.request_snapshot["paid_through_at"].as_string()
                == utc(subscription.paid_through).isoformat(),
            )
        )
    )
    unresolved = any(
        item.state not in {"canceled", "succeeded", "scheduled"} for item in operations
    )
    if unresolved:
        return "проверяем результат предыдущего списания; нового платежа не будет до завершения проверки"
    next_at = next_renewal_attempt(
        paid_through=subscription.paid_through,
        now=now,
        resolved_attempts={
            renewal_attempt_of(item)
            for item in operations
            if item.state in {"canceled", "succeeded"} and not renewal_canceled_without_payment(item)
        },
        unresolved=False,
    )
    if next_at is None:
        return "попытки в этом периоде завершены; доступна ручная оплата"
    if next_at <= now:
        if after_price_confirmation:
            return "после сохранения выбора, в ближайшее время"
        return (
            "после подтверждения возобновления, в ближайшее время"
            if for_resume
            else "в ближайшее время"
        )
    return _billing_datetime_label(next_at)


async def _resume_renewal_snapshot(db, *, subscription, now):
    if subscription.paid_through is None:
        raise PurchaseError("Нет оплаченного периода для возобновления")
    operations = list(await db.scalars(select(BillingOperation).where(
        BillingOperation.workspace_id == subscription.workspace_id,
        BillingOperation.kind == "renewal",
        BillingOperation.request_snapshot["paid_through_at"].as_string() == utc(subscription.paid_through).isoformat(),
    )))
    if next_renewal_attempt(
        paid_through=subscription.paid_through, now=now,
        resolved_attempts={renewal_attempt_of(item) for item in operations if item.state in {"canceled", "succeeded"} and not renewal_canceled_without_payment(item)},
        unresolved=any(item.state not in {"canceled", "succeeded", "scheduled"} for item in operations),
    ) is None:
        raise PurchaseError("Попытки автопродления недоступны. Проверьте историю и оплатите следующий период вручную")
    base = (await _approved_personal_catalog(db, now=now)).get(subscription.cycle)
    if base is None:
        raise PurchaseError("Цена продления временно недоступна")
    catalog, storage_price = await compose_personal_catalog(
        db, base=base, subscription=subscription, now=now
    )
    method = await db.scalar(
        select(BillingPaymentMethod.id).where(
            BillingPaymentMethod.workspace_id == subscription.workspace_id,
            BillingPaymentMethod.owner_user_id == subscription.billing_owner_id,
            BillingPaymentMethod.is_default.is_(True),
            BillingPaymentMethod.state == "active",
            BillingPaymentMethod.verified_at.is_not(None),
        )
    )
    if method is None:
        raise PurchaseError("Нужна подтверждённая сохранённая карта")
    return {
        "catalog_snapshot": catalog.as_dict(),
        "storage_price_snapshot": storage_price_snapshot(storage_price),
        "payment_method_id": str(method),
        "next_attempt_label": await _next_renewal_label(db, subscription, now=now, for_resume=True),
    }


async def _notify_storage_selection(db, *, subscription):
    if subscription.billing_owner_id is not None:
        await enqueue_billing_notification(
            db,
            workspace_id=subscription.workspace_id,
            recipient_id=subscription.billing_owner_id,
            event_id=f"storage:{subscription.workspace_id}:selection:{subscription.next_capacity_version}",
            kind=BillingNotification.STORAGE_SELECTION_CHANGED,
            payload={"action_path": "/billing/storage"},
            marketing_allowed=False,
        )
