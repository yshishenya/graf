"""Necessary choice control; never an event or provider identity (F273/T106)."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from twobrain_rec_server.db.base import Base


class PublicAnalyticsChoice(Base):
    __tablename__ = 'public_analytics_choices'
    __table_args__ = (
        CheckConstraint("consent_digest ~ '^[0-9a-f]{64}$'", name='public_consent_digest'),
        CheckConstraint(
            "jsonb_typeof(categories)='array' AND categories @> '[\"necessary\"]'::jsonb "
            "AND categories <@ '[\"necessary\",\"analytics\",\"advertising_attribution\",\"behavior_replay\"]'::jsonb "
            "AND jsonb_array_length(categories) BETWEEN 1 AND 4",
            name='public_consent_categories',
        ),
        CheckConstraint(
            "(categories='[\"necessary\"]'::jsonb AND copy_version IS NULL) OR "
            "(jsonb_array_length(categories)>1 AND copy_version IS NOT NULL)",
            name='public_consent_copy',
        ),
    )
    consent_digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    epoch: Mapped[UUID] = mapped_column(nullable=False)
    categories: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    copy_version: Mapped[str | None] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                server_default=func.now())
