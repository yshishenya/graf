"""Explicit owner automation; defaults never authorize a disclosure."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class SummarySharingPreference(Base):
    __tablename__ = "summary_sharing_preferences"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "owner_user_id", name="uq_summary_sharing_preferences_owner"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    ask_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    paused: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    auto_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    budget_window_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    budget_batches: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SummaryAutoSendRule(Base):
    __tablename__ = "summary_auto_send_rules"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "owner_user_id",
            "scope",
            "target_key",
            name="uq_summary_auto_send_rule_target",
        ),
        Index("ix_summary_auto_send_rules_active", "workspace_id", "owner_user_id", "enabled"),
        Index(
            "ix_summary_auto_send_rules_canonical",
            "workspace_id",
            "canonical_target_key",
            "enabled",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    distributor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_identities.id"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    target_key: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_target_key: Mapped[str] = mapped_column(String(100), nullable=False)
    meeting_id: Mapped[UUID | None] = mapped_column(ForeignKey("meetings.id"))
    calendar_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("calendar_sources.id"), nullable=False
    )
    external_calendar_id: Mapped[UUID] = mapped_column(
        ForeignKey("external_calendars.id"), nullable=False
    )
    calendar_series_id: Mapped[str | None] = mapped_column(String(500))
    template_key: Mapped[str] = mapped_column(String(160), nullable=False)
    approved_roster_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    approved_recipients_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SummaryAutoSendException(Base):
    """Sticky review/cancellation of one instance, independent of its series."""

    __tablename__ = "summary_auto_send_exceptions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "owner_user_id",
            "meeting_id",
            name="uq_summary_auto_send_exception_meeting",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    rule_id: Mapped[UUID | None] = mapped_column(ForeignKey("summary_auto_send_rules.id"))
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
