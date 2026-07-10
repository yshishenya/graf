from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class MeetingOutcomeSet(Base):
    __tablename__ = "meeting_outcome_sets"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "meeting_id",
            "media_revision_id",
            "processing_result_id",
            "generator_version",
            name="uq_meeting_outcome_sets_current_generator",
        ),
        Index("ix_meeting_outcome_sets_meeting_status", "workspace_id", "meeting_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
    processing_result_id: Mapped[UUID] = mapped_column(ForeignKey("processing_results.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="queued")
    summary_state: Mapped[str] = mapped_column(String(64), default="processing")
    key_points_state: Mapped[str] = mapped_column(String(64), default="processing")
    decisions_state: Mapped[str] = mapped_column(String(64), default="processing")
    action_items_state: Mapped[str] = mapped_column(String(64), default="processing")
    followups_state: Mapped[str] = mapped_column(String(64), default="processing")
    risks_state: Mapped[str] = mapped_column(String(64), default="processing")
    questions_state: Mapped[str] = mapped_column(String(64), default="processing")
    evidence_state: Mapped[str] = mapped_column(String(64), default="processing")
    source_kind: Mapped[str] = mapped_column(String(64), default="extractive_generator")
    generator_kind: Mapped[str] = mapped_column(String(64), default="deterministic_extractive")
    generator_version: Mapped[str] = mapped_column(String(120), nullable=False)
    source_result_hash: Mapped[str | None] = mapped_column(String(128))
    content_hash: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    failure_reason: Mapped[str | None] = mapped_column(String(240))
    failure_source: Mapped[str | None] = mapped_column(String(64))
    lifecycle_state: Mapped[str] = mapped_column(String(64), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class MeetingOutcomeItem(Base):
    __tablename__ = "meeting_outcome_items"
    __table_args__ = (
        UniqueConstraint(
            "outcome_set_id",
            "category",
            "sequence",
            name="uq_meeting_outcome_items_set_category_sequence",
        ),
        Index("ix_meeting_outcome_items_set_category_sequence", "outcome_set_id", "category", "sequence"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    outcome_set_id: Mapped[UUID] = mapped_column(ForeignKey("meeting_outcome_sets.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(64), default="available")
    text: Mapped[str | None] = mapped_column(String)
    owner_text: Mapped[str | None] = mapped_column(String(240))
    due_date_text: Mapped[str | None] = mapped_column(String(120))
    truth_label: Mapped[str] = mapped_column(String(64), default="supported")
    source_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MeetingOutcomeGenerationAttempt(Base):
    __tablename__ = "meeting_outcome_generation_attempts"
    __table_args__ = (
        Index(
            "ix_meeting_outcome_generation_attempts_input",
            "workspace_id",
            "meeting_id",
            "processing_result_id",
            "generator_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
    processing_result_id: Mapped[UUID] = mapped_column(ForeignKey("processing_results.id"), nullable=False)
    outcome_set_id: Mapped[UUID | None] = mapped_column(ForeignKey("meeting_outcome_sets.id"))
    status: Mapped[str] = mapped_column(String(64), default="queued")
    provider_kind: Mapped[str] = mapped_column(String(64), default="deterministic_extractive")
    generator_version: Mapped[str] = mapped_column(String(120), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    failure_reason: Mapped[str | None] = mapped_column(String(240))
    failure_source: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
