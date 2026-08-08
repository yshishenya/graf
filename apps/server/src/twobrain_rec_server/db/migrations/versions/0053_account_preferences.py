"""Persist account-scoped locale, timezone and theme preferences."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0053_account_preferences"
down_revision: str | None = "0052_source_artifact_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_identities",
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="ru-RU"),
    )
    op.add_column(
        "user_identities",
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="Europe/Moscow",
        ),
    )
    op.add_column(
        "user_identities",
        sa.Column("theme", sa.String(length=16), nullable=False, server_default="system"),
    )
    op.add_column(
        "external_identities",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_check_constraint(
        "user_identities_locale_allowed",
        "user_identities",
        "locale in ('ru-RU', 'en-US')",
    )
    op.create_check_constraint(
        "user_identities_timezone_allowed",
        "user_identities",
        "timezone in ('Europe/Moscow', 'UTC')",
    )
    op.create_check_constraint(
        "user_identities_theme_allowed",
        "user_identities",
        "theme in ('system', 'dark', 'light')",
    )


def downgrade() -> None:
    for name in (
        "user_identities_theme_allowed",
        "user_identities_timezone_allowed",
        "user_identities_locale_allowed",
    ):
        op.drop_constraint(name, "user_identities", type_="check")
    for name in ("theme", "timezone", "locale"):
        op.drop_column("user_identities", name)
    op.drop_column("external_identities", "is_active")
