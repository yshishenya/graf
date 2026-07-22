from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from twobrain_rec_server.db.base import Base


class SummaryTemplate(Base):
    __tablename__ = "summary_templates"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "owner_user_id",
            "template_key",
            "version",
            name="uq_summary_templates_owner_key_version",
        ),
        Index("ix_summary_templates_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    template_key: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    purpose: Mapped[str] = mapped_column(String(240), nullable=False)
    sections_json: Mapped[list] = mapped_column(JSON, default=list)
    output_language: Mapped[str] = mapped_column(String(16), nullable=False)
    detail_level: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MeetingOutcomeSet(Base):
    __tablename__ = "meeting_outcome_sets"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "meeting_id",
            "media_revision_id",
            "processing_result_id",
            "generator_version",
            name="uq_meeting_outcome_sets_current_generator",
        ),
        Index("ix_meeting_outcome_sets_meeting_status", "workspace_id", "meeting_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
    processing_result_id: Mapped[UUID] = mapped_column(ForeignKey("processing_results.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="queued")
    summary_state: Mapped[str] = mapped_column(String(64), default="processing")
    key_points_state: Mapped[str] = mapped_column(String(64), default="processing")
    decisions_state: Mapped[str] = mapped_column(String(64), default="processing")
    action_items_state: Mapped[str] = mapped_column(String(64), default="processing")
    followups_state: Mapped[str] = mapped_column(String(64), default="processing")
    risks_state: Mapped[str] = mapped_column(String(64), default="processing")
    questions_state: Mapped[str] = mapped_column(String(64), default="processing")
    evidence_state: Mapped[str] = mapped_column(String(64), default="processing")
    source_kind: Mapped[str] = mapped_column(String(64), default="extractive_generator")
    generator_kind: Mapped[str] = mapped_column(String(64), default="deterministic_extractive")
    generator_version: Mapped[str] = mapped_column(String(120), nullable=False)
    source_result_hash: Mapped[str | None] = mapped_column(String(128))
    content_hash: Mapped[str | None] = mapped_column(String(128))
    template_id: Mapped[UUID | None] = mapped_column(ForeignKey("summary_templates.id"))
    template_key: Mapped[str | None] = mapped_column(String(120))
    template_version: Mapped[int | None] = mapped_column(Integer)
    output_language: Mapped[str | None] = mapped_column(String(16))
    detail_level: Mapped[str | None] = mapped_column(String(32))
    revision_state: Mapped[str | None] = mapped_column(String(32))
    requested_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    accepted_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_identities.id"))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_outcome_set_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("meeting_outcome_sets.id")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    failure_reason: Mapped[str | None] = mapped_column(String(240))
    failure_source: Mapped[str | None] = mapped_column(String(64))
    lifecycle_state: Mapped[str] = mapped_column(String(64), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class MeetingOutcomeItem(Base):
    __tablename__ = "meeting_outcome_items"
    __table_args__ = (
        UniqueConstraint(
            "outcome_set_id",
            "category",
            "sequence",
            name="uq_meeting_outcome_items_set_category_sequence",
        ),
        Index("ix_meeting_outcome_items_set_category_sequence", "outcome_set_id", "category", "sequence"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    outcome_set_id: Mapped[UUID] = mapped_column(ForeignKey("meeting_outcome_sets.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(64), default="available")
    text: Mapped[str | None] = mapped_column(String)
    owner_text: Mapped[str | None] = mapped_column(String(240))
    due_date_text: Mapped[str | None] = mapped_column(String(120))
    truth_label: Mapped[str] = mapped_column(String(64), default="supported")
    source_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MeetingOutcomeGenerationAttempt(Base):
    __tablename__ = "meeting_outcome_generation_attempts"
    __table_args__ = (
        Index(
            "ix_meeting_outcome_generation_attempts_input",
            "workspace_id",
            "meeting_id",
            "processing_result_id",
            "generator_version",
        ),
        UniqueConstraint("candidate_id", name="uq_generation_attempt_candidate_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    meeting_id: Mapped[UUID] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    media_revision_id: Mapped[UUID | None] = mapped_column(ForeignKey("media_revisions.id"))
    processing_result_id: Mapped[UUID] = mapped_column(ForeignKey("processing_results.id"), nullable=False)
    outcome_set_id: Mapped[UUID | None] = mapped_column(ForeignKey("meeting_outcome_sets.id"))
    status: Mapped[str] = mapped_column(String(64), default="queued")
    provider_kind: Mapped[str] = mapped_column(String(64), default="deterministic_extractive")
    generator_version: Mapped[str] = mapped_column(String(120), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    failure_reason: Mapped[str | None] = mapped_column(String(240))
    failure_source: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    candidate_id: Mapped[UUID | None] = mapped_column()
    source_result_id: Mapped[UUID | None] = mapped_column(ForeignKey("processing_results.id"))
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_identities.id")
    )
    template_id: Mapped[UUID | None] = mapped_column(ForeignKey("summary_templates.id"))
    template_key: Mapped[str | None] = mapped_column(String(120))
    template_version: Mapped[int | None] = mapped_column(Integer)
    output_language: Mapped[str | None] = mapped_column(String(16))
    detail_level: Mapped[str | None] = mapped_column(String(32))
    prompt_name: Mapped[str | None] = mapped_column(String(240))
    prompt_version: Mapped[int | None] = mapped_column(Integer)
    prompt_source: Mapped[str | None] = mapped_column(String(64))
    prompt_definition: Mapped[dict | list | str | None] = mapped_column(JSON)
    prompt_config: Mapped[dict | None] = mapped_column(JSON)
    prompt_hash: Mapped[str | None] = mapped_column(String(64))
    output_schema_version: Mapped[str | None] = mapped_column(String(64))
    model_route: Mapped[str | None] = mapped_column(String(128))
    model_parameters: Mapped[dict | None] = mapped_column(JSON)
    workflow_id: Mapped[str | None] = mapped_column(String(240))
    workflow_run_id: Mapped[str | None] = mapped_column(String(240))
    langfuse_trace_id: Mapped[str | None] = mapped_column(String(64))
    temporal_transcript_hash: Mapped[str | None] = mapped_column(String(64))
    temporal_transcript_chunk_count: Mapped[int | None] = mapped_column(Integer)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_code: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class GenerationCall(Base):
    __tablename__ = "generation_calls"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "provider_attempt",
            "call_sequence",
            name="uq_generation_calls_candidate_provider_sequence",
        ),
        UniqueConstraint("observation_id", name="uq_generation_calls_observation_id"),
        Index("ix_generation_calls_workspace_export", "workspace_id", "export_status"),
        Index("ix_generation_calls_meeting_id", "meeting_id"),
        Index("ix_generation_calls_candidate_id", "candidate_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    # Deliberately opaque parent correlations: meeting/candidate deletion cannot cascade here.
    meeting_id: Mapped[UUID] = mapped_column(nullable=False)
    candidate_id: Mapped[UUID] = mapped_column(nullable=False)
    provider_attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    call_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    observation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    call_state: Mapped[str] = mapped_column(String(32), nullable=False, default="reserved")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_provider: Mapped[str | None] = mapped_column(String(128))
    actual_model: Mapped[str | None] = mapped_column(String(128))
    provider_request_id: Mapped[str | None] = mapped_column(String(240))
    token_usage: Mapped[dict | None] = mapped_column(JSON)
    cost_details: Mapped[dict | None] = mapped_column(JSON)
    request_json: Mapped[dict | None] = mapped_column(JSON)
    transcript_text: Mapped[str | None] = mapped_column(String)
    raw_response_json: Mapped[dict | list | str | None] = mapped_column(JSON)
    validated_result_json: Mapped[dict | list | None] = mapped_column(JSON)
    request_hash: Mapped[str | None] = mapped_column(String(64))
    transcript_hash: Mapped[str | None] = mapped_column(String(64))
    raw_response_hash: Mapped[str | None] = mapped_column(String(64))
    validated_result_hash: Mapped[str | None] = mapped_column(String(64))
    export_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    export_attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_export_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_export_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    export_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_export_error_code: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PromptOptimizationRun(Base):
    __tablename__ = "prompt_optimization_runs"
    __table_args__ = (
        Index("ix_prompt_optimization_runs_prompt_status", "prompt_name", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    deployment_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="global")
    initiated_by_actor_id: Mapped[str] = mapped_column(String(240), nullable=False)
    prompt_name: Mapped[str] = mapped_column(String(240), nullable=False)
    source_prompt_version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    train_dataset_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    development_dataset_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    heldout_dataset_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    dataset_manifest_hashes: Mapped[dict] = mapped_column(JSON, default=dict)
    optimizer_version: Mapped[str] = mapped_column(String(64), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_versions: Mapped[dict] = mapped_column(JSON, default=dict)
    reflection_prompt_name: Mapped[str] = mapped_column(String(240), nullable=False)
    reflection_prompt_version: Mapped[int] = mapped_column(Integer, nullable=False)
    reflection_config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    judge_prompt_refs: Mapped[list] = mapped_column(JSON, default=list)
    budget: Mapped[dict] = mapped_column(JSON, default=dict)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(240), nullable=False, unique=True)
    workflow_run_id: Mapped[str | None] = mapped_column(String(240))
    run_artifact_ref: Mapped[str | None] = mapped_column(String(500))
    checkpoint_revision: Mapped[int | None] = mapped_column(Integer)
    checkpoint_hash: Mapped[str | None] = mapped_column(String(64))
    checkpoint_schema_version: Mapped[str | None] = mapped_column(String(64))
    candidate_prompt_version: Mapped[int | None] = mapped_column(Integer)
    candidate_prompt_hash: Mapped[str | None] = mapped_column(String(64))
    candidate_config_hash: Mapped[str | None] = mapped_column(String(64))
    aggregate_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    rollback_prompt_version: Mapped[int] = mapped_column(Integer, nullable=False)
    approval_state: Mapped[str] = mapped_column(String(32), nullable=False, default="not_requested")
    approval_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_action_id: Mapped[UUID | None] = mapped_column(unique=True)
    approved_by_actor_id: Mapped[str | None] = mapped_column(String(240))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    failure_code: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PromptOptimizationCallLedger(Base):
    __tablename__ = "prompt_optimization_call_ledger"
    __table_args__ = (
        Index("ix_prompt_optimization_call_ledger_run_status", "run_id", "status"),
    )

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("prompt_optimization_runs.id", ondelete="CASCADE"), primary_key=True
    )
    call_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    phase: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[int] = mapped_column(Integer, nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model_route: Mapped[str] = mapped_column(String(128), nullable=False)
    reserved_token_ceiling: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_cost_ceiling: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="reserved")
    result_artifact_ref: Mapped[str | None] = mapped_column(String(500))
    actual_input_tokens: Mapped[int | None] = mapped_column(Integer)
    actual_output_tokens: Mapped[int | None] = mapped_column(Integer)
    actual_cost: Mapped[str | None] = mapped_column(String(64))
    activity_attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_fence: Mapped[UUID] = mapped_column(nullable=False)
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
