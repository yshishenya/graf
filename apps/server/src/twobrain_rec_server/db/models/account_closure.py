"""Durable account-close cooling and finalization state."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class AccountClosureRequest(Base):
    """One user/account close request with an auditable seven-day cooling window.

    This row is deliberately separate from meeting deletion.  Scheduling the
    close only disables future recurring charges; destructive access revocation
    is performed by the finalizer after the cooling window has elapsed.
    """

    __tablename__ = "account_closure_requests"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "requested_by_user_id",
            "request_key",
            name="uq_account_closure_request_key",
        ),
        Index("ix_account_closure_due", "state", "finalize_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    requested_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_identities.id"), nullable=False
    )
    request_key: Mapped[str] = mapped_column(String(160), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False, default="account-close-v1")
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finalize_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(String(240))
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
