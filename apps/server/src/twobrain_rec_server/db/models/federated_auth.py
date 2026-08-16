from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
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


class ExternalIdentity(Base):
    __tablename__ = "external_identities"
    __table_args__ = (UniqueConstraint("provider", "provider_subject"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(240), nullable=False)
    provider_username: Mapped[str | None] = mapped_column(String(160))
    email: Mapped[str | None] = mapped_column(String(240))
    phone: Mapped[str | None] = mapped_column(String(64))
    display_name: Mapped[str | None] = mapped_column(String(240))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    subject_issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkspaceAuthPolicy(Base):
    __tablename__ = "workspace_auth_policies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), unique=True, nullable=False)
    allow_yandex: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_vk: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_telegram: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_tid: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_sber_id: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_mts_id: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_esia: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_provider_self_enrollment: Mapped[bool] = mapped_column(Boolean, default=False)
    require_ru_local: Mapped[bool] = mapped_column(Boolean, default=True)
    residency_region_tag: Mapped[str] = mapped_column(String(16), default="ru")
    consent_text_version: Mapped[str] = mapped_column(String(64), default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (UniqueConstraint("session_token_hash"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    device_id: Mapped[UUID | None] = mapped_column(ForeignKey("registered_devices.id"))
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    session_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    claims_fingerprint: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuthSessionDeviceBinding(Base):
    __tablename__ = "auth_session_device_bindings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    auth_session_id: Mapped[UUID] = mapped_column(ForeignKey("auth_sessions.id"), nullable=False)
    registered_device_id: Mapped[UUID] = mapped_column(ForeignKey("registered_devices.id"), nullable=False)
    device_state: Mapped[str] = mapped_column(String(32), default="untrusted")
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(String(240))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkspaceProviderLinkState(Base):
    __tablename__ = "workspace_provider_link_states"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    initiating_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    source_provider_identity_id: Mapped[UUID] = mapped_column(ForeignKey("external_identities.id"), nullable=False)
    target_provider_identity_id: Mapped[UUID | None] = mapped_column(ForeignKey("external_identities.id"))
    initiating_auth_session_id: Mapped[UUID | None] = mapped_column(ForeignKey("auth_sessions.id"))
    callback_state_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("auth_callback_states.id"), unique=True
    )
    candidate_provider: Mapped[str | None] = mapped_column(String(64))
    candidate_identity_subject: Mapped[str | None] = mapped_column(String(240))
    candidate_email: Mapped[str | None] = mapped_column(String(240))
    candidate_phone: Mapped[str | None] = mapped_column(String(64))
    candidate_display_name: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(32), default="initiated")
    resolution: Mapped[str | None] = mapped_column(String(240))
    callback_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AccountMergeIntent(Base):
    """Short-lived, proof-bound state for an explicit account merge."""

    __tablename__ = "account_merge_intents"
    __table_args__ = (
        CheckConstraint("survivor_user_id <> source_user_id", name="ck_account_merge_distinct_users"),
        Index("ix_account_merge_intents_expiry", "status", "expires_at"),
        Index(
            "uq_account_merge_active_pair",
            "survivor_user_id",
            "source_user_id",
            unique=True,
            postgresql_where=(
                "status in ('initiated', 'awaiting_proof', 'preview_ready', 'confirmed')"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    survivor_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    source_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    email_proof_state: Mapped[str] = mapped_column(String(32), nullable=False, default="missing")
    oauth_proof_state: Mapped[str] = mapped_column(String(32), nullable=False, default="missing")
    preview_fingerprint: Mapped[str | None] = mapped_column(String(64))
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="initiated")
    blocker_code: Mapped[str | None] = mapped_column(String(120))
    error_code: Mapped[str | None] = mapped_column(String(120))
    idempotency_key_hash: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AccountMergeJournal(Base):
    """Immutable metadata-only result projection for merge support and retries."""

    __tablename__ = "account_merge_journals"
    __table_args__ = (UniqueConstraint("merge_intent_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merge_intent_id: Mapped[UUID] = mapped_column(ForeignKey("account_merge_intents.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    survivor_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    source_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    preview_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    counts_json: Mapped[dict] = mapped_column(JSON, default=dict)
    blocker_codes_json: Mapped[list] = mapped_column(JSON, default=list)
    error_code: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthCallbackState(Base):
    __tablename__ = "auth_callback_states"
    __table_args__ = (UniqueConstraint("state_nonce"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    state_nonce: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    requested_redirect: Mapped[str | None] = mapped_column(String(512))
    expected_state: Mapped[str] = mapped_column(String(256), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[str] = mapped_column(String(32), default="pending")
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthAuditEvent(Base):
    __tablename__ = "auth_audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    actor_ip_hash: Mapped[str | None] = mapped_column(String(128))
    request_id: Mapped[str | None] = mapped_column(String(128))
    outcome: Mapped[str] = mapped_column(String(32), default="success")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthRateLimitBucket(Base):
    """Hashed, workspace-scoped buckets for unauthenticated auth attempts."""

    __tablename__ = "auth_rate_limit_buckets"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "scope_hash",
            "action_key",
            name="uq_auth_rate_limit_scope",
        ),
        Index("ix_auth_rate_limit_blocked_until", "blocked_until"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    scope_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    action_key: Mapped[str] = mapped_column(String(64), nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkspaceConsentCopy(Base):
    __tablename__ = "workspace_consent_copy"
    __table_args__ = (UniqueConstraint("workspace_id", "language", "version"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="ru")
    version: Mapped[str] = mapped_column(String(32), default="v1")
    content_markdown: Mapped[str] = mapped_column(String(4000), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
