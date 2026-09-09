"""Meeting discussions: plain text and version-bound temporal anchors."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class MeetingComment(Base):
    __tablename__ = "meeting_comments"
    __table_args__ = (
        UniqueConstraint("author_user_id", "meeting_id", "request_id", name="uq_comment_request"),
        CheckConstraint(
            "start_ms >= 0 AND (end_ms IS NULL OR end_ms >= start_ms)", name="comment_range"
        ),
        CheckConstraint("version >= 1", name="comment_version"),
        Index("ix_comment_meeting_created", "workspace_id", "meeting_id", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    author_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    media_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_revisions.id"), nullable=False
    )
    processing_result_id: Mapped[UUID | None] = mapped_column(ForeignKey("processing_results.id"))
    # Canonical turns use either transcript or diarization sources. The service
    # validates this polymorphic UUID against the exact result and meeting.
    source_segment_id: Mapped[UUID | None] = mapped_column()
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("meeting_comments.id", ondelete="CASCADE")
    )
    request_id: Mapped[UUID] = mapped_column(nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    start_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    end_ms: Mapped[int | None] = mapped_column(BigInteger)
    body: Mapped[str] = mapped_column(String(10000), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    resolved: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    resolved_by: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MeetingCommentMention(Base):
    __tablename__ = "meeting_comment_mentions"
    __table_args__ = (UniqueConstraint("comment_id", "user_id", name="uq_comment_mention"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    comment_id: Mapped[UUID] = mapped_column(
        ForeignKey("meeting_comments.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    start: Mapped[int] = mapped_column(Integer, nullable=False)
    end: Mapped[int] = mapped_column(Integer, nullable=False)


class MeetingCommentReaction(Base):
    __tablename__ = "meeting_comment_reactions"
    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", "emoji", name="uq_comment_reaction"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    comment_id: Mapped[UUID] = mapped_column(
        ForeignKey("meeting_comments.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    emoji: Mapped[str] = mapped_column(String(32), nullable=False)
