from uuid import uuid4

from twobrain_rec_server.ingest.access_policy import default_access_policy


def test_default_access_policy_preserves_future_share_download_placeholders() -> None:
    meeting_id = uuid4()
    workspace_id = uuid4()
    policy = default_access_policy(meeting_id, workspace_id)
    assert policy.visibility == "owner_only"
    assert policy.admin_eligible is False
    assert policy.share_available is False
    assert policy.share_denial_reason == "share_not_implemented"
    assert policy.download_available is False
    assert policy.download_denial_reason == "download_not_implemented"
    assert policy.export_available is False
    assert policy.export_denial_reason == "export_not_implemented"
    assert policy.deletion_state == "not_requested"


def test_default_access_policy_can_represent_admin_and_deletion_placeholders() -> None:
    meeting_id = uuid4()
    workspace_id = uuid4()
    owner_user_id = uuid4()

    policy = default_access_policy(
        meeting_id=meeting_id,
        workspace_id=workspace_id,
        owner_user_id=owner_user_id,
        admin_eligible=True,
        deletion_state="pending_owner_confirmation",
    )

    assert policy.owner_user_id == owner_user_id
    assert policy.admin_eligible is True
    assert policy.deletion_state == "pending_owner_confirmation"
    assert policy.deletion_denial_reason is None
