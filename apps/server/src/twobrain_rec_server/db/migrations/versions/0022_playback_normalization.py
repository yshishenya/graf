"""playback normalization foundation

Revision ID: 0022_playback_normalization
Revises: 0021_calendar_auto_context_match
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_playback_normalization"
down_revision: str | None = "0021_calendar_auto_context_match"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROFILE_VERSION = "review_m4a_aac_lc_48k_mono_64k_v1"
VALIDATION_VERSION = "playback_validator_v1"

PLAYBACK_NORMALIZATION_TABLES = (
    "playback_backfill_runs",
    "playback_normalization_jobs",
    "playback_normalization_attempts",
)
NORMALIZATION_MAINTENANCE_SELECT_TABLES = (
    "playback_backfill_runs",
    "playback_normalization_jobs",
)
NORMALIZATION_MAINTENANCE_OPERATIONS = (
    "playback_normalization_inventory",
    "playback_normalization_dispatch",
)
LEGACY_MAINTENANCE_OPERATIONS = (
    "migration_verification",
    "production_smoke_cleanup",
    "backup_restore_rehearsal",
    "operator_diagnostics",
)
NORMALIZATION_RLS_PREDICATE = (
    "rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()"
)
NORMALIZATION_MAINTENANCE_PREDICATE = "rec_playback_normalization_maintenance_allowed()"
CANONICAL_PLAYBACK_PREDICATE = (
    "track_role = 'playback' and status = 'stored' "
    f"and normalization_profile_version = '{PROFILE_VERSION}' "
    "and validated_at is not null"
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _add_track_artifact_validation() -> None:
    with op.batch_alter_table("track_artifacts") as batch_op:
        batch_op.add_column(sa.Column("normalization_profile_version", sa.String(length=120)))
        batch_op.add_column(sa.Column("validated_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("derivation_kind", sa.String(length=64)))
        batch_op.add_column(sa.Column("source_fingerprint_sha256", sa.String(length=64)))
        batch_op.add_column(sa.Column("validation_version", sa.String(length=80)))
        batch_op.create_check_constraint(
            "ck_track_artifacts_track_artifact_validation_bundle",
            f"""
            (
                normalization_profile_version is null
                and validated_at is null
                and source_fingerprint_sha256 is null
                and validation_version is null
            )
            or
            (
                normalization_profile_version = '{PROFILE_VERSION}'
                and validated_at is not null
                and source_fingerprint_sha256 is not null
                and validation_version = '{VALIDATION_VERSION}'
                and derivation_kind is not null
                and track_role = 'playback'
                and status = 'stored'
                and media_revision_id is not null
            )
            """,
        )
        batch_op.create_check_constraint(
            "ck_track_artifacts_track_artifact_derivation_role",
            "derivation_kind is null or track_role = 'playback'",
        )
    op.create_index(
        "uq_track_artifacts_canonical_playback",
        "track_artifacts",
        ["workspace_id", "media_revision_id"],
        unique=True,
        postgresql_where=sa.text(CANONICAL_PLAYBACK_PREDICATE),
        sqlite_where=sa.text(CANONICAL_PLAYBACK_PREDICATE),
    )
    op.create_index(
        "ix_track_artifacts_workspace_meeting_role_status",
        "track_artifacts",
        ["workspace_id", "meeting_id", "track_role", "status"],
    )


def _create_backfill_runs() -> None:
    op.create_table(
        "playback_backfill_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column(
            "profile_version",
            sa.String(length=120),
            nullable=False,
            server_default=PROFILE_VERSION,
        ),
        sa.Column(
            "state",
            sa.String(length=64),
            nullable=False,
            server_default="inventory_pending",
        ),
        sa.Column("cursor_created_at", sa.DateTime(timezone=True)),
        sa.Column("cursor_media_revision_id", sa.Uuid(), sa.ForeignKey("media_revisions.id")),
        sa.Column("evaluated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("preserve_valid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validate_candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("normalize_source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unavailable_source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ready_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("terminal_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cancelled_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("safe_block_reason", sa.String(length=120)),
        sa.Column("inventory_started_at", sa.DateTime(timezone=True)),
        sa.Column("inventory_completed_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workspace_id",
            "profile_version",
            name="uq_playback_backfill_runs_workspace_profile",
        ),
        sa.CheckConstraint(
            "(cursor_created_at is null) = (cursor_media_revision_id is null)",
            name="ck_playback_backfill_runs_playback_backfill_cursor_pair",
        ),
        sa.CheckConstraint(
            f"profile_version = '{PROFILE_VERSION}'",
            name="ck_playback_backfill_runs_profile_allowed",
        ),
        sa.CheckConstraint(
            "state in ('inventory_pending', 'inventory_running', 'inventory_complete', "
            "'dispatching', 'complete', 'blocked')",
            name="ck_playback_backfill_runs_state_allowed",
        ),
        sa.CheckConstraint(
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
            name="ck_playback_backfill_runs_playback_backfill_nonnegative_counters",
        ),
        sa.CheckConstraint(
            """
            (state != 'inventory_running' or inventory_started_at is not null)
            and (state not in ('inventory_complete', 'dispatching', 'complete')
                 or inventory_completed_at is not null)
            and (state != 'complete' or completed_at is not null)
            and (state != 'blocked' or safe_block_reason is not null)
            """,
            name="ck_playback_backfill_runs_playback_backfill_state_facts",
        ),
    )
    op.create_index(
        "ix_playback_backfill_runs_state_updated",
        "playback_backfill_runs",
        ["state", "updated_at", "id"],
    )


def _create_jobs() -> None:
    op.create_table(
        "playback_normalization_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column(
            "requested_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("user_identities.id"),
            nullable=False,
        ),
        sa.Column(
            "source_device_id",
            sa.Uuid(),
            sa.ForeignKey("registered_devices.id"),
            nullable=False,
        ),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column(
            "media_revision_id",
            sa.Uuid(),
            sa.ForeignKey("media_revisions.id"),
            nullable=False,
        ),
        sa.Column(
            "profile_version",
            sa.String(length=120),
            nullable=False,
            server_default=PROFILE_VERSION,
        ),
        sa.Column(
            "validation_version",
            sa.String(length=80),
            nullable=False,
            server_default=VALIDATION_VERSION,
        ),
        sa.Column("trigger_kind", sa.String(length=64), nullable=False),
        sa.Column("priority_class", sa.String(length=64), nullable=False),
        sa.Column("source_kind", sa.String(length=64), nullable=False),
        sa.Column("source_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("backfill_run_id", sa.Uuid(), sa.ForeignKey("playback_backfill_runs.id")),
        sa.Column("planned_action", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="queued"),
        sa.Column("reason_code", sa.String(length=120)),
        sa.Column("workflow_id", sa.String(length=240), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=240)),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cycle_attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_cycle_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("lease_owner_sha256", sa.String(length=64)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("canonical_track_artifact_id", sa.Uuid(), sa.ForeignKey("track_artifacts.id")),
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("ready_at", sa.DateTime(timezone=True)),
        sa.Column("terminal_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workspace_id",
            "media_revision_id",
            "profile_version",
            name="uq_playback_normalization_jobs_workspace_revision_profile",
        ),
        sa.UniqueConstraint(
            "canonical_track_artifact_id",
            name="uq_playback_normalization_jobs_canonical_track_artifact_id",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0 and cycle_attempt_count between 0 and 4 and retry_cycle_count >= 0",
            name="ck_playback_normalization_jobs_playback_normalization_job_nonnegative_counters",
        ),
        sa.CheckConstraint(
            f"profile_version = '{PROFILE_VERSION}' "
            f"and validation_version = '{VALIDATION_VERSION}'",
            name="ck_playback_normalization_jobs_profile_allowed",
        ),
        sa.CheckConstraint(
            "state in ('queued', 'running', 'publishing', 'retry_wait', 'ready', "
            "'terminal', 'cancelled')",
            name="ck_playback_normalization_jobs_state_allowed",
        ),
        sa.CheckConstraint(
            "trigger_kind in ('finalize', 'reconcile', 'legacy_backfill') "
            "and priority_class in ('new_ingest', 'due_retry', 'legacy_backfill') "
            "and planned_action in ('validate_candidate', 'preserve_valid', "
            "'normalize_source', 'unavailable_source')",
            name="ck_playback_normalization_jobs_kind_allowed",
        ),
        sa.CheckConstraint(
            "length(source_fingerprint_sha256) = 64",
            name="ck_playback_normalization_jobs_fingerprint_length",
        ),
        sa.CheckConstraint(
            "(state in ('queued', 'running', 'publishing', 'ready') and reason_code is null) "
            "or state in ('retry_wait', 'terminal', 'cancelled')",
            name="ck_playback_normalization_jobs_reason_state",
        ),
        sa.CheckConstraint(
            "trigger_kind != 'legacy_backfill' or backfill_run_id is not null",
            name="ck_playback_normalization_jobs_playback_normalization_job_backfill_link",
        ),
        sa.CheckConstraint(
            """
            state != 'ready'
            or (
                canonical_track_artifact_id is not null
                and ready_at is not null
                and reason_code is null
            )
            """,
            name="ck_playback_normalization_jobs_playback_normalization_job_ready_facts",
        ),
        sa.CheckConstraint(
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
            name="ck_playback_normalization_jobs_playback_normalization_job_retry_facts",
        ),
        sa.CheckConstraint(
            """
            state != 'terminal'
            or (
                terminal_at is not null
                and reason_code in (
                    'empty_source', 'unsupported_container', 'unsupported_codec',
                    'encrypted_media', 'corrupt_source', 'no_audio',
                    'ambiguous_audio_tracks', 'stream_limit_exceeded',
                    'duration_limit_exceeded', 'source_size_limit_exceeded',
                    'source_missing', 'source_mismatch'
                )
            )
            """,
            name="ck_playback_normalization_jobs_playback_normalization_job_terminal_facts",
        ),
        sa.CheckConstraint(
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
            name="ck_playback_normalization_jobs_playback_normalization_job_cancelled_facts",
        ),
    )
    op.create_index(
        "ix_playback_normalization_jobs_due_pickup",
        "playback_normalization_jobs",
        ["state", "next_attempt_at", "priority_class", "created_at", "id"],
    )
    op.create_index(
        "ix_playback_normalization_jobs_workspace_meeting_state",
        "playback_normalization_jobs",
        ["workspace_id", "meeting_id", "state"],
    )
    op.create_index(
        "ix_playback_normalization_jobs_expired_lease",
        "playback_normalization_jobs",
        ["state", "lease_expires_at", "id"],
    )


def _create_attempts() -> None:
    op.create_table(
        "playback_normalization_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column(
            "media_revision_id",
            sa.Uuid(),
            sa.ForeignKey("media_revisions.id"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.Uuid(),
            sa.ForeignKey("playback_normalization_jobs.id"),
            nullable=False,
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="local_preparing"),
        sa.Column("storage_object_key", sa.String(length=1000), nullable=False),
        sa.Column("published_track_artifact_id", sa.Uuid(), sa.ForeignKey("track_artifacts.id")),
        sa.Column("derivation_kind", sa.String(length=64), nullable=False),
        sa.Column("selected_stream_index", sa.Integer()),
        sa.Column("source_stream_count", sa.Integer(), nullable=False),
        sa.Column("source_audio_stream_count", sa.Integer(), nullable=False),
        sa.Column("source_duration_ms", sa.BigInteger()),
        sa.Column("output_duration_ms", sa.BigInteger()),
        sa.Column("output_byte_length", sa.BigInteger()),
        sa.Column("output_sha256", sa.String(length=64)),
        sa.Column("output_audio_bit_rate", sa.Integer()),
        sa.Column("output_sample_rate_hz", sa.Integer()),
        sa.Column("output_channel_count", sa.Integer()),
        sa.Column("moov_before_mdat", sa.Boolean()),
        sa.Column("fragmented", sa.Boolean()),
        sa.Column("full_decode_passed", sa.Boolean()),
        sa.Column("cleanup_reason", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("uploaded_at", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("cleaned_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "job_id",
            "attempt_number",
            name="uq_playback_normalization_attempts_job_number",
        ),
        sa.UniqueConstraint(
            "storage_object_key",
            name="uq_playback_normalization_attempts_storage_object_key",
        ),
        sa.UniqueConstraint(
            "published_track_artifact_id",
            name="uq_playback_normalization_attempts_published_track_artifact_id",
        ),
        sa.CheckConstraint(
            """
            attempt_number >= 1
            and cycle_number >= 1
            and source_stream_count >= 0
            and source_audio_stream_count >= 0
            and source_audio_stream_count <= source_stream_count
            and (selected_stream_index is null or selected_stream_index >= 0)
            """,
            name="ck_playback_normalization_attempts_playback_normalization_attempt_number_counts",
        ),
        sa.CheckConstraint(
            "state in ('local_preparing', 'uploaded', 'published', "
            "'cleanup_pending', 'cleaned', 'purged')",
            name="ck_playback_normalization_attempts_state_allowed",
        ),
        sa.CheckConstraint(
            "derivation_kind in ('uploaded_candidate', 'source_byte_copy', "
            "'lossless_faststart_remux', 'single_source_transcode', "
            "'dual_source_mix_transcode', 'legacy_unvalidated')",
            name="ck_playback_normalization_attempts_derivation_allowed",
        ),
        sa.CheckConstraint(
            "(source_duration_ms is null or source_duration_ms > 0) "
            "and (output_duration_ms is null or output_duration_ms > 0) "
            "and (output_byte_length is null or output_byte_length > 0) "
            "and (output_sha256 is null or length(output_sha256) = 64) "
            "and (output_audio_bit_rate is null or output_audio_bit_rate > 0) "
            "and (output_sample_rate_hz is null or output_sample_rate_hz > 0) "
            "and (output_channel_count is null or output_channel_count > 0)",
            name="ck_playback_normalization_attempts_positive_facts",
        ),
        sa.CheckConstraint(
            "state != 'cleaned' or cleaned_at is not null",
            name="ck_playback_normalization_attempts_cleanup_facts",
        ),
        sa.CheckConstraint(
            """
            state not in ('uploaded', 'published')
            or (output_byte_length > 0 and output_sha256 is not null and uploaded_at is not null)
            """,
            name="ck_playback_normalization_attempts_playback_normalization_attempt_uploaded_facts",
        ),
        sa.CheckConstraint(
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
            name="ck_playback_normalization_attempts_playback_normalization_attempt_published_facts",
        ),
    )
    op.create_index(
        "ix_playback_normalization_attempts_workspace_meeting_state",
        "playback_normalization_attempts",
        ["workspace_id", "meeting_id", "state"],
    )
    op.create_index(
        "ix_playback_normalization_attempts_cleanup_recovery",
        "playback_normalization_attempts",
        ["state", "updated_at", "id"],
    )


def _create_normalization_maintenance_helper() -> None:
    operations = ", ".join(f"'{operation}'" for operation in NORMALIZATION_MAINTENANCE_OPERATIONS)
    op.execute(
        f"""
        create or replace function rec_playback_normalization_maintenance_allowed()
        returns boolean
        language sql
        stable
        as $$
            select session_user = 'twobrain_rec_media'
            and rec_setting('app.context_kind') = 'maintenance'
            and rec_setting('app.maintenance_operation') = any(array[{operations}])
            and rec_setting('app.maintenance_actor') is not null
            and rec_setting('app.maintenance_reason') is not null
            and rec_setting('app.maintenance_feature_area') = 'playback_normalization'
        $$;
        """
    )


def _replace_legacy_maintenance_helper(*, trusted_role_only: bool) -> None:
    operations = ", ".join(f"'{operation}'" for operation in LEGACY_MAINTENANCE_OPERATIONS)
    role_guard = (
        "and session_user = 'twobrain_rec_maintenance'" if trusted_role_only else ""
    )
    op.execute(
        f"""
        create or replace function rec_maintenance_allowed()
        returns boolean
        language sql
        stable
        as $$
            select rec_setting('app.context_kind') = 'maintenance'
            and rec_setting('app.maintenance_operation') = any(array[{operations}])
            and rec_setting('app.maintenance_actor') is not null
            and rec_setting('app.maintenance_reason') is not null
            and rec_setting('app.maintenance_feature_area') is not null
            {role_guard}
        $$;
        """
    )


def _create_normalization_workspace_page_function() -> None:
    op.execute(
        """
        create or replace function rec_playback_normalization_workspace_page(
            p_after_workspace_id uuid,
            p_page_size integer
        )
        returns table (
            organization_id uuid,
            workspace_id uuid,
            user_id uuid,
            device_id uuid
        )
        language sql
        stable
        security definer
        set search_path = pg_catalog, public
        set row_security = off
        as $$
            select
                workspace_parent.organization_id,
                workspace_parent.id,
                seed_meeting.created_by_user_id,
                seed_meeting.device_id
            from workspaces as workspace_parent
            join lateral (
                select meeting_parent.created_by_user_id, meeting_parent.device_id
                from meetings as meeting_parent
                where meeting_parent.workspace_id = workspace_parent.id
                order by meeting_parent.created_at, meeting_parent.id
                limit 1
            ) as seed_meeting on true
            where rec_setting('app.context_kind') = 'maintenance'
              and session_user = 'twobrain_rec_media'
              and rec_setting('app.maintenance_operation') =
                  'playback_normalization_inventory'
              and rec_setting('app.maintenance_actor') is not null
              and rec_setting('app.maintenance_reason') is not null
              and rec_setting('app.maintenance_feature_area') =
                  'playback_normalization'
              and (
                  p_after_workspace_id is null
                  or workspace_parent.id > p_after_workspace_id
              )
            order by workspace_parent.id
            limit least(greatest(p_page_size, 1), 50)
        $$;
        """
    )
    op.execute(
        "revoke all privileges on function "
        "rec_playback_normalization_workspace_page(uuid, integer) from public"
    )


def _create_normalization_cleanup_page_function() -> None:
    op.execute(
        """
        create or replace function rec_playback_normalization_cleanup_page(
            p_page_size integer
        )
        returns table (
            attempt_id uuid,
            job_id uuid,
            organization_id uuid,
            workspace_id uuid,
            user_id uuid,
            device_id uuid,
            attempt_state varchar
        )
        language sql
        stable
        security definer
        set search_path = pg_catalog, public
        set row_security = off
        as $$
            select
                cleanup_attempt.id,
                cleanup_job.id,
                cleanup_job.organization_id,
                cleanup_job.workspace_id,
                cleanup_job.requested_by_user_id,
                cleanup_job.source_device_id,
                cleanup_attempt.state
            from playback_normalization_attempts as cleanup_attempt
            join playback_normalization_jobs as cleanup_job
              on cleanup_job.id = cleanup_attempt.job_id
            where session_user = 'twobrain_rec_media'
              and rec_setting('app.context_kind') = 'maintenance'
              and rec_setting('app.maintenance_operation') =
                  'playback_normalization_dispatch'
              and rec_setting('app.maintenance_actor') is not null
              and rec_setting('app.maintenance_reason') is not null
              and rec_setting('app.maintenance_feature_area') =
                  'playback_normalization'
              and cleanup_attempt.state in (
                  'local_preparing', 'uploaded', 'cleanup_pending', 'purged'
              )
              and (
                  cleanup_attempt.state != 'purged'
                  or cleanup_attempt.cleaned_at is null
              )
            order by cleanup_attempt.updated_at asc nulls first, cleanup_attempt.id
            limit least(greatest(p_page_size, 1), 25)
        $$;
        """
    )
    op.execute(
        "revoke all privileges on function "
        "rec_playback_normalization_cleanup_page(integer) from public"
    )


def _create_rls_policies() -> None:
    _replace_legacy_maintenance_helper(trusted_role_only=True)
    _create_normalization_maintenance_helper()
    _create_normalization_workspace_page_function()
    _create_normalization_cleanup_page_function()
    for table_name in PLAYBACK_NORMALIZATION_TABLES:
        table = _q(table_name)
        tenant_policy = _q(f"{table_name}_tenant_isolation")
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"alter table {table} force row level security")
        op.execute(f"drop policy if exists {tenant_policy} on {table}")
        op.execute(
            f"create policy {tenant_policy} on {table} for all "
            f"using ({NORMALIZATION_RLS_PREDICATE}) "
            f"with check ({NORMALIZATION_RLS_PREDICATE})"
        )
    for table_name in NORMALIZATION_MAINTENANCE_SELECT_TABLES:
        table = _q(table_name)
        policy = _q(f"{table_name}_playback_scheduler_select")
        op.execute(f"drop policy if exists {policy} on {table}")
        op.execute(
            f"create policy {policy} on {table} for select "
            f"using ({NORMALIZATION_MAINTENANCE_PREDICATE})"
        )


def _drop_rls_policies() -> None:
    op.execute("drop function if exists rec_playback_normalization_cleanup_page(integer)")
    op.execute("drop function if exists rec_playback_normalization_workspace_page(uuid, integer)")
    for table_name in NORMALIZATION_MAINTENANCE_SELECT_TABLES:
        table = _q(table_name)
        policy = _q(f"{table_name}_playback_scheduler_select")
        op.execute(f"drop policy if exists {policy} on {table}")
    for table_name in reversed(PLAYBACK_NORMALIZATION_TABLES):
        table = _q(table_name)
        tenant_policy = _q(f"{table_name}_tenant_isolation")
        op.execute(f"drop policy if exists {tenant_policy} on {table}")
        op.execute(f"alter table {table} no force row level security")
        op.execute(f"alter table {table} disable row level security")
    op.execute("drop function if exists rec_playback_normalization_maintenance_allowed()")
    _replace_legacy_maintenance_helper(trusted_role_only=False)


def upgrade() -> None:
    _add_track_artifact_validation()
    _create_backfill_runs()
    _create_jobs()
    _create_attempts()
    if _is_postgresql():
        _create_rls_policies()


def downgrade() -> None:
    if _is_postgresql():
        _drop_rls_policies()
    op.drop_table("playback_normalization_attempts")
    op.drop_table("playback_normalization_jobs")
    op.drop_table("playback_backfill_runs")
    op.drop_index(
        "ix_track_artifacts_workspace_meeting_role_status",
        table_name="track_artifacts",
    )
    op.drop_index(
        "uq_track_artifacts_canonical_playback",
        table_name="track_artifacts",
    )
    with op.batch_alter_table("track_artifacts") as batch_op:
        batch_op.drop_constraint(
            "ck_track_artifacts_track_artifact_derivation_role",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_track_artifacts_track_artifact_validation_bundle",
            type_="check",
        )
        batch_op.drop_column("validation_version")
        batch_op.drop_column("source_fingerprint_sha256")
        batch_op.drop_column("derivation_kind")
        batch_op.drop_column("validated_at")
        batch_op.drop_column("normalization_profile_version")
