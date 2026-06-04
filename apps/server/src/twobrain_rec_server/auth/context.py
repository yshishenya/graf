from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    user_id: UUID
    organization_id: UUID
    workspace_ids: frozenset[UUID]
    subject: str


@dataclass(frozen=True, slots=True)
class DeviceContext:
    device_id: UUID
    workspace_id: UUID
    platform: str = "macos"
    client_version: str | None = None


@dataclass(frozen=True, slots=True)
class TenantScope:
    organization_id: UUID
    workspace_id: UUID
    user_id: UUID
    device_id: UUID
    upload_session_id: UUID | None = None
