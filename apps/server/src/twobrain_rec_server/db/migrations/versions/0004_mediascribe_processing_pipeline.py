"""mediascribe processing pipeline

Revision ID: 0004_mediascribe_processing_pipeline
Revises: 0003_federated_auth_foundation
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_mediascribe_processing_pipeline"
down_revision: str | None = "0003_federated_auth_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "processing_workflows",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("workflow_id", sa.String(length=240), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=240)),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="not_submitted"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reason_code", sa.String(length=120)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "meeting_id"),
        sa.UniqueConstraint("workflow_id"),
    )
    op.create_table(
        "mediascribe_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("processing_workflow_id", sa.Uuid(), sa.ForeignKey("processing_workflows.id"), nullable=False),
        sa.Column("external_job_id", sa.String(length=240)),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="not_submitted"),
        sa.Column("mic_track_artifact_id", sa.Uuid(), sa.ForeignKey("track_artifacts.id"), nullable=False),
        sa.Column("incoming_track_artifact_id", sa.Uuid(), sa.ForeignKey("track_artifacts.id"), nullable=False),
        sa.Column("request_mode", sa.String(length=64), nullable=False, server_default="dual_track"),
        sa.Column("diarize", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("summarize", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("speaker_count_mode", sa.String(length=32)),
        sa.Column("num_speakers", sa.Integer()),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("last_polled_at", sa.DateTime(timezone=True)),
        sa.Column("ready_at", sa.DateTime(timezone=True)),
        sa.Column("failed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_error_code", sa.String(length=120)),
        sa.Column("last_error_message", sa.String(length=500)),
        sa.UniqueConstraint("workspace_id", "meeting_id", name="uq_mediascribe_jobs_workspace_meeting"),
        sa.UniqueConstraint("workspace_id", "external_job_id", name="uq_mediascribe_jobs_workspace_external_job"),
    )
    op.create_table(
        "processing_results",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("mediascribe_job_id", sa.Uuid(), sa.ForeignKey("mediascribe_jobs.id"), nullable=False),
        sa.Column("result_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="importing"),
        sa.Column("transcript_status", sa.String(length=64), nullable=False, server_default="unavailable"),
        sa.Column("diarization_status", sa.String(length=64), nullable=False, server_default="unavailable"),
        sa.Column("summary_status", sa.String(length=64), nullable=False, server_default="not_requested"),
        sa.Column("language", sa.String(length=32)),
        sa.Column("segment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("diarization_segment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_result_hash", sa.String(length=128)),
        sa.Column("imported_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "mediascribe_job_id", "result_version"),
    )
    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("processing_result_id", sa.Uuid(), sa.ForeignKey("processing_results.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("start_seconds", sa.Numeric(12, 3), nullable=False),
        sa.Column("end_seconds", sa.Numeric(12, 3), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("source_role", sa.String(length=32), nullable=False),
        sa.Column("source_role_original", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("processing_result_id", "sequence"),
    )
    op.create_table(
        "diarization_segments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("processing_result_id", sa.Uuid(), sa.ForeignKey("processing_results.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("start_seconds", sa.Numeric(12, 3), nullable=False),
        sa.Column("end_seconds", sa.Numeric(12, 3), nullable=False),
        sa.Column("speaker_label", sa.String(length=120), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("source_role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("processing_result_id", "sequence"),
    )
    op.create_table(
        "processing_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id")),
        sa.Column("processing_workflow_id", sa.Uuid(), sa.ForeignKey("processing_workflows.id")),
        sa.Column("mediascribe_job_id", sa.Uuid(), sa.ForeignKey("mediascribe_jobs.id")),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "processing_dependency_states",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("dependency", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="not_contacted"),
        sa.Column("external_reference", sa.String(length=240)),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "meeting_id", "dependency"),
    )


def downgrade() -> None:
    for table_name in [
        "processing_dependency_states",
        "processing_audit_events",
        "diarization_segments",
        "transcript_segments",
        "processing_results",
        "mediascribe_jobs",
        "processing_workflows",
    ]:
        op.drop_table(table_name)
