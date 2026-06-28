"""calendar settings preferences

Revision ID: 0012_calendar_settings_prefs
Revises: 0011_recording_display_timezone
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_calendar_settings_prefs"
down_revision: str | None = "0011_recording_display_timezone"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
CONTENT_WORKSPACE_POLICIES = {
    "calendar_settings_preferences": "((rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())",
}


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.create_table(
        "calendar_settings_preferences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("join_prompt_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("record_prompt_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_upcoming_time", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_upcoming_title", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("include_events_without_participants", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("include_events_without_link_or_location", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("include_all_day_events", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("include_private_free_busy_prompt_candidates", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "owner_user_id", name="uq_calendar_settings_preferences_owner"),
    )
    if _is_postgresql():
        op.execute("alter table calendar_settings_preferences enable row level security")
        op.execute("alter table calendar_settings_preferences force row level security")
        op.execute(
            "create policy calendar_settings_preferences_tenant_isolation on calendar_settings_preferences "
            f"using ({CONTENT_WORKSPACE_POLICIES['calendar_settings_preferences']}) "
            f"with check ({CONTENT_WORKSPACE_POLICIES['calendar_settings_preferences']})"
        )


def downgrade() -> None:
    if _is_postgresql():
        op.execute("drop policy if exists calendar_settings_preferences_tenant_isolation on calendar_settings_preferences")
        op.execute("alter table calendar_settings_preferences no force row level security")
        op.execute("alter table calendar_settings_preferences disable row level security")
    op.drop_table("calendar_settings_preferences")
