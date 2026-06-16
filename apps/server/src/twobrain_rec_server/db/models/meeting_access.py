from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class MeetingShareGrant(Base):
    __tablename__ = "meeting_share_grants"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "meeting_id",
            "grantee_user_id",
            "status",
            name="uq_meeting_share_grants_active_user",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    grant_type: Mapped[str] = mapped_column(String(32), nullable=False)
    grantee_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    share_token_hash: Mapped[str | None] = mapped_column(String(128))
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    revoked_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    status: Mapped[str] = mapped_column(String(32), default="active")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MeetingArtifactPolicy(Base):
    __tablename__ = "meeting_artifact_policies"
    __table_args__ = (
        UniqueConstraint("workspace_id", "meeting_id", name="uq_meeting_artifact_policies_workspace_meeting"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    audio_download: Mapped[str] = mapped_column(String(32), default="disabled")
    transcript_download: Mapped[str] = mapped_column(String(32), default="disabled")
    summary_download: Mapped[str] = mapped_column(String(32), default="disabled")
    package_export: Mapped[str] = mapped_column(String(32), default="disabled")
    policy_source: Mapped[str] = mapped_column(String(64), default="meeting_default")
    updated_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class MeetingEgressAuditEvent(Base):
    __tablename__ = "meeting_egress_audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID | None] = mapped_column(ForeignKey("meetings.id"))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    device_id: Mapped[UUID | None] = mapped_column(ForeignKey("registered_devices.id"))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    artifact_class: Mapped[str | None] = mapped_column(String(32))
    policy_reason: Mapped[str | None] = mapped_column(String(240))
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExportPackage(Base):
    __tablename__ = "export_packages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    requested_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="requested")
    included_artifacts: Mapped[list] = mapped_column(JSON, default=list)
    excluded_artifacts: Mapped[list] = mapped_column(JSON, default=list)
    manifest_json: Mapped[dict] = mapped_column(JSON, default=dict)
    byte_length: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
