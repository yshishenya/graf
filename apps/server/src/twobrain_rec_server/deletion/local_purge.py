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
LOCAL_PURGE_TERMINAL_STATES = frozenset(
    {
        LocalPurgeTaskState.ACKNOWLEDGED.value,
        LocalPurgeTaskState.FAILED.value,
        LocalPurgeTaskState.UNREACHABLE.value,
        LocalPurgeTaskState.EXPIRED.value,
        LocalPurgeTaskState.LOCAL_EXPIRY_RELIED_UPON.value,
    }
)

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

VERIFIED_LOCAL_PURGE_ACK_REASONS = {
    "local_buffers_purged",
    "local_artifacts_deleted",
    "local_tombstone_verified",
    "cryptographically_unrecoverable",
}


async def create_local_purge_tasks_for_request(
    db: AsyncSession,
    *,
    meeting: Meeting,
    deletion_request_id: UUID,
    local_buffer_expiry_days: int | None = None,
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
    expiry_days = (
        local_buffer_expiry_days
        if local_buffer_expiry_days is not None
        else LOCAL_PURGE_TASK_EXPIRY_DAYS
    )
    expires_at = now + timedelta(days=expiry_days)
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
    expired = await reconcile_expired_local_purge_tasks(
        db,
        workspace_id=workspace_id,
        device_id=device_id,
    )
    if expired:
        await db.commit()
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
    _assert_verified_ack_state(payload)
    task = await db.scalar(
        select(LocalPurgeTaskModel)
        .where(LocalPurgeTaskModel.workspace_id == workspace_id)
        .where(LocalPurgeTaskModel.device_id == device_id)
        .where(LocalPurgeTaskModel.id == task_id)
    )
    if task is None:
        raise ProblemDetail(status=404, code="local_purge_task_not_found", title="Local purge task not found")

    expired = await reconcile_expired_local_purge_tasks(
        db,
        workspace_id=workspace_id,
        meeting_id=task.meeting_id,
        deletion_request_id=task.deletion_request_id,
    )
    if expired:
        await db.commit()
    # Keep every ACK mutation on Meeting → task rows → artifact → report. The
    # expiry pass may have committed, so reacquire the meeting fence before
    # taking the task lock below.
    meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.workspace_id == workspace_id, Meeting.id == task.meeting_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    task = await db.scalar(
        select(LocalPurgeTaskModel)
        .where(LocalPurgeTaskModel.workspace_id == workspace_id)
        .where(LocalPurgeTaskModel.device_id == device_id)
        .where(LocalPurgeTaskModel.id == task_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if task is None:
        raise ProblemDetail(status=404, code="local_purge_task_not_found", title="Local purge task not found")
    current_state = LocalPurgeTaskState(task.state)
    requested_state = payload.state
    if current_state in LOCAL_PURGE_TERMINAL_STATES:
        if current_state == requested_state:
            return _task_schema(task)
        raise ProblemDetail(
            status=409,
            code="local_purge_task_terminal",
            title="Local purge task is already terminal",
        )

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


async def reconcile_expired_local_purge_tasks(
    db: AsyncSession,
    *,
    workspace_id: UUID | None = None,
    meeting_id: UUID | None = None,
    deletion_request_id: UUID | None = None,
    device_id: UUID | None = None,
    limit: int = 100,
    now: datetime | None = None,
) -> int:
    """Advance unreachable pending tasks to a durable expiry state."""
    current = now or datetime.now(UTC)
    candidate_query = (
        select(LocalPurgeTaskModel)
        .where(LocalPurgeTaskModel.state.in_({
            LocalPurgeTaskState.PENDING.value,
            LocalPurgeTaskState.CLAIMED.value,
        }))
        .where(LocalPurgeTaskModel.expires_at <= current)
        .order_by(LocalPurgeTaskModel.expires_at.asc(), LocalPurgeTaskModel.id.asc())
        .limit(limit)
    )
    if workspace_id is not None:
        candidate_query = candidate_query.where(LocalPurgeTaskModel.workspace_id == workspace_id)
    if meeting_id is not None:
        candidate_query = candidate_query.where(LocalPurgeTaskModel.meeting_id == meeting_id)
    if deletion_request_id is not None:
        candidate_query = candidate_query.where(
            LocalPurgeTaskModel.deletion_request_id == deletion_request_id
        )
    if device_id is not None:
        candidate_query = candidate_query.where(LocalPurgeTaskModel.device_id == device_id)
    candidates = (await db.scalars(candidate_query)).all()
    request_keys = sorted(
        {
            (task.workspace_id, task.meeting_id, task.deletion_request_id)
            for task in candidates
        },
        key=lambda key: tuple(str(value) for value in key),
    )
    remaining = max(limit, 0)
    expired_count = 0
    for task_workspace_id, task_meeting_id, task_request_id in request_keys:
        if remaining <= 0:
            break
        # Every local purge mutation uses Meeting → task rows → report. This
        # prevents the maintenance-wide expiry pass from deadlocking an ACK.
        meeting = await db.scalar(
            select(Meeting)
            .where(Meeting.workspace_id == task_workspace_id, Meeting.id == task_meeting_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if meeting is None:
            continue
        task_query = (
            select(LocalPurgeTaskModel)
            .where(
                LocalPurgeTaskModel.workspace_id == task_workspace_id,
                LocalPurgeTaskModel.meeting_id == task_meeting_id,
                LocalPurgeTaskModel.deletion_request_id == task_request_id,
                LocalPurgeTaskModel.state.in_({
                    LocalPurgeTaskState.PENDING.value,
                    LocalPurgeTaskState.CLAIMED.value,
                }),
                LocalPurgeTaskModel.expires_at <= current,
            )
            .order_by(LocalPurgeTaskModel.id.asc())
            .limit(remaining)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        tasks = (await db.scalars(task_query)).all()
        if not tasks:
            continue
        for task in tasks:
            task.state = LocalPurgeTaskState.EXPIRED.value
            task.reason_code = "local_purge_expired"
            task.metadata_json = build_lifecycle_audit_metadata(
                task_type=LocalPurgeTaskType(task.task_type),
                device_state=LocalPurgeTaskState.EXPIRED,
                outcome=LifecycleAuditOutcome.COMPLETED,
                safe_reason=task.reason_code,
            )
            db.add(
                MeetingLifecycleAuditEvent(
                    workspace_id=task.workspace_id,
                    meeting_id=task.meeting_id,
                    deletion_request_id=task.deletion_request_id,
                    actor_user_id=None,
                    device_id=task.device_id,
                    event_type="local_purge_expired",
                    outcome=LifecycleAuditOutcome.COMPLETED.value,
                    safe_reason=task.reason_code,
                    metadata_json=task.metadata_json,
                    created_at=current,
                )
            )
        await _refresh_local_purge_report_state(db, task=tasks[0])
        expired_count += len(tasks)
        remaining -= len(tasks)
    if expired_count:
        await db.flush()
    return expired_count


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


def _assert_verified_ack_state(payload: LocalPurgeAckRequest) -> None:
    if payload.state != LocalPurgeTaskState.ACKNOWLEDGED:
        return
    if payload.reason_code in VERIFIED_LOCAL_PURGE_ACK_REASONS:
        return
    raise ProblemDetail(
        status=422,
        code="local_purge_unverified_ack",
        title="Local purge acknowledgement requires verified local deletion truth",
    )


async def _refresh_local_purge_report_state(db: AsyncSession, *, task: LocalPurgeTaskModel) -> None:
    # The meeting fence must be acquired before SQLAlchemy autoflushes any
    # task/artifact mutation and before the report lock.
    meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.workspace_id == task.workspace_id, Meeting.id == task.meeting_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting is None:
        return
    tasks = (
        await db.scalars(
            select(LocalPurgeTaskModel)
            .where(LocalPurgeTaskModel.workspace_id == task.workspace_id)
            .where(LocalPurgeTaskModel.meeting_id == task.meeting_id)
            .where(LocalPurgeTaskModel.deletion_request_id == task.deletion_request_id)
            .order_by(LocalPurgeTaskModel.id.asc())
            .with_for_update()
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
            .with_for_update()
            .execution_options(populate_existing=True)
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
        .with_for_update()
        .execution_options(populate_existing=True)
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
