"""Metadata-only web inbox; local device incidents never enter this table."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class ServerNotification(Base):
    __tablename__ = 'server_notifications'
    __table_args__ = (
        UniqueConstraint('recipient_id', 'workspace_id', 'family', 'source_id', name='uq_server_notification_source'),
        CheckConstraint('revision >= 1 AND read_revision >= 0 AND read_revision <= revision', name='notification_revision'),
        CheckConstraint("family IN ('result', 'share')", name='notification_family'),
        CheckConstraint("(family = 'share' AND kind = 'shared') OR (family = 'result' AND source_id = meeting_id AND kind IN ('transcript_ready', 'result_ready', 'summary_failed', 'processing_failed', 'no_speech'))", name='notification_source_family'),
        Index('ix_server_notification_recipient', 'recipient_id', 'created_at', 'id'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey('user_identities.id'), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey('workspaces.id'), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    family: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[UUID] = mapped_column(nullable=False)
    source_revision: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    read_revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requires_action: Mapped[bool] = mapped_column(default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
