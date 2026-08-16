from dataclasses import dataclass
from uuid import UUID

from twobrain_rec_server.auth.context import AuthenticatedPrincipal, DeviceContext, TenantScope

ORG_ID = UUID("10000000-0000-0000-0000-000000000001")
AUTH_BOOTSTRAP_WORKSPACE_ID = UUID("20000000-0000-0000-0000-000000000000")
WORKSPACE_ID = UUID("20000000-0000-0000-0000-000000000001")
PERSONAL_WORKSPACE_ID = UUID("20000000-0000-0000-0000-000000000002")
USER_ID = UUID("30000000-0000-0000-0000-000000000001")
DEVICE_ID = UUID("40000000-0000-0000-0000-000000000001")
REVOKED_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000099")
FORGED_USER_ID = UUID("30000000-0000-0000-0000-000000000099")


@dataclass(frozen=True, slots=True)
class DuplicateAccountFixture:
    user_id: UUID
    workspace_id: UUID
    email: str


def duplicate_account_fixture(slot: int, *, email: str | None = None) -> DuplicateAccountFixture:
    if not 1 <= slot <= 999999999999:
        raise ValueError("duplicate fixture slot must fit the deterministic UUID suffix")
    suffix = f"{slot:012d}"
    return DuplicateAccountFixture(
        user_id=UUID(f"30000000-0000-0000-0000-{suffix}"),
        workspace_id=UUID(f"20000000-0000-0000-0000-{suffix}"),
        email=email or f"duplicate-{slot}@example.test",
    )


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
