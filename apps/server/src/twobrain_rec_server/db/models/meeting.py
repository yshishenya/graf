from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "created_by_user_id",
            "local_recording_id",
            name="uq_meetings_workspace_user_local_recording",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    device_id: Mapped[UUID] = mapped_column(ForeignKey("registered_devices.id"), nullable=False)
    local_recording_id: Mapped[str] = mapped_column(String(240), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    title_source: Mapped[str] = mapped_column(
        String(64), nullable=False, default="legacy_unknown"
    )
    title_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    create_request_fingerprint_sha256: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recording_display_timezone_offset_minutes: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="draft")
    processing_status: Mapped[str] = mapped_column(String(64), default="not_submitted")
    visibility: Mapped[str] = mapped_column(String(64), default="owner_only")
    share_policy_state: Mapped[str] = mapped_column(String(64), default="not_available")
    download_policy_state: Mapped[str] = mapped_column(String(64), default="not_available")
    deletion_state: Mapped[str] = mapped_column(String(64), default="none")
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retention_delete_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retention_policy_state: Mapped[str] = mapped_column(String(64), default="not_configured")
    current_outcome_set_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "meeting_outcome_sets.id",
            name="fk_meetings_current_outcome_set",
            use_alter=True,
        )
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProcessingPlaceholder(Base):
    __tablename__ = "processing_placeholders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="not_submitted")
    meeting_status: Mapped[str] = mapped_column(String(64), default="draft")
    workflow_id: Mapped[str | None] = mapped_column(String(240))
    mediascribe_job_id: Mapped[str | None] = mapped_column(String(240))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
