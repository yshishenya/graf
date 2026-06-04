from uuid import UUID

from twobrain_rec_server.auth.context import AuthenticatedPrincipal, DeviceContext, TenantScope

ORG_ID = UUID("10000000-0000-0000-0000-000000000001")
WORKSPACE_ID = UUID("20000000-0000-0000-0000-000000000001")
USER_ID = UUID("30000000-0000-0000-0000-000000000001")
DEVICE_ID = UUID("40000000-0000-0000-0000-000000000001")
REVOKED_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000099")
FORGED_USER_ID = UUID("30000000-0000-0000-0000-000000000099")


def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=USER_ID,
        organization_id=ORG_ID,
        workspace_ids=frozenset({WORKSPACE_ID}),
        subject=str(USER_ID),
    )


def device() -> DeviceContext:
    return DeviceContext(device_id=DEVICE_ID, workspace_id=WORKSPACE_ID)


def tenant_scope() -> TenantScope:
    return TenantScope(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        user_id=USER_ID,
        device_id=DEVICE_ID,
    )
