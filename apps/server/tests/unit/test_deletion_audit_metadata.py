from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from twobrain_rec_server.deletion.audit import build_lifecycle_audit_metadata
from twobrain_rec_server.deletion.report import lifecycle_activity_item
from twobrain_rec_server.domain.statuses import (
    DeletionArtifactClass,
    DeletionArtifactState,
    DeletionControlScope,
    LifecycleAuditOutcome,
)


def test_lifecycle_audit_metadata_keeps_only_safe_lifecycle_fields() -> None:
    metadata = build_lifecycle_audit_metadata(
        state=DeletionArtifactState.PURGE_REQUESTED,
        artifact_class=DeletionArtifactClass.AUDIO_OBJECT,
        control_scope=DeletionControlScope.CONTROLLED,
        outcome=LifecycleAuditOutcome.ACCEPTED,
        attempt_count=1,
        safe_reason="delete_requested",
    )

    assert metadata == {
        "state": "purge_requested",
        "artifact_class": "audio_object",
        "control_scope": "controlled",
        "outcome": "accepted",
        "attempt_count": 1,
        "safe_reason": "delete_requested",
    }


@pytest.mark.parametrize(
    "private_payload",
    [
        {"object_key": "workspaces/private/audio.wav"},
        {"signed_url": "https://storage.example.test/private?signature=secret"},
        {"local_path": "/Users/person/private.wav"},
        {"transcript": "private transcript text"},
        {"metadata": {"token": "secret"}},
    ],
)
def test_lifecycle_audit_metadata_rejects_private_or_secret_payloads(private_payload: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="metadata-only"):
        build_lifecycle_audit_metadata(**private_payload)


def test_lifecycle_activity_item_is_metadata_only_and_actor_scoped() -> None:
    item = lifecycle_activity_item(
        event_id=uuid4(),
        event_type="local_purge_acknowledged",
        actor_user_id=None,
        device_id=uuid4(),
        outcome=LifecycleAuditOutcome.COMPLETED,
        safe_reason="local_buffers_purged",
        created_at=datetime.now(UTC),
    )

    assert item.actor_label == "Desktop device"
    assert item.outcome == "completed"
    assert item.safe_reason == "local_buffers_purged"
