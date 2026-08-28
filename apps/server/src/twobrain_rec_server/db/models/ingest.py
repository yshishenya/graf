from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
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


class MediaRevision(Base):
    __tablename__ = "media_revisions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "meeting_id",
            "revision_number",
            name="uq_media_revisions_workspace_meeting_revision",
        ),
        UniqueConstraint(
            "workspace_id",
            "meeting_id",
            "local_media_revision_id",
            name="uq_media_revisions_workspace_meeting_local_revision",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    local_media_revision_id: Mapped[str] = mapped_column(String(300), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_kind: Mapped[str] = mapped_column(
        String(64), nullable=False, default="initial_recording"
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending_upload")
    manifest_sha256: Mapped[str | None] = mapped_column(String(64))
    track_sha256_by_role: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    immutable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UploadSession(Base):
    __tablename__ = "upload_sessions"
    __table_args__ = (
        Index(
            "ix_upload_sessions_processing_dispatch_recovery",
            "finalized_at",
            "workspace_id",
            "meeting_id",
            "media_revision_id",
            postgresql_where=(
                "status = 'finalized' and processing_status = 'starting' "
                "and media_revision_id is not null"
            ),
        ),
        Index(
            "ix_upload_sessions_transient_hard_due",
            "finalized_at",
            "workspace_id",
            "meeting_id",
            "media_revision_id",
            postgresql_where=(
                "archive_audio = false and status = 'finalized' and media_revision_id is not null"
            ),
        ),
        Index(
            "ix_upload_sessions_transient_revision_custody",
            "workspace_id",
            "meeting_id",
            "media_revision_id",
            postgresql_where=("status = 'finalized' and media_revision_id is not null"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    device_id: Mapped[UUID] = mapped_column(ForeignKey("registered_devices.id"), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_identities.id"), nullable=False
    )
    upload_strategy: Mapped[str] = mapped_column(String(64), default="server_mediated")
    status: Mapped[str] = mapped_column(String(64), default="pending")
    processing_status: Mapped[str] = mapped_column(String(64), default="not_submitted")
    # Explicit user choice.  Existing sessions remain archival by default;
    # transient/no-archive processing is persisted on this same upload row.
    archive_audio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(240))
    expected_track_roles: Mapped[list] = mapped_column(JSON, default=list)
    expected_track_sizes: Mapped[dict] = mapped_column(JSON, default=dict)
    max_package_bytes_snapshot: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_track_bytes_snapshot: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UploadPart(Base):
    __tablename__ = "upload_parts"
    __table_args__ = (UniqueConstraint("upload_session_id", "track_role", "part_number"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    upload_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("upload_sessions.id"), nullable=False
    )
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
    __table_args__ = (Index("ix_temporary_upload_objects_session", "upload_session_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    upload_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("upload_sessions.id"), nullable=False
    )
    media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    storage_object_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    byte_length: Mapped[int] = mapped_column(BigInteger, nullable=False)
    object_role: Mapped[str] = mapped_column(String(64), default="accepted_part")
    cleanup_status: Mapped[str] = mapped_column(String(64), default="pending")
    failure_reason: Mapped[str | None] = mapped_column(String(240))
    last_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TrackArtifact(Base):
    __tablename__ = "track_artifacts"
    __table_args__ = (
        CheckConstraint(
            """
            (
                normalization_profile_version is null
                and validated_at is null
                and source_fingerprint_sha256 is null
                and validation_version is null
            )
            or
            (
                normalization_profile_version = 'review_m4a_aac_lc_48k_mono_64k_v1'
                and validated_at is not null
                and source_fingerprint_sha256 is not null
                and validation_version = 'playback_validator_v1'
                and derivation_kind is not null
                and track_role = 'playback'
                and status = 'stored'
                and media_revision_id is not null
            )
            """,
            name="track_artifact_validation_bundle",
        ),
        CheckConstraint(
            "derivation_kind is null or track_role = 'playback'",
            name="track_artifact_derivation_role",
        ),
        Index(
            "uq_track_artifacts_canonical_playback",
            "workspace_id",
            "media_revision_id",
            unique=True,
            postgresql_where=text(
                "track_role = 'playback' and status = 'stored' "
                "and normalization_profile_version = "
                "'review_m4a_aac_lc_48k_mono_64k_v1' "
                "and validated_at is not null"
            ),
        ),
        Index(
            "ix_track_artifacts_workspace_meeting_role_status",
            "workspace_id",
            "meeting_id",
            "track_role",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
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
    normalization_profile_version: Mapped[str | None] = mapped_column(String(120))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    derivation_kind: Mapped[str | None] = mapped_column(String(64))
    source_fingerprint_sha256: Mapped[str | None] = mapped_column(String(64))
    validation_version: Mapped[str | None] = mapped_column(String(80))
    # Current v5 ``media`` and legacy ``microphone``/``system`` sources are
    # lifecycle-accounted but never customer-quota chargeable.  Playback
    # verification and transcript import are independent retention gates.
    source_lifecycle_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_source"
    )
    source_transcript_imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_playback_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_retention_policy_version: Mapped[str | None] = mapped_column(String(120))
    source_retention_purge_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ManifestSnapshot(Base):
    __tablename__ = "manifest_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IngestAuditEvent(Base):
    __tablename__ = "ingest_audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID | None] = mapped_column(ForeignKey("meetings.id"))
    media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
    upload_session_id: Mapped[UUID | None] = mapped_column(ForeignKey("upload_sessions.id"))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    device_id: Mapped[UUID | None] = mapped_column(ForeignKey("registered_devices.id"))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
