from uuid import uuid4

from twobrain_rec_server.ingest.access_policy import default_access_policy


def test_default_access_policy_preserves_future_share_download_placeholders() -> None:
    meeting_id = uuid4()
    workspace_id = uuid4()
    policy = default_access_policy(meeting_id, workspace_id)
    assert policy.visibility == "owner_only"
    assert policy.share_available is False
    assert policy.download_available is False
