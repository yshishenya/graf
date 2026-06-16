from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from twobrain_rec_server.deletion.local_purge import _aggregate_local_purge_state
from twobrain_rec_server.deletion.report import artifact_row, assemble_verification_report
from twobrain_rec_server.domain.statuses import (
    DeletionArtifactState,
    DeletionControlScope,
    DeletionState,
    LocalPurgeTaskState,
)


def test_dependency_report_groups_external_workflow_temp_and_diagnostics_truth() -> None:
    report = assemble_verification_report(
        meeting_id=uuid4(),
        request_id=uuid4(),
        overall_state=DeletionState.DELETING,
        artifact_states=[
            artifact_row(
                artifact_class="audio_object",
                control_scope=DeletionControlScope.CONTROLLED,
                state=DeletionArtifactState.PURGE_REQUESTED,
                label="Server audio purge requested",
            ),
            artifact_row(
                artifact_class="mediascribe",
                control_scope=DeletionControlScope.EXTERNAL,
                state=DeletionArtifactState.DELETE_NOT_SUPPORTED,
                label="MediaScribe deletion is not confirmed",
                safe_reason="dependency_delete_not_supported",
            ),
            artifact_row(
                artifact_class="langfuse",
                control_scope=DeletionControlScope.EXTERNAL,
                state=DeletionArtifactState.METADATA_RETAINED,
                label="Langfuse metadata-only trace retained",
                safe_reason="metadata_only",
            ),
            artifact_row(
                artifact_class="processing_workflow",
                control_scope=DeletionControlScope.CONTROLLED,
                state=DeletionArtifactState.METADATA_RETAINED,
                label="Workflow metadata retained without content",
                safe_reason="workflow_metadata_only",
            ),
            artifact_row(
                artifact_class="upload_temp",
                control_scope=DeletionControlScope.CONTROLLED,
                state=DeletionArtifactState.PURGE_REQUESTED,
                label="Temporary upload purge requested",
                safe_reason="temp_purge_requested",
            ),
            artifact_row(
                artifact_class="diagnostics",
                control_scope=DeletionControlScope.CONTROLLED,
                state=DeletionArtifactState.METADATA_RETAINED,
                label="Diagnostics metadata retained without content",
                safe_reason="diagnostics_metadata_only",
            ),
        ],
        local_purge=[],
    )

    assert {row.artifact_class for row in report.dependencies} == {
        "mediascribe",
        "langfuse",
        "processing_workflow",
        "upload_temp",
        "diagnostics",
    }
    assert {row.artifact_class for row in report.artifact_states} == {"audio_object"}


def test_local_purge_aggregate_prioritizes_unfinished_or_failed_device_truth() -> None:
    assert _aggregate_local_purge_state([_task(LocalPurgeTaskState.FAILED)]) == DeletionArtifactState.RETRYABLE_FAILED
    assert (
        _aggregate_local_purge_state([_task(LocalPurgeTaskState.ACKNOWLEDGED), _task(LocalPurgeTaskState.UNREACHABLE)])
        == DeletionArtifactState.LOCAL_UNREACHABLE
    )
    assert (
        _aggregate_local_purge_state(
            [_task(LocalPurgeTaskState.ACKNOWLEDGED), _task(LocalPurgeTaskState.LOCAL_EXPIRY_RELIED_UPON), _task(LocalPurgeTaskState.PENDING)]
        )
        == DeletionArtifactState.LOCAL_PENDING
    )
    assert (
        _aggregate_local_purge_state([_task(LocalPurgeTaskState.ACKNOWLEDGED), _task(LocalPurgeTaskState.LOCAL_EXPIRY_RELIED_UPON)])
        == DeletionArtifactState.LOCAL_EXPIRY_RELIED_UPON
    )
    assert _aggregate_local_purge_state([_task(LocalPurgeTaskState.ACKNOWLEDGED)]) == DeletionArtifactState.LOCAL_ACKNOWLEDGED


def _task(state: LocalPurgeTaskState) -> SimpleNamespace:
    return SimpleNamespace(state=state.value)
