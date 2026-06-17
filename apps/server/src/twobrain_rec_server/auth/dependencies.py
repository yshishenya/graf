from datetime import UTC, datetime
from uuid import UUID

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy import and_, select

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, DeviceContext, TenantScope
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
    if auth_session:
        return auth_session.strip()
    if auth_session_cookie:
        return auth_session_cookie.strip()
    if not authorization:
        return None
    lowered = authorization.lower()
    if lowered.startswith("bearer "):
        return authorization[7:].strip()
    if lowered.startswith("token "):
        return authorization[6:].strip()
    return None


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
) -> AuthenticatedPrincipal:
    session_token = _extract_session_token(authorization, x_auth_session, auth_session_cookie)
    if session_token is not None:
        return await _principal_from_session_token(request, session_token)

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


async def get_device_context(
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    x_client_version: str | None = Header(default=None, alias="X-Client-Version"),
    x_device_registration_state: str | None = Header(default=None, alias="X-Device-Registration-State", include_in_schema=False),
    x_device_trust_state: str | None = Header(default=None, alias="X-Device-Trust-State", include_in_schema=False),
) -> DeviceContext:
    return DeviceContext(
        device_id=_parse_uuid(x_device_id, "X-Device-Id"),
        workspace_id=_parse_uuid(x_workspace_id, "X-Workspace-Id"),
        client_version=x_client_version,
        registration_state=x_device_registration_state,
        trust_state=x_device_trust_state,
    )


PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)


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
        if (
            user is None
            or user.organization_id != principal.organization_id
            or user.status != "active"
            or workspace is None
            or workspace.organization_id != principal.organization_id
            or membership is None
            or membership.status != "active"
            or registered_device is None
            or registered_device.workspace_id != workspace_id
            or registered_device.user_id != principal.user_id
        ):
            raise ProblemDetail(
                status=403,
                code="workspace_scope_denied",
                title="Workspace scope denied",
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
            if session.status not in {"active"}:
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
