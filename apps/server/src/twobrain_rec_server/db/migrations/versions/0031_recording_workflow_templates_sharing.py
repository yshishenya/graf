"""recording workflow templates, sharing, and retained observability

Revision ID: 0031_recording_workflows
Revises: 0030_expand_meeting_registry
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_recording_workflows"
down_revision: str | None = "0030_expand_meeting_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REQUEST_WORKER_TENANT = (
    "((rec_context_kind() in ('request', 'worker') "
    "and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())"
)
WORKER_OPERATOR_TENANT = (
    "((rec_context_kind() = 'worker' and workspace_id = rec_current_workspace_id()) "
    "or rec_maintenance_allowed())"
)
TENANT_TABLE_POLICIES = {
    "summary_templates": REQUEST_WORKER_TENANT,
    "meeting_share_invitations": REQUEST_WORKER_TENANT,
    "generation_calls": WORKER_OPERATOR_TENANT,
}
GLOBAL_OPERATOR_TABLES = (
    "prompt_optimization_runs",
    "prompt_optimization_call_ledger",
)


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _create_policy(table_name: str, expression: str) -> None:
    table = _q(table_name)
    policy = _q(f"{table_name}_isolation")
    op.execute(f"alter table {table} enable row level security")
    op.execute(f"alter table {table} force row level security")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(
        f"create policy {policy} on {table} "
        f"using ({expression}) with check ({expression})"
    )


def _drop_policy(table_name: str) -> None:
    table = _q(table_name)
    policy = _q(f"{table_name}_isolation")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(f"alter table {table} no force row level security")
    op.execute(f"alter table {table} disable row level security")


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.create_table(
        "summary_templates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("template_key", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("purpose", sa.String(length=240), nullable=False),
        sa.Column("sections_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("output_language", sa.String(length=16), nullable=False),
        sa.Column("detail_level", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workspace_id",
            "owner_user_id",
            "template_key",
            "version",
            name="uq_summary_templates_owner_key_version",
        ),
    )
    op.create_index(
        "ix_summary_templates_workspace_status",
        "summary_templates",
        ["workspace_id", "status"],
    )
    op.add_column(
        "workspaces",
        sa.Column(
            "default_summary_template_key",
            sa.String(length=120),
            nullable=False,
            server_default="graf-auto-v1",
        ),
    )
    op.add_column(
        "workspaces",
        sa.Column("default_summary_template_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column(
            "default_summary_template_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.create_foreign_key(
        "fk_workspaces_default_summary_template",
        "workspaces",
        "summary_templates",
        ["default_summary_template_id"],
        ["id"],
    )

    op.add_column("meetings", sa.Column("current_outcome_set_id", sa.Uuid()))
    op.add_column("meeting_outcome_sets", sa.Column("template_id", sa.Uuid()))
    op.add_column("meeting_outcome_sets", sa.Column("template_key", sa.String(length=120)))
    op.add_column("meeting_outcome_sets", sa.Column("template_version", sa.Integer()))
    op.add_column("meeting_outcome_sets", sa.Column("output_language", sa.String(length=16)))
    op.add_column("meeting_outcome_sets", sa.Column("detail_level", sa.String(length=32)))
    op.add_column("meeting_outcome_sets", sa.Column("revision_state", sa.String(length=32)))
    op.add_column("meeting_outcome_sets", sa.Column("requested_by_user_id", sa.Uuid()))
    op.add_column("meeting_outcome_sets", sa.Column("accepted_by_user_id", sa.Uuid()))
    op.add_column("meeting_outcome_sets", sa.Column("accepted_at", sa.DateTime(timezone=True)))
    op.add_column("meeting_outcome_sets", sa.Column("supersedes_outcome_set_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_meetings_current_outcome_set",
        "meetings",
        "meeting_outcome_sets",
        ["current_outcome_set_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_outcome_sets_template",
        "meeting_outcome_sets",
        "summary_templates",
        ["template_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_outcome_sets_requested_by",
        "meeting_outcome_sets",
        "user_identities",
        ["requested_by_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_outcome_sets_accepted_by",
        "meeting_outcome_sets",
        "user_identities",
        ["accepted_by_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_outcome_sets_supersedes",
        "meeting_outcome_sets",
        "meeting_outcome_sets",
        ["supersedes_outcome_set_id"],
        ["id"],
    )

    attempt_columns = (
        sa.Column("candidate_id", sa.Uuid()),
        sa.Column("source_result_id", sa.Uuid()),
        sa.Column("requested_by_user_id", sa.Uuid()),
        sa.Column("template_id", sa.Uuid()),
        sa.Column("template_key", sa.String(length=120)),
        sa.Column("template_version", sa.Integer()),
        sa.Column("output_language", sa.String(length=16)),
        sa.Column("detail_level", sa.String(length=32)),
        sa.Column("prompt_name", sa.String(length=240)),
        sa.Column("prompt_version", sa.Integer()),
        sa.Column("prompt_source", sa.String(length=64)),
        sa.Column("prompt_definition", sa.JSON()),
        sa.Column("prompt_config", sa.JSON()),
        sa.Column("prompt_hash", sa.String(length=64)),
        sa.Column("output_schema_version", sa.String(length=64)),
        sa.Column("model_route", sa.String(length=128)),
        sa.Column("model_parameters", sa.JSON()),
        sa.Column("workflow_id", sa.String(length=240)),
        sa.Column("workflow_run_id", sa.String(length=240)),
        sa.Column("langfuse_trace_id", sa.String(length=64)),
        sa.Column("temporal_transcript_hash", sa.String(length=64)),
        sa.Column("temporal_transcript_chunk_count", sa.Integer()),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_code", sa.String(length=120)),
    )
    for column in attempt_columns:
        op.add_column("meeting_outcome_generation_attempts", column)
    op.create_foreign_key(
        "fk_generation_attempt_source_result",
        "meeting_outcome_generation_attempts",
        "processing_results",
        ["source_result_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_generation_attempt_requested_by",
        "meeting_outcome_generation_attempts",
        "user_identities",
        ["requested_by_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_generation_attempt_template",
        "meeting_outcome_generation_attempts",
        "summary_templates",
        ["template_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_generation_attempt_candidate_id",
        "meeting_outcome_generation_attempts",
        ["candidate_id"],
    )
    op.create_index(
        "ix_generation_attempt_workflow_id",
        "meeting_outcome_generation_attempts",
        ["workflow_id"],
    )

    grant_columns = (
        sa.Column("audience_type", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column("audience_id", sa.Uuid()),
        sa.Column(
            "content_scope", sa.String(length=32), nullable=False, server_default="summary_only"
        ),
        sa.Column("can_download", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_export", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("rotated_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
    )
    for column in grant_columns:
        op.add_column("meeting_share_grants", column)
    op.execute(
        "update meeting_share_grants set audience_id = grantee_user_id "
        "where audience_type = 'user' and audience_id is null"
    )
    # Before scoped sharing, every active login-required grant exposed the full
    # meeting and its allowed egress. Preserve that meaning for existing rows;
    # the column defaults apply only to grants created after this migration.
    op.execute(
        "update meeting_share_grants set content_scope = 'full_meeting', "
        "can_download = true, can_export = true"
    )
    op.drop_constraint(
        "uq_meeting_share_grants_active_user",
        "meeting_share_grants",
        type_="unique",
    )
    op.create_index(
        "uq_meeting_share_grants_active_user",
        "meeting_share_grants",
        ["workspace_id", "meeting_id", "audience_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND audience_type = 'user'"),
    )
    op.create_index(
        "uq_meeting_share_grants_active_link",
        "meeting_share_grants",
        ["workspace_id", "meeting_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND audience_type = 'link'"),
    )

    op.create_table(
        "meeting_share_invitations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column(
            "invited_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("user_identities.id"),
            nullable=False,
        ),
        sa.Column("normalized_address_hash", sa.String(length=128), nullable=False),
        sa.Column("encrypted_delivery_address", sa.String(), nullable=False),
        sa.Column(
            "content_scope", sa.String(length=32), nullable=False, server_default="summary_only"
        ),
        sa.Column("can_download", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_export", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("resolved_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("failure_code", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "uq_meeting_share_invitations_address_status",
        "meeting_share_invitations",
        ["workspace_id", "meeting_id", "normalized_address_hash"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'sending', 'sent')"),
    )

    op.create_table(
        "generation_calls",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("provider_attempt", sa.Integer(), nullable=False),
        sa.Column("call_sequence", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("observation_id", sa.String(length=64), nullable=False),
        sa.Column("call_state", sa.String(length=32), nullable=False, server_default="reserved"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("actual_provider", sa.String(length=128)),
        sa.Column("actual_model", sa.String(length=128)),
        sa.Column("provider_request_id", sa.String(length=240)),
        sa.Column("token_usage", sa.JSON()),
        sa.Column("cost_details", sa.JSON()),
        sa.Column("request_json", sa.JSON()),
        sa.Column("transcript_text", sa.String()),
        sa.Column("raw_response_json", sa.JSON()),
        sa.Column("validated_result_json", sa.JSON()),
        sa.Column("request_hash", sa.String(length=64)),
        sa.Column("transcript_hash", sa.String(length=64)),
        sa.Column("raw_response_hash", sa.String(length=64)),
        sa.Column("validated_result_hash", sa.String(length=64)),
        sa.Column("export_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("export_attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_export_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("next_export_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("export_confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("last_export_error_code", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "candidate_id",
            "provider_attempt",
            "call_sequence",
            name="uq_generation_calls_candidate_provider_sequence",
        ),
        sa.UniqueConstraint("observation_id", name="uq_generation_calls_observation_id"),
    )
    op.create_index(
        "ix_generation_calls_workspace_export",
        "generation_calls",
        ["workspace_id", "export_status"],
    )
    op.create_index("ix_generation_calls_meeting_id", "generation_calls", ["meeting_id"])
    op.create_index("ix_generation_calls_candidate_id", "generation_calls", ["candidate_id"])

    op.create_table(
        "prompt_optimization_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("deployment_scope", sa.String(length=32), nullable=False, server_default="global"),
        sa.Column("initiated_by_actor_id", sa.String(length=240), nullable=False),
        sa.Column("prompt_name", sa.String(length=240), nullable=False),
        sa.Column("source_prompt_version", sa.Integer(), nullable=False),
        sa.Column("source_config_hash", sa.String(length=64), nullable=False),
        sa.Column("train_dataset_ref", sa.String(length=500), nullable=False),
        sa.Column("development_dataset_ref", sa.String(length=500), nullable=False),
        sa.Column("heldout_dataset_ref", sa.String(length=500), nullable=False),
        sa.Column("dataset_manifest_hashes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("optimizer_version", sa.String(length=64), nullable=False),
        sa.Column("adapter_version", sa.String(length=64), nullable=False),
        sa.Column("metric_versions", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reflection_prompt_name", sa.String(length=240), nullable=False),
        sa.Column("reflection_prompt_version", sa.Integer(), nullable=False),
        sa.Column("reflection_config_hash", sa.String(length=64), nullable=False),
        sa.Column("judge_prompt_refs", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("budget", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("workflow_id", sa.String(length=240), nullable=False, unique=True),
        sa.Column("workflow_run_id", sa.String(length=240)),
        sa.Column("run_artifact_ref", sa.String(length=500)),
        sa.Column("checkpoint_revision", sa.Integer()),
        sa.Column("checkpoint_hash", sa.String(length=64)),
        sa.Column("checkpoint_schema_version", sa.String(length=64)),
        sa.Column("candidate_prompt_version", sa.Integer()),
        sa.Column("candidate_prompt_hash", sa.String(length=64)),
        sa.Column("candidate_config_hash", sa.String(length=64)),
        sa.Column("aggregate_scores", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("rollback_prompt_version", sa.Integer(), nullable=False),
        sa.Column(
            "approval_state", sa.String(length=32), nullable=False, server_default="not_requested"
        ),
        sa.Column("approval_expires_at", sa.DateTime(timezone=True)),
        sa.Column("approval_action_id", sa.Uuid(), unique=True),
        sa.Column("approved_by_actor_id", sa.String(length=240)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("failure_code", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_prompt_optimization_runs_prompt_status",
        "prompt_optimization_runs",
        ["prompt_name", "status"],
    )

    op.create_table(
        "prompt_optimization_call_ledger",
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey("prompt_optimization_runs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("call_key", sa.String(length=128), primary_key=True),
        sa.Column("phase", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False),
        sa.Column("config_hash", sa.String(length=64), nullable=False),
        sa.Column("model_route", sa.String(length=128), nullable=False),
        sa.Column("reserved_token_ceiling", sa.Integer(), nullable=False),
        sa.Column("reserved_cost_ceiling", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="reserved"),
        sa.Column("result_artifact_ref", sa.String(length=500)),
        sa.Column("actual_input_tokens", sa.Integer()),
        sa.Column("actual_output_tokens", sa.Integer()),
        sa.Column("actual_cost", sa.String(length=64)),
        sa.Column("activity_attempt", sa.Integer(), nullable=False),
        sa.Column("activity_fence", sa.Uuid(), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_prompt_optimization_call_ledger_run_status",
        "prompt_optimization_call_ledger",
        ["run_id", "status"],
    )

    if _is_postgresql():
        for table_name, expression in TENANT_TABLE_POLICIES.items():
            _create_policy(table_name, expression)
        for table_name in GLOBAL_OPERATOR_TABLES:
            _create_policy(table_name, "rec_maintenance_allowed()")


def downgrade() -> None:
    if _is_postgresql():
        for table_name in (*TENANT_TABLE_POLICIES, *GLOBAL_OPERATOR_TABLES):
            _drop_policy(table_name)

    op.drop_index(
        "ix_prompt_optimization_call_ledger_run_status",
        table_name="prompt_optimization_call_ledger",
    )
    op.drop_table("prompt_optimization_call_ledger")
    op.drop_index(
        "ix_prompt_optimization_runs_prompt_status", table_name="prompt_optimization_runs"
    )
    op.drop_table("prompt_optimization_runs")
    op.drop_index("ix_generation_calls_candidate_id", table_name="generation_calls")
    op.drop_index("ix_generation_calls_meeting_id", table_name="generation_calls")
    op.drop_index("ix_generation_calls_workspace_export", table_name="generation_calls")
    op.drop_table("generation_calls")
    op.drop_index(
        "uq_meeting_share_invitations_address_status",
        table_name="meeting_share_invitations",
    )
    op.drop_table("meeting_share_invitations")

    op.drop_index("uq_meeting_share_grants_active_link", table_name="meeting_share_grants")
    op.drop_index("uq_meeting_share_grants_active_user", table_name="meeting_share_grants")
    # The legacy schema allowed only one row per recipient and status. Feature 121
    # deliberately retains every revoke/re-grant cycle, so downgrade must compact
    # duplicate historical revoked rows before restoring that older constraint.
    op.execute(
        """
        with ranked as (
            select id,
                   row_number() over (
                       partition by workspace_id, meeting_id, grantee_user_id, status
                       order by created_at desc, id desc
                   ) as row_number
            from meeting_share_grants
            where grantee_user_id is not null
        )
        delete from meeting_share_grants
        where id in (select id from ranked where row_number > 1)
        """
    )
    op.create_unique_constraint(
        "uq_meeting_share_grants_active_user",
        "meeting_share_grants",
        ["workspace_id", "meeting_id", "grantee_user_id", "status"],
    )

    for column_name in (
        "last_used_at",
        "rotated_at",
        "expires_at",
        "can_export",
        "can_download",
        "content_scope",
        "audience_id",
        "audience_type",
    ):
        op.drop_column("meeting_share_grants", column_name)

    op.drop_index(
        "ix_generation_attempt_workflow_id",
        table_name="meeting_outcome_generation_attempts",
    )
    op.drop_constraint(
        "uq_generation_attempt_candidate_id",
        "meeting_outcome_generation_attempts",
        type_="unique",
    )
    op.drop_constraint(
        "fk_generation_attempt_template",
        "meeting_outcome_generation_attempts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_generation_attempt_requested_by",
        "meeting_outcome_generation_attempts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_generation_attempt_source_result",
        "meeting_outcome_generation_attempts",
        type_="foreignkey",
    )
    for column_name in (
        "failure_code",
        "attempt_count",
        "temporal_transcript_chunk_count",
        "temporal_transcript_hash",
        "langfuse_trace_id",
        "workflow_run_id",
        "workflow_id",
        "model_parameters",
        "model_route",
        "output_schema_version",
        "prompt_hash",
        "prompt_config",
        "prompt_definition",
        "prompt_source",
        "prompt_version",
        "prompt_name",
        "detail_level",
        "output_language",
        "template_version",
        "template_key",
        "template_id",
        "requested_by_user_id",
        "source_result_id",
        "candidate_id",
    ):
        op.drop_column("meeting_outcome_generation_attempts", column_name)

    for constraint_name in (
        "fk_outcome_sets_supersedes",
        "fk_outcome_sets_accepted_by",
        "fk_outcome_sets_requested_by",
        "fk_outcome_sets_template",
    ):
        op.drop_constraint(constraint_name, "meeting_outcome_sets", type_="foreignkey")
    op.drop_constraint("fk_meetings_current_outcome_set", "meetings", type_="foreignkey")
    for column_name in (
        "supersedes_outcome_set_id",
        "accepted_at",
        "accepted_by_user_id",
        "requested_by_user_id",
        "revision_state",
        "detail_level",
        "output_language",
        "template_version",
        "template_key",
        "template_id",
    ):
        op.drop_column("meeting_outcome_sets", column_name)
    op.drop_column("meetings", "current_outcome_set_id")
    op.drop_constraint(
        "fk_workspaces_default_summary_template",
        "workspaces",
        type_="foreignkey",
    )
    op.drop_column("workspaces", "default_summary_template_version")
    op.drop_column("workspaces", "default_summary_template_id")
    op.drop_column("workspaces", "default_summary_template_key")
    op.drop_index("ix_summary_templates_workspace_status", table_name="summary_templates")
    op.drop_table("summary_templates")
