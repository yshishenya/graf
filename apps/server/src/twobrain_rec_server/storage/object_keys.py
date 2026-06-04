from uuid import UUID

from twobrain_rec_server.domain.statuses import TrackRole


def build_track_object_key(
    *,
    organization_id: UUID,
    workspace_id: UUID,
    meeting_id: UUID,
    upload_session_id: UUID,
    track_role: TrackRole,
    part_number: int,
) -> str:
    return (
        f"organizations/{organization_id}/workspaces/{workspace_id}/"
        f"meetings/{meeting_id}/sessions/{upload_session_id}/"
        f"tracks/{track_role.value}/parts/{part_number:08d}"
    )


def build_final_artifact_prefix(
    *,
    organization_id: UUID,
    workspace_id: UUID,
    meeting_id: UUID,
) -> str:
    return f"organizations/{organization_id}/workspaces/{workspace_id}/meetings/{meeting_id}/artifacts"
