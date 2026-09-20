import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import Problem
from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.callbacks import (
    CallbackFlowError,
    CallbackProfile,
    resolve_callback_to_provider_link,
    resolve_callback_to_user,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.auth.dependencies import (
    AUTH_SESSION_COOKIE_NAME,
    PrincipalDependency,
    require_web_csrf,
)
from twobrain_rec_server.auth.policy import (
    AuthPolicySnapshot,
    read_auth_providers,
    update_workspace_auth_policy,
)
from twobrain_rec_server.auth.provider_links import (
    ConfirmedProviderLink,
    ProviderLinkError,
    apply_provider_link_auth_context,
    apply_provider_link_request_context,
    confirm_provider_link,
    create_link_intent,
    link_for_callback,
)
from twobrain_rec_server.auth.providers import build_provider_registry, get_provider_adapter
from twobrain_rec_server.auth.providers.base import ProviderCredentials
from twobrain_rec_server.auth.rate_limit import enforce_auth_rate_limits
from twobrain_rec_server.auth.redirects import safe_first_party_path as _safe_browser_return_path
from twobrain_rec_server.auth.sessions import (
    create_callback_state,
    resolve_session_device,
    revoke_registered_devices,
)
from twobrain_rec_server.billing.catalog import FREE_STORAGE_BYTES
from twobrain_rec_server.billing.entitlements import effective_plan_code
from twobrain_rec_server.billing.storage import project_active_playback_storage
from twobrain_rec_server.cabinet.auth_return import resolve_browser_auth_return_path
from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.models import (
    AuthCallbackState,
    AuthSession,
    AuthSessionDeviceBinding,
    ExternalIdentity,
    RegisteredDevice,
    StorageReservation,
    TimeCreditLedgerEntry,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceProviderLinkState,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.tenant_context import (
    AuthCallbackLookupContext,
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context,
)
from twobrain_rec_server.product_analytics.acquisition import (
    KNOWN_VISIT_ATTRIBUTION_STATUSES,
    MAX_VISIT_ATTRIBUTION_REFS,
    VisitAttribution,
    build_client_acquisition_attribute_from_visit_attribution,
    build_client_acquisition_attribute_from_visits,
    is_within_attribution_window,
    load_visit_attributions_by_refs,
    record_client_acquisition_attribute_safely,
    resolve_last_non_direct_source,
)
from twobrain_rec_server.product_analytics.attribution import (
    ATTRIBUTION_RELIABILITY_UNKNOWN,
    CAMPAIGN_CONTEXT_FIELDS,
    AttributionHandoff,
    default_attribution_bridge_registry,
    normalize_attribution_reliability,
    resolve_attribution_handoff,
)
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.ingest import (
    ProductAnalyticsIngestResult,
    ProductAnalyticsIngestService,
)
from twobrain_rec_server.product_analytics.milestones import (
    milestone_attribution_properties,
)
from twobrain_rec_server.public.analytics import read_public_visit_attribution

BROWSER_AUTH_STATE_COOKIE_NAME = "__Host-twobrain_rec_browser_auth_state"
ACCOUNT_CONNECTED_AUTH_METHOD_CATEGORY = "oauth_provider"
# The embedded cabinet connects an account by an emailed code. It is a different
# way in, so it must not be recorded as an external provider: the whole point of
# ``auth_method_category`` is to tell the ways in apart (FR-021).
EMAIL_CODE_AUTH_METHOD_CATEGORY = "email_code"

logger = logging.getLogger(__name__)


class _ProviderEntry(BaseModel):
    provider: str
    enabled: bool
    label: str
    requires_email: bool


class _ResidencyState(BaseModel):
    require_ru_local: bool
    residency_region_tag: str


class _EnrollmentState(BaseModel):
    allow_provider_self_enrollment: bool


class _ConsentCopy(BaseModel):
    language: str
    version: str
    content_markdown: str


class _AuthProvidersPayload(BaseModel):
    providers: list[_ProviderEntry]
    residency: _ResidencyState
    enrollment: _EnrollmentState
    consent_version: str
    consent: _ConsentCopy


class PublicAuthProvidersResponse(_AuthProvidersPayload):
    pass


class AuthProvidersResponse(_AuthProvidersPayload):
    workspace_id: UUID


class AuthStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_return_url: str | None = None
    continue_session_id: UUID | None = None


class AuthStartResponse(BaseModel):
    authorization_url: str
    state_nonce: str
    expires_at: datetime
    provider: str


class ProviderLinkStartResponse(BaseModel):
    authorization_url: str
    expires_at: datetime
    provider: str
    link_state_id: UUID


class ProviderLinkConfirmResponse(BaseModel):
    provider: str
    status: str
    idempotent: bool
    merge_intent_id: UUID | None = None


class AuthCallbackResponse(BaseModel):
    user_id: UUID
    workspace_id: UUID
    active_session_id: UUID
    session_token: str
    session_expires_at: datetime
    provider: str
    provider_subject: str
    external_identity_id: UUID


class AuthDeviceRegisterRequest(BaseModel):
    device_public_id: str = Field(min_length=1, max_length=160)
    platform: str = Field(min_length=1, max_length=32, default="macos")
    client_version: str | None = Field(default=None, max_length=80)


class AuthDeviceStateResponse(BaseModel):
    device_id: UUID
    status: str
    registration_state: str
    created_at: datetime


class AuthDeviceRevokeResponse(BaseModel):
    device_id: UUID
    status: str
    revoked_at: datetime


class AuthLinkRequest(BaseModel):
    candidate_provider: str = Field(min_length=1)
    candidate_provider_subject: str = Field(min_length=1, max_length=240)
    candidate_display_name: str | None = None
    candidate_email: str | None = None
    candidate_phone: str | None = None
    expected_workspace_id: UUID


class LinkedProvider(BaseModel):
    provider: str
    provider_subject: str
    is_primary: bool
    confirmed_at: datetime | None = None


class BillingSummaryResponse(BaseModel):
    plan_code: str
    state: str
    trial_ends_at: datetime | None = None
    paid_through: datetime | None = None
    bonus_until: datetime | None = None
    renewal_resolution: str | None = None
    processing_unlimited: bool
    storage_used_bytes: int | None = None
    storage_capacity_bytes: int | None = None
    handoff_path: str = "/billing"


class MeResponse(BaseModel):
    user_id: UUID
    workspace_id: UUID
    active_session_id: UUID | None = None
    linked_providers: list[LinkedProvider]
    policy: AuthProvidersResponse
    registered_devices: list[AuthDeviceStateResponse]
    billing: BillingSummaryResponse


class AuthPolicyUpdateRequest(BaseModel):
    allow_yandex: bool | None = None
    allow_vk: bool | None = None
    allow_telegram: bool | None = None
    allow_tid: bool | None = None
    allow_sber_id: bool | None = None
    allow_mts_id: bool | None = None
    allow_esia: bool | None = None
    allow_provider_self_enrollment: bool | None = None
    require_ru_local: bool | None = None
    residency_region_tag: str | None = None
    consent_text_version: str | None = None


PROBLEM_RESPONSES = {
    400: {"model": Problem, "description": "Bad request"},
    401: {"model": Problem, "description": "Unauthorized"},
    403: {"model": Problem, "description": "Forbidden"},
    404: {"model": Problem, "description": "Not found"},
    409: {"model": Problem, "description": "Conflict"},
    422: {"model": Problem, "description": "Validation error"},
    503: {"model": Problem, "description": "Dependency unavailable"},
}


router = APIRouter(
    prefix="/api/v1/auth", tags=["auth"], responses=PROBLEM_RESPONSES, include_in_schema=True
)
WebCSRFDependency = Depends(require_web_csrf)


def build_account_connected_product_analytics_payload(
    *,
    stable_pseudonymous_user_id: str,
    auth_method_category: str,
    bridge_present: bool,
    attribution_reliability: str = ATTRIBUTION_RELIABILITY_UNKNOWN,
    elapsed_bucket: str | None = None,
    campaign_context: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    """The account-connected milestone, sent from the real authorization path.

    The event carries the campaign of the visit as well as the level of the link
    (FR-018, FR-023). The default reliability is ``unknown``: a caller that knows
    nothing about the campaign must not claim a link, and an event without labels
    says so explicitly instead of reading as a direct entry (FR-024).
    """
    level = normalize_attribution_reliability(attribution_reliability) or ATTRIBUTION_RELIABILITY_UNKNOWN
    event = build_activation_event(
        "desktop_account_connected",
        stable_pseudonymous_user_id=stable_pseudonymous_user_id,
        properties={
            "auth_method_category": auth_method_category,
            "account_connection_state": "connected",
            # One builder produces the whole attribution part of the event, so
            # the labels, the explicit state and the level can never disagree.
            **milestone_attribution_properties(
                attribution_reliability=level,
                bridge_present=bridge_present,
                campaign_context=campaign_context,
            ),
            **({"elapsed_bucket": elapsed_bucket} if elapsed_bucket else {}),
        },
    )
    return event.as_payload()


_HANDOFF_REQUEST_FIELDS = (
    "bridge",
    "graf_attribution_ref",
    "fallback",
    "graf_attribution_fallback",
    "landing_path",
    "attribution_ref",
    *CAMPAIGN_CONTEXT_FIELDS,
)


@dataclass(frozen=True, slots=True)
class _ResolvedAttributionSnapshot:
    """One auth-time selection shared by acquisition and the milestone."""

    attribution: dict[str, Any]
    visits: tuple[VisitAttribution, ...]
    selected_visit: VisitAttribution | None
    handoff: AttributionHandoff | None


def _request_attribution_snapshot(
    request: Request,
    *,
    now: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the one current request snapshot shared by every auth path.

    The browser cookie is session-scoped.  Its timestamp is checked here before
    labels are handed to the conversion event, so a stale cookie cannot become a
    90-day cross-session history by accident.  Bridge resolution remains the
    short-lived (72-hour) app fallback and is still allowed when the browser has
    no cookie.
    """
    moment = now or datetime.now(UTC)
    attribution = read_public_visit_attribution(request, now=moment)
    raw: dict[str, Any] = dict(getattr(request, "query_params", None) or {})
    values = {field: raw.get(field) for field in _HANDOFF_REQUEST_FIELDS}
    status = str(attribution.get("attribution_status") or "missing").strip().lower()
    first_seen_raw = attribution.get("first_seen_at")
    first_seen: datetime | None = None
    if isinstance(first_seen_raw, str):
        try:
            first_seen = datetime.fromisoformat(first_seen_raw.replace("Z", "+00:00"))
        except ValueError:
            first_seen = None
    if first_seen is not None:
        if first_seen.tzinfo is None:
            first_seen = first_seen.replace(tzinfo=UTC)
        else:
            first_seen = first_seen.astimezone(UTC)
    if (
        status in KNOWN_VISIT_ATTRIBUTION_STATUSES
        and first_seen is not None
        and is_within_attribution_window(first_seen, now=moment)
    ):
        for field in CAMPAIGN_CONTEXT_FIELDS:
            if attribution.get(field) is not None:
                values[field] = attribution[field]
        if attribution.get("landing_path") is not None:
            values["landing_path"] = attribution["landing_path"]
    else:
        # A browser cookie is untrusted input. It can help the public aggregate
        # describe this request, but it is never an authentication capability;
        # only an exact durable row or a live process bridge may attach labels to
        # a registered account.
        for field in CAMPAIGN_CONTEXT_FIELDS:
            values[field] = None
        values["landing_path"] = None
    return values, attribution


async def _durable_attribution_snapshot(
    request: Request,
    *,
    db: AsyncSession | None,
    now: datetime,
) -> _ResolvedAttributionSnapshot:
    """Resolve exact session refs and select one last non-direct visit.

    Cookie JSON and raw query campaign labels are client-controlled. Authentication
    loads only the exact opaque refs supplied by the session ring (plus the
    compatibility current ref) and applies the one shared attribution rule to the
    returned rows. A missing or forged ref is an ordinary attribution gap.
    """
    _, cookie_attribution = _request_attribution_snapshot(request, now=now)
    query_params = getattr(request, "query_params", None) or {}
    query_ref = query_params.get("attribution_ref")
    # Keep the bound at the authentication boundary as well as in the SQL
    # loader.  This prevents a forged/oversized cookie or mock loader from
    # turning an auth request into an unbounded lookup; current/query refs have
    # deterministic precedence and duplicates are removed without trusting labels.
    refs: list[Any] = []
    seen_refs: set[str] = set()
    for candidate in (
        query_ref,
        cookie_attribution.get("attribution_ref"),
        *(cookie_attribution.get("attribution_refs") or ()),
    ):
        if not isinstance(candidate, str) or not candidate or candidate in seen_refs:
            continue
        seen_refs.add(candidate)
        refs.append(candidate)
        if len(refs) >= MAX_VISIT_ATTRIBUTION_REFS:
            break
    visits = await load_visit_attributions_by_refs(db, refs, now=now)
    selected = resolve_last_non_direct_source(visits, now=now)
    if selected is None:
        handoff = await _bridge_handoff_for_request(request, now=now)
        return _ResolvedAttributionSnapshot({}, visits, None, handoff)
    values = {
        "attribution_ref": selected.attribution_ref,
        "utm_source": selected.source,
        "utm_medium": selected.medium,
        "utm_campaign": selected.campaign,
        "utm_content": selected.content,
        "utm_term": selected.term,
        "yclid": selected.yclid,
        "landing_path": selected.landing_path,
        "first_seen_at": selected.first_seen_at.isoformat(),
        "attribution_status": "saved",
    }
    handoff = AttributionHandoff(
        graf_attribution_id=None,
        campaign_context={
            "utm_source": selected.source,
            "utm_medium": selected.medium,
            "utm_campaign": selected.campaign,
            "utm_id": None,
            "utm_content": selected.content,
            "utm_term": selected.term,
        },
        fallback_recovered=False,
        landing_path=selected.landing_path,
    )
    return _ResolvedAttributionSnapshot(values, visits, selected, handoff)


async def _bridge_handoff_for_request(
    request: Request,
    *,
    now: datetime,
) -> AttributionHandoff | None:
    """Resolve only the short-lived server-owned app bridge on a miss."""
    return attribution_handoff_for_request(request, now=now)


async def resolve_attribution_snapshot_for_request_async(
    request: Request,
    *,
    db: AsyncSession | None,
    now: datetime | None = None,
) -> _ResolvedAttributionSnapshot:
    """Resolve one selected visit for the whole auth completion path."""
    return await _durable_attribution_snapshot(request, db=db, now=now or datetime.now(UTC))


async def attribution_handoff_for_request_async(
    request: Request,
    *,
    db: AsyncSession | None,
    now: datetime | None = None,
    snapshot: _ResolvedAttributionSnapshot | None = None,
) -> AttributionHandoff | None:
    """Return the handoff from the one durable selection used by auth."""
    resolved = snapshot or await _durable_attribution_snapshot(
        request, db=db, now=now or datetime.now(UTC)
    )
    return resolved.handoff


def attribution_handoff_for_request(
    request: Request,
    *,
    now: datetime | None = None,
) -> AttributionHandoff | None:
    """Resolve only the server-owned bridge for a synchronous auth milestone.

    Cookie JSON and raw query campaign labels are client-controlled. The
    synchronous milestone path has no database session, so it may use only the
    short-lived process bridge; browser-cookie attribution is resolved by the
    asynchronous durable path before the route schedules this milestone.
    """
    raw = dict(getattr(request, "query_params", None) or {})
    # Campaign labels and paths in an app URL are caller-controlled.  Keep the
    # URL shape backward-compatible, but resolve only the exact server-owned
    # bridge identifier; raw labels must never create attribution on their own.
    values = {
        field: raw.get(field)
        for field in (
            "bridge",
            "graf_attribution_ref",
            "fallback",
            "graf_attribution_fallback",
        )
    }
    handoff = resolve_attribution_handoff(
        values,
        registry=default_attribution_bridge_registry(),
        now=now,
    )
    if handoff is None:
        return None
    if handoff.graf_attribution_id is None and not handoff.campaign_known():
        return None
    return handoff


async def capture_client_acquisition_attribute(
    request: Request,
    *,
    db: AsyncSession | None,
    account_id: UUID,
    now: datetime | None = None,
    snapshot: _ResolvedAttributionSnapshot | None = None,
) -> bool:
    """Write the first acquisition attribute from the current auth request.

    This is shared by email login/registration and OAuth callbacks.  It uses the
    same session cookie/bridge snapshot as the milestone, keeps the 90-day check
    in the acquisition builder, and never lets measurement failure break auth.
    """
    moment = now or datetime.now(UTC)
    try:
        resolved = snapshot or await _durable_attribution_snapshot(request, db=db, now=moment)
        attribution = resolved.attribution
        handoff = resolved.handoff
        if resolved.selected_visit is not None:
            attribute = build_client_acquisition_attribute_from_visits(
                account_id=account_id,
                visits=[resolved.selected_visit],
                captured_at=moment,
                now=moment,
                linked_automatically=True,
            )
        else:
            # A bridge is already server-resolved and may be the only source in
            # an embedded app sign-in. Merge its owned campaign context into the
            # builder input; never use the unsigned cookie fallback.
            bridge_attribution = {
                **(attribution or {}),
                **(handoff.campaign_context if handoff is not None else {}),
                "landing_path": handoff.landing_path if handoff is not None else None,
                "attribution_status": "saved" if handoff and handoff.campaign_known() else "missing",
            }
            attribute = build_client_acquisition_attribute_from_visit_attribution(
                account_id=account_id,
                attribution=bridge_attribution,
                graf_attribution_id=handoff.graf_attribution_id if handoff else None,
                captured_at=moment,
                now=moment,
            )
        settings = getattr(getattr(request, "app", None), "state", None)
        settings = getattr(settings, "settings", None)
        return await record_client_acquisition_attribute_safely(
            db,
            attribute,
            settings=settings,
        )
    except Exception as exc:  # noqa: BLE001 - auth must succeed
        logger.warning(
            "client acquisition attribute was not captured: error=%s",
            exc.__class__.__name__,
        )
        return False


def record_account_connected_milestone(
    *,
    settings: Settings,
    user_id: UUID,
    provider: str,
    handoff: AttributionHandoff | None,
    auth_method_category: str = ACCOUNT_CONNECTED_AUTH_METHOD_CATEGORY,
) -> ProductAnalyticsIngestResult | None:
    """Send the milestone built above (FR-021).

    Measurement never breaks account connection: a failure of the analytics
    service is swallowed here, after the account itself is already stored.
    """
    if not settings.product_analytics_enabled:
        return None
    identity = build_safe_identity(user_source_id=str(user_id))
    payload = build_account_connected_product_analytics_payload(
        stable_pseudonymous_user_id=identity.stable_pseudonymous_user_id,
        auth_method_category=auth_method_category,
        bridge_present=handoff is not None,
        attribution_reliability=(handoff.reliability(account_connected=True) if handoff else ATTRIBUTION_RELIABILITY_UNKNOWN),
        campaign_context=handoff.campaign_context if handoff else None,
    )
    try:
        return ProductAnalyticsIngestService(settings).ingest(payload)
    except Exception:
        logger.warning(
            "product analytics account-connected milestone was not delivered",
            extra={"provider": provider},
            exc_info=True,
        )
        return None


def schedule_account_connected_milestone(
    background_tasks: BackgroundTasks,
    request: Request,
    *,
    user_id: UUID,
    provider: str,
    handoff: AttributionHandoff | None = None,
    auth_method_category: str = ACCOUNT_CONNECTED_AUTH_METHOD_CATEGORY,
) -> None:
    """Deliver the milestone after the response, never inside the login request.

    Routes with a database session pass the already-resolved durable/bridge
    handoff. The synchronous bridge-only fallback is retained for callers that
    cannot safely perform a database lookup, but unsigned cookie labels are never
    read here.
    """
    settings = getattr(request.app.state, "settings", None) or get_settings()
    if not settings.product_analytics_enabled:
        return
    if handoff is None:
        handoff = attribution_handoff_for_request(request)
    background_tasks.add_task(
        record_account_connected_milestone,
        settings=settings,
        user_id=user_id,
        provider=provider,
        handoff=handoff,
        auth_method_category=auth_method_category,
    )


def _parse_uuid(value: str | None, header_name: str) -> UUID:
    if not value:
        raise ProblemDetail(
            status=400,
            code="missing_workspace_id",
            title="Missing workspace id",
            detail=f"{header_name} is required",
        )
    try:
        return UUID(value)
    except ValueError as exc:
        raise ProblemDetail(
            status=400,
            code="invalid_workspace_id",
            title="Invalid workspace id",
            detail=f"{header_name} must be a UUID",
        ) from exc


def _parse_workspace_id(value: str | None) -> UUID:
    return _parse_uuid(value, "X-Workspace-Id")


def _internal_auth_workspace_id(request: Request) -> UUID:
    workspace_id = request.app.state.settings.web_login_workspace_id
    if workspace_id is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication workspace dependency unavailable",
        )
    return workspace_id


def _reject_public_workspace_target(request: Request) -> None:
    if "workspace_id" in request.query_params:
        raise ProblemDetail(
            status=400,
            code="workspace_target_not_allowed",
            title="Public authentication does not accept a workspace target",
        )


async def _get_request_db_session(request: Request):
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        yield None
        return
    async with sessionmaker() as session:
        yield session


AuthDbDependency = Depends(_get_request_db_session)


async def _apply_auth_public_context(db: AsyncSession, workspace_id: UUID) -> None:
    await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))


async def _apply_auth_request_context(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    principal: AuthenticatedPrincipal,
) -> None:
    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=principal.organization_id,
            workspace_id=workspace_id,
            user_id=principal.user_id,
            auth_session_id=principal.session_id,
            context_kind="request",
        ),
    )


async def _require_active_customer_membership(
    db: AsyncSession,
    *,
    request: Request,
    workspace_id: UUID,
    principal: AuthenticatedPrincipal,
) -> tuple[Workspace, WorkspaceMembership]:
    internal_workspace_id = request.app.state.settings.web_login_workspace_id
    if internal_workspace_id is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication workspace dependency unavailable",
        )
    if workspace_id == internal_workspace_id or workspace_id not in principal.workspace_ids:
        raise ProblemDetail(
            status=403,
            code="workspace_scope_denied",
            title="Workspace scope denied",
        )
    await _apply_auth_request_context(db, workspace_id=workspace_id, principal=principal)
    workspace = await db.get(Workspace, workspace_id)
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == principal.user_id,
            WorkspaceMembership.status == "active",
        )
    )
    personal_owner_is_valid = workspace is not None and (
        workspace.kind != "personal"
        or (
            workspace.owner_user_id == principal.user_id
            and membership is not None
            and membership.role == "owner"
        )
    )
    if (
        workspace is None
        or workspace.organization_id != principal.organization_id
        or membership is None
        or not personal_owner_is_valid
    ):
        raise ProblemDetail(
            status=403,
            code="workspace_scope_denied",
            title="Workspace scope denied",
        )
    return workspace, membership


def _provider_client_id(settings: Settings, provider: str) -> str:
    normalized = provider.lower()
    if normalized == "yandex":
        return settings.yandex_client_id
    if normalized == "vk":
        return settings.vk_client_id
    return settings.telegram_client_id


def _provider_secret_file(settings: Settings, provider: str) -> Path | None:
    normalized = provider.lower()
    if normalized == "yandex":
        return settings.yandex_client_secret_file
    if normalized == "vk":
        return settings.vk_client_secret_file
    return settings.telegram_client_secret_file


def _read_provider_secret(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def _provider_credentials(
    settings: Settings, provider: str, redirect_uri: str
) -> ProviderCredentials:
    return ProviderCredentials(
        client_id=_provider_client_id(settings, provider),
        client_secret=_read_provider_secret(_provider_secret_file(settings, provider)),
        redirect_uri=redirect_uri,
    )


def build_provider_callback_url(request: Request, provider: str) -> str:
    callback_url = str(request.url_for("auth_callback", provider=provider))
    public_base_url = getattr(request.app.state.settings, "auth_base_url", None)
    if public_base_url is None:
        return callback_url
    callback_path = urlsplit(callback_url).path
    return f"{str(public_base_url).rstrip('/')}{callback_path}"


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _request_client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _provider_link_callback_result(code: str) -> str:
    if code in {"callback_state_expired", "provider_link_expired"}:
        return "provider_link_expired"
    if code in {"callback_state_reused", "provider_link_reused"}:
        return "provider_link_reused"
    if code in {
        "callback_parse_error",
        "callback_state_invalid",
        "provider_link_callback_mismatch",
        "provider_link_candidate_missing",
    }:
        return "provider_link_invalid"
    if code == "callback_denied":
        return "provider_link_denied"
    return "provider_link_unavailable"


def _provider_link_callback_redirect(
    callback_state: AuthCallbackState,
    link: WorkspaceProviderLinkState,
    *,
    result: str,
) -> RedirectResponse:
    redirect_path = _safe_browser_return_path(callback_state.requested_redirect)
    if redirect_path is None:
        redirect_path = f"/settings/provider-links/{link.id}"
    response = RedirectResponse(f"{redirect_path}?result={result}", status_code=303)
    _clear_browser_auth_state_cookie(response)
    return response


def _set_browser_auth_state_cookie(response: Response, *, nonce: str, max_age: int) -> None:
    response.set_cookie(
        key=BROWSER_AUTH_STATE_COOKIE_NAME,
        value=nonce,
        max_age=max_age,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _clear_browser_auth_state_cookie(response: Response) -> None:
    response.delete_cookie(
        key=BROWSER_AUTH_STATE_COOKIE_NAME,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _browser_callback_error_redirect(
    request: Request,
    *,
    callback_state: AuthCallbackState | None,
    error_code: str,
) -> RedirectResponse | None:
    callback_is_browser_bound = (
        callback_state is not None
        and callback_state.expected_state != callback_state.state_nonce
    )
    requested_redirect = _safe_browser_return_path(
        callback_state.requested_redirect if callback_is_browser_bound else None
    )
    accepts_html = "text/html" in request.headers.get("accept", "").lower()
    if requested_redirect is None and not accepts_html:
        return None
    redirect = RedirectResponse(
        "/login?" + urlencode({"next": requested_redirect or "/meetings", "error": error_code}),
        status_code=303,
    )
    _clear_browser_auth_state_cookie(redirect)
    return redirect


def _set_auth_cookie(response: Response, *, token: str, expires_at: datetime) -> None:
    token_expires_at = expires_at
    if token_expires_at.tzinfo is None:
        token_expires_at = token_expires_at.replace(tzinfo=UTC)
    max_age = max(0, int((token_expires_at - datetime.now(UTC)).total_seconds()))
    response.set_cookie(
        key=AUTH_SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


async def _enforce_public_provider_rate_limits(
    request: Request,
    db: AsyncSession,
    *,
    workspace_id: UUID,
    scopes: tuple[tuple[str, str], ...],
    callback_state: AuthCallbackState | None = None,
) -> RedirectResponse | None:
    retry_after = await enforce_auth_rate_limits(
        db,
        workspace_id=workspace_id,
        scopes=scopes,
        sessionmaker=getattr(request.app.state, "db_sessionmaker", None),
        scope_secret=request.app.state.settings.share_identity_hash_secret,
    )
    if retry_after is not None:
        redirect = _browser_callback_error_redirect(
            request,
            callback_state=callback_state,
            error_code="auth_rate_limited",
        )
        if redirect is not None:
            redirect.headers["Retry-After"] = str(max(1, retry_after))
            redirect.headers["Cache-Control"] = "private, no-store"
            return redirect
        raise ProblemDetail(
            status=429,
            code="auth_rate_limited",
            title="Too many authentication attempts",
            headers={
                "Retry-After": str(max(1, retry_after)),
                "Cache-Control": "private, no-store",
            },
        )
    return None


async def _record_auth_audit(
    db: AsyncSession | None,
    *,
    request: Request,
    workspace_id: UUID | None,
    event_type: str,
    outcome: str = "success",
    actor_user_id: UUID | None = None,
    user_id: UUID | None = None,
    provider: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    if db is None or workspace_id is None:
        return
    await write_auth_audit_event(
        db,
        workspace_id=workspace_id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        actor_ip=_request_client_ip(request),
        user_id=user_id,
        provider=provider,
        outcome=outcome,
        metadata=metadata or {},
        request_id=_request_id(request),
    )


def _policy_to_response(
    snapshot: AuthPolicySnapshot, *, include_disabled: bool = False
) -> AuthProvidersResponse:
    return AuthProvidersResponse(
        workspace_id=snapshot.workspace_id,
        providers=[
            _ProviderEntry(
                provider=entry.provider,
                enabled=entry.enabled,
                label=entry.label,
                requires_email=entry.requires_email,
            )
            for entry in snapshot.providers
            if include_disabled or entry.enabled
        ],
        residency=_ResidencyState(
            require_ru_local=snapshot.require_ru_local,
            residency_region_tag=snapshot.residency_region_tag,
        ),
        enrollment=_EnrollmentState(
            allow_provider_self_enrollment=snapshot.allow_provider_self_enrollment,
        ),
        consent_version=snapshot.consent_text_version,
        consent=_ConsentCopy(
            language=snapshot.consent_language,
            version=snapshot.consent_text_version,
            content_markdown=snapshot.consent_content_markdown,
        ),
    )


def _policy_to_public_response(
    snapshot: AuthPolicySnapshot,
    *,
    include_disabled: bool = False,
) -> PublicAuthProvidersResponse:
    payload = _policy_to_response(snapshot, include_disabled=include_disabled)
    return PublicAuthProvidersResponse.model_validate(payload.model_dump(exclude={"workspace_id"}))


@router.get("/providers", response_model=PublicAuthProvidersResponse)
async def list_providers(
    request: Request,
    db: AsyncSession | None = AuthDbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    _reject_public_workspace_target(request)
    workspace_id = _internal_auth_workspace_id(request)
    await _apply_auth_public_context(db, workspace_id)
    adapters = build_provider_registry()
    snapshot = await read_auth_providers(db, workspace_id, adapters=adapters)
    return _policy_to_public_response(snapshot)


@router.get("/policy", response_model=AuthProvidersResponse)
async def get_workspace_auth_policy(
    request: Request,
    workspace_id: UUID,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = AuthDbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    if workspace_id == _internal_auth_workspace_id(request):
        raise ProblemDetail(
            status=404,
            code="workspace_policy_unavailable",
            title="Workspace policy unavailable",
        )
    await _require_active_customer_membership(
        db,
        request=request,
        workspace_id=workspace_id,
        principal=principal,
    )
    adapters = build_provider_registry()
    snapshot = await read_auth_providers(db, workspace_id, adapters=adapters)
    return _policy_to_response(snapshot, include_disabled=True)


@router.patch("/policy", response_model=AuthProvidersResponse, dependencies=[WebCSRFDependency])
async def patch_workspace_auth_policy(
    request: Request,
    workspace_id: UUID,
    payload: AuthPolicyUpdateRequest,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = AuthDbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    _, membership = await _require_active_customer_membership(
        db,
        request=request,
        workspace_id=workspace_id,
        principal=principal,
    )
    if membership.role not in {"owner", "admin"}:
        raise ProblemDetail(
            status=403,
            code="not_authorized_to_manage_policy",
            title="Workspace policy update is restricted",
        )
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise ProblemDetail(
            status=400,
            code="policy_payload_empty",
            title="No policy fields provided",
        )
    snapshot = await update_workspace_auth_policy(
        db, workspace_id=workspace_id, policy_updates=updates
    )
    await _record_auth_audit(
        db,
        request=request,
        workspace_id=workspace_id,
        event_type="workspace_auth_policy_updated",
        actor_user_id=principal.user_id,
        user_id=principal.user_id,
        provider="policy",
        metadata={
            "changed_fields": sorted(updates.keys()),
            "require_ru_local": snapshot.require_ru_local,
            "residency_region_tag": snapshot.residency_region_tag,
            "consent_text_version": snapshot.consent_text_version,
        },
    )
    await db.commit()
    return _policy_to_response(snapshot, include_disabled=True)


@router.post("/providers/{provider}/start", response_model=AuthStartResponse)
async def start_provider_flow(
    provider: str,
    request: Request,
    payload: AuthStartRequest,
    db: AsyncSession | None = AuthDbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    _reject_public_workspace_target(request)
    workspace_id = _internal_auth_workspace_id(request)
    await _apply_auth_public_context(db, workspace_id)
    normalized_provider = provider.lower()
    rate_limit_response = await _enforce_public_provider_rate_limits(
        request,
        db,
        workspace_id=workspace_id,
        scopes=(
            ("provider_start_ip", _request_client_ip(request) or "unknown"),
        ),
    )
    if rate_limit_response is not None:
        return rate_limit_response
    adapters = build_provider_registry()
    try:
        adapter = get_provider_adapter(normalized_provider)
    except ValueError as exc:
        await _record_auth_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            event_type="provider_auth_started",
            outcome="failure",
            provider=normalized_provider,
            metadata={"error_code": "provider_missing"},
        )
        raise ProblemDetail(
            status=403,
            code="provider_missing",
            title="Provider is not configured",
        ) from exc
    snapshot = await read_auth_providers(db, workspace_id, adapters=adapters, persist_defaults=True)
    provider_policy = next(
        (entry for entry in snapshot.providers if entry.provider == normalized_provider), None
    )
    if provider_policy is None or not provider_policy.enabled:
        await _record_auth_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            event_type="provider_auth_started",
            outcome="failure",
            provider=normalized_provider,
            metadata={"error_code": "provider_disabled"},
        )
        raise ProblemDetail(
            status=403,
            code="provider_disabled",
            title="Provider disabled",
        )
    state = create_callback_state(
        db,
        provider=normalized_provider,
        workspace_id=workspace_id,
        requested_redirect=payload.workspace_return_url,
        ttl_seconds=request.app.state.settings.auth_callback_state_ttl_seconds,
    )
    callback_url = build_provider_callback_url(request, normalized_provider)
    settings = request.app.state.settings
    credentials = _provider_credentials(settings, normalized_provider, callback_url)
    authorization_url = adapter.build_authorization_url(
        client_id=credentials.client_id,
        client_secret=credentials.client_secret,
        redirect_uri=callback_url,
        state=state.state_nonce,
        return_url=payload.workspace_return_url,
        workspace_id="public",
    )
    await _record_auth_audit(
        db,
        request=request,
        workspace_id=workspace_id,
        event_type="provider_auth_started",
        provider=normalized_provider,
        metadata={"state_nonce": state.state_nonce},
    )
    await db.commit()
    return AuthStartResponse(
        authorization_url=authorization_url,
        state_nonce=state.state_nonce,
        expires_at=state.expires_at,
        provider=normalized_provider,
    )


@router.post(
    "/providers/{provider}/link/start",
    response_model=ProviderLinkStartResponse,
    dependencies=[WebCSRFDependency],
)
async def start_provider_link_flow(
    provider: str,
    request: Request,
    workspace_id: UUID,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = AuthDbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    await _require_active_customer_membership(
        db,
        request=request,
        workspace_id=workspace_id,
        principal=principal,
    )
    normalized_provider = provider.lower()
    adapters = build_provider_registry()
    try:
        adapter = get_provider_adapter(normalized_provider)
    except ValueError as exc:
        raise ProblemDetail(
            status=403, code="provider_missing", title="Provider is not configured"
        ) from exc
    snapshot = await read_auth_providers(db, workspace_id, adapters=adapters, persist_defaults=True)
    provider_policy = next(
        (entry for entry in snapshot.providers if entry.provider == normalized_provider), None
    )
    if provider_policy is None or not provider_policy.enabled:
        raise ProblemDetail(status=403, code="provider_disabled", title="Provider disabled")
    await apply_provider_link_auth_context(
        db,
        principal=principal,
        workspace_id=workspace_id,
    )
    created_state = create_callback_state(
        db,
        provider=normalized_provider,
        workspace_id=workspace_id,
        requested_redirect=None,
        ttl_seconds=request.app.state.settings.auth_callback_state_ttl_seconds,
    )
    await db.flush()
    callback_state = await db.get(AuthCallbackState, created_state.id)
    if callback_state is None:
        raise ProblemDetail(
            status=503, code="provider_link_unavailable", title="Provider link unavailable"
        )
    await apply_provider_link_request_context(
        db,
        principal=principal,
        workspace_id=workspace_id,
    )
    try:
        link = await create_link_intent(
            db,
            principal=principal,
            workspace_id=workspace_id,
            provider=normalized_provider,
            callback_state=callback_state,
        )
    except ProviderLinkError as exc:
        status_code = 401 if exc.code == "provider_link_session_required" else 403
        raise ProblemDetail(
            status=status_code, code=exc.code, title="Provider link denied"
        ) from exc
    callback_url = build_provider_callback_url(request, normalized_provider)
    settings = request.app.state.settings
    credentials = _provider_credentials(settings, normalized_provider, callback_url)
    authorization_url = adapter.build_authorization_url(
        client_id=credentials.client_id,
        client_secret=credentials.client_secret,
        redirect_uri=callback_url,
        state=created_state.state_nonce,
        return_url=None,
        workspace_id=str(workspace_id),
    )
    await db.commit()
    return ProviderLinkStartResponse(
        authorization_url=authorization_url,
        expires_at=created_state.expires_at,
        provider=normalized_provider,
        link_state_id=link.id,
    )


@router.post(
    "/provider-links/{link_state_id}/confirm",
    response_model=ProviderLinkConfirmResponse,
    response_model_exclude_none=True,
    dependencies=[WebCSRFDependency],
)
async def confirm_provider_link_flow(
    link_state_id: UUID,
    request: Request,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = AuthDbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    if not principal.auth_via_session or principal.session_workspace_id is None:
        raise ProblemDetail(
            status=401,
            code="provider_link_session_required",
            title="Provider link session required",
        )
    await _require_active_customer_membership(
        db,
        request=request,
        workspace_id=principal.session_workspace_id,
        principal=principal,
    )
    try:
        confirmed: ConfirmedProviderLink = await confirm_provider_link(
            db,
            principal=principal,
            link_state_id=link_state_id,
        )
    except ProviderLinkError as exc:
        status_code = 400
        if exc.code == "provider_link_not_found":
            status_code = 404
        elif exc.code == "provider_link_conflict":
            status_code = 409
        elif exc.code in {"provider_link_session_required", "workspace_scope_denied"}:
            status_code = 403
        problem = ProblemDetail(
            status=status_code,
            code=exc.code,
            title="Provider link denied",
        )
        await db.commit()
        raise problem from exc
    response = ProviderLinkConfirmResponse(
        provider=confirmed.provider,
        status=confirmed.status,
        idempotent=confirmed.idempotent,
        merge_intent_id=confirmed.merge_intent_id,
    )
    await db.commit()
    return response


@router.get("/callback/{provider}", name="auth_callback", response_model=AuthCallbackResponse)
async def callback(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    provider: str,
    state: str | None = Query(default=None, description="Callback state"),
    db: AsyncSession | None = AuthDbDependency,
):
    if db is None:
        redirect = _browser_callback_error_redirect(
            request,
            callback_state=None,
            error_code="auth_dependency_unavailable",
        )
        if redirect is not None:
            return redirect
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    if not state:
        redirect = _browser_callback_error_redirect(
            request,
            callback_state=None,
            error_code="callback_state_invalid",
        )
        if redirect is not None:
            return redirect
        raise ProblemDetail(
            status=400,
            code="callback_state_invalid",
            title="Callback state is missing",
            detail="callback state is required",
        )
    auth_bootstrap_workspace_id = _internal_auth_workspace_id(request)
    provider = provider.lower()
    rate_limit_response = await _enforce_public_provider_rate_limits(
        request,
        db,
        workspace_id=auth_bootstrap_workspace_id,
        scopes=(
            ("provider_callback_ip", _request_client_ip(request) or "unknown"),
        ),
    )
    if rate_limit_response is not None:
        return rate_limit_response
    await apply_tenant_context(db, AuthCallbackLookupContext(state_nonce=state))
    query = dict(request.query_params)
    settings = request.app.state.settings
    callback_url = build_provider_callback_url(request, provider)
    callback_state = await db.scalar(
        select(AuthCallbackState).where(
            AuthCallbackState.provider == provider,
            AuthCallbackState.state_nonce == state,
        )
    )
    link = await link_for_callback(db, callback_state.id) if callback_state is not None else None
    if callback_state is not None:
        rate_limit_response = await _enforce_public_provider_rate_limits(
            request,
            db,
            workspace_id=auth_bootstrap_workspace_id,
            scopes=(("provider_callback_state", state),),
            callback_state=callback_state,
        )
        if rate_limit_response is not None:
            return rate_limit_response
    try:
        if link is not None:
            await resolve_callback_to_provider_link(
                db,
                provider=provider,
                query=query,
                state_nonce=state,
                link_state=link,
                provider_credentials=_provider_credentials(settings, provider, callback_url),
                browser_state_nonce=request.cookies.get(BROWSER_AUTH_STATE_COOKIE_NAME),
            )
            await db.commit()
            return _provider_link_callback_redirect(
                callback_state,
                link,
                result="callback_verified",
            )
        profile: CallbackProfile = await resolve_callback_to_user(
            db,
            provider=provider,
            query=query,
            state_nonce=state,
            provider_credentials=_provider_credentials(settings, provider, callback_url),
            auth_bootstrap_workspace_id=auth_bootstrap_workspace_id,
            session_ttl_seconds=settings.auth_session_ttl_seconds,
            actor_ip=_request_client_ip(request),
            request_id=_request_id(request),
            browser_state_nonce=request.cookies.get(BROWSER_AUTH_STATE_COOKIE_NAME),
            referral_token=request.cookies.get("graf_referral_token"),
            referral_enabled=bool(settings.billing_checkout_enabled),
            user_agent=request.headers.get("user-agent"),
        )
    except CallbackFlowError as exc:
        await db.commit()
        if link is not None and callback_state is not None:
            return _provider_link_callback_redirect(
                callback_state,
                link,
                result=_provider_link_callback_result(exc.code),
            )
        redirect = _browser_callback_error_redirect(
            request,
            callback_state=callback_state,
            error_code=exc.code,
        )
        if redirect is not None:
            return redirect
        status_code = 400
        if exc.code == "provider_unavailable":
            status_code = 503
        elif exc.code in {"callback_denied", "provider_disabled", "workspace_enrollment_required"}:
            status_code = 403
        raise ProblemDetail(
            status=status_code,
            code=exc.code,
            title="Callback processing failed",
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        if link is not None and callback_state is not None:
            await db.rollback()
            return _provider_link_callback_redirect(
                callback_state,
                link,
                result="provider_link_invalid",
            )
        redirect = _browser_callback_error_redirect(
            request,
            callback_state=callback_state,
            error_code="callback_state_invalid",
        )
        if redirect is not None:
            return redirect
        raise ProblemDetail(
            status=400,
            code="callback_state_invalid",
            title="Callback state is invalid",
        ) from exc
    redirect_path = (
        _safe_browser_return_path(profile.requested_redirect) if profile.browser_bound else None
    )
    if redirect_path is not None:
        redirect_path = await resolve_browser_auth_return_path(
            db,
            requested_redirect=redirect_path,
            organization_id=profile.organization_id,
            workspace_id=profile.workspace_id,
            user_id=profile.user_id,
            auth_session_id=profile.auth_session_id,
        )
    # FR-021: capture before the final transaction commit. The acquisition
    # writer deliberately uses the caller's transaction (commit=False), so
    # placing it after the auth commit would close the session with the new row
    # still uncommitted and silently lose OAuth registration attribution.
    resolved_handoff = None
    if profile.registered:
        attribution_snapshot = await resolve_attribution_snapshot_for_request_async(request, db=db)
        await capture_client_acquisition_attribute(
            request,
            db=db,
            account_id=profile.user_id,
            snapshot=attribution_snapshot,
        )
        resolved_handoff = await attribution_handoff_for_request_async(
            request,
            db=db,
            snapshot=attribution_snapshot,
        )
    await db.commit()
    # The milestone is delivered after the response and never blocks sign-in.
    schedule_account_connected_milestone(
        background_tasks,
        request,
        user_id=profile.user_id,
        provider=provider,
        handoff=resolved_handoff,
    )
    payload = AuthCallbackResponse(
        user_id=profile.user_id,
        workspace_id=profile.workspace_id,
        active_session_id=profile.auth_session_id,
        session_token=profile.token,
        session_expires_at=profile.token_expires_at,
        provider=provider,
        provider_subject=profile.provider_subject,
        external_identity_id=profile.external_identity_id,
    )
    if redirect_path is not None:
        redirect = RedirectResponse(redirect_path, status_code=303)
        _set_auth_cookie(redirect, token=profile.token, expires_at=profile.token_expires_at)
        _clear_browser_auth_state_cookie(redirect)
        if profile.registered:
            redirect.delete_cookie(
                key="graf_referral_token",
                path="/",
                secure=True,
                httponly=True,
                samesite="lax",
            )
        return redirect
    if profile.browser_bound:
        _set_auth_cookie(response, token=profile.token, expires_at=profile.token_expires_at)
        _clear_browser_auth_state_cookie(response)
        if profile.registered:
            response.delete_cookie(
                key="graf_referral_token",
                path="/",
                secure=True,
                httponly=True,
                samesite="lax",
            )
    return payload


@router.post("/link", status_code=409, deprecated=True, dependencies=[WebCSRFDependency])
async def link_provider(
    request: Request,
    payload: AuthLinkRequest,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = AuthDbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    await _require_active_customer_membership(
        db,
        request=request,
        workspace_id=payload.expected_workspace_id,
        principal=principal,
    )
    await _record_auth_audit(
        db,
        request=request,
        workspace_id=payload.expected_workspace_id,
        event_type="provider_link_rejected",
        outcome="failure",
        actor_user_id=principal.user_id,
        provider=payload.candidate_provider,
        metadata={"error_code": "provider_link_requires_verified_callback"},
    )
    await db.commit()
    raise ProblemDetail(
        status=409,
        code="provider_link_requires_verified_callback",
        title="Provider link requires verified callback",
        detail="Direct provider subject linking is disabled; use the verified provider callback flow.",
    )


@router.post(
    "/devices/register", response_model=AuthDeviceStateResponse, dependencies=[WebCSRFDependency]
)
async def register_device(
    request: Request,
    payload: AuthDeviceRegisterRequest,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    db: AsyncSession | None = AuthDbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    workspace_id = _parse_workspace_id(x_workspace_id)
    await _require_active_customer_membership(
        db,
        request=request,
        workspace_id=workspace_id,
        principal=principal,
    )
    existing = await db.scalar(
        select(RegisteredDevice).where(
            RegisteredDevice.workspace_id == workspace_id,
            RegisteredDevice.device_public_id == payload.device_public_id,
        )
    )
    if existing is not None and existing.user_id != principal.user_id:
        raise ProblemDetail(status=409, code="duplicate_device", title="Device already exists")
    auth_session = None
    if principal.auth_via_session and principal.session_id is not None:
        auth_session = await db.scalar(select(AuthSession).where(
            AuthSession.id == principal.session_id,
            AuthSession.user_id == principal.user_id,
            AuthSession.workspace_id == workspace_id,
            AuthSession.status == "active",
        ).with_for_update().execution_options(populate_existing=True))
        if auth_session is None:
            raise ProblemDetail(status=401, code="auth_session_invalid", title="Session is unavailable")
        allowed, attached_device = await resolve_session_device(db, auth_session)
        if not allowed:
            raise ProblemDetail(status=403, code="device_untrusted", title="Device binding is unavailable")
        if attached_device is not None and (
            existing is None or existing.id != attached_device.id
        ):
            raise ProblemDetail(status=409, code="auth_session_mismatched", title="Session already has a device")
    device = existing
    if device is None:
        device = RegisteredDevice(
            workspace_id=workspace_id, user_id=principal.user_id,
            device_public_id=payload.device_public_id, platform=payload.platform,
            client_version=payload.client_version, status="active", registration_state="approved",
        )
        db.add(device)
        await db.flush()
    if device.status == "active" and device.registration_state == "approved":
        device.platform = payload.platform
        device.client_version = payload.client_version
        if auth_session is not None:
            binding = await db.scalar(select(AuthSessionDeviceBinding).where(
                AuthSessionDeviceBinding.auth_session_id == auth_session.id,
                AuthSessionDeviceBinding.registered_device_id == device.id,
            ))
            if binding is not None and binding.device_state != "trusted":
                raise ProblemDetail(status=403, code="device_untrusted", title="Device binding is unavailable")
            if binding is None:
                db.add(AuthSessionDeviceBinding(auth_session_id=auth_session.id,
                    registered_device_id=device.id, device_state="trusted"))
            auth_session.device_id = device.id
    await db.flush()
    await _record_auth_audit(
        db,
        request=request,
        workspace_id=workspace_id,
        event_type="device_registered",
        actor_user_id=principal.user_id,
        user_id=principal.user_id,
        provider="device",
        metadata={"device_public_id": payload.device_public_id},
    )
    await db.commit()
    return AuthDeviceStateResponse(
        device_id=device.id,
        status=device.status,
        registration_state=device.registration_state,
        created_at=device.created_at,
    )


@router.post(
    "/devices/{device_id}/revoke",
    response_model=AuthDeviceRevokeResponse,
    dependencies=[WebCSRFDependency],
)
async def revoke_device(
    request: Request,
    device_id: UUID,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    db: AsyncSession | None = AuthDbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    workspace_id = _parse_workspace_id(x_workspace_id)
    _, actor_membership = await _require_active_customer_membership(
        db,
        request=request,
        workspace_id=workspace_id,
        principal=principal,
    )
    device = await db.get(RegisteredDevice, device_id)
    if device is None or device.workspace_id != workspace_id:
        raise ProblemDetail(
            status=404,
            code="device_not_found",
            title="Device not found",
        )
    if device.user_id != principal.user_id and actor_membership.role not in {"owner", "admin"}:
        await _record_auth_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            event_type="device_revoked",
            outcome="failure",
            actor_user_id=principal.user_id,
            metadata={"error_code": "link_denied", "device_id": str(device_id)},
        )
        raise ProblemDetail(
            status=403,
            code="link_denied",
            title="Cannot revoke other user device",
        )
    await revoke_registered_devices(db, [device], actor_user_id=principal.user_id)
    await _record_auth_audit(
        db,
        request=request,
        workspace_id=workspace_id,
        event_type="device_revoked",
        outcome="success",
        actor_user_id=principal.user_id,
        user_id=device.user_id,
        provider="device",
        metadata={"device_id": str(device_id)},
    )
    await db.commit()
    return AuthDeviceRevokeResponse(
        device_id=device.id,
        status="revoked",
        revoked_at=datetime.now(UTC),
    )


@router.get("/me", response_model=MeResponse)
async def get_me(
    request: Request,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    db: AsyncSession | None = AuthDbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    workspace_id = _parse_workspace_id(x_workspace_id)
    workspace, membership = await _require_active_customer_membership(
        db,
        request=request,
        workspace_id=workspace_id,
        principal=principal,
    )
    user = await db.get(UserIdentity, principal.user_id)
    if user is None or user.status != "active":
        raise ProblemDetail(
            status=401,
            code="auth_required",
            title="User not found",
        )
    is_personal_owner = (
        membership.role == "owner"
        and workspace is not None
        and workspace.kind == "personal"
        and workspace.owner_user_id == principal.user_id
    )
    billing_role = (
        "owner"
        if is_personal_owner
        else ("admin" if membership.role in {"owner", "admin"} else "member")
    )
    identities = (
        (
            await db.execute(
                select(ExternalIdentity)
                .where(
                    ExternalIdentity.user_id == principal.user_id,
                    ExternalIdentity.is_active.is_(True),
                )
                .order_by(ExternalIdentity.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    primary_identity_id = identities[0].id if identities else None
    linked_providers = [
        LinkedProvider(
            provider=item.provider,
            provider_subject=item.provider_subject,
            is_primary=item.id == primary_identity_id,
            confirmed_at=item.last_seen_at,
        )
        for item in identities
    ]
    devices = (
        (
            await db.execute(
                select(RegisteredDevice)
                .where(
                    RegisteredDevice.workspace_id == workspace_id,
                    RegisteredDevice.user_id == principal.user_id,
                )
                .order_by(RegisteredDevice.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    registered_devices = [
        AuthDeviceStateResponse(
            device_id=item.id,
            status=item.status,
            registration_state=item.registration_state,
            created_at=item.created_at,
        )
        for item in devices
    ]
    active_session_id = None
    if principal.auth_via_session and principal.session_id is not None:
        session = await db.get(AuthSession, principal.session_id)
        if (
            session is not None
            and session.workspace_id == workspace_id
            and session.user_id == principal.user_id
        ):
            active_session_id = session.id
    policy = _policy_to_response(
        await read_auth_providers(
            db,
            workspace_id,
            adapters=build_provider_registry(),
        )
    )
    subscription = await db.scalar(
        select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace_id)
    )
    now = datetime.now(UTC)
    raw_plan_code = subscription.plan_code if subscription is not None else "free"
    plan_code = effective_plan_code(
        plan_code=raw_plan_code,  # type: ignore[arg-type]
        state=subscription.state if subscription is not None else "free",
        now=now,
        paid_through=subscription.paid_through if subscription is not None else None,
        trial_ends_at=subscription.trial_ends_at if subscription is not None else None,
    )
    capacity = (
        subscription.capacity_bytes
        if subscription is not None and plan_code in {"trial", "personal"}
        else FREE_STORAGE_BYTES
    )
    reserved = int(
        await db.scalar(
            select(
                func.coalesce(
                    func.sum(
                        StorageReservation.declared_bytes - StorageReservation.committed_bytes
                    ),
                    0,
                )
            ).where(
                StorageReservation.workspace_id == workspace_id,
                StorageReservation.state == "active",
                (StorageReservation.expires_at.is_(None) | (StorageReservation.expires_at > now)),
            )
        )
        or 0
    )
    storage = await project_active_playback_storage(
        db,
        workspace_id=workspace_id,
        capacity_bytes=capacity,
        reserved_bytes=max(0, reserved),
    )
    bonus_until = await db.scalar(
        select(func.max(TimeCreditLedgerEntry.applied_end)).where(
            TimeCreditLedgerEntry.workspace_id == workspace_id,
            TimeCreditLedgerEntry.state == "applied",
            TimeCreditLedgerEntry.applied_end.is_not(None),
            TimeCreditLedgerEntry.applied_end > now,
        )
    )
    owner_billing = billing_role == "owner"
    member_billing = billing_role == "member"
    safe_state = (
        (subscription.state if subscription is not None else "free")
        if owner_billing
        else ("active" if plan_code in {"trial", "personal"} else "free")
    )
    return MeResponse(
        user_id=user.id,
        workspace_id=workspace_id,
        active_session_id=active_session_id,
        linked_providers=linked_providers,
        policy=policy,
        registered_devices=registered_devices,
        billing=BillingSummaryResponse(
            plan_code=plan_code,
            state=safe_state,
            trial_ends_at=subscription.trial_ends_at
            if owner_billing and subscription is not None and plan_code == "trial"
            else None,
            paid_through=subscription.paid_through
            if owner_billing and subscription is not None and plan_code == "personal"
            else None,
            bonus_until=bonus_until if owner_billing else None,
            renewal_resolution=subscription.renewal_resolution
            if owner_billing and subscription is not None
            else None,
            processing_unlimited=plan_code in {"trial", "personal"},
            storage_used_bytes=None if member_billing else storage.used_bytes,
            storage_capacity_bytes=None if member_billing else storage.capacity_bytes,
        ),
    )
