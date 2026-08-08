"""Persist user-scoped optional billing notification choices."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0048_billing_notification_preferences"
down_revision: str | None = "0047_referral_lookup_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "billing_notification_preferences",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), primary_key=True),
        sa.Column("optional_email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("optional_in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("alter table billing_notification_preferences enable row level security")
        op.execute("alter table billing_notification_preferences force row level security")
        op.execute(
            "create policy billing_notification_preferences_owner on billing_notification_preferences "
            "using (user_id = rec_current_user_id() or rec_maintenance_allowed()) "
            "with check (user_id = rec_current_user_id() or rec_maintenance_allowed())"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "drop policy if exists billing_notification_preferences_owner "
            "on billing_notification_preferences"
        )
    op.drop_table("billing_notification_preferences")
