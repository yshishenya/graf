from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
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


class MeetingShareGrant(Base):
    __tablename__ = "meeting_share_grants"
    __table_args__ = (
        Index(
            "uq_meeting_share_grants_active_user",
            "workspace_id",
            "meeting_id",
            "audience_id",
            unique=True,
            postgresql_where=text("status = 'active' AND audience_type = 'user'"),
        ),
        Index(
            "uq_meeting_share_grants_active_link",
            "workspace_id",
            "meeting_id",
            unique=True,
            postgresql_where=text("status = 'active' AND audience_type = 'link'"),
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
    audience_type: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    audience_id: Mapped[UUID | None] = mapped_column()
    content_scope: Mapped[str] = mapped_column(
        String(32), nullable=False, default="summary_only"
    )
    can_download: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_export: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MeetingShareInvitation(Base):
    __tablename__ = "meeting_share_invitations"
    __table_args__ = (
        Index(
            "uq_meeting_share_invitations_address_status",
            "workspace_id",
            "meeting_id",
            "normalized_address_hash",
            unique=True,
            postgresql_where=text("status IN ('pending', 'sending', 'sent')"),
        ),
        Index(
            "ix_meeting_share_invitations_token_hash",
            "workspace_id",
            "token_hash",
        ),
        Index(
            "ix_meeting_share_invitations_continuation_nonce",
            "workspace_id",
            "continuation_nonce",
            postgresql_where=text("continuation_nonce IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    invited_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_identities.id"), nullable=False
    )
    normalized_address_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_delivery_address: Mapped[str] = mapped_column(String, nullable=False)
    # Retained only until acceptance/revoke/expiry so magic-link bootstrap can
    # prove the invited address without putting PII in the URL.
    encrypted_recipient_address: Mapped[str | None] = mapped_column(String)
    grant_token_ciphertext: Mapped[str | None] = mapped_column(String)
    continuation_nonce: Mapped[str | None] = mapped_column(String(128))
    continuation_token_ciphertext: Mapped[str | None] = mapped_column(String)
    continuation_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    continuation_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_scope: Mapped[str] = mapped_column(
        String(32), nullable=False, default="summary_only"
    )
    can_download: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_export: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    resolved_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(120))
    account_created_email_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_applicable", server_default="not_applicable"
    )
    account_created_email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    account_created_email_failure_code: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MeetingShareRateLimitBucket(Base):
    """Durable actor/device buckets for authenticated share operations."""

    __tablename__ = "meeting_share_rate_limit_buckets"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "user_id",
            "device_id",
            "action_key",
            name="uq_meeting_share_rate_limit_scope",
        ),
        Index("ix_meeting_share_rate_limit_blocked_until", "blocked_until"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    device_id: Mapped[UUID] = mapped_column(ForeignKey("registered_devices.id"), nullable=False)
    action_key: Mapped[str] = mapped_column(String(64), nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
