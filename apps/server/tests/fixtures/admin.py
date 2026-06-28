from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from tests.fakes.auth_contexts import ORG_ID, WORKSPACE_ID
from twobrain_rec_server.db.models import (
    Organization,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)

ADMIN_ORG_ID = UUID("64000000-0000-0000-0000-000000000001")
ADMIN_WORKSPACE_ID = UUID("64000000-0000-0000-0000-000000000002")
ADMIN_FOREIGN_WORKSPACE_ID = UUID("64000000-0000-0000-0000-000000000003")
ADMIN_OWNER_ID = UUID("64000000-0000-0000-0000-000000000011")
ADMIN_SECOND_OWNER_ID = UUID("64000000-0000-0000-0000-000000000012")
ADMIN_ADMIN_ID = UUID("64000000-0000-0000-0000-000000000013")
ADMIN_MEMBER_ID = UUID("64000000-0000-0000-0000-000000000014")
ADMIN_INACTIVE_MEMBER_ID = UUID("64000000-0000-0000-0000-000000000015")
ADMIN_FOREIGN_USER_ID = UUID("64000000-0000-0000-0000-000000000016")
ADMIN_DEVICE_ID = UUID("64000000-0000-0000-0000-000000000021")
DEFAULT_ADMIN_USER_ID = UUID("30000000-0000-0000-0000-000000000101")
DEFAULT_MEMBER_USER_ID = UUID("30000000-0000-0000-0000-000000000102")
DEFAULT_ADMIN_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000101")
DEFAULT_MEMBER_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000102")


@dataclass(frozen=True, slots=True)
class AdminWorkspaceSeed:
    organization_id: UUID = ADMIN_ORG_ID
    workspace_id: UUID = ADMIN_WORKSPACE_ID
    foreign_workspace_id: UUID = ADMIN_FOREIGN_WORKSPACE_ID
    owner_id: UUID = ADMIN_OWNER_ID
    second_owner_id: UUID = ADMIN_SECOND_OWNER_ID
    admin_id: UUID = ADMIN_ADMIN_ID
    member_id: UUID = ADMIN_MEMBER_ID
    inactive_member_id: UUID = ADMIN_INACTIVE_MEMBER_ID
    foreign_user_id: UUID = ADMIN_FOREIGN_USER_ID
    device_id: UUID = ADMIN_DEVICE_ID


async def seed_admin_workspace(db: AsyncSession, *, second_owner: bool = True) -> AdminWorkspaceSeed:
    seed = AdminWorkspaceSeed()
    db.add_all(
        [
            Organization(id=seed.organization_id, slug="admin-org", name="Admin Org"),
            Workspace(
                id=seed.workspace_id,
                organization_id=seed.organization_id,
                slug="admin-workspace",
                name="Админ workspace",
            ),
            Workspace(
                id=seed.foreign_workspace_id,
                organization_id=seed.organization_id,
                slug="foreign-workspace",
                name="Чужой workspace",
            ),
            UserIdentity(
                id=seed.owner_id,
                organization_id=seed.organization_id,
                external_subject=str(seed.owner_id),
                display_name="Owner",
            ),
            UserIdentity(
                id=seed.second_owner_id,
                organization_id=seed.organization_id,
                external_subject=str(seed.second_owner_id),
                display_name="Second Owner",
            ),
            UserIdentity(
                id=seed.admin_id,
                organization_id=seed.organization_id,
                external_subject=str(seed.admin_id),
                display_name="Admin",
            ),
            UserIdentity(
                id=seed.member_id,
                organization_id=seed.organization_id,
                external_subject=str(seed.member_id),
                display_name="Member",
            ),
            UserIdentity(
                id=seed.inactive_member_id,
                organization_id=seed.organization_id,
                external_subject=str(seed.inactive_member_id),
                display_name="Inactive Member",
            ),
            UserIdentity(
                id=seed.foreign_user_id,
                organization_id=seed.organization_id,
                external_subject=str(seed.foreign_user_id),
                display_name="Foreign User",
            ),
            WorkspaceMembership(
                workspace_id=seed.workspace_id,
                user_id=seed.owner_id,
                role="owner",
                status="active",
            ),
            WorkspaceMembership(
                workspace_id=seed.workspace_id,
                user_id=seed.admin_id,
                role="admin",
                status="active",
            ),
            WorkspaceMembership(
                workspace_id=seed.workspace_id,
                user_id=seed.member_id,
                role="member",
                status="active",
            ),
            WorkspaceMembership(
                workspace_id=seed.workspace_id,
                user_id=seed.inactive_member_id,
                role="member",
                status="inactive",
            ),
            WorkspaceMembership(
                workspace_id=seed.foreign_workspace_id,
                user_id=seed.foreign_user_id,
                role="owner",
                status="active",
            ),
            RegisteredDevice(
                id=seed.device_id,
                workspace_id=seed.workspace_id,
                user_id=seed.owner_id,
                device_public_id="admin-device",
                status="active",
            ),
        ]
    )
    if second_owner:
        db.add(
            WorkspaceMembership(
                workspace_id=seed.workspace_id,
                user_id=seed.second_owner_id,
                role="owner",
                status="active",
            )
        )
    await db.commit()
    return seed


async def seed_default_workspace_admin_roles(db: AsyncSession) -> None:
    db.add_all(
        [
            UserIdentity(
                id=DEFAULT_ADMIN_USER_ID,
                organization_id=ORG_ID,
                external_subject=str(DEFAULT_ADMIN_USER_ID),
                display_name="Workspace Admin",
            ),
            UserIdentity(
                id=DEFAULT_MEMBER_USER_ID,
                organization_id=ORG_ID,
                external_subject=str(DEFAULT_MEMBER_USER_ID),
                display_name="Workspace Member",
            ),
            WorkspaceMembership(
                workspace_id=WORKSPACE_ID,
                user_id=DEFAULT_ADMIN_USER_ID,
                role="admin",
                status="active",
            ),
            WorkspaceMembership(
                workspace_id=WORKSPACE_ID,
                user_id=DEFAULT_MEMBER_USER_ID,
                role="member",
                status="active",
            ),
            RegisteredDevice(
                id=DEFAULT_ADMIN_DEVICE_ID,
                workspace_id=WORKSPACE_ID,
                user_id=DEFAULT_ADMIN_USER_ID,
                device_public_id="default-admin-device",
                status="active",
            ),
            RegisteredDevice(
                id=DEFAULT_MEMBER_DEVICE_ID,
                workspace_id=WORKSPACE_ID,
                user_id=DEFAULT_MEMBER_USER_ID,
                device_public_id="default-member-device",
                status="active",
            ),
        ]
    )
    await db.commit()


def auth_headers_for(*, user_id: UUID, device_id: UUID, workspace_id: UUID = WORKSPACE_ID) -> dict[str, str]:
    return {
        "X-Organization-Id": str(ORG_ID),
        "X-Workspace-Id": str(workspace_id),
        "X-User-Id": str(user_id),
        "X-Device-Id": str(device_id),
    }
