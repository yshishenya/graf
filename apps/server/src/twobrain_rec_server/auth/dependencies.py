from uuid import UUID

from fastapi import Depends, Header, Request
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, DeviceContext, TenantScope
from twobrain_rec_server.db.models import (
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)


def _parse_uuid(value: str | None, header_name: str) -> UUID:
    if not value:
        raise ProblemDetail(
            status=401,
            code="missing_auth_context",
            title="Missing authentication context",
            detail=f"{header_name} is required for 012 provider-neutral auth.",
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


async def get_principal(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
) -> AuthenticatedPrincipal:
    user_id = _parse_uuid(x_user_id, "X-User-Id")
    organization_id = _parse_uuid(x_organization_id, "X-Organization-Id")
    workspace_id = _parse_uuid(x_workspace_id, "X-Workspace-Id")
    return AuthenticatedPrincipal(
        user_id=user_id,
        organization_id=organization_id,
        workspace_ids=frozenset({workspace_id}),
        subject=str(user_id),
    )


async def get_device_context(
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    x_client_version: str | None = Header(default=None, alias="X-Client-Version"),
) -> DeviceContext:
    return DeviceContext(
        device_id=_parse_uuid(x_device_id, "X-Device-Id"),
        workspace_id=_parse_uuid(x_workspace_id, "X-Workspace-Id"),
        client_version=x_client_version,
    )


PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)


async def get_tenant_scope(
    request: Request,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
) -> TenantScope:
    if device.workspace_id not in principal.workspace_ids:
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
        user = await db.get(UserIdentity, principal.user_id)
        workspace = await db.get(Workspace, device.workspace_id)
        membership = await db.get(
            WorkspaceMembership,
            {"workspace_id": device.workspace_id, "user_id": principal.user_id},
        )
        registered_device = await db.get(RegisteredDevice, device.device_id)
        if (
            user is None
            or user.organization_id != principal.organization_id
            or user.status != "active"
            or workspace is None
            or workspace.organization_id != principal.organization_id
            or membership is None
            or membership.status != "active"
            or registered_device is None
            or registered_device.workspace_id != device.workspace_id
            or registered_device.user_id != principal.user_id
            or registered_device.status != "active"
        ):
            raise ProblemDetail(
                status=403,
                code="workspace_scope_denied",
                title="Workspace scope denied",
            )
    return TenantScope(
        organization_id=principal.organization_id,
        workspace_id=device.workspace_id,
        user_id=principal.user_id,
        device_id=device.device_id,
    )
