"""Persist MediaScribe v1 lifecycle and user-visible recovery scheduling."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0078_processing_recovery"
down_revision: str | None = "0077_provider_unlink_xworkspace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    workflow_columns = (
        sa.Column("attempt_ordinal", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("stage", sa.String(length=32), nullable=True),
        sa.Column("retry_class", sa.String(length=32), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_source", sa.String(length=32), nullable=True),
        sa.Column("schedule_generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manual_command_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manual_claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("manual_claimed_by", sa.String(length=32), nullable=True),
    )
    job_columns = (
        sa.Column("provider_status", sa.String(length=64), nullable=True),
        sa.Column("provider_queue_state", sa.String(length=64), nullable=True),
        sa.Column("provider_attempt", sa.Integer(), nullable=True),
        sa.Column("provider_max_attempts", sa.Integer(), nullable=True),
        sa.Column("provider_next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_after_seconds", sa.Integer(), nullable=True),
        sa.Column("last_request_id", sa.String(length=128), nullable=True),
        sa.Column("provider_location", sa.String(length=512), nullable=True),
        sa.Column("api_contract_version", sa.String(length=32), nullable=True),
        sa.Column("provider_build", sa.String(length=128), nullable=True),
        sa.Column("request_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("deletion_state", sa.String(length=32), nullable=True),
        sa.Column("deletion_status_url", sa.String(length=512), nullable=True),
        sa.Column("deletion_receipt_id", sa.String(length=240), nullable=True),
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deletion_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    result_columns = (
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.Column("overlaps_json", sa.JSON(), nullable=True),
        sa.Column("acoustic_turns_json", sa.JSON(), nullable=True),
        sa.Column("downloads_json", sa.JSON(), nullable=True),
    )
    for column in workflow_columns:
        op.add_column("processing_workflows", column)
    for column in job_columns:
        op.add_column("mediascribe_jobs", column)
    for column in result_columns:
        op.add_column("processing_results", column)
    op.create_index(
        "ix_processing_workflows_recovery_due",
        "processing_workflows",
        ["status", "next_attempt_at", "schedule_generation"],
    )


def downgrade() -> None:
    op.drop_index("ix_processing_workflows_recovery_due", table_name="processing_workflows")
    for name in ("downloads_json", "acoustic_turns_json", "overlaps_json", "provenance_json"):
        op.drop_column("processing_results", name)
    for name in (
        "deletion_confirmed_at", "deletion_requested_at", "deletion_receipt_id",
        "deletion_status_url", "deletion_state", "request_fingerprint", "provider_build",
        "api_contract_version", "provider_location", "last_request_id", "retry_after_seconds",
        "provider_next_retry_at", "provider_max_attempts", "provider_attempt",
        "provider_queue_state", "provider_status",
    ):
        op.drop_column("mediascribe_jobs", name)
    for name in (
        "manual_claimed_by", "manual_claimed_at", "manual_command_version",
        "schedule_generation", "next_attempt_source", "next_attempt_at", "deadline_at",
        "retry_count", "retry_class", "stage", "attempt_ordinal",
    ):
        op.drop_column("processing_workflows", name)
