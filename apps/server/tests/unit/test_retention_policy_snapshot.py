from __future__ import annotations

from tests.fakes.auth_contexts import WORKSPACE_ID
from twobrain_rec_server.config import Settings
from twobrain_rec_server.deletion.policy import (
    RETENTION_POLICY_UNSAFE_REASON,
    build_retention_policy_snapshot,
    retention_policy_allows_actions,
)
from twobrain_rec_server.domain.statuses import RetentionPolicySource


def test_deployment_default_retention_policy_snapshot_is_safe_metadata_only() -> None:
    snapshot = build_retention_policy_snapshot(
        Settings(
            retention_meeting_delete_after_days=30,
            retention_backup_expiry_days=7,
            retention_local_buffer_expiry_days=3,
        ),
        workspace_id=WORKSPACE_ID,
    )

    assert snapshot.workspace_id == WORKSPACE_ID
    assert snapshot.policy_source == RetentionPolicySource.DEPLOYMENT_DEFAULT.value
    assert snapshot.meeting_delete_after_days == 30
    assert snapshot.backup_expiry_days == 7
    assert snapshot.local_buffer_expiry_days == 3
    assert snapshot.unsafe_reason is None
    assert retention_policy_allows_actions(snapshot) is True
    assert snapshot.metadata_json == {
        "policy_source": "deployment_default",
        "outcome": "accepted",
        "safe_reason": "policy_active",
        "backup_expiry_days": 7,
    }


def test_missing_retention_policy_snapshot_fails_closed_without_private_metadata() -> None:
    snapshot = build_retention_policy_snapshot(
        Settings(retention_meeting_delete_after_days=None),
        workspace_id=WORKSPACE_ID,
    )

    assert snapshot.policy_source == RetentionPolicySource.DEPLOYMENT_DEFAULT.value
    assert snapshot.meeting_delete_after_days is None
    assert snapshot.unsafe_reason == RETENTION_POLICY_UNSAFE_REASON
    assert retention_policy_allows_actions(snapshot) is False
    assert snapshot.metadata_json == {
        "policy_source": "deployment_default",
        "outcome": "blocked",
        "safe_reason": RETENTION_POLICY_UNSAFE_REASON,
        "backup_expiry_days": 30,
    }
