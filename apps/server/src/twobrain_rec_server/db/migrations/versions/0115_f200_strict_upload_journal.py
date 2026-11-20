"""Prepare the existing purge journal for strict upload attempts."""

import sqlalchemy as sa
from alembic import op

revision: str = "0115_f200_strict_upload_journal"
down_revision: str | None = "0114_f200_calendar_upload_pin"
branch_labels = None
depends_on = None

_TABLE = "meeting_purge_journal"
_COLUMNS = (
    ("storage_scope", sa.String(128)),
    ("storage_epoch", sa.BigInteger()),
    ("deletion_epoch", sa.BigInteger()),
    ("write_state", sa.String(32)),
    ("multipart_upload_id", sa.String()),
)


def upgrade():
    for name, type_ in _COLUMNS:
        op.add_column(_TABLE, sa.Column(name, type_, nullable=True))
    op.execute("CREATE SEQUENCE strict_upload_attempt_no AS bigint NO CYCLE")


def downgrade():
    # Once used, a rollback must retain compatible cleanup and the sequence.
    op.execute("ALTER SEQUENCE strict_upload_attempt_no NO CYCLE")
    op.execute("LOCK TABLE meeting_purge_journal IN ACCESS EXCLUSIVE MODE")
    op.execute("SET LOCAL row_security = off")
    op.execute("""
        DO $$
        BEGIN
            IF (SELECT is_called FROM strict_upload_attempt_no)
                OR EXISTS (
                    SELECT 1 FROM meeting_purge_journal
                    WHERE storage_scope IS NOT NULL OR storage_epoch IS NOT NULL
                       OR deletion_epoch IS NOT NULL OR write_state IS NOT NULL
                       OR multipart_upload_id IS NOT NULL
                )
            THEN
                RAISE EXCEPTION 'strict upload journal requires a compatible rollback';
            END IF;
        END
        $$;
    """)
    op.execute("DROP SEQUENCE strict_upload_attempt_no")
    for name, _ in reversed(_COLUMNS):
        op.drop_column(_TABLE, name)
