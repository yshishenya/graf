from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from twobrain_rec_server.api.schemas import (
    ArtifactDeletionState,
    CreateDeletionRequest,
    DeletionVerificationReport,
    LocalPurgeAckRequest,
    LocalPurgeTask,
)
from twobrain_rec_server.db.models import Meeting
from twobrain_rec_server.deletion.service import _initial_artifact_states
from twobrain_rec_server.domain.statuses import (
    DeletionArtifactClass,
    DeletionArtifactState,
    DeletionControlScope,
    DeletionState,
    LocalPurgeTaskState,
    LocalPurgeTaskType,
)


def test_deletion_request_requires_bounded_confirmation_copy() -> None:
    request = CreateDeletionRequest(
        confirmation_boundary="Delete this meeting everywhere GRAF controls."
    )

    assert request.confirmation_boundary == "Delete this meeting everywhere GRAF controls."

    with pytest.raises(ValidationError):
        CreateDeletionRequest(confirmation_boundary="Delete this meeting everywhere.")


def test_deletion_report_schema_serializes_metadata_only_states() -> None:
    meeting_id = uuid4()
    request_id = uuid4()
    task_id = uuid4()
    report = DeletionVerificationReport(
        meeting_id=meeting_id,
        request_id=request_id,
        overall_state=DeletionState.DELETING,
        bounded_copy="Delete this meeting everywhere GRAF controls.",
        artifact_states=[
            ArtifactDeletionState(
                artifact_class="audio_object",
                control_scope=DeletionControlScope.CONTROLLED,
                state=DeletionArtifactState.PURGE_REQUESTED,
                label="Server audio purge requested",
            )
        ],
        backup=ArtifactDeletionState(
            artifact_class="backup",
            control_scope=DeletionControlScope.BACKUP,
            state=DeletionArtifactState.PENDING_EXPIRY,
            label="Backup expiry pending",
        ),
        local_purge=[
            LocalPurgeTask(
                task_id=task_id,
                meeting_id=meeting_id,
                task_type=LocalPurgeTaskType.PURGE_LOCAL_BUFFERS,
                state=LocalPurgeTaskState.PENDING,
                safe_reason="delete_requested",
                expires_at="2026-06-17T00:00:00Z",
            )
        ],
        dependencies=[
            ArtifactDeletionState(
                artifact_class="mediascribe",
                control_scope=DeletionControlScope.EXTERNAL,
                state=DeletionArtifactState.UNKNOWN,
                label="External deletion support unknown",
            )
        ],
        post_egress_limits=[
            ArtifactDeletionState(
                artifact_class="post_egress_copy",
                control_scope=DeletionControlScope.POST_EGRESS,
                state=DeletionArtifactState.OUTSIDE_2BRAIN_CONTROL,
                label="Outside GRAF control after delivery",
            )
        ],
    )

    payload = report.model_dump_json().lower()

    assert "graf controls" in payload
    for forbidden in [
        "object_key",
        "signed_url",
        "bearer ",
        "credential",
        "transcript text",
        "/users/",
        "external_job_id",
    ]:
        assert forbidden not in payload


def test_local_purge_ack_rejects_private_proof_payloads() -> None:
    valid = LocalPurgeAckRequest(state=LocalPurgeTaskState.ACKNOWLEDGED, reason_code="purged")

    assert valid.state == LocalPurgeTaskState.ACKNOWLEDGED

    with pytest.raises(ValidationError):
        LocalPurgeAckRequest(
            state=LocalPurgeTaskState.ACKNOWLEDGED,
            reason_code="purged",
            local_path="/Users/person/Library/Application Support/2brain/private.wav",
        )


def test_deletion_report_names_retained_plaintext_observability_without_failed_purge() -> None:
    meeting = Meeting(
        id=uuid4(),
        workspace_id=uuid4(),
        created_by_user_id=uuid4(),
        device_id=uuid4(),
        local_recording_id="synthetic-retained-observability",
        duration_seconds=0,
    )
    rows = _initial_artifact_states(meeting, uuid4())
    by_class = {row.artifact_class: row for row in rows}

    for artifact_class in (
        DeletionArtifactClass.GENERATION_CALL,
        DeletionArtifactClass.LANGFUSE,
        DeletionArtifactClass.TEMPORAL_HISTORY,
    ):
        row = by_class[artifact_class.value]
        assert row.state == DeletionArtifactState.OBSERVABILITY_RETAINED.value
        assert "plaintext" in row.safe_reason.casefold()
        assert "failed" not in row.safe_reason.casefold()

    assert "Generation Call" in by_class["generation_call"].safe_reason
    assert "Langfuse" in by_class["langfuse"].safe_reason
    assert "Temporal History" in by_class["temporal_history"].safe_reason
    assert "synthetic private meeting content" not in " ".join(row.safe_reason for row in rows)


def test_pending_generation_without_an_outcome_does_not_claim_a_summary_purge() -> None:
    meeting = Meeting(
        id=uuid4(),
        workspace_id=uuid4(),
        created_by_user_id=uuid4(),
        device_id=uuid4(),
        local_recording_id="synthetic-pending-generation",
        duration_seconds=0,
    )
    rows = _initial_artifact_states(
        meeting,
        uuid4(),
        outcomes_materialized=False,
        materialized_artifact_classes={DeletionArtifactClass.OUTCOME_ATTEMPT},
    )
    by_class = {row.artifact_class: row for row in rows}

    assert by_class["notes_summary"].state == DeletionArtifactState.NOT_APPLICABLE.value
    assert by_class["outcome_attempt"].state == DeletionArtifactState.METADATA_RETAINED.value
