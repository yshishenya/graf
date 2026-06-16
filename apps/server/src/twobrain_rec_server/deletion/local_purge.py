from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import LocalPurgeAckRequest, LocalPurgeTask
from twobrain_rec_server.db.models import (
    LocalPurgeTask as LocalPurgeTaskModel,
)
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingDeletionArtifactState,
    MeetingDeletionReport,
    MeetingLifecycleAuditEvent,
    RegisteredDevice,
)
from twobrain_rec_server.deletion.audit import build_lifecycle_audit_metadata
from twobrain_rec_server.domain.statuses import (
    DeletionArtifactClass,
    DeletionArtifactState,
    DeletionControlScope,
    LifecycleAuditOutcome,
    LocalPurgeTaskState,
    LocalPurgeTaskType,
)

LOCAL_PURGE_TASK_EXPIRY_DAYS = 7

PRIVATE_ACK_VALUE_FRAGMENTS = (
    "/users/",
    "\\users\\",
    "application support",
    ".m4a",
    ".mp3",
    ".wav",
    "object_key",
    "private",
    "screenshot",
    "secret",
    "sha256",
    "signed",
    "summary",
    "token",
    "transcript",
)


async def create_local_purge_tasks_for_request(
    db: AsyncSession,
    *,
    meeting: Meeting,
    deletion_request_id: UUID,
) -> list[LocalPurgeTaskModel]:
    devices = (
        await db.scalars(
            select(RegisteredDevice)
            .where(RegisteredDevice.workspace_id == meeting.workspace_id)
            .where(RegisteredDevice.status == "active")
            .where(RegisteredDevice.registration_state == "approved")
            .order_by(RegisteredDevice.created_at.asc())
        )
    ).all()
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=LOCAL_PURGE_TASK_EXPIRY_DAYS)
    tasks = [
        LocalPurgeTaskModel(
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            deletion_request_id=deletion_request_id,
            device_id=device.id,
            task_type=LocalPurgeTaskType.PURGE_LOCAL_BUFFERS.value,
            state=LocalPurgeTaskState.PENDING.value,
            reason_code="delete_requested",
            expires_at=expires_at,
            metadata_json=build_lifecycle_audit_metadata(
                task_type=LocalPurgeTaskType.PURGE_LOCAL_BUFFERS,
                device_state=LocalPurgeTaskState.PENDING,
                outcome=LifecycleAuditOutcome.ACCEPTED,
                safe_reason="delete_requested",
            ),
        )
        for device in devices
    ]
    db.add_all(tasks)
    await db.flush()
    return tasks


async def list_local_purge_tasks(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    device_id: UUID,
) -> list[LocalPurgeTask]:
    tasks = (
        await db.scalars(
            select(LocalPurgeTaskModel)
            .where(LocalPurgeTaskModel.workspace_id == workspace_id)
            .where(LocalPurgeTaskModel.device_id == device_id)
            .order_by(LocalPurgeTaskModel.created_at.asc())
        )
    ).all()
    return [_task_schema(task) for task in tasks]


async def acknowledge_local_purge_task(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    device_id: UUID,
    task_id: UUID,
    payload: LocalPurgeAckRequest,
) -> LocalPurgeTask:
    _assert_metadata_only_ack(payload)
    task = await db.scalar(
        select(LocalPurgeTaskModel)
        .where(LocalPurgeTaskModel.workspace_id == workspace_id)
        .where(LocalPurgeTaskModel.device_id == device_id)
        .where(LocalPurgeTaskModel.id == task_id)
    )
    if task is None:
        raise ProblemDetail(status=404, code="local_purge_task_not_found", title="Local purge task not found")

    now = datetime.now(UTC)
    task.state = payload.state.value
    task.reason_code = payload.reason_code or payload.state.value
    task.acknowledged_at = payload.completed_at or now
    task.metadata_json = build_lifecycle_audit_metadata(
        task_type=LocalPurgeTaskType(task.task_type),
        device_state=LocalPurgeTaskState(task.state),
        outcome=_audit_outcome_for_task_state(LocalPurgeTaskState(task.state)),
        safe_reason=task.reason_code,
    )
    db.add(
        MeetingLifecycleAuditEvent(
            workspace_id=workspace_id,
            meeting_id=task.meeting_id,
            deletion_request_id=task.deletion_request_id,
            actor_user_id=None,
            device_id=device_id,
            event_type="local_purge_acknowledged",
            outcome=_audit_outcome_for_task_state(LocalPurgeTaskState(task.state)).value,
            safe_reason=task.reason_code,
            metadata_json=task.metadata_json,
            created_at=now,
        )
    )
    await _refresh_local_purge_report_state(db, task=task)
    await db.flush()
    return _task_schema(task)


def _assert_metadata_only_ack(payload: LocalPurgeAckRequest) -> None:
    values = [payload.reason_code, payload.client_version]
    for value in values:
        if value is None:
            continue
        normalized = value.lower()
        if any(fragment in normalized for fragment in PRIVATE_ACK_VALUE_FRAGMENTS):
            raise ProblemDetail(
                status=422,
                code="local_purge_private_payload",
                title="Local purge acknowledgement must be metadata-only",
            )


async def _refresh_local_purge_report_state(db: AsyncSession, *, task: LocalPurgeTaskModel) -> None:
    tasks = (
        await db.scalars(
            select(LocalPurgeTaskModel)
            .where(LocalPurgeTaskModel.workspace_id == task.workspace_id)
            .where(LocalPurgeTaskModel.meeting_id == task.meeting_id)
            .where(LocalPurgeTaskModel.deletion_request_id == task.deletion_request_id)
        )
    ).all()
    aggregate_state = _aggregate_local_purge_state(tasks)
    safe_reason = _safe_reason_for_aggregate_state(aggregate_state)
    artifact = await db.scalar(
        select(MeetingDeletionArtifactState)
        .where(MeetingDeletionArtifactState.workspace_id == task.workspace_id)
        .where(MeetingDeletionArtifactState.meeting_id == task.meeting_id)
        .where(MeetingDeletionArtifactState.deletion_request_id == task.deletion_request_id)
        .where(MeetingDeletionArtifactState.artifact_class == DeletionArtifactClass.LOCAL_DESKTOP_BUFFER.value)
    )
    if artifact is not None:
        artifact.state = aggregate_state.value
        artifact.safe_reason = safe_reason
        artifact.control_scope = DeletionControlScope.LOCAL_DEVICE.value
        artifact.metadata_json = build_lifecycle_audit_metadata(
            artifact_class=DeletionArtifactClass.LOCAL_DESKTOP_BUFFER,
            control_scope=DeletionControlScope.LOCAL_DEVICE,
            state=aggregate_state,
            safe_reason=safe_reason,
        )
        artifact.updated_at = datetime.now(UTC)
    report = await db.scalar(
        select(MeetingDeletionReport)
        .where(MeetingDeletionReport.workspace_id == task.workspace_id)
        .where(MeetingDeletionReport.meeting_id == task.meeting_id)
        .where(MeetingDeletionReport.deletion_request_id == task.deletion_request_id)
    )
    if report is not None:
        report.local_purge_state = aggregate_state.value
        report.updated_at = datetime.now(UTC)


def _aggregate_local_purge_state(tasks: list[LocalPurgeTaskModel]) -> DeletionArtifactState:
    states = {task.state for task in tasks}
    if not states:
        return DeletionArtifactState.NOT_APPLICABLE
    if LocalPurgeTaskState.FAILED.value in states:
        return DeletionArtifactState.RETRYABLE_FAILED
    if LocalPurgeTaskState.UNREACHABLE.value in states:
        return DeletionArtifactState.LOCAL_UNREACHABLE
    if states & {LocalPurgeTaskState.PENDING.value, LocalPurgeTaskState.CLAIMED.value}:
        return DeletionArtifactState.LOCAL_PENDING
    if LocalPurgeTaskState.LOCAL_EXPIRY_RELIED_UPON.value in states or LocalPurgeTaskState.EXPIRED.value in states:
        return DeletionArtifactState.LOCAL_EXPIRY_RELIED_UPON
    if states <= {LocalPurgeTaskState.ACKNOWLEDGED.value}:
        return DeletionArtifactState.LOCAL_ACKNOWLEDGED
    return DeletionArtifactState.LOCAL_PENDING


def _safe_reason_for_aggregate_state(state: DeletionArtifactState) -> str:
    return {
        DeletionArtifactState.LOCAL_ACKNOWLEDGED: "Local purge acknowledged by desktop devices",
        DeletionArtifactState.RETRYABLE_FAILED: "Local purge acknowledgement failed",
        DeletionArtifactState.LOCAL_EXPIRY_RELIED_UPON: "Local buffer expiry relied upon",
        DeletionArtifactState.LOCAL_UNREACHABLE: "Local desktop device unreachable",
        DeletionArtifactState.LOCAL_PENDING: "Local purge pending",
    }.get(state, "Local purge not applicable")


def _audit_outcome_for_task_state(state: LocalPurgeTaskState) -> LifecycleAuditOutcome:
    if state == LocalPurgeTaskState.FAILED:
        return LifecycleAuditOutcome.FAILED
    return LifecycleAuditOutcome.COMPLETED


def _task_schema(task: LocalPurgeTaskModel) -> LocalPurgeTask:
    return LocalPurgeTask(
        task_id=task.id,
        meeting_id=task.meeting_id,
        task_type=LocalPurgeTaskType(task.task_type),
        state=LocalPurgeTaskState(task.state),
        safe_reason=task.reason_code,
        expires_at=task.expires_at,
        ack_url=f"/api/v1/desktop/local-purge-tasks/{task.id}/ack",
    )
