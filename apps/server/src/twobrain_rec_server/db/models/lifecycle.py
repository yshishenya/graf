from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
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


class DispatchIntent(Base):
    """Durable metadata-only handoff between a committed request and a worker.

    The payload is intentionally references/statuses only. Content-bearing data
    remains in the existing GenerationCall ledger and never enters the outbox.
    """

    __tablename__ = "dispatch_intents"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_dispatch_intents_workspace_idempotency_key",
        ),
        Index("ix_dispatch_intents_due", "state", "next_attempt_at"),
        Index("ix_dispatch_intents_meeting", "workspace_id", "meeting_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    candidate_id: Mapped[UUID | None] = mapped_column()
    intent_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(240), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    reconciliation_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_fingerprint: Mapped[str | None] = mapped_column(String(128))
    deletion_epoch: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_workflow_id: Mapped[str | None] = mapped_column(String(240))
    external_run_id: Mapped[str | None] = mapped_column(String(240))
    failure_code: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DeletionFence(Base):
    """One monotonic lifecycle fence per meeting."""

    __tablename__ = "meeting_deletion_fences"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "meeting_id", name="uq_meeting_deletion_fences_workspace_meeting"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    epoch: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    state: Mapped[str] = mapped_column(String(64), nullable=False, default="active")
    retention_boundary: Mapped[str] = mapped_column(
        String(64), nullable=False, default="graf_controlled_purge"
    )
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PurgeJournal(Base):
    """Retryable object-store purge ledger; DB and object deletion are not atomic."""

    __tablename__ = "meeting_purge_journal"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "meeting_id",
            "artifact_class",
            "object_key",
            name="uq_meeting_purge_journal_object",
        ),
        Index("ix_meeting_purge_journal_due", "state", "next_retry_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    deletion_request_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("meeting_deletion_requests.id")
    )
    artifact_class: Mapped[str] = mapped_column(String(64), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    safe_reason: Mapped[str | None] = mapped_column(String(240))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
