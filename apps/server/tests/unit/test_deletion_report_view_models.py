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

    assert "GRAF controls" in payload
    assert "object_key" not in payload
    assert "transcript text" not in payload


def test_verification_report_partitions_dependencies_post_egress_and_summary_rows() -> None:
    backup = report.artifact_row(
        artifact_class="backup",
        control_scope=DeletionControlScope.BACKUP,
        state=DeletionArtifactState.PENDING_EXPIRY,
        label="Backup expiry pending",
        safe_reason="backup_expiry_days:30",
    )
    rows = [
        report.artifact_row(
            artifact_class="audio_object",
            control_scope=DeletionControlScope.CONTROLLED,
            state=DeletionArtifactState.PURGE_REQUESTED,
            label="Server audio purge requested",
        ),
        backup,
        report.artifact_row(
            artifact_class="mediascribe",
            control_scope=DeletionControlScope.EXTERNAL,
            state=DeletionArtifactState.UNKNOWN,
            label="External deletion support is not confirmed",
        ),
        report.artifact_row(
            artifact_class="langfuse",
            control_scope=DeletionControlScope.EXTERNAL,
            state=DeletionArtifactState.METADATA_RETAINED,
            label="Langfuse metadata retained",
        ),
        report.artifact_row(
            artifact_class="post_egress_copy",
            control_scope=DeletionControlScope.POST_EGRESS,
            state=DeletionArtifactState.OUTSIDE_2BRAIN_CONTROL,
            label="Delivered copies are outside GRAF control",
        ),
    ]

    payload = report.assemble_verification_report(
        meeting_id=uuid4(),
        request_id=uuid4(),
        overall_state=DeletionState.DELETING,
        artifact_states=rows,
        local_purge=[],
    )

    assert [row.artifact_class for row in payload.artifact_states] == ["audio_object"]
    assert {row.artifact_class for row in payload.dependencies} == {"mediascribe", "langfuse"}
    assert payload.backup.safe_reason == "backup_expiry_days:30"
    assert payload.post_egress_limits[0].control_scope == DeletionControlScope.POST_EGRESS
    assert payload.post_egress_limits[0].state == DeletionArtifactState.OUTSIDE_2BRAIN_CONTROL
