from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
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
from twobrain_rec_server.normalization.statuses import CANONICAL_PROFILE_VERSION, VALIDATION_VERSION


class PlaybackBackfillRun(Base):
    __tablename__ = "playback_backfill_runs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "profile_version",
            name="uq_playback_backfill_runs_workspace_profile",
        ),
        Index("ix_playback_backfill_runs_state_updated", "state", "updated_at", "id"),
        CheckConstraint(
            "(cursor_created_at is null) = (cursor_media_revision_id is null)",
            name="playback_backfill_cursor_pair",
        ),
        CheckConstraint(
            "profile_version = 'review_m4a_aac_lc_48k_mono_64k_v1'",
            name="playback_backfill_profile_allowed",
        ),
        CheckConstraint(
            "state in ('inventory_pending', 'inventory_running', 'inventory_complete', "
            "'dispatching', 'complete', 'blocked')",
            name="playback_backfill_state_allowed",
        ),
        CheckConstraint(
            """
            evaluated_count >= 0
            and preserve_valid_count >= 0
            and validate_candidate_count >= 0
            and normalize_source_count >= 0
            and unavailable_source_count >= 0
            and ready_count >= 0
            and terminal_count >= 0
            and cancelled_count >= 0
            """,
            name="playback_backfill_nonnegative_counters",
        ),
        CheckConstraint(
            """
            (state != 'inventory_running' or inventory_started_at is not null)
            and (state not in ('inventory_complete', 'dispatching', 'complete')
                 or inventory_completed_at is not null)
            and (state != 'complete' or completed_at is not null)
            and (state != 'blocked' or safe_block_reason is not null)
            """,
            name="playback_backfill_state_facts",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    profile_version: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default=CANONICAL_PROFILE_VERSION,
    )
    state: Mapped[str] = mapped_column(String(64), nullable=False, default="inventory_pending")
    cursor_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cursor_media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
    evaluated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    preserve_valid_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validate_candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    normalize_source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unavailable_source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ready_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    terminal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancelled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    safe_block_reason: Mapped[str | None] = mapped_column(String(120))
    inventory_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    inventory_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class PlaybackNormalizationJob(Base):
    __tablename__ = "playback_normalization_jobs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "media_revision_id",
            "profile_version",
            name="uq_playback_normalization_jobs_workspace_revision_profile",
        ),
        Index(
            "ix_playback_normalization_jobs_due_pickup",
            "state",
            "next_attempt_at",
            "priority_class",
            "created_at",
            "id",
        ),
        Index(
            "ix_playback_normalization_jobs_workspace_meeting_state",
            "workspace_id",
            "meeting_id",
            "state",
        ),
        Index(
            "ix_playback_normalization_jobs_expired_lease",
            "state",
            "lease_expires_at",
            "id",
        ),
        CheckConstraint(
            "attempt_count >= 0 and cycle_attempt_count between 0 and 4 and retry_cycle_count >= 0",
            name="playback_normalization_job_nonnegative_counters",
        ),
        CheckConstraint(
            "profile_version = 'review_m4a_aac_lc_48k_mono_64k_v1' "
            "and validation_version = 'playback_validator_v1'",
            name="playback_normalization_job_profile_allowed",
        ),
        CheckConstraint(
            "state in ('queued', 'running', 'publishing', 'retry_wait', 'ready', "
            "'terminal', 'cancelled')",
            name="playback_normalization_job_state_allowed",
        ),
        CheckConstraint(
            "trigger_kind in ('finalize', 'reconcile', 'legacy_backfill') "
            "and priority_class in ('new_ingest', 'due_retry', 'legacy_backfill') "
            "and planned_action in ('validate_candidate', 'preserve_valid', "
            "'normalize_source', 'unavailable_source')",
            name="playback_normalization_job_kind_allowed",
        ),
        CheckConstraint(
            "length(source_fingerprint_sha256) = 64",
            name="playback_normalization_job_fingerprint_length",
        ),
        CheckConstraint(
            "(state in ('queued', 'running', 'publishing', 'ready') and reason_code is null) "
            "or state in ('retry_wait', 'terminal', 'cancelled')",
            name="playback_normalization_job_reason_state",
        ),
        CheckConstraint(
            "trigger_kind != 'legacy_backfill' or backfill_run_id is not null",
            name="playback_normalization_job_backfill_link",
        ),
        CheckConstraint(
            """
            state != 'ready'
            or (
                canonical_track_artifact_id is not null
                and ready_at is not null
                and reason_code is null
            )
            """,
            name="playback_normalization_job_ready_facts",
        ),
        CheckConstraint(
            """
            state != 'retry_wait'
            or (
                next_attempt_at is not null
                and reason_code in (
                    'storage_unavailable', 'database_unavailable', 'temporal_unavailable',
                    'temporary_storage_unavailable', 'worker_interrupted',
                    'dependency_unavailable', 'normalization_timeout',
                    'publish_interrupted', 'generated_output_invalid'
                )
            )
            """,
            name="playback_normalization_job_retry_facts",
        ),
        CheckConstraint(
            """
            state != 'terminal'
            or (
                terminal_at is not null
                and reason_code in (
                    'empty_source', 'unsupported_container', 'unsupported_codec',
                    'encrypted_media', 'corrupt_source', 'no_audio',
                    'ambiguous_audio_tracks', 'stream_limit_exceeded',
                    'duration_limit_exceeded', 'source_size_limit_exceeded',
                    'source_missing', 'source_mismatch', 'storage_capacity_exceeded'
                )
            )
            """,
            name="playback_normalization_job_terminal_facts",
        ),
        CheckConstraint(
            """
            state != 'cancelled'
            or (
                cancelled_at is not null
                and reason_code in (
                    'meeting_deleting', 'meeting_deleted', 'audio_purged',
                    'revision_superseded'
                )
            )
            """,
            name="playback_normalization_job_cancelled_facts",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    requested_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_identities.id"), nullable=False
    )
    source_device_id: Mapped[UUID] = mapped_column(
        ForeignKey("registered_devices.id"), nullable=False
    )
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    media_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_revisions.id"), nullable=False
    )
    profile_version: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default=CANONICAL_PROFILE_VERSION,
    )
    validation_version: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default=VALIDATION_VERSION,
    )
    trigger_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    priority_class: Mapped[str] = mapped_column(String(64), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    source_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    backfill_run_id: Mapped[UUID | None] = mapped_column(ForeignKey("playback_backfill_runs.id"))
    planned_action: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(64), nullable=False, default="queued")
    reason_code: Mapped[str | None] = mapped_column(String(120))
    workflow_id: Mapped[str] = mapped_column(String(240), nullable=False)
    workflow_run_id: Mapped[str | None] = mapped_column(String(240))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cycle_attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_cycle_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner_sha256: Mapped[str | None] = mapped_column(String(64))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canonical_track_artifact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("track_artifacts.id"),
        unique=True,
    )
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terminal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class PlaybackNormalizationAttempt(Base):
    __tablename__ = "playback_normalization_attempts"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "attempt_number",
            name="uq_playback_normalization_attempts_job_number",
        ),
        Index(
            "ix_playback_normalization_attempts_workspace_meeting_state",
            "workspace_id",
            "meeting_id",
            "state",
        ),
        Index(
            "ix_playback_normalization_attempts_cleanup_recovery",
            "state",
            "updated_at",
            "id",
        ),
        CheckConstraint(
            """
            attempt_number >= 1
            and cycle_number >= 1
            and source_stream_count >= 0
            and source_audio_stream_count >= 0
            and source_audio_stream_count <= source_stream_count
            and (selected_stream_index is null or selected_stream_index >= 0)
            """,
            name="playback_normalization_attempt_number_counts",
        ),
        CheckConstraint(
            "state in ('local_preparing', 'uploaded', 'published', "
            "'cleanup_pending', 'cleaned', 'purged')",
            name="playback_normalization_attempt_state_allowed",
        ),
        CheckConstraint(
            "derivation_kind in ('uploaded_candidate', 'source_byte_copy', "
            "'lossless_faststart_remux', 'single_source_transcode', "
            "'dual_source_mix_transcode', 'legacy_unvalidated')",
            name="playback_normalization_attempt_derivation_allowed",
        ),
        CheckConstraint(
            "(source_duration_ms is null or source_duration_ms > 0) "
            "and (output_duration_ms is null or output_duration_ms > 0) "
            "and (output_byte_length is null or output_byte_length > 0) "
            "and (output_sha256 is null or length(output_sha256) = 64) "
            "and (output_audio_bit_rate is null or output_audio_bit_rate > 0) "
            "and (output_sample_rate_hz is null or output_sample_rate_hz > 0) "
            "and (output_channel_count is null or output_channel_count > 0)",
            name="playback_normalization_attempt_positive_facts",
        ),
        CheckConstraint(
            "state != 'cleaned' or cleaned_at is not null",
            name="playback_normalization_attempt_cleanup_facts",
        ),
        CheckConstraint(
            """
            state not in ('uploaded', 'published')
            or (output_byte_length > 0 and output_sha256 is not null and uploaded_at is not null)
            """,
            name="playback_normalization_attempt_uploaded_facts",
        ),
        CheckConstraint(
            """
            state != 'published'
            or (
                published_track_artifact_id is not null
                and published_at is not null
                and output_duration_ms > 0
                and output_audio_bit_rate > 0
                and output_sample_rate_hz = 48000
                and output_channel_count = 1
                and moov_before_mdat = true
                and fragmented = false
                and full_decode_passed = true
            )
            """,
            name="playback_normalization_attempt_published_facts",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    media_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_revisions.id"), nullable=False
    )
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("playback_normalization_jobs.id"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(64), nullable=False, default="local_preparing")
    storage_object_key: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    published_track_artifact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("track_artifacts.id"),
        unique=True,
    )
    derivation_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_stream_index: Mapped[int | None] = mapped_column(Integer)
    source_stream_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_audio_stream_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    output_duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    output_byte_length: Mapped[int | None] = mapped_column(BigInteger)
    output_sha256: Mapped[str | None] = mapped_column(String(64))
    output_audio_bit_rate: Mapped[int | None] = mapped_column(Integer)
    output_sample_rate_hz: Mapped[int | None] = mapped_column(Integer)
    output_channel_count: Mapped[int | None] = mapped_column(Integer)
    moov_before_mdat: Mapped[bool | None] = mapped_column(Boolean)
    fragmented: Mapped[bool | None] = mapped_column(Boolean)
    full_decode_passed: Mapped[bool | None] = mapped_column(Boolean)
    cleanup_reason: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cleaned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
