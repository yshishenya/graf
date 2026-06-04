from dataclasses import dataclass
from uuid import UUID

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.domain.statuses import UploadStrategy


@dataclass(frozen=True, slots=True)
class UploadAuthorization:
    upload_strategy: UploadStrategy
    workspace_id: UUID
    device_id: UUID
    server_mediated: bool = True


def build_upload_authorization(tenant_scope: TenantScope) -> UploadAuthorization:
    return UploadAuthorization(
        upload_strategy=UploadStrategy.SERVER_MEDIATED,
        workspace_id=tenant_scope.workspace_id,
        device_id=tenant_scope.device_id,
    )


def can_access_owner_resource(tenant_scope: TenantScope, *, owner_user_id: UUID, workspace_id: UUID) -> bool:
    return tenant_scope.workspace_id == workspace_id and tenant_scope.user_id == owner_user_id


def can_access_workspace_resource(tenant_scope: TenantScope, *, workspace_id: UUID) -> bool:
    return tenant_scope.workspace_id == workspace_id
