"""Measurement storage for feature 273: the anonymous aggregate and level 2 attribution.

Level 1 rows (``anonymous_page_aggregate_buckets``) carry no identifier of any
kind: no device address, no session or visit identifier, no user-agent string,
no device fingerprint and no pseudonym. Level 2 rows hold campaign attribution
that belongs to a registered customer and is erased together with the account.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base

ACTIVATION_MILESTONE_STATES = (
    "not_requested",
    "pending",
    "pre_send_retry",
    "dispatching",
    "submitted",
    "ambiguous",
    "confirmed",
    "cancelled",
    "rejected",
)
ACTIVATION_MILESTONE_REASONS = (
    "not_requested",
    "accepted",
    "technical_pre_send",
    "dispatch_started",
    "http_accepted",
    "transport_ambiguous",
    "http_ambiguous",
    "interrupted_dispatch",
    "readback_confirmed",
    "purpose_withdrawn",
    "basis_unavailable",
    "provider_disabled",
    "payload_rejected",
    "restore_quarantine",
)
ACCOUNT_ACTIVATION_EVENTS = (
    "desktop_account_connected",
    "desktop_autorecord_enabled",
    "first_recording_completed",
    "first_result_viewed",
    "first_value_session_completed",
)


class ProductActivationMilestone(Base):
    """One durable first decision and two fixed delivery intents (F273/T113)."""

    __tablename__ = "product_activation_milestones"
    __table_args__ = (
        UniqueConstraint("account_id", "event_name", name="uq_activation_account_event"),
        CheckConstraint(f"event_name IN {ACCOUNT_ACTIVATION_EVENTS}", name="activation_event"),
        CheckConstraint(
            "source_kind IN ('browser', 'desktop', 'server')", name="activation_source"
        ),
        CheckConstraint(
            "jsonb_typeof(safe_payload) = 'object' AND "
            "octet_length(convert_to(safe_payload::text, 'UTF8')) <= 16384",
            name="activation_payload_size",
        ),
        *(
            CheckConstraint(
                f"{provider}_state IN {ACTIVATION_MILESTONE_STATES}",
                name=f"activation_{provider}_state",
            )
            for provider in ("posthog", "yandex")
        ),
        *(
            CheckConstraint(
                f"{provider}_reason IN {ACTIVATION_MILESTONE_REASONS}",
                name=f"activation_{provider}_reason",
            )
            for provider in ("posthog", "yandex")
        ),
        Index("ix_activation_posthog_pending", "posthog_state", "accepted_at"),
        Index("ix_activation_yandex_pending", "yandex_state", "accepted_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_identities.id", ondelete="CASCADE"), nullable=False
    )
    event_name: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[UUID] = mapped_column(nullable=False, unique=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    safe_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(8), nullable=False)
    posthog_state: Mapped[str] = mapped_column(String(16), nullable=False, default="not_requested")
    yandex_state: Mapped[str] = mapped_column(String(16), nullable=False, default="not_requested")
    posthog_reason: Mapped[str] = mapped_column(String(80), nullable=False, default="not_requested")
    yandex_reason: Mapped[str] = mapped_column(String(80), nullable=False, default="not_requested")
    posthog_attempt_id: Mapped[UUID | None] = mapped_column()
    yandex_attempt_id: Mapped[UUID | None] = mapped_column()
    posthog_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    yandex_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posthog_confirmation_ref: Mapped[str | None] = mapped_column(String(120))
    yandex_confirmation_ref: Mapped[str | None] = mapped_column(String(120))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AnonymousPageAggregateBucket(Base):
    """One counter row per combination of coarse page dimensions (level 1).

    Optional campaign labels stay ``NULL`` when absent; the unique constraint
    treats missing labels as equal so a repeated visit updates the same bucket
    instead of creating a parallel row.
    """

    __tablename__ = "anonymous_page_aggregate_buckets"
    __table_args__ = (
        UniqueConstraint(
            "bucket_date",
            "bucket_hour",
            "surface",
            "landing_path",
            "source",
            "medium",
            "campaign",
            "content",
            "term",
            "device_class",
            "region",
            "referrer_category",
            "traffic_class",
            name="uq_anonymous_page_aggregate_bucket",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "bucket_hour IS NULL OR (bucket_hour >= 0 AND bucket_hour <= 23)",
            name="aggregate_hour",
        ),
        CheckConstraint(
            "device_class IN ('desktop', 'mobile', 'tablet', 'unknown')",
            name="aggregate_device_class",
        ),
        CheckConstraint(
            "region IN ('ru', 'non_ru', 'unknown')",
            name="aggregate_region",
        ),
        CheckConstraint(
            "referrer_category IN ('direct', 'organic', 'paid', 'referral', 'unknown')",
            name="aggregate_referrer_category",
        ),
        CheckConstraint(
            "traffic_class IN ('external', 'internal', 'support', 'test', 'automated')",
            name="aggregate_traffic_class",
        ),
        CheckConstraint("visits >= 1", name="aggregate_visits"),
        Index("ix_anonymous_aggregate_report", "bucket_date", "traffic_class"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    bucket_date: Mapped[date] = mapped_column(Date, nullable=False)
    bucket_hour: Mapped[int | None] = mapped_column(SmallInteger)
    surface: Mapped[str] = mapped_column(String(40), nullable=False)
    landing_path: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str | None] = mapped_column(String(96))
    medium: Mapped[str | None] = mapped_column(String(96))
    campaign: Mapped[str | None] = mapped_column(String(96))
    content: Mapped[str | None] = mapped_column(String(96))
    term: Mapped[str | None] = mapped_column(String(96))
    device_class: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    region: Mapped[str] = mapped_column(
        String(7), nullable=False, default="unknown", server_default="unknown"
    )
    referrer_category: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    traffic_class: Mapped[str] = mapped_column(String(16), nullable=False, default="external")
    visits: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PublicVisitAttribution(Base):
    """The 90-day visit attribution used to carry a campaign into registration."""

    __tablename__ = "public_visit_attributions"
    __table_args__ = (
        CheckConstraint("expires_at > first_seen_at", name="attribution_window"),
        CheckConstraint(
            "expires_at <= first_seen_at + interval '90 days'",
            name="attribution_max_window",
        ),
        CheckConstraint(
            "yclid IS NULL OR (length(yclid) >= 8 AND length(yclid) <= 120)",
            name="attribution_yclid",
        ),
        Index("ix_public_visit_attribution_created_at", "created_at"),
        Index("ix_public_visit_attribution_expiry", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    attribution_ref: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    source: Mapped[str | None] = mapped_column(String(96))
    medium: Mapped[str | None] = mapped_column(String(96))
    campaign: Mapped[str | None] = mapped_column(String(96))
    content: Mapped[str | None] = mapped_column(String(96))
    term: Mapped[str | None] = mapped_column(String(96))
    yclid: Mapped[str | None] = mapped_column(String(120))
    landing_path: Mapped[str] = mapped_column(String(200), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ClientAcquisitionAttribute(Base):
    """The campaign attribute copied onto the client record at registration."""

    __tablename__ = "client_acquisition_attributes"
    __table_args__ = (
        CheckConstraint(
            "attribution_rule IN ('last_non_direct_90d')",
            name="acquisition_rule",
        ),
        CheckConstraint(
            "attribution_confidence IN ('linked', 'weak', 'unknown')",
            name="acquisition_confidence",
        ),
        CheckConstraint(
            "graf_attribution_id IS NULL OR graf_attribution_id ~ '^graf_attr_[0-9a-z_-]{8,64}$'",
            name="acquisition_attribution_bridge",
        ),
        UniqueConstraint("account_id", name="uq_client_acquisition_account"),
        Index("ix_client_acquisition_captured", "captured_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    source: Mapped[str | None] = mapped_column(String(96))
    medium: Mapped[str | None] = mapped_column(String(96))
    campaign: Mapped[str | None] = mapped_column(String(96))
    content: Mapped[str | None] = mapped_column(String(96))
    term: Mapped[str | None] = mapped_column(String(96))
    yclid: Mapped[str | None] = mapped_column(String(120))
    # The bridge the campaign arrived through (FR-022). An opaque identifier
    # issued by the product, kept under the same retention term as the campaign
    # it belongs to; it is never an identifier of a person.
    graf_attribution_id: Mapped[str | None] = mapped_column(String(80))
    landing_path: Mapped[str] = mapped_column(String(200), nullable=False)
    attribution_rule: Mapped[str] = mapped_column(
        String(40), nullable=False, default="last_non_direct_90d"
    )
    attribution_confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
