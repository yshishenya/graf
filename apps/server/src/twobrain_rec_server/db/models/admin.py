from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, BigInteger, Date, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class WorkspaceInvitation(Base):
    __tablename__ = "workspace_invitations"
    __table_args__ = (
        Index(
            "uq_workspace_invitations_active_pending_target",
            "workspace_id",
            "target_contact",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_workspace_invitations_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    target_contact: Mapped[str] = mapped_column(String(240), nullable=False)
    target_provider: Mapped[str | None] = mapped_column(String(64))
    invited_role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="admin")
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    completed_membership_id: Mapped[str | None] = mapped_column(String(160))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(String(240))
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class WorkspaceQuotaPolicy(Base):
    __tablename__ = "workspace_quota_policies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), unique=True, nullable=False)
    recording_minutes_limit: Mapped[int | None] = mapped_column(Integer)
    storage_bytes_limit: Mapped[int | None] = mapped_column(BigInteger)
    processing_jobs_limit: Mapped[int | None] = mapped_column(Integer)
    policy_source: Mapped[str] = mapped_column(String(80), nullable=False, default="display_only")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="not_configured")
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkspaceUsageDaily(Base):
    __tablename__ = "workspace_usage_daily"

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    usage_date: Mapped[date] = mapped_column(Date, primary_key=True)
    recording_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    processing_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recording_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deleted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    freshness_state: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    source_cutoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserUsageDaily(Base):
    __tablename__ = "user_usage_daily"

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), primary_key=True)
    usage_date: Mapped[date] = mapped_column(Date, primary_key=True)
    recording_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    processing_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    freshness_state: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    source_cutoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdminAuditEvent(Base):
    __tablename__ = "admin_audit_events"
    __table_args__ = (
        Index("ix_admin_audit_events_workspace_created", "workspace_id", "created_at"),
        Index("ix_admin_audit_events_workspace_action", "workspace_id", "action"),
        Index("ix_admin_audit_events_workspace_target", "workspace_id", "target_kind", "target_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    actor_role: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(160))
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(120))
    source_table: Mapped[str | None] = mapped_column(String(120))
    source_event_id: Mapped[str | None] = mapped_column(String(160))
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
