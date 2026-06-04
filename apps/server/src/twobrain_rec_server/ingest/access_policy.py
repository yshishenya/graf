from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AccessPolicySnapshot:
    meeting_id: UUID
    workspace_id: UUID
    visibility: str = "owner_only"
    share_available: bool = False
    download_available: bool = False


def default_access_policy(meeting_id: UUID, workspace_id: UUID) -> AccessPolicySnapshot:
    return AccessPolicySnapshot(meeting_id=meeting_id, workspace_id=workspace_id)
