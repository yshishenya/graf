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


def build_playback_attempt_object_key(
    *,
    organization_id: UUID,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID,
    attempt_id: UUID,
) -> str:
    prefix = build_final_artifact_prefix(
        organization_id=organization_id,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    return (
        f"{prefix}/playback-normalization/revisions/{media_revision_id}/"
        f"attempts/{attempt_id}/meeting-review.m4a"
    )


def build_canonical_playback_object_key(
    *,
    organization_id: UUID,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID,
    attempt_id: UUID,
) -> str:
    """Return the registered attempt key whose ownership becomes canonical."""

    return build_playback_attempt_object_key(
        organization_id=organization_id,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        attempt_id=attempt_id,
    )
