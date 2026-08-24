from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class ProcessingWorkflow(Base):
    __tablename__ = "processing_workflows"
    __table_args__ = (
        Index(
            "uq_processing_workflows_active_revision",
            "workspace_id",
            "meeting_id",
            "media_revision_id",
            "purpose",
            "source_fingerprint",
            unique=True,
            postgresql_where=(
                "media_revision_id is not null and status not in "
                "('processed', 'blocked', 'failed_terminal', 'canceled')"
            ),
        ),
        Index(
            "uq_processing_workflows_active_legacy",
            "workspace_id",
            "meeting_id",
            "purpose",
            "source_fingerprint",
            unique=True,
            postgresql_where=(
                "media_revision_id is null and status not in "
                "('processed', 'blocked', 'failed_terminal', 'canceled')"
            ),
        ),
        Index(
            "uq_processing_workflows_active_revision_missing_source",
            "workspace_id",
            "meeting_id",
            "media_revision_id",
            "purpose",
            unique=True,
            postgresql_where=(
                "media_revision_id is not null and source_fingerprint is null and status not in "
                "('processed', 'blocked', 'failed_terminal', 'canceled')"
            ),
        ),
        Index(
            "uq_processing_workflows_active_legacy_missing_source",
            "workspace_id",
            "meeting_id",
            "purpose",
            unique=True,
            postgresql_where=(
                "media_revision_id is null and source_fingerprint is null and status not in "
                "('processed', 'blocked', 'failed_terminal', 'canceled')"
            ),
        ),
        UniqueConstraint("workflow_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(240), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False, default="transcription")
    # ``archive_audio=False`` is the persisted no-archive admission.  The
    # transient timestamps live on the workflow row so maintenance can purge
    # deterministically after worker crashes without a second entity.
    archive_audio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    transient_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_applicable"
    )
    transient_admitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transient_terminal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transient_purge_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transient_hard_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transient_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_fingerprint: Mapped[str | None] = mapped_column(String(128))
    deletion_epoch_at_start: Mapped[int | None] = mapped_column(BigInteger)
    workflow_run_id: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(64), default="not_submitted")
    attempt_ordinal: Mapped[int] = mapped_column(Integer, default=1)
    stage: Mapped[str | None] = mapped_column(String(32))
    retry_class: Mapped[str | None] = mapped_column(String(32))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_source: Mapped[str | None] = mapped_column(String(32))
    schedule_generation: Mapped[int] = mapped_column(Integer, default=0)
    manual_command_version: Mapped[int] = mapped_column(Integer, default=0)
    manual_claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    manual_claimed_by: Mapped[str | None] = mapped_column(String(32))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reason_code: Mapped[str | None] = mapped_column(String(120))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class MediaScribeJob(Base):
    __tablename__ = "mediascribe_jobs"
    __table_args__ = (
        Index(
            "uq_mediascribe_jobs_workspace_revision_key",
            "workspace_id",
            "media_revision_id",
            "idempotency_key",
            unique=True,
            postgresql_where="media_revision_id is not null and idempotency_key is not null",
        ),
        Index(
            "uq_mediascribe_jobs_workspace_legacy_key",
            "workspace_id",
            "meeting_id",
            "idempotency_key",
            unique=True,
            postgresql_where="media_revision_id is null and idempotency_key is not null",
        ),
        UniqueConstraint(
            "workspace_id", "external_job_id", name="uq_mediascribe_jobs_workspace_external_job"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    processing_workflow_id: Mapped[UUID] = mapped_column(
        ForeignKey("processing_workflows.id"), nullable=False
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(240))
    source_fingerprint: Mapped[str | None] = mapped_column(String(128))
    deletion_epoch_at_start: Mapped[int | None] = mapped_column(BigInteger)
    external_job_id: Mapped[str | None] = mapped_column(String(240))
    submission_claim_token: Mapped[str | None] = mapped_column(String(64))
    submission_claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), default="not_submitted")
    mic_track_artifact_id: Mapped[UUID | None] = mapped_column(ForeignKey("track_artifacts.id"))
    incoming_track_artifact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("track_artifacts.id")
    )
    source_track_artifact_id: Mapped[UUID | None] = mapped_column(ForeignKey("track_artifacts.id"))
    request_mode: Mapped[str] = mapped_column(String(64), default="dual_track")
    diarize: Mapped[bool] = mapped_column(Boolean, default=True)
    summarize: Mapped[bool] = mapped_column(Boolean, default=False)
    speaker_count_mode: Mapped[str | None] = mapped_column(String(32))
    num_speakers: Mapped[int | None] = mapped_column(Integer)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_error_code: Mapped[str | None] = mapped_column(String(120))
    last_error_message: Mapped[str | None] = mapped_column(String(500))
    provider_status: Mapped[str | None] = mapped_column(String(64))
    provider_queue_state: Mapped[str | None] = mapped_column(String(64))
    provider_attempt: Mapped[int | None] = mapped_column(Integer)
    provider_max_attempts: Mapped[int | None] = mapped_column(Integer)
    provider_next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_after_seconds: Mapped[int | None] = mapped_column(Integer)
    last_request_id: Mapped[str | None] = mapped_column(String(128))
    provider_location: Mapped[str | None] = mapped_column(String(512))
    api_contract_version: Mapped[str | None] = mapped_column(String(32))
    provider_build: Mapped[str | None] = mapped_column(String(128))
    request_fingerprint: Mapped[str | None] = mapped_column(String(128))
    deletion_state: Mapped[str | None] = mapped_column(String(32))
    deletion_status_url: Mapped[str | None] = mapped_column(String(512))
    deletion_receipt_id: Mapped[str | None] = mapped_column(String(240))
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletion_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProcessingResult(Base):
    __tablename__ = "processing_results"
    __table_args__ = (
        UniqueConstraint("workspace_id", "mediascribe_job_id", "result_version"),
        Index(
            "uq_processing_results_run_source_hash",
            "workspace_id",
            "processing_workflow_id",
            "source_result_hash",
            unique=True,
            postgresql_where="source_result_hash is not null and processing_workflow_id is not null",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    mediascribe_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("mediascribe_jobs.id"), nullable=False
    )
    processing_workflow_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("processing_workflows.id")
    )
    deletion_epoch_at_start: Mapped[int | None] = mapped_column(BigInteger)
    result_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(64), default="importing")
    transcript_status: Mapped[str] = mapped_column(String(64), default="unavailable")
    diarization_status: Mapped[str] = mapped_column(String(64), default="unavailable")
    summary_status: Mapped[str] = mapped_column(String(64), default="not_requested")
    language: Mapped[str | None] = mapped_column(String(32))
    segment_count: Mapped[int] = mapped_column(Integer, default=0)
    diarization_segment_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_reason: Mapped[str | None] = mapped_column(String(240))
    failure_source: Mapped[str | None] = mapped_column(String(64))
    source_result_hash: Mapped[str | None] = mapped_column(String(128))
    provenance_json: Mapped[dict | None] = mapped_column(JSON)
    overlaps_json: Mapped[list | None] = mapped_column(JSON)
    acoustic_turns_json: Mapped[list | None] = mapped_column(JSON)
    downloads_json: Mapped[dict | None] = mapped_column(JSON)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (UniqueConstraint("processing_result_id", "sequence"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    processing_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("processing_results.id"), nullable=False
    )
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    start_seconds: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    end_seconds: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    source_role: Mapped[str] = mapped_column(String(32), nullable=False)
    source_role_original: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiarizationSegment(Base):
    __tablename__ = "diarization_segments"
    __table_args__ = (UniqueConstraint("processing_result_id", "sequence"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    processing_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("processing_results.id"), nullable=False
    )
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    start_seconds: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    end_seconds: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    speaker_label: Mapped[str] = mapped_column(String(120), nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    source_role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MeetingSpeakerName(Base):
    __tablename__ = "meeting_speaker_names"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "meeting_id",
            "speaker_key",
            name="uq_meeting_speaker_names_workspace_meeting_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    speaker_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    updated_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_identities.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProcessingAuditEvent(Base):
    __tablename__ = "processing_audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID | None] = mapped_column(ForeignKey("meetings.id"))
    processing_workflow_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("processing_workflows.id")
    )
    mediascribe_job_id: Mapped[UUID | None] = mapped_column(ForeignKey("mediascribe_jobs.id"))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProcessingDependencyState(Base):
    __tablename__ = "processing_dependency_states"
    __table_args__ = (
        Index(
            "uq_processing_dependency_revision",
            "workspace_id",
            "meeting_id",
            "media_revision_id",
            "dependency",
            unique=True,
            postgresql_where="media_revision_id is not null",
        ),
        Index(
            "uq_processing_dependency_legacy",
            "workspace_id",
            "meeting_id",
            "dependency",
            unique=True,
            postgresql_where="media_revision_id is null",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    dependency: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(64), default="not_contacted")
    external_reference: Mapped[str | None] = mapped_column(String(240))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
