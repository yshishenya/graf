from __future__ import annotations

from datetime import datetime
from uuid import UUID

from twobrain_rec_server.api.schemas import (
    ArtifactDeletionState,
    DeletionLifecycleState,
    DeletionVerificationReport,
    LifecycleActivityItem,
    LocalPurgeTask,
)
from twobrain_rec_server.domain.statuses import (
    DeletionArtifactState,
    DeletionControlScope,
    DeletionState,
    LifecycleAuditOutcome,
)

BOUNDED_DELETE_COPY = "Delete this meeting everywhere GRAF controls."

STATE_LABELS = {
    DeletionState.NONE: "Available",
    DeletionState.REQUESTED: "Deletion requested",
    DeletionState.DELETING: "Deleting",
    DeletionState.ACTIVE_PURGE_COMPLETE: "Server purge complete",
    DeletionState.PENDING_BACKUP_EXPIRY: "Waiting for backup expiry",
    DeletionState.COMPLETE: "Deletion complete",
    DeletionState.RETRYABLE_FAILED: "Deletion needs retry",
    DeletionState.TERMINAL_FAILED: "Deletion failed",
    DeletionState.POLICY_BLOCKED: "Deletion blocked by policy",
    DeletionState.POST_EGRESS_LIMIT: "Post-egress limits remain",
    DeletionState.LOCAL_PURGE_UNVERIFIED: "Local purge unverified",
}

DEPENDENCY_ARTIFACT_CLASSES = {
    "mediascribe",
    "langfuse",
    "processing_workflow",
    "upload_temp",
    "diagnostics",
}

SUMMARY_EXCLUDED_ARTIFACT_CLASSES = DEPENDENCY_ARTIFACT_CLASSES | {"backup", "post_egress_copy"}


def lifecycle_state(
    state: DeletionState,
    *,
    reason: str | None = None,
    can_view_report: bool | None = None,
) -> DeletionLifecycleState:
    return DeletionLifecycleState(
        state=state,
        label=STATE_LABELS[state],
        reason=reason,
        can_retry=state == DeletionState.RETRYABLE_FAILED,
        can_view_report=(state != DeletionState.NONE if can_view_report is None else can_view_report),
    )


def artifact_row(
    *,
    artifact_class: str,
    control_scope: DeletionControlScope,
    state: DeletionArtifactState,
    label: str,
    safe_reason: str | None = None,
    completed_at: datetime | None = None,
) -> ArtifactDeletionState:
    return ArtifactDeletionState(
        artifact_class=artifact_class,
        control_scope=control_scope,
        state=state,
        label=label,
        safe_reason=safe_reason,
        completed_at=completed_at,
    )


def retention_policy_activity_row(*, policy_snapshot_id: UUID | None) -> ArtifactDeletionState:
    return artifact_row(
        artifact_class="retention_policy",
        control_scope=DeletionControlScope.CONTROLLED,
        state=DeletionArtifactState.METADATA_RETAINED,
        label="Retention policy snapshot recorded",
        safe_reason="policy_snapshot_recorded" if policy_snapshot_id is not None else "policy_snapshot_missing",
    )


def lifecycle_activity_item(
    *,
    event_id: UUID,
    event_type: str,
    actor_user_id: UUID | None,
    device_id: UUID | None,
    outcome: LifecycleAuditOutcome,
    safe_reason: str | None,
    created_at: datetime,
) -> LifecycleActivityItem:
    return LifecycleActivityItem(
        event_id=event_id,
        event_type=event_type,
        actor_label=_lifecycle_actor_label(actor_user_id=actor_user_id, device_id=device_id),
        outcome=outcome.value,
        safe_reason=_safe_activity_reason(safe_reason),
        created_at=created_at,
    )


def empty_report(
    *,
    meeting_id: UUID,
    request_id: UUID,
    overall_state: DeletionState,
    backup: ArtifactDeletionState,
) -> DeletionVerificationReport:
    return DeletionVerificationReport(
        meeting_id=meeting_id,
        request_id=request_id,
        overall_state=overall_state,
        bounded_copy=BOUNDED_DELETE_COPY,
        artifact_states=[],
        backup=backup,
        local_purge=[],
        dependencies=[],
        post_egress_limits=[],
        activity=[],
    )


def assemble_verification_report(
    *,
    meeting_id: UUID,
    request_id: UUID,
    overall_state: DeletionState,
    artifact_states: list[ArtifactDeletionState],
    local_purge: list[LocalPurgeTask],
    activity: list[LifecycleActivityItem] | None = None,
    generated_at: datetime | None = None,
    bounded_copy: str = BOUNDED_DELETE_COPY,
) -> DeletionVerificationReport:
    backup = _first_artifact_row(artifact_states, "backup") or artifact_row(
        artifact_class="backup",
        control_scope=DeletionControlScope.BACKUP,
        state=DeletionArtifactState.PENDING_EXPIRY,
        label="Backup expiry pending",
    )
    return DeletionVerificationReport(
        meeting_id=meeting_id,
        request_id=request_id,
        overall_state=overall_state,
        bounded_copy=bounded_copy,
        artifact_states=[
            row
            for row in artifact_states
            if row.artifact_class not in SUMMARY_EXCLUDED_ARTIFACT_CLASSES
        ],
        backup=backup,
        local_purge=local_purge,
        dependencies=[
            row
            for row in artifact_states
            if row.artifact_class in DEPENDENCY_ARTIFACT_CLASSES
        ],
        post_egress_limits=[
            row
            for row in artifact_states
            if row.artifact_class == "post_egress_copy"
        ],
        activity=activity or [],
        generated_at=generated_at,
    )


def local_purge_tasks_for_report(tasks: list[LocalPurgeTask]) -> list[LocalPurgeTask]:
    return tasks


def _first_artifact_row(rows: list[ArtifactDeletionState], artifact_class: str) -> ArtifactDeletionState | None:
    return next((row for row in rows if row.artifact_class == artifact_class), None)


def _lifecycle_actor_label(*, actor_user_id: UUID | None, device_id: UUID | None) -> str:
    if device_id is not None and actor_user_id is None:
        return "Desktop device"
    if actor_user_id is not None:
        return "Owner/Admin"
    return "System"


def _safe_activity_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    normalized = reason.lower()
    private_fragments = (
        "/users/",
        "object_key",
        "signed",
        "token",
        "transcript",
        "summary",
        "secret",
        "credential",
    )
    if any(fragment in normalized for fragment in private_fragments):
        return "metadata_only"
    return reason
