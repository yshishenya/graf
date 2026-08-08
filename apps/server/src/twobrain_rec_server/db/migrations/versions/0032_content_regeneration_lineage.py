"""add revision-scoped processing lineage and lifecycle fences

Revision ID: 0032_content_regen_lineage
Revises: 0031_recording_workflows
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_content_regen_lineage"
down_revision: str | None = "0031_recording_workflows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = (
    "dispatch_intents",
    "meeting_deletion_fences",
)
TENANT_POLICY = (
    "((rec_context_kind() in ('request', 'worker') "
    "and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())"
)
CONTENT_WORKSPACE_POLICIES = {table_name: TENANT_POLICY for table_name in TENANT_TABLES}


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _create_policy(table_name: str) -> None:
    if not _is_postgresql():
        return
    quoted = f'"{table_name}"'
    policy = f'"{table_name}_isolation"'
    op.execute(f"alter table {quoted} enable row level security")
    op.execute(f"alter table {quoted} force row level security")
    op.execute(f"drop policy if exists {policy} on {quoted}")
    op.execute(
        f"create policy {policy} on {quoted} using ({TENANT_POLICY}) "
        f"with check ({TENANT_POLICY})"
    )


def _drop_policy(table_name: str) -> None:
    if not _is_postgresql():
        return
    quoted = f'"{table_name}"'
    policy = f'"{table_name}_isolation"'
    op.execute(f"drop policy if exists {policy} on {quoted}")
    op.execute(f"alter table {quoted} no force row level security")
    op.execute(f"alter table {quoted} disable row level security")


def _restore_legacy_unique_constraints() -> None:
    # The upgrade intentionally removes these meeting-wide constraints so
    # revision-scoped history can coexist. A downgrade must not silently lose
    # the old invariant; fail with a repairable message if history now contains
    # duplicate groups that cannot fit the legacy schema.
    constraints = (
        (
            "processing_workflows",
            ("workspace_id", "meeting_id"),
            "processing_workflows_workspace_id_meeting_id_key",
        ),
        (
            "mediascribe_jobs",
            ("workspace_id", "meeting_id"),
            "uq_mediascribe_jobs_workspace_meeting",
        ),
        (
            "processing_dependency_states",
            ("workspace_id", "meeting_id", "dependency"),
            # PostgreSQL truncates the legacy unnamed constraint to 63 bytes.
            "processing_dependency_states_workspace_id_meeting_id_dependency",
        ),
    )
    bind = op.get_bind()
    for table_name, columns, constraint_name in constraints:
        grouping = ", ".join(columns)
        duplicate = bind.execute(
            sa.text(
                f"select 1 from {table_name} group by {grouping} "
                "having count(*) > 1 limit 1"
            )
        ).first()
        if duplicate is not None:
            raise RuntimeError(
                f"0032 downgrade blocked: archive or deduplicate {table_name} "
                f"before restoring {constraint_name}"
            )
        op.create_unique_constraint(constraint_name, table_name, list(columns))


def upgrade() -> None:
    # New Spec Kit revision identifiers exceed the legacy 32-character Alembic
    # version column; widen it before Alembic records this migration.
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
    op.add_column(
        "meetings",
        sa.Column("deletion_epoch", sa.BigInteger(), nullable=False, server_default="0"),
    )
    for table_name, columns in {
        "processing_workflows": (
            sa.Column("purpose", sa.String(length=64), nullable=False, server_default="transcription"),
            sa.Column("source_fingerprint", sa.String(length=128)),
            sa.Column("deletion_epoch_at_start", sa.BigInteger()),
        ),
        "mediascribe_jobs": (
            sa.Column("idempotency_key", sa.String(length=240)),
            sa.Column("source_fingerprint", sa.String(length=128)),
            sa.Column("deletion_epoch_at_start", sa.BigInteger()),
        ),
        "processing_results": (
            sa.Column("processing_workflow_id", sa.Uuid(), sa.ForeignKey("processing_workflows.id")),
            sa.Column("deletion_epoch_at_start", sa.BigInteger()),
        ),
        "processing_dependency_states": (
            # media_revision_id was introduced by the recording sync migration.
        ),
        "meeting_outcome_sets": (
            sa.Column("source_fingerprint", sa.String(length=128)),
            sa.Column("deletion_epoch_at_start", sa.BigInteger()),
            sa.Column("expires_at", sa.DateTime(timezone=True)),
        ),
        "meeting_outcome_generation_attempts": (
            sa.Column("idempotency_key", sa.String(length=240)),
            sa.Column("request_intent", sa.String(length=64), nullable=False, server_default="automatic_baseline"),
            sa.Column("source_result_hash", sa.String(length=128)),
            sa.Column("source_fingerprint", sa.String(length=128)),
            sa.Column("deletion_epoch_at_start", sa.BigInteger()),
            sa.Column("expires_at", sa.DateTime(timezone=True)),
            sa.Column("display_format_name", sa.String(length=120)),
        ),
    }.items():
        for column in columns:
            op.add_column(table_name, column)

    # Existing deployments contain only one meeting-wide active row. Drop the
    # old blockers so future revisions can coexist; terminal history remains.
    for constraint_name in (
        # The original unnamed SQLAlchemy constraint uses the naming
        # convention's first-column form on fresh databases; older installs
        # may retain Alembic's longer generated name.
        "processing_workflows_workspace_id_meeting_id_key",
        "uq_processing_workflows_workspace_id",
    ):
        op.execute(
            "alter table processing_workflows drop constraint if exists "
            + constraint_name
        )
    op.execute(
        "alter table mediascribe_jobs drop constraint if exists "
        "uq_mediascribe_jobs_workspace_meeting"
    )
    for constraint_name in (
        "processing_dependency_states_workspace_id_meeting_id_dependency",
        "uq_processing_dependency_states_workspace_id",
    ):
        op.execute(
            "alter table processing_dependency_states drop constraint if exists "
            + constraint_name
        )
    op.create_index(
        "uq_processing_workflows_active_revision",
        "processing_workflows",
        ["workspace_id", "meeting_id", "media_revision_id", "purpose", "source_fingerprint"],
        unique=True,
        postgresql_where=sa.text(
            "media_revision_id is not null and status not in "
            "('processed', 'blocked', 'failed_terminal', 'canceled')"
        ),
    )
    op.create_index(
        "uq_processing_workflows_active_legacy",
        "processing_workflows",
        ["workspace_id", "meeting_id", "purpose", "source_fingerprint"],
        unique=True,
        postgresql_where=sa.text(
            "media_revision_id is null and status not in "
            "('processed', 'blocked', 'failed_terminal', 'canceled')"
        ),
    )
    op.create_index(
        "uq_processing_workflows_active_revision_missing_source",
        "processing_workflows",
        ["workspace_id", "meeting_id", "media_revision_id", "purpose"],
        unique=True,
        postgresql_where=sa.text(
            "media_revision_id is not null and source_fingerprint is null and status not in "
            "('processed', 'blocked', 'failed_terminal', 'canceled')"
        ),
    )
    op.create_index(
        "uq_processing_workflows_active_legacy_missing_source",
        "processing_workflows",
        ["workspace_id", "meeting_id", "purpose"],
        unique=True,
        postgresql_where=sa.text(
            "media_revision_id is null and source_fingerprint is null and status not in "
            "('processed', 'blocked', 'failed_terminal', 'canceled')"
        ),
    )
    op.create_index(
        "uq_mediascribe_jobs_workspace_revision_key",
        "mediascribe_jobs",
        ["workspace_id", "media_revision_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("media_revision_id is not null and idempotency_key is not null"),
    )
    op.create_index(
        "uq_mediascribe_jobs_workspace_legacy_key",
        "mediascribe_jobs",
        ["workspace_id", "meeting_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("media_revision_id is null and idempotency_key is not null"),
    )
    op.create_index(
        "uq_processing_dependency_revision",
        "processing_dependency_states",
        ["workspace_id", "meeting_id", "media_revision_id", "dependency"],
        unique=True,
        postgresql_where=sa.text("media_revision_id is not null"),
    )
    op.create_index(
        "uq_processing_dependency_legacy",
        "processing_dependency_states",
        ["workspace_id", "meeting_id", "dependency"],
        unique=True,
        postgresql_where=sa.text("media_revision_id is null"),
    )
    op.create_index(
        "uq_processing_results_run_source_hash",
        "processing_results",
        ["workspace_id", "processing_workflow_id", "source_result_hash"],
        unique=True,
        postgresql_where=sa.text(
            "source_result_hash is not null and processing_workflow_id is not null"
        ),
    )
    op.create_index(
        "ix_meeting_outcome_sets_source_fingerprint",
        "meeting_outcome_sets",
        ["workspace_id", "meeting_id", "source_fingerprint"],
    )

    op.create_table(
        "dispatch_intents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("candidate_id", sa.Uuid()),
        sa.Column("intent_kind", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=240), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="created"),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_fingerprint", sa.String(length=128)),
        sa.Column("deletion_epoch", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("external_workflow_id", sa.String(length=240)),
        sa.Column("external_run_id", sa.String(length=240)),
        sa.Column("failure_code", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workspace_id", "idempotency_key", name="uq_dispatch_intents_workspace_idempotency_key"
        ),
    )
    op.create_index("ix_dispatch_intents_due", "dispatch_intents", ["state", "next_attempt_at"])
    op.create_index("ix_dispatch_intents_meeting", "dispatch_intents", ["workspace_id", "meeting_id"])

    op.create_table(
        "meeting_deletion_fences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("epoch", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="active"),
        sa.Column("retention_boundary", sa.String(length=64), nullable=False, server_default="graf_controlled_purge"),
        sa.Column("requested_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workspace_id", "meeting_id", name="uq_meeting_deletion_fences_workspace_meeting"
        ),
    )
    # Publish the previously generated deterministic outcome for meetings that
    # predate the pointer contract; newer revisions remain candidates until an
    # explicit accept action advances the pointer.
    op.execute(
        """
        update meetings m
           set current_outcome_set_id = (
               select os.id
                 from meeting_outcome_sets os
                where os.workspace_id = m.workspace_id
                  and os.meeting_id = m.id
                  and os.lifecycle_state = 'active'
                  and os.status in ('available', 'partial')
                  and exists (
                      select 1
                        from processing_results pr
                       where pr.id = os.processing_result_id
                         and pr.workspace_id = os.workspace_id
                         and pr.meeting_id = os.meeting_id
                         and pr.status = 'imported'
                         and (
                             os.source_result_hash is null
                             or pr.source_result_hash is null
                             or os.source_result_hash = pr.source_result_hash
                         )
                  )
                  and (
                      os.media_revision_id is null
                      or exists (
                          select 1
                            from media_revisions mr
                           where mr.id = os.media_revision_id
                             and mr.workspace_id = os.workspace_id
                             and mr.meeting_id = os.meeting_id
                             and mr.status = 'accepted'
                             and mr.immutable = true
                      )
                  )
                order by os.generated_at desc nulls last, os.created_at desc, os.id desc
                limit 1
           )
         where m.current_outcome_set_id is null
           and exists (
               select 1
                 from meeting_outcome_sets os
                where os.workspace_id = m.workspace_id
                  and os.meeting_id = m.id
                  and os.lifecycle_state = 'active'
                  and os.status in ('available', 'partial')
                  and exists (
                      select 1
                        from processing_results pr
                       where pr.id = os.processing_result_id
                         and pr.workspace_id = os.workspace_id
                         and pr.meeting_id = os.meeting_id
                         and pr.status = 'imported'
                         and (
                             os.source_result_hash is null
                             or pr.source_result_hash is null
                             or os.source_result_hash = pr.source_result_hash
                         )
                  )
                  and (
                      os.media_revision_id is null
                      or exists (
                          select 1
                            from media_revisions mr
                           where mr.id = os.media_revision_id
                             and mr.workspace_id = os.workspace_id
                             and mr.meeting_id = os.meeting_id
                             and mr.status = 'accepted'
                             and mr.immutable = true
                      )
                  )
           )
        """
    )
    op.execute(
        """
        update meeting_outcome_sets os
           set revision_state = 'accepted'
         where os.revision_state is null
           and exists (
               select 1 from meetings m
                where m.current_outcome_set_id = os.id
           )
        """
    )
    for table_name in TENANT_TABLES:
        _create_policy(table_name)


def downgrade() -> None:
    for table_name in reversed(TENANT_TABLES):
        _drop_policy(table_name)
    op.drop_table("meeting_deletion_fences")
    op.drop_index("ix_dispatch_intents_meeting", table_name="dispatch_intents")
    op.drop_index("ix_dispatch_intents_due", table_name="dispatch_intents")
    op.drop_table("dispatch_intents")
    for table_name, index_name in (
        ("meeting_outcome_sets", "ix_meeting_outcome_sets_source_fingerprint"),
        ("processing_results", "uq_processing_results_run_source_hash"),
        ("processing_dependency_states", "uq_processing_dependency_legacy"),
        ("processing_dependency_states", "uq_processing_dependency_revision"),
        ("mediascribe_jobs", "uq_mediascribe_jobs_workspace_legacy_key"),
        ("mediascribe_jobs", "uq_mediascribe_jobs_workspace_revision_key"),
        ("processing_workflows", "uq_processing_workflows_active_legacy"),
        ("processing_workflows", "uq_processing_workflows_active_revision"),
        ("processing_workflows", "uq_processing_workflows_active_legacy_missing_source"),
        ("processing_workflows", "uq_processing_workflows_active_revision_missing_source"),
    ):
        op.drop_index(index_name, table_name=table_name)
    _restore_legacy_unique_constraints()
    for table_name, columns in {
        "meeting_outcome_generation_attempts": (
            "display_format_name",
            "expires_at",
            "deletion_epoch_at_start",
            "source_fingerprint",
            "source_result_hash",
            "request_intent",
            "idempotency_key",
        ),
        "meeting_outcome_sets": ("expires_at", "deletion_epoch_at_start", "source_fingerprint"),
        "processing_results": ("deletion_epoch_at_start", "processing_workflow_id"),
        "mediascribe_jobs": ("deletion_epoch_at_start", "source_fingerprint", "idempotency_key"),
        "processing_workflows": ("deletion_epoch_at_start", "source_fingerprint", "purpose"),
    }.items():
        for column in columns:
            op.drop_column(table_name, column)
    op.drop_column("meetings", "deletion_epoch")
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=64),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
