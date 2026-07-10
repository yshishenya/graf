"""user-scoped recording ids

Revision ID: 0020_user_scoped_recording_ids
Revises: 0019_publish_meeting_registry
Create Date: 2026-07-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_user_scoped_recording_ids"
down_revision: str | None = "0019_publish_meeting_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_CONSTRAINT = "uq_meetings_workspace_id_local_recording_id"
NEW_CONSTRAINT = "uq_meetings_workspace_user_local_recording"
LEGACY_MEDIA_REVISION_CONSTRAINT = "uq_media_revisions_workspace_local_revision"
NEW_MEDIA_REVISION_CONSTRAINT = "uq_media_revisions_workspace_meeting_local_revision"
POSTGRES_LEGACY_MEETING_CONSTRAINTS = (
    "uq_meetings_workspace_id",
    "meetings_workspace_id_local_recording_id_key",
    LEGACY_CONSTRAINT,
)
POSTGRES_LEGACY_MEDIA_REVISION_CONSTRAINTS = (
    "media_revisions_workspace_id_local_media_revision_id_key",
    LEGACY_MEDIA_REVISION_CONSTRAINT,
)
NAMING_CONVENTION = {
    "uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s",
}
MEETING_LEGACY_COLUMNS = ("workspace_id", "local_recording_id")
MEETING_NEW_COLUMNS = ("workspace_id", "created_by_user_id", "local_recording_id")
MEDIA_REVISION_LEGACY_COLUMNS = ("workspace_id", "local_media_revision_id")
MEDIA_REVISION_NEW_COLUMNS = ("workspace_id", "meeting_id", "local_media_revision_id")


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def _postgres_constraint_exists(table_name: str, constraint_name: str) -> bool:
    return bool(
        op.get_bind()
        .execute(
            sa.text(
                """
                select 1
                from pg_constraint c
                join pg_class t on t.oid = c.conrelid
                where t.relname = :table_name
                  and c.conname = :constraint_name
                  and c.contype = 'u'
                  and pg_table_is_visible(t.oid)
                """
            ),
            {"table_name": table_name, "constraint_name": constraint_name},
        )
        .scalar()
    )


def _postgres_unique_constraint_name_for_columns(table_name: str, columns: tuple[str, ...]) -> str | None:
    return op.get_bind().execute(
        sa.text(
            """
            select c.conname
            from pg_constraint c
            join pg_class t on t.oid = c.conrelid
            where t.relname = :table_name
              and c.contype = 'u'
              and pg_table_is_visible(t.oid)
              and (
                  select string_agg(a.attname, ',' order by keys.ordinality)
                  from unnest(c.conkey) with ordinality as keys(attnum, ordinality)
                  join pg_attribute a on a.attrelid = c.conrelid and a.attnum = keys.attnum
              ) = :columns_key
            """
        ),
        {"table_name": table_name, "columns_key": ",".join(columns)},
    ).scalar()


def _drop_postgres_unique_constraint(
    table_name: str,
    candidate_names: tuple[str, ...],
    columns: tuple[str, ...],
) -> bool:
    for constraint_name in candidate_names:
        if _postgres_constraint_exists(table_name, constraint_name):
            op.drop_constraint(constraint_name, table_name, type_="unique")
            return True

    column_constraint_name = _postgres_unique_constraint_name_for_columns(table_name, columns)
    if column_constraint_name is not None:
        op.drop_constraint(column_constraint_name, table_name, type_="unique")
        return True
    return False


def _ensure_postgres_unique_constraint(table_name: str, constraint_name: str, columns: tuple[str, ...]) -> None:
    if _postgres_unique_constraint_name_for_columns(table_name, columns) is not None:
        return
    op.create_unique_constraint(constraint_name, table_name, list(columns))


def _drop_legacy_constraint() -> None:
    if _dialect_name() == "postgresql":
        _drop_postgres_unique_constraint("meetings", POSTGRES_LEGACY_MEETING_CONSTRAINTS, MEETING_LEGACY_COLUMNS)
        return
    with op.batch_alter_table("meetings", naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint(LEGACY_CONSTRAINT, type_="unique")


def _restore_legacy_constraint() -> None:
    if _dialect_name() == "postgresql":
        _ensure_postgres_unique_constraint(
            "meetings",
            LEGACY_CONSTRAINT,
            MEETING_LEGACY_COLUMNS,
        )
        return
    with op.batch_alter_table("meetings", naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.create_unique_constraint(LEGACY_CONSTRAINT, ["workspace_id", "local_recording_id"])


def _drop_legacy_media_revision_constraint() -> None:
    if _dialect_name() == "postgresql":
        _drop_postgres_unique_constraint(
            "media_revisions",
            POSTGRES_LEGACY_MEDIA_REVISION_CONSTRAINTS,
            MEDIA_REVISION_LEGACY_COLUMNS,
        )
        return
    with op.batch_alter_table("media_revisions") as batch_op:
        batch_op.drop_constraint(LEGACY_MEDIA_REVISION_CONSTRAINT, type_="unique")


def _restore_legacy_media_revision_constraint() -> None:
    if _dialect_name() == "postgresql":
        _ensure_postgres_unique_constraint(
            "media_revisions",
            LEGACY_MEDIA_REVISION_CONSTRAINT,
            MEDIA_REVISION_LEGACY_COLUMNS,
        )
        return
    with op.batch_alter_table("media_revisions") as batch_op:
        batch_op.create_unique_constraint(LEGACY_MEDIA_REVISION_CONSTRAINT, ["workspace_id", "local_media_revision_id"])


def upgrade() -> None:
    _drop_legacy_constraint()
    _drop_legacy_media_revision_constraint()
    if _dialect_name() == "postgresql":
        _ensure_postgres_unique_constraint(
            "meetings",
            NEW_CONSTRAINT,
            MEETING_NEW_COLUMNS,
        )
        _ensure_postgres_unique_constraint(
            "media_revisions",
            NEW_MEDIA_REVISION_CONSTRAINT,
            MEDIA_REVISION_NEW_COLUMNS,
        )
        return
    with op.batch_alter_table("meetings") as batch_op:
        batch_op.create_unique_constraint(
            NEW_CONSTRAINT,
            ["workspace_id", "created_by_user_id", "local_recording_id"],
        )
    with op.batch_alter_table("media_revisions") as batch_op:
        batch_op.create_unique_constraint(
            NEW_MEDIA_REVISION_CONSTRAINT,
            ["workspace_id", "meeting_id", "local_media_revision_id"],
        )


def downgrade() -> None:
    if _dialect_name() == "postgresql":
        _drop_postgres_unique_constraint("meetings", (NEW_CONSTRAINT,), MEETING_NEW_COLUMNS)
        _drop_postgres_unique_constraint("media_revisions", (NEW_MEDIA_REVISION_CONSTRAINT,), MEDIA_REVISION_NEW_COLUMNS)
    else:
        with op.batch_alter_table("meetings") as batch_op:
            batch_op.drop_constraint(NEW_CONSTRAINT, type_="unique")
        with op.batch_alter_table("media_revisions") as batch_op:
            batch_op.drop_constraint(NEW_MEDIA_REVISION_CONSTRAINT, type_="unique")
    _restore_legacy_media_revision_constraint()
    _restore_legacy_constraint()
