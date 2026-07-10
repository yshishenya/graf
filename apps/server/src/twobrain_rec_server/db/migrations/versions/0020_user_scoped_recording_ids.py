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


def _drop_legacy_constraint() -> None:
    if _dialect_name() == "postgresql":
        for constraint_name in POSTGRES_LEGACY_MEETING_CONSTRAINTS:
            if _postgres_constraint_exists("meetings", constraint_name):
                op.drop_constraint(constraint_name, "meetings", type_="unique")
                return
        raise RuntimeError("legacy meetings local_recording_id unique constraint not found")
    with op.batch_alter_table("meetings", naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint(LEGACY_CONSTRAINT, type_="unique")


def _restore_legacy_constraint() -> None:
    if _dialect_name() == "postgresql":
        op.create_unique_constraint(
            "meetings_workspace_id_local_recording_id_key",
            "meetings",
            ["workspace_id", "local_recording_id"],
        )
        return
    with op.batch_alter_table("meetings", naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.create_unique_constraint(LEGACY_CONSTRAINT, ["workspace_id", "local_recording_id"])


def _drop_legacy_media_revision_constraint() -> None:
    if _dialect_name() == "postgresql":
        for constraint_name in POSTGRES_LEGACY_MEDIA_REVISION_CONSTRAINTS:
            if _postgres_constraint_exists("media_revisions", constraint_name):
                op.drop_constraint(constraint_name, "media_revisions", type_="unique")
                return
        raise RuntimeError("legacy media_revisions local_media_revision_id unique constraint not found")
    with op.batch_alter_table("media_revisions") as batch_op:
        batch_op.drop_constraint(LEGACY_MEDIA_REVISION_CONSTRAINT, type_="unique")


def _restore_legacy_media_revision_constraint() -> None:
    if _dialect_name() == "postgresql":
        op.create_unique_constraint(
            LEGACY_MEDIA_REVISION_CONSTRAINT,
            "media_revisions",
            ["workspace_id", "local_media_revision_id"],
        )
        return
    with op.batch_alter_table("media_revisions") as batch_op:
        batch_op.create_unique_constraint(LEGACY_MEDIA_REVISION_CONSTRAINT, ["workspace_id", "local_media_revision_id"])


def upgrade() -> None:
    _drop_legacy_constraint()
    _drop_legacy_media_revision_constraint()
    if _dialect_name() == "postgresql":
        op.create_unique_constraint(
            NEW_CONSTRAINT,
            "meetings",
            ["workspace_id", "created_by_user_id", "local_recording_id"],
        )
        op.create_unique_constraint(
            NEW_MEDIA_REVISION_CONSTRAINT,
            "media_revisions",
            ["workspace_id", "meeting_id", "local_media_revision_id"],
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
        op.drop_constraint(NEW_CONSTRAINT, "meetings", type_="unique")
        op.drop_constraint(NEW_MEDIA_REVISION_CONSTRAINT, "media_revisions", type_="unique")
    else:
        with op.batch_alter_table("meetings") as batch_op:
            batch_op.drop_constraint(NEW_CONSTRAINT, type_="unique")
        with op.batch_alter_table("media_revisions") as batch_op:
            batch_op.drop_constraint(NEW_MEDIA_REVISION_CONSTRAINT, type_="unique")
    _restore_legacy_media_revision_constraint()
    _restore_legacy_constraint()
