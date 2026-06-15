from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
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
        UniqueConstraint("workspace_id", "meeting_id"),
        UniqueConstraint("workflow_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(240), nullable=False)
    workflow_run_id: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(64), default="not_submitted")
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
        UniqueConstraint("workspace_id", "meeting_id", name="uq_mediascribe_jobs_workspace_meeting"),
        UniqueConstraint("workspace_id", "external_job_id", name="uq_mediascribe_jobs_workspace_external_job"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    processing_workflow_id: Mapped[UUID] = mapped_column(ForeignKey("processing_workflows.id"), nullable=False)
    external_job_id: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(64), default="not_submitted")
    mic_track_artifact_id: Mapped[UUID] = mapped_column(ForeignKey("track_artifacts.id"), nullable=False)
    incoming_track_artifact_id: Mapped[UUID] = mapped_column(ForeignKey("track_artifacts.id"), nullable=False)
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


class ProcessingResult(Base):
    __tablename__ = "processing_results"
    __table_args__ = (UniqueConstraint("workspace_id", "mediascribe_job_id", "result_version"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    mediascribe_job_id: Mapped[UUID] = mapped_column(ForeignKey("mediascribe_jobs.id"), nullable=False)
    result_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(64), default="importing")
    transcript_status: Mapped[str] = mapped_column(String(64), default="unavailable")
    diarization_status: Mapped[str] = mapped_column(String(64), default="unavailable")
    summary_status: Mapped[str] = mapped_column(String(64), default="not_requested")
    language: Mapped[str | None] = mapped_column(String(32))
    segment_count: Mapped[int] = mapped_column(Integer, default=0)
    diarization_segment_count: Mapped[int] = mapped_column(Integer, default=0)
    source_result_hash: Mapped[str | None] = mapped_column(String(128))
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
    processing_result_id: Mapped[UUID] = mapped_column(ForeignKey("processing_results.id"), nullable=False)
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
    processing_result_id: Mapped[UUID] = mapped_column(ForeignKey("processing_results.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    start_seconds: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    end_seconds: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    speaker_label: Mapped[str] = mapped_column(String(120), nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    source_role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProcessingAuditEvent(Base):
    __tablename__ = "processing_audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID | None] = mapped_column(ForeignKey("meetings.id"))
    processing_workflow_id: Mapped[UUID | None] = mapped_column(ForeignKey("processing_workflows.id"))
    mediascribe_job_id: Mapped[UUID | None] = mapped_column(ForeignKey("mediascribe_jobs.id"))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProcessingDependencyState(Base):
    __tablename__ = "processing_dependency_states"
    __table_args__ = (UniqueConstraint("workspace_id", "meeting_id", "dependency"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
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
