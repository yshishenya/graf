import base64
import binascii
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from fastapi import Cookie, Depends, Header, Request, Response
from sqlalchemy import and_, select

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, DeviceContext, TenantScope
from twobrain_rec_server.auth.csrf import CSRF_FORM_FIELD_NAME, CSRF_HEADER_NAME, require_csrf_token
from twobrain_rec_server.auth.sessions import decode_session_token, is_session_token_valid
from twobrain_rec_server.db.models import (
    AuthSession,
    AuthSessionDeviceBinding,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.db.tenant_context import (
    AuthSessionLookupContext,
    TenantDatabaseContext,
    apply_tenant_context,
)

AUTH_SESSION_COOKIE_NAME = "__Host-twobrain_rec_owner_session"
DESKTOP_CALENDAR_AUTH_COOKIE_NAME = "twobrain_rec_desktop_calendar_auth"
DESKTOP_CALENDAR_AUTH_COOKIE_PATH = "/desktop/settings/integrations/calendar"
DESKTOP_CALENDAR_AUTH_COOKIE_MAX_AGE_SECONDS = 15 * 60


@dataclass(frozen=True, slots=True)
class _DesktopCalendarAuthContext:
    user_id: UUID
    organization_id: UUID
    workspace_id: UUID
    device_id: UUID


def _parse_uuid(value: str | None, header_name: str) -> UUID:
    if not value:
        raise ProblemDetail(
            status=401,
            code="missing_auth_context",
            title="Missing authentication context",
            detail=f"{header_name} is required for auth context."
            " Use session token or legacy headers.",
        )
    try:
        return UUID(value)
    except ValueError as exc:
        raise ProblemDetail(
            status=400,
            code="invalid_auth_context",
            title="Invalid authentication context",
            detail=f"{header_name} must be a UUID.",
        ) from exc


def _extract_session_token(
    authorization: str | None,
    auth_session: str | None,
    auth_session_cookie: str | None = None,
) -> str | None:
    if auth_session is not None:
        token = auth_session.strip()
        if token:
            return token
    if auth_session_cookie is not None:
        token = auth_session_cookie.strip()
        if token:
            return token
    if not authorization:
        return None
    lowered = authorization.lower()
    if lowered.startswith("bearer "):
        return authorization[7:].strip()
    if lowered.startswith("token "):
        return authorization[6:].strip()
    return None


def _legacy_header_auth_allowed(request: Request) -> bool:
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        return True
    if getattr(settings, "env", "development").lower() != "production":
        return True
    return bool(getattr(settings, "legacy_header_auth_enabled", False))


def _ensure_legacy_header_auth_allowed(request: Request) -> None:
    if _legacy_header_auth_allowed(request):
        return
    raise ProblemDetail(
        status=401,
        code="legacy_header_auth_disabled",
        title="Legacy header authentication is disabled",
        detail="Use a validated auth session token in production.",
    )


def _desktop_calendar_auth_secret(request: Request) -> str:
    secret = getattr(request.app.state, "web_csrf_secret", None)
    if not secret:
        raise ProblemDetail(
            status=503,
            code="csrf_secret_unavailable",
            title="CSRF protection unavailable",
        )
    return str(secret)


def _is_desktop_calendar_request(request: Request) -> bool:
    return request.url.path.startswith(DESKTOP_CALENDAR_AUTH_COOKIE_PATH)


def _urlsafe_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _urlsafe_decode(payload: str) -> bytes:
    return base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))


def _sign_desktop_calendar_payload(payload: str, *, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), sha256).hexdigest()


def _desktop_calendar_cookie_value(
    *,
    principal: AuthenticatedPrincipal,
    tenant_scope: TenantScope,
    secret: str,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    payload = {
        "d": str(tenant_scope.device_id),
        "exp": int((issued_at + timedelta(seconds=DESKTOP_CALENDAR_AUTH_COOKIE_MAX_AGE_SECONDS)).timestamp()),
        "o": str(principal.organization_id),
        "u": str(principal.user_id),
        "w": str(tenant_scope.workspace_id),
    }
    encoded = _urlsafe_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    return f"{encoded}.{_sign_desktop_calendar_payload(encoded, secret=secret)}"


def _desktop_calendar_context_from_cookie(
    request: Request,
    token: str | None,
) -> _DesktopCalendarAuthContext | None:
    if not token or not _is_desktop_calendar_request(request):
        return None
    try:
        payload, signature = token.rsplit(".", 1)
    except ValueError as exc:
        raise ProblemDetail(status=401, code="desktop_calendar_auth_invalid", title="Desktop auth cookie is invalid") from exc
    expected = _sign_desktop_calendar_payload(payload, secret=_desktop_calendar_auth_secret(request))
    if not hmac.compare_digest(signature, expected):
        raise ProblemDetail(status=401, code="desktop_calendar_auth_invalid", title="Desktop auth cookie is invalid")
    try:
        decoded = json.loads(_urlsafe_decode(payload))
        if int(decoded["exp"]) < int(datetime.now(UTC).timestamp()):
            raise ValueError("expired")
        return _DesktopCalendarAuthContext(
            user_id=UUID(str(decoded["u"])),
            organization_id=UUID(str(decoded["o"])),
            workspace_id=UUID(str(decoded["w"])),
            device_id=UUID(str(decoded["d"])),
        )
    except (
        binascii.Error,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
    ) as exc:
        raise ProblemDetail(status=401, code="desktop_calendar_auth_invalid", title="Desktop auth cookie is invalid") from exc


def set_desktop_calendar_auth_cookie(
    response: Response,
    *,
    request: Request,
    principal: AuthenticatedPrincipal,
    tenant_scope: TenantScope,
) -> None:
    if principal.auth_via_session or not _is_desktop_calendar_request(request):
        return
    response.set_cookie(
        key=DESKTOP_CALENDAR_AUTH_COOKIE_NAME,
        value=_desktop_calendar_cookie_value(
            principal=principal,
            tenant_scope=tenant_scope,
            secret=_desktop_calendar_auth_secret(request),
        ),
        max_age=DESKTOP_CALENDAR_AUTH_COOKIE_MAX_AGE_SECONDS,
        path=DESKTOP_CALENDAR_AUTH_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite="strict",
    )


async def _principal_from_session_token(request: Request, token: str) -> AuthenticatedPrincipal | None:
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        raise ProblemDetail(
            status=503,
            code="auth_context_unavailable",
            title="Authentication context unavailable",
        )

    token_hash = decode_session_token(token)
    async with sessionmaker() as db:
        await apply_tenant_context(db, AuthSessionLookupContext(session_token_hash=token_hash))
        session = await db.scalar(
            select(AuthSession).where(
                AuthSession.session_token_hash == token_hash,
                AuthSession.status == "active",
            )
        )
        if session is None:
            raise ProblemDetail(
                status=401,
                code="auth_session_invalid",
                title="Session token is invalid",
            )
        if not is_session_token_valid(session, datetime.now(UTC)):
            session.status = "expired"
            await db.commit()
            raise ProblemDetail(
                status=401,
                code="auth_session_expired",
                title="Session token has expired",
            )

        user = await db.get(UserIdentity, session.user_id)
        if user is None or user.status != "active":
            raise ProblemDetail(
                status=403,
                code="auth_session_rejected",
                title="Session owner is not active",
            )
        return AuthenticatedPrincipal(
            user_id=user.id,
            organization_id=user.organization_id,
            workspace_ids=frozenset({session.workspace_id}),
            subject=str(user.id),
            session_id=session.id,
            auth_via_session=True,
            session_workspace_id=session.workspace_id,
            session_device_id=session.device_id,
        )


async def get_principal(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization", include_in_schema=False),
    x_auth_session: str | None = Header(default=None, alias="X-Auth-Session", include_in_schema=False),
    auth_session_cookie: str | None = Cookie(default=None, alias=AUTH_SESSION_COOKIE_NAME, include_in_schema=False),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    desktop_calendar_auth_cookie: str | None = Cookie(
        default=None,
        alias=DESKTOP_CALENDAR_AUTH_COOKIE_NAME,
        include_in_schema=False,
    ),
) -> AuthenticatedPrincipal:
    session_token = _extract_session_token(authorization, x_auth_session, auth_session_cookie)
    if session_token is not None:
        return await _principal_from_session_token(request, session_token)

    desktop_context = _desktop_calendar_context_from_cookie(request, desktop_calendar_auth_cookie)
    if desktop_context is not None:
        return AuthenticatedPrincipal(
            user_id=desktop_context.user_id,
            organization_id=desktop_context.organization_id,
            workspace_ids=frozenset({desktop_context.workspace_id}),
            subject=str(desktop_context.user_id),
            auth_via_session=False,
        )

    if any(value is not None for value in (x_user_id, x_organization_id, x_workspace_id)):
        _ensure_legacy_header_auth_allowed(request)
        user_id = _parse_uuid(x_user_id, "X-User-Id")
        organization_id = _parse_uuid(x_organization_id, "X-Organization-Id")
        workspace_id = _parse_uuid(x_workspace_id, "X-Workspace-Id")
        return AuthenticatedPrincipal(
            user_id=user_id,
            organization_id=organization_id,
            workspace_ids=frozenset({workspace_id}),
            subject=str(user_id),
            auth_via_session=False,
        )

    # No credentials is a normal unauthenticated browser/API request. Keep
    # the legacy-header guard for actual legacy-header attempts above, but do
    # not misclassify an empty request as a disabled legacy-auth flow.
    user_id = _parse_uuid(x_user_id, "X-User-Id")
    organization_id = _parse_uuid(x_organization_id, "X-Organization-Id")
    workspace_id = _parse_uuid(x_workspace_id, "X-Workspace-Id")
    return AuthenticatedPrincipal(
        user_id=user_id,
        organization_id=organization_id,
        workspace_ids=frozenset({workspace_id}),
        subject=str(user_id),
        auth_via_session=False,
    )


async def get_optional_principal(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization", include_in_schema=False),
    x_auth_session: str | None = Header(default=None, alias="X-Auth-Session", include_in_schema=False),
    auth_session_cookie: str | None = Cookie(default=None, alias=AUTH_SESSION_COOKIE_NAME, include_in_schema=False),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    desktop_calendar_auth_cookie: str | None = Cookie(
        default=None,
        alias=DESKTOP_CALENDAR_AUTH_COOKIE_NAME,
        include_in_schema=False,
    ),
) -> AuthenticatedPrincipal | None:
    if all(
        value is None
        for value in (
            authorization,
            x_auth_session,
            auth_session_cookie,
            x_user_id,
            x_organization_id,
            x_workspace_id,
            desktop_calendar_auth_cookie,
        )
    ):
        return None
    return await get_principal(
        request,
        authorization=authorization,
        x_auth_session=x_auth_session,
        auth_session_cookie=auth_session_cookie,
        x_user_id=x_user_id,
        x_organization_id=x_organization_id,
        x_workspace_id=x_workspace_id,
        desktop_calendar_auth_cookie=desktop_calendar_auth_cookie,
    )


async def get_device_context(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization", include_in_schema=False),
    x_auth_session: str | None = Header(default=None, alias="X-Auth-Session", include_in_schema=False),
    auth_session_cookie: str | None = Cookie(default=None, alias=AUTH_SESSION_COOKIE_NAME, include_in_schema=False),
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    x_client_version: str | None = Header(default=None, alias="X-Client-Version"),
    x_device_registration_state: str | None = Header(default=None, alias="X-Device-Registration-State", include_in_schema=False),
    x_device_trust_state: str | None = Header(default=None, alias="X-Device-Trust-State", include_in_schema=False),
) -> DeviceContext:
    session_token = _extract_session_token(authorization, x_auth_session, auth_session_cookie)
    if session_token is not None:
        principal = await _principal_from_session_token(request, session_token)
        if x_device_id and x_workspace_id:
            return DeviceContext(
                device_id=_parse_uuid(x_device_id, "X-Device-Id"),
                workspace_id=_parse_uuid(x_workspace_id, "X-Workspace-Id"),
                client_version=x_client_version,
                registration_state=x_device_registration_state,
                trust_state=x_device_trust_state,
            )
        if principal is not None and principal.session_device_id is not None and principal.session_workspace_id is not None:
            return DeviceContext(
                device_id=principal.session_device_id,
                workspace_id=principal.session_workspace_id,
                client_version=x_client_version,
                registration_state=x_device_registration_state,
                trust_state=x_device_trust_state,
            )
        raise ProblemDetail(
            status=401,
            code="auth_session_mismatched",
            title="Auth session context does not match workspace context",
        )

    _ensure_legacy_header_auth_allowed(request)
    return DeviceContext(
        device_id=_parse_uuid(x_device_id, "X-Device-Id"),
        workspace_id=_parse_uuid(x_workspace_id, "X-Workspace-Id"),
        client_version=x_client_version,
        registration_state=x_device_registration_state,
        trust_state=x_device_trust_state,
    )


PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)


async def get_web_csrf_secret(request: Request) -> str:
    secret = getattr(request.app.state, "web_csrf_secret", None)
    if not secret:
        raise ProblemDetail(
            status=503,
            code="csrf_secret_unavailable",
            title="CSRF protection unavailable",
        )
    return str(secret)


async def require_web_csrf(
    request: Request,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    x_auth_session: str | None = Header(default=None, alias="X-Auth-Session", include_in_schema=False),
    auth_session_cookie: str | None = Cookie(default=None, alias=AUTH_SESSION_COOKIE_NAME, include_in_schema=False),
    x_csrf_token: str | None = Header(default=None, alias=CSRF_HEADER_NAME, include_in_schema=False),
    desktop_calendar_auth_cookie: str | None = Cookie(
        default=None,
        alias=DESKTOP_CALENDAR_AUTH_COOKIE_NAME,
        include_in_schema=False,
    ),
    csrf_secret: str = Depends(get_web_csrf_secret),
) -> None:
    csrf_subject_id = None
    if principal.auth_via_session:
        if auth_session_cookie and not (x_auth_session or "").strip():
            csrf_subject_id = principal.session_id
    else:
        desktop_context = _desktop_calendar_context_from_cookie(request, desktop_calendar_auth_cookie)
        csrf_subject_id = desktop_context.device_id if desktop_context is not None else None
    if csrf_subject_id is None:
        return
    form_token: str | None = None
    if x_csrf_token is None and request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
        form = await request.form()
        value = form.get(CSRF_FORM_FIELD_NAME)
        form_token = str(value) if value is not None else None
    require_csrf_token(x_csrf_token or form_token, session_id=csrf_subject_id, secret=csrf_secret)


async def get_tenant_scope(
    request: Request,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
) -> TenantScope:
    return await _validate_tenant_scope(
        request,
        principal=principal,
        workspace_id=device.workspace_id,
        device_id=device.device_id,
    )


async def get_web_owner_tenant_scope(
    request: Request,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
    desktop_calendar_auth_cookie: str | None = Cookie(
        default=None,
        alias=DESKTOP_CALENDAR_AUTH_COOKIE_NAME,
        include_in_schema=False,
    ),
) -> TenantScope:
    if principal.auth_via_session:
        if principal.session_workspace_id is None or principal.session_device_id is None:
            raise ProblemDetail(
                status=401,
                code="auth_session_mismatched",
                title="Auth session context does not match workspace context",
            )
        return await _validate_tenant_scope(
            request,
            principal=principal,
            workspace_id=principal.session_workspace_id,
            device_id=principal.session_device_id,
        )

    desktop_context = _desktop_calendar_context_from_cookie(request, desktop_calendar_auth_cookie)
    if desktop_context is not None:
        return await _validate_tenant_scope(
            request,
            principal=principal,
            workspace_id=desktop_context.workspace_id,
            device_id=desktop_context.device_id,
        )

    if x_workspace_id is not None or x_device_id is not None:
        return await _validate_tenant_scope(
            request,
            principal=principal,
            workspace_id=_parse_uuid(x_workspace_id, "X-Workspace-Id"),
            device_id=_parse_uuid(x_device_id, "X-Device-Id"),
        )

    return await _validate_tenant_scope(
        request,
        principal=principal,
        workspace_id=_parse_uuid(x_workspace_id, "X-Workspace-Id"),
        device_id=_parse_uuid(x_device_id, "X-Device-Id"),
    )


async def _validate_tenant_scope(
    request: Request,
    *,
    principal: AuthenticatedPrincipal,
    workspace_id: UUID,
    device_id: UUID,
) -> TenantScope:
    if workspace_id not in principal.workspace_ids:
        raise ProblemDetail(
            status=403,
            code="workspace_scope_denied",
            title="Workspace scope denied",
        )
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        raise ProblemDetail(
            status=503,
            code="auth_context_unavailable",
            title="Authentication context unavailable",
        )
    async with sessionmaker() as db:
        await apply_tenant_context(
            db,
            TenantDatabaseContext(
                organization_id=principal.organization_id,
                workspace_id=workspace_id,
                user_id=principal.user_id,
                device_id=device_id,
                auth_session_id=principal.session_id,
            ),
        )
        user = await db.get(UserIdentity, principal.user_id)
        workspace = await db.get(Workspace, workspace_id)
        membership = await db.scalar(
            select(WorkspaceMembership).where(
                and_(
                    WorkspaceMembership.workspace_id == workspace_id,
                    WorkspaceMembership.user_id == principal.user_id,
                )
            )
        )
        registered_device = await db.get(RegisteredDevice, device_id)
        membership_is_inactive = membership is None or membership.status != "active"
        if (
            user is None
            or user.organization_id != principal.organization_id
            or user.status != "active"
            or workspace is None
            or workspace.organization_id != principal.organization_id
            or membership_is_inactive
            or registered_device is None
            or registered_device.workspace_id != workspace_id
            or registered_device.user_id != principal.user_id
        ):
            if principal.auth_via_session and principal.session_id is not None and membership_is_inactive:
                session = await db.get(AuthSession, principal.session_id)
                if session is not None and session.status == "active":
                    session.status = "revoked"
                    await db.commit()
            raise ProblemDetail(
                status=403,
                code="workspace_scope_denied",
                title="Workspace scope denied",
                headers={"X-GRAF-Cabinet-Recovery": "reselect-space"}
                if membership_is_inactive and request.url.path.startswith("/desktop/")
                else None,
            )
        if registered_device.status == "revoked" or registered_device.registration_state == "revoked":
            raise ProblemDetail(
                status=403,
                code="device_revoked",
                title="Device is revoked",
            )
        if registered_device.status == "quarantined":
            raise ProblemDetail(
                status=403,
                code="device_quarantined",
                title="Device is quarantined",
            )
        if registered_device.status != "active":
            raise ProblemDetail(
                status=403,
                code="workspace_scope_denied",
                title="Workspace scope denied",
            )
        if principal.auth_via_session and principal.session_id is not None:
            session = await db.get(AuthSession, principal.session_id)
            if (
                session is None
                or session.workspace_id != workspace_id
                or session.user_id != principal.user_id
                or (session.device_id is not None and session.device_id != device_id)
            ):
                raise ProblemDetail(
                    status=401,
                    code="auth_session_mismatched",
                    title="Auth session context does not match workspace context",
                )
            if not is_session_token_valid(session, datetime.now(UTC)):
                session.status = "expired"
                await db.commit()
                raise ProblemDetail(
                    status=401,
                    code="auth_session_expired",
                    title="Auth session has expired",
                )
            if session.status != "active":
                raise ProblemDetail(
                    status=403,
                    code="auth_session_invalid",
                    title="Auth session is not active",
                )
            binding = await db.scalar(
                select(AuthSessionDeviceBinding).where(
                    AuthSessionDeviceBinding.auth_session_id == session.id,
                    AuthSessionDeviceBinding.registered_device_id == registered_device.id,
                )
            )
            if binding is None:
                raise ProblemDetail(
                    status=403,
                    code="device_untrusted",
                    title="Device is not trusted for this session",
                )
            if binding is not None and binding.device_state == "blocked":
                raise ProblemDetail(
                    status=403,
                    code="device_revoked",
                    title="Device session binding is blocked",
                )
            if binding.device_state != "trusted":
                raise ProblemDetail(
                    status=403,
                    code="device_untrusted",
                    title="Device is not trusted for this session",
                )

    return TenantScope(
        organization_id=principal.organization_id,
        workspace_id=workspace_id,
        user_id=principal.user_id,
        device_id=device_id,
        auth_session_id=principal.session_id,
    )
