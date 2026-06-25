"""meeting outcomes mvp

Revision ID: 0009_meeting_outcomes_mvp
Revises: 0008_recording_sync_loop
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_meeting_outcomes_mvp"
down_revision: str | None = "0008_recording_sync_loop"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTENT_CONTEXT = "rec_context_kind() in ('request', 'worker')"
CONTENT_WORKSPACE_POLICIES = {
    "meeting_outcome_sets": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "meeting_outcome_items": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "meeting_outcome_generation_attempts": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
}
POLICY_NAMES = {
    "meeting_outcome_sets": "meeting_outcome_sets_tenant_isolation",
    "meeting_outcome_items": "meeting_outcome_items_tenant_isolation",
    "meeting_outcome_generation_attempts": "meeting_outcome_generation_attempts_tenant_isolation",
}


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _maintenance_expression() -> str:
    return "rec_maintenance_allowed()"


def _policy_expression(expression: str) -> str:
    return f"(({expression}) or {_maintenance_expression()})"


def _create_all_policy(table_name: str, expression: str) -> None:
    table = _q(table_name)
    policy = _q(POLICY_NAMES[table_name])
    predicate = _policy_expression(expression)
    op.execute(f"alter table {table} enable row level security")
    op.execute(f"alter table {table} force row level security")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(
        f"create policy {policy} on {table} "
        f"using ({predicate}) "
        f"with check ({predicate})"
    )


def _drop_policy(table_name: str) -> None:
    table = _q(table_name)
    policy = _q(POLICY_NAMES[table_name])
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(f"alter table {table} no force row level security")
    op.execute(f"alter table {table} disable row level security")


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.create_table(
        "meeting_outcome_sets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("media_revision_id", sa.Uuid(), sa.ForeignKey("media_revisions.id")),
        sa.Column("processing_result_id", sa.Uuid(), sa.ForeignKey("processing_results.id"), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="queued"),
        sa.Column("summary_state", sa.String(length=64), nullable=False, server_default="processing"),
        sa.Column("key_points_state", sa.String(length=64), nullable=False, server_default="processing"),
        sa.Column("decisions_state", sa.String(length=64), nullable=False, server_default="processing"),
        sa.Column("action_items_state", sa.String(length=64), nullable=False, server_default="processing"),
        sa.Column("followups_state", sa.String(length=64), nullable=False, server_default="processing"),
        sa.Column("risks_state", sa.String(length=64), nullable=False, server_default="processing"),
        sa.Column("questions_state", sa.String(length=64), nullable=False, server_default="processing"),
        sa.Column("evidence_state", sa.String(length=64), nullable=False, server_default="processing"),
        sa.Column("source_kind", sa.String(length=64), nullable=False, server_default="extractive_generator"),
        sa.Column("generator_kind", sa.String(length=64), nullable=False, server_default="deterministic_extractive"),
        sa.Column("generator_version", sa.String(length=120), nullable=False),
        sa.Column("source_result_hash", sa.String(length=128)),
        sa.Column("content_hash", sa.String(length=128)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("generated_at", sa.DateTime(timezone=True)),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("failure_reason", sa.String(length=240)),
        sa.Column("lifecycle_state", sa.String(length=64), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workspace_id",
            "meeting_id",
            "media_revision_id",
            "processing_result_id",
            "generator_version",
            name="uq_meeting_outcome_sets_current_generator",
        ),
    )
    op.create_index(
        "ix_meeting_outcome_sets_meeting_status",
        "meeting_outcome_sets",
        ["workspace_id", "meeting_id", "status"],
    )
    op.create_table(
        "meeting_outcome_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("outcome_set_id", sa.Uuid(), sa.ForeignKey("meeting_outcome_sets.id"), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="available"),
        sa.Column("text", sa.String()),
        sa.Column("owner_text", sa.String(length=240)),
        sa.Column("due_date_text", sa.String(length=120)),
        sa.Column("truth_label", sa.String(length=64), nullable=False, server_default="supported"),
        sa.Column("source_refs_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "outcome_set_id",
            "category",
            "sequence",
            name="uq_meeting_outcome_items_set_category_sequence",
        ),
    )
    op.create_index(
        "ix_meeting_outcome_items_set_category_sequence",
        "meeting_outcome_items",
        ["outcome_set_id", "category", "sequence"],
    )
    op.create_table(
        "meeting_outcome_generation_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("media_revision_id", sa.Uuid(), sa.ForeignKey("media_revisions.id")),
        sa.Column("processing_result_id", sa.Uuid(), sa.ForeignKey("processing_results.id"), nullable=False),
        sa.Column("outcome_set_id", sa.Uuid(), sa.ForeignKey("meeting_outcome_sets.id")),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="queued"),
        sa.Column("provider_kind", sa.String(length=64), nullable=False, server_default="deterministic_extractive"),
        sa.Column("generator_version", sa.String(length=120), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("failure_reason", sa.String(length=240)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_meeting_outcome_generation_attempts_input",
        "meeting_outcome_generation_attempts",
        ["workspace_id", "meeting_id", "processing_result_id", "generator_version"],
    )
    if _is_postgresql():
        for table_name, expression in CONTENT_WORKSPACE_POLICIES.items():
            _create_all_policy(table_name, expression)


def downgrade() -> None:
    if _is_postgresql():
        for table_name in CONTENT_WORKSPACE_POLICIES:
            _drop_policy(table_name)
    op.drop_index("ix_meeting_outcome_generation_attempts_input", table_name="meeting_outcome_generation_attempts")
    op.drop_table("meeting_outcome_generation_attempts")
    op.drop_index("ix_meeting_outcome_items_set_category_sequence", table_name="meeting_outcome_items")
    op.drop_table("meeting_outcome_items")
    op.drop_index("ix_meeting_outcome_sets_meeting_status", table_name="meeting_outcome_sets")
    op.drop_table("meeting_outcome_sets")
