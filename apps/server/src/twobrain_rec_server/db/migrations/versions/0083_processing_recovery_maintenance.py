"""Allow bounded maintenance recovery of committed processing starts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0083_processing_recovery"
down_revision: str | None = "0082_mediascribe_words"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PREVIOUS_OPERATIONS = (
    "migration_verification",
    "production_smoke_setup",
    "production_smoke_cleanup",
    "backup_restore_rehearsal",
    "operator_diagnostics",
    "provider_link_cleanup",
    "playback_normalization_inventory",
    "playback_normalization_dispatch",
    "prompt_optimization",
    "outcome_dispatch_reconciliation",
    "deletion_purge_reconciliation",
    "processing_legacy_lineage_reconciliation",
    "outcome_initial_baseline_reconciliation",
    "billing_reconciliation",
    "billing_notification_reconciliation",
    "account_merge",
    "calendar_sync_reconciliation",
)
CURRENT_OPERATIONS = (*PREVIOUS_OPERATIONS, "processing_recovery_reconciliation")
NORMALIZATION_TERMINAL_CONSTRAINT = (
    "ck_playback_normalization_jobs_playback_normalization_job_terminal_facts"
)


def _replace_maintenance_helper(operations: tuple[str, ...]) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    literals = ", ".join(f"'{operation}'" for operation in operations)
    op.execute(
        f"""
        create or replace function rec_maintenance_allowed()
        returns boolean
        language sql
        stable
        as $$
            select session_user = 'twobrain_rec_maintenance'
            and rec_setting('app.context_kind') = 'maintenance'
            and rec_setting('app.maintenance_operation') = any(array[{literals}])
            and rec_setting('app.maintenance_actor') is not null
            and rec_setting('app.maintenance_reason') is not null
            and rec_setting('app.maintenance_feature_area') is not null
            or (
                session_user = 'twobrain_rec_app'
                and rec_account_merge_context_valid()
            )
        $$;
        """
    )


def _replace_normalization_terminal_constraint(*, allow_storage_capacity: bool) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    terminal_reasons = (
        "'empty_source', 'unsupported_container', 'unsupported_codec', "
        "'encrypted_media', 'corrupt_source', 'no_audio', "
        "'ambiguous_audio_tracks', 'stream_limit_exceeded', "
        "'duration_limit_exceeded', 'source_size_limit_exceeded', "
        "'source_missing', 'source_mismatch'"
    )
    if allow_storage_capacity:
        terminal_reasons += ", 'storage_capacity_exceeded'"
    op.drop_constraint(
        NORMALIZATION_TERMINAL_CONSTRAINT,
        "playback_normalization_jobs",
        type_="check",
    )
    op.create_check_constraint(
        NORMALIZATION_TERMINAL_CONSTRAINT,
        "playback_normalization_jobs",
        f"state != 'terminal' or (terminal_at is not null and reason_code in ({terminal_reasons}))",
    )


def upgrade() -> None:
    _replace_maintenance_helper(CURRENT_OPERATIONS)
    _replace_normalization_terminal_constraint(allow_storage_capacity=True)
    op.add_column(
        "meeting_purge_journal",
        sa.Column("media_revision_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_meeting_purge_journal_media_revision_id",
        "meeting_purge_journal",
        "media_revisions",
        ["media_revision_id"],
        ["id"],
    )
    op.create_index(
        "ix_meeting_purge_journal_transient_revision",
        "meeting_purge_journal",
        ["media_revision_id", "state", "next_retry_at"],
        postgresql_where=sa.text("artifact_class = 'transient_audio'"),
    )
    op.create_index(
        "ix_upload_sessions_processing_dispatch_recovery",
        "upload_sessions",
        ["finalized_at", "workspace_id", "meeting_id", "media_revision_id"],
        postgresql_where=sa.text(
            "status = 'finalized' and processing_status = 'starting' "
            "and media_revision_id is not null"
        ),
    )
    op.create_index(
        "ix_processing_workflows_transient_hard_due",
        "processing_workflows",
        ["transient_hard_deadline", "workspace_id", "meeting_id", "media_revision_id"],
        postgresql_where=sa.text(
            "archive_audio = false and media_revision_id is not null and transient_state in "
            "('admitted', 'processing', 'terminal', 'purge_due')"
        ),
    )
    op.create_index(
        "ix_processing_workflows_transient_terminal_due",
        "processing_workflows",
        ["transient_purge_due_at", "workspace_id", "meeting_id", "media_revision_id"],
        postgresql_where=sa.text(
            "archive_audio = false and media_revision_id is not null and transient_state in "
            "('admitted', 'processing', 'terminal', 'purge_due')"
        ),
    )
    op.create_index(
        "ix_upload_sessions_transient_hard_due",
        "upload_sessions",
        ["finalized_at", "workspace_id", "meeting_id", "media_revision_id"],
        postgresql_where=sa.text(
            "archive_audio = false and status = 'finalized' and media_revision_id is not null"
        ),
    )
    op.create_index(
        "ix_upload_sessions_transient_revision_custody",
        "upload_sessions",
        ["workspace_id", "meeting_id", "media_revision_id"],
        postgresql_where=sa.text("status = 'finalized' and media_revision_id is not null"),
    )
    op.create_index(
        "ix_temporary_upload_objects_session",
        "temporary_upload_objects",
        ["upload_session_id"],
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            do $$
            begin
                if exists (
                    select 1
                    from playback_normalization_jobs
                    where state = 'terminal'
                      and reason_code = 'storage_capacity_exceeded'
                ) then
                    raise exception using
                        message = '0083 downgrade blocked: resolve storage_capacity_exceeded normalization jobs first';
                end if;
            end
            $$
            """
        )
    op.drop_index(
        "ix_temporary_upload_objects_session",
        table_name="temporary_upload_objects",
    )
    op.drop_index(
        "ix_upload_sessions_transient_revision_custody",
        table_name="upload_sessions",
    )
    op.drop_index("ix_upload_sessions_transient_hard_due", table_name="upload_sessions")
    op.drop_index(
        "ix_upload_sessions_processing_dispatch_recovery",
        table_name="upload_sessions",
    )
    op.drop_index(
        "ix_processing_workflows_transient_terminal_due",
        table_name="processing_workflows",
    )
    op.drop_index(
        "ix_processing_workflows_transient_hard_due",
        table_name="processing_workflows",
    )
    op.drop_index(
        "ix_meeting_purge_journal_transient_revision",
        table_name="meeting_purge_journal",
    )
    op.drop_constraint(
        "fk_meeting_purge_journal_media_revision_id",
        "meeting_purge_journal",
        type_="foreignkey",
    )
    op.drop_column("meeting_purge_journal", "media_revision_id")
    _replace_normalization_terminal_constraint(allow_storage_capacity=False)
    _replace_maintenance_helper(PREVIOUS_OPERATIONS)
