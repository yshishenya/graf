"""Immutable reader documents and durable, address-scoped delivery ledger."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class PublishedMeetingSummary(Base):
    __tablename__ = "published_meeting_summaries"
    __table_args__ = (
        Index("ix_published_summary_meeting", "workspace_id", "meeting_id"),
        UniqueConstraint("id", "workspace_id", "meeting_id", name="uq_published_summary_scope"),
        ForeignKeyConstraint(
            ["meeting_id", "workspace_id"],
            ["meetings.id", "meetings.workspace_id"],
            name="fk_published_summary_meeting_scope",
            onupdate="CASCADE",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    source_outcome_id: Mapped[UUID] = mapped_column(nullable=False)
    template_key: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    projection_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SummaryDeliveryBatch(Base):
    __tablename__ = "summary_delivery_batches"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "owner_user_id", "idempotency_key", name="uq_summary_batch_operation"
        ),
        UniqueConstraint("id", "workspace_id", name="uq_summary_batch_scope"),
        ForeignKeyConstraint(
            ["published_summary_id", "workspace_id", "meeting_id"],
            [
                "published_meeting_summaries.id",
                "published_meeting_summaries.workspace_id",
                "published_meeting_summaries.meeting_id",
            ],
            name="fk_summary_batch_publication_scope",
            onupdate="CASCADE",
        ),
        Index("ix_summary_batch_meeting", "workspace_id", "meeting_id"),
        Index("ix_summary_batch_due", "state", "scheduled_at"),
        Index(
            "uq_summary_auto_occurrence",
            "workspace_id",
            "auto_occurrence_key",
            unique=True,
            postgresql_where=text("automatic = true AND auto_occurrence_key IS NOT NULL"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    published_summary_id: Mapped[UUID] = mapped_column(
        ForeignKey("published_meeting_summaries.id"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    automatic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    auto_rule_id: Mapped[UUID | None] = mapped_column()
    auto_rule_version: Mapped[int | None] = mapped_column(Integer)
    auto_occurrence_key: Mapped[str | None] = mapped_column(String(128))
    auto_authority_json: Mapped[dict | None] = mapped_column(JSON)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(120))


class SummaryRecipientDelivery(Base):
    __tablename__ = "summary_recipient_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "batch_id", "normalized_address_hash", name="uq_summary_recipient_address"
        ),
        ForeignKeyConstraint(
            ["batch_id", "workspace_id"],
            ["summary_delivery_batches.id", "summary_delivery_batches.workspace_id"],
            name="fk_summary_recipient_batch_scope",
            onupdate="CASCADE",
        ),
        Index("ix_summary_recipient_batch", "workspace_id", "batch_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("summary_delivery_batches.id"), nullable=False
    )
    normalized_address_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_address: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    invitation_id: Mapped[UUID | None] = mapped_column(ForeignKey("meeting_share_invitations.id"))
    grant_id: Mapped[UUID | None] = mapped_column(ForeignKey("meeting_share_grants.id"))
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(120))
    provider_message_id: Mapped[str | None] = mapped_column(String(240))


class SummaryEmailSuppression(Base):
    __tablename__ = "summary_email_suppressions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "sender_user_id",
            "normalized_address_hash",
            name="uq_summary_suppression_scope",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    sender_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    normalized_address_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    token_ciphertext: Mapped[str] = mapped_column(String, nullable=False)
    opted_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
