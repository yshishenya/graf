"""Shop-global registry metadata, accessible only to the exact maintenance role."""
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from twobrain_rec_server.db.base import Base


class BillingRegistryImport(Base):
    __tablename__ = "billing_registry_imports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    environment: Mapped[str] = mapped_column(String(10))
    shop_id: Mapped[str] = mapped_column(String(32))
    report_date: Mapped[date] = mapped_column(Date)
    profile: Mapped[str] = mapped_column(String(64))
    config_fingerprint: Mapped[str] = mapped_column(String(64))
    input_digest: Mapped[str | None] = mapped_column(String(64))
    parts: Mapped[list] = mapped_column(JSONB)
    expected_empty: Mapped[list] = mapped_column(JSONB)
    accepted: Mapped[bool] = mapped_column(Boolean)
    files_complete: Mapped[bool] = mapped_column(Boolean)
    result_code: Mapped[str] = mapped_column(String(64))
    previous_accepted_id: Mapped[int | None] = mapped_column(ForeignKey("billing_registry_imports.id"))
    operator: Mapped[str] = mapped_column(String(64))
    reason_code: Mapped[str] = mapped_column(String(32))
    session_identity: Mapped[str] = mapped_column(String(64), server_default=func.session_user())
    current_identity: Mapped[str] = mapped_column(String(64), server_default=func.current_user())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())


class BillingRegistryGap(Base):
    __tablename__ = "billing_registry_gaps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    environment: Mapped[str] = mapped_column(String(10))
    shop_id: Mapped[str] = mapped_column(String(32))
    report_date: Mapped[date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(8))
    part_index: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(64))
    generation: Mapped[int] = mapped_column(Integer)
    owner: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(4), server_default="high")
    containment: Mapped[str] = mapped_column(String(24), server_default="report_unverified")
    state: Mapped[str] = mapped_column(String(8), server_default="detected")
    detected_receipt_id: Mapped[int] = mapped_column(ForeignKey("billing_registry_imports.id"))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closing_receipt_id: Mapped[int | None] = mapped_column(ForeignKey("billing_registry_imports.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_code: Mapped[str | None] = mapped_column(String(32))
    resolved_by: Mapped[str | None] = mapped_column(String(64))
