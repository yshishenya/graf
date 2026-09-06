"""Replace the two-zone default with an optional account IANA preference."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0086_user_timezone"
down_revision: str = "0085_merge_summary_mediascribe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("user_identities_timezone_allowed", "user_identities", type_="check")
    op.alter_column("user_identities", "timezone", existing_type=sa.String(64),
                    nullable=True, server_default=None)
    # Preserve explicit choices; the previous Moscow default was not device detection.
    op.execute("""
        UPDATE user_identities AS u SET timezone = NULL
        WHERE timezone = 'Europe/Moscow' AND NOT EXISTS (
            SELECT 1 FROM auth_audit_events AS a
            WHERE a.user_id = u.id AND a.event_type = 'account_preferences_updated'
                AND a.outcome = 'success'
                AND (a.metadata_json::jsonb -> 'fields') ? 'timezone'
        )
    """)
    op.create_check_constraint(
        "user_identities_timezone_allowed", "user_identities",
        "timezone IS NULL OR timezone = 'UTC' OR "
        "timezone ~ '^[A-Za-z_+-]+(/[A-Za-z0-9_+.-]+)+$'",
    )


def downgrade() -> None:
    # Refuse a lossy rollback; the operator must resolve unsupported preferences first.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM user_identities
                       WHERE timezone NOT IN ('Europe/Moscow', 'UTC')) THEN
                RAISE EXCEPTION 'Cannot downgrade: account time zones exceed Moscow/UTC';
            END IF;
        END $$
    """)
    op.drop_constraint("user_identities_timezone_allowed", "user_identities", type_="check")
    op.execute("UPDATE user_identities SET timezone = 'Europe/Moscow' WHERE timezone IS NULL")
    op.alter_column("user_identities", "timezone", existing_type=sa.String(64),
                    nullable=False, server_default="Europe/Moscow")
    op.create_check_constraint("user_identities_timezone_allowed", "user_identities",
                               "timezone in ('Europe/Moscow', 'UTC')")
