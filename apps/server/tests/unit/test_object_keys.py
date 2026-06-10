from uuid import UUID

from twobrain_rec_server.domain.statuses import TrackRole
from twobrain_rec_server.storage.object_keys import build_track_object_key


def test_object_key_contains_tenant_workspace_meeting_and_session_scope() -> None:
    key = build_track_object_key(
        organization_id=UUID("10000000-0000-0000-0000-000000000001"),
        workspace_id=UUID("20000000-0000-0000-0000-000000000001"),
        meeting_id=UUID("30000000-0000-0000-0000-000000000001"),
        upload_session_id=UUID("40000000-0000-0000-0000-000000000001"),
        track_role=TrackRole.MICROPHONE,
        part_number=2,
    )
    assert "organizations/10000000-0000-0000-0000-000000000001" in key
    assert "workspaces/20000000-0000-0000-0000-000000000001" in key
    assert "sessions/40000000-0000-0000-0000-000000000001" in key
    assert key.endswith("/tracks/microphone/parts/00000002")
