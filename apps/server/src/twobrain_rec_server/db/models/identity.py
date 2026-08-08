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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(240))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug"),
        CheckConstraint("kind in ('personal', 'corporate')", name="ck_workspaces_kind"),
        Index(
            "uq_workspaces_personal_owner",
            "organization_id",
            "owner_user_id",
            unique=True,
            postgresql_where=text("kind = 'personal'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    slug: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(240))
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="corporate")
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    default_summary_template_key: Mapped[str] = mapped_column(
        String(120), nullable=False, default="graf-auto-v1"
    )
    default_summary_template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("summary_templates.id")
    )
    default_summary_template_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserIdentity(Base):
    __tablename__ = "user_identities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    external_subject: Mapped[str] = mapped_column(String(240), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")


class RegisteredDevice(Base):
    __tablename__ = "registered_devices"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    device_public_id: Mapped[str] = mapped_column(String(160), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), default="macos")
    client_version: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(32), default="active")
    registration_state: Mapped[str] = mapped_column(String(32), default="approved")
    trusted_by: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    revoked_by: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
