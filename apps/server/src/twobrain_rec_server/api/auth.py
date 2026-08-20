from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
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
    confirm_provider_link,
    create_link_intent,
    link_for_callback,
)
from twobrain_rec_server.auth.providers import build_provider_registry, get_provider_adapter
from twobrain_rec_server.auth.providers.base import ProviderCredentials
from twobrain_rec_server.auth.sessions import create_callback_state
from twobrain_rec_server.billing.catalog import FREE_STORAGE_BYTES
from twobrain_rec_server.billing.entitlements import effective_plan_code
from twobrain_rec_server.billing.storage import project_active_playback_storage
from twobrain_rec_server.cabinet.auth_return import resolve_browser_auth_return_path
from twobrain_rec_server.config import Settings
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
    WorkspaceSubscription,
)
from twobrain_rec_server.db.tenant_context import (
    AuthCallbackLookupContext,
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context,
)
from twobrain_rec_server.product_analytics.events import build_activation_event

BROWSER_AUTH_STATE_COOKIE_NAME = "__Host-twobrain_rec_browser_auth_state"


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


router = APIRouter(prefix="/api/v1/auth", tags=["auth"], responses=PROBLEM_RESPONSES, include_in_schema=True)
WebCSRFDependency = Depends(require_web_csrf)


def build_account_connected_product_analytics_payload(
    *,
    stable_pseudonymous_user_id: str,
    auth_method_category: str,
    bridge_present: bool,
    attribution_reliability: str = "campaign_linked_reliable",
    elapsed_bucket: str | None = None,
) -> dict[str, object]:
    event = build_activation_event(
        "desktop_account_connected",
        stable_pseudonymous_user_id=stable_pseudonymous_user_id,
        properties={
            "auth_method_category": auth_method_category,
            "account_connection_state": "connected",
            "bridge_present": bridge_present,
            "attribution_reliability": attribution_reliability,
            **({"elapsed_bucket": elapsed_bucket} if elapsed_bucket else {}),
        },
    )
    return event.as_payload()


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
        or (workspace.owner_user_id == principal.user_id and membership is not None and membership.role == "owner")
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


def _provider_credentials(settings: Settings, provider: str, redirect_uri: str) -> ProviderCredentials:
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


def _safe_browser_return_path(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or not stripped.startswith("/") or stripped.startswith("//"):
        return None
    if any(char in stripped for char in "\r\n"):
        return None
    return stripped


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


def _policy_to_response(snapshot: AuthPolicySnapshot, *, include_disabled: bool = False) -> AuthProvidersResponse:
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
    snapshot = await update_workspace_auth_policy(db, workspace_id=workspace_id, policy_updates=updates)
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
    provider_policy = next((entry for entry in snapshot.providers if entry.provider == normalized_provider), None)
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
        raise ProblemDetail(status=403, code="provider_missing", title="Provider is not configured") from exc
    snapshot = await read_auth_providers(db, workspace_id, adapters=adapters, persist_defaults=True)
    provider_policy = next((entry for entry in snapshot.providers if entry.provider == normalized_provider), None)
    if provider_policy is None or not provider_policy.enabled:
        raise ProblemDetail(status=403, code="provider_disabled", title="Provider disabled")
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
        raise ProblemDetail(status=503, code="provider_link_unavailable", title="Provider link unavailable")
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
        raise ProblemDetail(status=status_code, code=exc.code, title="Provider link denied") from exc
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
    provider: str,
    state: str | None = Query(default=None, description="Callback state"),
    db: AsyncSession | None = AuthDbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    if not state:
        raise ProblemDetail(
            status=400,
            code="callback_state_invalid",
            title="Callback state is missing",
            detail="callback state is required",
        )
    auth_bootstrap_workspace_id = _internal_auth_workspace_id(request)
    await apply_tenant_context(db, AuthCallbackLookupContext(state_nonce=state))
    provider = provider.lower()
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
            redirect_path = _safe_browser_return_path(callback_state.requested_redirect)
            if redirect_path is None:
                redirect_path = f"/settings/provider-links/{link.id}"
            redirect = RedirectResponse(
                f"{redirect_path}?result=callback_verified",
                status_code=303,
            )
            _clear_browser_auth_state_cookie(redirect)
            return redirect
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
        )
    except CallbackFlowError as exc:
        await db.commit()
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
        raise ProblemDetail(
            status=400,
            code="callback_state_invalid",
            title="Callback state is invalid",
        ) from exc
    redirect_path = _safe_browser_return_path(profile.requested_redirect)
    if redirect_path is not None:
        redirect_path = await resolve_browser_auth_return_path(
            db,
            requested_redirect=redirect_path,
            organization_id=profile.organization_id,
            workspace_id=profile.workspace_id,
            user_id=profile.user_id,
            auth_session_id=profile.auth_session_id,
        )
    await db.commit()
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


@router.post("/devices/register", response_model=AuthDeviceStateResponse, dependencies=[WebCSRFDependency])
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
    if existing is not None:
        if existing.user_id != principal.user_id:
            await _record_auth_audit(
                db,
                request=request,
                workspace_id=workspace_id,
                event_type="device_registered",
                outcome="failure",
                actor_user_id=principal.user_id,
                metadata={"error_code": "duplicate_device"},
            )
            raise ProblemDetail(
                status=409,
                code="duplicate_device",
                title="Device already exists",
            )
        existing.platform = payload.platform
        existing.client_version = payload.client_version
        await _record_auth_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            event_type="device_registered",
            actor_user_id=principal.user_id,
            user_id=principal.user_id,
            provider="device",
            metadata={"status": existing.status, "registration_state": existing.registration_state},
        )
        await db.commit()
        return AuthDeviceStateResponse(
            device_id=existing.id,
            status=existing.status,
            registration_state=existing.registration_state,
            created_at=existing.created_at,
        )

    device = RegisteredDevice(
        workspace_id=workspace_id,
        user_id=principal.user_id,
        device_public_id=payload.device_public_id,
        platform=payload.platform,
        client_version=payload.client_version,
        status="active",
        registration_state="approved",
    )
    db.add(device)
    await db.flush()
    if principal.auth_via_session and principal.session_id is not None:
        auth_session = await db.get(AuthSession, principal.session_id)
        if auth_session is not None and auth_session.workspace_id == workspace_id:
            db.add(
                AuthSessionDeviceBinding(
                    auth_session_id=auth_session.id,
                    registered_device_id=device.id,
                    device_state="trusted",
                )
            )
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
    device.status = "revoked"
    device.registration_state = "revoked"
    device.revoked_by = principal.user_id
    bindings = (
        (
            await db.execute(
                select(AuthSessionDeviceBinding).where(
                    AuthSessionDeviceBinding.registered_device_id == device.id,
                )
            )
        )
        .scalars()
        .all()
    )
    for binding in bindings:
        binding.device_state = "blocked"
        binding.revocation_reason = "device_revoked"
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
    billing_role = "owner" if is_personal_owner else ("admin" if membership.role in {"owner", "admin"} else "member")
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
        if session is not None and session.workspace_id == workspace_id and session.user_id == principal.user_id:
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
                    func.sum(StorageReservation.declared_bytes - StorageReservation.committed_bytes),
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
            renewal_resolution=subscription.renewal_resolution if owner_billing and subscription is not None else None,
            processing_unlimited=plan_code in {"trial", "personal"},
            storage_used_bytes=None if member_billing else storage.used_bytes,
            storage_capacity_bytes=None if member_billing else storage.capacity_bytes,
        ),
    )
