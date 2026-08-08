from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class WorkspaceJoinOffer(Base):
    __tablename__ = "workspace_join_offers"
    __table_args__ = (
        UniqueConstraint("user_id", "invitation_id"),
        Index("ix_workspace_join_offers_user_status", "user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    invitation_id: Mapped[UUID] = mapped_column(ForeignKey("workspace_invitations.id"), nullable=False)
    workspace_name: Mapped[str] = mapped_column(String(240), nullable=False)
    invited_role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="offered")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
