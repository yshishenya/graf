from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AccessPolicySnapshot:
    meeting_id: UUID
    workspace_id: UUID
    visibility: str = "owner_only"
    owner_user_id: UUID | None = None
    admin_eligible: bool = False
    share_available: bool = False
    share_denial_reason: str = "share_not_implemented"
    download_available: bool = False
    download_denial_reason: str = "download_not_implemented"
    export_available: bool = False
    export_denial_reason: str = "export_not_implemented"
    deletion_state: str = "not_requested"
    deletion_denial_reason: str | None = None


def default_access_policy(
    meeting_id: UUID,
    workspace_id: UUID,
    owner_user_id: UUID | None = None,
    admin_eligible: bool = False,
    deletion_state: str = "not_requested",
) -> AccessPolicySnapshot:
    return AccessPolicySnapshot(
        meeting_id=meeting_id,
        workspace_id=workspace_id,
        owner_user_id=owner_user_id,
        admin_eligible=admin_eligible,
        deletion_state=deletion_state,
    )
