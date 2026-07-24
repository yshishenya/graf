"""mark pre-revision processing rows with an explicit legacy lineage identity

Revision ID: 0039_legacy_lineage_backfill
Revises: 0038_mediascribe_claim
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0039_legacy_lineage_backfill"
down_revision: str | None = "0038_mediascribe_claim"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PREVIOUS_MAINTENANCE_OPERATIONS = (
    "migration_verification",
    "production_smoke_setup",
    "production_smoke_cleanup",
    "backup_restore_rehearsal",
    "operator_diagnostics",
    "provider_link_cleanup",
    "playback_normalization_inventory",
    "playback_normalization_dispatch",
    "outcome_dispatch_reconciliation",
    "deletion_purge_reconciliation",
)
# Keep the operation name explicit for the RLS contract and migration audit:
# processing_legacy_lineage_reconciliation
MAINTENANCE_OPERATIONS = (*PREVIOUS_MAINTENANCE_OPERATIONS, "processing_legacy_lineage_reconciliation")


def _replace_maintenance_helper(operations: tuple[str, ...]) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    operation_literals = ", ".join(f"'{operation}'" for operation in operations)
    op.execute(
        f"""
        create or replace function rec_maintenance_allowed()
        returns boolean
        language sql
        stable
        as $$
            select rec_setting('app.context_kind') = 'maintenance'
            and rec_setting('app.maintenance_operation') = any(array[{operation_literals}])
            and rec_setting('app.maintenance_actor') is not null
            and rec_setting('app.maintenance_reason') is not null
            and rec_setting('app.maintenance_feature_area') is not null
            and session_user = 'twobrain_rec_maintenance'
        $$;
        """
    )


def upgrade() -> None:
    _replace_maintenance_helper(MAINTENANCE_OPERATIONS)
    connection = op.get_bind()
    workflows = sa.Table(
        "processing_workflows",
        sa.MetaData(),
        autoload_with=connection,
    )
    legacy_rows = connection.execute(
        sa.select(workflows.c.id, workflows.c.source_fingerprint).where(
            workflows.c.media_revision_id.is_(None),
            sa.or_(
                workflows.c.source_fingerprint.is_(None),
                ~workflows.c.source_fingerprint.like("legacy:%"),
            ),
        )
    ).all()
    for row in legacy_rows:
        connection.execute(
            workflows.update()
            .where(workflows.c.id == row.id)
            .values(source_fingerprint=f"legacy:{row.id}")
        )

    jobs = sa.Table("mediascribe_jobs", sa.MetaData(), autoload_with=connection)
    job_rows = connection.execute(
        sa.select(jobs.c.id, workflows.c.source_fingerprint)
        .select_from(jobs.join(workflows, jobs.c.processing_workflow_id == workflows.c.id))
        .where(
            jobs.c.media_revision_id.is_(None),
            workflows.c.source_fingerprint.like("legacy:%"),
        )
    ).all()
    for row in job_rows:
        connection.execute(
            jobs.update()
            .where(jobs.c.id == row.id)
            .values(source_fingerprint=row.source_fingerprint)
        )

    results = sa.Table("processing_results", sa.MetaData(), autoload_with=connection)
    result_rows = connection.execute(
        sa.select(results.c.id, jobs.c.processing_workflow_id)
        .select_from(
            results.join(jobs, results.c.mediascribe_job_id == jobs.c.id).join(
                workflows, jobs.c.processing_workflow_id == workflows.c.id
            )
        )
        .where(
            results.c.media_revision_id.is_(None),
            results.c.processing_workflow_id.is_(None),
            workflows.c.source_fingerprint.like("legacy:%"),
        )
    ).all()
    for row in result_rows:
        connection.execute(
            results.update()
            .where(results.c.id == row.id)
            .values(processing_workflow_id=row.processing_workflow_id)
        )


def downgrade() -> None:
    _replace_maintenance_helper(PREVIOUS_MAINTENANCE_OPERATIONS)
    connection = op.get_bind()
    workflows = sa.Table(
        "processing_workflows",
        sa.MetaData(),
        autoload_with=connection,
    )
    marker_count = connection.execute(
        sa.select(sa.func.count())
        .select_from(workflows)
        .where(workflows.c.source_fingerprint.like("legacy:%"))
    ).scalar_one()
    if marker_count:
        raise RuntimeError(
            "0039 downgrade requires legacy lineage markers to be reconciled first"
        )
