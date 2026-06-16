from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class MeetingDeletionRequest(Base):
    __tablename__ = "meeting_deletion_requests"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    requested_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    requested_by_device_id: Mapped[UUID | None] = mapped_column(ForeignKey("registered_devices.id"))
    request_source: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmation_boundary: Mapped[str] = mapped_column(String(240), nullable=False)
    state: Mapped[str] = mapped_column(String(64), default="requested")
    policy_snapshot_id: Mapped[UUID | None] = mapped_column(ForeignKey("retention_policy_snapshots.id"))
    failure_reason: Mapped[str | None] = mapped_column(String(240))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MeetingDeletionArtifactState(Base):
    __tablename__ = "meeting_deletion_artifact_states"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    deletion_request_id: Mapped[UUID] = mapped_column(ForeignKey("meeting_deletion_requests.id"), nullable=False)
    artifact_class: Mapped[str] = mapped_column(String(64), nullable=False)
    control_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(64), default="not_started")
    safe_reason: Mapped[str | None] = mapped_column(String(240))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MeetingDeletionReport(Base):
    __tablename__ = "meeting_deletion_reports"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    deletion_request_id: Mapped[UUID] = mapped_column(ForeignKey("meeting_deletion_requests.id"), nullable=False)
    overall_state: Mapped[str] = mapped_column(String(64), default="requested")
    summary_label: Mapped[str] = mapped_column(String(160), nullable=False)
    bounded_copy: Mapped[str] = mapped_column(String(500), nullable=False)
    artifact_summary_json: Mapped[list] = mapped_column(JSON, default=list)
    backup_state: Mapped[str] = mapped_column(String(64), default="not_applicable")
    local_purge_state: Mapped[str] = mapped_column(String(64), default="not_applicable")
    external_dependency_state: Mapped[str] = mapped_column(String(64), default="not_applicable")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RetentionPolicySnapshot(Base):
    __tablename__ = "retention_policy_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    policy_source: Mapped[str] = mapped_column(String(64), nullable=False)
    meeting_delete_after_days: Mapped[int | None] = mapped_column(Integer)
    backup_expiry_days: Mapped[int | None] = mapped_column(Integer)
    local_buffer_expiry_days: Mapped[int | None] = mapped_column(Integer)
    unsafe_reason: Mapped[str | None] = mapped_column(String(240))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LocalPurgeTask(Base):
    __tablename__ = "local_purge_tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    deletion_request_id: Mapped[UUID] = mapped_column(ForeignKey("meeting_deletion_requests.id"), nullable=False)
    device_id: Mapped[UUID] = mapped_column(ForeignKey("registered_devices.id"), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(64), default="pending")
    reason_code: Mapped[str | None] = mapped_column(String(120))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MeetingLifecycleAuditEvent(Base):
    __tablename__ = "meeting_lifecycle_audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID | None] = mapped_column(ForeignKey("meetings.id"))
    deletion_request_id: Mapped[UUID | None] = mapped_column(ForeignKey("meeting_deletion_requests.id"))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    device_id: Mapped[UUID | None] = mapped_column(ForeignKey("registered_devices.id"))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    safe_reason: Mapped[str | None] = mapped_column(String(240))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
