"""System identities are independent of product users and tenant sessions."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class SystemPrincipal(Base):
    __tablename__ = "principals"
    __table_args__ = (
        CheckConstraint(
            "status in ('invited','active','recovery_pending','blocked','revoked')", name="status"
        ),
        CheckConstraint("auth_version > 0", name="auth_version"),
        {"schema": "system_control"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    normalized_email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(24), default="invited")
    auth_version: Mapped[int] = mapped_column(default=1)
    linked_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_identities.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SystemRoleAssignment(Base):
    __tablename__ = "role_assignments"
    __table_args__ = (
        CheckConstraint(
            "role in ('superadmin','system_admin','support','billing_manager','analyst','auditor')",
            name="role",
        ),
        CheckConstraint("expires_at is null or expires_at > starts_at", name="interval"),
        CheckConstraint("version > 0", name="version"),
        Index(
            "uq_system_role_assignment_current",
            "principal_id",
            unique=True,
            postgresql_where=text("revoked_at is null"),
        ),
        {"schema": "system_control"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    principal_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.principals.id"))
    role: Mapped[str] = mapped_column(String(24))
    version: Mapped[int] = mapped_column(default=1, server_default="1")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    granted_by: Mapped[UUID | None] = mapped_column(ForeignKey("system_control.principals.id"))
    reason: Mapped[str | None] = mapped_column(String(1000))


class SystemSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("auth_version > 0", name="auth_version"),
        CheckConstraint(
            "absolute_expires_at > issued_at and "
            "absolute_expires_at <= issued_at + interval '12 hours'",
            name="lifetime",
        ),
        CheckConstraint("last_interaction_at >= issued_at", name="interaction"),
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="token_hash"),
        Index("ix_system_sessions_principal_revoked", "principal_id", "revoked_at"),
        {"schema": "system_control"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    principal_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.principals.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    auth_version: Mapped[int] = mapped_column()
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_interaction_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mfa_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SystemPermissionGrant(Base):
    __tablename__ = "permission_grants"
    __table_args__ = (
        Index("ix_system_grants_scope", "principal_id", "permission", "target_type", "target_id"),
        CheckConstraint(
            "permission in ('content.read','audio.listen','audio.download',"
            "'content.export','diagnostics.content','billing.manage','catalog.publish',"
            "'promotions.manage','promotions.publish')",
            name="permission",
        ),
        CheckConstraint(
            "expires_at > starts_at and expires_at <= starts_at + interval '24 hours'",
            name="lifetime",
        ),
        CheckConstraint("version > 0 and assignment_version > 0", name="versions"),
        {"schema": "system_control"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    principal_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.principals.id"))
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.role_assignments.id"))
    assignment_version: Mapped[int] = mapped_column()
    version: Mapped[int] = mapped_column(default=1, server_default="1")
    permission: Mapped[str] = mapped_column(String(40))
    target_type: Mapped[str] = mapped_column(String(24))
    target_id: Mapped[UUID] = mapped_column()
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    granted_by: Mapped[UUID] = mapped_column(ForeignKey("system_control.principals.id"))
    reason: Mapped[str] = mapped_column(String(1000))


class SystemCaseContext(Base):
    __tablename__ = "case_contexts"
    __table_args__ = (
        CheckConstraint(
            "expires_at > created_at and expires_at <= created_at + interval '12 hours'",
            name="lifetime",
        ),
        CheckConstraint("length(btrim(reason)) between 1 and 1000", name="reason"),
        {"schema": "system_control"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    principal_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.principals.id"))
    session_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.sessions.id"))
    target_type: Mapped[str] = mapped_column(String(24))
    target_id: Mapped[UUID] = mapped_column()
    reason: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SystemAuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("result in ('allowed','denied')", name="result"),
        Index("ix_system_audit_actor_time", "principal_id", "occurred_at"),
        Index("ix_system_audit_target_time", "target_type", "target_id", "occurred_at"),
        {"schema": "system_control"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    principal_id: Mapped[UUID | None] = mapped_column(ForeignKey("system_control.principals.id"))
    session_id: Mapped[UUID | None] = mapped_column(ForeignKey("system_control.sessions.id"))
    role: Mapped[str] = mapped_column(String(24))
    permission: Mapped[str] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(40))
    target_type: Mapped[str | None] = mapped_column(String(24))
    target_id: Mapped[UUID | None] = mapped_column()
    case_context_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("system_control.case_contexts.id")
    )
    result: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(String(1000))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    operation_id: Mapped[UUID | None] = mapped_column(ForeignKey("system_control.operations.id"))
    writer_transaction: Mapped[int] = mapped_column(BigInteger, server_default=func.txid_current())


class SystemPreview(Base):
    __tablename__ = "previews"
    __table_args__ = {"schema": "system_control"}

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    principal_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.principals.id"))
    session_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.sessions.id"))
    command: Mapped[dict] = mapped_column(JSON)
    permission: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[UUID]
    expected_version: Mapped[int] = mapped_column(BigInteger)
    effect_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SystemOperation(Base):
    __tablename__ = "operations"
    __table_args__ = {"schema": "system_control"}

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    principal_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.principals.id"))
    session_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.sessions.id"))
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.role_assignments.id"))
    assignment_version: Mapped[int]
    preview_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.previews.id"), unique=True)
    kind: Mapped[str] = mapped_column(String(40))
    command: Mapped[dict] = mapped_column(JSON)
    permission: Mapped[str] = mapped_column(String(40))
    idempotency_key: Mapped[UUID]
    request_hash: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(32), server_default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SystemOperationTarget(Base):
    __tablename__ = "operation_targets"
    __table_args__ = {"schema": "system_control"}

    operation_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.operations.id"), primary_key=True)
    target_id: Mapped[UUID] = mapped_column(primary_key=True)
    target_type: Mapped[str] = mapped_column(String(24))
    expected_version: Mapped[int] = mapped_column(BigInteger)
    state: Mapped[str] = mapped_column(String(32), server_default="queued")
    effect_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    domain_ref: Mapped[UUID | None]
    attempt_fence: Mapped[int] = mapped_column(BigInteger, server_default="0")
    allowed_continuation_actions: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}")
    error_code: Mapped[str | None] = mapped_column(String(40))


class SystemCredential(Base):
    __tablename__ = "credentials"
    __table_args__ = {"schema": "system_control"}
    principal_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.principals.id"), primary_key=True)
    credential_version: Mapped[int] = mapped_column(server_default="1")
    encrypted_totp_seed: Mapped[bytes | None] = mapped_column(LargeBinary)
    key_id: Mapped[str | None] = mapped_column(String(80))
    nonce: Mapped[bytes | None] = mapped_column(LargeBinary)
    last_totp_counter: Mapped[int] = mapped_column(BigInteger, server_default="-1")
    recovery_code_hashes: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}")


class SystemChallenge(Base):
    __tablename__ = "challenges"
    __table_args__ = {"schema": "system_control"}
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    principal_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.principals.id"))
    kind: Mapped[str] = mapped_column(String(24))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    issued_auth_version: Mapped[int]
    credential_version: Mapped[int]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(server_default="0")
    delivery_state: Mapped[str] = mapped_column(String(24), server_default="not_attempted")
    delivery_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    encrypted_totp_seed: Mapped[bytes | None] = mapped_column(LargeBinary)
    key_id: Mapped[str | None] = mapped_column(String(80))
    nonce: Mapped[bytes | None] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SystemAuthRateLimit(Base):
    __tablename__ = "rate_limits"
    __table_args__ = {"schema": "system_control"}
    bucket_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(24), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    attempts: Mapped[int]
    attempt_id: Mapped[UUID] = mapped_column(server_default=func.gen_random_uuid())


class SystemMediaTicket(Base):
    __tablename__ = "media_tickets"
    __table_args__ = ({"schema": "system_control"},)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    principal_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.principals.id"))
    session_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.sessions.id"))
    meeting_id: Mapped[UUID] = mapped_column()
    revision_id: Mapped[UUID] = mapped_column()
    case_context_id: Mapped[UUID] = mapped_column(ForeignKey("system_control.case_contexts.id"))
    permission: Mapped[str] = mapped_column(String(40))
    source_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_hash: Mapped[str | None] = mapped_column(String(64))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
