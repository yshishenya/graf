from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base

SUPPORT_INCIDENT_GITHUB_REPO = "yshishenya/crisp"


class SupportIncident(Base):
    __tablename__ = "support_incidents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "dedupe_key", name="uq_support_incidents_workspace_dedupe"),
        Index("ix_support_incidents_workspace_status", "workspace_id", "status"),
        Index("ix_support_incidents_github_issue", "github_repo", "github_issue_number"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    reporter_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    device_id: Mapped[UUID] = mapped_column(ForeignKey("registered_devices.id"), nullable=False)
    incident_number: Mapped[str | None] = mapped_column(String(32))
    dedupe_key: Mapped[str] = mapped_column(String(128), nullable=False)
    problem_code: Mapped[str] = mapped_column(String(160), nullable=False)
    failure_category: Mapped[str] = mapped_column(String(120), nullable=False)
    retry_class: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending_github")
    affected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    safe_affected_identities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    latest_safe_report_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    latest_safe_report_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    first_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_duplicate_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    redaction_result: Mapped[str] = mapped_column(String(64), nullable=False)
    github_repo: Mapped[str] = mapped_column(String(240), nullable=False, default=SUPPORT_INCIDENT_GITHUB_REPO)
    github_issue_number: Mapped[int | None] = mapped_column(Integer)
    github_issue_url: Mapped[str | None] = mapped_column(String(500))
    github_issue_state: Mapped[str | None] = mapped_column(String(32))
    github_last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    github_failure_code: Mapped[str | None] = mapped_column(String(120))


class SupportIncidentRateLimitBucket(Base):
    __tablename__ = "support_incident_rate_limit_buckets"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "reporter_user_id",
            "device_id",
            "dedupe_key",
            name="uq_support_incident_rate_limit_scope",
        ),
        Index("ix_support_incident_rate_limit_blocked_until", "blocked_until"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    reporter_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    device_id: Mapped[UUID] = mapped_column(ForeignKey("registered_devices.id"), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(128), nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
