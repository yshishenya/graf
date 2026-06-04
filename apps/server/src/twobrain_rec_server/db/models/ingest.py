from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    device_id: Mapped[UUID] = mapped_column(ForeignKey("registered_devices.id"), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("user_identities.id"), nullable=False)
    upload_strategy: Mapped[str] = mapped_column(String(64), default="server_mediated")
    status: Mapped[str] = mapped_column(String(64), default="pending")
    idempotency_key: Mapped[str | None] = mapped_column(String(240))
    expected_tracks: Mapped[dict] = mapped_column(JSON, default=dict)
    max_package_bytes_snapshot: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_track_bytes_snapshot: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UploadPart(Base):
    __tablename__ = "upload_parts"
    __table_args__ = (UniqueConstraint("upload_session_id", "track_role", "part_number"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    upload_session_id: Mapped[UUID] = mapped_column(ForeignKey("upload_sessions.id"), nullable=False)
    track_role: Mapped[str] = mapped_column(String(64), nullable=False)
    part_number: Mapped[int] = mapped_column(Integer, nullable=False)
    byte_offset: Mapped[int] = mapped_column(BigInteger, nullable=False)
    byte_length: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_object_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="accepted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TemporaryUploadObject(Base):
    __tablename__ = "temporary_upload_objects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    upload_session_id: Mapped[UUID] = mapped_column(ForeignKey("upload_sessions.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    storage_object_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    byte_length: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cleanup_status: Mapped[str] = mapped_column(String(64), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TrackArtifact(Base):
    __tablename__ = "track_artifacts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    track_role: Mapped[str] = mapped_column(String(64), nullable=False)
    codec: Mapped[str] = mapped_column(String(120), nullable=False)
    sample_rate_hz: Mapped[int] = mapped_column(Integer, nullable=False)
    channel_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    byte_length: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_object_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="stored")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ManifestSnapshot(Base):
    __tablename__ = "manifest_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IngestAuditEvent(Base):
    __tablename__ = "ingest_audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID | None] = mapped_column(ForeignKey("meetings.id"))
    upload_session_id: Mapped[UUID | None] = mapped_column(ForeignKey("upload_sessions.id"))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    device_id: Mapped[UUID | None] = mapped_column(ForeignKey("registered_devices.id"))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
