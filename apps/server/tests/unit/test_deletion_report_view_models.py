from __future__ import annotations

from uuid import uuid4

from twobrain_rec_server.deletion import report
from twobrain_rec_server.domain.statuses import (
    DeletionArtifactState,
    DeletionControlScope,
    DeletionState,
)


def test_lifecycle_state_maps_retry_and_report_visibility() -> None:
    state = report.lifecycle_state(DeletionState.RETRYABLE_FAILED, reason="safe_retry")

    assert state.state == DeletionState.RETRYABLE_FAILED
    assert state.can_retry is True
    assert state.can_view_report is True
    assert state.reason == "safe_retry"


def test_empty_report_uses_bounded_copy_and_metadata_only_rows() -> None:
    backup = report.artifact_row(
        artifact_class="backup",
        control_scope=DeletionControlScope.BACKUP,
        state=DeletionArtifactState.PENDING_EXPIRY,
        label="Backup expiry pending",
    )

    payload = report.empty_report(
        meeting_id=uuid4(),
        request_id=uuid4(),
        overall_state=DeletionState.DELETING,
        backup=backup,
    ).model_dump_json()

    assert "2brain Rec controls" in payload
    assert "object_key" not in payload
    assert "transcript text" not in payload
