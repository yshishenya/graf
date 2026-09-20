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
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


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
