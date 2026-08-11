from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
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


class BillingPlanVersion(Base):
    __tablename__ = "billing_plan_versions"
    __table_args__ = (UniqueConstraint("plan_code", "version", name="uq_billing_plan_versions_code_version"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    plan_code: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    cycle: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    amount_minor: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    processing_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    enabled_for_checkout: Mapped[bool] = mapped_column(nullable=False, default=False)
    policy_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromotionCampaign(Base):
    """Versioned, operator-created campaign; raw promo codes are never stored."""

    __tablename__ = "promotion_campaigns"
    __table_args__ = (UniqueConstraint("code_hash", name="uq_promotion_campaigns_code_hash"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    campaign_version: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_code: Mapped[str] = mapped_column(String(32), nullable=False)
    cycle: Mapped[str | None] = mapped_column(String(16))
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    max_redemptions: Mapped[int] = mapped_column(Integer, nullable=False)
    redeemed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    policy_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromotionRedemption(Base):
    """One atomic reservation/redemption bound to one invoice."""

    __tablename__ = "promotion_redemptions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "reservation_key",
            name="uq_promotion_redemptions_workspace_reservation_key",
        ),
        UniqueConstraint("workspace_id", "campaign_id", name="uq_promotion_redemptions_workspace_campaign"),
        Index("ix_promotion_redemptions_invoice", "invoice_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("promotion_campaigns.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("billing_invoices.id"), nullable=False)
    reservation_key: Mapped[str] = mapped_column(String(240), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    list_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    payable_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="reserved")
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkspaceSubscription(Base):
    __tablename__ = "workspace_subscriptions"

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    billing_owner_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    plan_code: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    cycle: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    capacity_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=250_000_000)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_through: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    billing_anchor: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recurring_allowed: Mapped[bool] = mapped_column(nullable=False, default=False)
    recurring_authority_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    renewal_resolution: Mapped[str | None] = mapped_column(String(40))
    application_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TrialActivation(Base):
    __tablename__ = "trial_activations"
    __table_args__ = (UniqueConstraint("user_id", name="uq_trial_activations_user"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BillingInvoice(Base):
    __tablename__ = "billing_invoices"
    __table_args__ = (UniqueConstraint("workspace_id", "operation_id", name="uq_billing_invoices_operation"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    operation_id: Mapped[UUID] = mapped_column(ForeignKey("billing_operations.id"), nullable=False)
    safe_number: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    plan_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    receipt_contact_snapshot: Mapped[str | None] = mapped_column(String(254))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BillingEntitlementGrant(Base):
    __tablename__ = "billing_entitlement_grants"
    __table_args__ = (
        UniqueConstraint("workspace_id", "invoice_id", name="uq_billing_entitlement_grant_invoice"),
        Index("ix_billing_entitlement_grants_workspace_period", "workspace_id", "starts_at", "ends_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("billing_invoices.id"), nullable=False)
    provider_payment_id: Mapped[str] = mapped_column(String(160), nullable=False)
    plan_code: Mapped[str] = mapped_column(String(32), nullable=False)
    cycle: Mapped[str] = mapped_column(String(16), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="provider_confirmed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BillingOperation(Base):
    __tablename__ = "billing_operations"
    __table_args__ = (UniqueConstraint("workspace_id", "idempotency_key", name="uq_billing_operations_key"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(240), nullable=False)
    provider_id: Mapped[str | None] = mapped_column(String(160))
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    provider_key_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BillingPaymentMethod(Base):
    __tablename__ = "billing_payment_methods"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    encrypted_provider_ref: Mapped[str] = mapped_column(String(2048), nullable=False)
    key_version: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="bank_card")
    masked_label: Mapped[str | None] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    is_default: Mapped[bool] = mapped_column(nullable=False, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ObservedProviderRefund(Base):
    __tablename__ = "observed_provider_refunds"
    __table_args__ = (UniqueConstraint("shop_environment", "provider_refund_id", name="uq_observed_refunds_provider"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("billing_invoices.id"), nullable=False)
    shop_environment: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_refund_id: Mapped[str] = mapped_column(String(160), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="succeeded")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FreeUsageWindow(Base):
    __tablename__ = "free_usage_windows"
    __table_args__ = (UniqueConstraint("workspace_id", "window_start", name="uq_free_usage_windows_workspace_window"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    included_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=18_000)
    committed_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    freshness_state: Mapped[str] = mapped_column(String(32), nullable=False, default="fresh")


class UsageReservation(Base):
    __tablename__ = "usage_reservations"
    __table_args__ = (UniqueConstraint("workspace_id", "idempotency_key", name="uq_usage_reservations_key"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    window_id: Mapped[UUID] = mapped_column(ForeignKey("free_usage_windows.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(240), nullable=False)
    declared_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    committed_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UsageLedgerEntry(Base):
    __tablename__ = "usage_ledger_entries"
    __table_args__ = (Index("ix_usage_ledger_entries_source_range", "workspace_id", "source_id", "start_second", "end_second", unique=True),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    reservation_id: Mapped[UUID] = mapped_column(ForeignKey("usage_reservations.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(String(240), nullable=False)
    start_second: Mapped[int] = mapped_column(Integer, nullable=False)
    end_second: Mapped[int] = mapped_column(Integer, nullable=False)
    committed_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StorageReservation(Base):
    __tablename__ = "storage_reservations"
    __table_args__ = (UniqueConstraint("workspace_id", "idempotency_key", name="uq_storage_reservations_key"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(240), nullable=False)
    declared_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    committed_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    artifact_id: Mapped[UUID | None] = mapped_column(ForeignKey("track_artifacts.id"))
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TimeCreditLedgerEntry(Base):
    __tablename__ = "time_credit_ledger_entries"
    __table_args__ = (
        UniqueConstraint("workspace_id", "source_ref", name="uq_time_credit_source"),
        Index("ix_time_credit_referral_attribution", "referral_attribution_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    referral_attribution_id: Mapped[UUID | None] = mapped_column(ForeignKey("referral_attributions.id"))
    source_ref: Mapped[str] = mapped_column(String(240), nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    maturity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    applied_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reversal_of_id: Mapped[UUID | None] = mapped_column(ForeignKey("time_credit_ledger_entries.id"))


class BillingAuditEvent(Base):
    __tablename__ = "billing_audit_events"
    __table_args__ = (Index("ix_billing_audit_events_workspace_created", "workspace_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    target_ref: Mapped[str | None] = mapped_column(String(160))
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(120))
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BillingNotificationDelivery(Base):
    __tablename__ = "billing_notification_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "event_id",
            "recipient_id",
            "channel",
            name="uq_billing_notification_delivery",
        ),
        Index("ix_billing_notification_delivery_pending", "workspace_id", "state", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    template_key: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    safe_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BillingNotificationPreference(Base):
    """User-scoped optional notification choices; mandatory notices override them."""

    __tablename__ = "billing_notification_preferences"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), primary_key=True)
    optional_email_enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    optional_in_app_enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FairUseReviewRecord(Base):
    """Persisted, metadata-only fair-use review visible to its affected user."""

    __tablename__ = "fair_use_reviews"
    __table_args__ = (
        UniqueConstraint("workspace_id", "evidence_ref", name="uq_fair_use_review_evidence"),
        CheckConstraint(
            "reason_code in ('automated_bulk', 'resale', 'limit_circumvention', 'security_abuse')",
            name="ck_fair_use_review_reason",
        ),
        CheckConstraint(
            "state in ('notice', 'restricted', 'appealed', 'cleared', 'confirmed')",
            name="ck_fair_use_review_state",
        ),
        CheckConstraint(
            "review_by <= starts_at + interval '24 hours'",
            name="ck_fair_use_review_deadline",
        ),
        CheckConstraint(
            "capability ~ '^[A-Za-z0-9_.:-]{1,64}$'",
            name="ck_fair_use_review_capability",
        ),
        CheckConstraint(
            "evidence_ref ~ '^[A-Za-z0-9_.:-]{1,160}$'",
            name="ck_fair_use_review_evidence_ref",
        ),
        Index("ix_fair_use_reviews_workspace_state", "workspace_id", "state", "review_by"),
        Index("ix_fair_use_reviews_subject_state", "subject_user_id", "state"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    subject_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    review_by: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="notice")
    appealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    appeal_ref: Mapped[str | None] = mapped_column(String(64))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_code: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BillingWebhookEvent(Base):
    __tablename__ = "billing_webhook_events"
    __table_args__ = (UniqueConstraint("workspace_id", "provider_event_id", name="uq_billing_webhook_provider_event"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    object_id: Mapped[str] = mapped_column(String(160), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="accepted")
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReferralLink(Base):
    """One stable inviter link that can create many invitee attributions."""

    __tablename__ = "referral_links"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_referral_links_token_hash"),
        Index("ix_referral_links_workspace_state", "workspace_id", "state"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    inviter_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    campaign_version: Mapped[str] = mapped_column(String(64), nullable=False, default="referral-v1")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class ReferralAttribution(Base):
    __tablename__ = "referral_attributions"
    __table_args__ = (
        UniqueConstraint("referral_link_id", "invitee_user_id", name="uq_referral_attributions_link_invitee"),
        Index("ix_referral_attributions_workspace_state", "workspace_id", "state"),
        Index("ix_referral_attributions_link_state", "referral_link_id", "state"),
        Index(
            "uq_referral_attributions_invitee",
            "invitee_user_id",
            unique=True,
            postgresql_where=text("invitee_user_id is not null"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    inviter_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    invitee_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    referral_link_id: Mapped[UUID] = mapped_column(ForeignKey("referral_links.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    campaign_version: Mapped[str] = mapped_column(String(64), nullable=False, default="referral-v1")
    first_touched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="issued")
    risk_signal: Mapped[str | None] = mapped_column(String(120))
